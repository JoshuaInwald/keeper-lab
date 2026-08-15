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
from klab.project import _blend_weight
from klab.standings_sim import simulate_finish_odds


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
    """A careless join could put a normal player on the board twice.

    The one INTENDED exception: a true two-way player
    (config.TWO_WAY_SPLIT_NAMES, e.g. Ohtani) legitimately has two rows
    sharing one fg_id from 2027 on -- hitter and pitcher, priced as
    separate auction assets (klab.board.project_all_players). Duplicated
    (fg_id, role) pairs, or a duplicated fg_id for anyone NOT in that set,
    are still the real bug this test exists to catch."""
    b, _, _ = board
    assert b.duplicated(["fg_id", "role"]).sum() == 0
    dup_fg_id = b[b["fg_id"].duplicated(keep=False)]
    assert set(dup_fg_id["name"].unique()) <= C.TWO_WAY_SPLIT_NAMES


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
    # Ohtani prices as two separate 2027 auction assets from
    # config.TWO_WAY_SPLIT_NAMES on -- one golden entry per role, not the
    # old single combined-$78 figure. Bounds are loose, same philosophy as
    # every other row here, not pinned to today's exact $49.98 / $0.00.
    ("Shohei Ohtani", "HIT", 30, 70),    # hitter side alone
    ("Shohei Ohtani", "PIT",  0, 30),    # pitcher side: cautious 2027 IP ramp
    ("Tarik Skubal",  None, 35,  70),   # elite starter
    ("Paul Skenes",   None, 25,  60),
    ("Mason Miller",  None, 20,  60),   # elite closer
    ("Junior Caminero", None, 20,  50),
    ("Elly De La Cruz", None, 20,  50),
    ("Julio Rodríguez", None, 15,  40),
    ("Pete Alonso",   None, 10,  35),
    ("Christian Scott", None, 0,  12),   # good rates, tiny sample
    ("Kevin Gausman", None,  0,  12),   # replacement level
]


@pytest.mark.parametrize("name,role,lo,hi", GOLDEN)
def test_golden_player_values(board, name, role, lo, hi):
    b, _, _ = board
    row = b[b["name"] == name]
    if role is not None:
        row = row[row["role"] == role]
    assert len(row) == 1, f"{name}{' ' + role if role else ''} not found exactly once"
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
    # Two rows from 2027 on -- hitter and pitcher, priced as separate
    # auction assets (config.TWO_WAY_SPLIT_NAMES). The PA>0 check belongs
    # on his hitter row specifically; his pitcher row has PA==0 by
    # construction, same as any other pitcher.
    ohtani = [r for r in p["board"] if r[ix["name"]] == "Shohei Ohtani"]
    assert {r[ix["role"]] for r in ohtani} == {"HIT", "PIT"}
    hit_row = next(r for r in ohtani if r[ix["role"]] == "HIT")
    assert hit_row[ix["PA"]] > 0
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


# --- ros_lines_for_basis: blended 2026 rest-of-season signal (FINDINGS #45) -

def test_prorated_to_date_lines_matches_ros_lines_schema():
    """Must be a drop-in alternative to ros_lines() -- same columns, since
    win_now_delta() and ros_value_over_replacement() both consume whichever
    one ros_lines_for_basis() hands back without knowing which it got."""
    from klab.trade import prorated_to_date_lines, ros_lines
    p = prorated_to_date_lines()
    r = ros_lines()
    assert set(p.columns) == set(r.columns)
    assert (p.drop(columns="fg_id") >= 0).all().all(), "prorated counting stats must be non-negative"


def test_prorated_to_date_lines_remaining_games_is_plausible():
    """Mid-season, this should land somewhere between 'season just started'
    and 'season is over' -- a wildly out-of-range value would mean the
    games-played percentile estimate broke, not that the season did."""
    from klab.trade import prorated_to_date_lines
    p = prorated_to_date_lines()
    assert 0.0 < p.attrs["remaining_games"] < C.SEASON_GAMES


