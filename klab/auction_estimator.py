"""Comp-based next-auction price estimator -- a separate exercise from the
rest of klab/, built 2026-08-13 at Josh's request after a trade review
raised a real question the existing model doesn't answer.

**What this is not.** `board.py`'s `redraft_value` is a regression-based
FAIR-VALUE estimate: it answers "what should a player with this production
be worth, on average, given how this league's money has behaved
historically." It does not know that name recognition, a big recent year,
positional scarcity panic, or a specific owner's blind spot move real
auction prices around that fair value. Nothing in `board.py`, `auction.py`,
or `keeper.py` is touched by this module, and nothing here feeds back into
those numbers -- this is deliberately a second, independent estimate, not a
correction to the first one.

**What this is.** For a target player, find the K most similar historical
auction purchases from this league's own 677-purchase, five-season record
(`out/auction_sample.csv`) by production profile and position, and ask: did
players like this typically sell for more or less than a pure production
regression would have predicted, in the season they were actually bought?
That premium/discount -- the part of the price the production regression
alone can't explain -- is applied to the target's own `redraft_value` to
produce a comp-adjusted estimate, reported as a range with the comp list
attached so the estimate is auditable, not a black box.

**Known limitation, stated up front.** There is no age or debut-year data
anywhere in `data/` (checked directly -- no file has an age/birthdate
column), so age-based comps (a real, standard input for this kind of
estimate -- see the young-player-modeling research from this session) are
not possible without a new data source. Position and realized production
level are the only comp axes available. This is a real gap, not a silent
one.
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

    The premium is computed against a regression fit *separately for each
    season* (not pooled) -- deliberately not reusing `auction.py`'s
    keeper-adjusted exchange rate, which this project's own FINDINGS #19
    already flags as not causally identified. This tool needs "what did the
    market pay for this level of production that season," which a plain
    per-season OLS answers directly without inheriting that debate.
    """
    d = pd.read_csv(C.OUT / "auction_sample.csv")
    d = d[d["played"]].copy()
    d["pos_group"] = d["pos"].map(position_group)

    resid = pd.Series(index=d.index, dtype=float)
    predicted = pd.Series(index=d.index, dtype=float)
    for season, g in d.groupby("season"):
        # Auction salaries are right-skewed and floored at $1, not normally
        # distributed around a linear trend -- a plain OLS on raw dollars
        # gets pulled by the handful of $30-45 stars and systematically
        # over-predicts everyone else (checked directly: raw-dollar OLS gave
        # a median residual of -8% to -22% every season, only balanced to a
        # ~0 mean by a few huge positive outliers -- the "typical" comp
        # looked overpriced by construction, which would bias every
        # estimate this tool produces low). Fit on log(salary) instead.
        X = sm.add_constant(g["roto_points"])
        fit = sm.OLS(np.log(g["salary"]), X).fit()
        pred = np.exp(fit.predict(X))
        predicted.loc[g.index] = pred
        # premium as a fraction of predicted price, not a raw dollar diff,
        # so a $2 miss on a $3 player and a $10 miss on a $30 player don't
        # get treated as the same-sized signal.
        resid.loc[g.index] = (g["salary"] - pred) / pred.clip(lower=1.0)

    # Recenter each season's premium to its own median rather than trust
    # either regression's absolute calibration. Checked both: raw-dollar OLS
    # has a systematically negative median (pulled positive only by a few
    # $30+ stars); log-salary OLS has a systematically POSITIVE median
    # instead (the classic retransformation/Jensen's-inequality bias from
    # exponentiating a log-scale fit back to dollars). Neither center is
    # trustworthy on its own. Recentering makes "premium" mean exactly what
    # it's supposed to mean -- relative to the TYPICAL player at this
    # production level that season, not relative to a regression line
    # that's biased one direction or the other by construction.
    for season, g in d.groupby("season"):
        resid.loc[g.index] -= resid.loc[g.index].median()

    d["predicted_salary"] = predicted
    d["premium_frac"] = resid
    return d


def _distance(pool: pd.DataFrame, target: pd.Series) -> pd.Series:
    """Normalized Euclidean distance in per-category roto-point space.
    Each axis is scaled by the comp pool's own spread so no single category
    (e.g. SV, which is usually near zero for most players) dominates."""
    scale = pool[PROFILE_COLS].std().replace(0, 1.0)
    # target is a row sliced from a mixed-dtype DataFrame (name/role are
    # strings), so the Series itself comes back as dtype=object even though
    # these particular values are floats -- cast explicitly or the object
    # dtype propagates into the subtraction and np.sqrt chokes on it.
    t = target[PROFILE_COLS].astype(float)
    diff = (pool[PROFILE_COLS] - t) / scale
    return np.sqrt((diff ** 2).sum(axis=1))


def find_comps(target: pd.Series, role: str, pos_group: str,
               k: int = 15) -> pd.DataFrame:
    """K nearest comps by production-profile distance. Prefers same
    position group; falls back to the full role if that group is too thin
    to say anything (this league is small -- 677 purchases over 5 seasons
    -- so a tight position+profile filter can leave single digits)."""
    pool = comp_pool()
    pool = pool[pool["role"] == role].copy()

    same_pos = pool[pool["pos_group"] == pos_group]
    used_pool = same_pos if len(same_pos) >= k else pool
    fallback = len(same_pos) < k

    d = _distance(used_pool, target)
    comps = used_pool.assign(distance=d).nsmallest(k, "distance")
    comps.attrs["fallback_to_full_role"] = fallback
    comps.attrs["n_same_position"] = len(same_pos)
    return comps


def estimate_auction_price(name: str, players: pd.DataFrame,
                           k: int = 15, role: str | None = None) -> dict:
    """Comp-adjusted next-auction price estimate for one player.

    `players` must have the columns in PROFILE_COLS plus roto_points,
    redraft_value, role, and fg_id -- i.e. `out/player_values_2027.csv`,
    or the keeper board.

    `role` disambiguates a name that resolves to more than one row -- a
    true two-way player (config.TWO_WAY_SPLIT_NAMES) has separate HIT and
    PIT rows sharing one name from 2027 on (see
    klab.board.project_all_players). Omitting it keeps the old
    first-match behavior for every other name, which still only ever
    resolves to one row.
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

    comps = find_comps(row, row["role"], pg, k=k)
    premiums = comps["premium_frac"]

    base = float(row["redraft_value"])
    lo = base * (1 + premiums.quantile(0.25))
    mid = base * (1 + premiums.median())
    hi = base * (1 + premiums.quantile(0.75))

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
        "comps": comps[["season", "player", "team", "salary", "pos",
                        "roto_points", "predicted_salary", "premium_frac",
                        "distance"]].reset_index(drop=True),
    }
