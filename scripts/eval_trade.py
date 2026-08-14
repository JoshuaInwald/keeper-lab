"""Evaluate a trade on both lenses, with a per-player breakdown.

    PYTHONPATH=. python3 scripts/eval_trade.py \
        "NPB No Stars" "Spehr's Army" \
        "Julio Rodriguez,Tarik Skubal" "Christian Scott,Brandon Lowe"
"""
import sys

import pandas as pd

import klab.config as C
from klab.board import build_board, build_2027_scorer
from klab.trade import (evaluate_trade, find_player, format_trade, ros_lines,
                        ros_value_over_replacement)
from klab.uncertainty import bootstrap_bands

pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 60)


def main():
    a_team, b_team = sys.argv[1], sys.argv[2]
    a_send = [x.strip() for x in sys.argv[3].split(",") if x.strip()]
    b_send = [x.strip() for x in sys.argv[4].split(",") if x.strip()]

    board, exch, meta = build_board()
    board = board.merge(bootstrap_bands().reset_index(), on="fg_id", how="left")
    _, D, base, _ = build_2027_scorer()
    ros = ros_lines()

    print("=== PER-PLAYER ===")
    rows = []
    for who, names in ((a_team, a_send), (b_team, b_send)):
        for n in names:
            p = find_player(board, n)
            r = ros[ros.fg_id == p["fg_id"]].copy()
            if len(r):
                r["role"] = p["role"]
                r = ros_value_over_replacement(r, D, base, meta["replacement_rp"])
                ros_rp = float(r["ros_rp"].iloc[0])
                ros_vor = float(r["ros_value_over_replacement"].iloc[0])
                remaining_frac = float(r["remaining_frac"].iloc[0])
            else:
                ros_rp = ros_vor = remaining_frac = 0.0
            rows.append({
                "from": who, "name": p["name"], "contract": p["contract"],
                "yrs": p["years_controlled"], "salary": p["salary"],
                "keeper_cost": p["keeper_cost"], "pt_scale": p["pt_scale"],
                "ros_frac_left": remaining_frac, "ros_rp": ros_rp,
                "ros_value_over_repl": ros_vor,
                "rp_2027": p["roto_points"], "val_2027": p["redraft_value"],
                "val_2027_range": f"{p['value_lo']:.1f}-{p['value_hi']:.1f}"
                                  if pd.notna(p.get("value_lo")) else "n/a",
                "rp_2028": p["roto_points_2028"],
                "val_2028": p["redraft_value_2028"],
                "surplus_2027": p["surplus_redraft"],
                "surplus_multiyr": p["surplus_multiyear"],
                "surplus_range": f"{p['surplus_lo']:.1f}-{p['surplus_hi']:.1f}"
                                 if pd.notna(p.get("surplus_lo")) else "n/a",
                "p_surplus_pos": p.get("p_surplus_positive"),
            })
    print(pd.DataFrame(rows).round(2).to_string(index=False))
    print("\nros_value_over_repl: this player's rest-of-2026 roto value over a")
    print("replacement player for the SAME remaining playing time -- a")
    print("player-intrinsic number, not a team-standings swap (see win_now")
    print("below for that). out/FINDINGS.md #34.")
    print("\nval_2027_range / surplus_range: 10th-90th percentile bootstrap band")
    print("(1,000 resamples of the team-seasons the denominators are fit on --")
    print("klab/uncertainty.py). p_surplus_pos: share of draws where the")
    print("keeper surplus stayed positive -- a player positive in 96% of")
    print("draws is a very different decision from one positive in 55%.")

    res = evaluate_trade(board, a_team, b_team, a_send, b_send,
                         usd_per_point=exch["usd_per_point"])
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
