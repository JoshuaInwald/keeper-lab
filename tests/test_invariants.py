"""Invariants that must hold, and that would have caught real bugs.

Every test here maps to a mistake actually made during development. They are
cheap (the whole file runs in a few seconds on a warm cache) and they are the
difference between "the numbers changed" and "the numbers broke".

    PYTHONPATH=. python3 -m pytest tests/ -q
"""
import numpy as np
import pandas as pd
import pytest

import klab.config as C
from klab.auction import match_drafts
from klab.board import build_board, fit_exchange_rate, keeper_status, value_players
from klab.denoms import teams_per_category
from klab.keeper import keeper_cost, years_controlled
from klab.trade import evaluate_trade, ros_value_over_replacement, standings_points
from klab.io import load_hitters_history, load_pitchers_history


@pytest.fixture(scope="module")
def board():
    b, exch, meta = build_board()
    return b, exch, meta


# --- the bug external review found -----------------------------------------

def test_budget_identity(board):
    """The 230 rostered players must clear exactly the league's cap.

    This failed silently for a whole build: values were calculated at
    full-time playing time against a scale calibrated on expected playing
    time, and the top 230 summed to $3,854 instead of $2,600.
    """
    _, _, meta = board
    assert meta["budget_check_top230"] == pytest.approx(C.N_TEAMS * C.BUDGET, rel=1e-6)


def test_replacement_agrees_with_auction_intercept(board):
    """Two unrelated routes to 'production you get for free' must agree.

    Replacement level is the 230th-best projection. The auction regression
    intercept is what $0 bought historically. Nothing forces them to match, so
    a large gap means one of the two chains is broken.
    """
    _, exch, meta = board
    assert abs(meta["replacement_rp"] - exch["intercept"]) < 1.5


# --- sign conventions -------------------------------------------------------

def test_standings_points_direction():
    """Biggest counting total earns the most points; lowest ERA/WHIP wins.

    An inverted rank here made every category backwards and put the league
    leader in last place. It was caught by a human noticing, not by the code.
    """
    wide = pd.DataFrame(
        {c: [1.0, 2.0, 3.0] for c in C.CATS}, index=["a", "b", "c"])
    pts = standings_points(wide)
    assert pts.loc["c", "HR"] > pts.loc["a", "HR"]      # more HR = more points
    assert pts.loc["a", "ERA"] > pts.loc["c", "ERA"]    # lower ERA = more points
    assert pts.loc["a", "WHIP"] > pts.loc["c", "WHIP"]


def test_denominators_positive_and_sane(board):
    _, _, meta = board
    D = meta["denominators"]
    assert set(D) == set(C.CATS)
    assert all(v > 0 for v in D.values())
    # 1 HR should buy more than 1 SB, and both far more than 1 R
    assert D["HR"] < D["SB"] < D["R"]


def test_saves_use_the_reduced_field_constant():
    """After punters are dropped the SV field is 8 teams, not 10.

    Using the 10-team range constant there overvalued every save by 19%.
    """
    n = teams_per_category()
    assert n["SV"] < C.N_TEAMS
    assert n["HR"] == C.N_TEAMS


# --- contract semantics -----------------------------------------------------

@pytest.mark.parametrize("code,years,cost", [
    ("1", 1, 20.0), ("2", 2, 20.0), ("3", 3, 20.0), ("F", 1, 25.0),
])
def test_contract_codes(code, years, cost):
    """The code is seasons remaining AFTER the current one; only F pays +$5.

    The original handoff had this backwards, which understated every
    multi-year contract by a season.
    """
    assert years_controlled(code) == years
    assert keeper_cost(20, code) == cost


def test_unknown_contract_is_charged_worst_case():
    assert keeper_cost(20, "?") == 25.0
    assert keeper_status("?") == "unknown"


# --- data integrity ---------------------------------------------------------

