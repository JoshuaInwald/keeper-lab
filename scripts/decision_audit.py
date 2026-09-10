"""Were the owners right? A decision-quality audit of past keeper calls.

Every other validation in this project scores the MODEL. This one scores the
OWNERS, and by extension the advice the model exists to give: for each keeper
decision, what did the player go on to do, and was the salary the owner paid or
declined a good price for it.

Scaffolded 2026-09-08 for the assessment phase (`docs/ASSESSMENT-BRIEF.md`). The
joins and the design decisions are made here so the assessment can argue about
the answer instead of rebuilding the question. Nothing is concluded; the printed
tables are the input to a judgment.

THE DESIGN DECISION THAT MATTERS

Realised production is a noisy scorer of a decision made ex ante. A player
thrown back who then got hurt does not prove the owner right, and a keeper who
broke out does not prove him smart. So every comparison is reported twice:

  ex ante    what was knowable at the deadline: prior-season roto points, and
             the model's own price for that line
  realised   what the player actually did in the decision season, priced on
             that season's own scale

A gap between the two columns is luck. A consistent gap in one direction is
skill, or a model error. Do not collapse them.

THREE POPULATIONS, AND ONLY THE FIRST IS CLEAN

  kept        owner paid `keeper_salary`. Counterfactual: he could have had the
              money instead.
  thrown back owner declined `keeper_salary`. For the subset re-bought at the
              next auction we observe the market's price for the same player,
              which is the sharpest single comparison in the file: the owner
              said "not worth $S" and the room then said "worth $X".
  unlabeled   in-season drops, not modelled (docs/FINDINGS.md #56.4).

2026 decisions have clean labels (n=134). 2023-2025 are reconstructed and carry
a selection bias: "kept" is only detectable when the player was LATER thrown
back, so held-forever keepers are missing and the kept class skews marginal.
They are reported separately and must not be pooled without saying so.

    PYTHONPATH=.:scripts python3 scripts/decision_audit.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from klab import config as C
from price_features import scored_history


def realised_by_season() -> pd.DataFrame:
    """Roto points each player actually produced, per season, on that season's
    own denominators. A player with no line scores 0: not playing is an outcome,
    not missing data."""
    sc = scored_history()
    return sc[["season", "fg_id", "roto_points"]].rename(
        columns={"season": "decision_season", "roto_points": "rp_realised"})


def rebuy_prices() -> pd.DataFrame:
    """What the auction paid for a player in the season he was thrown back.

    This is the market's answer to the owner's question. Only defined for the
    thrown-back players who were actually re-bought; the rest went unsold or
    were added later through free agency and leave no price.
    """
    f = pd.read_csv(C.OUT / "price_features.csv")
    return (f[["season", "fg_id", "salary"]]
            .rename(columns={"season": "decision_season", "salary": "rebuy_price"}))


def dollars_per_point(season: int) -> float:
    """The redraft scale in force. NOTE: this is the CURRENT build's rate applied
    to every season, which is wrong in level for 2023-2025 and right in ordering.
    Fixing it needs a per-season scale; flagged rather than silently fudged."""
    import json
    return float(json.loads((C.OUT / "model_params.json").read_text())
                 ["usd_per_rp_redraft"])


def names() -> dict:
    """fg_id -> name, from the purchase table and the current roster."""
    f = pd.read_csv(C.OUT / "price_features.csv")
    m = dict(zip(f["fg_id"], f["player"]))
    r = pd.read_csv(C.DATA / "rosters_valued.csv")
    r["player_id"] = pd.to_numeric(r["player_id"], errors="coerce")
    m.update(dict(zip(r.dropna(subset=["player_id"])["player_id"].astype(int),
                      r.dropna(subset=["player_id"])["name"])))
    return m


def build() -> pd.DataFrame:
    d = pd.read_csv(C.OUT / "keeper_decisions.csv")
    d["name"] = d["fg_id"].map(names())
    d = d.merge(realised_by_season(), on=["decision_season", "fg_id"], how="left")
    d["played"] = d["rp_realised"].notna().astype(int)
    d["rp_realised"] = d["rp_realised"].fillna(0.0)
    d = d.merge(rebuy_prices(), on=["decision_season", "fg_id"], how="left")

    usd = dollars_per_point(2026)
    params = pd.read_json(C.OUT / "model_params.json", typ="series")
    # Per-role bars, matching the board's own pricing. The scalar
    # `replacement_rp` is min(HIT, PIT) = the pitcher bar and overstated
    # every hitter's value by ~$10 here (FINDINGS #80).
    rbr = params.get("replacement_by_role") or {}
    if rbr:
        repl = np.where(d["role"] == "PIT", rbr["PIT"], rbr["HIT"])
    else:
        repl = float(params["replacement_rp"])
    # Value of what he actually produced, on the same scale the board uses.
    d["value_realised"] = ((d["rp_realised"] - repl) * usd + 1.0).clip(lower=0)
    d["value_ex_ante"] = ((d["rp_prior"] - repl) * usd + 1.0).clip(lower=0)

    # The decision's outcome, signed so that positive always means "the owner
    # came out ahead", whichever way he decided.
    kept = d["kept"] == 1
    d["surplus_realised"] = np.where(
        kept, d["value_realised"] - d["keeper_salary"],
        d["keeper_salary"] - d["value_realised"])
    d["surplus_ex_ante"] = np.where(
        kept, d["value_ex_ante"] - d["keeper_salary"],
        d["keeper_salary"] - d["value_ex_ante"])
    d["right_call_realised"] = (d["surplus_realised"] > 0).astype(int)
    d["right_call_ex_ante"] = (d["surplus_ex_ante"] > 0).astype(int)
    return d


def section(title: str) -> None:
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


def main() -> int:
    d = build()
    clean, recon = d[d["decision_season"] == 2026], d[d["decision_season"] < 2026]

    section("SCOREBOARD: how often the owner came out ahead")
    for lab, sub in (("2026 (clean labels)", clean),
                     ("2023-2025 (reconstructed, selection-biased)", recon)):
        if not len(sub):
            continue
        g = sub.groupby(sub["kept"].map({1: "kept", 0: "thrown back"})).apply(
            lambda x: pd.Series({
                "n": len(x),
                "mean_salary": round(x["keeper_salary"].mean(), 2),
                "right_ex_ante_%": round(100 * x["right_call_ex_ante"].mean(), 1),
                "right_realised_%": round(100 * x["right_call_realised"].mean(), 1),
                "mean_surplus_ex_ante": round(x["surplus_ex_ante"].mean(), 2),
                "mean_surplus_realised": round(x["surplus_realised"].mean(), 2),
            }), include_groups=False)
        print(f"\n{lab}")
        print(g.to_string())

    section("THE SHARPEST COMPARISON: he said no, the room said yes")
    rb = clean[(clean["kept"] == 0) & clean["rebuy_price"].notna()].copy()
    if len(rb):
        rb["market_minus_declined"] = rb["rebuy_price"] - rb["keeper_salary"]
        # Every thrown-back player has a re-buy price by construction: appearing
        # in that season's auction is HOW the throw-back is detected (#56.4).
        # This is the whole class, not a subset of it.
        print(f"thrown back, and therefore re-auctioned, in 2026: n={len(rb)}")
        print(f"  declined at a mean of ${rb['keeper_salary'].mean():.2f}, "
              f"re-bought for a mean of ${rb['rebuy_price'].mean():.2f}")
        print(f"  the room paid MORE than the owner declined: "
              f"{int((rb['market_minus_declined'] > 0).sum())} of {len(rb)}")
        print("\n  biggest disagreements (room paid most above the declined salary):")
        cols = ["name", "keeper_salary", "rebuy_price", "rp_prior", "rp_realised",
                "value_realised"]
        print(rb.nlargest(10, "market_minus_declined")[cols].round(2).to_string(index=False))
        print("\n  the owner was most vindicated (room paid least):")
        print(rb.nsmallest(8, "market_minus_declined")[cols].round(2).to_string(index=False))
    else:
        print("no re-bought thrown-back players found; check the rebuy join")

    section("LUCK vs JUDGMENT: where ex ante and realised disagree")
    for lab, sub in (("2026", clean), ("2023-2025", recon)):
        if not len(sub):
            continue
        agree = int((sub["right_call_ex_ante"] == sub["right_call_realised"]).sum())
        print(f"  {lab}: the two verdicts agree on {agree} of {len(sub)} decisions "
              f"({100 * agree / len(sub):.0f}%)")
        print(f"    looked right, turned out wrong: "
              f"{int(((sub['right_call_ex_ante'] == 1) & (sub['right_call_realised'] == 0)).sum())}")
        print(f"    looked wrong, turned out right: "
              f"{int(((sub['right_call_ex_ante'] == 0) & (sub['right_call_realised'] == 1)).sum())}")

    section("OPEN QUESTIONS THIS FILE DOES NOT ANSWER")
    print("""  1. Would the MODEL have done better? Needs the model's own keep/cut call
     as of each past deadline, which needs a projection built from data as of
     that date. Not reconstructable from the current build; the board is a
     2027 object. This is the single biggest gap in validating the product.
  2. The dollar scale is the 2026 one applied to every season. Levels for
     2023-2025 are wrong; ordering is not. See dollars_per_point().
  3. Realised value uses the redraft scale, so a kept player is scored against
     what he would fetch in a full redraft, not against the keeper market he
     was actually in. market_price is the better denominator and only exists
     for 2027.
  4. Roster-spot opportunity cost is ignored, which published practice says is
     the main thing surplus value misses (see the brief's sources).""")

    path = C.OUT / "decision_audit.csv"
    d.to_csv(path, index=False)
    print(f"\nwrote {path}  ({len(d)} decisions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
