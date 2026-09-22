# Board scan

`board.jpg` is map.pdf's page 1 rasterized at 300dpi (2550x3300), then
resized to 1700x2200 (exactly 2/3 scale) and re-encoded as JPEG to keep the
bundled asset small.

## Pixel calibration

`MapTab.tsx`'s `PHOTO_X0`/`PHOTO_DX`/`PHOTO_Y0`/`PHOTO_DY` constants map a
hex's `(col, row)` - `col` is its 0-indexed column letter (A=0..Q=16), `row`
is the raw row number printed on the board, exactly as used elsewhere in
this codebase (`app.data.hex_map`, the `/board/map` endpoint) - to a pixel
position on `board.jpg`.

Measured by isolating the printed row-number and column-letter margins
(clean background, no map art behind them) and finding each digit/letter's
pixel centroid via a simple dark-pixel connected-component scan, then a
linear fit. Two things fell out of that measurement that are worth knowing
if this ever needs re-deriving:

- **No odd/even column offset term is needed.** The engine's abstract
  hex_grid.py model treats "row" as a per-column sequential index and adds
  a half-row offset for odd columns (standard "odd-q" layout). The
  *printed* row numbers on the physical board are not that: they increment
  by 1 per half a physical hex-row, shared across interleaved columns, so
  a column's own row numbers are all the same parity as the column index
  (confirmed against 26/28 "rules"-confidence catalogued hexes in
  app.data.hex_map - Aberdeen H1, Edinburgh H5, Newcastle K10, etc. all
  have matching col/row parity). That means the pixel formula is a plain
  `x = X0 + col*DX; y = Y0 + row*DY` with no extra term - simpler than the
  schematic view's formula, but not interchangeable with it.
- **DX/DY ≈ sqrt(3)**, matching a standard flat-top hex tessellation
  where DY is *half* a physical hex-row (per the point above) - i.e.
  `DY = (sqrt(3) * hex_size) / 2`, `DX = 1.5 * hex_size`. `PHOTO_HEX_SIZE`
  in `MapTab.tsx` is derived from that relationship, not eyeballed.

Verified by predicting the pixel position of several other "rules"
hexes (Newcastle K10, Grimsby N23, London M38, Plymouth B43) purely from
the fitted formula and checking each lands inside the correct hex.

If `board.jpg` is ever regenerated at a different crop/scale, these four
constants need re-measuring against the new image - they're pixel offsets
into that specific asset, not a property of the game data.
