"""Does the top-230 calibration-pool pathology reproduce under a second
projection system? (docs/FINDINGS.md #65, item 1 of the assessment handoff.)

`board.value_players()` calibrates the $2,600 budget identity on the top 230
players by projected roto points regardless of role. #65 measured that pool on
the 2027 ZiPS Depth Charts blend and found 183 hitters / 47 pitchers, against
125-139 / 91-105 in every completed season scored on its own scale. It could
not tell whether that is a property of PROJECTIONS IN GENERAL (regression to
the mean compresses the less-projectable role out of a pool selected on
projected value) or an artefact of ZiPS DEPTH CHARTS specifically (innings
smeared across the full depth chart, so no projected pitcher looks like an ace).

The two answers send the repair to different places:
  general    -> the pool rule must handle it, in board.value_players()
  ZiPS-only  -> the fix belongs upstream in the projection step, klab/project.py

Marcel decides it. It is an independent ex-ante projection for 2024, 2025 and
2026 (#67) with no connection to ZiPS, so scoring it on each season's own scale
and taking the top 230 asks the same question of a different system.

Four arms, deliberately over-specified so the harness can be checked against
numbers that are already published:

  actual   each completed season's realised stat lines, scored on that season's
           scale. This MUST reproduce #65's table (2024 131/99, 2025 139/91,
           2026 130/100) or the harness is wrong and nothing below counts.
  marcel   Marcel's projection FOR that season, scored with the SAME scorer as
           the `actual` arm for that season. Same scale, same pool size, same
           replacement rule: only the stat lines differ.
  zips     the production 2027 board pool. MUST reproduce 183/47 and a 73.70%
           hitter dollar share.
  zips_raw the same 2027 pool with every blend weight set to zero, so the
           2026 actuals are removed and the pool is pure ZiPS Depth Charts.
           Separates "ZiPS is compressed" from "the blend compressed it".

Three cautions carried from #67, all of which bear on reading the output.
1. Marcel is the naive baseline, not a ZiPS substitute. What transfers here is
   the SHAPE of the answer (does a projection lose pitchers from the pool, and
   by how much), never a fitted constant.
2. Marcel projects saves; ZiPS 2027 does not, so the production path takes SV
   from `project_saves()` on 2026 actuals. The `zips_raw` arm keeps that model
   because zeroing SV would delete a whole category from one arm only.
3. 2026 actuals are ~75% of a season at the 2026-08-15 pull. The `actual` arm
   for 2026 is therefore a partial season; 2024 and 2025 are complete and are
   the ones to read. Partial-season roto points are scored against 2026's own
   (also partial) league levels, which is why #65's 2026 row still lands at
   130/100.

    PYTHONPATH=.:scripts python3 scripts/marcel_pool_test.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import klab.config as C
from klab.auction import score_season
from klab.board import project_all_players
from klab.denoms import (RotoScorer, denominators_for_level,
                         pooled_relative_dispersion, season_levels,
                         team_baselines, teams_per_category)
from klab.io import load_hitters_history, load_pitchers_history
from klab.marcel import SEASONS, marcel_fg_ids
from sensitivity import knob

pd.set_option("display.width", 220)

N_POOL = C.N_TEAMS * C.N_ACTIVE          # 230
N_HIT_FIELDABLE = C.N_TEAMS * C.N_HIT_SLOTS   # 140
N_PIT_FIELDABLE = C.N_TEAMS * C.N_PIT_SLOTS   # 90

KEEP = ["fg_id", "name", "role", "roto_points"]
RP_COLS = [f"rp_{c}" for c in C.CATS]


# --- one shared scorer per season -------------------------------------------

def season_scorer(season: int) -> RotoScorer:
    """The scorer `score_season` builds, exposed so the Marcel arm can borrow it.

    Both arms for a season MUST share this object. Scoring a projection on a
    scale derived from the projection itself would compare two different roto
    scales and the HIT/PIT split would move for reasons that have nothing to do
    with the projection's shape.
    """
    L = (season_levels().query("season == @season")
         .set_index("category")["level"].to_dict())
    D = denominators_for_level(pooled_relative_dispersion(), L,
                               n_by_cat=teams_per_category())
    b = team_baselines([season]).set_index("season").loc[season].to_dict()
    return RotoScorer(D, b)


# --- the four arms, each returning one row per player ------------------------

def arm_actual(season: int) -> pd.DataFrame:
    """Realised stat lines for `season`, scored on `season`'s scale."""
    out = score_season(season, pooled_relative_dispersion(), season_levels(),
                       load_hitters_history(), load_pitchers_history(),
                       team_baselines([season]))
    return out[KEEP + [c for c in RP_COLS if c in out]]


