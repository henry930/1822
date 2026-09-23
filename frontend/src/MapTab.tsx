import { useEffect, useMemo, useRef, useState } from "react";
import {
  debugForceTileLay,
  debugRemoveTile,
  deleteRegionCorrectionFromServer,
  fetchBoardMap,
  fetchRegionCorrections,
  fetchTileLayOptions,
  saveRegionCorrectionToServer,
  type BoardMapData,
  type MapCity,
  type MapOffboard,
  type MapTerrain,
  type TileLayOption,
} from "./api";
import manifestUrl from "./assets/tiles/manifest.json?url";
import boardImageUrl from "./assets/map/board.jpg";

type TileManifestEntry = {
  id: string;
  color: "yellow" | "green" | "brown" | "gray";
  count: number | "unlimited";
  label: string | null;
  file: string;
};

// path -> url for every tile SVG, resolved at build time by Vite.
const TILE_SVG_URLS = import.meta.glob("./assets/tiles/tile_*.svg", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

function tileUrl(file: string): string | undefined {
  return TILE_SVG_URLS[`./assets/tiles/${file}`];
}

const SIZE = 40; // hex "radius" (center to vertex) in px, schematic view only
const COL_SPACING = SIZE * 1.5;
const ROW_SPACING = SIZE * Math.sqrt(3);

function hexCenter(col: number, row: number, dx: number, dy: number) {
  const x = col * COL_SPACING;
  const y = row * ROW_SPACING + (col % 2 === 1 ? ROW_SPACING / 2 : 0);
  return { x: x + dx * COL_SPACING * 0.5, y: y + dy * ROW_SPACING * 0.5 };
}

// Calibration for the real board scan (board.jpg, 1700x2200 - see
// assets/map/README.md for how these were measured). The board's printed
// row numbers turned out to increment by 1 per HALF a physical hex-row
// (odd columns only ever carry odd row numbers, even columns only ever
// carry even ones - confirmed against 26/28 rules-confidence catalogued
// hexes), so a hex's pixel position is a *plain* linear map of its raw
// (col, row) - no extra odd/even column offset term needed, unlike the
// schematic view above which treats "row" as a per-column sequential index.
const PHOTO_X0 = 222.0;
const PHOTO_DX = 78.05; // px per column-letter step
const PHOTO_Y0 = 92.1;
const PHOTO_DY = 45.23; // px per printed row-number unit
const PHOTO_HEX_SIZE = 52; // center-to-vertex, tessellates with PHOTO_DX/DY above
const PHOTO_IMAGE_W = 1700;
const PHOTO_IMAGE_H = 2200;
const PHOTO_MAX_ROW = 43;

function photoHexCenter(col: number, row: number) {
  return { x: PHOTO_X0 + col * PHOTO_DX, y: PHOTO_Y0 + row * PHOTO_DY };
}

// Parses a hex id like "H23" into (col, row) the same way the systematic
// grid below does, for a hex that isn't necessarily part of it.
function parseHexId(hexId: string, columns: string[]): { col: number; row: number } | null {
  const m = /^([A-Za-z]{1,2})(\d{1,2})$/.exec(hexId);
  if (!m) return null;
  const col = columns.indexOf(m[1].toUpperCase());
  if (col === -1) return null;
  return { col, row: parseInt(m[2], 10) };
}

// Every tile SVG draws its hexagon inset within a square viewBox (a small
// margin around the hex for the stroke/labels) - the hex itself only spans
// 200 of the viewBox's 230 units. Scale placed-tile <image> elements up by
// this factor so the drawn hexagon fills the actual hex region instead of
// rendering visibly smaller than it with a gap around the edges.
const TILE_ART_SCALE = 230 / 200;

const TILE_COLOR_ORDER = ["yellow", "green", "brown", "gray"] as const;

function hexPoints(cx: number, cy: number, size: number): string {
  // Flat-top hex, matching the tile SVGs' own orientation.
  const pts = [
    [cx - size * 0.5, cy - size * 0.866],
    [cx + size * 0.5, cy - size * 0.866],
    [cx + size, cy],
    [cx + size * 0.5, cy + size * 0.866],
    [cx - size * 0.5, cy + size * 0.866],
    [cx - size, cy],
  ];
  return pts.map((p) => p.join(",")).join(" ");
}

type PlacedTile = { tile_id: string; rotation: number };
type HexEntry = { hex: MapCity | MapOffboard | MapTerrain; kind: "city" | "offboard" | "terrain" };

// --- Region data cross-check panel -----------------------------------------
// Lets a player who has the physical board in front of them correct/confirm
// what this engine has on file for a hex, one click at a time, without
// needing to touch code. Saved locally (so nothing is lost on refresh) and
// exportable as JSON to hand back for merging into app/data/hex_map.py -
// this UI doesn't write to the server, it just collects and hands off.
//
// A hex isn't necessarily just one "kind": Aberdeen/H1 and Glasgow/E6 are
// both a city (home of a minor) AND an off-board revenue area at once, so
// city/town and off-board/terrain are tracked as independent, combinable
// fields here rather than one mutually-exclusive "kind" - see
// app.data.hex_map.CityHex's docstring on the backend for the same point.
const REGION_CORRECTIONS_KEY = "1822-map-region-corrections-v1";

type CityOrTown = "" | "city" | "town";
// "normal" - track genuinely connects across this edge, ordinary case.
// "blocked" - the board explicitly marks this edge as never connecting
//   (e.g. a red coastal-break line) even though the two hexes sit right
//   next to each other and both carry track elsewhere.
// "toll" - connects, but costs money to build across.
// "empty" - there's simply no track connection here at all (open sea, off
//   the printed board, or otherwise not track territory) - not a
//   documented "blocked" rule, just nothing to connect. Functionally the
//   same as "blocked" for routing, recorded separately so the reason why
//   isn't lost when this gets merged back into the real map data.
type EdgeStatus = "normal" | "blocked" | "toll" | "empty";
type EdgeCorrection = { status: EdgeStatus; cost: string };

type RegionForm = {
  cityOrTown: CityOrTown;
  name: string;
  label: string;
  // Only meaningful when cityOrTown === "town" - some yellow tiles
  // (1/2/55/56/69) print two town circles on one hex.
  townCount: string;
  // Only meaningful when cityOrTown === "city" - almost always 1; London
  // is a six-city super-hex (its tiles print six separate city circles).
  cityCount: string;
  homeOfMajor: string;
  homeOfMinor: string;
  destinationOfMajor: string;
  isOffboard: boolean;
  offboardName: string;
  valueYellow: string;
  valueGreen: string;
  valueBrown: string;
  valueGrey: string;
  isTerrain: boolean;
  terrain: string;
  cost: string;
  // Per-edge (0=N,1=NE,2=SE,3=S,4=SW,5=NW) corrections - which neighboring
  // regions this hex does/doesn't connect to, and any toll to cross. Only
  // edges the player actually sets are stored; an edge absent here is left
  // as whatever's already on file, or defaults to "empty" (not yet
  // checked/nothing there) in the form itself - see the "Edges" section
  // below, deliberately not "normal", since most edges genuinely are
  // empty and this saves having to touch every one just to leave it alone.
  edges: Partial<Record<number, EdgeCorrection>>;
  note: string;
};

type SavedRegionCorrection = RegionForm & { hexId: string; savedAt: string };

const BLANK_REGION_FORM: RegionForm = {
  cityOrTown: "",
  name: "",
  label: "",
  townCount: "1",
  cityCount: "1",
  homeOfMajor: "",
  homeOfMinor: "",
  destinationOfMajor: "",
  isOffboard: false,
  offboardName: "",
  valueYellow: "",
  valueGreen: "",
  valueBrown: "",
  valueGrey: "",
  isTerrain: false,
  terrain: "",
  cost: "",
  edges: {},
  note: "",
};

const LABEL_OPTIONS = ["BM", "Y", "C", "EC", "L", "S", "T"];
const TERRAIN_OPTIONS = ["river_small", "river_large", "estuary", "rough", "hill", "mountain"];

// Edge numbering matches the backend (app.engine.hex_grid): 0=N, 1=NE,
// 2=SE, 3=S, 4=SW, 5=NW - a tile's printed edges line up with these directly.
const EDGE_DIRECTIONS: { edge: number; short: string; full: string }[] = [
  { edge: 0, short: "N", full: "North" },
  { edge: 1, short: "NE", full: "North-east" },
  { edge: 2, short: "SE", full: "South-east" },
  { edge: 3, short: "S", full: "South" },
  { edge: 4, short: "SW", full: "South-west" },
  { edge: 5, short: "NW", full: "North-west" },
];

// JS port of app.engine.hex_grid's neighbor math (flat-top hexes, "odd-q"
// column offset) - kept in sync deliberately with the same coordinate
// convention so a direction picked here always names the same real
// neighbor hex the backend would compute for a tile lay there.
const EVEN_COL_DELTAS: [number, number][] = [[0, -1], [1, -1], [1, 0], [0, 1], [-1, 0], [-1, -1]];
const ODD_COL_DELTAS: [number, number][] = [[0, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0]];
const GRID_MIN_ROW = 1;
const GRID_MAX_ROW = 44;

function neighborHexId(columns: string[], col: number, row: number, edge: number): string | null {
  const deltas = col % 2 === 1 ? ODD_COL_DELTAS : EVEN_COL_DELTAS;
  const [dCol, dRow] = deltas[edge];
  const nCol = col + dCol;
  const nRow = row + dRow;
  if (nCol < 0 || nCol >= columns.length || nRow < GRID_MIN_ROW || nRow > GRID_MAX_ROW) return null;
  return `${columns[nCol]}${nRow}`;
}

// Fills in any field missing from a stored correction with its blank
// default - guards against a correction saved by an older version of this
// form (e.g. from before `edges` or `cityCount` existed) crashing the page
// the instant it's loaded back in, since every field here is read
// unconditionally elsewhere (regionForm.edges[edge] etc.) rather than with
// optional chaining every time.
function normalizeRegionCorrection(raw: Partial<SavedRegionCorrection>, hexId: string): SavedRegionCorrection {
  return {
    ...BLANK_REGION_FORM,
    ...raw,
    edges: raw.edges ?? {},
    hexId: raw.hexId ?? hexId,
    savedAt: raw.savedAt ?? new Date(0).toISOString(),
  };
}

function loadRegionCorrections(): Record<string, SavedRegionCorrection> {
  try {
    const raw = localStorage.getItem(REGION_CORRECTIONS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, Partial<SavedRegionCorrection>>;
    const result: Record<string, SavedRegionCorrection> = {};
    for (const [hexId, entry] of Object.entries(parsed)) {
      result[hexId] = normalizeRegionCorrection(entry ?? {}, hexId);
    }
    return result;
  } catch {
    return {};
  }
}

function persistRegionCorrections(corrections: Record<string, SavedRegionCorrection>) {
  try {
    localStorage.setItem(REGION_CORRECTIONS_KEY, JSON.stringify(corrections));
  } catch {
    // private browsing / quota exceeded - the in-memory state for this
    // session still works, it just won't survive a refresh.
  }
}

// Pre-fills the form from whatever this engine already has catalogued for
// the hex (possibly several entries at once - see the comment above), so
// "correcting" it is edit-in-place, not re-typing from scratch. Edge data
// is filled in separately (see the reset effect) since it depends on the
// hex's neighbors, not on its own catalogue entries.
function regionFormFromCatalogued(entries: HexEntry[]): Omit<RegionForm, "edges"> {
  const form = { ...BLANK_REGION_FORM };
  for (const entry of entries) {
    if (entry.kind === "city") {
      const c = entry.hex as MapCity;
      form.cityOrTown = c.is_town ? "town" : "city";
      form.name = c.name;
      form.label = c.label ?? "";
      form.townCount = String(c.town_count || 1);
      form.cityCount = String(c.city_count || 1);
      form.homeOfMajor = c.home_of_major.join(", ");
      form.homeOfMinor = c.home_of_minor.join(", ");
      form.destinationOfMajor = c.destination_of_major ?? "";
    } else if (entry.kind === "offboard") {
      const o = entry.hex as MapOffboard;
      form.isOffboard = true;
      form.offboardName = o.name;
      form.valueYellow = String(o.value_yellow);
      form.valueGreen = String(o.value_green);
      form.valueBrown = String(o.value_brown);
      form.valueGrey = String(o.value_grey);
    } else if (entry.kind === "terrain") {
      const t = entry.hex as MapTerrain;
      form.isTerrain = true;
      form.terrain = t.terrain;
      form.cost = String(t.cost);
    }
  }
  return form;
}

type Props = {
  roomId: string | null;
  companyKind: "minor" | "major";
  companyId: string | null;
  boardTiles: Record<string, PlacedTile> | undefined;
  // null in a tile's entry means unlimited supply (see new_board_state).
  tilePool: Record<string, number | null> | undefined;
  canQueueLay: boolean;
  onQueueLay: (hexId: string, tileId: string, rotation: number) => void;
  queuedHexId: string | null;
  // Bump the nonce (any change - a new object is enough) to make the map
  // jump to and open hexId, e.g. "show me this company's home hex" from
  // outside this tab. A plain hexId prop wouldn't re-trigger for the same
  // hex picked twice in a row.
  focusRequest?: { hexId: string; nonce: number } | null;
};

export default function MapTab({
  roomId,
  companyKind,
  companyId,
  boardTiles,
  tilePool,
  canQueueLay,
  onQueueLay,
  queuedHexId,
  focusRequest,
}: Props) {
  const [mapData, setMapData] = useState<BoardMapData | null>(null);
  const [manifest, setManifest] = useState<TileManifestEntry[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedHexId, setSelectedHexId] = useState<string | null>(null);
  // An armed-but-unconfirmed placement: picking a tile from the modal sets
  // this (closing the modal) instead of placing anything, and it's what's
  // actually drawn live on the map at that hex - rotation and confirm/
  // cancel all act on this, not on any real game state, until Enter sends
  // it for real.
  const [pendingPlacement, setPendingPlacement] = useState<{ hexId: string; tileId: string; rotation: number } | null>(
    null
  );
  const [viewMode, setViewMode] = useState<"photo" | "schematic">("photo");
  const [placeConfirmed, setPlaceConfirmed] = useState<string | null>(null);
  const [placeError, setPlaceError] = useState<string | null>(null);
  const [placing, setPlacing] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [report, setReport] = useState<TileLayOption[] | null>(null);
  const [maxTileColor, setMaxTileColor] = useState<"yellow" | "green" | "brown" | "gray">("yellow");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [regionCorrections, setRegionCorrections] = useState<Record<string, SavedRegionCorrection>>(
    loadRegionCorrections
  );
  const [regionForm, setRegionForm] = useState<RegionForm>({ ...BLANK_REGION_FORM });
  const [regionSaved, setRegionSaved] = useState(false);
  const [regionCopied, setRegionCopied] = useState(false);

  // What's actually drawn on the map: real server state, with the pending
  // (unconfirmed) placement overlaid on top of its hex so rotating it is
  // visible immediately, before Enter ever sends anything.
  const effectiveBoardTiles = pendingPlacement
    ? { ...boardTiles, [pendingPlacement.hexId]: { tile_id: pendingPlacement.tileId, rotation: pendingPlacement.rotation } }
    : boardTiles;

  useEffect(() => {
    fetchBoardMap()
      .then(setMapData)
      .catch((e) => setLoadError((e as Error).message));
    fetch(manifestUrl)
      .then((r) => r.json())
      .then(setManifest)
      .catch((e) => setLoadError((e as Error).message));
  }, []);

  // Region corrections now live server-side (app.db) - previously only in
  // this browser's localStorage. On mount: pull the server's copy in as
  // the authoritative version for any hex it has, and push up anything
  // that only exists locally (saved before this session ever talked to
  // the server, or while offline) so the two converge. If the server is
  // unreachable (or predates this endpoint), this silently falls back to
  // working off localStorage alone, same as before.
  useEffect(() => {
    const localOnly = regionCorrections;
    fetchRegionCorrections()
      .then((serverCorrections) => {
        setRegionCorrections((prev) => {
          const merged: Record<string, SavedRegionCorrection> = { ...prev };
          for (const [hexId, raw] of Object.entries(serverCorrections)) {
            merged[hexId] = normalizeRegionCorrection(raw as Partial<SavedRegionCorrection>, hexId);
          }
          persistRegionCorrections(merged);
          return merged;
        });
        for (const [hexId, correction] of Object.entries(localOnly)) {
          if (!(hexId in serverCorrections)) {
            saveRegionCorrectionToServer(hexId, correction).catch(() => {});
          }
        }
      })
      .catch(() => {
        // Server unreachable - keep working off localStorage alone.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Every (tile, rotation) combination's legality for the selected hex right
  // now, fetched once per hex/room/company-kind change - re-derived from the
  // real engine validator server-side, so it can never drift out of sync
  // with what actually happens when Operate is clicked.
  //
  // Real bug found here: placing a tile that ends the operating round (e.g.
  // the only company in that OR set) flips App.tsx's `companyKind` prop
  // (minor -> major, since "operating" is no longer true) the instant the
  // placement succeeds. That's a dependency of this effect, so it fired
  // again right on the success render and reset pendingTileId to null -
  // collapsing the whole tile-picker UI (Place button, rotation picker, the
  // just-earned confirmation message) at the exact moment of success. From
  // the user's side that looked exactly like "the Place button doesn't
  // work". Guard against it: don't wipe the picker while a placement is
  // in flight or was just confirmed - the modal auto-closes shortly after
  // a confirmed placement anyway, so there's nothing useful to refetch for.
  function loadReportFor(hexId: string) {
    setReport(null);
    setReportError(null);
    if (!roomId) return;
    setReportLoading(true);
    // Always pass companyId when known - connectivity (rule 5.7.9) no
    // longer requires a real operating round to check (see
    // confirmPendingPlacement/debug_force_tile_lay), so gating this on
    // canQueueLay would leave the picker blind to it whenever a company was
    // only picked via the testing panel rather than a genuine operating turn.
    fetchTileLayOptions(roomId, hexId, companyKind, companyId)
      .then((r) => {
        setReport(r.report);
        setMaxTileColor(r.max_tile_color);
      })
      .catch((e) => setReportError((e as Error).message))
      .finally(() => setReportLoading(false));
  }

  // Real bug #2, found from the same root cause: guarding on `placing` /
  // `placeConfirmed` alone (checked above) blocked this effect for that one
  // render, but a state setter called *inside* an effect doesn't retroactively
  // change what other effects in that same commit already read - so this
  // effect's own closure still saw the stale (pre-reset) placeConfirmed value
  // too, and skipped fetching. Selecting any *other* hex afterwards still hit
  // this same effect (same guard, same stale closure risk) and could skip
  // fetching for hexes that were never involved in a placement at all -
  // leaving the picker permanently empty and the Place button permanently
  // disabled after the first successful placement. Fixed by keying the skip
  // to whether the hex/room actually changed (tracked via a ref, which -
  // unlike state - reads the value set just now, not last render's): only
  // skip when they *didn't* change (this is our own placement's companyKind
  // flip), never for an actual hex switch.
  const lastFetchKeyRef = useRef<string | null>(null);
  useEffect(() => {
    const key = `${selectedHexId ?? ""}|${roomId ?? ""}`;
    const hexOrRoomChanged = key !== lastFetchKeyRef.current;
    lastFetchKeyRef.current = key;

    if (!hexOrRoomChanged && (placing || placeConfirmed)) return;
    if (!selectedHexId) {
      setReport(null);
      setReportError(null);
      return;
    }
    loadReportFor(selectedHexId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHexId, roomId, companyKind, companyId, canQueueLay]);

  useEffect(() => {
    setPlaceConfirmed(null);
    setPlaceError(null);
    setPlacing(false);
    setPendingPlacement(null);
  }, [selectedHexId]);

  useEffect(() => {
    if (!placeConfirmed) return;
    const timeout = setTimeout(() => setModalOpen(false), 1200);
    return () => clearTimeout(timeout);
  }, [placeConfirmed]);

  function selectHex(hexId: string) {
    setSelectedHexId(hexId);
    setModalOpen(true);
  }

  useEffect(() => {
    if (!focusRequest) return;
    selectHex(focusRequest.hexId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusRequest]);

  // rule 5.7.9: the backend short-circuits every combo to the same
  // "isn't connected" reason when the hex is unreachable at all (see
  // tile_lay_report's connected=False path in board.py), so that's
  // detectable purely from the already-fetched report without a separate
  // request at confirm time.
  function isDisconnected(): boolean {
    if (!report || report.length === 0) return false;
    return report.every((r) => !r.valid && (r.reason?.includes("isn't connected") ?? false));
  }

  // null means unlimited (see new_board_state). Laying the tile already
  // sitting on the target hex back onto itself (e.g. just rotating it)
  // doesn't need a spare copy - the server returns the old one to the
  // pool before drawing a new one - so that case reads as +1 available,
  // matching the same relaying_same_tile logic server-side.
  function remainingSupply(tileId: string, hexId: string | null): number | null {
    const remaining = tilePool?.[tileId];
    if (remaining === undefined || remaining === null) return null;
    const relayingSameTile = hexId != null && boardTiles?.[hexId]?.tile_id === tileId;
    return relayingSameTile ? remaining + 1 : remaining;
  }

  // Lays the tile directly (debugForceTileLay) rather than going through a
  // real operate turn - no company-turn/director requirement, and no
  // round to end, so this never blocks a second placement right after the
  // first the way a real operate action would. Connectivity (rule 5.7.9)
  // and tile supply are checked once here against already-fetched data for
  // an instant "Invalid move"; every rule (those two plus phase/color,
  // city-town match, upgrade-must-preserve-track, and terrain cost vs.
  // treasury) is enforced again server-side as the real gate.
  async function confirmPendingPlacement() {
    const p = pendingPlacement;
    if (!p || placing) return;
    if (reportLoading) return;
    if (isDisconnected()) {
      window.alert("Invalid move");
      return;
    }
    const remaining = remainingSupply(p.tileId, p.hexId);
    if (remaining !== null && remaining <= 0) {
      window.alert("Invalid move");
      return;
    }
    if (!roomId) {
      setPlaceError("No room - start a game first.");
      return;
    }
    setPlaceConfirmed(null);
    setPlaceError(null);
    setPlacing(true);
    try {
      await debugForceTileLay(roomId, {
        hexId: p.hexId,
        tileId: p.tileId,
        rotation: p.rotation,
        companyId,
        companyKind,
      });
      setPlaceConfirmed(`Placed tile ${p.tileId} (rotation ${p.rotation}) on ${p.hexId}.`);
      setPendingPlacement(null);
    } catch (e) {
      const msg = (e as Error).message;
      if (msg.toLowerCase().includes("room not found") || msg.toLowerCase().includes("game has not started")) {
        setPlaceError(msg);
      } else {
        // Every other rejection is a tile-lay rule the server enforced
        // (connectivity, supply, phase/color, city-town match, upgrade
        // preservation, or treasury) - surface it as the spec'd alert.
        window.alert(`Invalid move: ${msg}`);
      }
    } finally {
      setPlacing(false);
    }
  }

  // Testing only - not a real game action (rule 5.7.16 says track is never
  // removed once laid). Lets a hex be tried out repeatedly during UI
  // testing without restarting the whole room every time.
  async function removeSelectedTile() {
    if (!roomId || !selectedHexId || removing) return;
    setPlaceConfirmed(null);
    setPlaceError(null);
    setRemoving(true);
    try {
      await debugRemoveTile(roomId, selectedHexId);
      setPlaceConfirmed(`Removed the tile on ${selectedHexId}.`);
    } catch (e) {
      setPlaceError((e as Error).message);
    } finally {
      setRemoving(false);
    }
  }

  // Left/Right rotate, Enter confirms (sends the real placement and checks
  // connectivity - rule 5.7.9 - first), Esc cancels. Re-subscribes on every
  // rotation change so the closures here (report, placing) never go stale.
  useEffect(() => {
    if (!pendingPlacement) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setPendingPlacement((p) => (p ? { ...p, rotation: (p.rotation + 5) % 6 } : p));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setPendingPlacement((p) => (p ? { ...p, rotation: (p.rotation + 1) % 6 } : p));
      } else if (e.key === "Enter") {
        e.preventDefault();
        confirmPendingPlacement();
      } else if (e.key === "Escape") {
        e.preventDefault();
        setPendingPlacement(null);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingPlacement, report, reportLoading, placing]);

  // Esc also closes the tile-picker modal itself (the "Choose a tile to
  // place here..." popup) when it's open with nothing armed yet - the
  // pendingPlacement case above already handles Esc once a tile's picked.
  useEffect(() => {
    if (!modalOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        setModalOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [modalOpen]);

  const allHexes: HexEntry[] = useMemo(() => {
    if (!mapData) return [];
    const list: HexEntry[] = [];
    for (const c of mapData.cities) list.push({ hex: c, kind: "city" });
    for (const o of mapData.offboard) list.push({ hex: o, kind: "offboard" });
    for (const t of mapData.terrain) list.push({ hex: t, kind: "terrain" });
    return list;
  }, [mapData]);

  // A hex can carry more than one catalogue entry at once (city + off-board
  // area - see the region-data-panel comment above), so this maps to a list,
  // not a single entry.
  const hexEntriesById = useMemo(() => {
    const map = new Map<string, HexEntry[]>();
    for (const entry of allHexes) {
      const list = map.get(entry.hex.id);
      if (list) list.push(entry);
      else map.set(entry.hex.id, [entry]);
    }
    return map;
  }, [allHexes]);

  // What's currently on file for a hex's 6 edges, read from the board map's
  // blocked_adjacencies/edge_tolls lists - used to pre-fill the edge
  // corrections form the same way regionFormFromCatalogued pre-fills the
  // rest of it.
  function edgesFromCatalogued(hexId: string): Partial<Record<number, EdgeCorrection>> {
    if (!mapData) return {};
    const parsed = parseHexId(hexId, mapData.columns);
    if (!parsed) return {};
    // Defensive against an older/cached /board/map response that predates
    // these two fields - without this, a stale server would throw on
    // `.find` of undefined the instant any hex was selected, crashing the
    // whole tab to a blank page instead of just leaving edges unannotated.
    const blockedAdjacencies = mapData.blocked_adjacencies ?? [];
    const edgeTolls = mapData.edge_tolls ?? [];
    const result: Partial<Record<number, EdgeCorrection>> = {};
    for (const { edge } of EDGE_DIRECTIONS) {
      const neighborId = neighborHexId(mapData.columns, parsed.col, parsed.row, edge);
      if (!neighborId) continue;
      const blocked = blockedAdjacencies.find(
        (b) => (b.hex_a === hexId && b.hex_b === neighborId) || (b.hex_a === neighborId && b.hex_b === hexId)
      );
      if (blocked) {
        result[edge] = { status: "blocked", cost: "" };
        continue;
      }
      const toll = edgeTolls.find(
        (t) => (t.hex_a === hexId && t.hex_b === neighborId) || (t.hex_a === neighborId && t.hex_b === hexId)
      );
      if (toll) result[edge] = { status: "toll", cost: String(toll.cost) };
    }
    return result;
  }

  // Reset the correction form whenever the selected hex changes: an already
  // -saved correction for this hex wins (that's the player's own latest
  // word on it), otherwise pre-fill from whatever's catalogued so far, or a
  // blank form for a hex this engine doesn't know about at all yet.
  useEffect(() => {
    setRegionSaved(false);
    if (!selectedHexId) {
      setRegionForm({ ...BLANK_REGION_FORM });
      return;
    }
    const existing = regionCorrections[selectedHexId];
    if (existing) {
      setRegionForm({ ...existing });
    } else {
      setRegionForm({
        ...regionFormFromCatalogued(hexEntriesById.get(selectedHexId) ?? []),
        edges: edgesFromCatalogued(selectedHexId),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHexId, hexEntriesById]);

  function saveRegionCorrection() {
    if (!selectedHexId) return;
    const entry: SavedRegionCorrection = { ...regionForm, hexId: selectedHexId, savedAt: new Date().toISOString() };
    setRegionCorrections((prev) => {
      const next = { ...prev, [selectedHexId]: entry };
      persistRegionCorrections(next);
      return next;
    });
    setRegionSaved(true);
    // Best-effort - localStorage above already made this durable client-
    // side even if the server request fails (offline, server down); the
    // mount-time sync effect will retry pushing it up on the next load.
    saveRegionCorrectionToServer(selectedHexId, entry).catch(() => {});
  }

  function discardRegionCorrection(hexId: string) {
    setRegionCorrections((prev) => {
      const next = { ...prev };
      delete next[hexId];
      persistRegionCorrections(next);
      return next;
    });
    if (hexId === selectedHexId) {
      setRegionForm({
        ...regionFormFromCatalogued(hexEntriesById.get(hexId) ?? []),
        edges: edgesFromCatalogued(hexId),
      });
      setRegionSaved(false);
    }
    deleteRegionCorrectionFromServer(hexId).catch(() => {});
  }

  function downloadRegionCorrections() {
    const blob = new Blob([JSON.stringify(regionCorrections, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "1822-map-corrections.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function copyRegionCorrections() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(regionCorrections, null, 2));
      setRegionCopied(true);
      setTimeout(() => setRegionCopied(false), 1500);
    } catch {
      // Clipboard API unavailable (e.g. insecure context) - Download still works.
    }
  }

  // Every clickable hex region on the real board scan: the printed board is
  // a full rectangular hex grid (sea hexes included, just colored blue), and
  // - per the calibration note above - a real hex only ever exists where the
  // column index and row number share the same parity. This is what makes
  // the photo view show "different hexagon regions" directly on the art,
  // not just the ~120 named/catalogued ones.
  const photoGrid = useMemo(() => {
    if (!mapData) return [];
    const list: { hexId: string; col: number; row: number }[] = [];
    const seen = new Set<string>();
    for (let col = 0; col < mapData.columns.length; col++) {
      for (let row = 1; row <= PHOTO_MAX_ROW; row++) {
        if (col % 2 === row % 2) {
          const hexId = `${mapData.columns[col]}${row}`;
          list.push({ hexId, col, row });
          seen.add(hexId);
        }
      }
    }
    // A hex that's actually got a tile on it (or is mid-placement) always
    // needs to be drawn, even if it falls on the "wrong" parity for the
    // systematic grid above - that grid is a best-effort approximation of
    // which positions exist on the real printed board, and a hex id typed
    // into search or reached some other way isn't guaranteed to land on
    // one of those positions, but a real placement on it is still real
    // game state that has to be visible.
    for (const hexId of Object.keys(effectiveBoardTiles ?? {})) {
      if (seen.has(hexId)) continue;
      const parsed = parseHexId(hexId, mapData.columns);
      if (parsed) {
        list.push({ hexId, ...parsed });
        seen.add(hexId);
      }
    }
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapData, effectiveBoardTiles]);

  const bounds = useMemo(() => {
    if (allHexes.length === 0) return { minX: 0, minY: 0, maxX: 800, maxY: 600 };
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const { hex } of allHexes) {
      const { x, y } = hexCenter(hex.col, hex.row, hex.dx, hex.dy);
      minX = Math.min(minX, x - SIZE);
      minY = Math.min(minY, y - SIZE);
      maxX = Math.max(maxX, x + SIZE);
      maxY = Math.max(maxY, y + SIZE);
    }
    return { minX: minX - 10, minY: minY - 10, maxX: maxX + 10, maxY: maxY + 10 };
  }, [allHexes]);

  const searchResults = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [];
    const fromCatalog = allHexes.filter(({ hex }) => {
      const name = "name" in hex ? (hex as MapCity | MapOffboard).name.toLowerCase() : "";
      return hex.id.toLowerCase().includes(q) || name.includes(q);
    });
    const results: { id: string; label: string }[] = fromCatalog.map(({ hex, kind }) => ({
      id: hex.id,
      label: `${hex.id} - ${"name" in hex ? (hex as MapCity | MapOffboard).name : kind}`,
    }));
    // Allow typing a raw hex id (e.g. "K20") that isn't in the catalogued
    // ~120 named hexes - most of the board's several hundred hexes aren't
    // catalogued, but the tile-lay validator works for any hex id.
    const rawMatch = /^[A-Qa-q]{1,2}\d{1,2}$/.test(search.trim());
    if (rawMatch && !results.some((r) => r.id.toLowerCase() === search.trim().toLowerCase())) {
      const id = search.trim().toUpperCase();
      results.unshift({ id, label: `${id} (uncatalogued hex)` });
    }
    return results.slice(0, 20);
  }, [allHexes, search]);

  const selectedEntries = selectedHexId ? hexEntriesById.get(selectedHexId) ?? [] : [];
  // A single representative entry for the places this still shows one
  // thing (the modal/panel title) - prefers the city entry when a hex is
  // both a city and an off-board area, since the city name is the more
  // recognizable one.
  const selectedInfo = selectedEntries.find((e) => e.kind === "city") ?? selectedEntries[0];
  const selectedPlacedTile = selectedHexId ? effectiveBoardTiles?.[selectedHexId] : undefined;

  const colorFor = (kind: "city" | "offboard" | "terrain", hex: MapCity | MapOffboard | MapTerrain) => {
    if (kind === "city") return (hex as MapCity).is_town ? "#dbe4ee" : "#8fb8e0";
    if (kind === "offboard") return "#8a8a8a";
    const terrain = (hex as MapTerrain).terrain;
    if (terrain === "mountain") return "#6b4f3a";
    if (terrain === "hill") return "#9c7a52";
    return "#6fa8a0"; // river/estuary/rough
  };

  const grouped: Record<string, TileManifestEntry[]> = { yellow: [], green: [], brown: [], gray: [] };
  for (const t of manifest) grouped[t.color]?.push(t);

  // "Tiles laid so far" is real, confirmed board state only - the pending
  // (unconfirmed) placement doesn't belong in that list even though it's
  // drawn on the map.
  const placedList = Object.entries(boardTiles ?? {});

  // Picking a tile arms it at rotation 0 and closes the modal - rotation
  // and confirm/cancel all happen afterwards via the keyboard, directly on
  // the map (see the keydown effect above).
  function pickTile(tileId: string) {
    if (!selectedHexId) return;
    setModalOpen(false);
    setPendingPlacement({ hexId: selectedHexId, tileId, rotation: 0 });
  }

  return (
    <div className="panel map-panel">
      <h3>Map & Tile Placement</h3>
      <p className="hint">
        The board on the left is the actual scanned 1822 map (map.pdf) with a clickable hex grid
        overlaid on it - click any hexagon region directly on the map (or search by id/city name
        below it) to select it, then pick a tile for the current phase. The tile then sits on
        that hex, unconfirmed: <strong>← / →</strong> rotates it, <strong>Enter</strong> confirms
        (checked against the real connectivity rule - an unreachable hex pops up "Invalid move"),
        and <strong>Esc</strong> cancels.
      </p>
      {loadError && <p className="error">{loadError}</p>}

      <div className="map-view-toggle">
        <button
          className={`tab-btn${viewMode === "photo" ? " active" : ""}`}
          onClick={() => setViewMode("photo")}
        >
          Real board scan
        </button>
        <button
          className={`tab-btn${viewMode === "schematic" ? " active" : ""}`}
          onClick={() => setViewMode("schematic")}
        >
          Clickable schematic
        </button>
      </div>

      <div className="map-layout">
        {viewMode === "photo" ? (
          <div className="board-photo-col">
            <div className="board-photo-scroll">
              <div className="board-photo-wrap">
                <img src={boardImageUrl} alt="1822 board map" className="board-photo" />
                <svg
                  className="board-photo-overlay"
                  viewBox={`0 0 ${PHOTO_IMAGE_W} ${PHOTO_IMAGE_H}`}
                >
                  {photoGrid.map(({ hexId, col, row }) => {
                    const { x, y } = photoHexCenter(col, row);
                    const placed = effectiveBoardTiles?.[hexId];
                    const catalogued = (hexEntriesById.get(hexId)?.length ?? 0) > 0;
                    const isSelected = hexId === selectedHexId;
                    const isQueued = hexId === queuedHexId;
                    const isPending = pendingPlacement?.hexId === hexId;
                    return (
                      <g key={hexId} onClick={() => selectHex(hexId)}>
                        <polygon
                          points={hexPoints(x, y, PHOTO_HEX_SIZE)}
                          className={`photo-hex${catalogued ? " catalogued" : ""}${
                            placed ? " placed" : ""
                          }${isSelected ? " selected" : ""}${isQueued ? " queued" : ""}${
                            isPending ? " pending" : ""
                          }`}
                        />
                        {placed && tileUrl(`tile_${placed.tile_id}.svg`) && (
                          <image
                            href={tileUrl(`tile_${placed.tile_id}.svg`)}
                            x={x - PHOTO_HEX_SIZE * TILE_ART_SCALE}
                            y={y - PHOTO_HEX_SIZE * TILE_ART_SCALE}
                            width={PHOTO_HEX_SIZE * 2 * TILE_ART_SCALE}
                            height={PHOTO_HEX_SIZE * 2 * TILE_ART_SCALE}
                            transform={`rotate(${placed.rotation * 60} ${x} ${y})`}
                            pointerEvents="none"
                          />
                        )}
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>
            <div className="hex-search">
              <input
                placeholder="Find a hex by id (e.g. D35) or city name (e.g. Swansea)"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {searchResults.length > 0 && (
                <ul className="hex-search-results">
                  {searchResults.map((r) => (
                    <li key={r.id}>
                      <button
                        onClick={() => {
                          selectHex(r.id);
                          setSearch("");
                        }}
                      >
                        {r.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {placedList.length > 0 && (
              <div className="placed-tiles-list">
                <h4>Tiles laid so far</h4>
                <ul>
                  {placedList.map(([hexId, t]) => (
                    <li key={hexId}>
                      <button onClick={() => selectHex(hexId)}>
                        {hexId}: tile {t.tile_id} @ rotation {t.rotation}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {Object.keys(regionCorrections).length > 0 && (
              <div className="placed-tiles-list region-corrections-list">
                <h4>Your region corrections ({Object.keys(regionCorrections).length})</h4>
                <ul>
                  {Object.values(regionCorrections).map((c) => {
                    const tags = [
                      c.cityOrTown && (c.cityOrTown === "town" ? "town" : "city"),
                      c.isOffboard && "offboard",
                      c.isTerrain && "terrain",
                    ].filter(Boolean);
                    return (
                      <li key={c.hexId}>
                        <button onClick={() => selectHex(c.hexId)}>
                          {c.hexId}: {tags.length > 0 ? tags.join(" + ") : "?"}
                          {c.name ? ` - ${c.name}` : ""}
                        </button>
                      </li>
                    );
                  })}
                </ul>
                <div className="region-data-actions">
                  <button onClick={downloadRegionCorrections}>Download corrections.json</button>
                  <button onClick={copyRegionCorrections}>{regionCopied ? "Copied!" : "Copy to clipboard"}</button>
                </div>
                <p className="hint">
                  Saved to the server as you go now, so anyone hitting this backend sees the same corrections. The
                  download/copy buttons above are still there if you want to hand the whole batch off directly.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="hex-map-scroll">
            <svg
              className="hex-map-svg"
              width={bounds.maxX - bounds.minX}
              height={bounds.maxY - bounds.minY}
              viewBox={`${bounds.minX} ${bounds.minY} ${bounds.maxX - bounds.minX} ${bounds.maxY - bounds.minY}`}
            >
              {allHexes.map(({ hex, kind }) => {
                const { x, y } = hexCenter(hex.col, hex.row, hex.dx, hex.dy);
                const placed = effectiveBoardTiles?.[hex.id];
                const isSelected = hex.id === selectedHexId;
                const isQueued = hex.id === queuedHexId;
                const isPending = pendingPlacement?.hexId === hex.id;
                return (
                  <g key={`${kind}-${hex.id}`} onClick={() => selectHex(hex.id)} className="map-hex">
                    <polygon
                      points={hexPoints(x, y, SIZE)}
                      fill={colorFor(kind, hex)}
                      stroke={isPending ? "#d4a017" : isSelected ? "#c0392b" : isQueued ? "#2c6e49" : "#333"}
                      strokeWidth={isPending || isSelected || isQueued ? 3 : 1}
                      strokeDasharray={isPending ? "4 2" : undefined}
                    />
                    {placed && tileUrl(`tile_${placed.tile_id}.svg`) && (
                      <image
                        href={tileUrl(`tile_${placed.tile_id}.svg`)}
                        x={x - SIZE * TILE_ART_SCALE}
                        y={y - SIZE * TILE_ART_SCALE}
                        width={SIZE * 2 * TILE_ART_SCALE}
                        height={SIZE * 2 * TILE_ART_SCALE}
                        transform={`rotate(${placed.rotation * 60} ${x} ${y})`}
                        pointerEvents="none"
                      />
                    )}
                    <text x={x} y={y + SIZE + 9} textAnchor="middle" fontSize={8} fill="#333">
                      {hex.id}
                    </text>
                    {"name" in hex && (
                      <text x={x} y={y + 3} textAnchor="middle" fontSize={7} fill="#111" pointerEvents="none">
                        {(hex as MapCity | MapOffboard).name.slice(0, 10)}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>
        )}

        <div className="map-side-panel">
          {!selectedHexId && (
            <p className="hint">Click a hexagon on the map (or search above) to inspect or lay a tile on it.</p>
          )}
          {selectedHexId && (
            <>
              <h4>
                {selectedHexId}
                {selectedInfo && "name" in selectedInfo.hex ? ` - ${(selectedInfo.hex as MapCity).name}` : ""}
              </h4>
              {selectedInfo ? (
                <p className="hint">
                  {selectedInfo.kind === "city" &&
                    `${(selectedInfo.hex as MapCity).is_town ? "Town" : "City"}${
                      (selectedInfo.hex as MapCity).label ? ` (label ${(selectedInfo.hex as MapCity).label})` : ""
                    }`}
                  {selectedInfo.kind === "offboard" &&
                    `Off-board area: ${(selectedInfo.hex as MapOffboard).name} (£${
                      (selectedInfo.hex as MapOffboard).value_yellow
                    }/£${(selectedInfo.hex as MapOffboard).value_green}/£${
                      (selectedInfo.hex as MapOffboard).value_brown
                    }/£${(selectedInfo.hex as MapOffboard).value_grey})`}
                  {selectedInfo.kind === "terrain" &&
                    `Difficult terrain: ${(selectedInfo.hex as MapTerrain).terrain} (£${
                      (selectedInfo.hex as MapTerrain).cost
                    } to cross)`}
                </p>
              ) : (
                <p className="hint">Not in the catalogued hex list - showing tile legality only.</p>
              )}
              <p className="hint">
                {selectedPlacedTile
                  ? `Currently has tile ${selectedPlacedTile.tile_id} at rotation ${selectedPlacedTile.rotation}.`
                  : "No tile placed yet on this hex."}
              </p>

              {pendingPlacement && pendingPlacement.hexId === selectedHexId ? (
                <div className="pending-placement-panel">
                  <div className="tile-preview">
                    {tileUrl(`tile_${pendingPlacement.tileId}.svg`) && (
                      <img
                        src={tileUrl(`tile_${pendingPlacement.tileId}.svg`)}
                        alt={pendingPlacement.tileId}
                        style={{ transform: `rotate(${pendingPlacement.rotation * 60}deg)` }}
                      />
                    )}
                  </div>
                  <p className="hint">
                    Tile {pendingPlacement.tileId}, rotation {pendingPlacement.rotation} - not placed yet.
                  </p>
                  <p className="hint">
                    <strong>←</strong> / <strong>→</strong> rotate &nbsp;·&nbsp; <strong>Enter</strong> confirm
                    &nbsp;·&nbsp; <strong>Esc</strong> cancel
                  </p>
                  <div className="rotation-controls">
                    <button
                      onClick={() =>
                        setPendingPlacement((p) => (p ? { ...p, rotation: (p.rotation + 5) % 6 } : p))
                      }
                    >
                      ⟲ Rotate
                    </button>
                    <button
                      onClick={() =>
                        setPendingPlacement((p) => (p ? { ...p, rotation: (p.rotation + 1) % 6 } : p))
                      }
                    >
                      ⟳ Rotate
                    </button>
                  </div>
                  <div className="pending-placement-actions">
                    <button className="place-tile-btn" disabled={placing} onClick={confirmPendingPlacement}>
                      {placing ? "Placing..." : "Confirm (Enter)"}
                    </button>
                    <button onClick={() => setPendingPlacement(null)}>Cancel (Esc)</button>
                  </div>
                  <button
                    onClick={() => {
                      setPendingPlacement(null);
                      setModalOpen(true);
                    }}
                  >
                    Pick a different tile...
                  </button>
                  <button
                    onClick={() => {
                      onQueueLay(pendingPlacement.hexId, pendingPlacement.tileId, pendingPlacement.rotation);
                      setPendingPlacement(null);
                    }}
                  >
                    Queue for Operate instead (to also pick a dividend / buy a train)
                  </button>
                  {placeError && <p className="error">{placeError}</p>}
                </div>
              ) : (
                <div className="hex-actions-row">
                  <button
                    className="open-picker-btn"
                    onClick={() => {
                      setPlaceConfirmed(null);
                      setModalOpen(true);
                    }}
                  >
                    Choose a tile to place here...
                  </button>
                  {selectedPlacedTile && (
                    <button className="remove-tile-btn" disabled={removing} onClick={removeSelectedTile}>
                      {removing ? "Removing..." : "Remove tile"}
                    </button>
                  )}
                </div>
              )}
              {placeConfirmed && <p className="place-confirmed">✓ {placeConfirmed}</p>}
              {!pendingPlacement && placeError && <p className="error">{placeError}</p>}
              {isQueuedNote(selectedHexId, queuedHexId)}

              <div className="region-data-panel">
                <h4>Cross-check this region's data</h4>
                <p className="hint">Currently on file for {selectedHexId}:</p>
                {selectedEntries.length > 0 ? (
                  <>
                    {selectedEntries.map((info) => (
                      <ul className="region-data-list" key={info.kind}>
                        <li>
                          Kind:{" "}
                          <strong>
                            {info.kind === "city" ? ((info.hex as MapCity).is_town ? "Town" : "City") : info.kind}
                          </strong>
                        </li>
                        {"name" in info.hex && <li>Name: {(info.hex as MapCity | MapOffboard).name}</li>}
                        {info.kind === "city" && (
                          <>
                            <li>Label: {(info.hex as MapCity).label ?? "none"}</li>
                            {(info.hex as MapCity).is_town && (info.hex as MapCity).town_count > 1 && (
                              <li>Number of towns on this hex: {(info.hex as MapCity).town_count}</li>
                            )}
                            {!(info.hex as MapCity).is_town && (info.hex as MapCity).city_count > 1 && (
                              <li>Number of cities on this hex: {(info.hex as MapCity).city_count}</li>
                            )}
                            <li>Home of major(s): {(info.hex as MapCity).home_of_major.join(", ") || "none"}</li>
                            <li>Home of minor(s): {(info.hex as MapCity).home_of_minor.join(", ") || "none"}</li>
                            <li>Destination of major: {(info.hex as MapCity).destination_of_major ?? "none"}</li>
                          </>
                        )}
                        {info.kind === "offboard" && (
                          <li>
                            Revenue (yellow/green/brown/grey): £{(info.hex as MapOffboard).value_yellow}/£
                            {(info.hex as MapOffboard).value_green}/£
                            {(info.hex as MapOffboard).value_brown}/£
                            {(info.hex as MapOffboard).value_grey}
                          </li>
                        )}
                        {info.kind === "terrain" && (
                          <li>
                            Terrain: {(info.hex as MapTerrain).terrain}, £{(info.hex as MapTerrain).cost} to cross
                          </li>
                        )}
                        <li>
                          Confidence:{" "}
                          <span className={`confidence-badge confidence-${info.hex.confidence}`}>
                            {info.hex.confidence}
                          </span>
                        </li>
                      </ul>
                    ))}
                  </>
                ) : (
                  <p className="hint">
                    Not catalogued at all - this engine treats {selectedHexId} as plain, undifferentiated land/sea.
                  </p>
                )}

                {selectedHexId && mapData && (
                  <>
                    <p className="hint">Edges on file:</p>
                    <ul className="region-data-list region-edges-list">
                      {(() => {
                        const parsed = parseHexId(selectedHexId, mapData.columns);
                        const currentEdges = edgesFromCatalogued(selectedHexId);
                        return EDGE_DIRECTIONS.map(({ edge, short, full }) => {
                          const neighborId = parsed
                            ? neighborHexId(mapData.columns, parsed.col, parsed.row, edge)
                            : null;
                          const current = currentEdges[edge];
                          return (
                            <li key={edge}>
                              {full} ({short}) → {neighborId ?? "off the board"}
                              {current?.status === "blocked" && " - blocked, no connection"}
                              {current?.status === "toll" && ` - toll £${current.cost}`}
                            </li>
                          );
                        });
                      })()}
                    </ul>
                  </>
                )}

                {regionCorrections[selectedHexId] && (
                  <p className="hint region-data-saved-note">
                    ✓ Saved {new Date(regionCorrections[selectedHexId].savedAt).toLocaleString()} - included in the
                    export below.
                  </p>
                )}

                <div className="region-data-form">
                  <p className="hint">
                    A hex can be more than one of these at once (e.g. Aberdeen is both a city and an off-board
                    revenue area) - check everything that's actually printed there.
                  </p>

                  <label>
                    City / town on this hex?
                    <select
                      value={regionForm.cityOrTown}
                      onChange={(e) => setRegionForm({ ...regionForm, cityOrTown: e.target.value as CityOrTown })}
                    >
                      <option value="">none</option>
                      <option value="city">City</option>
                      <option value="town">Town</option>
                    </select>
                  </label>

                  {(regionForm.cityOrTown === "city" || regionForm.cityOrTown === "town") && (
                    <>
                      <label>
                        Printed name
                        <input
                          value={regionForm.name}
                          onChange={(e) => setRegionForm({ ...regionForm, name: e.target.value })}
                          placeholder="e.g. Portsmouth"
                        />
                      </label>
                      <label>
                        Printed label (letter code inside the city circle, if any)
                        <select
                          value={regionForm.label}
                          onChange={(e) => setRegionForm({ ...regionForm, label: e.target.value })}
                        >
                          <option value="">none</option>
                          {LABEL_OPTIONS.map((l) => (
                            <option key={l} value={l}>
                              {l}
                            </option>
                          ))}
                        </select>
                      </label>
                      {regionForm.cityOrTown === "town" && (
                        <label>
                          Number of town circles printed on this one hex
                          <select
                            value={regionForm.townCount}
                            onChange={(e) => setRegionForm({ ...regionForm, townCount: e.target.value })}
                          >
                            <option value="1">1</option>
                            <option value="2">2</option>
                          </select>
                        </label>
                      )}
                      {regionForm.cityOrTown === "city" && (
                        <label>
                          Number of city circles printed on this one hex (almost always 1 - London is 6)
                          <select
                            value={regionForm.cityCount}
                            onChange={(e) => setRegionForm({ ...regionForm, cityCount: e.target.value })}
                          >
                            {[1, 2, 3, 4, 5, 6].map((n) => (
                              <option key={n} value={n}>
                                {n}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                      <label>
                        Home of major compan(y/ies) - comma-separated abbreviations, if any
                        <input
                          value={regionForm.homeOfMajor}
                          onChange={(e) => setRegionForm({ ...regionForm, homeOfMajor: e.target.value })}
                          placeholder="e.g. NBR"
                        />
                      </label>
                      <label>
                        Home of minor compan(y/ies) - comma-separated numbers, if any
                        <input
                          value={regionForm.homeOfMinor}
                          onChange={(e) => setRegionForm({ ...regionForm, homeOfMinor: e.target.value })}
                          placeholder="e.g. 3"
                        />
                      </label>
                      <label>
                        Destination of major (abbreviation, if any)
                        <input
                          value={regionForm.destinationOfMajor}
                          onChange={(e) => setRegionForm({ ...regionForm, destinationOfMajor: e.target.value })}
                          placeholder="e.g. NER"
                        />
                      </label>
                    </>
                  )}

                  <label className="region-data-checkbox">
                    <input
                      type="checkbox"
                      checked={regionForm.isOffboard}
                      onChange={(e) => setRegionForm({ ...regionForm, isOffboard: e.target.checked })}
                    />
                    Off-board revenue area here too (a company's starting point, or just a revenue-only box)
                  </label>
                  {regionForm.isOffboard && (
                    <>
                      <label>
                        Off-board area name
                        <input
                          value={regionForm.offboardName}
                          onChange={(e) => setRegionForm({ ...regionForm, offboardName: e.target.value })}
                          placeholder="e.g. Highlands"
                        />
                      </label>
                      <label>
                        Revenue by phase color (yellow / green / brown / grey)
                        <div className="region-data-values-row">
                          <input
                            value={regionForm.valueYellow}
                            onChange={(e) => setRegionForm({ ...regionForm, valueYellow: e.target.value })}
                            placeholder="£ yellow"
                          />
                          <input
                            value={regionForm.valueGreen}
                            onChange={(e) => setRegionForm({ ...regionForm, valueGreen: e.target.value })}
                            placeholder="£ green"
                          />
                          <input
                            value={regionForm.valueBrown}
                            onChange={(e) => setRegionForm({ ...regionForm, valueBrown: e.target.value })}
                            placeholder="£ brown"
                          />
                          <input
                            value={regionForm.valueGrey}
                            onChange={(e) => setRegionForm({ ...regionForm, valueGrey: e.target.value })}
                            placeholder="£ grey"
                          />
                        </div>
                      </label>
                    </>
                  )}

                  <label className="region-data-checkbox">
                    <input
                      type="checkbox"
                      checked={regionForm.isTerrain}
                      onChange={(e) => setRegionForm({ ...regionForm, isTerrain: e.target.checked })}
                    />
                    Difficult terrain here too (costs money to lay the first tile)
                  </label>
                  {regionForm.isTerrain && (
                    <>
                      <label>
                        Terrain type
                        <select
                          value={regionForm.terrain}
                          onChange={(e) => setRegionForm({ ...regionForm, terrain: e.target.value })}
                        >
                          <option value="">— pick one —</option>
                          {TERRAIN_OPTIONS.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Cost to cross (£)
                        <input
                          value={regionForm.cost}
                          onChange={(e) => setRegionForm({ ...regionForm, cost: e.target.value })}
                          placeholder="e.g. 40"
                        />
                      </label>
                    </>
                  )}

                  <p className="hint region-data-edges-heading">
                    Edges - which of the 6 neighboring regions this hex actually connects to. Starts as "Empty"
                    (nothing there / not yet checked) for every edge - switch one to "Normal" once you've confirmed
                    it's an ordinary connection, "Blocked" for a red no-go line, or "Toll" for a marked fee to
                    connect.
                  </p>
                  {selectedHexId &&
                    mapData &&
                    EDGE_DIRECTIONS.map(({ edge, short, full }) => {
                      const parsed = parseHexId(selectedHexId, mapData.columns);
                      const neighborId = parsed ? neighborHexId(mapData.columns, parsed.col, parsed.row, edge) : null;
                      const current = regionForm.edges[edge] ?? { status: "empty", cost: "" };
                      return (
                        <div className="region-edge-row" key={edge}>
                          <span className="region-edge-label">
                            {full} ({short}) → {neighborId ?? "off board"}
                          </span>
                          <select
                            value={current.status}
                            disabled={!neighborId}
                            onChange={(e) =>
                              setRegionForm({
                                ...regionForm,
                                edges: {
                                  ...regionForm.edges,
                                  [edge]: { ...current, status: e.target.value as EdgeStatus },
                                },
                              })
                            }
                          >
                            <option value="normal">Normal - connects</option>
                            <option value="blocked">Blocked - marked as never connecting</option>
                            <option value="toll">Toll - connects, costs money</option>
                            <option value="empty">Empty - nothing here, no connection</option>
                          </select>
                          {current.status === "toll" && (
                            <input
                              className="region-edge-toll-input"
                              value={current.cost}
                              onChange={(e) =>
                                setRegionForm({
                                  ...regionForm,
                                  edges: { ...regionForm.edges, [edge]: { ...current, cost: e.target.value } },
                                })
                              }
                              placeholder="£ toll"
                            />
                          )}
                        </div>
                      );
                    })}

                  <label>
                    Notes (optional)
                    <textarea
                      value={regionForm.note}
                      onChange={(e) => setRegionForm({ ...regionForm, note: e.target.value })}
                      rows={2}
                      placeholder="Anything I should know about this hex"
                    />
                  </label>

                  <div className="region-data-actions">
                    <button onClick={saveRegionCorrection}>Save correction for {selectedHexId}</button>
                    {regionCorrections[selectedHexId] && (
                      <button onClick={() => discardRegionCorrection(selectedHexId)}>Discard</button>
                    )}
                  </div>
                  {regionSaved && <p className="place-confirmed">✓ Saved - added to your corrections export.</p>}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {modalOpen && selectedHexId && (
        <div className="tile-modal-backdrop" onClick={() => setModalOpen(false)}>
          <div className="tile-modal" onClick={(e) => e.stopPropagation()}>
            <div className="tile-modal-header">
              <h3>
                {selectedHexId}
                {selectedInfo && "name" in selectedInfo.hex ? ` - ${(selectedInfo.hex as MapCity).name}` : ""}
              </h3>
              <button className="tile-modal-close" onClick={() => setModalOpen(false)} aria-label="Close">
                ✕
              </button>
            </div>

            <p className="hint">
              {selectedPlacedTile
                ? `Currently has tile ${selectedPlacedTile.tile_id} at rotation ${selectedPlacedTile.rotation}.`
                : "No tile placed yet on this hex."}
            </p>
            {!roomId && <p className="hint">Start or join a game to see which tiles are legal here.</p>}
            {roomId && reportLoading && <p className="hint">Checking which tiles can legally be placed here...</p>}
            {reportError && <p className="error">{reportError}</p>}

            <div className="tile-modal-body">
              <div className="tile-modal-palette tile-modal-palette-only">
                <h4>Pick a tile for phase {companyKind === "minor" ? "(minor)" : "(major)"} - click one to place it</h4>
                {TILE_COLOR_ORDER.map((color) => {
                  const phaseAllows = TILE_COLOR_ORDER.indexOf(color) <= TILE_COLOR_ORDER.indexOf(maxTileColor);
                  const available = grouped[color].filter(() => phaseAllows);
                  if (available.length === 0) return null;
                  return (
                    <div key={color} className="tile-palette-row modal-tile-palette-row">
                      <span className="tile-palette-label">{color}</span>
                      {available.map((t) => {
                        const url = tileUrl(t.file);
                        const remaining = remainingSupply(t.id, selectedHexId);
                        const outOfSupply = remaining !== null && remaining <= 0;
                        return (
                          <button
                            key={t.id}
                            className={`tile-swatch modal-tile-swatch${outOfSupply ? " out-of-supply" : ""}`}
                            onClick={() => pickTile(t.id)}
                            title={
                              outOfSupply
                                ? `Tile ${t.id}: none left in supply`
                                : `Tile ${t.id} (${remaining === null ? "unlimited" : `${remaining} left`})`
                            }
                          >
                            {url ? <img src={url} alt={t.id} /> : t.id}
                            {remaining !== null && <span className="tile-swatch-count">{remaining}</span>}
                          </button>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function isQueuedNote(selectedHexId: string | null, queuedHexId: string | null) {
  if (selectedHexId && selectedHexId === queuedHexId) {
    return <p className="hint">Queued - go to the Operate tab and click Operate to lay it.</p>;
  }
  return null;
}
