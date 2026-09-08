"""ROADMAP item 2, scoped: is team-specific category value estimable here?

The premise is not in doubt. A team already first in saves gains nothing from
more saves; a team 20 steals behind fourth gains a standings point from the next
ten. `denoms.py` prices both the same. The question this script answers is
whether the correction can be ESTIMATED from ten teams without being swamped by
noise, and the answer decides whether item 2 is a build or a dead end.

Two estimators, tested the way CLAUDE.md requires (persistence across seasons,
not fit quality within one):

  gap multiplier  `teamvalue.value_multipliers()`: units this team needs for one
                  standings point, from the local gaps around its own rank,
                  relative to the league-average team.
  category rank   just where the team finished, 1-10.

    PYTHONPATH=.:scripts python3 scripts/team_category_value.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from klab import config as C
from klab.teamvalue import value_multipliers

TRANSITIONS = ((2022, 2023), (2023, 2024), (2024, 2025), (2025, 2026))


def wides() -> dict:
    st = pd.read_csv(C.DATA / "standings_long_all.csv")
    out = {}
    for s, g in st.groupby("season"):
        w = g.pivot(index="team", columns="category", values="total")
        out[int(s)] = w.rename(columns={"BA": "AVG"})[list(C.CATS)]
    return out


def ranks(w: pd.DataFrame) -> pd.DataFrame:
    r = pd.DataFrame(index=w.index)
    for c in C.CATS:
        r[c] = w[c].rank(ascending=(c not in C.NEG_CATS))
    return r


def persistence(W: dict, transform) -> pd.DataFrame:
    rows = []
    for c in C.CATS:
        xs, ys = [], []
        for a, b in TRANSITIONS:
            common = [t for t in W[a].index if t in W[b].index]
            xs += list(transform(W[a]).loc[common, c])
            ys += list(transform(W[b]).loc[common, c])
        rows.append({"cat": c, "n": len(xs),
                     "persistence": round(float(spearmanr(xs, ys).statistic), 3)})
    return pd.DataFrame(rows)


def main() -> int:
    W = wides()
    print("Spread of the gap multiplier within a season (1.0 = league-average team)")
    for s in sorted(W):
        m = value_multipliers(W[s]).values
        print(f"  {s}: {m.min():.2f} to {m.max():.2f}, median {np.median(m):.2f}")
    print("\nA 0.3x-to-13x swing in what a unit is worth is the whole prize, IF it is real.\n")

    gap = persistence(W, value_multipliers).rename(columns={"persistence": "gap_mult"})
    rnk = persistence(W, ranks).rename(columns={"persistence": "rank"})
    t = gap.merge(rnk[["cat", "rank"]], on="cat")
    print("Year-over-year persistence, same team same category, pooled over 4 transitions")
    print(t.to_string(index=False))
    print(f"\n  mean gap-multiplier persistence: {t['gap_mult'].mean():+.3f}")
    print(f"  mean rank persistence:           {t['rank'].mean():+.3f}")

    print("\nVERDICT")
    print("  The gap multiplier does not persist at all. Where a team sits RELATIVE")
    print("  to the pack in a category is a property of one season's realised")
    print("  standings, not of the team, so pricing 2027 players with it would be")
    print("  fitting noise -- the same n=10 instability as METHODS section 3 #1.")
    print("  Category RANK persists modestly and unevenly: usable in K, SB, R, AVG")
    print("  and SV, absent in RBI and ERA. That is a contend-or-punt flag, not a")
    print("  continuous multiplier, and it is a much smaller build than item 2 as")
    print("  written.")
    print("\n  Saves are the standing counterexample and already handled")
    print("  (docs/FINDINGS.md #1): every season has one or two punters at 0-16 and")
    print("  the rest in a band, which is structural rather than noise.")
    for s in sorted(W):
        print(f"    {s} SV: {sorted(W[s]['SV'].round(0).astype(int).tolist())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