def arm_marcel(season: int) -> pd.DataFrame:
    """Marcel's projection FOR `season`, scored with `season`'s own scorer."""
    sc = season_scorer(season)
    h = marcel_fg_ids(season, "HIT")
    p = marcel_fg_ids(season, "PIT")
    H = h[["fg_id", "name"]].join(sc.hitters(h)).assign(is_hit=1)
    P = p[["fg_id", "name"]].join(sc.pitchers(p)).assign(is_hit=0)
    out = pd.concat([H, P], ignore_index=True).dropna(subset=["fg_id"])
    # A two-way player has a row in each file. Summed, matching score_season(),
    # so the `actual` and `marcel` arms treat him identically.
    agg = {c: "sum" for c in RP_COLS if c in out}
    out = out.groupby("fg_id", as_index=False).agg(
        {**agg, "roto_points": "sum", "name": "first", "is_hit": "max"})
    out["role"] = np.where(out["is_hit"] > 0, "HIT", "PIT")
    return out[KEEP + [c for c in RP_COLS if c in out]]


def arm_zips() -> pd.DataFrame:
    """The pool `board.value_players()` actually calibrates on."""
    base, _, _, _ = project_all_players(full_time=False)
    b = base.copy()
    # project_all_players keeps Ohtani as two rows (TWO_WAY_SPLIT_NAMES) and
    # labels incidental two-way rows "TWO"; fold both to a role so every arm
    # counts the same way.
    b["role"] = np.where(b["role"] == "PIT", "PIT", "HIT")
    return b[["fg_id", "name", "role", "roto_points"]]


def arm_zips_raw() -> pd.DataFrame:
    """The same pool with the 2026 actuals blended out: pure ZiPS Depth Charts.

    Zeroing all four blend caps drives every weight on source A to 0, so rates
    and playing time come entirely from ZiPS. The has_a/has_b fallbacks and the
    save model are untouched: a player with no ZiPS line still leans on 2026,
    which is correct here because dropping him would shrink the universe rather
    than change the projection.
    """
    with knob(BLEND_W_2026=0.0, PT_BLEND_CAP_HITTER=0.0,
              PT_BLEND_CAP_PITCHER=0.0, PT_BLEND_CAP_PITCHER_EXCEEDED=0.0):
        return arm_zips()


# --- measurement ------------------------------------------------------------