def test_board_has_no_duplicate_players(board):
    """Ohtani has two rows in the contracts file (batter and pitcher) sharing
    one FanGraphs id; a careless join put him on the board twice."""
    b, _, _ = board
    assert b["fg_id"].duplicated().sum() == 0


def test_only_real_two_way_players_are_tagged_two(board):
    """The FanGraphs hitter export carries a zero-PA row for every pitcher.
    Left in, it tagged every starter as a two-way player."""
    b, _, _ = board
    assert (b["role"] == "TWO").sum() <= 2
    assert (b["role"] == "PIT").sum() > 50


def test_name_matching_coverage():
    """671 of 677 auction purchases resolve. The 6 that don't are genuine
    zero-production buys (Bauer suspended, Painter/Buehler on TJ)."""
    d = match_drafts(verbose=False)
    assert d["fg_id"].notna().sum() >= 670
    assert len(d) == 677


def test_values_never_negative(board):
    """A player cannot be a negative asset -- a bad arm gets benched and the
    roster spot reverts to a waiver pickup."""
    b, _, _ = board
    assert (b["redraft_value"] >= 0).all()
    assert (b["keep_value"] >= 0).all()


def test_keeper_sets_respect_league_limits(board):
    b, _, _ = board
    counts = b[b["keep_2027"]].groupby("team").size()
    assert (counts >= C.MIN_KEEPERS).all()
    assert (counts <= C.MAX_KEEPERS).all()


def test_full_time_value_never_below_expected(board):
    """Scaling playing time up cannot make a player worth less."""
    b, _, _ = board
    assert (b["redraft_value_ft"] >= b["redraft_value"] - 1e-6).all()


# --- golden file: ten players across the value spectrum ---------------------
#
# Not exact equality -- the model is meant to change. These are loose bounds
# that encode domain knowledge, so a refactor that silently breaks the
# valuation fails here rather than in a trade discussion.

GOLDEN = [
    ("Shohei Ohtani",    50, 120),   # best player in the league, two-way
    ("Tarik Skubal",     35,  70),   # elite starter
    ("Paul Skenes",      25,  60),
    ("Mason Miller",     20,  60),   # elite closer
    ("Junior Caminero",  20,  50),
    ("Elly De La Cruz",  20,  50),
    ("Julio Rodríguez",  15,  40),
    ("Pete Alonso",      10,  35),
    ("Christian Scott",   0,  12),   # good rates, tiny sample
    ("Kevin Gausman",     0,  12),   # replacement level
]


@pytest.mark.parametrize("name,lo,hi", GOLDEN)
def test_golden_player_values(board, name, lo, hi):
    b, _, _ = board
    row = b[b["name"] == name]
    assert len(row) == 1, f"{name} not found exactly once"
    v = float(row["redraft_value"].iloc[0])
    assert lo <= v <= hi, f"{name} valued at ${v:.1f}, expected ${lo}-${hi}"


# --- free agents and the public API ----------------------------------------

def test_free_agents_carry_their_draft_contract():
    """A dropped player keeps his draft-year contract if re-added, so 2026
    buys have two years of control and 2025 buys have one."""
    from klab.freeagents import free_agent_board
    fa = free_agent_board()
    live = fa[fa["acquisition"] == "draft contract"]
    assert len(live) > 20
    for yr, yrs in [(2026, 2), (2025, 1)]:
        sub = live[live["draft_year"] == yr]
        if len(sub):
            assert (sub["years_controlled"] == yrs).all()
    # anything older has expired and reverts to the standard price
    stale = fa[fa["acquisition"] == "free agent price"]
    assert (stale["salary"] == C.FA_SALARY_POST_ASB).all()


def test_free_agents_are_not_on_rosters(board):
    from klab.freeagents import free_agent_board
    b, _, _ = board
    fa = free_agent_board()
    assert len(set(fa["fg_id"]) & set(b["fg_id"])) == 0


