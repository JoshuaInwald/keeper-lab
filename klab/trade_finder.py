"""Precomputed trade suggestions, three scenarios per team pair.

Searches for 1-for-1 trades on top of `klab/trade.py`'s evaluator.
Precomputed at build time (`scripts/build_trade_suggestions.py` writes
`out/trade_suggestions.json`) because the app is static HTML with no server.

Scenarios: (1) win-now for future -- a contender sends a multi-year keeper
for a seller's best rental (F-contract players especially, FINDINGS #39);
(2) challenge trade -- both live in 2026 with complementary categories, both
gain standings points; (3) mutual value swap -- both out of contention, both
gain multi-year surplus. One shared shortlist and one evaluate_trade() pass
per pair; only the scoring differs. Multi-player packages are not searched.
"""
from __future__ import annotations

import pandas as pd

from .trade import evaluate_trade

SHORTLIST_SIZE = 10
STANDINGS_GAP_FOR_WIN_NOW = 8.0   # points apart before we call one side a seller


def _shortlist(board: pd.DataFrame, team: str, n: int = SHORTLIST_SIZE) -> list[str]:
    """Union of top-n by roto_points (catches F-contract rentals) and top-n
    by surplus_multiyear (real keepers); talent-only let rentals crowd out
    the keepers a partner would want."""
    t = board[board["team"] == team]
    # groupby: a split player's two rows must rank as one combined asset or
    # he falls out of both top-n lists at half strength (FINDINGS #80).
    agg = t.groupby("name")[["roto_points", "surplus_multiyear"]].sum()
    by_talent = set(agg.nlargest(n, "roto_points").index)
    by_value = set(agg.nlargest(n, "surplus_multiyear").index)
    # Sorted: set iteration order varies per process and the pickers break
    # ties first-seen-wins, so reruns silently differed (FINDINGS #41).
    return sorted(by_talent | by_value)


def _search_pair(board: pd.DataFrame, exch: dict, team_a: str, team_b: str,
                 standings_pts: dict) -> list[dict]:
    """Evaluate every 1-for-1 combination from each team's shortlist once,
    returning the raw results for scenario scoring to pick over."""
    a_list = _shortlist(board, team_a)
    b_list = _shortlist(board, team_b)
    usd_per_point = exch["usd_per_point"]

    results = []
    for a_player in a_list:
        for b_player in b_list:
            try:
                res = evaluate_trade(board, team_a, team_b, [a_player], [b_player],
                                     usd_per_point=usd_per_point)
            except ValueError:
                continue     # ambiguous/unresolved name, skip rather than crash a batch job
            results.append({
                "a_sends": a_player, "b_sends": b_player,
                "a_surplus_delta": res["a"]["d_surplus_multiyear"],
                "b_surplus_delta": res["b"]["d_surplus_multiyear"],
                "a_standings_delta": res["a"]["d_standings_points_2026"],
                "b_standings_delta": res["b"]["d_standings_points_2026"],
            })
    return results


def _pick_win_now(board: pd.DataFrame, results: list[dict], team_a: str, team_b: str,
                  standings_pts: dict) -> dict | None:
    gap = standings_pts[team_a] - standings_pts[team_b]
    if abs(gap) < STANDINGS_GAP_FOR_WIN_NOW:
        return None    # neither side is clearly buying or selling
    buyer, seller = (team_a, team_b) if gap > 0 else (team_b, team_a)
    # groupby, not set_index: a split player has two rows under one name and a
    # duplicate index makes .get() return a Series; his asset is the sum (FINDINGS #80).
    surplus = board.groupby("name")["surplus_multiyear"].sum()
    best = None
    for r in results:
        buyer_gain = r["a_standings_delta"] if buyer == team_a else r["b_standings_delta"]
        seller_gain = r["a_surplus_delta"] if seller == team_a else r["b_surplus_delta"]
        # The seller must receive a positive-surplus player, not just a
        # positive net delta (dumping a bad contract for a $0 throwaway passes that).
        incoming_to_seller = r["b_sends"] if seller == team_a else r["a_sends"]
        if seller_gain <= 0 or surplus.get(incoming_to_seller, 0.0) <= 0:
            continue
        # Tie-break on seller_gain, or iteration order decides (FINDINGS #41).
        score = (buyer_gain, seller_gain)
        if best is None or score > best["_score"]:
            best = {**r, "_score": score, "buyer": buyer, "seller": seller}
    if best is None or best["_score"][0] <= 0:
        return None
    return {"scenario": "win_now_for_future", "buyer": best["buyer"], "seller": best["seller"],
            "a_sends": best["a_sends"], "b_sends": best["b_sends"],
            "buyer_standings_gain": round(best["_score"][0], 2),
            "seller_surplus_gain": round(
                best["a_surplus_delta"] if best["seller"] == team_a else best["b_surplus_delta"], 2)}


def _pick_challenge(results: list[dict], team_a: str, team_b: str) -> dict | None:
    """Score is (min(a,b), sum(a,b)): min so neither side is shortchanged,
    sum to break the frequent ties on min (FINDINGS #41)."""
    best = None
    for r in results:
        if r["a_standings_delta"] <= 0 or r["b_standings_delta"] <= 0:
            continue
        score = (min(r["a_standings_delta"], r["b_standings_delta"]),
                 r["a_standings_delta"] + r["b_standings_delta"])
        if best is None or score > best["_score"]:
            best = {**r, "_score": score}
    if best is None:
        return None
    return {"scenario": "challenge_trade", "a_sends": best["a_sends"], "b_sends": best["b_sends"],
            "a_standings_gain": round(best["a_standings_delta"], 2),
            "b_standings_gain": round(best["b_standings_delta"], 2)}


def _pick_mutual_value(results: list[dict], team_a: str, team_b: str) -> dict | None:
    """Same (min, sum) tie-break as _pick_challenge -- see its docstring."""
    best = None
    for r in results:
        if r["a_surplus_delta"] <= 0 or r["b_surplus_delta"] <= 0:
            continue
        score = (min(r["a_surplus_delta"], r["b_surplus_delta"]),
                 r["a_surplus_delta"] + r["b_surplus_delta"])
        if best is None or score > best["_score"]:
            best = {**r, "_score": score}
    if best is None:
        return None
    return {"scenario": "mutual_value_swap", "a_sends": best["a_sends"], "b_sends": best["b_sends"],
            "a_surplus_gain": round(best["a_surplus_delta"], 2),
            "b_surplus_gain": round(best["b_surplus_delta"], 2)}


def suggest_trades(board: pd.DataFrame, exch: dict, team_a: str, team_b: str,
                   standings_pts: dict) -> dict:
    """Up to three suggested trades between team_a and team_b, one per
    scenario; a scenario with nothing clearing its bar returns None."""
    results = _search_pair(board, exch, team_a, team_b, standings_pts)
    return {
        "team_a": team_a, "team_b": team_b,
        "win_now_for_future": _pick_win_now(board, results, team_a, team_b, standings_pts),
        "challenge_trade": _pick_challenge(results, team_a, team_b),
        "mutual_value_swap": _pick_mutual_value(results, team_a, team_b),
    }