def test_prorated_to_date_lines_does_not_inflate_a_starters_innings():
    """Real bug, caught before shipping (out/LAB_NOTEBOOK.md #24): dividing
    a starting pitcher's to-date innings by his own G (which counts STARTS,
    not team games) and multiplying by team games remaining projected Tarik
    Skubal for 256 more innings. No individual pitcher's remaining-innings
    projection should ever exceed a full season's IP -- the specific,
    per-player sanity check the original bug would have failed and the
    aggregate "non-negative" / "plausible total remaining games" checks did
    not catch."""
    from klab.io import load_pitchers_history
    from klab.trade import prorated_to_date_lines
    p26 = load_pitchers_history().query("season == 2026")
    starters = p26[(p26["GS"] > 10) & (p26["IP"] > 50)]
    assert len(starters) > 0, "test needs at least one qualifying starter"
    prorated = prorated_to_date_lines().set_index("fg_id")
    for fid in starters["fg_id"]:
        if fid in prorated.index:
            assert prorated.loc[fid, "IP"] < C.SEASON_GAMES, \
                f"fg_id {fid} projected for an implausible {prorated.loc[fid, 'IP']:.0f} more innings"


def test_ros_lines_for_basis_blend_is_the_average_of_its_two_inputs():
    from klab.trade import ros_lines_for_basis, ros_lines, prorated_to_date_lines
    blend = ros_lines_for_basis("blend").set_index("fg_id")
    a = ros_lines().set_index("fg_id")
    b = prorated_to_date_lines().set_index("fg_id")
    # pick a player present in both source tables
    common = a.index.intersection(b.index)
    assert len(common) > 0, "test needs at least one player in both ROS sources"
    fid = common[0]
    for col in ["PA", "IP"]:
        expected = (a.loc[fid, col] + b.loc[fid, col]) / 2.0
        assert blend.loc[fid, col] == pytest.approx(expected, abs=1e-6)


def test_ros_lines_for_basis_rejects_unknown_basis():
    from klab.trade import ros_lines_for_basis
    with pytest.raises(ValueError):
        ros_lines_for_basis("preseason")


def test_evaluate_trade_ros_basis_changes_win_now_numbers(board):
    """Not just 'doesn't crash' -- the win-now standings delta must actually
    respond to ros_basis, or the parameter is decorative."""
    b, exch, meta = board
    teams = b["team"].unique()
    t = b[b["team"] == teams[0]]
    other = b[b["team"] == teams[1]]
    a_name = t.nlargest(1, "roto_points")["name"].iloc[0]
    b_name = other.nlargest(1, "roto_points")["name"].iloc[0]
    r1 = evaluate_trade(b, teams[0], teams[1], [a_name], [b_name],
                        usd_per_point=100.0, ros_basis="ros")
    r2 = evaluate_trade(b, teams[0], teams[1], [a_name], [b_name],
                        usd_per_point=100.0, ros_basis="blend")
    # the two ROS signals are different data, so at least one side's win-now
    # points should differ between bases for a randomly-picked real trade
    assert (r1["a"]["d_standings_points_2026"] != pytest.approx(r2["a"]["d_standings_points_2026"])
           or r1["b"]["d_standings_points_2026"] != pytest.approx(r2["b"]["d_standings_points_2026"]))


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


# --- playing-time / rate decoupling (out/FINDINGS.md #51) -------------------

def test_playing_time_weight_capped_lower_than_rate_weight_for_pitchers():
    """The whole point of the fix: for the same 2026 innings sample, the
    PLAYING TIME weight must be capped well below the RATE weight for
    pitchers specifically -- that gap is what stops a shortened,
    injury-affected season from docking a healthy pitcher's projected 2027
    innings the way it silently did for Hunter Brown before this fix."""
    ip_a = pd.Series([200.0])   # a large sample, so both weights hit their cap
    rate_w = _blend_weight(ip_a, 70.0, cap=C.BLEND_W_2026)
    pt_w = _blend_weight(ip_a, 70.0, cap=C.PT_BLEND_CAP_PITCHER)
    assert pt_w.iloc[0] < rate_w.iloc[0]
    assert pt_w.iloc[0] == pytest.approx(C.PT_BLEND_CAP_PITCHER)


