"""Helpers for reading/placing company tokens on the stock market grid
(app.data.stock_market), and the rule 1.6.2 "descending share price order"
comparison it feeds into (used for operating-round turn order, rule 5.2).
"""
from __future__ import annotations

from app.data.stock_market import STOCK_MARKET_BY_POSITION

from .models import GameState


def cell_value(row: int, col: int) -> int:
    return STOCK_MARKET_BY_POSITION[(row, col)].value


def company_value(state: GameState, company_id: str) -> int:
    row, col = state.stock_positions[company_id]
    return cell_value(row, col)


def place_token(state: GameState, company_id: str, row: int, col: int) -> None:
    """Place (or move) a company's token onto a cell, appending to that
    cell's stack (rule 4.12.2/5.19.2: a token moving onto an occupied cell
    goes to the *bottom* of that cell's stack)."""
    old_pos = state.stock_positions.get(company_id)
    if old_pos is not None:
        stack = state.stock_stack.get(old_pos)
        if stack and company_id in stack:
            stack.remove(company_id)

    state.stock_positions[company_id] = (row, col)
    state.stock_stack.setdefault((row, col), []).append(company_id)


def descending_price_key(state: GameState, company_id: str):
    """Sort key for rule 1.6.2/5.2.2 "descending share price order": higher
    value first, then rightmost column, then topmost in that cell's stack."""
    row, col = state.stock_positions[company_id]
    value = cell_value(row, col)
    stack = state.stock_stack.get((row, col), [])
    stack_rank = stack.index(company_id) if company_id in stack else 0
    return (-value, -col, stack_rank)