def test_free_agents_have_out_year_values():
    """Merging 2028 values off the rostered board silently zeroed every free
    agent's out year and understated multi-year surplus."""
    from klab.freeagents import free_agent_board
    fa = free_agent_board()
    live = fa[fa["acquisition"] == "draft contract"]
    assert (live["redraft_value_2028"] > 0).sum() > 5


def test_snapshot_is_self_consistent():
    from klab.api import snapshot
    s = snapshot()
    assert s.constants["budget_check_top230"] == pytest.approx(2600, rel=1e-6)
    assert 1.0 < s.constants["inflation"] < 3.0
    assert set(s.teams.index) == set(s.board["team"].unique())
    assert len(s.standings) == C.N_TEAMS


def test_multiyear_surplus_never_penalises_length():
    """A contract is an option: an extra year of control cannot make a player
    worth less than the same player with one year."""
    from klab.keeper import multiyear_surplus
    v27 = pd.Series([10.0, 10.0]); v28 = pd.Series([0.0, 0.0])
    cost = pd.Series([11.0, 11.0]); yrs = pd.Series([1, 2])
    out = multiyear_surplus(v27, v28, cost, yrs, pd.Series([11.0, 11.0]))
    assert out["surplus_multiyear"].iloc[1] >= out["surplus_multiyear"].iloc[0] - 1e-9


def test_category_sign_conventions_hold_every_season():
    """Across all five seasons, a bigger counting total must earn more
    standings points and a lower ERA/WHIP must too."""
    from klab.io import load_standings_long
    from scipy.stats import spearmanr
    st = load_standings_long()
    for y in st["season"].unique():
        w = st[st["season"] == y].pivot(index="team", columns="category", values="total")
        pts = standings_points(w[C.CATS])
        for cat in C.CATS:
            rho = spearmanr(w[cat], pts[cat]).statistic
            want = -1.0 if cat in C.NEG_CATS else 1.0
            assert abs(rho - want) < 0.01, f"{y} {cat}: rho={rho}"


def test_final_year_player_can_buy_two_extension_years():
    """Tests multiyear_surplus()'s raw math in isolation: IF an F player's
    extension were live, a 2028 line clearing the extra $5 must be valued at
    two years, not one. As of out/FINDINGS.md #39 this computation is never
    actually applied on the real board -- klab.board.build_board marks every
    F player unkeepable unconditionally, because the real extension window
    closes before that player's own walk-year draft, not now. Kept as a math
    check on the function itself; see
    test_f_contract_players_are_never_keepable for the board-level behavior
    that actually ships."""
    from klab.keeper import multiyear_surplus
    # Cheap star: $16 salary, worth $72 in 2027 and $62 in 2028.
    v27, v28 = pd.Series([72.0]), pd.Series([62.0])
    sal = pd.Series([16.0])
    cost = sal + C.EXTENSION_COST          # keeper_cost for an `F` contract
    out = multiyear_surplus(v27, v28, cost, pd.Series([1]), sal)
    one_year = float(v27.iloc[0] - cost.iloc[0])
    two_year = float((v27.iloc[0] - (sal.iloc[0] + 10))
                     + (v28.iloc[0] - (sal.iloc[0] + 10)) * C.FUTURE_YEAR_DISCOUNT)
    assert out["extension_years"].iloc[0] == 2
    assert out["surplus_multiyear"].iloc[0] == pytest.approx(two_year)
    assert out["surplus_multiyear"].iloc[0] > one_year

    # ...and a player whose 2028 line does NOT clear it stays at one year.
    out2 = multiyear_surplus(v27, pd.Series([18.0]), cost, pd.Series([1]), sal)
    assert out2["extension_years"].iloc[0] == 1
    assert out2["extension_option"].iloc[0] == pytest.approx(0.0)
    assert out2["surplus_multiyear"].iloc[0] == pytest.approx(one_year)


