import { useEffect, useMemo, useState } from "react";
import { fetchBoardMap, type BoardMapData, type MapCity, type MapOffboard, type MapTerrain } from "./api";
import manifestUrl from "./assets/tiles/manifest.json?url";

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

const SIZE = 40; // hex "radius" (center to vertex) in px
const COL_SPACING = SIZE * 1.5;
const ROW_SPACING = SIZE * Math.sqrt(3);

function hexCenter(col: number, row: number, dx: number, dy: number) {
  const x = col * COL_SPACING;
  const y = row * ROW_SPACING + (col % 2 === 1 ? ROW_SPACING / 2 : 0);
  return { x: x + dx * COL_SPACING * 0.5, y: y + dy * ROW_SPACING * 0.5 };
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

type Props = {
  boardTiles: Record<string, PlacedTile> | undefined;
  inGame: boolean;
  canQueueLay: boolean;
  onQueueLay: (hexId: string, tileId: string, rotation: number) => void;
  queuedHexId: string | null;
};

export default function MapTab({ boardTiles, inGame, canQueueLay, onQueueLay, queuedHexId }: Props) {
  const [mapData, setMapData] = useState<BoardMapData | null>(null);
  const [manifest, setManifest] = useState<TileManifestEntry[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedHexId, setSelectedHexId] = useState<string | null>(null);
  const [pendingTileId, setPendingTileId] = useState<string | null>(null);
  const [pendingRotation, setPendingRotation] = useState(0);

  useEffect(() => {
    fetchBoardMap()
      .then(setMapData)
      .catch((e) => setLoadError((e as Error).message));
    fetch(manifestUrl)
      .then((r) => r.json())
      .then(setManifest)
      .catch((e) => setLoadError((e as Error).message));
  }, []);

  const allHexes = useMemo(() => {
    if (!mapData) return [];
    const list: { hex: MapCity | MapOffboard | MapTerrain; kind: "city" | "offboard" | "terrain" }[] = [];
    for (const c of mapData.cities) list.push({ hex: c, kind: "city" });
    for (const o of mapData.offboard) list.push({ hex: o, kind: "offboard" });
    for (const t of mapData.terrain) list.push({ hex: t, kind: "terrain" });
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

  return (
    <div className="panel map-panel">
      <h3>Map & Tile Placement</h3>
      <p className="hint">
        Preview of the catalogued hexes (cities, towns, off-board areas, difficult terrain) -
        not yet the full physical board (see task #12/#3). Click a hex, pick a tile and
        rotation, then queue it - that fills the same tile-lay fields the Operate tab sends,
        so switch there and click Operate during that company's turn to actually place it.
      </p>
      {loadError && <p className="error">{loadError}</p>}

      <div className="map-layout">
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
              <g
                key={`${kind}-${hex.id}`}
                onClick={() => setSelectedHexId(hex.id)}
                className="map-hex"
              >
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

        <div className="map-side-panel">
          {!selectedInfo && <p className="hint">Click a hex on the map to inspect or lay a tile on it.</p>}
          {selectedInfo && (
            <>
              <h4>
                {selectedInfo.hex.id}
                {"name" in selectedInfo.hex ? ` - ${(selectedInfo.hex as MapCity).name}` : ""}
              </h4>
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
              <p className="hint">
                {selectedPlacedTile
                  ? `Currently has tile ${selectedPlacedTile.tile_id} at rotation ${selectedPlacedTile.rotation}.`
                  : "No tile placed yet on this hex."}
              </p>

              <h4>Pick a tile</h4>
              {(["yellow", "green", "brown", "gray"] as const).map((color) => (
                <div key={color} className="tile-palette-row">
                  <span className="tile-palette-label">{color}</span>
                  {grouped[color].map((t) => {
                    const url = tileUrl(t.file);
                    return (
                      <button
                        key={t.id}
                        className={`tile-swatch${pendingTileId === t.id ? " selected" : ""}`}
                        onClick={() => setPendingTileId(t.id)}
                        title={`Tile ${t.id} (${t.count} in supply)`}
                      >
                        {url ? <img src={url} alt={t.id} /> : t.id}
                      </button>
                    );
                  })}
                </div>
              ))}

              {pendingTileId && (
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
              )}

              <div>
                <button
                  disabled={!pendingTileId || !inGame || !canQueueLay}
                  onClick={() => {
                    if (selectedHexId && pendingTileId) onQueueLay(selectedHexId, pendingTileId, pendingRotation);
                  }}
                >
                  Queue this tile lay for Operate
                </button>
                {!inGame && <p className="hint">Start or join a game to lay tiles.</p>}
                {inGame && !canQueueLay && (
                  <p className="hint">Only usable during an operating round.</p>
                )}
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
