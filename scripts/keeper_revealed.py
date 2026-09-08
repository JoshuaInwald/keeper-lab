"""Step 1b: keeper decisions as revealed preference.

Every keep/throw-back is a censored reading of what the owner thinks a player
is worth: kept at salary S means "worth at least S to me", thrown back means
"worth less than S". That is a second calibration of price, independent of
auction bids, and it is the exact margin this tool advises on
(docs/ROADMAP.md item 1 Step 1b, docs/FINDINGS.md #56).

Labels are RECONSTRUCTED, not read out of `data/keepers_YYYY.csv`. Those files
were the open question in HANDOFF.md, and the data settles it: `keepers_2025.csv`
shares ZERO players with the 2024 auction class, so it is not a keeper
submission for the contracts that were actually up. `keepers_2026.csv` (100
rows) is sound and agrees with the roster contract codes on 31 of 35 players
in the 2025 class, with no contradictions. So:

  thrown back  he appears in season S's auction. A player under a live
               contract only re-enters the auction pool by being released.
               Read straight off the draft files, which are complete.
  kept         season S == 2026: in `keepers_2026.csv`, or on the current
               roster with a contract code (`1`/`F`) whose acquisition year
               predates 2026.
               season S < 2026: he was NOT in the S auction but WAS in the
               S+1 auction. To be thrown back in S+1 he had to be rostered
               through S, so he was kept in S.
  unlabeled    neither. Overwhelmingly in-season drops: a released player
               keeps his draft contract and returns through free agency at
               $10/$20 (docs/FINDINGS.md #23.6), never through the auction,
               so he leaves no trace in these files. Dropped, not modelled.

The pre-2026 seasons carry a selection bias that 2026 does not: "kept" is only
detected when the player was LATER thrown back, so a player kept and held
forever reads as unlabeled. That inflates the marginal share of the kept class.
2026 is the headline; earlier seasons are a robustness check, reported apart.

    PYTHONPATH=.:scripts python3 scripts/keeper_revealed.py
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

from klab import config as C
from klab.auction import build_player_pool
from klab.io import (NameResolver, load_hitters_history, load_pitchers_history,
                     load_rosters)
from price_features import playing_time, scored_history

CONTRACT_YEARS = 3          # auction price holds for the buy year plus two
DECISION_SEASONS = (2023, 2024, 2025, 2026)


def _resolver() -> NameResolver:
    return NameResolver(build_player_pool(load_hitters_history(),
                                          load_pitchers_history()))


def _keeper_file(season: int, res: NameResolver) -> set[int]:
    d = pd.read_csv(C.DATA / f"keepers_{season}.csv")
    ids = {res.resolve(n, season)[0] for n in d["Player"]}
    return {int(i) for i in ids if i}


def decision_set(feats: pd.DataFrame) -> pd.DataFrame:
    """One row per keeper decision: who was under contract, and what happened."""
    res = _resolver()
    bought = {s: set(g.loc[g["fg_id"] > 0, "fg_id"])
              for s, g in feats.groupby("season")}
    # Salary and buy season per (fg_id, buy year) -- the price a keeper pays.
    price = {(int(r.fg_id), int(r.season)): int(r.salary)
             for r in feats.itertuples() if r.fg_id > 0}

    ros = load_rosters()
    ros["fg_id"] = ros["fg_id"].astype("Int64")
    code = ros["contract"].astype(str)
    held_over = set(ros.loc[code.isin(["1", "F"]), "fg_id"].dropna().astype(int))

    kept_2026 = _keeper_file(2026, res)      # hoisted: resolving 100 names per row is O(n^2)

    rows = []
    for S in DECISION_SEASONS:
        # Under a live contract going into S: bought in S-1 or S-2.
        for lag in (1, 2):
            buy_season = S - lag
            if buy_season not in bought:
                continue
            for fid in bought[buy_season]:
                if lag == 2 and fid in bought[S - 1]:
                    continue        # re-auctioned last year; that contract is dead
                thrown = fid in bought.get(S, set())
                if S == 2026:
                    kept = (fid in kept_2026) or (fid in held_over)
                else:
                    kept = (not thrown) and fid in bought.get(S + 1, set())
                if thrown and kept:
                    continue        # contradictory; never observed, guard anyway
                if not (thrown or kept):
                    continue        # unlabeled: an in-season drop, not a decision
                rows.append({
                    "decision_season": S, "fg_id": fid, "buy_season": buy_season,
                    "keeper_salary": price[(fid, buy_season)],
                    "years_control_left": CONTRACT_YEARS - lag,
                    "kept": int(kept),
                })
    return pd.DataFrame(rows)


def attach_features(dec: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    """Production and age as of the keeper deadline: season S-1's actual line.

    Taken from `auction.score_season()` over the whole league, NOT from
    `price_features.csv`. A kept player has no auction row in S and usually
    none in S-1 either, so reading his prior line off the purchase table
    returned zero for every keeper -- which made production look like it
    *lowered* the odds of being kept.
    """
    prior = scored_history()[["season", "fg_id", "roto_points"]].merge(
        playing_time(), on=["season", "fg_id"], how="outer")
    prior["decision_season"] = prior["season"] + 1
    prior = prior.drop(columns=["season"]).rename(columns={
        "roto_points": "rp_prior", "PA": "PA_prior",
        "IP": "IP_prior", "SV": "SV_prior"})

    static = (feats.sort_values("season")
              .groupby("fg_id")[["role", "pos_group", "birth_year"]].last()
              .reset_index())

    d = dec.merge(prior, on=["decision_season", "fg_id"], how="left")
    d = d.merge(static, on="fg_id", how="left")
    # NaN means "no MLB line in S-1", which is information, not a zero: keep
    # the flag and only then floor the points, or a rookie reads as a bust.
    d["played_prior"] = d["rp_prior"].notna().astype(int)
    for c in ("rp_prior", "PA_prior", "IP_prior", "SV_prior"):
        d[c] = d[c].fillna(0.0)
    d["age"] = d["decision_season"] - d["birth_year"]
    d["is_pit"] = (d["role"] == "PIT").astype(int)
    return d


def fit(d: pd.DataFrame, label: str):
    X = pd.DataFrame({
        "const": 1.0,
        "rp_prior": d["rp_prior"],
        "played_prior": d["played_prior"],
        "keeper_salary": d["keeper_salary"],
        "years_control_left": d["years_control_left"],
        "is_pit": d["is_pit"],
        # Age belongs here and not in the board's keeper logic. This model is
        # fit on last season's ACTUALS, which carry no age information, so the
        # owners' age effect is real signal. `production_value` gets its age
        # adjustment from ZiPS already, which is why CONSTRAINTS.md declines a
        # second aging curve there (docs/FINDINGS.md #59).
        "age": d["age"].fillna(d["age"].mean()),
    })
    m = sm.Logit(d["kept"], X).fit(disp=0)
    print(f"\n--- P(kept) logit, {label} (n={len(d)}, "
          f"{int(d['kept'].sum())} kept / {int((1 - d['kept']).sum())} thrown back) ---")
    print(f"pseudo R^2 {m.prsquared:.3f}")
    print(pd.DataFrame({"coef": m.params.round(4), "se": m.bse.round(4),
                        "z": m.tvalues.round(2), "p": m.pvalues.round(4)}).to_string())
    return m


def implied_prices(m, d: pd.DataFrame, nbins: int = 10) -> pd.DataFrame:
    """Salary at which P(kept) = 0.5, by prior-production decile.

    The logit is linear in salary, so the indifference price solves
    b0 + b_rp*rp + b_yrs*yrs + b_pit*pit + b_sal*S = 0 for S. Evaluated at each
    decile's own mean covariates, not at the sample mean, so the number is the
    price the owners of THOSE players revealed.
    """
    p = m.params
    q = pd.qcut(d["rp_prior"], nbins, labels=False, duplicates="drop")
    out = []
    for b, g in d.groupby(q):
        lin = (p["const"] + p["rp_prior"] * g["rp_prior"].mean()
               + p["played_prior"] * g["played_prior"].mean()
               + p["years_control_left"] * g["years_control_left"].mean()
               + p["is_pit"] * g["is_pit"].mean()
               + p["age"] * g["age"].fillna(g["age"].mean()).mean())
        out.append({
            "decile": int(b) + 1, "n": len(g),
            "mean_rp_prior": round(g["rp_prior"].mean(), 2),
            "kept_rate": round(g["kept"].mean(), 3),
            "mean_salary": round(g["keeper_salary"].mean(), 2),
            "implied_price_p50": round(-lin / p["keeper_salary"], 2),
        })
    return pd.DataFrame(out).pipe(_add_model_columns)


def _add_model_columns(t: pd.DataFrame) -> pd.DataFrame:
    """What the current engine says a player at that production level is worth.

    Read from `out/model_params.json`, never recomputed here: the two dollar
    scales are `board.value_players()`'s, and hand-arithmetic on them has been
    wrong before (CONSTRAINTS.md).
    """
    mp = json.loads((C.OUT / "model_params.json").read_text())
    repl, usd = mp["replacement_rp"], mp["usd_per_rp_redraft"]
    ex = mp["exchange_rate"]
    t["production_value"] = ((t["mean_rp_prior"] - repl) * usd + 1.0).clip(lower=0).round(2)
    t["keep_value"] = ((t["mean_rp_prior"] - ex["intercept"])
                       / ex["slope"]).clip(lower=0).round(2)
    return t


def main() -> int:
    feats = pd.read_csv(C.OUT / "price_features.csv")
    dec = decision_set(feats)
    d = attach_features(dec, feats)
    path = C.OUT / "keeper_decisions.csv"
    d.to_csv(path, index=False)

    print("labeled keeper decisions by season")
    print(d.groupby("decision_season").agg(
        n=("kept", "size"), kept=("kept", "sum"),
        keep_rate=("kept", lambda s: round(s.mean(), 3)),
        mean_salary=("keeper_salary", "mean")).round(2).to_string())

    clean = d[d["decision_season"] == 2026]
    m = fit(clean, "2026 only, labels from keeper file + roster codes")
    print("\nimplied indifference price by prior-production decile (2026)")
    print(implied_prices(m, clean).to_string(index=False))

    older = d[d["decision_season"] < 2026]
    if len(older) > 30:
        m2 = fit(older, "2023-2025, reconstructed labels (selection-biased)")
        print("\nimplied indifference price by prior-production decile (2023-2025)")
        print(implied_prices(m2, older).to_string(index=False))

    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
