"""Would the model have beaten the owners? The out-of-sample keep/cut test.

This is the test `docs/FINDINGS.md` #66 named as the biggest gap in the project.
#66 scored the OWNERS on 336 past keeper decisions and could not score the
MODEL, because `board.py` is a 2027 object. `klab/rewind.py` rewinds it and the
Marcel archive (#67) supplies an honest ex-ante projection, so both sides of the
comparison now exist for 2024, 2025 and 2026.

THE COMPARISON

For each past decision (a player, his keeper salary, and the season it was
decided for) there is what the owner did, what each candidate rule would have
advised, and what the season then showed.

  owner            what the owner actually did, from `out/keeper_decisions.csv`
  model_redraft    keep iff projected `redraft_value` > salary. What board.py
                   does today: `surplus_multiyear` runs off `redraft_value`.
  model_replace    keep iff projected replacement cost > salary. The
                   opportunity-cost rule; see `klab.rewind.rewound_exchange`.
  model_matched_k  the model keeping exactly as many players as the owner did,
                   which removes the threshold and tests ranking alone
  truth            keeping was right iff REPLACEMENT COST exceeded the salary

TWO METRICS, AND THE SECOND IS THE ONE THAT MATTERS

  accuracy   share of calls that matched truth. Easy to read, but it treats a
             $1 mistake and a $40 mistake alike.
  dollars    surplus captured, `c * (replace_cost - keeper_salary)` summed.
             Throwing a player back is the zero baseline: the salary returns to
             the budget and buys roughly fair value at auction.

READ EVERY DOLLAR FIGURE AGAINST `keep everything`, NOT AGAINST ZERO. This
league withholds enough keepers that contracts are cheap on average, so keeping
them all already captures most of the available surplus. A caller that trails
that baseline is subtracting value no matter how positive its raw total looks.

THREE THINGS THAT LIMIT WHAT THIS CAN CLAIM, ALL STRUCTURAL

1. **Marcel is the naive baseline, not ZiPS** (#67). A model win here means the
   engine beats the owners USING A DELIBERATELY DUMB PROJECTION. That is a
   floor on the real board's edge, not an estimate of it. A model loss would be
   damning; a model win is encouraging and not conclusive.
2. **2024 and 2025 labels are reconstructed and selection-biased** (#56.4).
   Pre-2026 a keep is only detectable when the player was LATER thrown back, so
   the observed "kept" class skews marginal and the owners look worse than they
   were. That bias flatters the model. 2026 labels are clean; lead with them.
3. **2026 outcomes are a partial season** (~75% at the 2026-09-07 pull). Both
   sides are calibrated to the same $2,600 identity on 2026's own partial
   scale, which absorbs the level error, but a full-season projection scored
   against a three-quarter season still favours durable players.

There is no season with both clean labels and complete outcomes. All three are
reported separately and must not be pooled.

    PYTHONPATH=.:scripts python3 scripts/backtest_keepers.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from klab import config as C
from klab.auction import match_drafts
from klab.rewind import POOL_RULES, realised_board, rewound_board

pd.set_option("display.width", 220)

SEASONS = (2024, 2025, 2026)


def decisions() -> pd.DataFrame:
    """The owner side, with the team that held each contract attached.

    Team comes from the auction the player was bought in (`buy_season`), which
    is the only place it is recorded for a past decision. It is needed for the
    roster-constrained variant: the league caps keepers at MAX_KEEPERS and
    forces MIN_KEEPERS, so an owner can decline a positive-surplus player.
    """
    d = pd.read_csv(C.OUT / "keeper_decisions.csv")
    d = d[d["decision_season"].isin(SEASONS)].copy()
    d["fg_id"] = d["fg_id"].astype(int)
    # match_drafts(), not load_drafts(): the raw auction files carry fg_id for
    # only a minority of rows, and a silent all-NaN join made the roster-cap
    # variant identical to the unconstrained one.
    drafts = (match_drafts(verbose=False).dropna(subset=["fg_id"])
              .rename(columns={"season": "buy_season"}))
    drafts["fg_id"] = drafts["fg_id"].astype(int)
    team = drafts.groupby(["buy_season", "fg_id"], as_index=False)["team"].first()
    return d.merge(team, on=["buy_season", "fg_id"], how="left")


def team_constrained_calls(d: pd.DataFrame, value_col: str) -> pd.Series:
    """`board.mark_optimal_keepers` applied to a past season, MAX_KEEPERS only.

    MIN_KEEPERS is deliberately NOT applied. The production rule forces six
    keepers out of a team's full set of keepable contracts; `keeper_decisions`
    holds only the decisions that could be RECOVERED, which for 2024-2025 is a
    biased subset (#56.4) and for 2026 runs 4 to 17 rows per team. Forcing six
    out of a four-row view would invent keeps the owner was never choosing
    between, so only the cap that can be evaluated on a partial view is used.

    Rows with no team keep their unconstrained call rather than being dropped,
    so both variants always score the same decisions.
    """
    surplus = d[value_col] - d["keeper_salary"]
    call = (surplus > 0).astype(int)
    for _, g in d.assign(_s=surplus).groupby(["decision_season", "team"]):
        pos = g[g["_s"] > 0].sort_values("_s", ascending=False).head(C.MAX_KEEPERS)
        call.loc[g.index] = 0
        call.loc[pos.index] = 1
    return call


CALLERS = ["owner", "model_redraft", "model_replace", "model_matched_k"]


def build(pool_rule: str) -> pd.DataFrame:
    """One row per decision, with every caller's call and the truth.

    THE TRUTH COLUMN IS THE REPLACEMENT-COST ONE, and the choice matters more
    than anything else in this file. Keeping a player at $S forgoes $S of
    auction budget, and $S of budget buys `intercept + S * slope` roto points,
    so keeping is right exactly when his realised production exceeds that.
    Equivalently `replace_cost > salary`. Scoring against `redraft_value`
    instead asks what he would fetch in a no-keeper redraft, a cheaper market,
    which makes every keep look bad: on that scale only 17-28% of these
    decisions are keeps, against owners keeping 47-55%. Because the model keeps
    less often than owners do, that bias would hand the model a win for free.
    `surplus_redraft` is kept alongside so the size of the bias stays visible.
    """
    d = decisions()
    frames = []
    for s in SEASONS:
        sub = d[d["decision_season"] == s].copy()
        proj = rewound_board(s, pool_rule)[
            ["fg_id", "redraft_value", "replace_cost", "rel", "role"]].rename(
            columns={"redraft_value": "proj_redraft",
                     "replace_cost": "proj_replace"})
        real = realised_board(s, pool_rule)[
            ["fg_id", "value_realised", "replace_cost"]].rename(
            columns={"replace_cost": "true_replace"})
        sub = sub.drop(columns=[c for c in ("role",) if c in sub])
        sub = sub.merge(proj, on="fg_id", how="left")
        sub = sub.merge(real, on="fg_id", how="left")
        frames.append(sub)
    d = pd.concat(frames, ignore_index=True)

    # A player with no Marcel line had no MLB record to project from, and a
    # player with no realised line did not play. Both are real outcomes worth
    # $0, not missing data; `has_proj` keeps the distinction auditable.
    d["has_proj"] = d["proj_redraft"].notna()
    for c in ("proj_redraft", "proj_replace", "value_realised", "true_replace"):
        d[c] = d[c].fillna(0.0)

    d["surplus_true"] = d["true_replace"] - d["keeper_salary"]
    d["surplus_redraft"] = d["value_realised"] - d["keeper_salary"]
    d["truth"] = (d["surplus_true"] > 0).astype(int)

    d["owner"] = d["kept"].astype(int)
    # The production rule (board.py runs surplus_multiyear off redraft_value)
    # and the opportunity-cost rule, so the backtest can choose between them.
    d["model_redraft"] = (d["proj_redraft"] > d["keeper_salary"]).astype(int)
    d["model_replace"] = (d["proj_replace"] > d["keeper_salary"]).astype(int)
    d["model_matched_k"] = matched_k_calls(d)
    d["model_teamcap"] = team_constrained_calls(d, "proj_redraft")
    return d


def matched_k_calls(d: pd.DataFrame) -> pd.Series:
    """The model keeping exactly as many players as the owner did, per season.

    This is the cleanest single comparison in the file because it removes the
    threshold entirely. Both callers keep the same COUNT, so whoever captures
    more surplus did so by picking better players, not by being more or less
    willing to keep. Any residual difference is ranking skill.
    """
    call = pd.Series(0, index=d.index)
    for s, g in d.groupby("decision_season"):
        k = int(g["owner"].sum())
        top = (g["proj_replace"] - g["keeper_salary"]).nlargest(k).index
        call.loc[top] = 1
    return call


def scoreboard(d: pd.DataFrame, calls: list[str]) -> pd.DataFrame:
    """Accuracy and dollars captured, per caller, on one set of decisions."""
    # Keeping everything is the baseline that matters, not $0. This league
    # withholds enough keepers that contracts are cheap on average, so a naive
    # "keep them all" already captures most of the available surplus and any
    # caller has to be read against it, not against zero.
    keep_all = d["surplus_true"].sum()
    rows = []
    for c in calls:
        captured = (d[c] * d["surplus_true"]).sum()
        rows.append({
            "caller": c, "n": len(d),
            "kept_%": round(100 * d[c].mean(), 1),
            "accuracy_%": round(100 * (d[c] == d["truth"]).mean(), 1),
            "dollars": round(captured, 1),
            "vs_keep_all": round(captured - keep_all, 1),
            "per_decision": round(captured / len(d), 2),
        })
    # The ceiling and the floor, so a number in the middle can be read.
    perfect = d["surplus_true"].clip(lower=0).sum()
    rows.append({"caller": "perfect foresight", "n": len(d),
                 "kept_%": round(100 * d["truth"].mean(), 1), "accuracy_%": 100.0,
                 "dollars": round(perfect, 1),
                 "vs_keep_all": round(perfect - keep_all, 1),
                 "per_decision": round(perfect / len(d), 2)})
    rows.append({"caller": "keep everything", "n": len(d), "kept_%": 100.0,
                 "accuracy_%": round(100 * d["truth"].mean(), 1),
                 "dollars": round(keep_all, 1), "vs_keep_all": 0.0,
                 "per_decision": round(keep_all / len(d), 2)})
    return pd.DataFrame(rows)


def head_to_head(d: pd.DataFrame, model_col: str) -> pd.DataFrame:
    """Only the decisions where model and owner disagreed.

    This is the sharpest cut in the file. Where they agree the comparison is
    uninformative; the entire edge, in either direction, lives here.
    """
    dis = d[d[model_col] != d["owner"]]
    if not len(dis):
        return pd.DataFrame()
    rows = []
    for s, g in dis.groupby("decision_season"):
        rows.append({
            "season": s, "disagreements": len(g),
            "model_right": int((g[model_col] == g["truth"]).sum()),
            "owner_right": int((g["owner"] == g["truth"]).sum()),
            "model_$": round((g[model_col] * g["surplus_true"]).sum(), 1),
            "owner_$": round((g["owner"] * g["surplus_true"]).sum(), 1),
        })
    return pd.DataFrame(rows)


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    d = build("slot_role")

    section("1. DOES THE MODEL BEAT THE OWNERS?   (pool rule: slot_role)")
    print("truth = replacement cost exceeded the salary; dollars = surplus captured")
    for s in SEASONS:
        sub = d[d["decision_season"] == s]
        label = ("CLEAN labels, partial-season outcomes: the one to lead with"
                 if s == 2026 else
                 "reconstructed labels, selection-biased toward the model (#56.4)")
        print(f"\n-- {s} (n={len(sub)}, {label})")
        print(scoreboard(sub, CALLERS).to_string(index=False))

    section("2. SAME KEEP COUNT: ranking skill, or just keeping fewer?")
    print("model_matched_k keeps exactly as many players as the owner did, so a")
    print("win here cannot come from the threshold. It is player selection.")
    rows = []
    for s in SEASONS:
        sub = d[d["decision_season"] == s]
        o = (sub["owner"] * sub["surplus_true"]).sum()
        m = (sub["model_matched_k"] * sub["surplus_true"]).sum()
        rows.append({"season": s, "n": len(sub), "k_kept": int(sub["owner"].sum()),
                     "owner_$": round(o, 1), "model_$": round(m, 1),
                     "edge_$": round(m - o, 1),
                     "edge_per_decision": round((m - o) / len(sub), 2),
                     "owner_acc_%": round(100 * (sub["owner"] == sub["truth"]).mean(), 1),
                     "model_acc_%": round(100 * (sub["model_matched_k"] == sub["truth"]).mean(), 1)})
    print(pd.DataFrame(rows).to_string(index=False))

    section("3. HEAD TO HEAD, only where the two disagreed (model_replace)")
    print(head_to_head(d, "model_replace").to_string(index=False))

    section("4. WHICH SCALE SHOULD THE KEEP THRESHOLD USE?")
    print("board.py runs surplus_multiyear off redraft_value. The opportunity-cost")
    print("rule keeps iff replacing him would cost more than his salary.")
    rows = []
    for s in SEASONS:
        sub = d[d["decision_season"] == s]
        for c in ("model_redraft", "model_replace"):
            rows.append({"season": s, "rule": c,
                         "kept_%": round(100 * sub[c].mean(), 1),
                         "accuracy_%": round(100 * (sub[c] == sub["truth"]).mean(), 1),
                         "dollars": round((sub[c] * sub["surplus_true"]).sum(), 1)})
    print(pd.DataFrame(rows).to_string(index=False))

    section("5. WHICH POOL RULE? chosen by decision quality, not by argument")
    print("#68 argued slot_role from a perfect-foresight benchmark. This scores the")
    print("calls each rule would actually have produced.")
    rows = []
    for pool_rule in POOL_RULES:
        b = build(pool_rule)
        for s in SEASONS:
            sub = b[b["decision_season"] == s]
            rows.append({"pool_rule": pool_rule, "season": s,
                         "redraft_acc_%": round(100 * (sub["model_redraft"] == sub["truth"]).mean(), 1),
                         "redraft_$": round((sub["model_redraft"] * sub["surplus_true"]).sum(), 1),
                         "replace_acc_%": round(100 * (sub["model_replace"] == sub["truth"]).mean(), 1),
                         "replace_$": round((sub["model_replace"] * sub["surplus_true"]).sum(), 1)})
    print(pd.DataFrame(rows).to_string(index=False))

    section("6. HOUSEKEEPING")
    cov = d.groupby("decision_season")["has_proj"].agg(["sum", "count"])
    for s, r in cov.iterrows():
        print(f"  Marcel coverage {s}: {int(r['sum'])}/{int(r['count'])} "
              f"({100 * r['sum'] / r['count']:.0f}%); unprojected players are called $0")
    n_cap = int((d["model_redraft"] != d["model_teamcap"]).sum())
    max_keeps = int(d.groupby(["decision_season", "team"])["model_redraft"].sum().max())
    print(f"  MAX_KEEPERS binds on {n_cap} of {len(d)} decisions (most any team "
          f"keeps is {max_keeps} against a cap of {C.MAX_KEEPERS}), so the roster "
          f"constraint is not what separates the callers.")
    lowrel = d[d["rel"].notna() & (d["rel"] < 0.30)]
    print(f"  Marcel rel < 0.30 on {len(lowrel)} of {len(d)} decided players; "
          f"#67 warns those rows are mostly league mean.")
    print(f"  On the redraft scale only {100 * (d['surplus_redraft'] > 0).mean():.0f}% "
          f"of these keeps read as right, against {100 * d['truth'].mean():.0f}% on "
          f"the replacement-cost scale. That gap is the bias this file avoids.")

    out = C.OUT / "backtest_keepers.csv"
    d.to_csv(out, index=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
