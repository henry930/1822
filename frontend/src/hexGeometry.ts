// Hex-grid geometry shared by anything that draws or clicks the real board
// scan (MapTab's photo view, CompaniesTab's embedded picker) - kept in one
// place specifically so the coordinate math and the pixel calibration
// can't drift out of sync between the two, the way they briefly did here:
// this file's neighbor math used to be a stale copy of an already-fixed
// backend bug (see app.engine.hex_grid's module docstring on the backend -
// "odd-q offset" was simply the wrong coordinate system for this board;
// the real one is "doubled-height", confirmed against the rules-confirmed
// F23<->F25 / F31<->F33 blocked-adjacency pairs). This module now matches
// that fix; if it's ever touched again, fix it here once, not per-component.

// Parses a hex id like "H23" into (col, row).
export function parseHexId(hexId: string, columns: string[]): { col: number; row: number } | null {
  const m = /^([A-Za-z]{1,2})(\d{1,2})$/.exec(hexId);
  if (!m) return null;
  const col = columns.indexOf(m[1].toUpperCase());
  if (col === -1) return null;
  return { col, row: parseInt(m[2], 10) };
}

// Doubled-height coordinates (see app.engine.hex_grid's module docstring):
// same-column N/S neighbors are 2 rows away, not 1; diagonal neighbors
// move 1 column and 1 row. One uniform delta table, no column-parity split.
// Edges: 0=N, 1=NE, 2=SE, 3=S, 4=SW, 5=NW.
export const EDGE_DELTAS: [number, number][] = [
  [0, -2],
  [1, -1],
  [1, 1],
  [0, 2],
  [-1, 1],
  [-1, -1],
];
export const GRID_MIN_ROW = 1;
export const GRID_MAX_ROW = 44;

export function neighborHexId(columns: string[], col: number, row: number, edge: number): string | null {
  const [dCol, dRow] = EDGE_DELTAS[edge];
  const nCol = col + dCol;
  const nRow = row + dRow;
  if (nCol < 0 || nCol >= columns.length || nRow < GRID_MIN_ROW || nRow > GRID_MAX_ROW) return null;
  return `${columns[nCol]}${nRow}`;
}

// Calibration for the real board scan (board.jpg, 1700x2200 - see
// assets/map/README.md for how these were measured). The board's printed
// row numbers turned out to increment by 1 per HALF a physical hex-row
// (odd columns only ever carry odd row numbers, even columns only ever
// carry even ones - confirmed against 26/28 rules-confidence catalogued
// hexes), so a hex's pixel position is a *plain* linear map of its raw
// (col, row).
export const PHOTO_X0 = 222.0;
export const PHOTO_DX = 78.05; // px per column-letter step
export const PHOTO_Y0 = 92.1;
export const PHOTO_DY = 45.23; // px per printed row-number unit
export const PHOTO_HEX_SIZE = 52; // center-to-vertex, tessellates with PHOTO_DX/DY above
export const PHOTO_IMAGE_W = 1700;
export const PHOTO_IMAGE_H = 2200;
export const PHOTO_MAX_ROW = 43;

export function photoHexCenter(col: number, row: number) {
  return { x: PHOTO_X0 + col * PHOTO_DX, y: PHOTO_Y0 + row * PHOTO_DY };
}

export function hexPoints(cx: number, cy: number, size: number): string {
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

// Every real hex position on the printed board, within the given columns -
// a real hex only exists where the column index and row number share
// parity (see the calibration note above). Includes any extra hex ids
// (e.g. ones with live state) the caller already knows about even if they
// fall on the "wrong" parity, since real placed/selected state is still
// real regardless of this best-effort grid.
export function photoGridPositions(
  columns: string[],
  extraHexIds: Iterable<string> = []
): { hexId: string; col: number; row: number }[] {
  const list: { hexId: string; col: number; row: number }[] = [];
  const seen = new Set<string>();
  for (let col = 0; col < columns.length; col++) {
    for (let row = 1; row <= PHOTO_MAX_ROW; row++) {
      if (col % 2 === row % 2) {
        const hexId = `${columns[col]}${row}`;
        list.push({ hexId, col, row });
        seen.add(hexId);
      }
    }
  }
  for (const hexId of extraHexIds) {
    if (seen.has(hexId)) continue;
    const parsed = parseHexId(hexId, columns);
    if (parsed) {
      list.push({ hexId, ...parsed });
      seen.add(hexId);
    }
  }
  return list;
}
