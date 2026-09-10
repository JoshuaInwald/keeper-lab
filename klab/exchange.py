"""Alternative exchange-rate estimators: the menu behind the app's fit toggle.

The exchange rate is the least identified, most load-bearing parameter in the
chain (docs/MODEL-REVIEW.md section 6): n = 5 auctions, keeper count and
calendar time collinear at 0.987 (#19), split halves of 2026 disagreeing
threefold (#7). The shipped estimator (`board.fit_exchange_rate`, two stacked
OLS fits predicted at 100 keepers) is one defensible member of a family.
This module fits the rest of the family so the decision test can score them
(`scripts/exchange_lab.py`), and so `build_app.py` can ship the survivors as a
user-facing dropdown.

Every estimator returns the same shape `board.keep_cost()` consumes:
{"slope", "intercept", "usd_per_point", "n", "label", ...}, plus "curve"
({"rp_knots", "usd_knots"}) for the two non-linear members. `usd_per_point`
for a curve is the top-segment marginal rate and is reported, not used.

`before_season` rewinds a fit to data that existed before that season
(prior-season purchases, prior-season dispersion and field sizes, mirroring
`klab.rewind.rewound_exchange`), so the backtest can re-score the keep/cut
calls each estimator would actually have produced.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .auction import auction_sample, regress
from .io import cached

# Salary knots for the piecewise (non-linear) members, from the #2 band table
# and spec_battery's price bins; the top segment is n=36 picks and says so.
SALARY_KNOTS = (6.0, 16.0, 31.0)
SALARY_MAX = 45.0            # the league's all-time ceiling (#2)


def _sample(seasons: tuple[int, ...], before_season: int | None = None,
            projected: bool = False) -> pd.DataFrame:
    """Auction purchases with the keeper count `k` attached.

    `before_season` swaps in prior-season dispersion and field sizes so no
    post-decision information leaks into a rewound fit (FINDINGS #80).
    `projected` replaces delivered points with the ex-ante blended projection
    (#67's Marcel archive), because the market bids on projections, not
    outcomes; unprojected players count 0, matching auction_sample's
    treatment of never-played purchases.
    """
    if before_season is not None:
        from .denoms import pooled_relative_dispersion, teams_per_category
        from .rewind import prior_seasons
        prior = sorted(prior_seasons(before_season))
        seasons = tuple(s for s in seasons if s in prior)
        sigma = pooled_relative_dispersion(seasons=list(seasons))
        nbc = tuple(sorted(teams_per_category(seasons=list(seasons)).items()))
        s = auction_sample(seasons=seasons, sigma_rel=sigma, n_by_cat=nbc)
    else:
        s = auction_sample(seasons=seasons)
    s = s.copy()
    s["k"] = s["season"].map(C.KEEPERS_REMOVED).astype(float)
    if projected:
        from .rewind import blended_points
        from .marcel import SEASONS as MARCEL_SEASONS
        keep = [y for y in s["season"].unique() if y in MARCEL_SEASONS]
        s = s[s["season"].isin(keep)].copy()
        proj = pd.concat([blended_points(y).assign(season=y) for y in sorted(keep)],
                         ignore_index=True)
        s = s.drop(columns=["roto_points"]).merge(
            proj[["season", "fg_id", "roto_points"]],
            on=["season", "fg_id"], how="left")
        s["roto_points"] = s["roto_points"].fillna(0.0)
    return s


def _per_season(sample: pd.DataFrame, median: bool = False) -> pd.DataFrame:
    """First-stage fits, one row per season: usd/pt, intercept, keeper count."""
    import statsmodels.api as sm
    rows = []
    for y, g in sample.groupby("season"):
        if median:
            X = sm.add_constant(g[["salary"]])
            r = sm.QuantReg(g["roto_points"], X).fit(q=0.5, max_iter=5000)
        else:
            r = regress(g)
        rows.append({"season": y, "k": float(C.KEEPERS_REMOVED[y]),
                     "usd": 1.0 / r.params["salary"],
                     "icept": float(r.params["const"]), "n": int(len(g))})
    return pd.DataFrame(rows)


def _trend_at_k(per: pd.DataFrame, k: float) -> tuple[float, float]:
    """Second stage: usd and intercept regressed on keeper count, read at k."""
    import statsmodels.api as sm
    fit = sm.OLS(per["usd"], sm.add_constant(per[["k"]])).fit()
    usd = float(fit.params["const"] + fit.params["k"] * k)
    ifit = sm.OLS(per["icept"], sm.add_constant(per[["k"]])).fit()
    icept = float(ifit.params["const"] + ifit.params["k"] * k)
    return usd, icept


def _linear(usd: float, icept: float, n: int, label: str, **extra) -> dict:
    return {"slope": 1.0 / usd, "intercept": icept, "usd_per_point": usd,
            "n": int(n), "label": label, "basis": label, **extra}


def fit_pooled(seasons=None, before_season=None, median=False,
               projected=False) -> dict:
    """One OLS over every pick in the window: the known-wrong baseline
    ($/pt averaged across different keeper regimes), kept on the menu so the
    others can be read against it."""
    import statsmodels.api as sm
    seasons = tuple(seasons or C.AUCTION_SEASONS)
    s = _sample(seasons, before_season, projected)
    label = ("median" if median else "pooled") + ("_projected" if projected else "")
    if median:
        X = sm.add_constant(s[["salary"]])
        r = sm.QuantReg(s["roto_points"], X).fit(q=0.5, max_iter=5000)
        return _linear(1.0 / r.params["salary"], float(r.params["const"]),
                       len(s), label, seasons=sorted(set(s["season"])))
    r = regress(s)
    return _linear(1.0 / r.params["salary"], float(r.params["const"]),
                   int(r.nobs), label, seasons=sorted(set(s["season"])),
                   slope_se=float(r.bse["salary"]), r2=float(r.rsquared))


def fit_two_stage(seasons=None, before_season=None, k=None,
                  median=False, projected=False) -> dict:
    """The shipped architecture (per-season fits, then usd on keeper count,
    read at the expected 2027 count), refittable on any window, with a
    median-regression first stage as the robust variant."""
    seasons = tuple(seasons or sorted(C.KEEPERS_REMOVED))
    s = _sample(seasons, before_season, projected)
    per = _per_season(s, median=median)
    if len(per) < 3:
        raise ValueError(f"two-stage fit needs >= 3 seasons, have {len(per)}")
    k = float(k if k is not None else C.KEEPERS_EXPECTED_2027)
    usd, icept = _trend_at_k(per, k)
    label = ("median_two_stage" if median else "two_stage") + \
            ("_projected" if projected else "")
    return _linear(usd, icept, len(s), label, k=k,
                   seasons=sorted(set(s["season"])),
                   per_season=per.to_dict("records"))


def fit_pick_level(seasons=None, before_season=None, k=None,
                   projected=False) -> dict:
    """Pooled pick-level regression with keeper count as a covariate:
    rp ~ salary + k + salary*k, read at the expected count.

    The same extrapolation as the shipped two-stage fit (nothing escapes the
    n=5 collinearity, #19), but the standard errors come from every pick
    instead of a five-point second stage, and the regime drift is estimated
    where the picks are instead of season-by-season.
    """
    import statsmodels.api as sm
    seasons = tuple(seasons or sorted(C.KEEPERS_REMOVED))
    s = _sample(seasons, before_season, projected)
    k = float(k if k is not None else C.KEEPERS_EXPECTED_2027)
    X = pd.DataFrame({"const": 1.0, "k": s["k"], "salary": s["salary"],
                      "salary_k": s["salary"] * s["k"]}, index=s.index)
    r = sm.OLS(s["roto_points"], X).fit(cov_type="HC1")
    slope = float(r.params["salary"] + r.params["salary_k"] * k)
    icept = float(r.params["const"] + r.params["k"] * k)
    g = np.array([0.0, 0.0, 1.0, k])
    slope_se = float(np.sqrt(g @ r.cov_params().values @ g))
    label = "pick_level" + ("_projected" if projected else "")
    return _linear(1.0 / slope, icept, int(r.nobs), label, k=k,
                   seasons=sorted(set(s["season"])), slope_se=slope_se,
                   usd_se=slope_se / slope ** 2)


def fit_partial_pool(seasons=None, before_season=None) -> dict:
    """Per-season fits shrunk toward the pooled rate (method-of-moments
    between-season variance), then the most recent season's shrunk value.
    Answers "how much of 2026's $9.98 is signal" without a trend line."""
    seasons = tuple(seasons or sorted(C.KEEPERS_REMOVED))
    s = _sample(seasons, before_season)
    per = _per_season(s)
    # Delta-method SE of usd per season, from each season's own fit.
    ses = []
    for y, g in s.groupby("season"):
        r = regress(g)
        ses.append(float(r.bse["salary"]) / float(r.params["salary"]) ** 2)
    per["se"] = ses
    pooled_usd = fit_pooled(seasons=[y for y in seasons
                                     if y in set(per["season"])])["usd_per_point"]
    tau2 = max(0.0, float(per["usd"].var(ddof=1)) - float((per["se"] ** 2).mean()))
    w = tau2 / (tau2 + per["se"] ** 2)
    per["usd_shrunk"] = w * per["usd"] + (1 - w) * pooled_usd
    last = per.sort_values("season").iloc[-1]
    icept = float(per.sort_values("season").iloc[-1]["icept"])
    return _linear(float(last["usd_shrunk"]), icept, len(s), "partial_pool",
                   tau2=tau2, per_season=per.round(4).to_dict("records"))


def _pwl_design(s: pd.DataFrame, with_k: bool) -> pd.DataFrame:
    X = {"const": 1.0, "s0": s["salary"]}
    for j, kn in enumerate(SALARY_KNOTS, start=1):
        X[f"s{j}"] = (s["salary"] - kn).clip(lower=0)
    if with_k:
        X["k"] = s["k"]
    return pd.DataFrame(X, index=s.index)


def _curve_from_segments(rp0: float, seg_usd: list[float]) -> dict:
    """Piecewise curve knots from an intercept and per-segment $/pt values.
    Segment bounds are $0..6..16..31..45; rp knots accumulate salary/usd."""
    bounds = [0.0] + list(SALARY_KNOTS) + [SALARY_MAX]
    rp_knots, usd_knots, rp = [rp0], [0.0], rp0
    for j, u in enumerate(seg_usd):
        rp += (bounds[j + 1] - bounds[j]) / u
        rp_knots.append(rp)
        usd_knots.append(bounds[j + 1])
    return {"rp_knots": rp_knots, "usd_knots": usd_knots}


def fit_spline(seasons=None, before_season=None, k=None) -> dict:
    """Shape-constrained-by-inspection piecewise-linear fit: rp on a linear
    salary spline (knots at $6/$16/$31) with keeper count shifting the level.

    The value-side answer to the three instruments saying the market is not
    linear at the top (#56.5, #57.6, #75): if the fitted rp-on-salary curve is
    convex, its inverse (what the board charges per point) is concave and the
    top of the board stops being priced at the mid-table rate. Monotonicity is
    checked, not imposed; a non-monotone fit raises rather than ships.
    """
    import statsmodels.api as sm
    seasons = tuple(seasons or sorted(C.KEEPERS_REMOVED))
    s = _sample(seasons, before_season)
    k = float(k if k is not None else C.KEEPERS_EXPECTED_2027)
    X = _pwl_design(s, with_k=True)
    r = sm.OLS(s["roto_points"], X).fit(cov_type="HC1")
    coefs = [float(r.params["s0"])]
    for j in range(1, len(SALARY_KNOTS) + 1):
        coefs.append(coefs[-1] + float(r.params[f"s{j}"]))
    if min(coefs) <= 0:
        raise ValueError(f"spline fit is non-monotone (segment slopes {coefs})")
    rp0 = float(r.params["const"] + r.params["k"] * k)
    curve = _curve_from_segments(rp0, [1.0 / c for c in coefs])
    # Reported linear summary: the top segment's marginal rate, which is what
    # an extra dollar at the star tier buys. Never used in keep_cost().
    return {"slope": coefs[-1], "intercept": rp0,
            "usd_per_point": 1.0 / coefs[-1], "n": int(r.nobs),
            "label": "spline", "basis": "spline", "k": k, "curve": curve,
            "segment_usd": [round(1.0 / c, 3) for c in coefs],
            "seasons": sorted(set(s["season"]))}


def fit_tiered_two_stage(seasons=None, before_season=None, k=None) -> dict:
    """The tiered exchange in the shipped two-stage architecture: per-season
    piecewise fits, then each segment's $/pt regressed on keeper count and
    read at the expected 2027 count.

    The honest cost of tiering: the top segment is ~7 picks per season, so
    its per-season slope is noise and the second stage inherits it. A
    degenerate segment (predicted $/pt <= 0) raises rather than ships.
    """
    import statsmodels.api as sm
    seasons = tuple(seasons or sorted(C.KEEPERS_REMOVED))
    s = _sample(seasons, before_season)
    k = float(k if k is not None else C.KEEPERS_EXPECTED_2027)
    rows = []
    for y, g in s.groupby("season"):
        X = _pwl_design(g, with_k=False)
        r = sm.OLS(g["roto_points"], X).fit()
        segs = [float(r.params["s0"])]
        for j in range(1, len(SALARY_KNOTS) + 1):
            segs.append(segs[-1] + float(r.params[f"s{j}"]))
        rows.append({"season": y, "k": float(C.KEEPERS_REMOVED[y]),
                     "icept": float(r.params["const"]),
                     **{f"usd_seg{j}": 1.0 / c if c > 0 else np.nan
                        for j, c in enumerate(segs)}})
    per = pd.DataFrame(rows)
    seg_usd = []
    for j in range(len(SALARY_KNOTS) + 1):
        col = per[f"usd_seg{j}"].dropna()
        sub = per.loc[col.index]
        # A segment whose per-season slope came out negative in some seasons
        # loses those rows; if what is left cannot support a trend (too few
        # seasons, or no keeper-count variation), the estimator is degenerate
        # and says so instead of extrapolating from noise.
        if len(col) < 4 or sub["k"].nunique() < 2:
            raise ValueError(
                f"tiered two-stage segment {j} has {len(col)} usable seasons "
                f"(per-season usd {list(per[f'usd_seg{j}'].round(2))}); "
                f"no honest trend exists")
        fit = sm.OLS(col, sm.add_constant(sub[["k"]])).fit()
        u = float(fit.params["const"] + fit.params["k"] * k)
        if u <= 0 or not np.isfinite(u):
            raise ValueError(
                f"tiered two-stage segment {j} degenerates at k={k:.0f} "
                f"(usd {u:.2f}); per-season values {list(col.round(2))}")
        seg_usd.append(u)
    ifit = sm.OLS(per["icept"], sm.add_constant(per[["k"]])).fit()
    rp0 = float(ifit.params["const"] + ifit.params["k"] * k)
    curve = _curve_from_segments(rp0, seg_usd)
    return {"slope": 1.0 / seg_usd[-1], "intercept": rp0,
            "usd_per_point": seg_usd[-1], "n": int(len(s)),
            "label": "tiered_two_stage", "basis": "tiered_two_stage", "k": k,
            "curve": curve, "segment_usd": [round(u, 3) for u in seg_usd],
            "per_season": per.round(3).to_dict("records")}


# The menu `scripts/exchange_lab.py` scores and `build_app.py` draws from.
# Keys are stable identifiers; docs and the app reference them by name.
def fit_variant(name: str, before_season: int | None = None,
                k: float | None = None) -> dict:
    all_seasons = tuple(sorted(C.KEEPERS_REMOVED))
    fits = {
        "keeper_adjusted": lambda: _shipped(),
        "two_stage_rewound": lambda: fit_two_stage(all_seasons, before_season, k),
        "pooled_2426": lambda: fit_pooled(C.AUCTION_SEASONS, before_season),
        "pooled_2226": lambda: fit_pooled(all_seasons, before_season),
        "recent_2026": lambda: fit_pooled((2026,), before_season),
        "window_2425": lambda: fit_pooled((2024, 2025), before_season),
        "pick_level": lambda: fit_pick_level(all_seasons, before_season, k),
        "pick_level_2426": lambda: fit_pick_level(
            tuple(C.AUCTION_SEASONS), before_season, k),
        "projected": lambda: fit_pick_level(all_seasons, before_season, k,
                                            projected=True),
        "projected_pooled": lambda: fit_pooled(C.AUCTION_SEASONS, before_season,
                                               projected=True),
        "partial_pool": lambda: fit_partial_pool(all_seasons, before_season),
        "median_two_stage": lambda: fit_two_stage(all_seasons, before_season,
                                                  k, median=True),
        "median_pooled": lambda: fit_pooled(C.AUCTION_SEASONS, before_season,
                                            median=True),
        "spline": lambda: fit_spline(all_seasons, before_season, k),
        "tiered_two_stage": lambda: fit_tiered_two_stage(all_seasons,
                                                         before_season, k),
    }
    if name not in fits:
        raise KeyError(f"unknown exchange variant {name!r}; "
                       f"have {sorted(fits)}")
    out = fits[name]()
    out["label"] = name
    return out


def _shipped() -> dict:
    from .board import fit_exchange_rate
    exch, _ = fit_exchange_rate()
    out = dict(exch)
    out["label"] = "keeper_adjusted"
    return out
