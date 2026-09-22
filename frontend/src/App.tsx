import { useEffect, useRef, useState } from "react";
import { createRoom, joinRoom, startRoom, wsUrl } from "./api";
import "./App.css";

type LobbyMessage = {
  type: "lobby";
  room_id: string;
  players: { player_id: string; name: string; connected: boolean }[];
  started: boolean;
};

type StateMessage = {
  type: "state";
  state: Record<string, unknown>;
};

function App() {
  const [name, setName] = useState("");
  const [roomIdInput, setRoomIdInput] = useState("");
  const [roomId, setRoomId] = useState<string | null>(null);
  const [playerId, setPlayerId] = useState<string | null>(null);
  const [lobby, setLobby] = useState<LobbyMessage | null>(null);
  const [gameState, setGameState] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!roomId || !playerId) return;
    const ws = new WebSocket(wsUrl(roomId, playerId));
    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data) as LobbyMessage | StateMessage;
      if (msg.type === "lobby") setLobby(msg);
      if (msg.type === "state") setGameState(msg.state);
    };
    wsRef.current = ws;
    return () => ws.close();
  }, [roomId, playerId]);

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

  return (
    <div className="app">
      <h1>1822</h1>
      {!roomId && (
        <div className="join-form">
          <input
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
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
          {error && <p className="error">{error}</p>}
        </div>
      )}

      {roomId && !gameState && (
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
          <p>Game started. Phase {String(gameState.phase)}.</p>
          <pre>{JSON.stringify(gameState, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
