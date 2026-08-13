"""Backtest: does the engine explain seasons other than 2026?

The headline validation (current rosters -> 2026 standings, Spearman 0.842) is
one season, and the rosters used were the ones that produced those standings.
This is a harder test: for every auction 2022-26, sum the roto points each
team's *drafted* players actually delivered, and see whether that predicts
where the team finished.

It is deliberately incomplete -- draft picks are only a third of a roster, so
a perfect model would not reach 1.0. What matters is whether the relationship
is positive and stable across five independent seasons.
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import klab.config as C
from klab.auction import auction_sample
from klab.io import load_standings_long
from klab.trade import standings_points

pd.set_option("display.width", 300)


def main():
    s = auction_sample()
    st = load_standings_long()

    print("=" * 96)
    print("BACKTEST — do drafted roto points predict where a team finished?")
    print("=" * 96)
    rows = []
    for y in sorted(s["season"].unique()):
        w = st[st["season"] == y].pivot(index="team", columns="category", values="total")
        pts = standings_points(w[C.CATS])["TOTAL"]
        g = (s[s["season"] == y]
             .groupby("team")
             .agg(drafted_rp=("roto_points", "sum"),
                  spend=("salary", "sum"), n=("salary", "size")))
        g["rp_per_$"] = g["drafted_rp"] / g["spend"]
        # team names drift across seasons; match what we can
        g = g.join(pts.rename("standings"), how="inner")
        if len(g) < 6:
            print(f"  {y}: only {len(g)} teams matched by name, skipping")
            continue
        rows.append({
            "season": y, "teams_matched": len(g),
            "rho_drafted_rp": spearmanr(g["drafted_rp"], g["standings"]).statistic,
            "rho_rp_per_$": spearmanr(g["rp_per_$"], g["standings"]).statistic,
            "rho_spend": spearmanr(g["spend"], g["standings"]).statistic,
        })
    t = pd.DataFrame(rows)
    print(t.round(3).to_string(index=False))
    print()
    print(f"  mean rho(drafted roto points, standings) = {t['rho_drafted_rp'].mean():+.3f}")
    print(f"  mean rho(roto points per $,   standings) = {t['rho_rp_per_$'].mean():+.3f}")
    print(f"  mean rho(auction spend,       standings) = {t['rho_spend'].mean():+.3f}")
    print()
    print("  Drafted production should predict finishing position. Raw spend")
    print("  should predict it far less -- that is the whole thesis, and if")
    print("  spend correlated as strongly the engine would be adding nothing.")

    print("\n" + "=" * 96)
    print("CATEGORY-LEVEL CHECK — does a category's roto points track its standings points?")
    print("=" * 96)
    out = []
    for y in sorted(st["season"].unique()):
        w = st[st["season"] == y].pivot(index="team", columns="category", values="total")
        pts = standings_points(w[C.CATS])
        for cat in C.CATS:
            out.append({"season": y, "category": cat,
                        "rho": spearmanr(w[cat], pts[cat]).statistic})
    o = pd.DataFrame(out).pivot(index="category", columns="season", values="rho")
    print(o.round(3).loc[C.CATS].to_string())
    print("\n  ERA and WHIP must be -1.0 (lower total = more points); everything")
    print("  else must be +1.0. Any other value means a sign convention broke.")
    bad = ((o.loc[[c for c in C.CATS if c not in C.NEG_CATS]] < 0.99).any().any()
           or (o.loc[list(C.NEG_CATS)] > -0.99).any().any())
    print(f"  sign conventions: {'**BROKEN**' if bad else 'all correct'}")


if __name__ == "__main__":
    main()
