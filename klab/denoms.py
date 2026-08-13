"""Step 1 + 2: marginal roto points per stat unit.

A roto "denominator" for a category is the number of stat units that buys one
standings point. In a 10-team roto league the points are ranks, so the natural
estimator is the average gap between adjacent teams in the final standings.

Three estimators are computed so the choice is visible rather than assumed:
  range      (max - min) / (N - 1)          -- classic, outlier-sensitive
  trimmed    drop the top and bottom team   -- robust to tanks/juggernauts
  median_gap median of the N-1 adjacent gaps-- most robust, downward-biased

Rate categories (AVG/ERA/WHIP) get denominators in rate units; converting a
player into rate-category roto points needs a league-average team baseline,
which `team_baselines()` estimates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .io import cached
from .io import  load_hitters_history, load_pitchers_history, load_standings_long


# --- denominator estimators -------------------------------------------------

def _gaps(values: np.ndarray) -> np.ndarray:
    v = np.sort(np.asarray(values, dtype=float))
    return np.diff(v)


def denom_estimators(values) -> dict:
    """Four estimators of "stat units per standings point".

    `range` and `trimmed` are determined by 2 of the N observations, which is
    why they swing hard year to year in a 10-team league. `sd` and `slope`
    use all N and are the ones worth trusting.
    """
    v = np.sort(np.asarray(values, dtype=float))
    n = len(v)
    out = {"n_teams": n}
    out["range"] = (v[-1] - v[0]) / (n - 1) if n > 1 else np.nan
    out["trimmed"] = (v[-2] - v[1]) / (n - 3) if n > 3 else np.nan
    g = _gaps(v)
    out["median_gap"] = float(np.median(g)) if len(g) else np.nan

    # sd-based: for a normal sample of size n the expected range is c_n * sd,
    # so the average adjacent gap is c_n/(n-1) * sd. Uses every team.
    c_n = {8: 2.847, 9: 2.970, 10: 3.078}.get(n, 3.078)
    out["sd"] = float(np.std(v, ddof=1) * c_n / (n - 1)) if n > 1 else np.nan

    # slope-based: regress standings points (1..n) on the stat total. The
    # inverse slope is literally "stat units bought per standings point".
    if n > 2:
        pts = np.arange(1, n + 1, dtype=float)
        b = np.polyfit(v, pts, 1)[0]
        out["slope"] = float(1.0 / b) if b != 0 else np.nan
    else:
        out["slope"] = np.nan

    # iqr-based: sd estimated from the middle half of the standings, so a
    # single tanking or juggernaut team cannot move it. This is the default.
    q75, q25 = np.percentile(v, [75, 25])
    sd_hat = (q75 - q25) / 1.349
    out["iqr"] = float(sd_hat * c_n / (n - 1)) if n > 1 else np.nan
    return out


def denominator_table(standings: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-season, per-category denominators with SV punters removed."""
    st = standings if standings is not None else load_standings_long()
    rows = []
    for (season, cat), grp in st.groupby(["season", "category"]):
        vals = grp["total"].astype(float).values
        n_dropped = 0
        if cat == "SV":
            keep = vals >= C.SV_PUNT_THRESHOLD
            n_dropped = int((~keep).sum())
            vals = vals[keep]
        est = denom_estimators(vals)
        rows.append({
            "season": season, "category": cat,
            "n_dropped_punters": n_dropped,
            "min": float(np.min(vals)), "max": float(np.max(vals)),
            "mean": float(np.mean(vals)),
            **est,
        })
    return pd.DataFrame(rows).sort_values(["category", "season"])


