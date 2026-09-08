"""How much of a season carries into the next one, and does age change that?

The blend that builds 2027 (`docs/METHODS.md` 2.3) weights last year's actuals
by playing time and per-category reliability, and by nothing else. It does not
know how old a player is. Josh's question, 2026-09-08: a 22-year-old with a big
2026 and a 31-year-old with the same big 2026 are not the same bet, and ZiPS
2027 was pulled mid-season so it has only partly absorbed 2026 either.

This measures the thing directly, on this league's own scoring, using the five
seasons of FanGraphs actuals in `data/`: for every player with a line in season
Y-1, how well does Y-1 predict Y, and does that change with age?

Two populations, reported separately, because the difference between them IS
the answer for young players:

  survivors   players with a line in BOTH years. The naive persistence.
  all         players with a line in Y-1, counting a missing Y as zero roto
              points. This is the population the keeper decision actually faces:
              "he might not play" is part of the bet, and survivor-only
              persistence is the classic way to overrate prospects.

    PYTHONPATH=.:scripts python3 scripts/age_persistence.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

from klab import config as C
from price_features import playing_time, scored_history

SEASONS = (2022, 2023, 2024, 2025, 2026)


def pairs() -> pd.DataFrame:
    sc = scored_history()[["season", "fg_id", "roto_points", "role"]]
    pt = playing_time()
    d = sc.merge(pt, on=["season", "fg_id"], how="left")

    reg = pd.read_csv(C.DATA / "chadwick_register.csv")
    reg = reg[reg["birth_year"].notna()][["key_fangraphs", "birth_year"]]
    reg = reg.rename(columns={"key_fangraphs": "fg_id"}).astype({"fg_id": int})

    nxt = d[["season", "fg_id", "roto_points"]].copy()
    nxt["season"] = nxt["season"] - 1
    nxt = nxt.rename(columns={"roto_points": "rp_next"})

    out = d.merge(nxt, on=["season", "fg_id"], how="left")
    out = out[out["season"] < max(SEASONS)]          # 2026 has no "next" yet
    out = out.merge(reg, on="fg_id", how="left")
    out["age"] = out["season"] - out["birth_year"]
    out["survived"] = out["rp_next"].notna().astype(int)
    out["rp_next_all"] = out["rp_next"].fillna(0.0)
    out["vol"] = np.where(out["role"] == "PIT", out["IP"], out["PA"])
    return out


def band(a):
    if a <= 23: return "<=23"
    if a <= 26: return "24-26"
    if a <= 29: return "27-29"
    if a <= 32: return "30-32"
    return "33+"


def fit_band(g: pd.DataFrame, ycol: str) -> dict:
    """Slope of next-season roto points on this-season roto points."""
    if len(g) < 40:
        return {}
    X = sm.add_constant(g["roto_points"])
    m = sm.OLS(g[ycol], X).fit()
    return {"n": len(g), "slope": round(float(m.params["roto_points"]), 3),
            "se": round(float(m.bse["roto_points"]), 3),
            "R2": round(float(m.rsquared), 3),
            "intercept": round(float(m.params["const"]), 2)}


def main() -> int:
    d = pairs()
    d = d[d["age"].notna()]
    # A real season, not a cup of coffee: the population the blend applies to.
    d = d[((d["role"] == "HIT") & (d["PA"] >= 200))
          | ((d["role"] == "PIT") & (d["IP"] >= 40))].copy()
    d["age_band"] = d["age"].map(band)
    print(f"player-seasons with a real Y-1 line and a known age: {len(d)}")
    print(f"survive into Y: {int(d['survived'].sum())} "
          f"({100 * d['survived'].mean():.1f}%)\n")

    for ycol, lab in (("rp_next", "SURVIVORS ONLY (both seasons played)"),
                      ("rp_next_all", "ALL (missing next season counted as 0)")):
        sub = d if ycol == "rp_next_all" else d[d["survived"] == 1]
        print("=" * 72)
        print(f"{lab}: rp_next = a + b * rp_this, by age")
        print("=" * 72)
        rows = []
        for b_, g in sub.groupby("age_band"):
            r = fit_band(g, ycol)
            if r:
                r["age_band"] = b_
                r["survival"] = round(float(g["survived"].mean()), 3)
                r["mean_rp"] = round(float(g["roto_points"].mean()), 2)
                rows.append(r)
        order = {"<=23": 0, "24-26": 1, "27-29": 2, "30-32": 3, "33+": 4}
        t = pd.DataFrame(rows).sort_values("age_band", key=lambda s: s.map(order))
        print(t[["age_band", "n", "mean_rp", "survival", "slope", "se",
                 "intercept", "R2"]].to_string(index=False))
        print()

    print("=" * 72)
    print("Does age change the slope? Interaction test, all-population")
    print("=" * 72)
    x = pd.DataFrame({"const": 1.0, "rp": d["roto_points"],
                      "age_c": d["age"] - d["age"].mean()})
    x["rp_x_age"] = x["rp"] * x["age_c"]
    m = sm.OLS(d["rp_next_all"], x).fit(cov_type="HC1")
    print(pd.DataFrame({"coef": m.params.round(4), "se": m.bse.round(4),
                        "t": m.tvalues.round(2), "p": m.pvalues.round(4)}).to_string())
    b_rp, b_int = m.params["rp"], m.params["rp_x_age"]
    print(f"\nimplied slope at age 22: {b_rp + b_int * (22 - d['age'].mean()):.3f}")
    print(f"implied slope at age 30: {b_rp + b_int * (30 - d['age'].mean()):.3f}")

    print("\n" + "=" * 72)
    print("BIG SEASONS ONLY (top quartile of rp_this): what happens next?")
    print("=" * 72)
    cut = d["roto_points"].quantile(0.75)
    big = d[d["roto_points"] >= cut]
    g = big.groupby("age_band").apply(lambda x: pd.Series({
        "n": len(x), "mean_rp_this": round(x["roto_points"].mean(), 2),
        "survival": round(x["survived"].mean(), 3),
        "mean_rp_next_survivors": round(x.loc[x["survived"] == 1, "rp_next"].mean(), 2),
        "mean_rp_next_all": round(x["rp_next_all"].mean(), 2),
        "retained_pct_all": round(100 * x["rp_next_all"].mean() / x["roto_points"].mean(), 1),
    }), include_groups=False)
    print(g.reindex([b for b in order if b in g.index]).to_string())
    print(f"\n(top-quartile cut = {cut:.2f} roto points)")
    d.to_csv(C.OUT / "age_persistence.csv", index=False)
    print(f"\nwrote {C.OUT / 'age_persistence.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
