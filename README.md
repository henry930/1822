# 1822 (digital)

A digital, online-multiplayer implementation of the 1822 board game (rules in `rules.pdf`).

## Structure

- `backend/` — Python rules engine + FastAPI/WebSocket game server.
  - `app/data/` — static game data transcribed from the rulebook (trains, phases,
    private/minor/major company tables, per-player-count setup values).
  - `app/engine/` — mutable game state models and setup/init logic. Stock round,
    operating round, auction, and map/routing logic land here next.
  - `app/rooms.py`, `app/main.py` — lobby + WebSocket room transport layer.
- `frontend/` — React + TypeScript (Vite) client. Currently a lobby (create/join/start
  a room) plus a raw JSON view of game state; map/board rendering is the next milestone.

## Status

Early scaffold. Working: game setup (shuffled stacks, bid boxes, starting cash/certificate
limits per player count), lobby + WebSocket room sync. Not yet implemented: stock round
actions (bidding, buying/selling shares), operating round actions (tile-laying, routing,
train runs, dividends), the hex map itself, and company acquisition/merger logic.

## Running locally

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                      # run tests
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env        # points at the local backend
npm run dev
```
