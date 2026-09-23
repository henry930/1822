# Track tiles

Clean vector (SVG) recreations of every distinct hex track tile from the
physical 1822 tile sheets shown in `rail_track.jpg` (the yellow/green/brown/gray
die-cut sheets numbered 1/4-4/4), one file per tile number
(`tile_<id>.svg`), plus `manifest.json` listing each tile's color, per-game
copy count, and city/label.

## Why recreated instead of cropped

`rail_track.jpg` is a phone photo of the sheets shot at an angle, with
perspective distortion, glare, and shadow — cropping it directly would carry
all of that into the game UI. Instead, `tools/gen_tiles.py` draws each tile
from its actual track/city specification (which edges connect, city revenue
and slot count, town dots, tile labels like `Y`/`C`/`BM`/`S`/`EC`/`L`/`T`) and
renders it as a flat-color hex with black rail lines and white city markers,
at any resolution.

The track topology and per-tile counts are the public 1822 tile manifest
(the same tile numbering used by the open-source 18xx.games rules engine,
cross-checked against the photographed sheets: tile numbers, £-costs and
revenue values printed on the sheets match). Colors/line weights follow
standard 18xx tile-art convention (yellow -> green -> brown -> gray upgrade
path).

## Rendering conventions (matching the printed sheets)

- Track meets each hex edge at the edge midpoint. Edge-to-edge track is a
  straight line (opposite edges), a sharp arc (adjacent edges) or a gentle
  arc (edges two apart); every rail has a thin white casing.
- A town on a single through-track (#3, #4, #58, and both towns on
  #1/#2/#55/#56/#69) sits *on* that straight/arc as a bold black dot. On the
  two-rail tiles the second rail is drawn crossing over the first, and each
  town is slid along its own rail away from the crossing.
- A town with 3+ exits (#141-#144, #767-#769, X17) is a dot at the center
  with straight spokes to each exit edge.
- Every town's revenue is printed in a white bubble, auto-placed in the
  clearest spot next to its dot so it never sits under track.
- Junction tiles (no revenue location) have no dot.

## Regenerating

```bash
python3 tools/gen_tiles.py
```

Rewrites every `tile_*.svg` and `manifest.json` from the tile table at the
bottom of `tools/gen_tiles.py`. Edit that table (add/adjust a tile's code,
color, or count) and re-run to regenerate.

## Tile code format

Each tile's spec string follows the 18xx convention:
- `city=revenue:R[,slots:N]` — a city lot worth R, with N station slots (default 1).
- `town=revenue:R` — a town (dot) lot worth R.
- `path=a:E,b:_L` — track from hex edge `E` (0-5, clockwise from the top edge)
  to lot index `L` (in order of appearance).
- `path=a:E1,b:E2` — plain track directly between two edges (no city/town).
- `junction` — a plain track crossing with no revenue location.
- `label=X` — the tile's printed city-type label.

61 distinct tiles in total: 14 yellow, 20 green, 15 brown, 12 gray.