def pool_stats(df: pd.DataFrame, label: str) -> dict:
    """Everything #65 reports about a pool, from one frame of roto points.

    Two shares, because they answer different questions and differ by 5 points.

    `hit_surplus_share` is the share of roto points ABOVE REPLACEMENT held by
    hitters in the pool. It is the quantity that drives the split.

    `hit_dollar_share` is #65's published 73.70%: the same allocation after
    `board.value_players()`'s dollar conversion, which hands every one of the
    230 a $1 minimum bid and calibrates the rest against $2,600 - $230. That
    floor pulls the dollar share toward the HEAD-COUNT share, so a pool holding
    183 of 230 slots reads 5 points higher in dollars than in surplus. Both are
    reported or the two published figures look inconsistent.
    """
    d = df.dropna(subset=["roto_points"])
    top = d.nlargest(N_POOL, "roto_points")
    repl = float(top["roto_points"].min())
    surplus = (top["roto_points"] - repl).clip(lower=0.0)
    is_hit = top["role"].eq("HIT")

    budget = C.N_TEAMS * C.BUDGET
    usd_per_rp = (budget - N_POOL * 1.0) / float(surplus.sum())
    hit_usd = int(is_hit.sum()) * 1.0 + float(surplus[is_hit].sum()) * usd_per_rp

    hit_all = d[d["role"].eq("HIT")]["roto_points"].sort_values(ascending=False)
    pit_all = d[d["role"].eq("PIT")]["roto_points"].sort_values(ascending=False)

    def nth(s: pd.Series, n: int) -> float:
        return float(s.iloc[n - 1]) if len(s) >= n else float("nan")

    return {
        "arm": label,
        "n_hit": int(is_hit.sum()),
        "n_pit": int((~is_hit).sum()),
        "hit_dollar_share": hit_usd / budget,
        "hit_surplus_share": float(surplus[is_hit].sum() / surplus.sum()),
        "repl_rp": repl,
        # #65's clearest single symptom: where the 90th-best pitcher sits.
        # Completed seasons put him at 4.95-7.22; the 2027 ZiPS blend at 3.527.
        "rp_pit_90th": nth(pit_all, N_PIT_FIELDABLE),
        "rp_hit_140th": nth(hit_all, N_HIT_FIELDABLE),
        "universe_hit": int(len(hit_all)),
        "universe_pit": int(len(pit_all)),
    }


def category_gap(proj: pd.DataFrame, actual: pd.DataFrame, role: str,
                 n_top: int) -> pd.DataFrame:
    """#65's decomposition, run on Marcel instead of ZiPS.

    Selection is done ONCE, on the projection, and the same players are then
    looked up in the actuals. Re-selecting on the actuals would compare two
    different sets of players and measure survivorship rather than calibration.
    #65 ran this for ZiPS 2027 against 2026 actuals and found the entire
    1.79-point pitcher gap sitting in ERA, WHIP and SV, with W and K calibrated
    to within 0.02, while the hitter side needed nothing.
    """
    cats = C.HIT_CATS if role == "HIT" else C.PIT_CATS
    cols = [f"rp_{c}" for c in cats]
    top = proj[proj["role"].eq(role)].nlargest(n_top, "roto_points")
    m = top.merge(actual[actual["role"].eq(role)][["fg_id"] + cols + ["roto_points"]],
                  on="fg_id", how="inner", suffixes=("_proj", "_act"))
    row_p = {c: m[f"{c}_proj"].mean() for c in cols}
    row_a = {c: m[f"{c}_act"].mean() for c in cols}
    row_p["total"] = m["roto_points_proj"].mean()
    row_a["total"] = m["roto_points_act"].mean()
    return pd.DataFrame([{"line": "projected", "n": len(m), **row_p},
                         {"line": "actual", "n": len(m), **row_a}])


def pool_rules(df: pd.DataFrame, label: str, season: int) -> dict:
    """The three candidate pool rules #65 measured, run on any arm.

    Run on the `actual` arm this answers a question #65 could not ask, because
    it only ever had the 2027 projection to measure: what does each rule produce
    under PERFECT FORESIGHT? That is the benchmark a rule has to hit. A rule
    whose output on realised data sits at X cannot be faulted for producing X on
    a projection, and a rule that cannot reach the league's spend share even
    with the season already played is being asked for the wrong thing.

    blind        top 230 by roto points regardless of role; replacement is the
                 230th of that pool. This is what board.value_players() does.
    slot_pooled  top 140 hitters + top 90 pitchers, but replacement is still the
                 230th of the ROLE-BLIND pool. #65's second candidate.
    slot_role    the same slot-constrained pool with role-specific replacement
                 (140th hitter, 90th pitcher). #65's first candidate, the one it
                 rejected at 54.21%.
    """
    d = df.dropna(subset=["roto_points"])
    blind = d.nlargest(N_POOL, "roto_points")
    repl_blind = float(blind["roto_points"].min())
    H = d[d["role"].eq("HIT")].nlargest(N_HIT_FIELDABLE, "roto_points")
    P = d[d["role"].eq("PIT")].nlargest(N_PIT_FIELDABLE, "roto_points")
    slot = pd.concat([H, P])
    budget = C.N_TEAMS * C.BUDGET

    def hit_share(top: pd.DataFrame, repl) -> float:
        surplus = (top["roto_points"] - repl).clip(lower=0.0)
        is_hit = top["role"].eq("HIT")
        usd = (budget - len(top) * 1.0) / float(surplus.sum())
        return (int(is_hit.sum()) * 1.0
                + float(surplus[is_hit].sum()) * usd) / budget

    role_repl = pd.Series(
        np.where(slot["role"].eq("HIT"), H["roto_points"].min(),
                 P["roto_points"].min()), index=slot.index)
    return {"season": season, "arm": label,
            "blind": hit_share(blind, repl_blind),
            "slot_pooled": hit_share(slot, repl_blind),
            "slot_role": hit_share(slot, role_repl)}


