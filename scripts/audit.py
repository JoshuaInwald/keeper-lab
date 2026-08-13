"""Data-integrity audit: accounting identities that must hold.

This is the answer to "how do I check your work without reading every line".
None of these look at the model. They are arithmetic facts about a 10-team,
$260, 23-slot league that must be true regardless of how anything is
computed. When one fails, the data is wrong -- and it will usually tell you
*which* file is wrong.

The keeper-file problem was found exactly this way: keepers + auction picks
should roughly fill 230 active slots, and keeper salaries + auction spend
should equal $2,600. For 2022-25 both failed by enormous margins.

    PYTHONPATH=. python3 scripts/audit.py
"""
import glob

import numpy as np
import pandas as pd

import klab.config as C
from klab.io import (load_contracts, load_drafts, load_hitters_history,
                     load_pitchers_history, load_rosters, load_standings_long)

pd.set_option("display.width", 300)

FAILS = []


def check(name, ok, detail=""):
    tag = "PASS" if ok else "**FAIL**"
    print(f"  [{tag}] {name}")
    if detail:
        print(f"           {detail}")
    if not ok:
        FAILS.append(name)


def roster_accounting():
    """Every active slot in the league is filled by a keeper or an auction pick."""
    print("\n1. ROSTER ACCOUNTING — keepers + auction picks should fill 230 slots")
    d = load_drafts()
    kc = {}
    for f in sorted(glob.glob(str(C.DATA / "keepers_*.csv"))) + \
             sorted(glob.glob("/mnt/user-data/uploads/Fantasy Baseball/keepers_*.csv")):
        y = int(f.split("_")[-1][:4])
        kc.setdefault(y, len(pd.read_csv(f)))
    rows = []
    for y in sorted(d["season"].unique()):
        picks = int((d["season"] == y).sum())
        spend = int(d.loc[d["season"] == y, "salary"].sum())
        keep = kc.get(y, np.nan)
        rows.append({
            "season": y, "keepers_in_file": keep, "auction_picks": picks,
            "sum": keep + picks if keep == keep else np.nan,
            "slots_unaccounted": 230 - (keep + picks) if keep == keep else np.nan,
            "auction_spend": spend, "implied_keeper_$": C.N_TEAMS * C.BUDGET - spend,
            "implied_$_per_keeper": round((C.N_TEAMS * C.BUDGET - spend) / keep, 1)
            if keep == keep and keep else np.nan,
        })
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    for r in rows:
        if r["keepers_in_file"] != r["keepers_in_file"]:
            continue
        # a keeper costing more than $25 on average is not credible in a
        # $260 league where the whole point of keeping is a discount
        check(f"{r['season']} implied keeper salary is credible",
              r["implied_$_per_keeper"] < 25,
              f"${r['implied_$_per_keeper']}/keeper from "
              f"${r['implied_keeper_$']} across {r['keepers_in_file']} keepers")
        check(f"{r['season']} roster slots roughly accounted for",
              abs(r["slots_unaccounted"]) < 50,
              f"{r['slots_unaccounted']:.0f} of 230 slots unexplained")
    print("\n  Estimated TRUE keeper counts from the two identities:")
    t["est_from_slots"] = 230 - t["auction_picks"]
    t["est_from_budget"] = (t["implied_keeper_$"] / 13.6).round(0)
    print(t[["season", "keepers_in_file", "est_from_slots", "est_from_budget"]].to_string(index=False))


def salary_cap():
    print("\n2. SALARY CAP — committed salary vs the $260 x 10 cap")
    r = load_rosters()
    per = r.groupby("team")["salary"].sum()
    print(per.sort_values(ascending=False).to_string())
    check("no team is absurdly over the cap", per.max() < C.BUDGET * 2,
          f"max ${per.max()}, cap ${C.BUDGET} (reserve/IL players inflate this)")


def contract_consistency():
    print("\n3. CONTRACTS — codes align with when the player was last bought")
    from klab.auction import match_drafts
    c = load_contracts()
    d = match_drafts(verbose=False).dropna(subset=["fg_id"])
    d["fg_id"] = d["fg_id"].astype(int)
    last = d.sort_values("season").groupby("fg_id")["season"].max().rename("last_draft")
    m = c.join(last, on="fg_id")
    ct = pd.crosstab(m["contract"], m["last_draft"])
    print(ct.to_string())
    expected = {"2": 2026, "1": 2025, "F": 2024}
    for code, yr in expected.items():
        if code in ct.index and yr in ct.columns:
            share = ct.loc[code, yr] / ct.loc[code].sum()
            check(f"code '{code}' is mostly {yr} acquisitions", share > 0.6,
                  f"{share:.0%} of coded-'{code}' drafted players came from {yr}")


def stats_vs_standings():
    """Do the players in the stats files add up to the league's team totals?"""
    print("\n4. STATS vs STANDINGS — is the player pool big enough to produce the totals?")
    st = load_standings_long()
    hit, pit = load_hitters_history(), load_pitchers_history()
    for y in sorted(st["season"].unique()):
        w = st[st["season"] == y].pivot(index="team", columns="category", values="total")
        lg_hr = w["HR"].sum()
        pool_hr = hit[hit["season"] == y].nlargest(140, "PA")["HR"].sum()
        ratio = lg_hr / pool_hr if pool_hr else np.nan
        check(f"{y} league HR is achievable from the top-140 hitter pool",
              0.6 < ratio < 1.25,
              f"league {lg_hr:.0f} vs pool {pool_hr:.0f} (ratio {ratio:.2f})")


def duplicates_and_ids():
    print("\n5. IDENTIFIERS")
    r = load_rosters()
    dup = r["fg_id"].duplicated().sum()
    check("no duplicate player ids on rosters", dup == 0, f"{dup} duplicates")
    c = load_contracts()
    check("every rostered player has a contract",
          r["fg_id"].isin(c["fg_id"]).mean() > 0.95,
          f"{100*r['fg_id'].isin(c['fg_id']).mean():.0f}% matched")


if __name__ == "__main__":
    print("=" * 96)
    print("DATA INTEGRITY AUDIT")
    print("=" * 96)
    roster_accounting()
    salary_cap()
    contract_consistency()
    stats_vs_standings()
    duplicates_and_ids()
    print("\n" + "=" * 96)
    if FAILS:
        print(f"{len(FAILS)} CHECK(S) FAILED:")
        for f in FAILS:
            print(f"  - {f}")
    else:
        print("all checks passed")
    print("=" * 96)
