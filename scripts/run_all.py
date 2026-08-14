"""Build everything and write the output files."""
import json

import pandas as pd

import klab.config as C
from klab.auction import auction_sample, spec_battery
from klab.board import build_board, fit_exchange_rate
from klab.denoms import (denominator_table, pooled_relative_dispersion,
                         season_levels)
from klab.project import fit_save_model

OUT = C.OUT


def main():
    sigma = pooled_relative_dispersion(seasons=C.DENOM_SEASONS)
    sigma.to_csv(OUT / "denominator_dispersion.csv", index=False)
    denominator_table().to_csv(OUT / "denominators_by_season.csv", index=False)
    season_levels().to_csv(OUT / "league_levels_by_season.csv", index=False)

    sample = auction_sample()
    sample.to_csv(OUT / "auction_sample.csv", index=False)
    spec_battery(sample).to_csv(OUT / "auction_regression_battery.csv", index=False)

    board, exch, meta = build_board()

    # Uncertainty bands used to live only inside the app's own payload merge
    # (scripts/build_app.py) -- every other consumer of the board (this CSV,
    # eval_trade.py, team_reports.py) showed point estimates only, with no
    # way to tell "the model is confident" from "the model is guessing"
    # apart. Merged here so it's in the board everywhere from this point on.
    from klab.uncertainty import bootstrap_bands
    board = board.merge(bootstrap_bands().reset_index(), on="fg_id", how="left")

    board.to_csv(OUT / "keeper_board_2027.csv", index=False)
    board[board["keep_2027"]].to_csv(OUT / "optimal_keepers_2027.csv", index=False)

    from klab.board import value_players
    players, _, _ = value_players(exch)
    players.sort_values("roto_points", ascending=False).to_csv(
        OUT / "player_values_2027.csv", index=False)

    params = {
        "exchange_rate": exch,
        "save_model": fit_save_model(),
        "denominators_2027": meta["denominators"],
        "league_avg_team_2027": meta["baseline"],
        "replacement_rp": meta["replacement_rp"],
        "usd_per_rp_keep": meta["usd_per_rp_keep"],
        "usd_per_rp_redraft": meta["usd_per_rp_redraft"],
        "config": {k: v for k, v in vars(C).items()
                   if k.isupper() and isinstance(v, (int, float, str, list, dict))},
    }
    (OUT / "model_params.json").write_text(json.dumps(params, indent=2, default=str))

    import build_app
    build_app.main()

    print("wrote:", *sorted(p.name for p in OUT.glob("*")), sep="\n  ")
    return board, exch, meta


if __name__ == "__main__":
    main()