def test_extension_years_is_zero_where_the_option_is_worthless():
    """A live contract whose extension is not worth exercising reports 0 years,
    so the board never advises paying $5 for nothing."""
    from klab.keeper import multiyear_surplus
    sal = pd.Series([30.0])
    out = multiyear_surplus(pd.Series([20.0]), pd.Series([5.0]), sal,
                            pd.Series([2]), sal)
    assert out["extension_years"].iloc[0] == 0
    assert out["extension_option"].iloc[0] == pytest.approx(0.0)


def test_extension_only_eligible_with_one_year_of_control_left():
    """The constitution's only extension clause is for a player 'about to
    enter the final year of his contract eligibility' -- code 1, one year of
    control left. Codes 2 and 3 still have guaranteed seasons before that's
    live, and must report zero extension option regardless of how good the
    2028 line is (out/FINDINGS.md #33 -- 9 players carried a phantom
    extension option here before this was fixed)."""
    from klab.keeper import multiyear_surplus
    sal = pd.Series([10.0, 10.0, 10.0])
    v27 = pd.Series([30.0, 30.0, 30.0])
    v28 = pd.Series([40.0, 40.0, 40.0])          # clearly clears any extension cost
    years = pd.Series([1, 2, 3])
    out = multiyear_surplus(v27, v28, sal, years, sal)
    assert out["extension_option"].iloc[0] > 0, "code 1 should be extension-eligible"
    assert out["extension_option"].iloc[1] == pytest.approx(0.0), "code 2 is not eligible yet"
    assert out["extension_option"].iloc[2] == pytest.approx(0.0), "code 3 is not eligible yet"
    assert out["extension_years"].iloc[1] == 0
    assert out["extension_years"].iloc[2] == 0


def test_app_payload_has_no_column_collisions_and_no_nans():
    """The exported payload is what the browser sees. A silent column collision
    (ros PA vs projected PA) shipped a null into the player card once."""
    import sys
    sys.path.insert(0, str(C.DATA.parent / "scripts"))
    from build_app import build_payload, PLAYER_COLS
    p = build_payload()
    assert len(p["cols"]) == len(set(p["cols"])), "duplicate column in payload"
    ix = {c: i for i, c in enumerate(p["cols"])}
    for col in ["PA", "AB", "IP", "redraft_value", "keeper_cost", "surplus_multiyear"]:
        assert col in ix
    ohtani = [r for r in p["board"] if r[ix["name"]] == "Shohei Ohtani"]
    assert len(ohtani) == 1 and ohtani[0][ix["PA"]] > 0
    # every rostered row must carry the fields the UI dereferences
    for r in p["board"]:
        for col in ["name", "team", "role", "salary", "keeper_cost", "redraft_value"]:
            assert r[ix[col]] is not None, f"{r[ix['name']]} missing {col}"
    assert set(p["cur_totals"]) == set(t["team"] for t in p["teams"])


