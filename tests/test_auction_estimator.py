"""Tests for klab/auction_estimator.py -- a separate exercise from the rest
of the model (see the module docstring). Kept in its own file on purpose,
mirroring that separation.

    PYTHONPATH=. python3 -m pytest tests/test_auction_estimator.py -q
"""
import numpy as np
import pandas as pd
import pytest

from klab.auction_estimator import (comp_pool, estimate_auction_price,
                                    find_comps, position_group)


@pytest.fixture(scope="module")
def players():
    board = pd.read_csv("out/keeper_board_2027.csv")
    p = pd.read_csv("out/player_values_2027.csv")
    names = board.set_index("fg_id")["name"]
    roles = board.set_index("fg_id")["role"]
    p = p.copy()
    p["name"] = p["fg_id"].map(names)
    p["role"] = p["fg_id"].map(roles)
    return p.dropna(subset=["name", "role"])


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
