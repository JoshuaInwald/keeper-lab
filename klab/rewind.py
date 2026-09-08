"""A valuation board for a season that has already been played, built only from
data that existed before it.

Why this exists. `docs/FINDINGS.md` #66 scored the OWNERS on 336 past keeper
decisions and could not score the MODEL, because `board.py` is a 2027 object:
its projection, its denominators and its dollar scale all read the current
files. "Would the model have beaten the room" is the product's central claim and
it has never been tested. The Marcel archive (#67) supplies the missing half, an
honest ex-ante projection for 2024, 2025 and 2026, so the board can be rewound.

WHAT IS REWOUND AND WHAT IS NOT

Rewound, because using post-season information here would leak the answer:
  projection    Marcel FOR the season (#67), never that season's actuals
  dispersion    `pooled_relative_dispersion` over completed seasons BEFORE it
  league level  mean of the two completed seasons before it, mirroring how
                LEVEL_SEASONS = [2024, 2025] feeds a 2027 board
  baselines     `team_baselines` over those same two seasons
  field size    `teams_per_category` over the seasons before it

NOT rewound, deliberately:
  the $2,600 budget identity and the 14/9 roster shape are league rules, not
  estimates, and they did not change over the window.

The auction exchange rate is not rewound either, because it is not used. The
keep/cut call runs off `surplus_redraft` (`board.mark_optimal_keepers`), and
`redraft_value` is calibrated against the league's $2,600 of cap space rather
than against the auction regression. That keeps `fit_exchange_rate`'s
keeper-count machinery (`KEEPERS_REMOVED`, `KEEPERS_EXPECTED_2027`) out of the
backtest entirely. Any future work that needs `keep_value` out of sample has to
rewind that fit too, and it is genuinely harder.

THE POOL RULE IS A PARAMETER, ON PURPOSE

`pool_rule` selects the set the dollar scale is calibrated on. #65 found the
production rule ("blind") picks 183 hitters and 47 pitchers out of a 2027
projection, and #68 found that is general to projections rather than a ZiPS
artefact. #68 also showed the repair #65 rejected ("slot_role") is the one that
reproduces perfect foresight. Making the rule an argument is what lets the
backtest DECIDE between them on keep/cut accuracy instead of on that argument.

    from klab.rewind import rewound_board
    b = rewound_board(2025, pool_rule="slot_role")
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .denoms import (RotoScorer, denominators_for_level,
                     pooled_relative_dispersion, season_levels,
                     team_baselines, teams_per_category)
from .io import cached, load_standings_long
from .marcel import SEASONS as MARCEL_SEASONS, marcel_fg_ids

POOL_RULES = ("blind", "slot_role", "slot_pooled")

N_POOL = C.N_TEAMS * C.N_ACTIVE               # 230
N_HIT_FIELDABLE = C.N_TEAMS * C.N_HIT_SLOTS   # 140
N_PIT_FIELDABLE = C.N_TEAMS * C.N_PIT_SLOTS   # 90


def prior_seasons(season: int, n: int | None = None) -> list[int]:
    """Completed seasons before `season`, most recent first, optionally the n
    most recent. Raises rather than silently returning a short list: a board
    quietly fitted on one season would look fine and be badly estimated.
    """
    have = sorted(int(s) for s in load_standings_long()["season"].unique())
    before = [s for s in have if s < season]
    if not before:
        raise ValueError(f"no completed seasons before {season} in the standings")
    before = sorted(before, reverse=True)
    if n is not None:
        if len(before) < n:
            raise ValueError(
                f"rewinding {season} wants {n} prior seasons, only {len(before)} "
                f"exist ({before}). Widen the window or drop the season.")
        before = before[:n]
    return before


@cached
def rewound_scorer(season: int) -> RotoScorer:
    """The roto scale as it could have been estimated before `season`.

    Level and baselines come from the two most recent completed seasons, which
    is the shape the production board uses (LEVEL_SEASONS is the two complete
    seasons behind a 2027 build, not the partial one in front of it).
    Dispersion pools every prior season, because sigma estimated off 10 teams
    in one year has a year-to-year CV of 0.25-0.75 (see denoms.py).
    """
    lvl_seasons = prior_seasons(season, 2)
    disp_seasons = prior_seasons(season)

    sigma = pooled_relative_dispersion(seasons=sorted(disp_seasons))
    levels = season_levels()
    lvl = (levels[levels["season"].isin(lvl_seasons)]
           .groupby("category")["level"].mean().to_dict())
    D = denominators_for_level(
        sigma, lvl, n_by_cat=teams_per_category(seasons=sorted(disp_seasons)))
    base = (team_baselines(sorted(lvl_seasons))
            .drop(columns=["season"]).mean().to_dict())
    return RotoScorer(D, base)


@cached
def rewound_points(season: int) -> pd.DataFrame:
    """Marcel's projection FOR `season`, scored on the rewound scale.

    Carries `rel`, Marcel's reliability weight, because a fifth to a quarter of
    pitcher rows sit below 0.30 and are mostly league mean wearing a player's
    name (#67). Anything that scores those as forecasts must say so.
    """
    if season not in MARCEL_SEASONS:
        raise ValueError(
            f"no Marcel projection for {season}; the archive covers "
            f"{MARCEL_SEASONS}. See klab/marcel.py.")
    sc = rewound_scorer(season)
    h, p = marcel_fg_ids(season, "HIT"), marcel_fg_ids(season, "PIT")
    H = h[["fg_id", "name", "rel"]].join(sc.hitters(h)[["roto_points"]]).assign(is_hit=1)
    P = p[["fg_id", "name", "rel"]].join(sc.pitchers(p)[["roto_points"]]).assign(is_hit=0)
    out = pd.concat([H, P], ignore_index=True).dropna(subset=["fg_id"])
    # Two-way players have a row in each file; summing matches auction.score_season
    # so the projected and realised sides of any comparison treat them alike.
    out = out.groupby("fg_id", as_index=False).agg(
        {"roto_points": "sum", "rel": "max", "name": "first", "is_hit": "max"})
    out["role"] = np.where(out["is_hit"] > 0, "HIT", "PIT")
    out["fg_id"] = out["fg_id"].astype(int)
    return out[["fg_id", "name", "role", "rel", "roto_points"]]


def _prior_actuals(season: int, role: str) -> pd.DataFrame:
    """Season T-1's realised line, the analogue of the production blend's
    "source A" (2026 actuals plus rest-of-season)."""
    from .io import load_hitters_history, load_pitchers_history

    prev = season - 1
    if role == "HIT":
        h = load_hitters_history()
        d = h[(h["season"] == prev) & (h["PA"].fillna(0) > 0)]
        cols = ["PA", "AB", "H", "HR", "R", "RBI", "SB"]
    else:
        p = load_pitchers_history()
        d = p[(p["season"] == prev) & (p["IP"].fillna(0) > 0)]
        cols = ["IP", "W", "SV", "K", "ER", "BB", "H"]
    out = d.groupby("fg_id", as_index=False)[cols].sum()
    out["fg_id"] = out["fg_id"].astype(int)
    return out


def blended_points(season: int, w_cap: float = C.BLEND_W_2026,
                   pt_cap_hit: float = C.PT_BLEND_CAP_HITTER,
                   pt_cap_pit: float = C.PT_BLEND_CAP_PITCHER) -> pd.DataFrame:
    """Marcel-for-`season` blended with season T-1 actuals, weights as arguments.

    This mirrors `project.project_hitters` / `project_pitchers`: source A is the
    prior season's realised line, source B the projection, the weight on A rises
    with A's own sample size and is capped, playing time carries its OWN lower
    cap (#51), and each counting rate's weight is discounted by that stat's
    year-over-year reliability (#28). Only the caps are parameters, which is
    what makes `BLEND_W_2026` and the `PT_BLEND_CAP_*` constants fittable.

    THE CAVEAT THAT LIMITS WHAT A FIT HERE MEANS. Marcel already averages three
    prior seasons internally, so blending T-1 actuals back in double-counts them
    harder than blending into ZiPS would (ZiPS 2027 loads 2026 at roughly a
    quarter of 2025's weight). Read the SHAPE of the curve, never the level.
    """
    from .project import RELIABILITY, REL_MAX, SHRINK_IP, SHRINK_PA, _safe_div

    def wcap(pt_a, shrink, cap):
        w = pt_a.fillna(0.0) / (pt_a.fillna(0.0) + shrink)
        return w.clip(upper=cap)

    def rel(stat, base):
        return base * (RELIABILITY.get(stat, REL_MAX) / REL_MAX)

    frames = []
    for role in ("HIT", "PIT"):
        A = _prior_actuals(season, role)
        B = marcel_fg_ids(season, role).dropna(subset=["fg_id"]).copy()
        B["fg_id"] = B["fg_id"].astype(int)
        pt, shrink = ("PA", SHRINK_PA) if role == "HIT" else ("IP", SHRINK_IP)
        cats = (["HR", "R", "RBI", "SB"] if role == "HIT"
                else ["W", "SV", "K", "ER", "BB"])
        keep_b = ["fg_id", "name", "rel", pt] + cats + (
            ["AB", "H"] if role == "HIT" else ["H"])

        m = A.merge(B[keep_b], on="fg_id", how="outer", suffixes=("_a", "_b"))
        has_a, has_b = m[f"{pt}_a"].fillna(0) > 0, m[f"{pt}_b"].fillna(0) > 0
        cap = pt_cap_hit if role == "HIT" else pt_cap_pit

        w = wcap(m[f"{pt}_a"], shrink, w_cap).where(has_b, 1.0).where(has_a, 0.0)
        w_pt = wcap(m[f"{pt}_a"], shrink, cap).where(has_b, 1.0).where(has_a, 0.0)
        m[pt] = w_pt * m[f"{pt}_a"].fillna(0) + (1 - w_pt) * m[f"{pt}_b"].fillna(0)

        for c in cats:
            ra = _safe_div(m[f"{c}_a"], m[f"{pt}_a"]).fillna(0.0)
            rb = _safe_div(m[f"{c}_b"], m[f"{pt}_b"]).fillna(0.0)
            wc = rel(c, w).where(has_a, 0.0).where(has_b, 1.0)
            m[c] = (wc * ra + (1 - wc) * rb) * m[pt]

        if role == "HIT":
            ab_rate = (w * _safe_div(m["AB_a"], m["PA_a"]).fillna(0.91)
                       + (1 - w) * _safe_div(m["AB_b"], m["PA_b"]).fillna(0.91))
            m["AB"] = m["PA"] * ab_rate
            ha = _safe_div(m["H_a"], m["AB_a"]).fillna(0.0)
            hb = _safe_div(m["H_b"], m["AB_b"]).fillna(0.0)
            wavg = rel("AVG", w).where(has_a, 0.0).where(has_b, 1.0)
            m["H"] = (wavg * ha + (1 - wavg) * hb) * m["AB"]
            m = m[m["PA"] > 20.0]
        else:
            ha = _safe_div(m["H_a"], m["IP_a"]).fillna(0.0)
            hb = _safe_div(m["H_b"], m["IP_b"]).fillna(0.0)
            wh = rel("H", w).where(has_a, 0.0).where(has_b, 1.0)
            m["H"] = (wh * ha + (1 - wh) * hb) * m["IP"]
            m = m[m["IP"] > 5.0]

        m["role"] = role
        frames.append(m)

    sc = rewound_scorer(season)
    H, P = frames[0], frames[1]
    Hs = H[["fg_id", "name", "role", "rel"]].join(sc.hitters(H)[["roto_points"]])
    Ps = P[["fg_id", "name", "role", "rel"]].join(sc.pitchers(P)[["roto_points"]])
    out = pd.concat([Hs, Ps], ignore_index=True)
    out["is_hit"] = (out["role"] == "HIT").astype(int)
    out = out.groupby("fg_id", as_index=False).agg(
        {"roto_points": "sum", "rel": "max", "name": "first", "is_hit": "max"})
    out["role"] = np.where(out["is_hit"] > 0, "HIT", "PIT")
    out["fg_id"] = out["fg_id"].astype(int)
    return out[["fg_id", "name", "role", "rel", "roto_points"]]


def _pool_and_replacement(pts: pd.DataFrame, pool_rule: str):
    """The calibration pool and each player's replacement level, per rule.

    blind        top 230 by roto points regardless of role, replacement = the
                 230th. What board.value_players() does today (#65).
    slot_pooled  top 140 hitters + top 90 pitchers, replacement still the 230th
                 of the ROLE-BLIND pool. #65's second candidate, 71.55%.
    slot_role    the same slot-constrained pool with role-specific replacement
                 (140th hitter, 90th pitcher). #65's first candidate at 54.21%,
                 which #68 showed matches perfect foresight (52.0-55.1%).
    """
    if pool_rule not in POOL_RULES:
        raise ValueError(f"pool_rule must be one of {POOL_RULES}, got {pool_rule!r}")
    d = pts.dropna(subset=["roto_points"])
    blind = d.nlargest(N_POOL, "roto_points")
    repl_blind = float(blind["roto_points"].min())

    if pool_rule == "blind":
        return blind, pd.Series(repl_blind, index=d.index), repl_blind

    H = d[d["role"].eq("HIT")].nlargest(N_HIT_FIELDABLE, "roto_points")
    P = d[d["role"].eq("PIT")].nlargest(N_PIT_FIELDABLE, "roto_points")
    pool = pd.concat([H, P])
    if pool_rule == "slot_pooled":
        return pool, pd.Series(repl_blind, index=d.index), repl_blind

    repl_h, repl_p = float(H["roto_points"].min()), float(P["roto_points"].min())
    repl = pd.Series(np.where(d["role"].eq("HIT"), repl_h, repl_p), index=d.index)
    return pool, repl, {"HIT": repl_h, "PIT": repl_p}


@cached
def rewound_board(season: int, pool_rule: str = "blind") -> pd.DataFrame:
    """Every projected player for `season` with a `redraft_value` in dollars.

    The dollar conversion is `board.value_players()`'s, kept identical on
    purpose so a difference between this board and the production one is the
    projection and the pool rule, never the arithmetic: every player in the
    pool gets the $1 minimum bid and the remaining $2,600 - $230 is spread in
    proportion to roto points above replacement.
    """
    return price_points(rewound_points(season), season, pool_rule)


def price_points(points: pd.DataFrame, season: int,
                 pool_rule: str = "blind") -> pd.DataFrame:
    """The dollar conversion on its own, so any projection can be priced.

    Split out of `rewound_board` because the blend-weight sweep prices dozens of
    candidate projections for one season and must hold the pricing arithmetic
    exactly constant while it does.
    """
    pts = points.copy()
    pool, repl, repl_meta = _pool_and_replacement(pts, pool_rule)

    surplus = (pool["roto_points"] - repl.loc[pool.index]).clip(lower=0.0)
    usd_per_rp = (C.N_TEAMS * C.BUDGET - len(pool) * 1.0) / float(surplus.sum())

    pts["replacement_rp"] = repl
    pts["redraft_value"] = (
        (pts["roto_points"] - repl) * usd_per_rp + 1.0).clip(lower=0.0)

    # Both scales, because the backtest tests WHICH ONE the keep rule should
    # use. `redraft_value` is what board.py's surplus_multiyear runs on today;
    # `replace_cost` is the auction opportunity cost, which is what a keep is
    # actually traded against. They disagree by a lot at the top.
    exch = rewound_exchange(season)
    pts["replace_cost"] = (
        (pts["roto_points"] - exch["intercept"]) / exch["slope"]).clip(lower=0.0)

    pts.attrs.update({
        "exchange": exch,
        "season": season, "pool_rule": pool_rule, "usd_per_rp": usd_per_rp,
        "replacement": repl_meta, "n_pool": len(pool),
        "pool_hit": int(pool["role"].eq("HIT").sum()),
        "pool_pit": int(pool["role"].eq("PIT").sum()),
    })
    return pts


@cached
def rewound_exchange(season: int) -> dict:
    """Roto points per auction dollar, fitted only on auctions before `season`.

    This is the OPPORTUNITY-COST scale (`board.py`'s `keep_value`): what the
    league's own auction charges for a given level of production, so
    `(rp - intercept) / slope` is the money it would take to replace a player.
    That is the correct denominator for "was keeping him at $S right", and it is
    not the same as `redraft_value`. Scoring a keep against redraft value asks
    what he would fetch in a full redraft with no keepers withheld, which is a
    cheaper market, so it makes every keep look worse than it was
    (`scripts/decision_audit.py` flags exactly this as its open question 3).

    A plain pooled fit, not `board.fit_exchange_rate`'s keeper-count adjustment:
    that regression needs several prior auctions to fit a line through, and
    rewinding to 2024 leaves only 2022 and 2023. Two points would be fitted
    perfectly and mean nothing.
    """
    from .auction import auction_sample, regress

    seasons = sorted(prior_seasons(season))
    sigma = pooled_relative_dispersion(seasons=seasons)
    sample = auction_sample(seasons=tuple(seasons), sigma_rel=sigma)
    r = regress(sample)
    slope, intercept = float(r.params["salary"]), float(r.params["const"])
    return {"slope": slope, "intercept": intercept,
            "usd_per_point": 1.0 / slope, "n": int(r.nobs), "seasons": seasons}


@cached
def realised_board(season: int, pool_rule: str = "blind") -> pd.DataFrame:
    """What each player turned out to be worth in `season`, in the same dollars.

    Deliberately EX POST: the stat lines are what happened and the roto scale is
    that season's own. This is the scorer of a decision, not an input to one, so
    using post-season information is correct here and only here.

    It also fixes what `scripts/decision_audit.py` flags as its open question 2.
    That file prices every season with the CURRENT build's `usd_per_rp` and
    replacement level, which it notes is wrong in level for 2023-2025. Running
    the same $2,600 calibration on each season's own realised points puts both
    sides of every comparison on that season's scale.
    """
    from .auction import score_season
    from .io import load_hitters_history, load_pitchers_history

    scored = score_season(season, pooled_relative_dispersion(), season_levels(),
                          load_hitters_history(), load_pitchers_history(),
                          team_baselines([season]))
    pts = scored[["fg_id", "name", "role", "roto_points"]].copy()
    pts["fg_id"] = pts["fg_id"].astype(int)
    pool, repl, repl_meta = _pool_and_replacement(pts, pool_rule)

    surplus = (pool["roto_points"] - repl.loc[pool.index]).clip(lower=0.0)
    usd_per_rp = (C.N_TEAMS * C.BUDGET - len(pool) * 1.0) / float(surplus.sum())
    pts["value_realised"] = (
        (pts["roto_points"] - repl) * usd_per_rp + 1.0).clip(lower=0.0)

    # The replacement-cost scale, and the one a KEEP should be judged on: what
    # this league's auction charges for that much production. See
    # rewound_exchange() for why redraft dollars are the wrong denominator.
    exch = rewound_exchange(season)
    pts["replace_cost"] = (
        (pts["roto_points"] - exch["intercept"]) / exch["slope"]).clip(lower=0.0)

    pts.attrs.update({"season": season, "pool_rule": pool_rule,
                      "usd_per_rp": usd_per_rp, "replacement": repl_meta,
                      "exchange": exch})
    return pts[["fg_id", "name", "role", "roto_points",
                "value_realised", "replace_cost"]]
