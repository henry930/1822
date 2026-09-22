const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function createRoom(): Promise<{ room_id: string }> {
  const res = await fetch(`${API_BASE}/rooms`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create room");
  return res.json();
}

export async function joinRoom(
  roomId: string,
  name: string
): Promise<{ player_id: string; room_id: string }> {
  const res = await fetch(`${API_BASE}/rooms/${roomId}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to join room");
  return res.json();
}

export async function startRoom(roomId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/rooms/${roomId}/start`, { method: "POST" });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to start room");
}

export function wsUrl(roomId: string, playerId: string): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/ws/${roomId}/${playerId}`;
}
