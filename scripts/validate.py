"""Sanity checks that must pass before any number is presented.

1. Does the roto-point scorer reproduce the 2026 standings from rosters?
2. Do the ten hand-checked players land where domain knowledge says?
3. Does the auction sample reconcile with the league's actual cap?
"""
import numpy as np
import pandas as pd

import klab.config as C
from klab.board import build_board, fit_exchange_rate
from klab.denoms import (RotoScorer, denominators_for_level,
                         pooled_relative_dispersion, season_levels,
                         team_baselines)
from klab.io import load_hitters_history, load_pitchers_history, load_standings_long
from klab.trade import standings_points

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 50)


def check_2026_standings(board):
    """Roll each team's CURRENT roster forward over its actual 2026 stats and
    compare the implied standings to the real ones.

    Caveat: rosters are as of mid-August, so anyone acquired in-season carries
    production they banked for a different team. This is a directional check,
    not an identity.
    """
    hit = load_hitters_history()
    pit = load_pitchers_history()
    h26 = hit[hit["season"] == 2026]
    p26 = pit[pit["season"] == 2026]

    r = board[["team", "fg_id"]]
    H = r.merge(h26, on="fg_id", how="inner")
    P = r.merge(p26, on="fg_id", how="inner")

    gh = H.groupby("team")[["AB", "H", "HR", "R", "RBI", "SB"]].sum()
    gp = P.groupby("team")[["IP", "W", "SV", "K", "ER", "BB", "H"]].sum()
    gp = gp.rename(columns={"H": "H_allowed"})
    t = gh.join(gp, how="outer").fillna(0.0)
    t["AVG"] = t["H"] / t["AB"]
    t["ERA"] = t["ER"] * 9 / t["IP"]
    t["WHIP"] = (t["BB"] + t["H_allowed"]) / t["IP"]

    pred = standings_points(t[C.CATS])
    st = load_standings_long()
    actual_wide = st[st["season"] == 2026].pivot(index="team", columns="category",
                                                 values="total")
    act = standings_points(actual_wide[C.CATS])

    cmp = pd.DataFrame({
        "predicted_pts": pred["TOTAL"], "actual_pts": act["TOTAL"],
    }).dropna()
    cmp["pred_rank"] = cmp["predicted_pts"].rank(ascending=False)
    cmp["act_rank"] = cmp["actual_pts"].rank(ascending=False)
    from scipy.stats import spearmanr, pearsonr
    rho = spearmanr(cmp["predicted_pts"], cmp["actual_pts"]).statistic
    r_p = pearsonr(cmp["predicted_pts"], cmp["actual_pts"]).statistic
    print("=== CHECK 1: current rosters -> 2026 standings ===")
    print(cmp.sort_values("actual_pts", ascending=False).round(1).to_string())
    print(f"\nSpearman(predicted, actual) = {rho:.3f}   Pearson = {r_p:.3f}")
    print("(rosters are mid-August, so in-season adds carry other teams' production)")
    return cmp


HAND_CHECK = [
    "Shohei Ohtani", "Aaron Judge", "Tarik Skubal", "Bobby Witt Jr.",
    "Paul Skenes", "Yordan Alvarez", "Elly De La Cruz", "Mason Miller",
    "Pete Alonso", "Spencer Strider",
]


def check_players(board):
    print("\n=== CHECK 2: hand-check across the value spectrum ===")
    cols = ["team", "name", "role", "contract", "salary", "keeper_cost",
            "PA", "HR", "R", "RBI", "SB", "AVG", "IP", "W", "SV", "K",
            "ERA", "WHIP", "roto_points", "redraft_value", "surplus_redraft"]
    rows = []
    for n in HAND_CHECK:
        m = board[board["name"].str.contains(n.split()[-1], case=False, na=False)]
        m = m[m["name"].str.lower().str[0] == n[0].lower()]
        if len(m):
            rows.append(m.iloc[0])
    print(pd.DataFrame(rows)[cols].round(2).to_string(index=False))


def check_budget(board, exch, meta):
    print("\n=== CHECK 3: budget reconciliation ===")
    tot_sal = board["salary"].sum()
    print(f"salary committed across all 275 rostered players: ${tot_sal:,.0f}")
    print(f"league cap (10 x $260):                           ${C.N_TEAMS*C.BUDGET:,.0f}")
    print(f"BUDGET IDENTITY top-230 redraft_value:            "
          f"${meta['budget_check_top230']:,.0f}  (must equal $2,600)")
    print(f"replacement roto points (230th player):           {meta['replacement_rp']:.2f}")
    print(f"auction regression intercept (free production):   {exch['intercept']:.2f}")
    print("  -> these two estimate the same quantity from independent data;")
    print("     agreement within ~0.8 roto points is the key validation.")
    print(f"$/roto point, auction opportunity cost:           ${meta['usd_per_rp_keep']:.2f}")
    print(f"$/roto point, redraft budget normalisation:       ${meta['usd_per_rp_redraft']:.2f}")

    k = board[board["keep_2027"]]
    by_team = k.groupby("team").agg(
        n_keep=("name", "size"), keeper_salary=("keeper_cost", "sum"),
        value=("redraft_value", "sum"), surplus=("surplus_redraft", "sum"))
    by_team["auction_budget_left"] = C.BUDGET - by_team["keeper_salary"]
    print("\n=== CHECK 4: optimal 2027 keeper set by team ===")
    print(by_team.sort_values("surplus", ascending=False).round(0).to_string())


if __name__ == "__main__":
    board, exch, meta = build_board()
    check_2026_standings(board)
    check_players(board)
    check_budget(board, exch, meta)
