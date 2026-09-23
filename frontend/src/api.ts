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
  max_tile_color: "yellow" | "green" | "brown" | "gray";
};

export async function fetchTileLayOptions(
  roomId: string,
  hexId: string,
  companyKind: "minor" | "major",
  companyId?: string | null
): Promise<TileLayOptionsResponse> {
  const params: Record<string, string> = { hex_id: hexId, company_kind: companyKind };
  if (companyId) params.company_id = companyId;
  const url = `${API_BASE}/rooms/${roomId}/tile_lay_options?${new URLSearchParams(params)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to load tile lay options");
  return res.json();
}

// Testing/debug only - jumps the live room straight to a given phase and/or
// round (optionally making a specific company operate) without playing
// through the bidding that would normally get there. Mutates state
// directly server-side and broadcasts the result to every connected
// client, same as a real action.
export async function debugForceRound(
  roomId: string,
  opts: { phase?: number; roundType?: "stock" | "operating"; companyId?: string; playerId?: string }
): Promise<{ status: string; phase: number; round_type: string }> {
  const body: Record<string, unknown> = {};
  if (opts.phase !== undefined) body.phase = opts.phase;
  if (opts.roundType !== undefined) body.round_type = opts.roundType;
  if (opts.companyId !== undefined) body.company_id = opts.companyId;
  if (opts.playerId !== undefined) body.player_id = opts.playerId;
  const res = await fetch(`${API_BASE}/rooms/${roomId}/debug/force_round`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to force round");
  return res.json();
}

// Testing/debug only - lays a tile directly onto the board with only the
// connectivity check (rule 5.7.9) enforced against companyId's network.
// Doesn't require an actual operating round, turn, or director, and
// doesn't advance anything - so any number of these can be sent in a row.
export async function debugForceTileLay(
  roomId: string,
  opts: { hexId: string; tileId: string; rotation: number; companyId: string; companyKind: "minor" | "major" }
): Promise<{ status: string; hex_id: string; tile_id: string; rotation: number }> {
  const res = await fetch(`${API_BASE}/rooms/${roomId}/debug/force_tile_lay`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hex_id: opts.hexId,
      tile_id: opts.tileId,
      rotation: opts.rotation,
      company_id: opts.companyId,
      company_kind: opts.companyKind,
    }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to lay tile");
  return res.json();
}
