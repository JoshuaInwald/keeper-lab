"""Step 4: 2027 player projections.

Two independent views of each player:
  A. 2026 full season  = actuals to date + ZiPS rest-of-season
  B. ZiPS 2027 pre-season depth-chart projection

They are blended at the rate x playing-time level rather than on raw counting
stats. Blending counting stats directly double-counts ZiPS's playing-time
haircut: ZiPS already docks Yordan Alvarez to 474 PA for durability, so
averaging his *counting* line with a healthy 2026 line applies the haircut
twice and buries him. Rates and PT are blended separately instead.

Source A is weighted by its own sample size, so a prospect with 60 PA of 2026
leans on ZiPS while a 650-PA regular leans on his own season.

Saves are handled apart from everything else: the ZiPS 2027 export has no SV
column at all, so 2027 saves come from a fitted persistence model.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import config as C
from .io import cached
from .io import (load_hitters_history, load_pitchers_history, load_ros_hitters,
                 load_ros_pitchers, load_zips27_hitters, load_zips27_pitchers)

# Source A gets weight PA/(PA+SHRINK_PA), capped at BLEND_W_2026.
SHRINK_PA = 250.0
SHRINK_IP = 70.0

# Year-over-year r of each rate on this dataset (hitters 250+ PA, n=693;
# pitchers 40+ IP, n=785); the 2026 leg's weight is scaled by r / max r, so
# a non-repeating stat like W (r=0.15) barely carries forward.
# BB and H must be their own fitted r, not WHIP's 0.237 -- a copy-paste once
# discounted walk/hit rates as if they were as noisy as WHIP (FINDINGS #28).
RELIABILITY = {
    "HR": 0.607, "R": 0.425, "RBI": 0.380, "SB": 0.739, "AVG": 0.436,
    "K": 0.701, "W": 0.151, "ER": 0.176, "WHIP": 0.237, "BB": 0.463,
    "H": 0.359,
}
REL_MAX = max(RELIABILITY.values())


def rel_weight(stat: str, base: pd.Series) -> pd.Series:
    """Sample-size weight on the 2026 leg, discounted by that stat's signal."""
    return base * (RELIABILITY.get(stat, REL_MAX) / REL_MAX)
# Below these thresholds a projected line is noise, not a player. They also
# stop position players who mopped up an inning from being scored as pitchers.
MIN_PA_HITTER = 20.0
MIN_IP_PITCHER = 5.0


# --- saves model ------------------------------------------------------------

@cached
def fit_save_model(min_ip: float = 20.0) -> dict:
    """SV_{t+1} ~ SV_t over all pitchers with a real workload in year t.

    Fitting on every pitcher (not just incumbent closers) keeps the intercept
    honest -- restricting to SV_t >= 10 produces a +5.0 intercept that would
    hand five phantom saves to every mop-up arm in the league.
    """
    p = load_pitchers_history()
    frames = []
    for a, b in [(2022, 2023), (2023, 2024), (2024, 2025)]:
        ta = p[(p["season"] == a) & (p["IP"] >= min_ip)][["fg_id", "SV", "G", "GS"]]
        tb = p[p["season"] == b][["fg_id", "SV"]].rename(columns={"SV": "SV_next"})
        m = ta.merge(tb, on="fg_id", how="left")
        m["SV_next"] = m["SV_next"].fillna(0.0)   # gone from MLB = zero saves
        frames.append(m)
    d = pd.concat(frames, ignore_index=True)
    r = sm.OLS(d["SV_next"], sm.add_constant(d[["SV"]])).fit()
    return {"intercept": float(r.params["const"]), "slope": float(r.params["SV"]),
            "r2": float(r.rsquared), "n": int(r.nobs),
            "mean_sv_t": float(d["SV"].mean()), "mean_sv_t1": float(d["SV_next"].mean())}


