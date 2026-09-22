import { useEffect, useMemo, useState } from "react";
import {
  fetchBoardMap,
  fetchTileLayOptions,
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

type Props = {
  roomId: string | null;
  companyKind: "minor" | "major";
  boardTiles: Record<string, PlacedTile> | undefined;
  inGame: boolean;
  canQueueLay: boolean;
  onQueueLay: (hexId: string, tileId: string, rotation: number) => void;
  queuedHexId: string | null;
};

export default function MapTab({
  roomId,
  companyKind,
  boardTiles,
  inGame,
  canQueueLay,
  onQueueLay,
  queuedHexId,
}: Props) {
  const [mapData, setMapData] = useState<BoardMapData | null>(null);
  const [manifest, setManifest] = useState<TileManifestEntry[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedHexId, setSelectedHexId] = useState<string | null>(null);
  const [pendingTileId, setPendingTileId] = useState<string | null>(null);
  const [pendingRotation, setPendingRotation] = useState(0);
  const [viewMode, setViewMode] = useState<"photo" | "schematic">("photo");
  const [search, setSearch] = useState("");
  const [report, setReport] = useState<TileLayOption[] | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    fetchBoardMap()
      .then(setMapData)
      .catch((e) => setLoadError((e as Error).message));
    fetch(manifestUrl)
      .then((r) => r.json())
      .then(setManifest)
      .catch((e) => setLoadError((e as Error).message));
  }, []);

  // Every (tile, rotation) combination's legality for the selected hex right
  // now, fetched once per hex/room/company-kind change - re-derived from the
  // real engine validator server-side, so it can never drift out of sync
  // with what actually happens when Operate is clicked.
  useEffect(() => {
    setReport(null);
    setReportError(null);
    setPendingTileId(null);
    if (!selectedHexId || !roomId) return;
    setReportLoading(true);
    fetchTileLayOptions(roomId, selectedHexId, companyKind)
      .then((r) => setReport(r.report))
      .catch((e) => setReportError((e as Error).message))
      .finally(() => setReportLoading(false));
  }, [selectedHexId, roomId, companyKind]);

  const reportByTile = useMemo(() => {
    const map = new Map<string, TileLayOption[]>();
    if (!report) return map;
    for (const opt of report) {
      const list = map.get(opt.tile_id) ?? [];
      list.push(opt);
      map.set(opt.tile_id, list);
    }
    return map;
  }, [report]);

  const allHexes: HexEntry[] = useMemo(() => {
    if (!mapData) return [];
    const list: HexEntry[] = [];
    for (const c of mapData.cities) list.push({ hex: c, kind: "city" });
    for (const o of mapData.offboard) list.push({ hex: o, kind: "offboard" });
    for (const t of mapData.terrain) list.push({ hex: t, kind: "terrain" });
    return list;
  }, [mapData]);

  const hexById = useMemo(() => {
    const map = new Map<string, HexEntry>();
    for (const entry of allHexes) map.set(entry.hex.id, entry);
    return map;
  }, [allHexes]);

  // Every clickable hex region on the real board scan: the printed board is
  // a full rectangular hex grid (sea hexes included, just colored blue), and
  // - per the calibration note above - a real hex only ever exists where the
  // column index and row number share the same parity. This is what makes
  // the photo view show "different hexagon regions" directly on the art,
  // not just the ~120 named/catalogued ones.
  const photoGrid = useMemo(() => {
    if (!mapData) return [];
    const list: { hexId: string; col: number; row: number }[] = [];
    for (let col = 0; col < mapData.columns.length; col++) {
      for (let row = 1; row <= PHOTO_MAX_ROW; row++) {
        if (col % 2 === row % 2) {
          list.push({ hexId: `${mapData.columns[col]}${row}`, col, row });
        }
      }
    }
    return list;
  }, [mapData]);

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

  const selectedInfo = allHexes.find(({ hex }) => hex.id === selectedHexId);
  const selectedPlacedTile = selectedHexId ? boardTiles?.[selectedHexId] : undefined;

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

  const placedList = Object.entries(boardTiles ?? {});

  const pendingOptions = pendingTileId ? reportByTile.get(pendingTileId) ?? [] : [];
  const pendingCurrent = pendingOptions.find((o) => o.rotation === pendingRotation);

  function pickTile(tileId: string) {
    setPendingTileId(tileId);
    const opts = reportByTile.get(tileId) ?? [];
    const firstValid = opts.find((o) => o.valid);
    setPendingRotation(firstValid ? firstValid.rotation : 0);
  }

  return (
    <div className="panel map-panel">
      <h3>Map & Tile Placement</h3>
      <p className="hint">
        The board on the left is the actual scanned 1822 map (map.pdf) with a clickable hex grid
        overlaid on it - click any hexagon region directly on the map (or search by id/city name
        below it) to select it. Once a hex is picked, only tiles that are actually legal to lay
        there right now (checked live against the game's real rules - phase/color, tile supply,
        upgrade-must-preserve-track, city label) are offered; pick a rotation and "Queue" fills
        the same tile-lay fields the Operate tab sends.
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
                    const placed = boardTiles?.[hexId];
                    const catalogued = hexById.get(hexId);
                    const isSelected = hexId === selectedHexId;
                    const isQueued = hexId === queuedHexId;
                    return (
                      <g key={hexId} onClick={() => setSelectedHexId(hexId)}>
                        <polygon
                          points={hexPoints(x, y, PHOTO_HEX_SIZE)}
                          className={`photo-hex${catalogued ? " catalogued" : ""}${
                            placed ? " placed" : ""
                          }${isSelected ? " selected" : ""}${isQueued ? " queued" : ""}`}
                        />
                        {placed && tileUrl(`tile_${placed.tile_id}.svg`) && (
                          <image
                            href={tileUrl(`tile_${placed.tile_id}.svg`)}
                            x={x - PHOTO_HEX_SIZE}
                            y={y - PHOTO_HEX_SIZE}
                            width={PHOTO_HEX_SIZE * 2}
                            height={PHOTO_HEX_SIZE * 2}
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
                          setSelectedHexId(r.id);
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
                      <button onClick={() => setSelectedHexId(hexId)}>
                        {hexId}: tile {t.tile_id} @ rotation {t.rotation}
                      </button>
                    </li>
                  ))}
                </ul>
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
                const placed = boardTiles?.[hex.id];
                const isSelected = hex.id === selectedHexId;
                const isQueued = hex.id === queuedHexId;
                return (
                  <g key={`${kind}-${hex.id}`} onClick={() => setSelectedHexId(hex.id)} className="map-hex">
                    <polygon
                      points={hexPoints(x, y, SIZE)}
                      fill={colorFor(kind, hex)}
                      stroke={isSelected ? "#c0392b" : isQueued ? "#2c6e49" : "#333"}
                      strokeWidth={isSelected || isQueued ? 3 : 1}
                    />
                    {placed && tileUrl(`tile_${placed.tile_id}.svg`) && (
                      <image
                        href={tileUrl(`tile_${placed.tile_id}.svg`)}
                        x={x - SIZE}
                        y={y - SIZE}
                        width={SIZE * 2}
                        height={SIZE * 2}
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

              {!roomId && <p className="hint">Start or join a game to see which tiles are legal here.</p>}
              {roomId && reportLoading && <p className="hint">Checking which tiles can legally be placed here...</p>}
              {reportError && <p className="error">{reportError}</p>}

              {report && (
                <>
                  <h4>Tiles that can be placed here ({companyKind})</h4>
                  {(["yellow", "green", "brown", "gray"] as const).map((color) => {
                    const placeable = grouped[color].filter((t) =>
                      (reportByTile.get(t.id) ?? []).some((o) => o.valid)
                    );
                    if (placeable.length === 0) return null;
                    return (
                      <div key={color} className="tile-palette-row">
                        <span className="tile-palette-label">{color}</span>
                        {placeable.map((t) => {
                          const url = tileUrl(t.file);
                          return (
                            <button
                              key={t.id}
                              className={`tile-swatch${pendingTileId === t.id ? " selected" : ""}`}
                              onClick={() => pickTile(t.id)}
                              title={`Tile ${t.id} (${t.count} in supply)`}
                            >
                              {url ? <img src={url} alt={t.id} /> : t.id}
                            </button>
                          );
                        })}
                      </div>
                    );
                  })}
                  {(["yellow", "green", "brown", "gray"] as const).every(
                    (color) => grouped[color].filter((t) => (reportByTile.get(t.id) ?? []).some((o) => o.valid)).length === 0
                  ) && <p className="hint">No tile can legally be placed here right now.</p>}
                </>
              )}

              {pendingTileId && (
                <>
                  <div className="tile-preview-row">
                    <div className="tile-preview">
                      {tileUrl(`tile_${pendingTileId}.svg`) && (
                        <img
                          src={tileUrl(`tile_${pendingTileId}.svg`)}
                          alt={pendingTileId}
                          style={{ transform: `rotate(${pendingRotation * 60}deg)` }}
                        />
                      )}
                    </div>
                    <div>
                      <p className="hint">Tile {pendingTileId}, rotation {pendingRotation}</p>
                      <button onClick={() => setPendingRotation((r) => (r + 5) % 6)}>⟲ rotate</button>
                      <button onClick={() => setPendingRotation((r) => (r + 1) % 6)}>⟳ rotate</button>
                    </div>
                  </div>
                  <div className="rotation-picker">
                    {[0, 1, 2, 3, 4, 5].map((rot) => {
                      const opt = pendingOptions.find((o) => o.rotation === rot);
                      return (
                        <button
                          key={rot}
                          className={`rotation-swatch${opt?.valid ? " valid" : " invalid"}${
                            pendingRotation === rot ? " selected" : ""
                          }`}
                          onClick={() => setPendingRotation(rot)}
                          title={opt?.valid ? `Rotation ${rot}: valid` : opt?.reason ?? "Invalid"}
                        >
                          {rot}
                        </button>
                      );
                    })}
                  </div>
                  {pendingCurrent && !pendingCurrent.valid && (
                    <p className="error">Not valid at this rotation: {pendingCurrent.reason}</p>
                  )}
                  {pendingCurrent?.valid && pendingCurrent.cost ? (
                    <p className="hint">Terrain cost: £{pendingCurrent.cost}</p>
                  ) : null}
                </>
              )}

              <div>
                <button
                  disabled={!pendingTileId || !pendingCurrent?.valid || !inGame || !canQueueLay}
                  onClick={() => {
                    if (selectedHexId && pendingTileId) onQueueLay(selectedHexId, pendingTileId, pendingRotation);
                  }}
                >
                  Queue this tile lay for Operate
                </button>
                {!inGame && <p className="hint">Start or join a game to lay tiles.</p>}
                {inGame && !canQueueLay && <p className="hint">Only usable during an operating round.</p>}
                {isQueuedNote(selectedHexId, queuedHexId)}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function isQueuedNote(selectedHexId: string | null, queuedHexId: string | null) {
  if (selectedHexId && selectedHexId === queuedHexId) {
    return <p className="hint">Queued - go to the Operate tab and click Operate to lay it.</p>;
  }
  return null;
}
