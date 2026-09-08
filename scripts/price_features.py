"""Step 1: the ex-ante feature table behind every auction purchase.

`out/auction_sample.csv` pairs a price with the roto points the player went on
to deliver, which is the wrong side of the auction: bidders cannot see it. This
script rebuilds, for all 677 purchases 2022-2026, only what was knowable on
auction day, so `scripts/price_model.py` can fit price on information a bidder
actually had (docs/ROADMAP.md item 1 Step 1, docs/FINDINGS.md #56).

Features, all as of the auction for season S:

  production   `auction.score_season()` roto points for S-1 and S-2, each on
               its own season's denominators, plus the playing time (PA / IP)
               and the saves total that produced them (saves are the one
               category the market misprices, docs/FINDINGS.md #1)
  rookie       `no_prior_line`: no MLB line in either S-1 or S-2. 25% of
               purchases; the model has to price them from something else
  tenure       `auction_tenure`: prior purchases in THIS league's auctions,
               counted strictly before S. Not `auction_estimator.player_tenure()`,
               which counts a player's whole career including sales after S
               and would leak the future into the fit
  contract     `last_salary` / `years_since_last`: the most recent price this
               league paid him. Prior salary carries coefficient 0.48 and
               doubles R^2 among re-auctioned players (docs/ROADMAP.md item 1)
  role/pos     role bought as (HIT/PIT) and `auction_estimator.position_group()`
  age          season minus birth year from `data/chadwick_register.csv`

Coverage limit, deliberate: the FanGraphs history exports start in 2022, so
2022's 137 purchases have no prior-season line and are not distinguishable from
genuine rookies. `has_prior_window` is 0 for them; the price model fits on
2023-2026 only and says so.

    PYTHONPATH=.:scripts python3 scripts/price_features.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from klab import config as C
from klab.auction import score_season
from klab.auction_estimator import position_group
from klab.denoms import pooled_relative_dispersion, season_levels, team_baselines
from klab.io import load_hitters_history, load_pitchers_history

SEASONS = (2022, 2023, 2024, 2025, 2026)
HISTORY_START = min(SEASONS)


def scored_history() -> pd.DataFrame:
    """Roto points per (season, fg_id) on that season's own scale."""
    sigma_rel = pooled_relative_dispersion()
    levels, hit, pit = season_levels(), load_hitters_history(), load_pitchers_history()
    bl = team_baselines(list(SEASONS))
    return pd.concat([score_season(s, sigma_rel, levels, hit, pit, bl)
                      for s in SEASONS], ignore_index=True)


def playing_time() -> pd.DataFrame:
    """PA, IP and SV per (season, fg_id): the volume behind the roto points."""
    h = load_hitters_history()[["season", "fg_id", "PA"]].copy()
    h["IP"] = 0.0
    h["SV"] = 0.0
    p = load_pitchers_history()[["season", "fg_id", "IP", "SV"]].copy()
    p["PA"] = 0.0
    both = pd.concat([h, p[["season", "fg_id", "PA", "IP", "SV"]]], ignore_index=True)
    # A two-way player has a row in each file; sum, matching score_season().
    return both.groupby(["season", "fg_id"], as_index=False).sum()


def ages() -> pd.DataFrame:
    """Birth year by fg_id. Missing for 8 of 450 players, every one of them a
    2026 prospect or NPB import whose FanGraphs id postdates the register."""
    reg = pd.read_csv(C.DATA / "chadwick_register.csv")
    reg = reg[reg["birth_year"].notna()]
    return (reg[["key_fangraphs", "birth_year"]]
            .rename(columns={"key_fangraphs": "fg_id"})
            .astype({"fg_id": int, "birth_year": int}))


