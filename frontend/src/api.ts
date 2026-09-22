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

export type MapHex = {
  id: string;
  col: number;
  row: number;
  dx: number;
  dy: number;
  confidence: string;
};
export type MapCity = MapHex & {
  name: string;
  label: string | null;
  is_town: boolean;
  home_of_minor: number | null;
  home_of_major: string | null;
  destination_of_major: string | null;
};
export type MapOffboard = MapHex & {
  area_id: string;
  name: string;
  value_yellow: number;
  value_green: number;
  value_brown: number;
  value_grey: number;
};
export type MapTerrain = MapHex & { terrain: string; cost: number };
export type BoardMapData = {
  columns: string[];
  cities: MapCity[];
  offboard: MapOffboard[];
  terrain: MapTerrain[];
};

export async function fetchBoardMap(): Promise<BoardMapData> {
  const res = await fetch(`${API_BASE}/board/map`);
  if (!res.ok) throw new Error("Failed to load board map data");
  return res.json();
}

export type TileLayOption = {
  tile_id: string;
  rotation: number;
  valid: boolean;
  cost: number | null;
  reason: string | null;
};
export type TileLayOptionsResponse = {
  hex_id: string;
  phase: number;
  company_kind: string;
  report: TileLayOption[];
};

export async function fetchTileLayOptions(
  roomId: string,
  hexId: string,
  companyKind: "minor" | "major"
): Promise<TileLayOptionsResponse> {
  const url = `${API_BASE}/rooms/${roomId}/tile_lay_options?${new URLSearchParams({
    hex_id: hexId,
    company_kind: companyKind,
  })}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to load tile lay options");
  return res.json();
}
