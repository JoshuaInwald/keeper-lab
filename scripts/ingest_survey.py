"""Score the survey answers against the model, and against each other.

Takes the JSON blobs `out/keeper_survey.html` produces and turns opinions into a
comparison. `docs/FINDINGS.md` #69 found the model does not beat this league's
owners out of sample, so a reviewer's calls are a benchmark and not a review:
the interesting output is not "he agreed with us 80% of the time" but the list
of expensive contracts where he and the model disagree, which is the only place
either of them can learn anything.

    python3 scripts/ingest_survey.py data/survey_*.json

Save each reviewer's pasted text as its own `.json` file first. `data/` is
gitignored, which is the right place for one person's private opinions.

THREE COMPARISONS, IN ORDER OF WHAT THEY TEACH

1. **Disagreements, ranked by dollars at stake.** Where he says cut and the
   model says keep on an expensive contract, one of them is wrong by a lot.
   These are the rows to argue about and then to score after 2027 is played.
2. **Price calibration, split by role.** The model's most falsifiable claim is
   that this league underpays for pitching: 20 of its 25 biggest bargains are
   pitchers. If the reviewer's auction prices come in above the model's for
   pitchers and level for hitters, that claim is dead and the board is
   overvaluing arms. If they come in level, the edge is real.
3. **Reviewer against reviewer**, when there is more than one. Two experts
   disagreeing on a player is a different signal from both disagreeing with the
   model, and it bounds how much of any gap is judgment rather than noise.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from klab import config as C


def load(paths: list[str]) -> pd.DataFrame:
    rows = []
    for p in paths:
        blob = json.loads(open(p).read())
        who = blob.get("who") or p
        for fg_id, a in blob.get("answers", {}).items():
            if a.get("keep") is None:
                continue
            rows.append({"who": who, "fg_id": int(fg_id), "name": a.get("name"),
                         "their_keep": bool(a["keep"]),
                         "their_price": a.get("price")})
    if not rows:
        raise SystemExit("no answered players found in those files")
    return pd.DataFrame(rows)


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        raise SystemExit(__doc__)
    ans = load(paths)

    b = pd.read_csv(C.OUT / "keeper_board_2027.csv")
    keep_col = b[["fg_id", "role", "keeper_cost", "keep_2027", "surplus_multiyear",
                  "market_price", "production_value", "keep_value"]]
    d = ans.merge(keep_col, on="fg_id", how="left")
    d["model_keep"] = d["keep_2027"].fillna(False).astype(bool)
    d["agree"] = d["their_keep"] == d["model_keep"]

    print("=" * 74)
    print("1. EACH REVIEWER AGAINST THE MODEL")
    print("=" * 74)
    for who, g in d.groupby("who"):
        print(f"\n{who}: {len(g)} answered, keeps {100*g['their_keep'].mean():.0f}% "
              f"where the model keeps {100*g['model_keep'].mean():.0f}%, "
              f"agree on {100*g['agree'].mean():.0f}%")
        dis = g[~g["agree"]].copy()
        if not len(dis):
            print("  no disagreements")
            continue
        dis["at_stake"] = dis["keeper_cost"].fillna(0)
        print("  biggest disagreements, most money first:")
        cols = ["name", "role", "keeper_cost", "surplus_multiyear", "their_keep"]
        top = dis.nlargest(min(10, len(dis)), "at_stake")[cols].round(1)
        top = top.rename(columns={"surplus_multiyear": "model_surplus",
                                  "their_keep": "he_keeps"})
        print(top.to_string(index=False))

    print()
    print("=" * 74)
    print("2. PRICE CALIBRATION, BY ROLE  (the model's most falsifiable claim)")
    print("=" * 74)
    pr = d[d["their_price"].notna() & d["market_price"].notna()].copy()
    if not len(pr):
        print("no prices given yet")
    else:
        pr["err"] = pr["their_price"] - pr["market_price"]
        for who, g in pr.groupby("who"):
            print(f"\n{who}: {len(g)} prices")
            for role in ("HIT", "PIT"):
                s = g[g["role"] == role]
                if not len(s):
                    continue
                print(f"  {role}: n={len(s):3d}  his mean ${s['their_price'].mean():5.1f}  "
                      f"model ${s['market_price'].mean():5.1f}  "
                      f"he is {'HIGHER' if s['err'].mean() > 0 else 'lower'} "
                      f"by ${abs(s['err'].mean()):.1f}")
            h = g[g["role"] == "HIT"]["err"].mean() if (g["role"] == "HIT").any() else np.nan
            p_ = g[g["role"] == "PIT"]["err"].mean() if (g["role"] == "PIT").any() else np.nan
            if np.isfinite(h) and np.isfinite(p_):
                print(f"  pitcher minus hitter bias: ${p_ - h:+.1f}. Positive means he prices "
                      f"pitchers ABOVE the model,\n  which would kill the 'the room underpays "
                      f"for pitching' claim; near zero leaves it alive.")

    if d["who"].nunique() > 1:
        print()
        print("=" * 74)
        print("3. REVIEWER AGAINST REVIEWER")
        print("=" * 74)
        w = d.pivot_table(index=["fg_id", "name"], columns="who",
                          values="their_keep", aggfunc="first").dropna()
        if len(w) and w.shape[1] > 1:
            a, bb = w.columns[0], w.columns[1]
            same = (w[a] == w[bb]).mean()
            print(f"\n{len(w)} players answered by both; they agree on {100*same:.0f}%")
            split = w[w[a] != w[bb]].reset_index()
            if len(split):
                print("  where they split:")
                print(split.merge(keep_col, on="fg_id")[
                    ["name", "role", "keeper_cost", a, bb, "keep_2027"]
                ].rename(columns={"keep_2027": "model"}).round(1).to_string(index=False))
        else:
            print("\nnot enough overlap yet")

    out = C.OUT / "survey_comparison.csv"
    d.to_csv(out, index=False)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