def build() -> pd.DataFrame:
    a = pd.read_csv(C.OUT / "auction_sample.csv")
    a = a[["season", "team", "player", "salary", "pos", "fg_id", "match",
           "role", "roto_points", "played"]].copy()
    a["fg_id"] = a["fg_id"].fillna(-1).astype(int)
    a = a.rename(columns={"roto_points": "rp_realized"})

    scored = scored_history()[["season", "fg_id", "roto_points"]]
    pt = playing_time()
    prior = scored.merge(pt, on=["season", "fg_id"], how="outer")

    out = a.copy()
    for lag in (1, 2):
        lagged = prior.copy()
        lagged["season"] = lagged["season"] + lag        # S-lag line -> season S row
        lagged = lagged.rename(columns={
            "roto_points": f"rp_prior{lag}", "PA": f"PA_prior{lag}",
            "IP": f"IP_prior{lag}", "SV": f"SV_prior{lag}"})
        out = out.merge(lagged, on=["season", "fg_id"], how="left")
        out[f"played_prior{lag}"] = out[f"rp_prior{lag}"].notna().astype(int)

    # 2022 has no window to look back into: its zeros are censoring, not rookies.
    out["has_prior_window"] = (out["season"] > HISTORY_START).astype(int)
    out["no_prior_line"] = ((out["played_prior1"] == 0)
                            & (out["played_prior2"] == 0)
                            & (out["has_prior_window"] == 1)).astype(int)

    # Ex-ante only: purchases in a STRICTLY earlier season. Computed per row,
    # not by a (season, fg_id) merge: `io.NameResolver` maps both Max Muncys to
    # fg_id 13301, and they were bought by two teams in the same 2026 auction,
    # so that merge cartesian-joined the pair into four rows.
    hist = a[a["fg_id"] > 0][["fg_id", "season", "salary"]]
    by_id: dict[int, list[tuple[int, int]]] = {}
    for fid, sea, sal in hist.itertuples(index=False, name=None):
        by_id.setdefault(int(fid), []).append((int(sea), int(sal)))
    tenure, last_sal, last_sea = [], [], []
    for fid, sea in zip(out["fg_id"], out["season"]):
        earlier = sorted(x for x in by_id.get(int(fid), []) if x[0] < int(sea))
        tenure.append(len(earlier))
        last_sal.append(earlier[-1][1] if earlier else np.nan)
        last_sea.append(earlier[-1][0] if earlier else np.nan)
    out["auction_tenure"] = tenure
    out["last_salary"] = last_sal
    out["last_salary_season"] = last_sea
    out["years_since_last"] = out["season"] - out["last_salary_season"]
    out["ever_bought_before"] = out["last_salary"].notna().astype(int)

    out["pos_group"] = out["pos"].map(position_group)
    out = out.merge(ages(), on="fg_id", how="left")
    out["age"] = out["season"] - out["birth_year"]

    # Convenience aggregates the model uses directly.
    for lag in (1, 2):
        out[f"rp_prior{lag}"] = out[f"rp_prior{lag}"].fillna(0.0)
        for c in ("PA", "IP", "SV"):
            out[f"{c}_prior{lag}"] = out[f"{c}_prior{lag}"].fillna(0.0)
    out["rp_prior_best"] = out[["rp_prior1", "rp_prior2"]].max(axis=1)
    out["rp_prior_mean"] = out[["rp_prior1", "rp_prior2"]].mean(axis=1)
    out["log_salary"] = np.log(out["salary"])

    cols = ["season", "team", "player", "fg_id", "match", "salary", "log_salary",
            "pos", "pos_group", "role",
            "rp_prior1", "rp_prior2", "rp_prior_best", "rp_prior_mean",
            "PA_prior1", "IP_prior1", "SV_prior1",
            "PA_prior2", "IP_prior2", "SV_prior2",
            "played_prior1", "played_prior2", "has_prior_window", "no_prior_line",
            "auction_tenure", "ever_bought_before", "last_salary",
            "last_salary_season", "years_since_last",
            "birth_year", "age", "rp_realized", "played"]
    return out[cols].sort_values(["season", "salary"], ascending=[True, False])


def main() -> int:
    d = build()
    path = C.OUT / "price_features.csv"
    d.to_csv(path, index=False)

    print(f"{len(d)} purchases, {d['fg_id'].nunique()} players\n")
    same_season = (d[d["fg_id"] > 0].groupby(["season", "fg_id"])["player"]
                   .nunique().pipe(lambda s: s[s > 1]))
    if len(same_season):
        print(f"WARNING: {len(same_season)} fg_id(s) carry two different players "
              f"in one season (NameResolver collision):")
        for (sea, fid) in same_season.index:
            names = sorted(d[(d["season"] == sea) & (d["fg_id"] == fid)]["player"].unique())
            print(f"  {sea} fg_id {fid}: {', '.join(names)}")
        print()
    print("coverage by season")
    cov = d.groupby("season").agg(
        n=("salary", "size"),
        mean_price=("salary", "mean"),
        pct_prior_line=("played_prior1", lambda s: round(100 * s.mean(), 1)),
        pct_rookie=("no_prior_line", lambda s: round(100 * s.mean(), 1)),
        pct_rebought=("ever_bought_before", lambda s: round(100 * s.mean(), 1)),
        pct_age=("age", lambda s: round(100 * s.notna().mean(), 1)))
    print(cov.to_string())

    fit = d[d["has_prior_window"] == 1]
    print(f"\nmodelling set (2023-2026, prior window exists): n={len(fit)}")
    print(f"  age known:        {fit['age'].notna().sum()} "
          f"({100 * fit['age'].notna().mean():.1f}%)")
    print(f"  no prior MLB line:{fit['no_prior_line'].sum():>4} "
          f"({100 * fit['no_prior_line'].mean():.1f}%), "
          f"mean price ${fit.loc[fit['no_prior_line'] == 1, 'salary'].mean():.2f} "
          f"vs ${fit.loc[fit['no_prior_line'] == 0, 'salary'].mean():.2f}")
    print(f"  bought before:    {fit['ever_bought_before'].sum():>4} "
          f"({100 * fit['ever_bought_before'].mean():.1f}%)")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