def rostered_shares() -> pd.DataFrame:
    """The hitter share on the population #64 actually measured.

    This is the panel that shows #65 compared two different things. #64's
    63-64% is the hitter share of AUCTION SPEND and of DELIVERED ROTO POINTS
    over the players this league rosters. #65's 73.70% is the hitter share of
    MODEL DOLLARS over the top 230 by projected roto points, which is a
    hitter-skewed set (183 of 230) precisely because of the compression this
    script measures. Putting both quantities on both populations separates
    "the projection mis-splits the roles" from "the dollar conversion does".
    """
    from klab.board import value_players
    from klab.io import load_rosters

    players, _, _ = value_players()
    players["r"] = np.where(players["role"] == "PIT", "PIT", "HIT")
    # 277 rows against 276 rostered players: Ohtani is carried as two assets
    # (TWO_WAY_SPLIT_NAMES), which is correct here, both are really rostered.
    rostered = players.merge(load_rosters()[["fg_id"]].drop_duplicates(), on="fg_id")
    top = players.nlargest(N_POOL, "roto_points")

    rows = []
    for label, d in (("rostered (276)", rostered), ("calibration top-230", top)):
        for col in ("roto_points", "redraft_value"):
            s = d.groupby("r")[col].sum()
            rows.append({"population": label, "n": len(d), "quantity": col,
                         "hit_share": float(s.get("HIT", 0.0) / s.sum())})
    return pd.DataFrame(rows)


def compression(proj: pd.DataFrame, actual: pd.DataFrame, season: int) -> pd.DataFrame:
    """How much narrower is the projected spread than the realised one, by role?

    The pool rule selects on projected roto points, so what decides the HIT/PIT
    split is not the mean of either role but the SPREAD: a role whose top is
    flattened toward the middle loses its best players' separation and falls out
    of a pooled top-230. #67 predicts exactly this asymmetry from Marcel's own
    reliability weights (pitchers 0.47, hitters 0.71): the less projectable role
    is regressed harder, so it is compressed harder.

    No top-N filter is applied. Selecting on the projection would truncate the
    projected distribution from below while leaving the actuals untruncated,
    which shrinks the projected sd for reasons that have nothing to do with
    compression. The set is instead every player carrying both a Marcel line and
    a realised line, which is an ex-ante filter on both sides.
    """
    rows = []
    for role in ("HIT", "PIT"):
        m = (proj[proj["role"].eq(role)][["fg_id", "roto_points"]]
             .merge(actual[actual["role"].eq(role)][["fg_id", "roto_points"]],
                    on="fg_id", how="inner", suffixes=("_proj", "_act")))
        sd_p = float(m["roto_points_proj"].std())
        sd_a = float(m["roto_points_act"].std())
        rows.append({"season": season, "role": role, "n": len(m),
                     "sd_proj": sd_p, "sd_actual": sd_a, "sd_ratio": sd_p / sd_a,
                     "mean_proj": float(m["roto_points_proj"].mean()),
                     "mean_actual": float(m["roto_points_act"].mean())})
    return pd.DataFrame(rows)