@cached
def pooled_relative_dispersion(standings: pd.DataFrame | None = None,
                               seasons=None) -> pd.DataFrame:
    """Estimate each category's dispersion as a fraction of its league mean,
    pooling team-seasons.

    Estimating sigma from 10 teams in a single year is hopeless -- the
    year-to-year CV of any single-season denominator runs 0.25-0.75. Pooling
    N seasons of 10 teams (after dividing each season by its own league mean,
    so level shifts like the 2023 stolen-base rule change wash out) estimates
    the same quantity off 40 observations instead of 10.

    Returns sigma_rel = sd(total / season_mean), plus its standard error.
    """
    st = standings if standings is not None else load_standings_long()
    seasons = seasons or C.DENOM_SEASONS
    rows = []
    for cat, g in st.groupby("category"):
        vals = []
        for s in seasons:
            if cat == "SB" and s < C.SB_REGIME_START:
                continue        # pre-rule-change stolen bases are a different game
            if (C.DENOM_EXCLUDE_PARTIAL_FOR_RATES and cat in C.RATE_CATS
                    and s in C.PARTIAL_SEASONS):
                continue        # see config.PARTIAL_SEASONS -- a rate stat is
                                # over-dispersed while its denominator is still
                                # accumulating innings and at-bats
            gs = g[g["season"] == s]["total"].astype(float).values
            if cat == "SV":
                gs = gs[gs >= C.SV_PUNT_THRESHOLD]
            if len(gs) < 3:
                continue
            vals.append(gs / gs.mean())
        if not vals:
            continue
        pooled = np.concatenate(vals)
        n = len(pooled)
        sigma_rel = float(np.std(pooled, ddof=1))
        rows.append({
            "category": cat,
            "sigma_rel": sigma_rel,
            "se_sigma_rel": sigma_rel / np.sqrt(2 * (n - 1)),
            "n_team_seasons": n,
            "n_seasons": len(vals),
        })
    out = pd.DataFrame(rows).set_index("category")
    return out.loc[[c for c in C.CATS if c in out.index]].reset_index()


C_N = {6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}


def denominators_for_level(sigma_rel: pd.DataFrame, levels: dict,
                           n_teams: int = C.N_TEAMS,
                           n_by_cat: dict | None = None) -> dict:
    """Convert pooled relative dispersion + a league level into denominators.

    `levels` maps category -> that season's mean team total.

    The bridge from sigma to "units per standings point" is
    E[range]/(n-1) = c_n * sigma / (n - 1), and c_n depends on how many teams
    are actually in the comparison. Saves are the case that matters: after
    punters are excluded the SV field is 8 or 9 teams, not 10, and applying
    the 10-team constant there understates the SV denominator by 9-19% --
    which overvalues every closer in the league by the same margin.
    """
    s = sigma_rel.set_index("category")["sigma_rel"]
    n_by_cat = n_by_cat or {}
    out = {}
    for cat in s.index:
        if cat not in levels:
            continue
        n = int(n_by_cat.get(cat, n_teams))
        k = C_N.get(n, 3.078) / max(n - 1, 1)
        out[cat] = float(s[cat] * levels[cat] * k)
    return out


@cached
def teams_per_category(standings: pd.DataFrame | None = None,
                       seasons=None) -> dict:
    """Mean size of the field actually compared in each category."""
    st = standings if standings is not None else load_standings_long()
    seasons = seasons or C.DENOM_SEASONS
    out = {}
    for cat, g in st.groupby("category"):
        ns = []
        for s in seasons:
            v = g[g["season"] == s]["total"].astype(float).values
            if cat == "SV":
                v = v[v >= C.SV_PUNT_THRESHOLD]
            if len(v):
                ns.append(len(v))
        out[cat] = float(np.mean(ns)) if ns else C.N_TEAMS
    return {k: int(round(v)) for k, v in out.items()}


@cached
def season_levels(standings: pd.DataFrame | None = None) -> pd.DataFrame:
    """Mean team total per category per season (SV punters excluded for SV)."""
    st = standings if standings is not None else load_standings_long()
    rows = []
    for (season, cat), g in st.groupby(["season", "category"]):
        v = g["total"].astype(float).values
        if cat == "SV":
            v = v[v >= C.SV_PUNT_THRESHOLD]
        rows.append({"season": season, "category": cat, "level": float(v.mean())})
    return pd.DataFrame(rows)


# --- league-average team baselines (for rate categories) --------------------

