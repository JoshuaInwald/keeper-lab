"""Comp-based next-auction price estimator -- a separate exercise from the
rest of klab/. Nothing here feeds back into board.py/auction.py/keeper.py.

`board.py`'s `redraft_value` is a regression FAIR-VALUE estimate; real
auction prices move around it (name recognition, a big recent year, owner
blind spots). This module finds the K most similar historical purchases
from `out/auction_sample.csv` by production profile and position and
reports what they actually sold for, with the comp list attached.

Known limitation: no age/debut-year data exists in `data/`, so age-based
comps are not possible; position and production level are the only axes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import config as C
from .io import cached

PROFILE_COLS = ["rp_R", "rp_HR", "rp_RBI", "rp_SB", "rp_AVG",
                "rp_W", "rp_SV", "rp_K", "rp_ERA", "rp_WHIP"]

POSITION_GROUPS = {
    "C": "C", "1B": "CI", "3B": "CI", "CI": "CI",
    "2B": "MI", "SS": "MI", "MI": "MI",
    "LF": "OF", "CF": "OF", "RF": "OF", "OF": "OF",
    "U": "UTIL", "DH": "UTIL",
    "SP": "SP", "P": "SP", "RP": "RP",
}


def position_group(pos: str) -> str:
    return POSITION_GROUPS.get(str(pos).strip().upper(), "UNKNOWN")


@cached
def comp_pool() -> pd.DataFrame:
    """Every historical auction purchase, with a position group and a
    per-season market-premium residual attached.

    The premium regression is fit per season, not reusing `auction.py`'s
    keeper-adjusted exchange rate (not causally identified, FINDINGS #19).
    """
    d = pd.read_csv(C.OUT / "auction_sample.csv")
    d = d[d["played"]].copy()
    d["pos_group"] = d["pos"].map(position_group)

    resid = pd.Series(index=d.index, dtype=float)
    predicted = pd.Series(index=d.index, dtype=float)
    for season, g in d.groupby("season"):
        # Fit on log(salary): raw-dollar OLS is pulled by the $30-45 stars
        # and over-predicts everyone else (median residual -8% to -22%).
        X = sm.add_constant(g["roto_points"])
        fit = sm.OLS(np.log(g["salary"]), X).fit()
        pred = np.exp(fit.predict(X))
        predicted.loc[g.index] = pred
        # premium as a fraction of predicted price, not a raw dollar diff
        resid.loc[g.index] = (g["salary"] - pred) / pred.clip(lower=1.0)

    # Recenter each season's premium to its own median: neither raw-dollar
    # (negative median) nor log-fit (positive, retransformation bias) is centred.
    for season, g in d.groupby("season"):
        resid.loc[g.index] -= resid.loc[g.index].median()

    d["predicted_salary"] = predicted
    d["premium_frac"] = resid

    # Prior purchases of this player before this row's season (0 = first
    # sale), so debuts aren't comped against proven veterans. fg_id == -1
    # (unmatched draft placeholder) is not one player; left at 0.
    d = d.sort_values("season")
    real = d["fg_id"] != -1
    d["appearances_to_date"] = 0
    d.loc[real, "appearances_to_date"] = d[real].groupby("fg_id").cumcount()
    return d


def _distance(pool: pd.DataFrame, target: pd.Series) -> pd.Series:
    """Normalized Euclidean distance in per-category roto-point space.
    Each axis is scaled by the comp pool's own spread so no single category
    (e.g. SV, which is usually near zero for most players) dominates."""
    scale = pool[PROFILE_COLS].std().replace(0, 1.0)
    # target is an object-dtype row from a mixed frame; cast or np.sqrt chokes
    t = target[PROFILE_COLS].astype(float)
    diff = (pool[PROFILE_COLS] - t) / scale
    return np.sqrt((diff ** 2).sum(axis=1))


def player_tenure(fg_id: int) -> int:
    """Times this player has been bought in this league's auction history
    (0 = his next sale would be his first); feeds find_comps()."""
    pool = comp_pool()
    return int((pool["fg_id"] == fg_id).sum())


def find_comps(target: pd.Series, role: str, pos_group: str,
               k: int = 15, target_is_first_timer: bool = False) -> pd.DataFrame:
    """K nearest comps by production-profile distance. Prefers same
    position group, falling back to the full role if fewer than `k` exist.

    `target_is_first_timer` (`player_tenure()` == 0): prefer other
    first-timers, same fallback rule -- a debut sale is a different market
    than an established player's identical line, and without this a rookie
    closer got comped against proven $30+ closers."""
    pool = comp_pool()
    pool = pool[pool["role"] == role].copy()

    same_pos = pool[pool["pos_group"] == pos_group]
    used_pool = same_pos if len(same_pos) >= k else pool
    fallback = len(same_pos) < k

    tenure_filtered = False
    if target_is_first_timer:
        first_timers = used_pool[used_pool["appearances_to_date"] == 0]
        if len(first_timers) >= k:
            used_pool = first_timers
            tenure_filtered = True

    d = _distance(used_pool, target)
    comps = used_pool.assign(distance=d).nsmallest(k, "distance")
    comps.attrs["fallback_to_full_role"] = fallback
    comps.attrs["n_same_position"] = len(same_pos)
    comps.attrs["tenure_filtered"] = tenure_filtered
    return comps


def estimate_auction_price(name: str, players: pd.DataFrame,
                           k: int = 15, role: str | None = None) -> dict:
    """Comp-adjusted next-auction price estimate for one player.

    `players` must have the columns in PROFILE_COLS plus roto_points,
    redraft_value, role, and fg_id -- i.e. `klab.board.value_players()`'s
    frame, or the keeper board. `role` disambiguates a two-way player
    (config.TWO_WAY_SPLIT_NAMES) whose name resolves to HIT and PIT rows.
    """
    from .keeper import position_map

    row = players[players["name"] == name]
    if role is not None:
        row = row[row["role"] == role]
    if not len(row):
        raise ValueError(f"'{name}' not found")
    row = row.iloc[0]

    pmap = position_map()
    pos = pmap.get(int(row["fg_id"]), "UNKNOWN")
    pg = position_group(pos)

    first_timer = player_tenure(int(row["fg_id"])) == 0
    comps = find_comps(row, row["role"], pg, k=k, target_is_first_timer=first_timer)

    # Use the comps' own real salaries as the anchor, never
    # redraft_value * (1 + premium): a percentage on top of an extrapolated
    # fair value stayed runaway ($64 for a pitcher in a league that never
    # paid one more than $34) -- docs/FINDINGS.md, 2026-08-15.
    lo = comps["salary"].quantile(0.25)
    mid = comps["salary"].median()
    hi = comps["salary"].quantile(0.75)
    base = float(row["redraft_value"])  # kept on the return value for context/audit

    return {
        "name": name, "role": row["role"], "position": pos,
        "position_group": pg, "roto_points": float(row["roto_points"]),
        "regression_fair_value": base,
        "comp_adjusted_low": max(1.0, lo),
        "comp_adjusted_mid": max(1.0, mid),
        "comp_adjusted_high": max(1.0, hi),
        "n_comps": len(comps),
        "fallback_to_full_role": bool(comps.attrs["fallback_to_full_role"]),
        "n_same_position_available": int(comps.attrs["n_same_position"]),
        "target_is_first_timer": first_timer,
        "tenure_filtered": bool(comps.attrs["tenure_filtered"]),
        "comps": comps[["season", "player", "team", "salary", "pos",
                        "roto_points", "predicted_salary", "premium_frac",
                        "distance", "appearances_to_date"]].reset_index(drop=True),
    }
