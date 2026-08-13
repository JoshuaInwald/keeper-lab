"""Evaluate a trade on both lenses, with a per-player breakdown.

    PYTHONPATH=. python3 scripts/eval_trade.py \
        "NPB No Stars" "Spehr's Army" \
        "Julio Rodriguez,Tarik Skubal" "Christian Scott,Brandon Lowe"
"""
import sys

import pandas as pd

import klab.config as C
from klab.board import build_board
from klab.denoms import (RotoScorer, denominators_for_level,
                         pooled_relative_dispersion, season_levels,
                         team_baselines)
from klab.trade import evaluate_trade, find_player, format_trade, ros_lines

pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 60)


def ros_roto():
    """Rest-of-2026 roto points per player, on the 2026 scale."""
    sig = pooled_relative_dispersion(seasons=C.DENOM_SEASONS)
    lv = season_levels()
    D26 = denominators_for_level(
        sig, lv[lv.season == 2026].set_index("category")["level"].to_dict())
    sc = RotoScorer(D26, team_baselines([2026]).iloc[0].to_dict())
    ros = ros_lines().rename(columns={"H_allowed": "Hp"})
    h = sc.hitters(ros[["PA", "AB", "H", "HR", "R", "RBI", "SB"]])
    p = ros.copy(); p["H"] = p["Hp"]
    pp = sc.pitchers(p[["IP", "W", "SV", "K", "ER", "BB", "H"]])
    ros["ros_rp"] = h["roto_points"].fillna(0) + pp["roto_points"].fillna(0)
    return ros


def main():
    a_team, b_team = sys.argv[1], sys.argv[2]
    a_send = [x.strip() for x in sys.argv[3].split(",") if x.strip()]
    b_send = [x.strip() for x in sys.argv[4].split(",") if x.strip()]

    board, exch, meta = build_board()
    ros = ros_roto()

    print("=== PER-PLAYER ===")
    rows = []
    for who, names in ((a_team, a_send), (b_team, b_send)):
        for n in names:
            p = find_player(board, n)
            r = ros[ros.fg_id == p["fg_id"]]
            rows.append({
                "from": who, "name": p["name"], "contract": p["contract"],
                "yrs": p["years_controlled"], "salary": p["salary"],
                "keeper_cost": p["keeper_cost"], "pt_scale": p["pt_scale"],
                "ros_2026_rp": float(r["ros_rp"].iloc[0]) if len(r) else 0.0,
                "rp_2027": p["roto_points"], "val_2027": p["redraft_value"],
                "rp_2028": p["roto_points_2028"],
                "val_2028": p["redraft_value_2028"],
                "surplus_2027": p["surplus_redraft"],
                "surplus_multiyr": p["surplus_multiyear"],
            })
    print(pd.DataFrame(rows).round(2).to_string(index=False))

    res = evaluate_trade(board, a_team, b_team, a_send, b_send)
    print("\n" + format_trade(res))
    print("\n2026 category standings-point deltas:")
    for t, d in res["win_now"]["category_point_delta"].items():
        print(" ", t, {k: round(v, 1) for k, v in d.items() if abs(v) > 0.01})
    print("\nall teams, 2026 pts before -> after:")
    pb, pa = res["win_now"]["points_before"], res["win_now"]["points_after"]
    for t in sorted(pb, key=lambda x: -pb[x]):
        print(f"  {t:26s} {pb[t]:5.1f} -> {pa[t]:5.1f}  ({pa[t]-pb[t]:+.1f})")


if __name__ == "__main__":
    main()
