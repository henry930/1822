# Rulings by rules owner (2026-11-21)

Provisional decisions confirmed (keep as implemented): 
1. Minor face value = 100. 2. Phase-2 minor start price = highest start value <= half the bid, min 50. 3. Minor bid flow (player pays full; treasury 100 / 2x price / full bid by phase; bank covers difference). 4. LNWR conversion: bank pays whole start price, player pays nothing. 5. Director succession per 4.4.2 as implemented (>=2 units, LNWR 1, more than seller; tie -> nearest after seller). 7. Train export: 4.11.6 exports count as L, no phase trigger; 4.11.7 exports go through phase/rust check. 8. Unaffordable winner passes to next affordable bidder; none -> stays in box, no export. 
11-14. Deferred: P16 exceptions, P9 exception, 4.8 direct formation, 5.12.13 arrows. 
15. Market data left-aligned / short top columns: confirmed as is. 17. "100% in players' hands" = treasury and bank pool both 0: confirmed.

Changed decisions (require code/contract change):
- 6. A round with only bids is NOT a sale for rule 10.1.1. bidding.place_or_move_bid must NOT set any_sale_this_stock_round (contract v2 item 1 is reversed). Legacy tests assuming a bid-only first round continues will need updating.
- 9. From phase 5, concessions left in bid boxes are removed (cleared).
- 10. 4.4.7: a player over the certificate limit after selling is forced to discard (sell) down to the limit. Needs implementation.
- 16. sell_shares sets any_sale_this_stock_round (selling is a trade).