def test_reliability_weights_match_a_fresh_refit():
    """klab.project.RELIABILITY is a hard-coded fit, not something recomputed
    at runtime. It quietly drifted: BB and H were both set to WHIP's r=0.237
    (WHIP is never looked up through rel_weight -- it's inert -- so this was
    a copy-paste into the two keys that ARE live), rather than their own
    correlations. Refitting directly gave BB=0.463, H=0.359. This test
    reruns the same fit the dict is supposed to represent and would have
    caught that a value in the dict came from the wrong stat."""
    from klab.project import RELIABILITY

    def yoy_r(df, id_col, pt_col, pt_min, num_a, num_b, denom_a, denom_b, pairs):
        frames = []
        for a, b in pairs:
            ta = df[(df["season"] == a) & (df[pt_col] >= pt_min)]
            tb = df[(df["season"] == b) & (df[pt_col] >= pt_min)]
            m = ta.merge(tb, on=id_col, suffixes=("_a", "_b"))
            ra = m[num_a] / m[denom_a]
            rb = m[num_b] / m[denom_b]
            frames.append(pd.DataFrame({"a": ra, "b": rb}))
        p = pd.concat(frames, ignore_index=True).dropna()
        return float(np.corrcoef(p["a"], p["b"])[0, 1])

    pairs = [(2022, 2023), (2023, 2024), (2024, 2025)]
    hit = load_hitters_history()
    pit = load_pitchers_history()

    refit = {}
    for stat in ["HR", "R", "RBI", "SB"]:
        refit[stat] = yoy_r(hit, "fg_id", "PA", 250,
                            f"{stat}_a", f"{stat}_b", "PA_a", "PA_b", pairs)
    refit["AVG"] = yoy_r(hit, "fg_id", "PA", 250, "H_a", "H_b", "AB_a", "AB_b", pairs)
    for stat in ["W", "K", "ER", "BB", "H"]:
        refit[stat] = yoy_r(pit, "fg_id", "IP", 40,
                            f"{stat}_a", f"{stat}_b", "IP_a", "IP_b", pairs)

    for stat, r in refit.items():
        assert abs(RELIABILITY[stat] - r) < 0.03, (
            f"RELIABILITY[{stat!r}]={RELIABILITY[stat]} but a fresh refit on "
            f"the same season pairs gives {r:.3f} -- the hard-coded dict has "
            f"drifted from the fit it's supposed to represent")


# --- evaluate_trade: had zero coverage until out/FINDINGS.md #32.1 --------

def test_evaluate_trade_requires_usd_per_point(board):
    """usd_per_point used to default to a hardcoded, silently-stale 7.6 that
    every real caller forgot to override (out/FINDINGS.md #32.1). It's now a
    required argument specifically so a caller who forgets it fails loudly,
    at call time, instead of shipping a quietly-wrong verdict_score."""
    b, exch, meta = board
    teams = b["team"].unique()
    a_name = b[b["team"] == teams[0]]["name"].iloc[0]
    b_name = b[b["team"] == teams[1]]["name"].iloc[0]
    with pytest.raises(TypeError):
        evaluate_trade(b, teams[0], teams[1], [a_name], [b_name])


def test_evaluate_trade_verdict_responds_to_usd_per_point(board):
    """The win-now term is contention_weight * delta_points * usd_per_point.
    If usd_per_point weren't actually wired through, verdict_score wouldn't
    move when it changes -- which is exactly the bug #32.1 found (the JS side
    was live-wired to the wrong constant, not a dead one, so this alone
    wouldn't have caught that specific mistake, but it does guard against the
    parameter being ignored entirely)."""
    b, exch, meta = board
    teams = b["team"].unique()
    a_name = b[b["team"] == teams[0]]["name"].iloc[0]
    b_name = b[b["team"] == teams[1]]["name"].iloc[0]
    low = evaluate_trade(b, teams[0], teams[1], [a_name], [b_name], usd_per_point=1.0)
    high = evaluate_trade(b, teams[0], teams[1], [a_name], [b_name], usd_per_point=100.0)
    if abs(low["a"]["d_standings_points_2026"]) > 0.01:
        assert low["a"]["verdict_score"] != pytest.approx(high["a"]["verdict_score"])


# --- ros_value_over_replacement: rest-of-season value, not a full year ----

