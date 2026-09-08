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

Two further columns split "worth" from "cost" (docs/ROADMAP.md item 1 Step 0):

  production_value  Alias of `redraft_value`, byte-identical by construction.
                It is what a player is worth TO A ROSTER on a budget scale, a
                production quantity, not a price anyone will pay.

  market_price  What he will actually COST at this league's auction. Fitted by
                `scripts/price_model.py` from 677 revealed purchases; NaN here
                until ROADMAP item 1 Step 3 calibrates the level to the 2027
                budget. The gap `production_value - market_price` is the
                buy/sell signal. Never blend the two (CONSTRAINTS.md).
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
    n_by_cat = teams_per_category()
    D = denominators_for_level(sigma, lvl27, n_by_cat=n_by_cat)
    # SE of each denominator: denom is linear in sigma_rel, so run
    # se_sigma_rel through the same conversion rather than separate algebra.
    D_se = denominators_for_level(sigma.assign(sigma_rel=sigma["se_sigma_rel"]),
                                  lvl27, n_by_cat=n_by_cat)
    bl = team_baselines(C.LEVEL_SEASONS)
    base = bl.drop(columns=["season"]).mean().to_dict()
    return RotoScorer(D, base), D, base, D_se


@cached
def fit_exchange_rate(sigma=None, seasons=None):
    """Roto points per auction dollar, projected into the 2027 environment.

    $/roto-point tracks the keeper count withheld before each auction
    (r = 0.80; 29 in 2024-25 vs 100 in 2026), so EXCHANGE_BASIS =
    "keeper_adjusted" fits the rate on keeper count and predicts at the
    expected 2027 count instead of pooling two different regimes.
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
        # one full-history sample serves both fits (sampling twice was slow)
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

    scorer, D, base, D_se = build_2027_scorer()
    sm_ = fit_save_model()
    H = project_hitters()
    P = project_pitchers(sm_)
    if full_time:
        # A two-way player must not collect both PT floors (his arm was once
        # lifted 97 -> 150 IP, +$20, from a workload nobody expects).
        two_way = set(H.loc[H["PA"] >= 300, "fg_id"]) & set(P.loc[P["IP"] >= 20, "fg_id"])
        H = to_full_time(H)
        P = to_full_time(P, exclude_ids=two_way)
    else:
        H["pt_scale"] = 1.0; H["pt_extrapolated"] = False; H["pt_scale_kind"] = "health"
        P["pt_scale"] = 1.0; P["pt_extrapolated"] = False; P["pt_scale_kind"] = "health"

    Hs = H.join(scorer.hitters(H))
    Ps = P.join(scorer.pitchers(P))
    keep = ["fg_id", "name", "role", "w_2026", "pt_scale", "pt_scale_kind", "roto_points"] + \
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

    # Incidental two-way rows (mop-up pitching, token PA) are combined into
    # one row; a true two-way player (TWO_WAY_SPLIT_NAMES) is kept as two.
    split_names = out["name"].isin(C.TWO_WAY_SPLIT_NAMES)
    split_rows = out[split_names].copy()
    out = out[~split_names]

    num = [c for c in out.columns if c.startswith("rp_")] + ["roto_points"] + \
          [c for c in stat_cols if c not in ("AVG", "ERA", "WHIP")]
    out["_hit"] = (out["role"] == "HIT").astype(int)
    out["_pit"] = (out["role"] == "PIT").astype(int)
    agg = {c: "sum" for c in num}
    agg.update({"name": "first", "w_2026": "mean", "pt_scale": "max",
                "pt_scale_kind": "first",
                "AVG": "max", "ERA": "min", "WHIP": "min",
                "_hit": "max", "_pit": "max"})
    out = out.groupby("fg_id", as_index=False).agg(agg)
    out["role"] = np.where(out["_hit"] & out["_pit"], "TWO",
                           np.where(out["_hit"] > 0, "HIT", "PIT"))
    out = out.drop(columns=["_hit", "_pit"])
    return pd.concat([out, split_rows], ignore_index=True), D, base, D_se


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

    Valuing at full time while calibrating on expected time once broke the
    budget identity (top 230 summed to $3,854); both must use the same pool.

    `positional=True` (docs/FINDINGS.md #52) prices catchers/shortstops
    against `two_position_replacement()`'s level; `usd_per_rp` is refit
    against the SAME per-player levels or the $2,600 identity breaks.
    """
    base_players, D, base, D_se = project_all_players(full_time=False)
    ft_players, _, _, _ = project_all_players(full_time=True)
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

    # Replacement level must be position-specific for every eligible player;
    # min(pooled, pos) silently no-op'd since C/SS sit ABOVE pooled (FINDINGS #52).
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
    # clip(lower=0) must roughly match dollars()'s $0 floor: under positional
    # adjustment a top-230 player can sit below his own bar (FINDINGS #52; ~1%).
    pool_rp = float((top["roto_points"] - repl_series.loc[top.index]).clip(lower=0.0).sum())
    dollars_above_min = C.N_TEAMS * C.BUDGET - n_rostered * 1.0
    usd_per_rp = dollars_above_min / pool_rp

    def dollars(rp, repl):
        return ((rp - repl) * usd_per_rp + 1.0).clip(lower=0.0)

    players = base_players.copy()
    players["rp_above_repl"] = players["roto_points"] - repl_series
    players["redraft_value"] = dollars(players["roto_points"], repl_series)
    # production_value is redraft_value under the name that says what it is:
    # worth to a roster, not a price. market_price (the auction cost) is a
    # separate quantity and stays NaN until Step 3 calibrates its level.
    players["production_value"] = players["redraft_value"]
    players["market_price"] = np.nan
    # A player cannot be worth less than nothing (bench him, use the wire).
    players["keep_value"] = (
        (players["roto_points"] - exch["intercept"]) / exch["slope"]).clip(lower=0.0)

    # Merge on (fg_id, role), not a fg_id-keyed .map(): a two-way player
    # (TWO_WAY_SPLIT_NAMES) has two rows per fg_id, which breaks .map().
    ft = ft_players[["fg_id", "role", "roto_points", "pt_scale", "pt_scale_kind"]].rename(
        columns={"roto_points": "roto_points_ft", "pt_scale": "pt_scale_full",
                "pt_scale_kind": "pt_scale_kind_full"})
    players = players.merge(ft, on=["fg_id", "role"], how="left")
    players["pt_scale"] = players["pt_scale_full"].fillna(1.0)
    players = players.drop(columns=["pt_scale_full"])
    players["redraft_value_ft"] = dollars(players["roto_points_ft"].fillna(
        players["roto_points"]), repl_series)
    players["upside_ft"] = players["redraft_value_ft"] - players["redraft_value"]
    # Which floor produced upside_ft (FINDINGS #53): "health" = full healthy
    # workload; "role" = 5+ save reliever handed the closer job, a weaker bet.
    players["upside_kind"] = players["pt_scale_kind_full"].fillna("health")
    players = players.drop(columns=["pt_scale_kind_full"])

    meta = {"replacement_rp": repl_rp, "n_rostered": n_rostered,
            "pool_rp_above_repl": pool_rp,
            "usd_per_rp_redraft": usd_per_rp,
            "usd_per_rp_keep": exch["usd_per_point"],
            "positional_replacement": pos_repl,
            "budget_check_top230": float(
                players.nlargest(n_rostered, "roto_points")["redraft_value"].sum())}
    return players, exch, {"denominators": D, "denominators_se": D_se, "baseline": base, **meta}