def compression_by_category(proj: pd.DataFrame, actual: pd.DataFrame,
                            season: int) -> pd.DataFrame:
    """The same ratio per category, which is what localises the mechanism.

    Roto points are a sum over categories, so a role is compressed exactly as
    much as its categories are. If the low ratios land on the rate categories,
    the cause is regression to the mean (every projection does it, ZiPS and
    Marcel alike) rather than anything about how one system distributes playing
    time. Pitchers carry three of the four hardest-compressed categories and
    hitters one, which is a scoring-format fact, not a projection defect.
    """
    rows = []
    for role, cats in (("HIT", C.HIT_CATS), ("PIT", C.PIT_CATS)):
        m = proj[proj["role"].eq(role)].merge(
            actual[actual["role"].eq(role)], on="fg_id", suffixes=("_p", "_a"))
        r = {"season": season, "role": role, "n": len(m)}
        for c in cats:
            r[f"rp_{c}"] = float(m[f"rp_{c}_p"].std() / m[f"rp_{c}_a"].std())
        rows.append(r)
    return pd.DataFrame(rows)


def innings_shape(label: str, ip: pd.Series) -> dict:
    """Is the pitcher pool smeared? #65's mechanism, measured directly.

    ZiPS Depth Charts spreads innings over the whole depth chart, so it carries
    far more 100-IP arms than a real season and far fewer 150-IP arms. A system
    that does not smear should land near the realised counts on both.
    """
    ip = pd.Series(ip).dropna()
    return {"arm": label, "n_pitchers": int(len(ip)),
            "ip_ge_100": int((ip >= 100).sum()), "ip_ge_150": int((ip >= 150).sum()),
            "ip_max": float(ip.max()) if len(ip) else float("nan")}


