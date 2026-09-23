import { useEffect, useRef, useState } from "react";
import { createRoom, debugForceRound, fetchBoardMap, joinRoom, startRoom, wsUrl, type BoardMapData } from "./api";
import MapTab from "./MapTab";
import "./App.css";

type LobbyMessage = {
  type: "lobby";
  room_id: string;
  players: { player_id: string; name: string; connected: boolean }[];
  started: boolean;
  seq?: number;
};

// The engine's serialized GameState. Only the fields the UI actually reads
// are named; everything else passes through as unknown for the raw-JSON view.
type BidBoxItem = { kind: string; ref: number | string; bids: Record<string, number> };
type MinorState = {
  director_player_id: string | null;
  floated: boolean;
  treasury: number;
  trains: string[];
};
type MajorState = {
  director_player_id: string | null;
  floated: boolean;
  treasury: number;
  share_price: number | null;
  trains: string[];
  shares_in_bank_pool: number;
  shares_in_treasury: number;
};
type EngineState = {
  phase: number;
  round_type: "stock" | "operating";
  active_player_id: string | null;
  player_order: string[];
  players: Record<
    string,
    { name: string; cash: number; loans: number; shares: Record<string, number>; concessions: string[] }
  >;
  bank: { cash: number; train_pool: Record<string, number> };
  concession_bid_boxes: (BidBoxItem | null)[];
  minor_bid_boxes: (BidBoxItem | null)[];
  private_bid_boxes: (BidBoxItem | null)[];
  minors: Record<string, MinorState>;
  majors: Record<string, MajorState>;
  operating_order: string[];
  current_company_index: number;
  operating_round_index: number;
  stock_rounds_completed: number;
  game_over: boolean;
  log: string[];
  board: {
    tiles: Record<string, { tile_id: string; rotation: number; tokens: Record<string, string> }>;
    tile_pool: Record<string, number | null>;
  };
  [key: string]: unknown;
};

type StateMessage = {
  type: "state";
  state: EngineState;
  player_id_map: Record<string, string>; // lobby player_id -> engine player_id ("p1".."pN")
  seq?: number;
};

type ErrorMessage = { type: "error"; message: string };

// One hotseat "seat": a lobby player_id with its own WebSocket connection,
// so the single browser session can act as any of the players in turn.
type Seat = { lobbyPlayerId: string; name: string; ws: WebSocket };

// Pure versions of activeSeat()'s logic, usable from code that isn't inside
// a render (the "skip to operating round" fast-forward, which polls a ref
// instead of reading React state).
function activeEngineIdFor(state: EngineState): string | null {
  if (state.round_type === "operating") {
    const cid = state.operating_order[state.current_company_index] ?? null;
    if (!cid) return null;
    return state.minors[cid]?.director_player_id ?? state.majors[cid]?.director_player_id ?? null;
  }
  return state.active_player_id;
}

function seatForEngineId(engineId: string | null, seatsList: Seat[], idMap: Record<string, string>): Seat | null {
  if (!engineId) return null;
  const lobbyId = Object.entries(idMap).find(([, eng]) => eng === engineId)?.[0];
  return seatsList.find((s) => s.lobbyPlayerId === lobbyId) ?? null;
}

// A plain `new WebSocket(...)` that drops (server restart, idle timeout,
// network blip) just goes silent forever - nothing in this app used to
// retry, so a tab left open across a backend restart would look normal but
// stop receiving *any* further broadcasts, including ones triggered from
// the testing panel. Reconnects with backoff instead, and hands the caller
// each new socket via onSocket so it can update wherever the old reference
// was stored (a ref, or a specific seat's `ws` field in React state).
//
// Rooms are in-memory only (see rooms.py) - a backend restart doesn't just
// drop the connection, it erases the room itself, and the server closes
// the socket with code 4404 to say so. Retrying that forever would just
// spin, so onRoomGone fires instead and retries stop - the caller should
// clear its room/game state and tell the person to start over.
//
// Returns a cleanup function that stops retrying and closes the socket.
function connectWithRetry(
  url: string,
  onMessage: (data: string) => void,
  onSocket: (ws: WebSocket) => void,
  onStatusChange?: (connected: boolean) => void,
  onRoomGone?: () => void
): () => void {
  let stopped = false;
  let attempt = 0;
  let current: WebSocket | null = null;

  function connect() {
    if (stopped) return;
    const ws = new WebSocket(url);
    current = ws;
    onSocket(ws);
    ws.onmessage = (evt) => onMessage(evt.data);
    ws.onopen = () => {
      attempt = 0;
      onStatusChange?.(true);
    };
    ws.onclose = (evt) => {
      if (stopped) return;
      if (evt.code === 4404) {
        stopped = true;
        onRoomGone?.();
        return;
      }
      onStatusChange?.(false);
      const delay = Math.min(1000 * 2 ** attempt, 8000);
      attempt++;
      setTimeout(connect, delay);
    };
  }
  connect();

  return () => {
    stopped = true;
    current?.close();
  };
}