def test_ros_value_over_replacement_scales_with_remaining_playing_time():
    """A player projected for twice the remaining PA of an otherwise-identical
    player should be worth roughly twice the counting-stat roto points, and
    the replacement baseline he's compared against should scale the same way
    -- the whole point of this metric is that it's a fair per-player
    comparison regardless of how much season each individually has left."""
    from klab.board import build_2027_scorer
    scorer, D, base, sigma = build_2027_scorer()

    def make(pa_frac):
        pa = C.KEEPER_PA_FLOOR * pa_frac
        return pd.DataFrame([{
            "fg_id": 1, "role": "HIT", "PA": pa, "AB": pa * 0.9,
            "H": pa * 0.9 * 0.27, "HR": pa * 0.04, "R": pa * 0.13,
            "RBI": pa * 0.13, "SB": pa * 0.02,
            "IP": 0.0, "W": 0.0, "SV": 0.0, "K": 0.0, "ER": 0.0, "BB": 0.0,
            "H_allowed": 0.0,
        }])

    half = ros_value_over_replacement(make(0.5), D, base, 4.78)
    full = ros_value_over_replacement(make(1.0), D, base, 4.78)
    assert half["remaining_frac"].iloc[0] == pytest.approx(0.5, abs=0.01)
    assert full["remaining_frac"].iloc[0] == pytest.approx(1.0, abs=0.01)
    # same per-PA rate, half the PA -> roughly half the value over replacement
    ratio = half["ros_value_over_replacement"].iloc[0] / full["ros_value_over_replacement"].iloc[0]
    assert 0.4 < ratio < 0.6


def test_ros_value_over_replacement_ranks_better_rates_higher():
    """Holding remaining playing time equal, a better rate line must score
    higher -- the specific thing this metric exists to compare across
    players with different amounts of season left is not supposed to also
    scramble the ranking of players with the SAME amount left."""
    from klab.board import build_2027_scorer
    scorer, D, base, sigma = build_2027_scorer()
    pa = C.KEEPER_PA_FLOOR * 0.3

    good = pd.DataFrame([{
        "fg_id": 1, "role": "HIT", "PA": pa, "AB": pa * 0.9,
        "H": pa * 0.9 * 0.31, "HR": pa * 0.06, "R": pa * 0.16, "RBI": pa * 0.16,
        "SB": pa * 0.03, "IP": 0.0, "W": 0.0, "SV": 0.0, "K": 0.0, "ER": 0.0,
        "BB": 0.0, "H_allowed": 0.0,
    }])
    bad = good.copy()
    bad[["H", "HR", "R", "RBI", "SB"]] *= 0.5

    g = ros_value_over_replacement(good, D, base, 4.78)
    b = ros_value_over_replacement(bad, D, base, 4.78)
    assert g["ros_value_over_replacement"].iloc[0] > b["ros_value_over_replacement"].iloc[0]


def test_f_contract_players_are_never_keepable(board):
    """out/FINDINGS.md #39: the extension window closes before a player's OWN
    walk-year draft, not now -- so any player observed as F in
    contracts_parsed.csv already missed it and is confirmed for free agency,
    regardless of whether he's ever used a prior extension or how good his
    projection is. keepable must be False, extension_option/surplus_multiyear
    must be exactly 0, and he must never be flagged keep_2027, for EVERY F
    player on the board -- not just the ones already_extended() catches."""
    b, _, _ = board
    f_players = b[b["contract"].astype(str).str.upper() == "F"]
    assert len(f_players) > 0, "test needs at least one F-contract player to exist"
    assert not f_players["keepable"].any()
    assert not f_players["keep_2027"].any()
    assert (f_players["extension_option"] == 0).all()
    assert (f_players["surplus_multiyear"] == 0).all()


def test_f_contract_status_label_does_not_claim_an_extension_exists(board):
    """Real bug, caught in a 2026-08-13 UI audit, not by any prior test:
    board.py's `keepable` logic was fixed for #39, but `keeper_status()`
    (klab/board.py) still returned the literal string "extension +$5" for
    every F-contract player -- exactly the pre-#39 claim the rest of the
    board had already stopped believing. Anyone reading the app's player
    card (which displays this string directly) would see a live extension
    price next to a player the model had already zeroed out. See
    out/FINDINGS.md #44."""
    b, _, _ = board
    f_players = b[b["contract"].astype(str).str.upper() == "F"]
    assert len(f_players) > 0, "test needs at least one F-contract player to exist"
    assert not f_players["keeper_status"].str.contains(r"\$", regex=True).any()
    assert f_players["keeper_status"].eq("free agent after 2026 (not extendable)").all()