def test_pitcher_playing_time_cap_is_lower_than_hitter_cap():
    """Josh's explicit reasoning: a shortened pitcher-season skews
    injury-driven (expected to be fine next year); a shortened hitter
    season is more often role/platoon-driven, which IS informative about
    2027. Pitchers should trust ZiPS's own playing-time opinion more."""
    assert C.PT_BLEND_CAP_PITCHER < C.PT_BLEND_CAP_HITTER


def test_short_season_pitcher_projected_innings_lean_toward_zips(board):
    """End-to-end version of the same check, on real data: a pitcher whose
    2026 (actual + rest-of-season) innings project well short of a normal
    workload should land, in the final 2027 blend, closer to ZiPS's own
    healthy innings total than to the 50/50 midpoint the old shared-weight
    blend would have produced. Doesn't hardcode Hunter Brown by name --
    finds whichever qualifying short-season starter exists in the current
    data, so this keeps working as rosters change."""
    from klab.project import project_pitchers
    from klab.io import load_zips27_pitchers
    p = project_pitchers()
    z = load_zips27_pitchers().groupby("fg_id", as_index=False)["IP"].sum()
    m = p.merge(z, on="fg_id", suffixes=("", "_zips"))
    # a starter ZiPS expects to throw a full workload, but whose blended IP
    # implies real 2026 shortfall was priced in at all (w_2026 < 1, i.e. some
    # 2026 evidence exists) and who isn't a reliever
    candidates = m[(~m["reliever"]) & (m["IP_zips"] > 140) & (m["w_2026"] < 0.99)
                  & (m["w_2026"] > 0.01) & (m["IP"] < m["IP_zips"] * 0.9)]
    assert len(candidates) > 0, "test needs at least one short-season qualifying starter"
    r = candidates.iloc[0]
    # the actual invariant: a lower PT cap must keep the blended IP close to
    # ZiPS's own total, not dragged down toward a shortened 2026 sample
    assert abs(r["IP"] - r["IP_zips"]) < r["IP_zips"] * 0.35, \
        f"{r['name']}: blended IP {r['IP']:.1f} strayed too far from ZiPS's {r['IP_zips']:.1f}"


# --- direction-aware pitcher playing-time trust (out/FINDINGS.md #53) ------

def test_exceeded_pitcher_cap_is_higher_than_default_cap():
    """Josh's approved fix: a pitcher whose real 2026 (actual + ROS) innings
    already exceed ZiPS's own 2027 opinion for him has direct proof he can
    carry that workload -- stronger evidence than a system's generic
    caution about ramping a young arm's innings -- so he gets a higher cap
    than the injury-shortfall default. Still below full trust: a team's
    actual workload-management plan is real information too."""
    assert C.PT_BLEND_CAP_PITCHER < C.PT_BLEND_CAP_PITCHER_EXCEEDED < 1.0


def test_blend_weight_accepts_a_per_player_cap_series():
    """_blend_weight()'s cap can now vary player-to-player (out/FINDINGS.md
    #53) -- pandas' elementwise clip, not one scalar bound applied to
    everyone alike, which is what lets project_pitchers() give only the
    players who exceeded ZiPS's number the higher cap."""
    ip_a = pd.Series([200.0, 200.0])   # same sample size for both
    cap = pd.Series([C.PT_BLEND_CAP_PITCHER, C.PT_BLEND_CAP_PITCHER_EXCEEDED])
    w = _blend_weight(ip_a, 70.0, cap=cap)
    assert w.iloc[0] == pytest.approx(C.PT_BLEND_CAP_PITCHER)
    assert w.iloc[1] == pytest.approx(C.PT_BLEND_CAP_PITCHER_EXCEEDED)