from .keeper import keeper_cost, years_controlled     # noqa: E402


def keeper_status(contract) -> str:
    c = str(contract).strip().upper()
    if c in C.YEARS_REMAINING:
        return f"keepable x{C.YEARS_REMAINING[c]}yr"
    if c in C.EXTENSION_REQUIRED:
        # "F" = extension window already closed, nothing to buy (FINDINGS
        # #39); this string once still said "extension +$5" (FINDINGS #44).
        return "free agent after 2026 (not extendable)"
    return "unknown"


def value_2028(exch: dict, meta: dict, saves_2027: pd.Series,
               positional: bool = False) -> pd.DataFrame:
    """Dollar values for the out year, on the same 2027 scale.

    `positional` (docs/FINDINGS.md #52) reuses the 2027 catcher/shortstop
    replacement levels in `meta["positional_replacement"]`, as the pooled
    2027 level and $/point scale are reused for 2028 generally.
    """
    from .keeper import project_2028
    scorer, _, _, _ = build_2027_scorer()
    # No full-time scaling: 2027 is on expected PT, so 2028 must be too.
    H, P = project_2028(saves_2027)
    Hs = H[["fg_id", "name"]].join(scorer.hitters(H)[["roto_points"]])
    Ps = P[["fg_id", "name"]].join(scorer.pitchers(P)[["roto_points"]])
    Hs["role"], Ps["role"] = "HIT", "PIT"
    both = pd.concat([Hs, Ps], ignore_index=True)

    # Mirror project_all_players()'s split: a two-way player keeps separate
    # 2028 lines (role non-null); summing would give both 2027 rows the total.
    split_names = both["name"].isin(C.TWO_WAY_SPLIT_NAMES)
    split_rows = both[split_names][["fg_id", "role", "roto_points"]]
    combined = (both[~split_names].groupby("fg_id", as_index=False)["roto_points"].sum()
               .assign(role=None))
    out = pd.concat([combined, split_rows], ignore_index=True)
    out = out.rename(columns={"roto_points": "roto_points_2028"})
    scale = meta["usd_per_rp_redraft"]

    repl = pd.Series(meta["replacement_rp"], index=out.index)
    if positional and meta.get("positional_replacement"):
        # Same override/any_mask pattern as value_players(): min(pooled, pos)
        # silently no-op'd here too (FINDINGS #52, #53).
        from .io import load_position_eligibility
        elig = load_position_eligibility()
        override = pd.Series(np.inf, index=out.index)
        any_mask = pd.Series(False, index=out.index)
        for pos, r in meta["positional_replacement"].items():
            mask = out["fg_id"].isin(elig.get(pos, set()))
            override = np.minimum(override, np.where(mask, r, np.inf))
            any_mask = any_mask | mask
        repl = repl.where(~any_mask, override)

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
    # Alias, so it must survive the same fillna. market_price is filled later
    # by attach_market_price(), which needs the keeper set to set its level.
    b["production_value"] = b["redraft_value"]
    b["pt_scale"] = b["pt_scale"].fillna(1.0)
    for c in ("roto_points_ft", "redraft_value_ft", "upside_ft"):
        b[c] = b[c].fillna(0.0)

    # groupby().max(), not set_index(): a two-way player has two rows per
    # fg_id and a duplicate index breaks .map() inside project_saves().
    sv27 = players.groupby("fg_id")["SV"].max() if "SV" in players else None
    v28 = value_2028(exch, meta, sv27, positional=positional)
    # Two-way rows (role non-null in v28) merge on (fg_id, role) or a plain
    # fg_id merge cartesian-joins them 2x2; everyone else merges on fg_id.
    v28_normal = v28[v28["role"].isna()].drop(columns=["role"])
    v28_split = v28[v28["role"].notna()]
    two_way_ids = set(v28_split["fg_id"])
    b_normal = b[~b["fg_id"].isin(two_way_ids)].merge(v28_normal, on="fg_id", how="left")
    b_split = b[b["fg_id"].isin(two_way_ids)].merge(v28_split, on=["fg_id", "role"], how="left")
    b = pd.concat([b_normal, b_split], ignore_index=True)
    b["roto_points_2028"] = b["roto_points_2028"].fillna(0.0)
    b["redraft_value_2028"] = b["redraft_value_2028"].fillna(0.0)

    # Commissioner-resolved contracts ("?" in the export), applied before
    # anything is priced off them.
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
    # Every `F` player is unkeepable unconditionally -- the extension window
    # closed before his own draft; `~(used & is_final)` missed first-timers (FINDINGS #39).
    is_final = b["contract"].astype(str).str.upper().isin(C.EXTENSION_REQUIRED)
    b["keepable"] = ~is_final
    b = pd.concat([b, my], axis=1)

    # Unkeepable = zero forward surplus, not NaN (NaN sorted oddly and showed
    # a positive Surplus '27 next to a LOCKED tag).
    surplus_cols = ["surplus_y2027", "surplus_y2028", "surplus_y2029",
                    "extension_option", "extension_years", "surplus_multiyear",
                    "surplus_keep", "surplus_redraft"]
    b.loc[~b["keepable"], surplus_cols] = 0.0
    b = mark_optimal_keepers(b[b["keepable"]].copy(), col="surplus_multiyear").pipe(
        lambda k: pd.concat([k, b[~b["keepable"]].assign(keep_2027=False)]))

    b, price_meta = attach_market_price(b, players)
    meta.update(price_meta)
    return (b.sort_values(["team", "surplus_multiyear"], ascending=[True, False]),
            exch, meta)