def project_saves(sv_2026: pd.Series, model: dict,
                  reliever: pd.Series | None = None) -> pd.Series:
    """The intercept is the chance an arm backs into saves next year. That
    applies to relievers, not to starters, so it is switched off for anyone
    who mostly starts."""
    base = model["intercept"]
    if reliever is not None:
        base = pd.Series(np.where(reliever.fillna(False), model["intercept"], 0.0),
                         index=sv_2026.index)
    return (base + model["slope"] * sv_2026.fillna(0.0)).clip(lower=0.0)


# --- helpers ----------------------------------------------------------------

def _blend_weight(pt_a: pd.Series, shrink: float,
                  cap: float | pd.Series = C.BLEND_W_2026) -> pd.Series:
    """Weight on source A (2026 form): rises with its own sample size, capped
    at `cap`. PROJECTION_BASIS can force it to either pole.

    `cap` is a parameter because playing time uses a lower cap than rates
    (PT_BLEND_CAP_*, docs/FINDINGS.md #51) and may be a per-player Series
    (docs/FINDINGS.md #53) -- Series.clip bounds elementwise."""
    if C.PROJECTION_BASIS == "projection":
        return pd.Series(0.0, index=pt_a.index)
    if C.PROJECTION_BASIS == "actuals":
        return pd.Series(1.0, index=pt_a.index)
    w = pt_a.fillna(0.0) / (pt_a.fillna(0.0) + shrink)
    return w.clip(upper=cap)


def _safe_div(a, b):
    b = pd.Series(b).astype(float).replace(0.0, np.nan)
    return pd.Series(a).astype(float) / b


# --- hitters ----------------------------------------------------------------

@cached
def season_completion_2026() -> tuple[float, float]:
    """How much of 2026 is already banked, for hitters and for pitchers.

    Playing time to date over playing time for the whole season (to date plus
    the ZiPS rest-of-season projection), restricted to players who actually
    have a 2026 line so that ROS rows for players who never appeared cannot
    inflate the denominator.

    Needed because the 2026 STANDINGS are a partial season. Scoring a
    full-season stat line against partial-season denominators would inflate
    every counting category by the missing fraction. Checks out against the
    observed levels: 2026 sits at 0.885-0.916 of the 2024-25 mean for HR, R,
    RBI, W and K, which brackets this estimate. SB and SV sit at 0.80 because
    the league is genuinely running fewer of both, which is exactly the drift
    this estimator must NOT absorb, and does not.
    """
    h = load_hitters_history()
    h26 = h[h["season"] == 2026]
    rh = load_ros_hitters()
    pa_now = float(h26["PA"].sum())
    pa_ros = float(rh[rh["fg_id"].isin(set(h26["fg_id"]))]["PA"].sum())

    p = load_pitchers_history()
    p26 = p[p["season"] == 2026]
    rp = load_ros_pitchers()
    ip_now = float(p26["IP"].sum())
    ip_ros = float(rp[rp["fg_id"].isin(set(p26["fg_id"]))]["IP"].sum())
    return pa_now / (pa_now + pa_ros), ip_now / (ip_now + ip_ros)


@cached
def lines_2026_hitters() -> pd.DataFrame:
    """A full 2026 hitter season: banked actuals plus the ZiPS rest-of-season
    projection for the weeks still to play.

    This is the projection's "source A". It is extracted so the board can SHOW
    it (docs/FINDINGS.md #72): a 2027 number with nothing to compare it against
    cannot be read, and the first question anyone asks of a projection is how
    far it sits from what the player just did.
    """
    hist = load_hitters_history()
    a26 = hist[hist["season"] == 2026].copy()
    ros = load_ros_hitters()

    cols = ["PA", "AB", "H", "HR", "R", "RBI", "SB"]
    r = ros[["fg_id"] + cols].groupby("fg_id", as_index=False).sum()
    a = a26[["fg_id", "name"] + cols].groupby("fg_id", as_index=False).agg(
        {"name": "first", **{c: "sum" for c in cols}})

    A = a.merge(r, on="fg_id", how="outer", suffixes=("", "_ros"))
    A["name"] = A["name"].fillna("")
    for c in cols:
        A[c] = A[c].fillna(0.0) + A[f"{c}_ros"].fillna(0.0)
    return A[["fg_id", "name"] + cols]


