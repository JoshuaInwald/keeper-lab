"""Uncertainty bands on every dollar figure, from denominator uncertainty.

Roto points are linear in 1/denominator and only `sigma_rel` is resampled,
so a bootstrap draw is a per-category rescaling of the computed `rp_*`
columns: rp_cat(draw) = rp_cat(point) * sigma_0(cat) / sigma_b(cat).

Approximations: (1) 2028 is shocked by each player's own 2027 ratio;
(2) replacement level and the $2,600 calibration are refit inside every
draw, so bands describe relative mispricing; (3) this is uncertainty in how
to score a stat line, not in the line -- projection error is additional.
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
                    lo_pct: float = 10.0, hi_pct: float = 90.0,
                    exch: dict | None = None) -> pd.DataFrame:
    """Per-player dollar bands, indexed by (`fg_id`, `role`): lo/hi on
    `redraft_value` and `surplus_multiyear`, plus the share of draws in
    which the player is still worth keeping.

    `exch` overrides the exchange fit so the app's fit dropdown gets bands
    that describe the fit on screen (FINDINGS #82); a dict argument bypasses
    the cache, so a variant's bands never shadow the default's.
    """
    rng = np.random.default_rng(seed)
    players, dexch, meta = value_players()
    board, _, _ = build_board(exch=exch)
    exch = exch or dexch

    pools = _pools()
    cats = [c for c in C.CATS if c in pools]
    sigma0 = np.array([pools[c].std(ddof=1) for c in cats])

    rp = players[[f"rp_{c}" for c in cats]].fillna(0.0).to_numpy(float)
    n_rostered = C.N_TEAMS * C.N_ACTIVE
    dollars_above_min = C.N_TEAMS * C.BUDGET - n_rostered * 1.0
    rank = C.WAIVER_RANK.get(C.WAIVER_VALUE, n_rostered)
    # The draws must apply the same pool rule as value_players() or the bands
    # describe a different estimator than the point values (FINDINGS #80: they
    # kept the role-blind 230 after POOL_RULE went "slot_role" in #70). Since
    # #82 slot_role holds under every anchor; WAIVER_VALUE moves only the bar.
    slot_role = C.POOL_RULE == "slot_role"
    rank_h = round(rank * C.N_HIT_SLOTS / C.N_ACTIVE)
    rank_p = round(rank * C.N_PIT_SLOTS / C.N_ACTIVE)
    hit_mask = (players["role"] != "PIT").to_numpy()
    n_hit, n_pit = C.N_TEAMS * C.N_HIT_SLOTS, C.N_TEAMS * C.N_PIT_SLOTS

    # Keyed on (fg_id, role), not fg_id alone: a two-way player has two rows
    # per fg_id and a fg_id-only .loc duplicate-expanded them (shape mismatch).
    ids = players["fg_id"].to_numpy()
    roles = players["role"].to_numpy()
    pos = {(int(f), r): i for i, (f, r) in enumerate(zip(ids, roles))}
    board_keys = list(zip(board["fg_id"].astype(int), board["role"]))
    keep_idx = np.array([pos[k] for k in board_keys if k in pos])
    keep_pairs = [k for k in board_keys if k in pos]
    keep_ids = np.array([k[0] for k in keep_pairs])
    keep_roles = np.array([k[1] for k in keep_pairs])
    loc_key = list(zip(keep_ids, keep_roles))

    b = board.set_index(["fg_id", "role"])
    v27_0 = b.loc[loc_key, "redraft_value"].to_numpy(float)
    v28_0 = b.loc[loc_key, "redraft_value_2028"].to_numpy(float)
    # The surplus draws must run on the same scale as the shipped
    # surplus_multiyear (config.KEEP_BASIS): the app shows the band under that
    # headline, and redraft-basis draws under a keep-basis number were
    # describing a different quantity than they sat beside (FINDINGS #80).
    if C.KEEP_BASIS == "replacement":
        s27_0 = b.loc[loc_key, "keep_value"].to_numpy(float)
        s28_0 = b.loc[loc_key, "keep_value_2028"].to_numpy(float)
    else:
        s27_0, s28_0 = v27_0, v28_0
    # .set_axis(keep_ids): multiyear_surplus() aligns by label against plain
    # keep_ids Series; a MultiIndex here silently produced all-NaN surplus.
    cost = b.loc[loc_key, "keeper_cost"].astype(float).set_axis(keep_ids)
    years = b.loc[loc_key, "years_controlled"].astype(float).set_axis(keep_ids)
    salary = b.loc[loc_key, "salary"].astype(float).set_axis(keep_ids)
    keepable = b.loc[loc_key, "keepable"].to_numpy(bool)

    v27_draws = np.empty((B, len(keep_ids)))
    my_draws = np.empty((B, len(keep_ids)))

    for d in range(B):
        sig_b = np.array([pools[c][rng.integers(0, len(pools[c]), len(pools[c]))]
                          .std(ddof=1) for c in cats])
        tot = rp @ (sigma0 / sig_b)

        # replacement level and the $2,600 calibration, refit inside the draw
        if slot_role:
            th = np.sort(tot[hit_mask])[::-1][:n_hit]
            tp = np.sort(tot[~hit_mask])[::-1][:n_pit]
            # The bar per anchor, mirroring value_players(): fieldable
            # minimum ("low"), per-role deeper ranks ("medium"), or the
            # measured FA level as a role-blind constant ("high").
            if C.WAIVER_VALUE == "high":
                repl_h = repl_p = float(C.WAIVER_HIGH_RP)
            elif C.WAIVER_VALUE == "medium":
                repl_h = float(np.sort(tot[hit_mask])[::-1][rank_h - 1])
                repl_p = float(np.sort(tot[~hit_mask])[::-1][rank_p - 1])
            else:
                repl_h, repl_p = float(th[-1]), float(tp[-1])
            pool_rp = float(np.clip(th - repl_h, 0.0, None).sum()
                            + np.clip(tp - repl_p, 0.0, None).sum())
            repl_vec = np.where(hit_mask, repl_h, repl_p)
        else:
            order = np.sort(tot)[::-1]
            repl = float(C.WAIVER_HIGH_RP) if C.WAIVER_VALUE == "high" else float(order[rank - 1])
            pool_rp = float(order[:n_rostered].sum() - repl * n_rostered)
            repl_vec = repl
        usd = dollars_above_min / pool_rp
        val = np.clip((tot - repl_vec) * usd + 1.0, 0.0, None)

        v27 = val[keep_idx]
        # Surplus on the KEEP_BASIS scale; the exchange fit is held fixed
        # across draws (refitting it per draw would mean rebuilding the
        # auction sample; its own error is reported separately, ~+/-40%, #7).
        if C.KEEP_BASIS == "replacement":
            s27 = np.clip((tot - exch["intercept"]) / exch["slope"], 0.0, None)[keep_idx]
        else:
            s27 = v27
        # 2028 is shocked by the player's own 2027 ratio (see module docstring)
        shock = np.where(s27_0 > 0, s27 / np.where(s27_0 > 0, s27_0, 1.0), 1.0)
        s28 = s28_0 * shock

        my = multiyear_surplus(pd.Series(s27, index=keep_ids),
                               pd.Series(s28, index=keep_ids),
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
        "role": keep_roles,
        "value_lo": np.percentile(v27_draws, lo_pct, axis=0),
        "value_hi": np.percentile(v27_draws, hi_pct, axis=0),
        "surplus_lo": s_lo, "surplus_hi": s_hi, "p_surplus_positive": p_pos,
    }).set_index(["fg_id", "role"])
    out.attrs["B"] = B
    out.attrs["interval"] = (lo_pct, hi_pct)
    return out