def test_pitcher_who_exceeded_zips_leans_more_on_his_own_workload():
    """End-to-end: for a pitcher whose real 2026 workload already exceeds
    ZiPS's own 2027 IP opinion for him, the shipped blend must land closer
    to his own total than the pre-#53 formula (a single PT_BLEND_CAP_PITCHER
    for everyone) would have. Doesn't hardcode Cam Schlittler (187 actual vs.
    128 ZiPS 2027 -- the case that motivated this) by name, so it keeps
    working as rosters and projections change. Reimplements the same IP_a/
    IP_b merge project_pitchers() does internally, since those columns
    don't survive onto its returned frame."""
    from klab.io import load_ros_pitchers, load_zips27_pitchers
    from klab.project import SHRINK_IP

    hist = load_pitchers_history()
    a26 = hist[hist["season"] == 2026].copy()
    ros = load_ros_pitchers()
    cols = ["IP", "W", "SV", "K", "ER", "BB", "H"]
    a = a26[["fg_id", "name", "G", "GS"] + cols].groupby("fg_id", as_index=False).agg(
        {"name": "first", "G": "sum", "GS": "sum", **{c: "sum" for c in cols}})
    r = ros.rename(columns={"SO": "K"})[["fg_id"] + cols].groupby(
        "fg_id", as_index=False).sum()
    A = a.merge(r, on="fg_id", how="outer", suffixes=("", "_ros"))
    for c in cols:
        A[c] = A[c].fillna(0.0) + A[f"{c}_ros"].fillna(0.0)
    A["reliever"] = A["GS"].fillna(0) < 0.5 * A["G"].fillna(0).clip(lower=1)

    z = load_zips27_pitchers().rename(columns={"SO": "K"})
    B = z[["fg_id", "IP"]].groupby("fg_id", as_index=False).sum()
    m = A.merge(B, on="fg_id", suffixes=("_a", "_b"))

    exceeded = (~m["reliever"]) & (m["IP_a"] > m["IP_b"]) & (m["IP_b"] > 60)
    assert exceeded.sum() > 0, "test needs at least one qualifying exceeded-workload starter"
    cand = m[exceeded].iloc[0]

    w_default = _blend_weight(pd.Series([cand["IP_a"]]), SHRINK_IP,
                              cap=C.PT_BLEND_CAP_PITCHER).iloc[0]
    ip_old_formula = w_default * cand["IP_a"] + (1 - w_default) * cand["IP_b"]

    from klab.project import project_pitchers
    p = project_pitchers()
    ip_shipped = p.loc[p["fg_id"] == cand["fg_id"], "IP"].iloc[0]

    assert ip_shipped > ip_old_formula, (
        f"{cand['name']}: shipped IP {ip_shipped:.1f} should exceed the "
        f"pre-#53 formula's {ip_old_formula:.1f} once the higher cap applies")


# --- C/SS positional adjustment (out/FINDINGS.md #52) -----------------------

def test_positional_adjustment_actually_changes_values():
    """Real bug, caught testing this directly before it shipped: the first
    version took min(pooled, position-specific) to break a tie for a player
    eligible at multiple adjusted positions, but that same "min" also
    silently compared against the pooled default -- and since both catcher
    and shortstop replacement come out ABOVE the pooled level on this
    league's real 2026 data, positional=True produced byte-identical
    output to positional=False with no error. A change that does nothing
    is worse than one that's visibly wrong: nothing would have caught this
    in the UI either, since the toggle would have looked like it worked."""
    from klab.board import value_players
    off, _, _ = value_players(None, positional=False)
    on, _, _ = value_players(None, positional=True)
    m = off[["fg_id", "redraft_value"]].merge(
        on[["fg_id", "redraft_value"]], on="fg_id", suffixes=("_off", "_on"))
    changed = (m["redraft_value_off"] != m["redraft_value_on"]).sum()
    assert changed > 50, f"only {changed} players changed -- adjustment is probably a no-op"