@cached
def project_hitters() -> pd.DataFrame:
    # Source A = 2026 actuals + rest of season
    A = lines_2026_hitters()

    z = load_zips27_hitters()
    B = z[["fg_id", "name", "PA", "AB", "H", "HR", "R", "RBI", "SB"]].groupby(
        "fg_id", as_index=False).agg({"name": "first", **{c: "sum" for c in
        ["PA", "AB", "H", "HR", "R", "RBI", "SB"]}})

    m = A.merge(B, on="fg_id", how="outer", suffixes=("_a", "_b"))
    m["name"] = m["name_a"].replace("", np.nan).fillna(m["name_b"])

    has_a = m["PA_a"].fillna(0) > 0
    has_b = m["PA_b"].fillna(0) > 0
    w = _blend_weight(m["PA_a"], SHRINK_PA)
    w = w.where(has_b, 1.0)            # no ZiPS 2027 line -> lean fully on 2026
    w = w.where(has_a, 0.0)            # no 2026 line -> lean fully on ZiPS
    m["w_2026"] = w

    # Playing time gets its own lower-capped weight, decoupled from the rate
    # weight: a short 2026 says little about a healthy 2027 role (FINDINGS #51).
    w_pt = _blend_weight(m["PA_a"], SHRINK_PA, cap=C.PT_BLEND_CAP_HITTER)
    w_pt = w_pt.where(has_b, 1.0).where(has_a, 0.0)
    m["PA"] = w_pt * m["PA_a"].fillna(0) + (1 - w_pt) * m["PA_b"].fillna(0)
    ab_rate = (w * _safe_div(m["AB_a"], m["PA_a"]).fillna(0.91)
               + (1 - w) * _safe_div(m["AB_b"], m["PA_b"]).fillna(0.91))
    m["AB"] = m["PA"] * ab_rate

    # per-PA rates for counting stats, per-AB for hits; each blended with a
    # weight scaled by that stat's year-over-year reliability
    for c in ["HR", "R", "RBI", "SB"]:
        ra = _safe_div(m[f"{c}_a"], m["PA_a"]).fillna(0.0)
        rb = _safe_div(m[f"{c}_b"], m["PA_b"]).fillna(0.0)
        wc = rel_weight(c, w).where(has_a, 0.0).where(has_b, 1.0)
        m[c] = (wc * ra + (1 - wc) * rb) * m["PA"]
    ha = _safe_div(m["H_a"], m["AB_a"]).fillna(0.0)
    hb = _safe_div(m["H_b"], m["AB_b"]).fillna(0.0)
    wavg = rel_weight("AVG", w).where(has_a, 0.0).where(has_b, 1.0)
    m["AVG_rate"] = wavg * ha + (1 - wavg) * hb
    m["H"] = m["AVG_rate"] * m["AB"]
    m["AVG"] = m["AVG_rate"]
    m["role"] = "HIT"
    # The FanGraphs hitter export carries a zero-PA row for every pitcher.
    # Drop them or every starter turns up as a two-way player.
    m = m[m["PA"] > MIN_PA_HITTER]
    return m[["fg_id", "name", "role", "w_2026", "PA", "AB", "H",
              "HR", "R", "RBI", "SB", "AVG"]]


# --- pitchers ---------------------------------------------------------------

@cached
@cached
def lines_2026_pitchers() -> pd.DataFrame:
    """A full 2026 pitcher season: banked actuals plus ZiPS rest-of-season.

    The projection's "source A", extracted for the same reason as the hitter
    version (docs/FINDINGS.md #72). `reliever` rides along because the save
    model needs it and it is derived from the same G/GS split.
    """
    hist = load_pitchers_history()
    a26 = hist[hist["season"] == 2026].copy()
    ros = load_ros_pitchers()

    cols = ["IP", "W", "SV", "K", "ER", "BB", "H"]
    a = a26[["fg_id", "name", "G", "GS"] + cols].groupby("fg_id", as_index=False).agg(
        {"name": "first", "G": "sum", "GS": "sum", **{c: "sum" for c in cols}})
    r = ros.rename(columns={"SO": "K"})[["fg_id"] + cols].groupby(
        "fg_id", as_index=False).sum()

    A = a.merge(r, on="fg_id", how="outer", suffixes=("", "_ros"))
    A["name"] = A["name"].fillna("")
    for c in cols:
        A[c] = A[c].fillna(0.0) + A[f"{c}_ros"].fillna(0.0)
    A["reliever"] = A["GS"].fillna(0) < 0.5 * A["G"].fillna(0).clip(lower=1)
    return A[["fg_id", "name", "reliever"] + cols]


