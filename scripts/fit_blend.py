"""Fit the blend weights, which METHODS section 3 #9 admits were never fitted.

`BLEND_W_2026 = 0.50` caps how much of the prior season's realised line the
projection carries; `PT_BLEND_CAP_HITTER = 0.30` and `PT_BLEND_CAP_PITCHER =
0.15` cap it separately for playing time (#51). All four are judgment calls.
`klab/rewind.py` makes them scorable for the first time: blend season T-1
actuals into Marcel-for-T, price the result, and score the KEEP/CUT DECISIONS it
would have produced against what actually happened.

WHAT IS BEING OPTIMISED, AND WHY IT IS NOT CORRELATION

The objective is dollars of keeper surplus captured, on the replacement-cost
scale, against the keep-everything baseline (docs/FINDINGS.md #69). A blend that
raises the rank correlation between projection and outcome but does not move a
single keep/cut call is worth nothing to this project, and a blend that improves
ten marginal calls is worth a lot even if the correlation is flat.

LEAVE ONE SEASON OUT, BECAUSE THREE SEASONS IS NOT MANY

Picking the weight that scores best across 2024-2026 and then reporting that
score is fitting and evaluating on the same data. Each season is therefore held
out in turn: the weight is chosen on the other two and scored on the held-out
one. The gap between the in-sample and held-out columns is how much of any
apparent gain is fitting noise. #7 is this file's cautionary tale.

TWO CAVEATS THAT BOUND THE ANSWER

1. **Marcel already averages three prior seasons internally**, so blending T-1
   actuals back in double-counts them harder than blending into ZiPS does. ZiPS
   2027 loads 2026 at roughly a quarter of 2025's weight (checked directly:
   regressing ZiPS 2027 rates on 2025 and 2026 rates gives 0.60 against 0.16),
   so it carries the prior season but not fully. Read the SHAPE here (is the cap
   binding? is 0.50 far from flat?), never the level.
2. **Only 2024-2026 exist**, one of them a partial season, and the 2024-2025
   keeper labels are reconstructed (#56.4). Three points is enough to see a
   shape and not enough to fit a constant to two decimals.

    PYTHONPATH=.:scripts python3 scripts/fit_blend.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from klab import config as C
from klab.rewind import blended_points, price_points, realised_board
from backtest_keepers import decisions

pd.set_option("display.width", 220)

SEASONS = (2024, 2025, 2026)
W_GRID = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
PT_GRID = [0.0, 0.15, 0.30, 0.50, 0.75, 1.0]
POOL_RULE = "slot_role"


def score(season: int, w_cap: float, pt_hit: float, pt_pit: float) -> dict:
    """Keeper surplus a blend would have captured in one season.

    Both the model's calls and the truth use the replacement-cost scale, which
    is the only correct denominator for a keep (#69): keeping at $S forgoes $S
    of auction budget, so keeping is right iff replacing him costs more.
    """
    pts = blended_points(season, w_cap=w_cap, pt_cap_hit=pt_hit, pt_cap_pit=pt_pit)
    board = price_points(pts, season, POOL_RULE)[["fg_id", "replace_cost"]]
    real = realised_board(season, POOL_RULE)[["fg_id", "replace_cost"]].rename(
        columns={"replace_cost": "true_replace"})

    d = decisions()
    d = d[d["decision_season"] == season].merge(
        board.rename(columns={"replace_cost": "proj"}), on="fg_id", how="left")
    d = d.merge(real, on="fg_id", how="left")
    d[["proj", "true_replace"]] = d[["proj", "true_replace"]].fillna(0.0)

    surplus = d["true_replace"] - d["keeper_salary"]
    call = (d["proj"] > d["keeper_salary"]).astype(int)
    truth = (surplus > 0).astype(int)
    return {"season": season, "n": len(d),
            "dollars": float((call * surplus).sum()),
            # Against keeping everything, which already captures most of the
            # available surplus in this league (#69). Zero is not the baseline.
            "vs_keep_all": float((call * surplus).sum() - surplus.sum()),
            "accuracy": float((call == truth).mean()),
            "kept": float(call.mean())}


def sweep_rate_cap() -> pd.DataFrame:
    """`BLEND_W_2026` swept with the playing-time caps held at production."""
    rows = []
    for w in W_GRID:
        for s in SEASONS:
            r = score(s, w, C.PT_BLEND_CAP_HITTER, C.PT_BLEND_CAP_PITCHER)
            rows.append({"w_cap": w, **r})
    return pd.DataFrame(rows)


def sweep_pt_cap() -> pd.DataFrame:
    """Both playing-time caps swept together, rate cap held at production."""
    rows = []
    for pt in PT_GRID:
        for s in SEASONS:
            r = score(s, C.BLEND_W_2026, pt, pt)
            rows.append({"pt_cap": pt, **r})
    return pd.DataFrame(rows)


def loso(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Choose the weight on two seasons, score it on the third."""
    rows = []
    for held in SEASONS:
        train = df[df["season"] != held].groupby(key)["vs_keep_all"].mean()
        best = float(train.idxmax())
        test = df[(df["season"] == held) & (df[key] == best)].iloc[0]
        prod = C.BLEND_W_2026 if key == "w_cap" else C.PT_BLEND_CAP_HITTER
        base = df[(df["season"] == held) & (np.isclose(df[key], prod))]
        rows.append({
            "held_out": held, f"best_{key}_on_other_two": best,
            "in_sample_mean_$": round(float(train.max()), 1),
            "held_out_$": round(float(test["vs_keep_all"]), 1),
            "production_$": round(float(base["vs_keep_all"].iloc[0]), 1) if len(base) else np.nan,
            "gain_vs_production": round(
                float(test["vs_keep_all"]) - float(base["vs_keep_all"].iloc[0]), 1)
            if len(base) else np.nan,
        })
    return pd.DataFrame(rows)


def section(t: str) -> None:
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    section("1. RATE BLEND CAP (BLEND_W_2026, production 0.50)")
    print("dollars of keeper surplus against the keep-everything baseline")
    rc = sweep_rate_cap()
    piv = rc.pivot(index="w_cap", columns="season", values="vs_keep_all").round(1)
    piv["mean"] = piv.mean(axis=1).round(1)
    print(piv.to_string())
    print("\naccuracy of the keep/cut call at each cap")
    print((100 * rc.pivot(index="w_cap", columns="season", values="accuracy")
           ).round(1).to_string())

    section("2. LEAVE ONE SEASON OUT: does the best cap survive?")
    print(loso(rc, "w_cap").to_string(index=False))

    section("3. PLAYING-TIME CAPS (production 0.30 hitters / 0.15 pitchers)")
    pc = sweep_pt_cap()
    pp = pc.pivot(index="pt_cap", columns="season", values="vs_keep_all").round(1)
    pp["mean"] = pp.mean(axis=1).round(1)
    print(pp.to_string())

    section("4. LEAVE ONE SEASON OUT, PLAYING TIME")
    print(loso(pc, "pt_cap").to_string(index=False))

    section("5. THE PRODUCTION SETTING ITSELF")
    # Section 3 moves both playing-time caps together, so it never evaluates the
    # asymmetric pair production actually ships (0.30 hitters, 0.15 pitchers).
    prod = pd.DataFrame([score(s, C.BLEND_W_2026, C.PT_BLEND_CAP_HITTER,
                               C.PT_BLEND_CAP_PITCHER) for s in SEASONS])
    print(f"w_cap={C.BLEND_W_2026}, pt_hit={C.PT_BLEND_CAP_HITTER}, "
          f"pt_pit={C.PT_BLEND_CAP_PITCHER} (shipped today)")
    print(prod[["season", "n", "vs_keep_all", "accuracy", "kept"]].round(3).to_string(index=False))
    print(f"  mean vs keep-everything: ${prod['vs_keep_all'].mean():.1f}")

    section("6. HOW FLAT IS IT?")
    m = rc.groupby("w_cap")["vs_keep_all"].mean()
    print(f"  best cap {m.idxmax():.2f} at ${m.max():.1f}; production 0.50 at "
          f"${m.loc[0.50]:.1f}; worst {m.idxmin():.2f} at ${m.min():.1f}")
    print(f"  spread across the whole 0-1 grid: ${m.max() - m.min():.1f} per season,")
    print(f"  against a perfect-foresight headroom of several hundred dollars (#69).")
    out = C.OUT / "blend_sweep.csv"
    rc.assign(knob="w_cap").rename(columns={"w_cap": "value"}).to_csv(out, index=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