def test_positional_adjustment_leaves_default_path_untouched():
    """positional=False (every existing caller) must be byte-identical to
    before this feature existed -- the shared value_players()/build_board()
    functions were restructured to support the new parameter, and a
    regression here would silently change every dollar figure in the app,
    not just catcher/shortstop ones."""
    from klab.board import build_board
    b1, _, m1 = build_board()             # default, positional not passed
    b2, _, m2 = build_board(positional=False)   # explicit False
    assert (b1["redraft_value"] == b2["redraft_value"]).all()
    assert m1["budget_check_top230"] == pytest.approx(2600.0, abs=0.01)


def test_positional_adjustment_budget_check_stays_close(board):
    """The $2,600 top-230 identity is exact under pooled replacement (every
    top-230 player is above the pooled bar by construction) but only
    approximate under positional adjustment (a player can rank in the
    overall top 230 while sitting below his OWN position's higher bar,
    breaking the clean linear calibration -- see the long comment in
    value_players()). Approximate is fine for a documented sanity-check
    number; miscalibrated by a lot would mean the recalibration math itself
    is wrong."""
    from klab.board import build_board
    _, _, meta = build_board(positional=True)
    assert meta["budget_check_top230"] == pytest.approx(2600.0, rel=0.05)


def test_positional_adjustment_only_touches_catchers_and_shortstops():
    """A player who isn't C/SS-eligible should see his `rp_above_repl`
    change ONLY through the recalibrated $/point scale's effect on
    redraft_value, never through a different replacement level being
    subtracted -- his own rp_above_repl (roto_points minus replacement)
    must be identical on vs off, even though his dollar value can move."""
    from klab.board import value_players
    from klab.io import load_position_eligibility
    off, _, _ = value_players(None, positional=False)
    on, _, _ = value_players(None, positional=True)
    elig = load_position_eligibility()
    adjusted_ids = elig["C"] | elig["SS"]
    # Merge on (fg_id, role), not fg_id alone -- a true two-way player
    # (config.TWO_WAY_SPLIT_NAMES) has two rows sharing one fg_id in both
    # `off` and `on`, and a plain fg_id merge cartesian-joins his 2x2 rows
    # into 4, comparing e.g. his HIT row's off-value against his PIT row's
    # on-value and reporting a bogus mismatch. Everyone else still has one
    # role per fg_id, so this is a no-op widening for them.
    m = off[["fg_id", "role", "rp_above_repl"]].merge(
        on[["fg_id", "role", "rp_above_repl"]], on=["fg_id", "role"],
        suffixes=("_off", "_on"))
    unaffected = m[~m["fg_id"].isin(adjusted_ids)]
    assert (unaffected["rp_above_repl_off"] == unaffected["rp_above_repl_on"]).all()


def test_positional_adjustment_2028_actually_uses_the_position_specific_bar():
    """The SAME min()-based no-op bug #52 found in value_players() was still
    live in value_2028() -- caught by reverse-solving the replacement level
    implied by a shortstop's 2028 dollar figure and finding it equal to the
    pooled number, not his own position's. A shortstop's 2028 value must
    actually move by the gap between the pooled and position-specific
    replacement level, not only by the leaguewide $/point rescale every
    player rides regardless of position."""
    from klab.board import build_board, value_players, value_2028
    _, exch_on, meta_on = build_board(positional=True)

    players_on, _, _ = value_players(exch_on, positional=True)
    # .groupby(...).max(), not .set_index(...) -- a true two-way player
    # (config.TWO_WAY_SPLIT_NAMES) has two rows sharing one fg_id, and a
    # duplicate-keyed Series breaks the .map() lookup inside
    # project_saves(). Same fix as klab.board.build_board() /
    # klab.freeagents.free_agent_board().
    sv27 = players_on.groupby("fg_id")["SV"].max() if "SV" in players_on else None
    # Same exch/meta (same $/point scale, same pooled replacement_rp) for
    # both calls -- positional=False here just skips the override block, so
    # this isolates the replacement-level effect from the scale-rescale
    # effect every player rides regardless of position.
    v28_pooled_repl = value_2028(exch_on, meta_on, sv27, positional=False)
    v28_position_repl = value_2028(exch_on, meta_on, sv27, positional=True)

    from klab.io import load_position_eligibility
    elig = load_position_eligibility()
    ss_ids = elig["SS"]
    m = v28_pooled_repl[["fg_id", "redraft_value_2028"]].merge(
        v28_position_repl[["fg_id", "redraft_value_2028"]],
        on="fg_id", suffixes=("_pooled", "_position"))
    ss_rows = m[m["fg_id"].isin(ss_ids) & (m["redraft_value_2028_pooled"] > 1.0)]
    assert len(ss_rows) > 0, "test needs at least one non-floored rostered-caliber shortstop"
    # SS replacement (6.76) sits above pooled (~4.8), so applying it must
    # strictly lower every affected shortstop's 2028 value, not leave it
    # identical to the pooled-replacement run.
    assert (ss_rows["redraft_value_2028_position"]
           < ss_rows["redraft_value_2028_pooled"]).all()