@cached
def project_pitchers(save_model: dict | None = None) -> pd.DataFrame:
    save_model = save_model or fit_save_model()
    A = lines_2026_pitchers()
    cols = ["IP", "W", "SV", "K", "ER", "BB", "H"]

    z = load_zips27_pitchers().rename(columns={"SO": "K"})
    B = z[["fg_id", "name"] + [c for c in cols if c != "SV"]].groupby(
        "fg_id", as_index=False).agg({"name": "first",
        **{c: "sum" for c in cols if c != "SV"}})

    m = A.merge(B, on="fg_id", how="outer", suffixes=("_a", "_b"))
    m["name"] = m["name_a"].replace("", np.nan).fillna(m["name_b"])

    has_a = m["IP_a"].fillna(0) > 0
    has_b = m["IP_b"].fillna(0) > 0
    w = _blend_weight(m["IP_a"], SHRINK_IP)
    w = w.where(has_b, 1.0)
    w = w.where(has_a, 0.0)
    m["w_2026"] = w

    # Playing-time weight is capped lower for pitchers (injury-shortened
    # 2026 must not dock 2027 IP, FINDINGS #51); a pitcher whose 2026 IP
    # already EXCEEDED ZiPS's 2027 IP gets the higher cap (FINDINGS #53).
    exceeded = m["IP_a"].fillna(0) > m["IP_b"].fillna(0)
    pt_cap = pd.Series(np.where(exceeded, C.PT_BLEND_CAP_PITCHER_EXCEEDED,
                                C.PT_BLEND_CAP_PITCHER), index=m.index)
    w_pt = _blend_weight(m["IP_a"], SHRINK_IP, cap=pt_cap)
    w_pt = w_pt.where(has_b, 1.0).where(has_a, 0.0)
    m["IP"] = w_pt * m["IP_a"].fillna(0) + (1 - w_pt) * m["IP_b"].fillna(0)
    for c in ["W", "K", "ER", "BB", "H"]:
        ra = _safe_div(m[f"{c}_a"], m["IP_a"]).fillna(0.0)
        rb = _safe_div(m[f"{c}_b"], m["IP_b"]).fillna(0.0)
        wc = rel_weight(c, w).where(has_a, 0.0).where(has_b, 1.0)
        m[c] = (wc * ra + (1 - wc) * rb) * m["IP"]

    # ZiPS 2027 has no SV column, so saves come from the persistence model
    # applied to the 2026 full-season total.
    m["SV_2026"] = m["SV"].fillna(0.0)
    m["reliever"] = m["reliever"].fillna(True).astype(bool)
    m["SV"] = project_saves(m["SV_2026"], save_model, m["reliever"])

    m["ERA"] = _safe_div(m["ER"] * 9.0, m["IP"])
    m["WHIP"] = _safe_div(m["BB"] + m["H"], m["IP"])
    m["role"] = "PIT"
    m = m[m["IP"] > MIN_IP_PITCHER]
    return m[["fg_id", "name", "role", "w_2026", "reliever", "IP", "W", "SV",
              "SV_2026", "K", "ER", "BB", "H", "ERA", "WHIP"]]


def projected_2027_levels(levels: pd.DataFrame) -> dict:
    """League level (mean team total) to build 2027 denominators against."""
    d = levels[levels["season"].isin(C.LEVEL_SEASONS)]
    return d.groupby("category")["level"].mean().to_dict()
