"""Uncertainty bands on every dollar figure.

The denominators are estimated from a small number of team-seasons, and the
bootstrap says the typical one is good to about ±38%. Until now that number
lived in a footnote. This module propagates it to the quantity you actually
act on: what a player is worth, and whether his contract has surplus.

**Why this is cheap, and exact.** Roto points are *linear in one over the
denominator* in every category:

    counting:  rp_cat = stat / d_cat
    rate:      rp_AVG = (team_AVG_with_him − league_AVG) / d_AVG

and the denominator is `sigma_rel × level × c_n/(n−1)`, of which only
`sigma_rel` is resampled. So a bootstrap draw is a per-category rescaling of
the already-computed `rp_*` columns:

    rp_cat(draw) = rp_cat(point) × sigma_0(cat) / sigma_b(cat)

No re-projection, no re-fit, no approximation in the scoring step. A thousand
draws is a thousand multiplications of a 2,000 × 10 matrix.

**Where it is approximate**, stated plainly:

1. The 2028 valuation is shocked by each player's own 2027 ratio rather than
   rescored from its own category lines, which the board does not store. Same
   player, same categories, so the shock is close to right.
2. Replacement level and the $2,600 calibration are recomputed inside every
   draw, so the budget identity holds in each one. That is deliberate: it
   means the bands describe *relative* mispricing, not a leaguewide inflation
   of every value at once.
3. It is uncertainty in **how to score a stat line**, not in the stat line.
   Projection error is separate and additional.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .board import build_board, value_players
from .io import cached, load_standings_long
from .keeper import multiyear_surplus


def _pools(seasons=None) -> dict:
    """The pooled, mean-normalised team-season deviations, per category.

    Must apply exactly the filters `pooled_relative_dispersion` applies, or
    the bands describe a different estimator than the point values do.
    """
    st = load_standings_long()
    seasons = seasons or C.DENOM_SEASONS
    out = {}
    for cat, g in st.groupby("category"):
        if cat not in C.CATS:
            continue
        vals = []
        for s in seasons:
            if cat == "SB" and s < C.SB_REGIME_START:
                continue
            if (C.DENOM_EXCLUDE_PARTIAL_SEASON and cat in C.PARTIAL_EXCLUDE_CATS
                    and s in C.PARTIAL_SEASONS):
                continue
            v = g[g["season"] == s]["total"].astype(float).values
            if cat == "SV":
                v = v[v >= C.SV_PUNT_THRESHOLD]
            if len(v) < 3:
                continue
            vals.append(v / v.mean())
        if vals:
            out[cat] = np.concatenate(vals)
    return out


@cached
def bootstrap_bands(B: int = 1000, seed: int = 0,
                    lo_pct: float = 10.0, hi_pct: float = 90.0) -> pd.DataFrame:
    """Per-player dollar bands, indexed by `fg_id`.

    Returns lo/hi on `redraft_value` and on `surplus_multiyear`, plus the
    share of draws in which the player is still worth keeping. That last
    column is the one that matters: a player whose surplus is positive in 96%
    of draws is a different decision from one who is positive in 55%.
    """
    rng = np.random.default_rng(seed)
    players, exch, meta = value_players()
    board, _, _ = build_board()

    pools = _pools()
    cats = [c for c in C.CATS if c in pools]
    sigma0 = np.array([pools[c].std(ddof=1) for c in cats])

    rp = players[[f"rp_{c}" for c in cats]].fillna(0.0).to_numpy(float)
    n_rostered = C.N_TEAMS * C.N_ACTIVE
    dollars_above_min = C.N_TEAMS * C.BUDGET - n_rostered * 1.0
    rank = C.WAIVER_RANK.get(C.WAIVER_VALUE, n_rostered)

    ids = players["fg_id"].to_numpy()
    pos = {int(f): i for i, f in enumerate(ids)}
    keep_idx = np.array([pos[int(f)] for f in board["fg_id"] if int(f) in pos])
    keep_ids = np.array([int(f) for f in board["fg_id"] if int(f) in pos])

    b = board.set_index("fg_id")
    v27_0 = b.loc[keep_ids, "redraft_value"].to_numpy(float)
    v28_0 = b.loc[keep_ids, "redraft_value_2028"].to_numpy(float)
    cost = b.loc[keep_ids, "keeper_cost"].astype(float)
    years = b.loc[keep_ids, "years_controlled"].astype(float)
    salary = b.loc[keep_ids, "salary"].astype(float)
    keepable = b.loc[keep_ids, "keepable"].to_numpy(bool)

    v27_draws = np.empty((B, len(keep_ids)))
    my_draws = np.empty((B, len(keep_ids)))

    for d in range(B):
        sig_b = np.array([pools[c][rng.integers(0, len(pools[c]), len(pools[c]))]
                          .std(ddof=1) for c in cats])
        tot = rp @ (sigma0 / sig_b)

        # replacement level and the $2,600 calibration, refit inside the draw
        order = np.sort(tot)[::-1]
        repl = float(C.WAIVER_HIGH_RP) if C.WAIVER_VALUE == "high" else float(order[rank - 1])
        pool_rp = float(order[:n_rostered].sum() - repl * n_rostered)
        usd = dollars_above_min / pool_rp
        val = np.clip((tot - repl) * usd + 1.0, 0.0, None)

        v27 = val[keep_idx]
        # 2028 is shocked by the player's own 2027 ratio (see module docstring)
        shock = np.where(v27_0 > 0, v27 / np.where(v27_0 > 0, v27_0, 1.0), 1.0)
        v28 = v28_0 * shock

        my = multiyear_surplus(pd.Series(v27, index=keep_ids),
                               pd.Series(v28, index=keep_ids),
                               cost, years, salary)["surplus_multiyear"].to_numpy()
        v27_draws[d] = v27
        my_draws[d] = np.where(keepable, my, 0.0)

    # Unkeepable players are all-NaN by construction; percentile them separately
    # rather than letting numpy warn on every empty slice.
    s_lo = np.full(len(keep_ids), np.nan)
    s_hi = np.full(len(keep_ids), np.nan)
    p_pos = np.full(len(keep_ids), np.nan)
    if keepable.any():
        k = np.where(keepable)[0]
        s_lo[k] = np.percentile(my_draws[:, k], lo_pct, axis=0)
        s_hi[k] = np.percentile(my_draws[:, k], hi_pct, axis=0)
        p_pos[k] = (my_draws[:, k] > 0).mean(axis=0)

    out = pd.DataFrame({
        "fg_id": keep_ids,
        "value_lo": np.percentile(v27_draws, lo_pct, axis=0),
        "value_hi": np.percentile(v27_draws, hi_pct, axis=0),
        "surplus_lo": s_lo, "surplus_hi": s_hi, "p_surplus_positive": p_pos,
    }).set_index("fg_id")
    out.attrs["B"] = B
    out.attrs["interval"] = (lo_pct, hi_pct)
    return out
