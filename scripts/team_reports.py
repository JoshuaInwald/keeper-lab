"""Per-team 2027 keeper recommendations + where 2026 production came from.

Two outputs:
  1. For every team, the recommended keeper set with the full arithmetic
     exposed so each number can be checked by hand.
  2. Decomposition of 2026 roto production by acquisition channel
     (auction / keeper / in-season free agent).
"""
import sys

import numpy as np
import pandas as pd

import klab.config as C
from klab.board import build_board, fit_exchange_rate, value_players
from klab.io import load_drafts

pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 60)


def keeper_report(board, team, meta, exch):
    d = board[board["team"] == team].sort_values("surplus_multiyear",
                                                 ascending=False)
    cols = ["name", "role", "contract", "years_controlled", "salary",
            "keeper_cost", "roto_points", "redraft_value", "redraft_value_ft",
            "redraft_value_2028", "extension_option", "surplus_redraft",
            "surplus_multiyear", "keep_2027"]
    print(f"\n{'='*110}\n{team}\n{'='*110}")
    print(d[cols].round(2).to_string(index=False))
    k = d[d["keep_2027"]]
    print(f"\n  RECOMMEND KEEPING {len(k)}  |  salary committed ${k['keeper_cost'].sum():.0f}"
          f"  |  auction budget left ${C.BUDGET - k['keeper_cost'].sum():.0f}"
          f"  |  total surplus +${k['surplus_multiyear'].sum():.0f}")
    marg = d[~d["keep_2027"]].head(3)
    if len(marg):
        print("  closest calls not kept: " + ", ".join(
            f"{r['name']} (${r['surplus_multiyear']:+.0f})" for _, r in marg.iterrows()))


def acquisition_channels(board):
    """How much of each team's 2026 roto production came from which channel.

    Channel is inferred from the 2026 auction file plus the league's fixed
    free-agent prices: $10 is the pre-All-Star-break acquisition cost and $20
    the post-break cost, so a player at exactly those salaries who does not
    appear in the auction is an in-season pickup.

    Caveat: rosters are as of mid-August. A player acquired in July carries
    the production he banked for his previous team, so "free agent" production
    is overstated to the extent teams traded for or claimed producing players.
    """
    from klab.auction import match_drafts
    lb = pd.read_csv(C.OUT / "leaderboard_2026.csv")
    dr = match_drafts(verbose=False)
    dr = dr[(dr["season"] == 2026) & dr["fg_id"].notna()]
    d26 = set(dr["fg_id"].astype(int))

    b = board[["team", "fg_id", "name", "salary", "contract"]].copy()
    b = b.merge(lb[["fg_id", "roto_points", "hindsight_$"]], on="fg_id", how="left")
    b["roto_points"] = b["roto_points"].fillna(0.0)

    def channel(r):
        if int(r["fg_id"]) in d26:
            return "auction 2026"
        if r["salary"] in (C.FA_SALARY_PRE_ASB, C.FA_SALARY_POST_ASB):
            return "free agent"
        return "keeper"

    b["channel"] = b.apply(channel, axis=1)

    print(f"\n{'='*110}\nWHERE 2026 PRODUCTION CAME FROM\n{'='*110}")
    tot = b.groupby("channel").agg(
        players=("name", "size"), salary=("salary", "sum"),
        roto=("roto_points", "sum"), value=("hindsight_$", "sum"))
    tot["roto_share"] = 100 * tot["roto"] / tot["roto"].sum()
    tot["roto_per_$"] = tot["roto"] / tot["salary"]
    print(tot.round(2).to_string())

    piv = b.pivot_table(index="team", columns="channel", values="roto_points",
                        aggfunc="sum").fillna(0)
    piv["TOTAL"] = piv.sum(axis=1)
    share = piv[[c for c in piv.columns if c != "TOTAL"]].div(piv["TOTAL"], axis=0) * 100
    print("\nshare of each team's 2026 roto production, by channel (%):")
    print(share.round(1).sort_values("free agent", ascending=False).to_string())

    print("\nefficiency: roto points banked per $ committed, by team and channel")
    sal = b.pivot_table(index="team", columns="channel", values="salary",
                        aggfunc="sum").fillna(0)
    eff = (piv[[c for c in piv.columns if c != "TOTAL"]] / sal).replace(
        [np.inf, -np.inf], np.nan)
    print(eff.round(2).to_string())
    b.to_csv(C.OUT / "acquisition_channels_2026.csv", index=False)
    return b


if __name__ == "__main__":
    exch, _ = fit_exchange_rate()
    _, _, meta = value_players(exch)
    board, exch, meta2 = build_board()

    print("MODEL CONSTANTS USED")
    print(f"  exchange rate : roto_points = {exch['intercept']:.3f} "
          f"+ {exch['slope']:.4f} x $   (n={exch['n']}, seasons {exch['seasons']})")
    print(f"  replacement   : {meta2['replacement_rp']:.3f} roto points (230th projection)")
    print(f"  redraft scale : ${meta2['usd_per_rp_redraft']:.3f} per roto point above replacement")
    print(f"  budget check  : top-230 redraft values sum to ${meta2['budget_check_top230']:,.0f}")
    print(f"  denominators  : " + ", ".join(
        f"{k} {v:.4g}" for k, v in meta2["denominators"].items()))

    teams = sys.argv[1:] or sorted(board["team"].unique())
    for t in teams:
        keeper_report(board, t, meta2, exch)
    acquisition_channels(board)
