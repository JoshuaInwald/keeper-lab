"""Precomputed trade suggestions, three scenarios per team pair.

Built 2026-08-13, a deliberately separate exercise from the interactive
trade evaluator (`klab/trade.py`) it's built on top of -- this module
*searches* for trades instead of scoring one you already have in mind.

**Why precomputed, not live.** The app is a single static HTML file with no
server (see `README.md`'s whole pitch), and only one thing is re-implemented
in JS for exactly that reason. A real search — even the bounded one here —
is a few thousand `evaluate_trade()` calls; that's a build-time cost, not a
click-time one. `scripts/build_trade_suggestions.py` runs this for every
team pair and writes `out/trade_suggestions.json`; `build_app.py` ships the
result as static data, same as everything else in the payload.

**The three scenarios**, and why these three specifically: they're the
three shapes a real fantasy trade actually takes, not an arbitrary menu.

1. **Win-now for future** — one team is competing, one isn't. The
   contender sends a real multi-year keeper for the other team's best
   rest-of-season rental (prioritizing players who cost the seller nothing
   long-term — `F`-contract players especially, who are confirmed heading
   to free agency anyway per `out/FINDINGS.md` #39).
2. **Challenge trade** — both teams are live in the 2026 race but have
   complementary category profiles (one's stacked in HR, thin in SB; the
   other's the reverse). Swapping a player each can raise BOTH teams'
   standings points simultaneously, at little or no dollar cost.
3. **Mutual value swap** — both teams are effectively out of 2026 contention
   and each has a player the other's roster construction values more than
   its own does. A dynasty-style trade: both sides' multi-year surplus goes
   up, current-season standings barely move either way.

**One shared search, three scores.** All three scenarios draw candidates
from the same shortlist (each team's top players by `roto_points`, contract
status agnostic -- Scenario 1 specifically wants rental-only `F` players in
the pool) and evaluate the same 1-for-1 combinations through
`evaluate_trade()` once. Only the SCORING differs per scenario. This is 3x
cheaper than three independent searches and is honest about what's
happening: these are three different lenses on the same real trade market
between two teams, not three unrelated searches.

**What this doesn't do.** Multi-player packages (2-for-1, 2-for-2) are not
searched — 1-for-1 keeps the combinatorics small enough to run for all 45
team pairs in a reasonable build step, and a clean single-player suggestion
is also the most legible starting point for two managers actually talking.
Nothing stops a human from building a bigger package around a suggestion
this surfaces.
"""
from __future__ import annotations

import pandas as pd

from .trade import evaluate_trade

SHORTLIST_SIZE = 10
STANDINGS_GAP_FOR_WIN_NOW = 8.0   # points apart before we call one side a seller


def _shortlist(board: pd.DataFrame, team: str, n: int = SHORTLIST_SIZE) -> list[str]:
    """Union of top-n by roto_points (talent -- catches rentals, since an
    F-contract player's talent doesn't disappear even though his keeper
    value is zero) and top-n by surplus_multiyear (real trade chips).
    Talent-only was too narrow: a team can easily have 6+ of its top-10
    talents be unkeepable F-contract rentals, which crowds out the actual
    keepers a trade partner would want in return -- checked directly on
    Spehr's Army, which is exactly this shape."""
    t = board[board["team"] == team]
    by_talent = set(t.nlargest(n, "roto_points")["name"])
    by_value = set(t.nlargest(n, "surplus_multiyear")["name"])
    # Sorted, not just de-duplicated: iterating a raw set is order-unstable
    # across processes (Python randomises string hashing per run), and the
    # scenario pickers below break ties on first-seen-wins. An unsorted
    # shortlist made suggest_trades() silently return a different, sometimes
    # worse, "best" trade on every identical rerun -- see FINDINGS.md #41.
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
    surplus = board.set_index("name")["surplus_multiyear"]
    best = None
    for r in results:
        buyer_gain = r["a_standings_delta"] if buyer == team_a else r["b_standings_delta"]
        seller_gain = r["a_surplus_delta"] if seller == team_a else r["b_surplus_delta"]
        # incoming_to_seller: the specific player the seller receives -- not
        # just "is the net delta positive," which a trade like "bad $35
        # contract for a $0 throwaway" can satisfy without the seller
        # actually getting anything of value (checked directly: this exact
        # failure mode showed up testing NPB/Spehr's Army -- Guerrero Jr.
        # for James Wood scored positive purely because Guerrero's own
        # surplus was so negative, not because Wood is a real asset).
        incoming_to_seller = r["b_sends"] if seller == team_a else r["a_sends"]
        if seller_gain <= 0 or surplus.get(incoming_to_seller, 0.0) <= 0:
            continue
        # Tie-break on seller_gain: buyer_gain alone ties often (many
        # rentals move the buyer's standings by the same amount), and
        # picking the first tie encountered means the shortlist's iteration
        # order silently decides the answer. See FINDINGS.md #41.
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
    """Score is (min(a,b), sum(a,b)): min is the real criterion -- neither
    side should be shortchanged -- but ties on min are common (many
    candidates move one side's standings by the exact same amount), and the
    sum breaks the tie toward the Pareto-better candidate instead of
    whichever the shortlist happened to reach first. See FINDINGS.md #41."""
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
    scenario. Any scenario that finds nothing clearing its bar returns None
    for that key -- not every pair has a real challenge trade or a real
    seller, and forcing one would ship a bad suggestion as if it were real."""
    results = _search_pair(board, exch, team_a, team_b, standings_pts)
    return {
        "team_a": team_a, "team_b": team_b,
        "win_now_for_future": _pick_win_now(board, results, team_a, team_b, standings_pts),
        "challenge_trade": _pick_challenge(results, team_a, team_b),
        "mutual_value_swap": _pick_mutual_value(results, team_a, team_b),
    }