function App() {
  const [name, setName] = useState("");
  const [roomIdInput, setRoomIdInput] = useState("");
  const [roomId, setRoomId] = useState<string | null>(null);
  const [playerId, setPlayerId] = useState<string | null>(null);
  const [lobby, setLobby] = useState<LobbyMessage | null>(null);
  const [gameState, setGameState] = useState<EngineState | null>(null);
  const [playerIdMap, setPlayerIdMap] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [showRaw, setShowRaw] = useState(false);
  const [bidAmounts, setBidAmounts] = useState<Record<string, string>>({});
  const [dividendChoice, setDividendChoice] = useState("withhold");
  const [activeTab, setActiveTab] = useState<"bid" | "stocks" | "map" | "operate" | "players">("bid");
  const [convertPrice, setConvertPrice] = useState<Record<string, string>>({});
  const [buyCompanyId, setBuyCompanyId] = useState("");
  const [buySource, setBuySource] = useState<"bank" | "treasury">("bank");
  const [sellCompanyId, setSellCompanyId] = useState("");
  const [sellCount, setSellCount] = useState("1");
  const [includeTileLay, setIncludeTileLay] = useState(false);
  const [tileHexId, setTileHexId] = useState("");
  const [tileId, setTileId] = useState("");
  const [tileRotation, setTileRotation] = useState("0");
  const [includeBuyTrain, setIncludeBuyTrain] = useState(false);
  const [buyTrainCode, setBuyTrainCode] = useState("");
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [debugPhase, setDebugPhase] = useState("");
  const [debugRoundType, setDebugRoundType] = useState<"stock" | "operating">("operating");
  const [debugCompanyId, setDebugCompanyId] = useState("M1");
  const [debugBusy, setDebugBusy] = useState(false);
  const [debugResult, setDebugResult] = useState<string | null>(null);
  const [boardMapData, setBoardMapData] = useState<BoardMapData | null>(null);
  const [mapFocusRequest, setMapFocusRequest] = useState<{ hexId: string; nonce: number } | null>(null);
  // Count of currently-dropped sockets (single-connection mode has at most
  // one; solo mode has up to three seats) - >0 means at least one
  // connection is down and connectWithRetry is trying to bring it back.
  const [disconnectedCount, setDisconnectedCount] = useState(0);
  // Set when the server says our room itself is gone (backend restarted -
  // rooms are in-memory only), as opposed to just a dropped connection.
  // Nothing can reconnect to a room that no longer exists.
  const [roomLost, setRoomLost] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  // Mirrors gameState/playerIdMap for code that runs outside React's render
  // cycle (the "skip to operating round" fast-forward below) - reading
  // React state there would only ever see the value from when that async
  // function was called, not later broadcasts.
  const latestStateRef = useRef<EngineState | null>(null);
  const latestPlayerIdMapRef = useRef<Record<string, string>>({});
  // Highest broadcast "seq" applied so far (see rooms.py's Room.broadcast) -
  // guards against a stale message on a slower solo-mode socket landing
  // after a newer one from a faster socket and silently reverting the UI.
  // Reset whenever a new room is created/joined, since seq restarts at 1
  // per room.
  const lastSeqRef = useRef(0);
  // Guards the bot auto-pass effect against re-sending for the same turn
  // (effects can re-run before the resulting state broadcast arrives).
  const lastAutoPassedFor = useRef<string | null>(null);

  // Loaded once for the debug panel's "home hex" lookup - the same
  // cities/home-of-minor/home-of-major data MapTab already fetches for
  // itself, but App doesn't otherwise need the board map.
  useEffect(() => {
    fetchBoardMap()
      .then(setBoardMapData)
      .catch(() => {});
  }, []);

  function homeHexFor(companyId: string): string | null {
    if (!boardMapData) return null;
    const isMinor = /^M\d+$/.test(companyId);
    const minorNumber = isMinor ? parseInt(companyId.slice(1), 10) : null;
    const city = boardMapData.cities.find((c) =>
      isMinor ? c.home_of_minor.includes(minorNumber!) : c.home_of_major.includes(companyId)
    );
    return city?.id ?? null;
  }

  function handleRoomGone() {
    setRoomLost(true);
    setGameState(null);
    setLobby(null);
    setSeats([]);
    setPlayerId(null);
    setRoomId(null);
  }

  function handleStartOver() {
    setRoomLost(false);
    setError(null);
  }

  // Single-connection mode (normal multiplayer: one browser = one player)
  useEffect(() => {
    if (!roomId || !playerId || seats.length > 0) return;
    return connectWithRetry(
      wsUrl(roomId, playerId),
      (data) => handleMessage(data),
      (ws) => {
        wsRef.current = ws;
      },
      (connected) => setDisconnectedCount((n) => Math.max(0, n + (connected ? -1 : 1))),
      handleRoomGone
    );
  }, [roomId, playerId, seats.length]);

  // Solo mode: only seat 0 ("Player 1") is the human; seats 1 and 2 always
  // just pass, so you never have to click for them. This keeps the real
  // 3-player rules intact (1822 requires >=3) while playing solo.
  const isBotSeat = (s: Seat) => seats.length > 1 && s !== seats[0];

  useEffect(() => {
    if (seats.length === 0 || !gameState) return;
    const acting = activeSeat();
    if (!acting || !isBotSeat(acting)) return;

    const activeEngineId =
      gameState.round_type === "operating" ? activeCompanyDirector() : gameState.active_player_id;
    const signature = `${gameState.round_type}:${activeEngineId}:${gameState.current_company_index}:${gameState.operating_round_index}:${gameState.stock_rounds_completed}`;
    if (lastAutoPassedFor.current === signature) return;

    // Marking lastAutoPassedFor only happens once the pass is actually
    // sent, not when the timer is merely scheduled: React 18 StrictMode
    // double-invokes effects in dev (mount -> cleanup -> mount), and the
    // cleanup below cancels the first invocation's timer. If the ref were
    // set eagerly here, that cancelled timer would still "count" as sent,
    // and the second invocation's guard would skip scheduling a real one -
    // leaving nothing pending and the bot stuck forever.
    const timer = setTimeout(() => {
      if (lastAutoPassedFor.current === signature) return;
      lastAutoPassedFor.current = signature;
      acting.ws.send(JSON.stringify({ type: "pass" }));
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameState, seats]);

  function handleMessage(raw: string) {
    const msg = JSON.parse(raw) as LobbyMessage | StateMessage | ErrorMessage;
    if (msg.type === "lobby" || msg.type === "state") {
      if (msg.seq !== undefined) {
        if (msg.seq <= lastSeqRef.current) return; // stale - a newer broadcast already landed
        lastSeqRef.current = msg.seq;
      }
    }
    if (msg.type === "lobby") setLobby(msg);
    if (msg.type === "state") {
      setGameState(msg.state);
      setPlayerIdMap(msg.player_id_map);
      latestStateRef.current = msg.state;
      latestPlayerIdMapRef.current = msg.player_id_map;
    }
    if (msg.type === "error") setError(msg.message);
  }

  async function handleCreate() {
    setError(null);
    try {
      const { room_id } = await createRoom();
      setRoomIdInput(room_id);
      const { player_id } = await joinRoom(room_id, name || "Player");
      lastSeqRef.current = 0;
      setRoomId(room_id);
      setPlayerId(player_id);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleJoin() {
    setError(null);
    try {
      const { player_id } = await joinRoom(roomIdInput, name || "Player");
      lastSeqRef.current = 0;
      setRoomId(roomIdInput);
      setPlayerId(player_id);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleStart() {
    if (!roomId) return;
    setError(null);
    try {
      await startRoom(roomId);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // Solo: one browser opens a connection per seat (engine still needs 3
  // players), but only seat 0 is driven by the human - seats 1 and 2 are
  // auto-passed by the effect above whenever it's their turn.
  async function handleSoloGame() {
    setError(null);
    try {
      const { room_id } = await createRoom();
      lastSeqRef.current = 0;
      const names = ["Player 1", "Player 2", "Player 3"];
      const newSeats: Seat[] = [];
      for (const seatName of names) {
        const { player_id } = await joinRoom(room_id, seatName);
        // seat.ws is mutated in place by connectWithRetry on every
        // (re)connect - the `seats` React state array keeps holding this
        // same object, so later code reading seat.ws always sees the
        // current socket without needing a setSeats round-trip.
        const seat: Seat = { lobbyPlayerId: player_id, name: seatName, ws: null as unknown as WebSocket };
        connectWithRetry(
          wsUrl(room_id, player_id),
          (data) => handleMessage(data),
          (ws) => {
            seat.ws = ws;
          },
          (connected) => setDisconnectedCount((n) => Math.max(0, n + (connected ? -1 : 1))),
          handleRoomGone
        );
        newSeats.push(seat);
      }
      setRoomId(room_id);
      setSeats(newSeats);
      await new Promise((r) => setTimeout(r, 200)); // let sockets connect before starting
      await startRoom(room_id);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // Testing convenience: starts a solo game exactly like handleSoloGame,
  // then plays out real, legitimate actions (bid on the first minor,
  // pass everyone else through) until an operating round actually starts -
  // so map/tile-lay features can be tested immediately without manually
  // clicking through the bidding phase every time. Nothing here is faked;
  // it's the same websocket actions a human would send.
  async function handleSoloGameSkipToOperating() {
    setError(null);
    try {
      const { room_id } = await createRoom();
      lastSeqRef.current = 0;
      const names = ["Player 1", "Player 2", "Player 3"];
      const newSeats: Seat[] = [];
      for (const seatName of names) {
        const { player_id } = await joinRoom(room_id, seatName);
        const seat: Seat = { lobbyPlayerId: player_id, name: seatName, ws: null as unknown as WebSocket };
        connectWithRetry(
          wsUrl(room_id, player_id),
          (data) => handleMessage(data),
          (ws) => {
            seat.ws = ws;
          },
          (connected) => setDisconnectedCount((n) => Math.max(0, n + (connected ? -1 : 1))),
          handleRoomGone
        );
        newSeats.push(seat);
      }
      setRoomId(room_id);
      setSeats(newSeats);
      await new Promise((r) => setTimeout(r, 300));
      await startRoom(room_id);

      for (let i = 0; i < 30 && !latestStateRef.current; i++) {
        await new Promise((r) => setTimeout(r, 150));
      }

      // Each iteration sends exactly one action and then waits for the
      // resulting broadcast to actually land (polling latestStateRef, which
      // handleMessage updates synchronously) before deciding what to do
      // next - rather than firing on a fixed timer. A fixed-timer loop can
      // queue up several actions before it has processed any of their
      // results: by the time it locally notices the operating round has
      // begun and stops sending *new* actions, a few already-sent ones
      // (e.g. extra passes) may still be in flight, and the server applies
      // them anyway - passing M24 straight through its operate turn and on
      // into further minor floats the loop never intended to trigger. This
      // way there is only ever one action outstanding at a time, so the
      // loop stops the instant it observes an operating round with nothing
      // still queued behind it.
      let biddedOnMinor = false;
      for (let i = 0; i < 40; i++) {
        const state = latestStateRef.current;
        if (!state || state.round_type === "operating") break;

        const seat = seatForEngineId(activeEngineIdFor(state), newSeats, latestPlayerIdMapRef.current);
        if (!seat) break;

        if (!biddedOnMinor) {
          const boxIndex = state.minor_bid_boxes.findIndex((b) => b !== null);
          if (boxIndex >= 0) {
            seat.ws.send(
              JSON.stringify({ type: "bid", bids: [{ kind: "minor", box_index: boxIndex, amount: 100 }] })
            );
            biddedOnMinor = true;
          } else {
            seat.ws.send(JSON.stringify({ type: "pass" }));
          }
        } else {
          seat.ws.send(JSON.stringify({ type: "pass" }));
        }

        const stateBefore = state;
        for (let w = 0; w < 40 && latestStateRef.current === stateBefore; w++) {
          await new Promise((r) => setTimeout(r, 50));
        }
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // The seat (WebSocket) that should act right now: whoever the engine says
  // is on turn, mapped from engine player_id back to a lobby seat.
  function activeSeat(): Seat | null {
    if (!gameState || seats.length === 0) return null;
    const activeEngineId =
      gameState.round_type === "operating" ? activeCompanyDirector() : gameState.active_player_id;
    if (!activeEngineId) return null;
    const lobbyId = Object.entries(playerIdMap).find(([, eng]) => eng === activeEngineId)?.[0];
    return seats.find((s) => s.lobbyPlayerId === lobbyId) ?? null;
  }

  function activeCompanyId(): string | null {
    if (!gameState) return null;
    return gameState.operating_order[gameState.current_company_index] ?? null;
  }

  function activeCompanyDirector(): string | null {
    const cid = activeCompanyId();
    if (!cid || !gameState) return null;
    return gameState.minors[cid]?.director_player_id ?? gameState.majors[cid]?.director_player_id ?? null;
  }

  // Which company the Map tab checks connectivity against: the real
  // active company during a genuine operating round, or otherwise the
  // testing panel's own company picker - laying a tile there (via
  // debug/force_tile_lay) never requires an actual operating round, so it
  // needs a company some other way.
  function mapCompanyIdFor(): string | null {
    if (gameState?.round_type === "operating") return activeCompanyId();
    return debugCompanyId || null;
  }

  function send(action: object) {
    const seat = activeSeat();
    if (!seat) {
      setError("No seat can currently act (no one is on turn, or that seat isn't connected).");
      return;
    }
    setError(null);
    seat.ws.send(JSON.stringify(action));
  }

  function sendPass() {
    send({ type: "pass" });
  }

  function sendBid(kind: string, boxIndex: number) {
    const key = `${kind}-${boxIndex}`;
    const amount = parseInt(bidAmounts[key] ?? "", 10);
    if (!amount || amount <= 0) {
      setError("Enter a bid amount first.");
      return;
    }
    send({ type: "bid", bids: [{ kind, box_index: boxIndex, amount }] });
  }

  function sendConvertConcession(abbr: string) {
    const priceStr = convertPrice[abbr] ?? "";
    const startPrice = parseInt(priceStr, 10);
    if (!startPrice || startPrice <= 0) {
      setError("Enter a starting share price first.");
      return;
    }
    send({ type: "convert_concession", abbr, start_price: startPrice });
  }

  function sendBuyShare() {
    if (!buyCompanyId) {
      setError("Pick a company to buy into first.");
      return;
    }
    send({ type: "buy_share", company_id: buyCompanyId, source: buySource });
  }

  function sendSellShares() {
    const count = parseInt(sellCount, 10);
    if (!sellCompanyId || !count || count <= 0) {
      setError("Pick a company and a positive count to sell first.");
      return;
    }
    send({ type: "sell_shares", company_id: sellCompanyId, count });
  }

  // Testing/debug only: jumps the live room straight to a phase and/or
  // round via the server's debug endpoint, instead of playing bid/pass
  // actions through to get there. The endpoint broadcasts the result like
  // any real action, so this session's own sockets pick it up automatically.
  async function handleDebugForceRound(opts: { phase?: number; roundType?: "stock" | "operating" }) {
    setDebugResult(null);
    if (!roomId) {
      setDebugResult("Nothing to do: not connected to a room right now.");
      return;
    }
    setError(null);
    setDebugBusy(true);
    try {
      const payload: Parameters<typeof debugForceRound>[1] = { ...opts };
      if (opts.roundType === "operating") {
        if (!debugCompanyId) {
          setDebugResult("Pick a company first.");
          return;
        }
        payload.companyId = debugCompanyId;
        // Always direct to *this* browser's own seat (never a company's
        // pre-existing director, who may be a bot seat left over from
        // ordinary background bidding) - otherwise the frontend's bot
        // auto-pass effect can end this single-company operating round
        // with a legitimate pass within ~300ms, reverting straight back
        // to a stock round before anyone can act on it.
        const humanLobbyId = seats.length > 0 ? seats[0].lobbyPlayerId : playerId;
        const humanEngineId = humanLobbyId ? playerIdMap[humanLobbyId] : undefined;
        if (humanEngineId) payload.playerId = humanEngineId;
      }
      const result = await debugForceRound(roomId, payload);
      setDebugResult(`Server confirmed: phase ${result.phase}, ${result.round_type} round.`);
      if (opts.roundType === "operating") {
        const home = homeHexFor(debugCompanyId);
        if (home) {
          setActiveTab("map");
          setMapFocusRequest({ hexId: home, nonce: Date.now() });
        }
      }
    } catch (e) {
      setDebugResult(`Failed: ${(e as Error).message}`);
    } finally {
      setDebugBusy(false);
    }
  }

  function sendOperate() {
    const cid = activeCompanyId();
    if (!cid) return;
    const action: Record<string, unknown> = { type: "operate", company_id: cid, dividend_choice: dividendChoice };
    if (includeTileLay) {
      if (!tileHexId || !tileId) {
        setError("Enter both a hex id and a tile id for the tile lay, or uncheck it.");
        return;
      }
      action.tile_lay = { hex_id: tileHexId, tile_id: tileId, rotation: parseInt(tileRotation, 10) || 0 };
    }
    if (includeBuyTrain) {
      if (!buyTrainCode) {
        setError("Pick a train to buy, or uncheck it.");
        return;
      }
      action.buy_train = buyTrainCode;
    }
    send(action);
  }

  function nameFor(engineId: string | null): string {
    if (!engineId || !gameState) return "-";
    return gameState.players[engineId]?.name ?? engineId;
  }

  const inHotseat = seats.length > 0;
  const seat = activeSeat();

  return (
    <div className="app">
      <h1>1822</h1>
      {roomLost && (
        <p className="room-lost-banner">
          Your game session was lost - the server was restarted, and rooms aren't saved across restarts. Please
          start a new game below.{" "}
          <button onClick={handleStartOver}>Dismiss</button>
        </p>
      )}
      {!roomId && (
        <div className="join-form">
          <input placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} />
          <div>
            <button onClick={handleCreate}>Create room</button>
          </div>
          <div>
            <input
              placeholder="Room code"
              value={roomIdInput}
              onChange={(e) => setRoomIdInput(e.target.value)}
            />
            <button onClick={handleJoin}>Join room</button>
          </div>
          <div className="solo-row">
            <button onClick={handleSoloGame}>Start solo game (you vs 2 auto-passing bots)</button>
          </div>
          <div className="solo-row">
            <button onClick={handleSoloGameSkipToOperating} className="skip-to-operating-btn">
              Start solo game, skip straight to an operating round (for testing)
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </div>
      )}

      {roomId && !inHotseat && !gameState && (
        <div className="lobby">
          <p>
            Room code: <strong>{roomId}</strong> (share this with other players)
          </p>
          <ul>
            {lobby?.players.map((p) => (
              <li key={p.player_id}>
                {p.name} {p.connected ? "🟢" : "⚪"}
              </li>
            ))}
          </ul>
          <button onClick={handleStart} disabled={(lobby?.players.length ?? 0) < 3}>
            Start game ({lobby?.players.length ?? 0}/3-7 players)
          </button>
          {error && <p className="error">{error}</p>}
        </div>
      )}

      {gameState && (
        <div className="game">
          {disconnectedCount > 0 && (
            <p className="disconnected-banner">
              Reconnecting to server... any actions you take right now (or updates from the testing panel) won't be
              seen until this reconnects.
            </p>
          )}
          <div className="status-bar">
            <span>Phase {gameState.phase}</span>
            <span>{gameState.round_type === "stock" ? "Stock round" : "Operating round"}</span>
            {gameState.round_type === "stock" ? (
              <span>
                On turn: <strong>{nameFor(gameState.active_player_id)}</strong>
              </span>
            ) : (
              <span>
                Operating: <strong>{activeCompanyId() ?? "-"}</strong> (director:{" "}
                {nameFor(activeCompanyDirector())})
              </span>
            )}
            {inHotseat && seat && (
              <span className="acting-as">Acting as: {seat.name}</span>
            )}
          </div>

          <div className="debug-panel-toggle">
            <button className="debug-toggle-btn" onClick={() => setShowDebugPanel((v) => !v)}>
              {showDebugPanel ? "Hide" : "Show"} testing controls
            </button>
          </div>
          {showDebugPanel && (
            <div className="debug-panel">
              <p className="hint">
                Testing only - jumps straight to a phase/round instead of playing through bidding. Mutates the live
                game for everyone in this room.
              </p>
              <div className="debug-panel-row">
                <label>
                  Phase:{" "}
                  <input
                    type="number"
                    min={1}
                    value={debugPhase}
                    onChange={(e) => setDebugPhase(e.target.value)}
                    style={{ width: 60 }}
                  />
                </label>
                <button
                  disabled={debugBusy || !debugPhase}
                  onClick={() => handleDebugForceRound({ phase: parseInt(debugPhase, 10) })}
                >
                  Set phase
                </button>
              </div>
              <div className="debug-panel-row">
                <select value={debugRoundType} onChange={(e) => setDebugRoundType(e.target.value as "stock" | "operating")}>
                  <option value="operating">Operating round</option>
                  <option value="stock">Stock round</option>
                </select>
                {debugRoundType === "operating" && (
                  <select value={debugCompanyId} onChange={(e) => setDebugCompanyId(e.target.value)}>
                    <option value="">Pick a company...</option>
                    {Object.keys(gameState.minors).map((cid) => (
                      <option key={cid} value={cid}>
                        {cid} (minor)
                      </option>
                    ))}
                    {Object.keys(gameState.majors).map((cid) => (
                      <option key={cid} value={cid}>
                        {cid} (major)
                      </option>
                    ))}
                  </select>
                )}
                <button
                  disabled={debugBusy || (debugRoundType === "operating" && !debugCompanyId)}
                  onClick={() => handleDebugForceRound({ roundType: debugRoundType })}
                >
                  Set round
                </button>
              </div>
              {debugResult && <p className="debug-result">{debugResult}</p>}
              {debugRoundType === "operating" && debugCompanyId && (
                <p className="hint">
                  {homeHexFor(debugCompanyId) ? (
                    <>
                      {debugCompanyId}'s home hex (where its station token goes, and the only legal spot to lay
                      track before it has any) is <strong>{homeHexFor(debugCompanyId)}</strong>.{" "}
                      <button
                        onClick={() => {
                          setActiveTab("map");
                          setMapFocusRequest({ hexId: homeHexFor(debugCompanyId)!, nonce: Date.now() });
                        }}
                      >
                        Jump to it on the map
                      </button>
                    </>
                  ) : (
                    "Home hex not found in the board data."
                  )}
                </p>
              )}
            </div>
          )}

          {gameState.game_over && <p className="game-over">Game over.</p>}
          {error && <p className="error">{error}</p>}

          <div className="tab-bar">
            {(
              [
                ["bid", "Bidding & Concessions"],
                ["stocks", "Trade Stocks"],
                ["map", "Map & Tiles"],
                ["operate", "Operate Trains"],
                ["players", "Players & Log"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                className={`tab-btn${activeTab === key ? " active" : ""}`}
                onClick={() => setActiveTab(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {activeTab === "bid" && (
            <div className="panel">
              <h3>Bid</h3>
              {gameState.round_type !== "stock" && (
                <p className="hint">
                  Not currently a stock round - shown read-only. Bidding boxes are how initial
                  concessions, minors, and privates are auctioned off (rule 4.10).
                </p>
              )}
              {(["concession", "minor", "private"] as const).map((kind) => {
                const boxes =
                  kind === "concession"
                    ? gameState.concession_bid_boxes
                    : kind === "minor"
                    ? gameState.minor_bid_boxes
                    : gameState.private_bid_boxes;
                return (
                  <div key={kind} className="bid-kind">
                    <h4>{kind}</h4>
                    {boxes.map((item, i) =>
                      item ? (
                        <div className="bid-box" key={i}>
                          <span>
                            #{i} {kind === "concession" ? item.ref : `${kind === "minor" ? "M" : "P"}${item.ref}`}
                          </span>
                          <span className="bids">
                            {Object.entries(item.bids)
                              .map(([pid, amt]) => `${nameFor(pid)}: £${amt}`)
                              .join(", ") || "no bids"}
                          </span>
                          <input
                            type="number"
                            step={5}
                            placeholder="amount"
                            disabled={gameState.round_type !== "stock"}
                            value={bidAmounts[`${kind}-${i}`] ?? ""}
                            onChange={(e) =>
                              setBidAmounts({ ...bidAmounts, [`${kind}-${i}`]: e.target.value })
                            }
                          />
                          <button onClick={() => sendBid(kind, i)} disabled={gameState.round_type !== "stock"}>
                            Bid
                          </button>
                        </div>
                      ) : null
                    )}
                  </div>
                );
              })}
              <button onClick={sendPass} className="pass-btn" disabled={gameState.round_type !== "stock"}>
                Pass
              </button>

              <h3>Convert a won concession into a company</h3>
              {gameState.round_type !== "stock" ? (
                <p className="hint">Only available during a stock round.</p>
              ) : (gameState.players[gameState.active_player_id ?? ""]?.concessions ?? []).length === 0 ? (
                <p className="hint">The player on turn holds no unconverted concessions.</p>
              ) : (
                (gameState.players[gameState.active_player_id ?? ""]?.concessions ?? []).map((abbr) => (
                  <div className="bid-box" key={abbr}>
                    <span>{abbr}</span>
                    <input
                      type="number"
                      step={5}
                      placeholder="starting share price"
                      value={convertPrice[abbr] ?? ""}
                      onChange={(e) => setConvertPrice({ ...convertPrice, [abbr]: e.target.value })}
                    />
                    <button onClick={() => sendConvertConcession(abbr)}>Convert & float</button>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "stocks" && (
            <div className="panel">
              <h3>Trade Stocks (major companies)</h3>
              {gameState.round_type !== "stock" && (
                <p className="hint">
                  Buying/selling only happens during a stock round - shown read-only for now.
                </p>
              )}
              <table>
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Floated</th>
                    <th>Price</th>
                    <th>Bank pool</th>
                    <th>Treasury</th>
                    <th>Director</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(gameState.majors).map(([abbr, m]) => (
                    <tr key={abbr}>
                      <td>{abbr}</td>
                      <td>{m.floated ? "yes" : "no"}</td>
                      <td>{m.share_price != null ? `£${m.share_price}` : "-"}</td>
                      <td>{m.shares_in_bank_pool}</td>
                      <td>{m.shares_in_treasury}</td>
                      <td>{nameFor(m.director_player_id)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <h4>Buy a share</h4>
              <div className="bid-box">
                <select value={buyCompanyId} onChange={(e) => setBuyCompanyId(e.target.value)}>
                  <option value="">- pick a company -</option>
                  {Object.entries(gameState.majors)
                    .filter(([, m]) => m.floated)
                    .map(([abbr]) => (
                      <option key={abbr} value={abbr}>
                        {abbr}
                      </option>
                    ))}
                </select>
                <select value={buySource} onChange={(e) => setBuySource(e.target.value as "bank" | "treasury")}>
                  <option value="bank">from bank pool</option>
                  <option value="treasury">from company treasury</option>
                </select>
                <button onClick={sendBuyShare} disabled={gameState.round_type !== "stock"}>
                  Buy
                </button>
              </div>

              <h4>Sell shares (player on turn's holdings)</h4>
              <p className="hint">
                {Object.entries(gameState.players[gameState.active_player_id ?? ""]?.shares ?? {})
                  .filter(([, n]) => n > 0)
                  .map(([abbr, n]) => `${abbr}: ${n}`)
                  .join(", ") || "No shares held."}
              </p>
              <div className="bid-box">
                <select value={sellCompanyId} onChange={(e) => setSellCompanyId(e.target.value)}>
                  <option value="">- pick a company -</option>
                  {Object.entries(gameState.players[gameState.active_player_id ?? ""]?.shares ?? {})
                    .filter(([, n]) => n > 0)
                    .map(([abbr]) => (
                      <option key={abbr} value={abbr}>
                        {abbr}
                      </option>
                    ))}
                </select>
                <input
                  type="number"
                  min={1}
                  value={sellCount}
                  onChange={(e) => setSellCount(e.target.value)}
                  style={{ width: 60 }}
                />
                <button onClick={sendSellShares} disabled={gameState.round_type !== "stock"}>
                  Sell
                </button>
              </div>
            </div>
          )}

          {activeTab === "map" && (
            <MapTab
              roomId={roomId}
              companyKind={mapCompanyIdFor() && /^M\d+$/.test(mapCompanyIdFor()!) ? "minor" : "major"}
              companyId={mapCompanyIdFor()}
              boardTiles={gameState.board?.tiles}
              tilePool={gameState.board?.tile_pool}
              canQueueLay={gameState.round_type === "operating"}
              queuedHexId={includeTileLay ? tileHexId : null}
              onQueueLay={(hexId, tid, rotation) => {
                setTileHexId(hexId);
                setTileId(tid);
                setTileRotation(String(rotation));
                setIncludeTileLay(true);
                setActiveTab("operate");
              }}
              focusRequest={mapFocusRequest}
            />
          )}

          {activeTab === "operate" && (
            <div className="panel">
              <h3>Operate {gameState.round_type === "operating" ? activeCompanyId() : ""}</h3>
              {gameState.round_type !== "operating" ? (
                <p className="hint">Not currently an operating round - shown read-only.</p>
              ) : (
                <p className="hint">
                  Runs first-turn housekeeping, an optional tile lay, checks destination
                  connection (majors), runs owned trains, pays the dividend choice, and an
                  optional train purchase - all as one turn-ending action (rule 5.1-5.14).
                </p>
              )}

              <label className="hint">
                <input
                  type="checkbox"
                  checked={includeTileLay}
                  onChange={(e) => setIncludeTileLay(e.target.checked)}
                />{" "}
                Lay a tile
              </label>
              {includeTileLay && (
                <div className="bid-box">
                  <input
                    placeholder="hex id (e.g. K9)"
                    value={tileHexId}
                    onChange={(e) => setTileHexId(e.target.value)}
                    style={{ width: 100 }}
                  />
                  <input
                    placeholder="tile id (e.g. 9)"
                    value={tileId}
                    onChange={(e) => setTileId(e.target.value)}
                    style={{ width: 90 }}
                  />
                  <input
                    type="number"
                    min={0}
                    max={5}
                    placeholder="rotation 0-5"
                    value={tileRotation}
                    onChange={(e) => setTileRotation(e.target.value)}
                    style={{ width: 100 }}
                  />
                </div>
              )}

              <label>
                Dividend:{" "}
                <select value={dividendChoice} onChange={(e) => setDividendChoice(e.target.value)}>
                  <option value="withhold">Withhold</option>
                  <option value="half">Half</option>
                  <option value="full">Full</option>
                </select>
              </label>

              <div>
                <label className="hint">
                  <input
                    type="checkbox"
                    checked={includeBuyTrain}
                    onChange={(e) => setIncludeBuyTrain(e.target.checked)}
                  />{" "}
                  Buy a train from the bank
                </label>
                {includeBuyTrain && (
                  <select value={buyTrainCode} onChange={(e) => setBuyTrainCode(e.target.value)}>
                    <option value="">- pick a train -</option>
                    {Object.entries(gameState.bank.train_pool)
                      .filter(([, count]) => count > 0)
                      .map(([code, count]) => (
                        <option key={code} value={code}>
                          {code}-train (£, {count} left)
                        </option>
                      ))}
                  </select>
                )}
              </div>

              <div>
                <button onClick={sendOperate} disabled={gameState.round_type !== "operating"}>
                  Operate
                </button>
                <button onClick={sendPass} className="pass-btn" disabled={gameState.round_type !== "operating"}>
                  Pass
                </button>
              </div>
            </div>
          )}

          {activeTab === "players" && (
            <>
              <div className="players-panel">
                <h3>Players</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Cash</th>
                      <th>Loans</th>
                      <th>Shares</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gameState.player_order.map((pid) => (
                      <tr key={pid}>
                        <td>{gameState.players[pid]?.name}</td>
                        <td>£{gameState.players[pid]?.cash}</td>
                        <td>£{gameState.players[pid]?.loans}</td>
                        <td>
                          {Object.entries(gameState.players[pid]?.shares ?? {})
                            .filter(([, n]) => n > 0)
                            .map(([abbr, n]) => `${abbr}:${n}`)
                            .join(", ") || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {gameState.log.length > 0 && (
                <div className="log-panel">
                  <h3>Log</h3>
                  <ul>
                    {gameState.log.slice(-10).map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                </div>
              )}

              <button className="raw-toggle" onClick={() => setShowRaw(!showRaw)}>
                {showRaw ? "Hide" : "Show"} raw state
              </button>
              {showRaw && <pre>{JSON.stringify(gameState, null, 2)}</pre>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
