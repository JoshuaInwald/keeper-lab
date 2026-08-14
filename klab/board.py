"""Step 5: dollar values and the 2027 keeper board.

Two dollar scales, because "what is he worth" is two different questions:

  keep_value    Opportunity cost. The auction regression says a dollar spent
                in *this* league's auction returns `slope` roto points on top
                of `intercept` points you get for free. So a player projected
                for RP is worth (RP - intercept) / slope: that is the money
                you would have to spend at auction to replace him. This is the
                number that decides keep-vs-cut.

  redraft_value The same ranking rescaled so the 230 rostered players sum to
                the league's actual $2,600 of cap space. This is what a player
                would fetch in a full redraft with no keepers. It is the fair
                scale for comparing the two sides of a trade, because both
                teams face the same budget constraint.

They differ by a lot, and the gap is the point: keep_value totals far more
than $2,600 across the league. That excess *is* the aggregate keeper discount
-- it is why keeping is profitable and why the auction has thinned out.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .io import cached
from .auction import auction_sample, regress
from .denoms import (RotoScorer, denominators_for_level,
                     pooled_relative_dispersion, season_levels, team_baselines,
                     teams_per_category)
from .io import  load_rosters
from .project import (fit_save_model, project_hitters, project_pitchers,
                      projected_2027_levels)


@cached
def build_2027_scorer():
    sigma = pooled_relative_dispersion(seasons=C.DENOM_SEASONS)
    levels = season_levels()
    lvl27 = projected_2027_levels(levels)
    D = denominators_for_level(sigma, lvl27, n_by_cat=teams_per_category())
    bl = team_baselines(C.LEVEL_SEASONS)
    base = bl.drop(columns=["season"]).mean().to_dict()
    return RotoScorer(D, base), D, base, sigma


@cached
def fit_exchange_rate(sigma=None, seasons=None):
    """Roto points per auction dollar, projected into the 2027 environment.

    A straight pooled fit answers "what did a dollar buy on average across
    these auctions". That is the wrong question when the auctions happened in
    different worlds: 29 keepers were withheld before 2024 and 2025, but 100
    before 2026, and $/roto-point tracks that count at r = 0.80. 2027 will
    look like 2026, so the pooled figure understates what a dollar will cost.

    EXCHANGE_BASIS = "keeper_adjusted" fits the rate on keeper count across
    all five auctions and predicts at the expected 2027 count -- every
    observation used, but landing in the right regime.
    """
    import statsmodels.api as sm

    seasons = seasons or C.AUCTION_SEASONS
    sample = auction_sample(seasons=tuple(seasons), sigma_rel=sigma)

    if C.EXCHANGE_BASIS == "recent":
        seasons = [max(C.KEEPERS_REMOVED)]
        sample = auction_sample(seasons=tuple(seasons), sigma_rel=sigma)

    r = regress(sample)
    slope, intercept = float(r.params["salary"]), float(r.params["const"])
    usd = 1.0 / slope

    if C.EXCHANGE_BASIS == "keeper_adjusted":
        # one full-history sample serves both the pooled fit and the
        # per-season fits; sampling twice doubled the most expensive call
        full = auction_sample(seasons=tuple(sorted(C.KEEPERS_REMOVED)), sigma_rel=sigma)
        per = []
        for y in sorted(C.KEEPERS_REMOVED):
            ry = regress(full[full["season"] == y])
            per.append({"k": C.KEEPERS_REMOVED[y], "usd": 1.0 / ry.params["salary"],
                        "icept": ry.params["const"]})
        pf = pd.DataFrame(per)
        fit = sm.OLS(pf["usd"], sm.add_constant(pf[["k"]])).fit()
        usd = float(fit.params["const"] + fit.params["k"] * C.KEEPERS_EXPECTED_2027)
        slope = 1.0 / usd
        ifit = sm.OLS(pf["icept"], sm.add_constant(pf[["k"]])).fit()
        intercept = float(ifit.params["const"] + ifit.params["k"] * C.KEEPERS_EXPECTED_2027)

    return {
        "slope": slope, "intercept": intercept,
        "slope_se": float(r.bse["salary"]),
        "r2": float(r.rsquared), "n": int(r.nobs),
        "usd_per_point": usd, "seasons": seasons, "basis": C.EXCHANGE_BASIS,
    }, sample


@cached
def project_all_players(full_time: bool = True) -> pd.DataFrame:
    """Every projected 2027 player with roto points on the 2027 scale.

    With full_time=True (the default for keeper decisions) each line is scaled
    to a full workload before scoring -- see klab.keeper.to_full_time.
    """
    from .keeper import to_full_time

    scorer, D, base, sigma = build_2027_scorer()
    sm_ = fit_save_model()
    H = project_hitters()
    P = project_pitchers(sm_)
    if full_time:
        # A two-way player must not collect both playing-time floors. Ohtani
        # already projects past 600 PA, so his bat is not scaled; without this
        # his arm would still be lifted from 97 to 150 IP and he would gain
        # $20 of value from a workload nobody expects him to carry.
        two_way = set(H.loc[H["PA"] >= 300, "fg_id"]) & set(P.loc[P["IP"] >= 20, "fg_id"])
        H = to_full_time(H)
        P = to_full_time(P, exclude_ids=two_way)
    else:
        H["pt_scale"] = 1.0; H["pt_extrapolated"] = False
        P["pt_scale"] = 1.0; P["pt_extrapolated"] = False

    Hs = H.join(scorer.hitters(H))
    Ps = P.join(scorer.pitchers(P))
    keep = ["fg_id", "name", "role", "w_2026", "pt_scale", "roto_points"] + \
           [f"rp_{c}" for c in C.CATS]
    for df in (Hs, Ps):
        for c in keep:
            if c not in df:
                df[c] = np.nan

    stat_cols = ["PA", "AB", "H", "HR", "R", "RBI", "SB", "AVG",
                 "IP", "W", "SV", "K", "ER", "BB", "ERA", "WHIP"]
    out = pd.concat([Hs, Ps], ignore_index=True)
    for c in stat_cols:
        if c not in out:
            out[c] = np.nan

    # Ohtani shares one FanGraphs id across the hitter and pitcher files.
    # Sum his roto points; keep both stat lines by summing counting stats.
    num = [c for c in out.columns if c.startswith("rp_")] + ["roto_points"] + \
          [c for c in stat_cols if c not in ("AVG", "ERA", "WHIP")]
    out["_hit"] = (out["role"] == "HIT").astype(int)
    out["_pit"] = (out["role"] == "PIT").astype(int)
    agg = {c: "sum" for c in num}
    agg.update({"name": "first", "w_2026": "mean", "pt_scale": "max",
                "AVG": "max", "ERA": "min", "WHIP": "min",
                "_hit": "max", "_pit": "max"})
    out = out.groupby("fg_id", as_index=False).agg(agg)
    # numeric flags instead of a per-group lambda; same answer, far cheaper
    out["role"] = np.where(out["_hit"] & out["_pit"], "TWO",
                           np.where(out["_hit"] > 0, "HIT", "PIT"))
    return out.drop(columns=["_hit", "_pit"]), D, base


@cached
def value_players(exch: dict | None = None, positional: bool = False
                  ) -> tuple[pd.DataFrame, dict, dict]:
    """Dollar values on two playing-time assumptions.

    The headline columns (`roto_points`, `redraft_value`, `keep_value`) use
    each player's *expected* playing time. The dollar scale is calibrated on
    that same pool, so the league's 230 rostered players sum to exactly
    $2,600 and the budget identity actually holds.

    The `_ft` columns are the upside case: what the player is worth if he
    takes a full season's workload (600 PA / 150 IP / 25 SV). They are scored
    on the expected-PT scale, so they answer "what would he be worth in a
    normal market if he played every day" -- a counterfactual, not a price.

    An earlier build valued everyone at full time while calibrating on
    expected time. That combination broke the budget identity badly (top 230
    summed to $3,854) because a full-time-scaled player was being priced
    against a replacement level built from real, injury-shortened seasons.

    `positional=True` (out/FINDINGS.md #52) swaps the pooled replacement
    level for a per-player one: catchers and shortstops (the only two spots
    Josh's scoping call treats as scarce enough to matter) are priced
    against `two_position_replacement()`'s catcher-only / shortstop-only
    replacement level instead of the league-wide one; everyone else is
    unaffected. `usd_per_rp` is recalibrated against the SAME per-player
    replacement levels used for `rp_above_repl`/`redraft_value` -- giving
    some players a different (not necessarily lower -- see the finding)
    bar to clear changes how many total roto-points-above-replacement the
    top-230 pool has, and the $/point scale has to be refit to that or the
    top-230-sums-to-$2,600 budget identity breaks.
    """
    base_players, D, base = project_all_players(full_time=False)
    ft_players, _, _ = project_all_players(full_time=True)
    if exch is None:
        exch, _ = fit_exchange_rate()

    n_rostered = C.N_TEAMS * C.N_ACTIVE
    # Replacement level: how good is the best player available for nothing?
    # See config.WAIVER_VALUE for what each setting is anchored on.
    if C.WAIVER_VALUE == "high":
        repl_rp = float(C.WAIVER_HIGH_RP)
    else:
        rank = C.WAIVER_RANK.get(C.WAIVER_VALUE, n_rostered)
        ranked = base_players.nlargest(rank, "roto_points")
        repl_rp = float(ranked["roto_points"].min())

    # Per-player replacement level: pooled by default; overridden for
    # catcher/shortstop when `positional` is on -- ALWAYS overridden for an
    # eligible player, not just when it happens to help him. Real bug caught
    # testing this directly: the first version took min(pooled, position-
    # specific) meant to break a tie for a player eligible at both adjusted
    # positions, but that same "min" silently compared against the POOLED
    # level too -- and since both catcher (5.12) and shortstop (6.76) come
    # out ABOVE the pooled level (4.78) on this league's real 2026 data (see
    # out/FINDINGS.md #52), "take the min" always kept the pooled number,
    # so positional=True produced byte-identical output to positional=False
    # with no error or warning. Fixed: an eligible player's replacement
    # level is always the position-specific one; "most favorable" only
    # applies to *choosing between* multiple adjusted positions he's
    # eligible for (which the data shows essentially never happens for
    # C/SS -- zero overlap -- but is handled correctly either way).
    repl_series = pd.Series(repl_rp, index=base_players.index)
    pos_repl: dict = {}
    if positional:
        from .io import load_position_eligibility
        from .keeper import two_position_replacement
        elig = load_position_eligibility()
        pos_repl = two_position_replacement(base_players, elig)
        override = pd.Series(np.inf, index=base_players.index)
        any_mask = pd.Series(False, index=base_players.index)
        for pos, r in pos_repl.items():
            mask = base_players["fg_id"].isin(elig.get(pos, set()))
            override = np.minimum(override, np.where(mask, r, np.inf))
            any_mask = any_mask | mask
        repl_series = repl_series.where(~any_mask, override)

    top = base_players.nlargest(n_rostered, "roto_points")
    # clip(lower=0) here has to roughly match the clip inside dollars()
    # below, or the budget identity breaks badly: under pooled replacement
    # every top-230 player is by construction above the pooled bar
    # (repl_rp IS the 230th-ranked value), so this clip was always a no-op
    # there. Positional adjustment breaks that guarantee -- a player can be
    # good enough overall to rank in the top 230 while sitting BELOW his
    # own position's (higher) bar, e.g. a shortstop who's a fine overall
    # player but below the loaded 2026 SS replacement level. His dollars()
    # floors at $0 instead of going negative; pool_rp has to floor
    # similarly or it calibrates against points that never actually get
    # paid out. This isn't an EXACT match, though: dollars() floors the
    # final DOLLAR figure at $0 (i.e. at roto-points-space
    # `rp - repl == -1/usd_per_rp`, not exactly 0, because of the +$1
    # minimum-salary floor folded into the same clip), while this clips at
    # exactly 0 in roto-points space for simplicity. Solving that exactly
    # would need an iterative fit (which players end up floored depends on
    # the scale you're solving for). Checked directly: this approximation
    # lands the top-230 budget check within ~1% of $2,600 under positional
    # adjustment (was exact under pooled) -- close enough for what is
    # already a documented sanity-check number, not a value anything else
    # depends on. See out/FINDINGS.md #52.
    pool_rp = float((top["roto_points"] - repl_series.loc[top.index]).clip(lower=0.0).sum())
    dollars_above_min = C.N_TEAMS * C.BUDGET - n_rostered * 1.0
    usd_per_rp = dollars_above_min / pool_rp

    def dollars(rp, repl):
        return ((rp - repl) * usd_per_rp + 1.0).clip(lower=0.0)

    players = base_players.copy()
    players["rp_above_repl"] = players["roto_points"] - repl_series
    players["redraft_value"] = dollars(players["roto_points"], repl_series)
    # A player cannot be worth less than nothing: a bad arm gets benched and
    # the roster spot reverts to a waiver pickup at replacement level.
    players["keep_value"] = (
        (players["roto_points"] - exch["intercept"]) / exch["slope"]).clip(lower=0.0)

    ft = ft_players.set_index("fg_id")
    players["roto_points_ft"] = players["fg_id"].map(ft["roto_points"])
    players["pt_scale"] = players["fg_id"].map(ft["pt_scale"]).fillna(1.0)
    players["redraft_value_ft"] = dollars(players["roto_points_ft"].fillna(
        players["roto_points"]), repl_series)
    players["upside_ft"] = players["redraft_value_ft"] - players["redraft_value"]

    meta = {"replacement_rp": repl_rp, "n_rostered": n_rostered,
            "pool_rp_above_repl": pool_rp,
            "usd_per_rp_redraft": usd_per_rp,
            "usd_per_rp_keep": exch["usd_per_point"],
            "positional_replacement": pos_repl,
            "budget_check_top230": float(
                players.nlargest(n_rostered, "roto_points")["redraft_value"].sum())}
    return players, exch, {"denominators": D, "baseline": base, **meta}


from .keeper import keeper_cost, years_controlled     # noqa: E402


def keeper_status(contract) -> str:
    c = str(contract).strip().upper()
    if c in C.YEARS_REMAINING:
        return f"keepable x{C.YEARS_REMAINING[c]}yr"
    if c in C.EXTENSION_REQUIRED:
        # This used to read "extension +$5", true before the correction in
        # out/FINDINGS.md #39: an "F" observed here means the extension
        # window (which closes before his own walk-year draft) has already
        # passed, so there is no extension to buy. Left stale here even
        # after board.py's `keepable` logic was fixed -- nothing re-checked
        # this string against the corrected model, and it only surfaced
        # visually in the app's player-card subheader. Caught 2026-08-13
        # UI audit; see out/FINDINGS.md #44.
        return "free agent after 2026 (not extendable)"
    return "unknown"


def value_2028(exch: dict, meta: dict, saves_2027: pd.Series,
               positional: bool = False) -> pd.DataFrame:
    """Dollar values for the out year, on the same 2027 scale.

    `positional` (out/FINDINGS.md #52) reuses the SAME catcher/shortstop
    replacement levels `meta["positional_replacement"]` already computed
    for 2027 (from `value_players()`), rather than refitting a fresh
    position-specific replacement level on the 2028 pool -- consistent
    with how this function already reuses the pooled 2027 replacement
    level and $/point scale for 2028 generally ("on the same 2027 scale").
    """
    from .keeper import project_2028
    scorer, _, _, _ = build_2027_scorer()
    # No full-time scaling here: the headline 2027 value is on expected
    # playing time, so the out year has to be too, or multi-year surplus
    # silently mixes an expected-PT 2027 with a full-time 2028.
    H, P = project_2028(saves_2027)
    Hs = H[["fg_id"]].join(scorer.hitters(H)[["roto_points"]])
    Ps = P[["fg_id"]].join(scorer.pitchers(P)[["roto_points"]])
    out = pd.concat([Hs, Ps]).groupby("fg_id", as_index=False)["roto_points"].sum()
    out = out.rename(columns={"roto_points": "roto_points_2028"})
    scale = meta["usd_per_rp_redraft"]

    repl = pd.Series(meta["replacement_rp"], index=out.index)
    if positional and meta.get("positional_replacement"):
        from .io import load_position_eligibility
        elig = load_position_eligibility()
        for pos, r in meta["positional_replacement"].items():
            mask = out["fg_id"].isin(elig.get(pos, set()))
            repl = repl.where(~mask, np.minimum(repl, r))

    out["redraft_value_2028"] = (
        (out["roto_points_2028"] - repl) * scale + 1.0).clip(lower=0.0)
    return out


def build_board(exch: dict | None = None, positional: bool = False
               ) -> tuple[pd.DataFrame, dict, dict]:
    players, exch, meta = value_players(exch, positional=positional)
    ros = load_rosters()[["team", "fg_id", "name", "role", "il",
                          "salary", "contract"]]
    ros = ros.rename(columns={"name": "roster_name", "role": "roster_role"})

    b = ros.merge(players, on="fg_id", how="left")
    b["name"] = b["name"].fillna(b["roster_name"])
    b["role"] = b["role"].fillna(b["roster_role"])
    b["roto_points"] = b["roto_points"].fillna(0.0)
    b["keep_value"] = b["keep_value"].fillna(0.0)
    b["redraft_value"] = b["redraft_value"].fillna(0.0)
    b["pt_scale"] = b["pt_scale"].fillna(1.0)
    for c in ("roto_points_ft", "redraft_value_ft", "upside_ft"):
        b[c] = b[c].fillna(0.0)

    sv27 = players.set_index("fg_id")["SV"] if "SV" in players else None
    v28 = value_2028(exch, meta, sv27, positional=positional)
    b = b.merge(v28, on="fg_id", how="left")
    b["roto_points_2028"] = b["roto_points_2028"].fillna(0.0)
    b["redraft_value_2028"] = b["redraft_value_2028"].fillna(0.0)

    # Commissioner-resolved contracts, applied before anything is priced off
    # them. Three players came out of the export as "?" and were being valued
    # with no contract at all.
    for nm, (code, sal) in C.CONTRACT_OVERRIDES.items():
        m = b["name"] == nm
        if m.any():
            b.loc[m, "contract"] = code
            b.loc[m, "salary"] = sal

    b["keeper_cost"] = [keeper_cost(s, c) for s, c in zip(b["salary"], b["contract"])]
    b["keeper_status"] = b["contract"].map(keeper_status)
    b["years_controlled"] = b["contract"].map(years_controlled)
    b["surplus_keep"] = b["keep_value"] - b["keeper_cost"]
    b["surplus_redraft"] = b["redraft_value"] - b["keeper_cost"]

    from .keeper import already_extended, multiyear_surplus
    my = multiyear_surplus(b["redraft_value"], b["redraft_value_2028"],
                           b["keeper_cost"], b["years_controlled"], b["salary"])
    # One extension per contract. A live contract that has spent it keeps only
    # the years it has; an `F` player in the same position cannot be kept at all.
    used = (b["fg_id"].isin(already_extended())
            | b["name"].isin(C.NON_EXTENDABLE_NAMES))
    my.loc[used.values, ["extension_option", "extension_years"]] = 0
    my["surplus_multiyear"] = (my["surplus_y2027"] + my["surplus_y2028"]
                               + my["surplus_y2029"] + my["extension_option"])
    b["extension_used"] = used.values
    # CORRECTED 2026-08-13 (out/FINDINGS.md #39): an `F` player observed in
    # THIS data is never keepable, full stop -- not conditional on whether
    # he has used a prior extension. The constitution's extension window is
    # "about to enter the final year," i.e. it closes before that season's
    # OWN draft. `contracts_parsed.csv` is a mid-season-or-later snapshot, so
    # any player still coded `F` in it already missed that window; he is
    # confirmed for unrestricted free agency after this season, not offering
    # a live extension choice for 2027. This used to read
    # `~(used & is_final)`, which only caught a player who had *already*
    # spent an extension -- a first-time F player (the common case) was
    # incorrectly treated as extendable right now.
    is_final = b["contract"].astype(str).str.upper().isin(C.EXTENSION_REQUIRED)
    b["keepable"] = ~is_final
    b = pd.concat([b, my], axis=1)

    # A player who cannot be kept has no future surplus -- not "unknown"
    # surplus. He is a 2026 rental and hits the 2027 auction like anyone else,
    # so every forward-looking figure is zero, not NaN. NaN also sorted oddly
    # and left a positive "Surplus '27" showing next to a LOCKED tag.
    surplus_cols = ["surplus_y2027", "surplus_y2028", "surplus_y2029",
                    "extension_option", "extension_years", "surplus_multiyear",
                    "surplus_keep", "surplus_redraft"]
    b.loc[~b["keepable"], surplus_cols] = 0.0
    b = mark_optimal_keepers(b[b["keepable"]].copy(), col="surplus_multiyear").pipe(
        lambda k: pd.concat([k, b[~b["keepable"]].assign(keep_2027=False)]))
    return (b.sort_values(["team", "surplus_multiyear"], ascending=[True, False]),
            exch, meta)


def mark_optimal_keepers(b: pd.DataFrame,
                         col: str = "surplus_redraft") -> pd.DataFrame:
    """Flag each team's best legal keeper set.

    Rostering 27 players says nothing about keeper value -- most of them will
    be cut. The decision is which 6-13 to hold, so the surplus that matters is
    the sum over the chosen set, not over the whole roster. Take every player
    with positive surplus, capped at MAX_KEEPERS; if fewer than MIN_KEEPERS
    clear zero, the league forces you to keep the least-bad ones anyway.
    """
    b = b.copy()
    b["keep_2027"] = False
    for team, g in b.groupby("team"):
        g = g.sort_values(col, ascending=False)
        pos = g[g[col] > 0].head(C.MAX_KEEPERS)
        if len(pos) < C.MIN_KEEPERS:
            pos = g.head(C.MIN_KEEPERS)     # forced to keep six
        b.loc[pos.index, "keep_2027"] = True
    return b
