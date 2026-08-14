"""Tests for klab/trade_finder.py -- kept in its own file, mirroring the
module's separation from the rest of the model.

    PYTHONPATH=. python3 -m pytest tests/test_trade_finder.py -q
"""
import pandas as pd
import pytest

import klab.config as C
from klab.board import build_board
from klab.io import load_standings_long
from klab.trade import standings_points
from klab.trade_finder import _shortlist, suggest_trades


@pytest.fixture(scope="module")
def board_and_pts():
    board, exch, meta = build_board()
    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category", values="total")
    pts = standings_points(cur[C.CATS])["TOTAL"].to_dict()
    return board, exch, pts


def test_shortlist_includes_value_players_not_just_talent(board_and_pts):
    """Real bug found building this: a team can have most of its top-talent
    players be unkeepable F-contract rentals, which crowds out the actual
    trade chips (positive-surplus keepers) a shortlist-by-roto_points-alone
    would need for Scenario 1 to find anything. The union with top-surplus
    must recover them."""
    board, _, _ = board_and_pts
    sl = _shortlist(board, "Spehr's Army")
    t = board[board["team"] == "Spehr's Army"]
    best_keeper = t.nlargest(1, "surplus_multiyear")["name"].iloc[0]
    assert best_keeper in sl


def test_suggest_trades_returns_all_three_keys(board_and_pts):
    board, exch, pts = board_and_pts
    res = suggest_trades(board, exch, "NPB No Stars", "Spehr's Army", pts)
    assert set(res.keys()) == {"team_a", "team_b", "win_now_for_future",
                               "challenge_trade", "mutual_value_swap"}


def test_win_now_scenario_never_offers_a_worthless_return(board_and_pts):
    """The exact bug found and fixed while building this: a candidate used
    to score positive purely because the OUTGOING piece was such a bad
    contract that anything looked like an upgrade, even a $0-surplus
    unkeepable throwaway coming back. The player returning to the seller
    must have positive standalone surplus_multiyear."""
    board, exch, pts = board_and_pts
    surplus = board.set_index("name")["surplus_multiyear"]
    checked = 0
    for team_a, team_b in [("NPB No Stars", "Spehr's Army"), ("All-Stars", "McBlocks"),
                           ("Producers", "Pookie 2.0")]:
        res = suggest_trades(board, exch, team_a, team_b, pts)
        wn = res["win_now_for_future"]
        if wn is None:
            continue
        checked += 1
        incoming_to_seller = wn["b_sends"] if wn["seller"] == team_a else wn["a_sends"]
        assert surplus.get(incoming_to_seller, 0.0) > 0
    assert checked > 0, "test needs at least one pair with a found win_now trade"


def test_shortlist_is_sorted(board_and_pts):
    """Real bug: _shortlist used to return list(set_a | set_b) -- a set's
    iteration order is randomised per Python process (string hash seeding),
    so an identical board produced a different "best" trade on every rerun
    in a fresh process whenever two candidates tied on a scenario's primary
    score, which is common (many candidates move one side's standings by
    the exact same amount). A single process reuses one hash seed for its
    whole lifetime, so this couldn't be caught by comparing two in-process
    calls -- it only showed up rerunning `scripts/build_trade_suggestions.py`
    end to end with unchanged data and diffing the output. Fixed by sorting
    the shortlist and adding a real secondary tie-break (sum of both deltas)
    to the scenario pickers. See out/FINDINGS.md #41."""
    board, _, _ = board_and_pts
    sl = _shortlist(board, "Pookie 2.0")
    assert sl == sorted(sl)


def test_challenge_picks_pareto_better_candidate_on_a_tie():
    """Two candidates tie on min(a_delta, b_delta) -- the primary score --
    but one is strictly better for team_a. The sum-based tie-break must
    prefer it, not whichever the caller happened to list first."""
    from klab.trade_finder import _pick_challenge
    worse = {"a_sends": "Worse", "b_sends": "Same",
             "a_standings_delta": 3.5, "b_standings_delta": 1.5}
    better = {"a_sends": "Better", "b_sends": "Same",
              "a_standings_delta": 5.5, "b_standings_delta": 1.5}
    assert _pick_challenge([worse, better], "A", "B")["a_sends"] == "Better"
    assert _pick_challenge([better, worse], "A", "B")["a_sends"] == "Better"


def test_challenge_and_mutual_value_never_favor_only_one_side():
    """Both scenarios are explicitly mutual -- if a candidate is returned,
    BOTH sides' relevant delta must be positive, not just the max of the two."""
    board, exch, meta = build_board()
    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category", values="total")
    pts = standings_points(cur[C.CATS])["TOTAL"].to_dict()
    found_any = {"challenge_trade": False, "mutual_value_swap": False}
    for team_a, team_b in [("NPB No Stars", "Spehr's Army"), ("All-Stars", "Lisbon Long Balls"),
                           ("McBlocks", "The Fighting Phils")]:
        res = suggest_trades(board, exch, team_a, team_b, pts)
        ct = res["challenge_trade"]
        if ct:
            found_any["challenge_trade"] = True
            assert ct["a_standings_gain"] > 0 and ct["b_standings_gain"] > 0
        mv = res["mutual_value_swap"]
        if mv:
            found_any["mutual_value_swap"] = True
            assert mv["a_surplus_gain"] > 0 and mv["b_surplus_gain"] > 0
    assert any(found_any.values()), "test needs at least one scenario to be found somewhere"