# --- Monte Carlo standings simulator (out/ROADMAP.md Phase 5) --------------

def test_money_probabilities_are_internally_consistent(board):
    """p_money must equal the sum of p_finish_1..p_finish_PAYOUT_SPOTS
    exactly (it's computed that way, but this catches a future refactor
    breaking the identity), every probability must be a valid [0,1] value,
    and across all ten teams each p_finish_N column must sum to ~1.0 --
    exactly one team finishes in each place in every draw, so summing "how
    often was team X in place N" across every team must recover the total
    draw count, within Monte Carlo noise."""
    b, _, _ = board
    out = simulate_finish_odds(b, B=500, seed=0)
    assert len(out) == C.N_TEAMS
    finish_cols = [f"p_finish_{p}" for p in range(1, C.PAYOUT_SPOTS + 1)]
    assert out["p_money"].to_numpy() == pytest.approx(out[finish_cols].sum(axis=1).to_numpy())
    assert ((out[finish_cols + ["p_money"]] >= 0).all().all())
    assert ((out[finish_cols + ["p_money"]] <= 1).all().all())
    for col in finish_cols:
        assert out[col].sum() == pytest.approx(1.0, abs=1e-9)


def test_current_standings_leader_favored_over_last_place(board):
    """A team that's already well ahead in the real, already-accumulated
    2026 standings must come out with materially higher odds of finishing
    in the money than the team that's well behind -- the simulator only
    jitters what's LEFT to play, so a big enough real head start should
    dominate simulated rest-of-season noise, not get washed out by it."""
    b, _, _ = board
    out = simulate_finish_odds(b, B=500, seed=0)
    leader = out.loc[out["current_points"].idxmax()]
    last = out.loc[out["current_points"].idxmin()]
    assert leader["p_money"] > last["p_money"]


def test_same_seed_is_reproducible(board):
    """A fixed seed must give byte-identical results run to run -- both so a
    single build is reproducible, and because the JS port's verification
    check needs a stable Python reference to compare against, not a moving
    target."""
    b, _, _ = board
    a = simulate_finish_odds(b, B=300, seed=7)
    c = simulate_finish_odds(b, B=300, seed=7)
    assert a["p_money"].equals(c["p_money"])


def test_zero_shock_scale_is_fully_deterministic(board):
    """With shock_scale=0 every draw jitters nothing, so the same team must
    finish in each payout place in literally every draw -- the most direct
    confirmation that the jitter mechanism, not something else, is what's
    producing variance in the normal (shock_scale>0) case."""
    b, _, _ = board
    out = simulate_finish_odds(b, B=50, seed=0, shock_scale=0.0)
    assert (out["p_finish_1"].isin([0.0, 1.0])).all()
    assert out["p_finish_1"].sum() == pytest.approx(1.0)


