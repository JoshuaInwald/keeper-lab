"""Comp-based next-auction price estimate for one player -- a separate
exercise from the rest of the model (see klab/auction_estimator.py's module
docstring for what this is and isn't).

    PYTHONPATH=. python3 scripts/estimate_auction_price.py "Freddie Freeman"
    PYTHONPATH=. python3 scripts/estimate_auction_price.py "Tarik Skubal" --k 20
"""
import argparse

import pandas as pd

import klab.config as C
from klab.auction_estimator import estimate_auction_price


def load_players() -> pd.DataFrame:
    board = pd.read_csv(C.OUT / "keeper_board_2027.csv")
    p = pd.read_csv(C.OUT / "player_values_2027.csv")
    p = p.copy()
    p["name"] = p["fg_id"].map(board.set_index("fg_id")["name"])
    p["role"] = p["fg_id"].map(board.set_index("fg_id")["role"])
    return p.dropna(subset=["name", "role"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--k", type=int, default=15, help="number of comps")
    args = ap.parse_args()

    players = load_players()
    res = estimate_auction_price(args.name, players, k=args.k)

    print(f"{res['name']}  ({res['position']}, {res['role']})")
    print(f"  projected 2027 roto points: {res['roto_points']:.2f}")
    print(f"  regression fair value:      ${res['regression_fair_value']:.2f}")
    print(f"  comp-adjusted estimate:     ${res['comp_adjusted_low']:.2f} - "
          f"${res['comp_adjusted_high']:.2f}  (median ${res['comp_adjusted_mid']:.2f})")
    print(f"  n comps: {res['n_comps']}"
          + ("  (fell back to full role -- position pool too thin)"
             if res["fallback_to_full_role"] else
             f"  (position pool: {res['n_same_position_available']} available)"))
    print(f"\n  {'season':6s} {'player':22s} {'salary':>6s} {'rp':>6s} {'premium':>8s}")
    for _, r in res["comps"].iterrows():
        print(f"  {r['season']:<6.0f} {r['player']:22s} ${r['salary']:>5.0f} "
              f"{r['roto_points']:6.2f} {r['premium_frac']:+7.0%}")


if __name__ == "__main__":
    main()