def _market_surplus(b: pd.DataFrame, priced: pd.DataFrame, k: float) -> pd.DataFrame:
    """Market-basis surplus columns for a given price scale."""
    from .price import market_price_2028
    from .keeper import multiyear_surplus
    out = pd.DataFrame(index=b.index)
    out["market_price"] = priced["pred"].to_numpy()
    out["market_price_lo"] = priced["p20"].to_numpy()
    out["market_price_hi"] = priced["p80"].to_numpy()
    tmp = b.assign(market_price=out["market_price"])
    out["market_price_2028"] = market_price_2028(tmp, k).to_numpy()
    # ROADMAP item 1 Step 4: the cost of NOT keeping him is what it takes to buy
    # him back at auction, so the arbitrage on a contract is market price minus
    # keeper cost. `surplus_redraft`/`surplus_multiyear` keep answering the
    # other question (what the roster spot is worth) and are left alone.
    out["surplus_market"] = out["market_price"] - b["keeper_cost"]
    mm = multiyear_surplus(out["market_price"], out["market_price_2028"],
                           b["keeper_cost"], b["years_controlled"], b["salary"])
    out["surplus_multiyear_market"] = mm["surplus_multiyear"].to_numpy()
    out.loc[~b["keepable"], ["surplus_market", "surplus_multiyear_market"]] = 0.0
    return out


