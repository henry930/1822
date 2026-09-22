import { useEffect, useRef, useState } from "react";
import { createRoom, joinRoom, startRoom, wsUrl } from "./api";
import "./App.css";

type LobbyMessage = {
  type: "lobby";
  room_id: string;
  players: { player_id: string; name: string; connected: boolean }[];
  started: boolean;
};

// The engine's serialized GameState. Only the fields the UI actually reads
// are named; everything else passes through as unknown for the raw-JSON view.
type BidBoxItem = { kind: string; ref: number | string; bids: Record<string, number> };
type MinorState = { director_player_id: string | null; floated: boolean; treasury: number };
type MajorState = {
  director_player_id: string | null;
  floated: boolean;
  treasury: number;
  share_price: number | null;
};
type EngineState = {
  phase: number;
  round_type: "stock" | "operating";
  active_player_id: string | null;
  player_order: string[];
  players: Record<string, { name: string; cash: number; loans: number }>;
  concession_bid_boxes: (BidBoxItem | null)[];
  minor_bid_boxes: (BidBoxItem | null)[];
  private_bid_boxes: (BidBoxItem | null)[];
  minors: Record<string, MinorState>;
  majors: Record<string, MajorState>;
  operating_order: string[];
  current_company_index: number;
  game_over: boolean;
  log: string[];
  [key: string]: unknown;
};

type StateMessage = {
  type: "state";
  state: EngineState;
  player_id_map: Record<string, string>; // lobby player_id -> engine player_id ("p1".."pN")
};

type ErrorMessage = { type: "error"; message: string };

// One hotseat "seat": a lobby player_id with its own WebSocket connection,
// so the single browser session can act as any of the players in turn.
type Seat = { lobbyPlayerId: string; name: string; ws: WebSocket };

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
  const wsRef = useRef<WebSocket | null>(null);
  // Guards the bot auto-pass effect against re-sending for the same turn
  // (effects can re-run before the resulting state broadcast arrives).
  const lastAutoPassedFor = useRef<string | null>(null);

  // Single-connection mode (normal multiplayer: one browser = one player)
  useEffect(() => {
    if (!roomId || !playerId || seats.length > 0) return;
    const ws = new WebSocket(wsUrl(roomId, playerId));
    ws.onmessage = (evt) => handleMessage(evt.data);
    wsRef.current = ws;
    return () => ws.close();
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
    if (msg.type === "lobby") setLobby(msg);
    if (msg.type === "state") {
      setGameState(msg.state);
      setPlayerIdMap(msg.player_id_map);
    }
    if (msg.type === "error") setError(msg.message);
  }

  async function handleCreate() {
    setError(null);
    try {
      const { room_id } = await createRoom();
      setRoomIdInput(room_id);
      const { player_id } = await joinRoom(room_id, name || "Player");
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
      const names = ["Player 1", "Player 2", "Player 3"];
      const newSeats: Seat[] = [];
      for (const seatName of names) {
        const { player_id } = await joinRoom(room_id, seatName);
        const ws = new WebSocket(wsUrl(room_id, player_id));
        ws.onmessage = (evt) => handleMessage(evt.data);
        newSeats.push({ lobbyPlayerId: player_id, name: seatName, ws });
      }
      setRoomId(room_id);
      setSeats(newSeats);
      await new Promise((r) => setTimeout(r, 200)); // let sockets connect before starting
      await startRoom(room_id);
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

  function sendOperate() {
    const cid = activeCompanyId();
    if (!cid) return;
    send({ type: "operate", company_id: cid, dividend_choice: dividendChoice });
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
          {gameState.game_over && <p className="game-over">Game over.</p>}
          {error && <p className="error">{error}</p>}

          {gameState.round_type === "stock" && (
            <div className="panel">
              <h3>Bid</h3>
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
                            value={bidAmounts[`${kind}-${i}`] ?? ""}
                            onChange={(e) =>
                              setBidAmounts({ ...bidAmounts, [`${kind}-${i}`]: e.target.value })
                            }
                          />
                          <button onClick={() => sendBid(kind, i)}>Bid</button>
                        </div>
                      ) : null
                    )}
                  </div>
                );
              })}
              <button onClick={sendPass} className="pass-btn">
                Pass
              </button>
            </div>
          )}

          {gameState.round_type === "operating" && (
            <div className="panel">
              <h3>Operate {activeCompanyId()}</h3>
              <p className="hint">
                Runs first-turn housekeeping, checks destination, runs any owned trains, and pays
                the dividend choice below. (Tile-laying isn't in this quick UI yet - use the raw
                action JSON via a WebSocket client if you need it.)
              </p>
              <label>
                Dividend:{" "}
                <select value={dividendChoice} onChange={(e) => setDividendChoice(e.target.value)}>
                  <option value="withhold">Withhold</option>
                  <option value="half">Half</option>
                  <option value="full">Full</option>
                </select>
              </label>
              <div>
                <button onClick={sendOperate}>Operate</button>
                <button onClick={sendPass} className="pass-btn">
                  Pass
                </button>
              </div>
            </div>
          )}

          <div className="players-panel">
            <h3>Players</h3>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Cash</th>
                  <th>Loans</th>
                </tr>
              </thead>
              <tbody>
                {gameState.player_order.map((pid) => (
                  <tr key={pid}>
                    <td>{gameState.players[pid]?.name}</td>
                    <td>£{gameState.players[pid]?.cash}</td>
                    <td>£{gameState.players[pid]?.loans}</td>
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
        </div>
      )}
    </div>
  );
}

export default App;
