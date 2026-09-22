# Individual cards

One PNG per company/train, extracted from the sprite-sheet pages in `docs/`
(`train-cards.html`, `minor-company-cards.html`, `private-company-cards.html`,
`major-company-cards.html`) via `docs/tools/extract_cards.py`.

- `trains/train_<code>.png` — 8 files (L, 2, 3, 4, 5, 6, 7, E)
- `minors/M<n>.png` — 30 files (M1-M30)
- `privates/P<n>.png` — 21 files (P1-P21)
- `majors/<ABBR>.png` — 10 files (LNWR, MR, LBSCR, SECR, NER, GWR, CR, LYR, NBR, SWR)

Filenames match the ids used throughout `backend/app/data/` (train codes,
minor/private company numbers, major company abbreviations with `&` stripped,
e.g. `L&YR` -> `LYR`), so game code can look up a card by the same id it uses
everywhere else.

## Regenerating

After editing any of the four sprite-sheet HTML files (or the data feeding
them in `backend/app/data/`), regenerate every individual card:

```bash
cd docs/tools
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 extract_cards.py
```

Each card is captured directly from its `.card` DOM element via its
`data-id` attribute, at 2x device scale, so adding a new card to a sheet
(with a `data-id`) is picked up automatically - no per-card coordinates to
maintain.