def test_swap_changes_the_odds_in_the_expected_direction(board):
    """Moving a real, valuable player from one team to another must raise
    the acquiring team's odds of finishing in the money and lower the
    sending team's -- the same `swap` mechanism `win_now_delta()` uses,
    exercised through the simulator instead. Picks the two teams with the
    most genuine uncertainty (p_money closest to 0.5) rather than hardcoding
    which teams -- with PAYOUT_SPOTS=4 (a much easier bar than the original
    top-2-only build), the current standings' 2nd/3rd place teams are
    already near a 100% ceiling with no room left to move; the real
    uncertainty sits lower in the standings, around whichever teams are
    fighting for the last payout spot, which changes as rosters do."""
    b, _, _ = board
    before = simulate_finish_odds(b, B=800, seed=3)
    by_uncertainty = before.assign(dist=(before["p_money"] - 0.5).abs()).sort_values("dist")
    recipient, donor_team = by_uncertainty["team"].iloc[0], by_uncertainty["team"].iloc[1]
    donor = b[b["team"] == donor_team].nlargest(1, "roto_points").iloc[0]
    fid = int(donor["fg_id"])

    after = simulate_finish_odds(b, swap={fid: recipient}, B=800, seed=3)

    p_before = before.set_index("team")["p_money"]
    p_after = after.set_index("team")["p_money"]
    assert p_after[recipient] > p_before[recipient]
    assert p_after[donor_team] < p_before[donor_team]


# --- Stage 3: 2027 keeper-core finish odds (out/ROADMAP.md Phase 5) --------

def test_keeper_finish_odds_probabilities_are_internally_consistent(board):
    """Same identity check as the rest-of-2026 simulator, for the 2027
    keeper-core version: p_money must equal the sum of the per-place
    columns, every probability must be valid, and each place column must
    sum to ~1.0 across teams."""
    from klab.standings_sim import simulate_keeper_finish_odds
    from klab.freeagents import free_agent_board
    b, _, meta = board
    fa = free_agent_board()
    out = simulate_keeper_finish_odds(b, fa, meta["replacement_rp"], B=300, seed=0)
    finish_cols = [f"p_finish_{p}" for p in range(1, C.PAYOUT_SPOTS + 1)]
    assert out["p_money"].to_numpy() == pytest.approx(out[finish_cols].sum(axis=1).to_numpy())
    assert ((out[finish_cols + ["p_money"]] >= 0).all().all())
    assert ((out[finish_cols + ["p_money"]] <= 1).all().all())
    for col in finish_cols:
        assert out[col].sum() == pytest.approx(1.0, abs=1e-9)


def test_keeper_finish_odds_reassignment_moves_the_odds(board):
    """Moving a real keeper from one team's keeper set to another's (the
    `keeper_override` mechanism) must raise the receiving team's odds and
    lower the sending team's -- mirrors the rest-of-2026 simulator's own
    swap-direction test, using whichever two teams have the closest to 50%
    baseline odds so neither is already at a ceiling or floor with no room
    to move."""
    from klab.standings_sim import simulate_keeper_finish_odds
    from klab.freeagents import free_agent_board
    b, _, meta = board
    fa = free_agent_board()
    repl = meta["replacement_rp"]
    before = simulate_keeper_finish_odds(b, fa, repl, B=600, seed=5)
    by_uncertainty = before.assign(dist=(before["p_money"] - 0.5).abs()).sort_values("dist")
    recipient, donor_team = by_uncertainty["team"].iloc[0], by_uncertainty["team"].iloc[1]

    kept = b[b["keep_2027"] & (b["team"] == donor_team)]
    assert len(kept) > 0, "test needs a donor team with at least one keeper"
    donor = kept.nlargest(1, "roto_points").iloc[0]
    fid = int(donor["fg_id"])

    after = simulate_keeper_finish_odds(b, fa, repl, keeper_override={fid: recipient},
                                        B=600, seed=5)
    p_before = before.set_index("team")["p_money"]
    p_after = after.set_index("team")["p_money"]
    assert p_after[recipient] > p_before[recipient]
    assert p_after[donor_team] < p_before[donor_team]
