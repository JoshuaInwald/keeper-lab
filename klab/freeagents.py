"""The free-agent pool, priced as keeper assets.

A player who was drafted and later dropped keeps his draft-year contract if
re-added. That makes the waiver wire an inventory of *priced* assets, not just
loose talent: Justin Crawford went for $1 in the 2026 auction, so re-adding
him buys a $1 salary with two years of control, exactly as if he had never
been dropped.

Contract years follow the same rule as the roster (see config): a 2026 draft
buy has 2027 and 2028 left, a 2025 buy has 2027 only, and anything bought in
2024 or earlier has expired and reverts to the standard free-agent price.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .io import cached
from .keeper import keeper_cost, multiyear_surplus, years_controlled

# Draft year -> contract code, from the perspective of the 2027 keeper
# decision. Anything older than this has run out.
DRAFT_YEAR_TO_CODE = {2026: "2", 2025: "1"}


@cached
def free_agent_board() -> pd.DataFrame:
    """Every unrostered player, with the contract he would carry if re-added."""
    from .auction import match_drafts
    from .board import build_board, fit_exchange_rate, value_players

    board, exch, meta = build_board()
    players, _, _ = value_players(exch)
    rostered = set(board["fg_id"])

    fa = players[~players["fg_id"].isin(rostered)].copy()

    # most recent auction price for each player, which is the contract he
    # would resume on re-acquisition
    d = match_drafts(verbose=False).dropna(subset=["fg_id"]).copy()
    d["fg_id"] = d["fg_id"].astype(int)
    last = (d.sort_values("season")
              .groupby("fg_id")
              .agg(draft_year=("season", "last"), draft_salary=("salary", "last")))
    fa = fa.merge(last, on="fg_id", how="left")

    fa["contract"] = fa["draft_year"].map(DRAFT_YEAR_TO_CODE)
    has_contract = fa["contract"].notna()

    # No live contract -> the league's standard acquisition price. Post-break
    # is the conservative assumption for a player added from here on.
    fa["acquisition"] = np.where(has_contract, "draft contract", "free agent price")
    fa["salary"] = np.where(has_contract, fa["draft_salary"], C.FA_SALARY_POST_ASB)
    fa["contract"] = fa["contract"].fillna("1")

    fa["keeper_cost"] = [keeper_cost(s, c) for s, c in zip(fa["salary"], fa["contract"])]
    fa["years_controlled"] = fa["contract"].map(years_controlled)

    # 2028 values must come from the full projection, not from the rostered
    # board -- a free agent is by definition absent from it, so merging there
    # silently zeroed every out-year value and understated multi-year surplus.
    from .board import value_2028
    sv27 = players.set_index("fg_id")["SV"] if "SV" in players else None
    v28 = value_2028(exch, meta, sv27)[["fg_id", "redraft_value_2028"]]
    fa = fa.merge(v28, on="fg_id", how="left")
    fa["redraft_value_2028"] = fa["redraft_value_2028"].fillna(0.0)

    my = multiyear_surplus(fa["redraft_value"], fa["redraft_value_2028"],
                           fa["keeper_cost"], fa["years_controlled"], fa["salary"])
    fa = pd.concat([fa.reset_index(drop=True), my.reset_index(drop=True)], axis=1)
    fa["surplus_redraft"] = fa["redraft_value"] - fa["keeper_cost"]
    return fa.sort_values("surplus_multiyear", ascending=False)
