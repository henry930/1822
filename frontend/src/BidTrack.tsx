// A single bid box rendered like the physical 1822 bid-box board: a labelled
// card in the middle, framed top and bottom by the £-value loop track it sits
// on (rule 4.10 / 1.6), with a colored marker for each player showing where
// their current bid sits on that track.
import type { CSSProperties } from "react";

export type BidBoxItem = { kind: string; ref: number | string; bids: Record<string, number> };

// Loop tracks, transcribed from board.webp (see backend/app/data/bid_box_tracks.py):
// concession/minor boxes run 100->195 in steps of 5, private boxes run 0->95.
const CONCESSION_MINOR_LOOP: number[] = Array.from({ length: 20 }, (_, i) => 100 + 5 * i);
const PRIVATE_LOOP: number[] = Array.from({ length: 20 }, (_, i) => 5 * i);

// Cycled by the player's position in player_order, so a given seat keeps the
// same marker color across every bid box and stock-round view.
const PLAYER_COLORS = [
  "#c0392b", // red
  "#2c6e49", // green
  "#2e5eaa", // blue
  "#b45309", // amber
  "#7b3fa0", // purple
  "#0e7c86", // teal
  "#c2185b", // pink
  "#555555", // grey
];

export function playerColor(playerOrder: string[], engineId: string): string {
  const idx = playerOrder.indexOf(engineId);
  return PLAYER_COLORS[idx < 0 ? 0 : idx % PLAYER_COLORS.length];
}

function loopFor(kind: string): number[] {
  return kind === "private" ? PRIVATE_LOOP : CONCESSION_MINOR_LOOP;
}

function labelFor(kind: string, ref: number | string): string {
  if (kind === "concession") return String(ref); // major company abbr, e.g. "LNWR"
  if (kind === "minor") return `M${ref}`;
  return `P${ref}`;
}

function TrackRow({
  values,
  startIndex,
  bids,
  topBidder,
  playerOrder,
  nameFor,
}: {
  values: number[];
  startIndex: number;
  bids: Record<string, number>;
  topBidder: string | null;
  playerOrder: string[];
  nameFor: (id: string) => string;
}) {
  return (
    <div className="bid-track-row">
      {values.map((value, col) => {
        const i = startIndex === 0 ? col : 19 - col;
        const holders = Object.entries(bids).filter(([, amount]) => amount === value);
        return (
          <div className="bid-track-cell" key={i}>
            <span className="bid-track-value">{value}</span>
            <div className="bid-track-markers">
              {holders.map(([pid]) => (
                <span
                  key={pid}
                  className={`bid-track-marker${pid === topBidder ? " top" : ""}`}
                  style={{ "--marker-color": playerColor(playerOrder, pid) } as CSSProperties}
                  title={`${nameFor(pid)}: £${value}`}
                >
                  {nameFor(pid).slice(0, 2).toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function BidTrackCard({
  kind,
  boxIndex,
  item,
  playerOrder,
  nameFor,
  bidAmount,
  onBidAmountChange,
  onBid,
  disabled,
}: {
  kind: "concession" | "minor" | "private";
  boxIndex: number;
  item: BidBoxItem;
  playerOrder: string[];
  nameFor: (id: string) => string;
  bidAmount: string;
  onBidAmountChange: (v: string) => void;
  onBid: () => void;
  disabled: boolean;
}) {
  const loop = loopFor(kind);
  const topRow = loop.slice(0, 10);
  const bottomRow = loop.slice(10, 20).reverse();
  const topBidder =
    Object.keys(item.bids).length > 0
      ? Object.entries(item.bids).reduce((a, b) => (b[1] > a[1] ? b : a))[0]
      : null;
  const topAmount = topBidder ? item.bids[topBidder] : null;

  return (
    <div className={`bid-track-card kind-${kind}`}>
      <TrackRow
        values={topRow}
        startIndex={0}
        bids={item.bids}
        topBidder={topBidder}
        playerOrder={playerOrder}
        nameFor={nameFor}
      />
      <div className="bid-track-center">
        <div className="bid-track-header">
          <span className="bid-track-kind">{kind}</span>
          <span className="bid-track-label">{labelFor(kind, item.ref)}</span>
        </div>
        <div className="bid-track-shares">
          <span className="share-icon" />
          <span className="share-icon" />
          <span className="share-caption">
            {kind === "private" ? "Private company" : "Director's cert - two shares"}
          </span>
        </div>
        <div className="bid-track-top-bid">
          {topAmount != null ? (
            <>
              High bid <strong>£{topAmount}</strong> ({nameFor(topBidder!)})
            </>
          ) : (
            <span className="hint">no bids yet</span>
          )}
        </div>
        <div className="bid-track-controls">
          <input
            type="number"
            step={5}
            placeholder="amount"
            disabled={disabled}
            value={bidAmount}
            onChange={(e) => onBidAmountChange(e.target.value)}
          />
          <button onClick={onBid} disabled={disabled}>
            Bid
          </button>
        </div>
      </div>
      <TrackRow
        values={bottomRow}
        startIndex={10}
        bids={item.bids}
        topBidder={topBidder}
        playerOrder={playerOrder}
        nameFor={nameFor}
      />
      <div className="bid-track-index">#{boxIndex}</div>
    </div>
  );
}