def _market_keeper_set(b: pd.DataFrame, priced: pd.DataFrame, k: float):
    """Each team's best legal keeper set under the market basis."""
    s = _market_surplus(b, priced, k)
    sub = b.assign(surplus_multiyear_market=s["surplus_multiyear_market"])
    sub = sub[sub["keepable"]].copy()
    mk = mark_optimal_keepers(sub, col="surplus_multiyear_market")
    flag = pd.Series(False, index=b.index)
    flag.loc[mk.index] = mk["keep_2027"].to_numpy()
    return flag.to_numpy()


def attach_market_price(b: pd.DataFrame, players: pd.DataFrame
                       ) -> tuple[pd.DataFrame, dict]:
    """Fill `market_price` (ROADMAP item 1 Step 3, docs/FINDINGS.md #56).

    The level is set by the money that will actually be in the room: the lots
    the 2027 auction will sell must sum to $2,600 minus committed keeper
    salaries. Calibration uses the auction POOL (everyone projected who is not
    a keeper) so free agents count toward the lot count; the resulting scale is
    then applied to keepers too, because "what would he cost if I threw him
    back" is exactly the keeper question.
    """
    from .price import (apply_scale, calibrate_to_budget, raw_prices_2027,
                        role_ceiling)


    # Fixed point: the price LEVEL depends on how much salary the keepers tie
    # up, and once surplus is measured in market dollars the keeper set depends
    # on the price level. Seeding with the production-based set gave 70 keepers
    # and a set of prices implying 88, which is not a consistent answer to
    # anything. Iterate until the keeper set stops moving.
    raw_all = raw_prices_2027(b)
    ceiling = role_ceiling(b["role"])
    keys = pd.Series(list(zip(players["fg_id"], players["role"])), index=players.index)
    kept_mask = b["keep_2027"].to_numpy().copy()
    cal = None
    for _ in range(10):
        kept = b[kept_mask]
        pool = players[~keys.isin(set(zip(kept["fg_id"], kept["role"])))]
        cal = calibrate_to_budget(pool, raw_prices_2027(pool), len(kept),
                                  float(kept["keeper_cost"].sum()))
        nxt = _market_keeper_set(b, apply_scale(raw_all, ceiling, cal["meta"]["scale_k"]),
                                 cal["meta"]["scale_k"])
        if (nxt == kept_mask).all():
            break
        kept_mask = nxt
    k = cal["meta"]["scale_k"]
    cal["meta"]["fixed_point_keepers"] = int(kept_mask.sum())

    priced = apply_scale(raw_all, ceiling, k)
    b = b.copy()
    for c, v in _market_surplus(b, priced, k).items():
        b[c] = v
    b["keep_2027_market"] = kept_mask

    return b, {"market": cal["meta"]}


def mark_optimal_keepers(b: pd.DataFrame,
                         col: str = "surplus_redraft") -> pd.DataFrame:
    """Flag each team's best legal keeper set: every player with positive
    surplus, capped at MAX_KEEPERS; if fewer than MIN_KEEPERS clear zero the
    league forces the least-bad ones anyway.
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
