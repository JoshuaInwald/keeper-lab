"""Print the board rows for a set of players."""
import sys

import pandas as pd

from klab.board import build_board

pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 60)

COLS = ["team", "name", "contract", "years_controlled", "salary", "keeper_cost",
        "pt_scale", "PA", "IP", "SV", "roto_points", "redraft_value",
        "roto_points_2028", "redraft_value_2028", "surplus_redraft",
        "surplus_multiyear"]

if __name__ == "__main__":
    board, exch, meta = build_board()
    print("board rows:", len(board))
    names = sys.argv[1:] or ["DeLauter", "Julio Rodr", "Skubal",
                             "Christian Scott", "Brandon Lowe"]
    for n in names:
        m = board[board["name"].str.contains(n, case=False, na=False)]
        print(m[COLS].round(2).to_string(index=False) if len(m) else f"NOT FOUND: {n}")
