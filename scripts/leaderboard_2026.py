"""2026 full-season leaderboard: what every player was actually worth.

Full season = actuals through 121 games + ZiPS rest-of-season. Scored on the
same denominators as the 2027 keeper board so the two are directly comparable.

`hindsight_$` is the number Josh asked for: what this player would have gone
for at the 2026 auction if his 2026 production had been guaranteed in advance.
It is a perfect-foresight price -- the whole pool is renormalised so the 230
rostered players clear exactly the league's $2,600 of cap space. Comparing it
to what was actually paid is the cleanest picture of who was a bargain.
"""
import numpy as np
import pandas as pd

import klab.config as C
from klab.auction import match_drafts
from klab.board import build_2027_scorer
from klab.io import load_contracts, load_rosters
from klab.trade import ros_lines
from klab.project import project_hitters, project_pitchers, fit_save_model

pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 60)


def full_2026():
    """2026 actuals + rest-of-season, per player."""
    from klab.io import load_hitters_history, load_pitchers_history
    from klab.io import load_ros_hitters, load_ros_pitchers

    hc = ["PA", "AB", "H", "HR", "R", "RBI", "SB"]
    h = load_hitters_history()
    a = h[h["season"] == 2026].groupby("fg_id", as_index=False).agg(
        {"name": "first", **{c: "sum" for c in hc}})
    r = load_ros_hitters()[["fg_id"] + hc].groupby("fg_id", as_index=False).sum()
    H = a.merge(r, on="fg_id", how="outer", suffixes=("", "_r"))
    H["name"] = H["name"].fillna("")
    for c in hc:
        H[c] = H[c].fillna(0.0) + H[f"{c}_r"].fillna(0.0)
    H = H[H["PA"] > 0][["fg_id", "name"] + hc]
    H["AVG"] = H["H"] / H["AB"].replace(0, np.nan)
    H["role"] = "HIT"

    pc = ["IP", "W", "SV", "K", "ER", "BB", "H"]
    p = load_pitchers_history()
    a = p[p["season"] == 2026].groupby("fg_id", as_index=False).agg(
        {"name": "first", **{c: "sum" for c in pc}})
    r = load_ros_pitchers().rename(columns={"SO": "K"})[["fg_id"] + pc].groupby(
        "fg_id", as_index=False).sum()
    P = a.merge(r, on="fg_id", how="outer", suffixes=("", "_r"))
    P["name"] = P["name"].fillna("")
    for c in pc:
        P[c] = P[c].fillna(0.0) + P[f"{c}_r"].fillna(0.0)
    P = P[P["IP"] > 0][["fg_id", "name"] + pc]
    P["ERA"] = P["ER"] * 9 / P["IP"]
    P["WHIP"] = (P["BB"] + P["H"]) / P["IP"]
    P["role"] = "PIT"
    return H, P


def main():
    scorer, D, base, _ = build_2027_scorer()
    H, P = full_2026()
    Hs = H.join(scorer.hitters(H)[["roto_points"]])
    Ps = P.join(scorer.pitchers(P)[["roto_points"]])

    cols = ["PA", "HR", "R", "RBI", "SB", "AVG", "IP", "W", "SV", "K", "ERA", "WHIP"]
    both = pd.concat([Hs, Ps], ignore_index=True)
    for c in cols:
        if c not in both:
            both[c] = np.nan
    agg = {"roto_points": "sum", "name": "first",
           **{c: "sum" for c in ["PA", "HR", "R", "RBI", "SB", "IP", "W", "SV", "K"]},
           "AVG": "max", "ERA": "min", "WHIP": "min"}
    agg["role"] = lambda s: "TWO" if s.nunique() > 1 else s.iloc[0]
    d = both.groupby("fg_id", as_index=False).agg(agg)

    # perfect-foresight dollars: renormalise so the 230 rostered players
    # clear the league's actual $2,600
    n = C.N_TEAMS * C.N_ACTIVE
    top = d.nlargest(n, "roto_points")
    repl = float(top["roto_points"].min())
    pool = float(top["roto_points"].sum() - repl * n)
    usd = (C.N_TEAMS * C.BUDGET - n * 1.0) / pool
    d["hindsight_$"] = ((d["roto_points"] - repl) * usd + 1).clip(lower=0)

    # what was actually paid, and who holds him now
    dr = match_drafts(verbose=False)
    dr = dr[dr["season"] == 2026].dropna(subset=["fg_id"])
    dr["fg_id"] = dr["fg_id"].astype(int)
    d = d.merge(dr[["fg_id", "salary"]].rename(columns={"salary": "drafted_$"}),
                on="fg_id", how="left")
    # rosters_valued already carries salary+contract and is one row per
    # roster spot. Ohtani has two contract rows (batter and pitcher) sharing
    # one FanGraphs id, so dedupe or he lands on the board twice.
    ros = load_rosters()[["fg_id", "team", "salary", "contract"]].rename(
        columns={"salary": "current_$"})
    ros = ros.sort_values("current_$", ascending=False).drop_duplicates("fg_id")
    d = d.merge(ros, on="fg_id", how="left")
    d["bargain"] = d["hindsight_$"] - d["current_$"]

    d = d.sort_values("roto_points", ascending=False).reset_index(drop=True)
    d.insert(0, "rank", d.index + 1)
    d.to_csv(C.OUT / "leaderboard_2026.csv", index=False)

    print(f"replacement level (230th player): {repl:.2f} roto pts | "
          f"${usd:.2f} per roto point above replacement")
    show = ["rank", "name", "role", "team", "current_$", "contract", "drafted_$",
            "roto_points", "hindsight_$", "bargain",
            "PA", "HR", "R", "RBI", "SB", "AVG", "IP", "W", "SV", "K", "ERA", "WHIP"]
    print("\n=== TOP 60 BY 2026 ROTO VALUE (actuals + ROS) ===")
    print(d.head(60)[show].round(2).to_string(index=False))
    print("\n=== 25 BIGGEST BARGAINS ON CURRENT ROSTERS (hindsight $ - salary) ===")
    print(d[d["team"].notna()].nlargest(25, "bargain")[show].round(2).to_string(index=False))
    print("\n=== 20 WORST CONTRACTS ON CURRENT ROSTERS ===")
    print(d[d["team"].notna()].nsmallest(20, "bargain")[show].round(2).to_string(index=False))
    print(f"\nwrote {C.OUT / 'leaderboard_2026.csv'} ({len(d)} players)")


if __name__ == "__main__":
    main()