def main() -> None:
    rows, ip_rows, gaps, comps, cats, rules = [], [], [], [], [], []

    for s in SEASONS:
        act, mar = arm_actual(s), arm_marcel(s)
        rows.append({"season": s, **pool_stats(act, "actual")})
        rows.append({"season": s, **pool_stats(mar, "marcel")})
        act_ip = load_pitchers_history().query("season == @s")["IP"]
        ip_rows.append({"season": s, **innings_shape("actual", act_ip)})
        ip_rows.append({"season": s,
                        **innings_shape("marcel", marcel_fg_ids(s, "PIT")["IP"])})
        for role, n in (("PIT", N_PIT_FIELDABLE), ("HIT", N_HIT_FIELDABLE)):
            g = category_gap(mar, act, role, n)
            gaps.append(g.assign(season=s, role=role))
        comps.append(compression(mar, act, s))
        rules.append(pool_rules(act, 'actual', s))
        rules.append(pool_rules(mar, 'marcel', s))
        cats.append(compression_by_category(mar, act, s))

    z = arm_zips()
    rows.append({"season": 2027, **pool_stats(z, "zips")})
    zr = arm_zips_raw()
    rows.append({"season": 2027, **pool_stats(zr, "zips_raw")})
    rules.append(pool_rules(z, 'zips', 2027))
    rules.append(pool_rules(zr, 'zips_raw', 2027))

    base, _, _, _ = project_all_players(full_time=False)
    ip_rows.append({"season": 2027,
                    **innings_shape("zips", base.query("role == 'PIT'")["IP"])})
    with knob(BLEND_W_2026=0.0, PT_BLEND_CAP_HITTER=0.0,
              PT_BLEND_CAP_PITCHER=0.0, PT_BLEND_CAP_PITCHER_EXCEEDED=0.0):
        raw, _, _, _ = project_all_players(full_time=False)
        ip_rows.append({"season": 2027,
                        **innings_shape("zips_raw", raw.query("role == 'PIT'")["IP"])})

    pools = pd.DataFrame(rows)
    print("\n=== TOP-230 CALIBRATION POOL, BY ARM ===")
    print("league fields 140 HIT / 90 PIT by rule; observed active rosters 134/96")
    print(pools.to_string(index=False,
                          formatters={"hit_dollar_share": "{:.4f}".format,
                                      "hit_surplus_share": "{:.4f}".format,
                                      "repl_rp": "{:.3f}".format,
                                      "rp_pit_90th": "{:.3f}".format,
                                      "rp_hit_140th": "{:.3f}".format}))

    print("\n=== PITCHER INNINGS SHAPE (#65's proposed mechanism) ===")
    print(pd.DataFrame(ip_rows).to_string(index=False))

    print("\n=== WHICH STEP MIS-SPLITS THE ROLES: THE PROJECTION OR THE DOLLARS? ===")
    print("#64's league references: auction spend 63.86%, roto points delivered 64.11%")
    print(rostered_shares().to_string(index=False,
                                      float_format=lambda v: f"{v:7.4f}"))

    print("\n=== HITTER DOLLAR SHARE UNDER THE THREE CANDIDATE POOL RULES ===")
    print("the `actual` rows are the perfect-foresight benchmark each rule must be judged against")
    print("league auction spend on hitters is 63.86% (#64), over a DIFFERENT population: see the writeup")
    print(pd.DataFrame(rules).to_string(index=False,
                                        float_format=lambda v: f"{v:7.4f}"))

    print("\n=== DISPERSION: is the projected spread narrower, and for which role? ===")
    print(pd.concat(comps, ignore_index=True).to_string(
        index=False, float_format=lambda v: f"{v:6.3f}"))

    print("\n  same ratio per category (this is where the mechanism localises):")
    print(pd.concat(cats, ignore_index=True).to_string(
        index=False, na_rep="", float_format=lambda v: f"{v:6.3f}"))

    print("\n=== CATEGORY DECOMPOSITION: Marcel vs the same players' actuals ===")
    print("selection is on the projection only, so both lines score one player set")
    gap = pd.concat(gaps, ignore_index=True)
    cols = ["season", "role", "line", "n"] + RP_COLS + ["total"]
    print(gap[cols].to_string(index=False, na_rep="",
                              float_format=lambda v: f"{v:6.3f}"))

    print("\n=== CONTROLS: these must match published numbers ===")
    published = {2024: (131, 99), 2025: (139, 91), 2026: (130, 100)}
    ok = True
    for s, (eh, ep) in published.items():
        r = pools.query("season == @s and arm == 'actual'").iloc[0]
        hit = (int(r["n_hit"]), int(r["n_pit"])) == (eh, ep)
        ok &= hit
        print(f"  #65 actual {s}: expected {eh}/{ep}, got "
              f"{int(r['n_hit'])}/{int(r['n_pit'])}  {'ok' if hit else 'MISMATCH'}")
    zr_ = pools.query("arm == 'zips'").iloc[0]
    hit = (int(zr_["n_hit"]), int(zr_["n_pit"])) == (183, 47)
    ok &= hit
    print(f"  #65 zips 2027: expected 183/47, got "
          f"{int(zr_['n_hit'])}/{int(zr_['n_pit'])}  {'ok' if hit else 'MISMATCH'}")
    share_ok = abs(zr_["hit_dollar_share"] - 0.7370) < 0.0005
    ok &= share_ok
    print(f"  #65 hitter dollar share: expected 0.7370, got "
          f"{zr_['hit_dollar_share']:.4f}  {'ok' if share_ok else 'MISMATCH'}")
    # #65's two rejected repairs are controls too: reproducing the numbers it
    # rejected is what licenses re-reading them against a benchmark it lacked.
    zrule = next(r for r in rules if r["arm"] == "zips")
    for key, want in (("slot_role", 0.5421), ("slot_pooled", 0.7155)):
        hit = abs(zrule[key] - want) < 0.0005
        ok &= hit
        print(f"  #65 {key}: expected {want:.4f}, got {zrule[key]:.4f}  "
              f"{'ok' if hit else 'MISMATCH'}")
    print(f"\n{'ALL CONTROLS HOLD' if ok else 'CONTROLS FAILED: do not read the above'}")


if __name__ == "__main__":
    main()
