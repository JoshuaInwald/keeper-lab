"""Tests for klab/auction_estimator.py -- a separate exercise from the rest
of the model (see the module docstring). Kept in its own file on purpose,
mirroring that separation.

    PYTHONPATH=. python3 -m pytest tests/test_auction_estimator.py -q
"""
import numpy as np
import pandas as pd
import pytest

from klab.auction_estimator import (comp_pool, estimate_auction_price,
                                    find_comps, player_tenure, position_group)


@pytest.fixture(scope="module")
def players():
    """`player_values_2027.csv` restricted to rostered (fg_id, role) pairs.

    An inner merge on (fg_id, role), not a fg_id-keyed .map() -- a true
    two-way player (config.TWO_WAY_SPLIT_NAMES) has two rows sharing one
    fg_id from 2027 on (see klab.board.project_all_players), and
    `board.set_index("fg_id")` used to break outright here with a
    duplicate-index error. `p` already carries its own name/role columns,
    so this only needs to filter to rostered pairs, not re-attach them.
    """
    board = pd.read_csv("out/keeper_board_2027.csv")
    p = pd.read_csv("out/player_values_2027.csv")
    rostered = board[["fg_id", "role"]].drop_duplicates()
    return p.merge(rostered, on=["fg_id", "role"], how="inner")


def test_position_group_covers_every_real_value():
    """Every non-null pos value actually in the comp pool must map to a
    known group -- an unmapped position silently falling into 'UNKNOWN'
    would quietly shrink that position's comp pool without anyone noticing."""
    pool = pd.read_csv("out/auction_sample.csv")
    real_positions = pool["pos"].dropna().unique()
    for pos in real_positions:
        assert position_group(pos) != "UNKNOWN", f"'{pos}' has no group mapping"


def test_premium_is_recentered_to_zero_median_per_season():
    """The whole point of the recentering step: comparing a player against
    'what similar comps paid relative to a biased regression line' would be
    meaningless. Each season's premium must median to exactly 0."""
    pool = comp_pool()
    medians = pool.groupby("season")["premium_frac"].median()
    assert (medians.abs() < 1e-9).all()


def test_estimate_runs_for_a_real_hitter_and_pitcher(players):
    for name in ["Freddie Freeman", "Tarik Skubal"]:
        res = estimate_auction_price(name, players, k=15)
        assert res["n_comps"] == 15
        assert res["comp_adjusted_low"] <= res["comp_adjusted_mid"] <= res["comp_adjusted_high"]
        assert res["comp_adjusted_low"] >= 1.0, "auction floor is $1"
        assert len(res["comps"]) == 15


def test_a_below_replacement_player_floors_at_one_dollar(players):
    """A player whose regression fair value is already $0 (clipped) must not
    somehow come back with a comp-adjusted estimate below the league's own
    $1 minimum bid -- that's not a real price anyone could actually pay."""
    weak = players[players["roto_points"] < 1.0]
    assert len(weak) > 0, "test needs at least one below-replacement player to exist"
    res = estimate_auction_price(weak.iloc[0]["name"], players, k=15)
    assert res["comp_adjusted_low"] >= 1.0


def test_estimate_disambiguates_a_two_way_players_two_rows(players):
    """Ohtani (config.TWO_WAY_SPLIT_NAMES) has two rows sharing one name and
    fg_id from 2027 on. Passing `role` must resolve each independently --
    not silently return the same row's estimate for both."""
    oht = players[players["name"] == "Shohei Ohtani"]
    assert set(oht["role"]) == {"HIT", "PIT"}, "test needs both of his rows present"
    hit = estimate_auction_price("Shohei Ohtani", players, k=15, role="HIT")
    pit = estimate_auction_price("Shohei Ohtani", players, k=15, role="PIT")
    # position_map() is keyed by fg_id alone (a real, pre-existing gap --
    # not something this test introduces or this fix needs to solve), so
    # both rows resolve to his historical roster position ("U"/UTIL)
    # regardless of role. What has to actually differ is which comps get
    # compared against -- role filters the comp pool before position does.
    assert hit["role"] == "HIT" and pit["role"] == "PIT"
    assert hit["regression_fair_value"] != pit["regression_fair_value"]
    pitcher_pos = {"SP", "RP", "P"}
    assert set(pit["comps"]["pos"].dropna()) <= pitcher_pos
    assert not (set(hit["comps"]["pos"].dropna()) & pitcher_pos)


def test_appearances_to_date_counts_prior_sales_only():
    """0 on a player's own first-ever sale in the sample; must never count
    a LATER sale of the same player (that would leak future information
    into a comp used to price him)."""
    pool = comp_pool()
    repeat = pool[pool.duplicated("fg_id", keep=False)]
    assert len(repeat) > 0, "test needs a real repeat-sale player to exist"
    fid = repeat["fg_id"].iloc[0]
    his = pool[pool["fg_id"] == fid].sort_values("season")
    assert his["appearances_to_date"].tolist() == list(range(len(his)))


def test_player_tenure_zero_for_a_never_sold_player():
    """A fg_id that never appears in the sample has never been bought here
    -- his next sale would be his first, tenure 0."""
    pool = comp_pool()
    never_sold = -999999
    assert never_sold not in set(pool["fg_id"])
    assert player_tenure(never_sold) == 0


def test_first_timer_filtering_only_ever_uses_other_first_timers():
    """When find_comps actually engages the tenure filter (enough
    first-timer comps to fill k), every comp returned must itself be a
    first-timer -- a target with no track record shouldn't get priced off
    an established veteran's identical-looking season."""
    pool = comp_pool()
    target = pool[(pool["role"] == "PIT") & (pool["appearances_to_date"] == 0)].iloc[0]
    comps = find_comps(target, "PIT", "SP", k=10, target_is_first_timer=True)
    if comps.attrs["tenure_filtered"]:
        assert (comps["appearances_to_date"] == 0).all()


def test_find_comps_falls_back_when_position_pool_is_thin():
    """A synthetic position with (deliberately) zero real comps must trigger
    the full-role fallback rather than returning garbage from an empty
    slice."""
    pool = comp_pool()
    target = pool[pool["role"] == "HIT"].iloc[0]
    comps = find_comps(target, "HIT", "NO_SUCH_POSITION_GROUP", k=15)
    assert comps.attrs["fallback_to_full_role"] is True
    assert comps.attrs["n_same_position"] == 0
    assert len(comps) == 15