@cached
def team_baselines(seasons=None) -> pd.DataFrame:
    """Estimate a league-average fantasy team's AB/H and IP/ER/(H+BB).

    Standings give team AVG/ERA/WHIP but not the volume behind them. We
    reconstruct volume by taking the MLB players who would plausibly fill the
    league's roster slots (top 14*N by PA, top 9*N by IP), then rescaling that
    pool's playing time by how much of its counting production the league
    actually banked. That rescale is the "roster realization" factor: it
    absorbs IL days, empty slots and bench players who never accumulate.
    """
    seasons = seasons or C.DENOM_SEASONS
    st = load_standings_long()
    hit = load_hitters_history()
    pit = load_pitchers_history()

    rows = []
    for s in seasons:
        ss = st[st["season"] == s]
        wide = ss.pivot_table(index="team", columns="category", values="total")
        n_teams = len(wide)

        # --- hitters
        pool = hit[hit["season"] == s].nlargest(C.N_HIT_SLOTS * n_teams, "PA")
        implied = []
        for cat in ("HR", "R", "RBI"):
            if pool[cat].sum() > 0:
                implied.append(wide[cat].sum() / pool[cat].sum())
        realization_h = float(np.mean(implied))
        team_AB = pool["AB"].sum() * realization_h / n_teams
        team_AVG = float(wide["AVG"].mean())
        team_H = team_AB * team_AVG

        # --- pitchers
        ppool = pit[pit["season"] == s].nlargest(C.N_PIT_SLOTS * n_teams, "IP")
        implied_p = []
        for cat in ("K", "W"):
            if ppool[cat].sum() > 0:
                implied_p.append(wide[cat].sum() / ppool[cat].sum())
        realization_p = float(np.mean(implied_p))
        team_IP = ppool["IP"].sum() * realization_p / n_teams
        team_ERA = float(wide["ERA"].mean())
        team_WHIP = float(wide["WHIP"].mean())
        team_ER = team_IP * team_ERA / 9.0
        team_WH = team_IP * team_WHIP

        rows.append({
            "season": s, "n_teams": n_teams,
            "realization_hit": realization_h, "realization_pit": realization_p,
            "team_AB": team_AB, "team_H": team_H, "team_AVG": team_AVG,
            "team_IP": team_IP, "team_ER": team_ER, "team_WH": team_WH,
            "team_ERA": team_ERA, "team_WHIP": team_WHIP,
        })
    return pd.DataFrame(rows)


# --- player -> roto points --------------------------------------------------

class RotoScorer:
    """Turn a player stat line into roto points using fixed denominators."""

    def __init__(self, denoms: dict, baseline: dict):
        self.d = denoms
        self.b = baseline
        h = C.N_HIT_SLOTS
        p = C.N_PIT_SLOTS
        # A league-average team minus one slot: the counterfactual the player
        # is being dropped into.
        self.base_AB = baseline["team_AB"] * (h - 1) / h
        self.base_H = baseline["team_H"] * (h - 1) / h
        self.base_IP = baseline["team_IP"] * (p - 1) / p
        self.base_ER = baseline["team_ER"] * (p - 1) / p
        self.base_WH = baseline["team_WH"] * (p - 1) / p
        self.lg_AVG = baseline["team_AVG"]
        self.lg_ERA = baseline["team_ERA"]
        self.lg_WHIP = baseline["team_WHIP"]

    def hitters(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        for cat in ("R", "HR", "RBI", "SB"):
            out[f"rp_{cat}"] = df[cat].fillna(0) / self.d[cat]
        new_avg = (self.base_H + df["H"].fillna(0)) / (self.base_AB + df["AB"].fillna(0))
        out["rp_AVG"] = (new_avg - self.lg_AVG) / self.d["AVG"]
        out["roto_points"] = out.filter(like="rp_").sum(axis=1)
        return out

    def pitchers(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        for cat in ("W", "SV", "K"):
            out[f"rp_{cat}"] = df[cat].fillna(0) / self.d[cat]
        ip = df["IP"].fillna(0)
        new_era = (self.base_ER + df["ER"].fillna(0)) * 9.0 / (self.base_IP + ip)
        out["rp_ERA"] = (self.lg_ERA - new_era) / self.d["ERA"]
        wh = df["BB"].fillna(0) + df["H"].fillna(0)
        new_whip = (self.base_WH + wh) / (self.base_IP + ip)
        out["rp_WHIP"] = (self.lg_WHIP - new_whip) / self.d["WHIP"]
        out["roto_points"] = out.filter(like="rp_").sum(axis=1)
        return out
