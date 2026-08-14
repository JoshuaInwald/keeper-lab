"""Precompute trade suggestions for every team pair, three scenarios each.

Kept separate from run_all.py's hot path on purpose: 45 team pairs x ~200
candidate combinations each is a real cost (a couple minutes), not the
sub-10-second cost the rest of the build is. Run this after roster changes,
not on every rebuild.

    PYTHONPATH=.:scripts python3 scripts/build_trade_suggestions.py
"""
import itertools
import json
import time

import klab.config as C
from klab.board import build_board
from klab.io import load_standings_long
from klab.trade import standings_points
from klab.trade_finder import suggest_trades

OUT = C.OUT


def main():
    board, exch, meta = build_board()
    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category", values="total")
    standings_pts = standings_points(cur[C.CATS])["TOTAL"].to_dict()

    teams = sorted(board["team"].unique())
    print(f"{len(teams)} teams, {len(teams) * (len(teams) - 1) // 2} pairs")

    all_suggestions = []
    t0 = time.time()
    for team_a, team_b in itertools.combinations(teams, 2):
        res = suggest_trades(board, exch, team_a, team_b, standings_pts)
        all_suggestions.append(res)
        found = sum(1 for k in ("win_now_for_future", "challenge_trade", "mutual_value_swap")
                    if res[k] is not None)
        print(f"  {team_a} <-> {team_b}: {found}/3 scenarios found")

    (OUT / "trade_suggestions.json").write_text(json.dumps(all_suggestions, indent=2, default=str))
    print(f"\nwrote {OUT / 'trade_suggestions.json'} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
