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
from klab.board import build_board, keeper_status, value_players
from klab.denoms import teams_per_category
from klab.keeper import keeper_cost, multiyear_surplus, years_controlled
from klab.trade import evaluate_trade, ros_value_over_replacement, standings_points
from klab.io import load_hitters_history, load_pitchers_history
from klab.project import _blend_weight
from klab.standings_sim import simulate_finish_odds


@pytest.fixture(scope="module")
def board():
    b, exch, meta = build_board()
    return b, exch, meta


@pytest.fixture(scope="module")
def fa():
    from klab.freeagents import free_agent_board
    return free_agent_board()


@pytest.fixture(scope="module")
def trade_pair(board):
    """One player from each of the first two teams, for evaluate_trade tests."""
    b, _, _ = board
    teams = b["team"].unique()
    a_name = b[b["team"] == teams[0]]["name"].iloc[0]
    b_name = b[b["team"] == teams[1]]["name"].iloc[0]
    return teams[0], teams[1], a_name, b_name


# --- the bug external review found -----------------------------------------

def test_budget_identity(board):
    """The 230 rostered players must clear exactly the league's cap. Values
    at full-time PT against a scale calibrated on expected PT once summed to
    $3,854 instead of $2,600."""
    _, _, meta = board
    assert meta["budget_check_top230"] == pytest.approx(C.N_TEAMS * C.BUDGET, rel=1e-6)


def test_replacement_agrees_with_auction_intercept(board):
    """Replacement level (230th projection) and the auction intercept ($0
    bought historically) estimate the same quantity from unrelated data."""
    _, exch, meta = board
    assert abs(meta["replacement_rp"] - exch["intercept"]) < 1.5


# --- sign conventions -------------------------------------------------------

def test_standings_points_direction():
    """Biggest counting total earns the most points; lowest ERA/WHIP wins.
    An inverted rank once put the league leader in last place."""
    wide = pd.DataFrame(
        {c: [1.0, 2.0, 3.0] for c in C.CATS}, index=["a", "b", "c"])
    pts = standings_points(wide)
    assert pts.loc["c", "HR"] > pts.loc["a", "HR"]      # more HR = more points
    assert pts.loc["a", "ERA"] > pts.loc["c", "ERA"]    # lower ERA = more points
    assert pts.loc["a", "WHIP"] > pts.loc["c", "WHIP"]


def test_category_sign_conventions_hold_every_season():
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


def test_denominators_positive_and_sane(board):
    _, _, meta = board
    D = meta["denominators"]
    assert set(D) == set(C.CATS)
    assert all(v > 0 for v in D.values())
    # 1 HR should buy more than 1 SB, and both far more than 1 R
    assert D["HR"] < D["SB"] < D["R"]


def test_saves_use_the_reduced_field_constant():
    """After punters are dropped the SV field is 8 teams, not 10; the 10-team
    range constant overvalued every save by 19%."""
    n = teams_per_category()
    assert n["SV"] < C.N_TEAMS
    assert n["HR"] == C.N_TEAMS


# --- contract semantics -----------------------------------------------------

@pytest.mark.parametrize("code,years,cost", [
    ("1", 1, 20.0), ("2", 2, 20.0), ("3", 3, 20.0), ("F", 1, 25.0),
])
def test_contract_codes(code, years, cost):
    """The code is seasons remaining AFTER the current one; only F pays +$5.
    The original handoff had this backwards."""
    assert years_controlled(code) == years
    assert keeper_cost(20, code) == cost


def test_unknown_contract_is_charged_worst_case():
    assert keeper_cost(20, "?") == 25.0
    assert keeper_status("?") == "unknown"


def test_multiyear_surplus_never_penalises_length():
    """A contract is an option: an extra year of control cannot make a player
    worth less than the same player with one year."""
    v27 = pd.Series([10.0, 10.0]); v28 = pd.Series([0.0, 0.0])
    cost = pd.Series([11.0, 11.0]); yrs = pd.Series([1, 2])
    out = multiyear_surplus(v27, v28, cost, yrs, pd.Series([11.0, 11.0]))
    assert out["surplus_multiyear"].iloc[1] >= out["surplus_multiyear"].iloc[0] - 1e-9


def test_final_year_player_can_buy_two_extension_years():
    """multiyear_surplus()'s raw math in isolation: IF an F player's extension
    were live, a 2028 line clearing the extra $5 is valued at two years, not
    one. Never applied on the real board since docs/FINDINGS.md #39 -- see
    test_f_contract_players_are_never_keepable."""
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


def test_extension_option_eligibility_and_worthless_option():
    """Only code 1 (about to enter his final year) is extension-eligible --
    codes 2/3 carried a phantom option before docs/FINDINGS.md #33 -- and a
    live option not worth exercising reports 0 years, never "pay $5 for nothing"."""
    sal = pd.Series([10.0, 10.0, 10.0])
    v27 = pd.Series([30.0, 30.0, 30.0])
    v28 = pd.Series([40.0, 40.0, 40.0])          # clearly clears any extension cost
    out = multiyear_surplus(v27, v28, sal, pd.Series([1, 2, 3]), sal)
    assert out["extension_option"].iloc[0] > 0, "code 1 should be extension-eligible"
    assert out["extension_option"].iloc[1] == pytest.approx(0.0), "code 2 is not eligible yet"
    assert out["extension_option"].iloc[2] == pytest.approx(0.0), "code 3 is not eligible yet"
    assert out["extension_years"].iloc[1] == 0
    assert out["extension_years"].iloc[2] == 0

    sal = pd.Series([30.0])
    out = multiyear_surplus(pd.Series([20.0]), pd.Series([5.0]), sal, pd.Series([2]), sal)
    assert out["extension_years"].iloc[0] == 0
    assert out["extension_option"].iloc[0] == pytest.approx(0.0)


def test_f_contract_players_are_never_keepable(board):
    """docs/FINDINGS.md #39: an F observed in contracts_parsed.csv already
    missed the extension window, so keepable is False and every forward
    figure is 0 for EVERY F player; and his status label must not claim an
    extension exists (it said "extension +$5" until FINDINGS #44)."""
    b, _, _ = board
    f_players = b[b["contract"].astype(str).str.upper() == "F"]
    assert len(f_players) > 0, "test needs at least one F-contract player to exist"
    assert not f_players["keepable"].any()
    assert not f_players["keep_2027"].any()
    assert (f_players["extension_option"] == 0).all()
    assert (f_players["surplus_multiyear"] == 0).all()
    assert not f_players["keeper_status"].str.contains(r"\$", regex=True).any()
    assert f_players["keeper_status"].eq("free agent after 2026 (not extendable)").all()


# --- data integrity ---------------------------------------------------------

def test_board_two_way_handling(board):
    """No duplicated (fg_id, role); the only duplicated fg_id is a true
    two-way player (config.TWO_WAY_SPLIT_NAMES); and the zero-PA pitcher rows
    in the FanGraphs hitter export must not tag every starter as TWO."""
    b, _, _ = board
    assert b.duplicated(["fg_id", "role"]).sum() == 0
    dup_fg_id = b[b["fg_id"].duplicated(keep=False)]
    assert set(dup_fg_id["name"].unique()) <= C.TWO_WAY_SPLIT_NAMES
    assert (b["role"] == "TWO").sum() <= 2
    assert (b["role"] == "PIT").sum() > 50


def test_name_matching_coverage():
    """671 of 677 auction purchases resolve; the rest are genuine
    zero-production buys."""
    d = match_drafts(verbose=False)
    assert d["fg_id"].notna().sum() >= 670
    assert len(d) == 677


def test_values_never_negative_and_full_time_never_below_expected(board):
    """A player cannot be a negative asset, and scaling playing time up
    cannot make him worth less."""
    b, _, _ = board
    assert (b["redraft_value"] >= 0).all()
    assert (b["keep_value"] >= 0).all()
    assert (b["redraft_value_ft"] >= b["redraft_value"] - 1e-6).all()


def test_keeper_sets_respect_league_limits(board):
    b, _, _ = board
    counts = b[b["keep_2027"]].groupby("team").size()
    assert (counts >= C.MIN_KEEPERS).all()
    assert (counts <= C.MAX_KEEPERS).all()


# --- golden file: ten players across the value spectrum ---------------------
#
# Loose bounds that encode domain knowledge, not exact equality -- the model
# is meant to change.

GOLDEN = [
    ("Shohei Ohtani", "HIT", 30, 70),    # priced as two 2027 assets (TWO_WAY_SPLIT_NAMES)
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

def test_free_agent_board_invariants(board, fa):
    """A dropped player keeps his draft-year contract if re-added (2026 buys
    two years, 2025 one, older reverts to the FA price); no free agent is on a
    roster; and out-year values come from the full projection (merging off
    the rostered board silently zeroed every free agent's 2028)."""
    b, _, _ = board
    live = fa[fa["acquisition"] == "draft contract"]
    assert len(live) > 20
    for yr, yrs in [(2026, 2), (2025, 1)]:
        sub = live[live["draft_year"] == yr]
        if len(sub):
            assert (sub["years_controlled"] == yrs).all()
    stale = fa[fa["acquisition"] == "free agent price"]
    assert (stale["salary"] == C.FA_SALARY_POST_ASB).all()
    assert len(set(fa["fg_id"]) & set(b["fg_id"])) == 0
    assert (live["redraft_value_2028"] > 0).sum() > 5


def test_snapshot_is_self_consistent():
    from klab.api import snapshot
    s = snapshot()
    assert s.constants["budget_check_top230"] == pytest.approx(2600, rel=1e-6)
    assert 1.0 < s.constants["inflation"] < 3.0
    assert set(s.teams.index) == set(s.board["team"].unique())
    assert len(s.standings) == C.N_TEAMS


def test_app_payload_has_no_column_collisions_and_no_nans():
    """The exported payload is what the browser sees. A silent column
    collision (ros PA vs projected PA) shipped a null into the player card."""
    import sys
    sys.path.insert(0, str(C.DATA.parent / "scripts"))
    from build_app import build_payload
    p = build_payload()
    assert len(p["cols"]) == len(set(p["cols"])), "duplicate column in payload"
    ix = {c: i for i, c in enumerate(p["cols"])}
    for col in ["PA", "AB", "IP", "redraft_value", "keeper_cost", "surplus_multiyear"]:
        assert col in ix
    # A two-way player ships as HIT and PIT rows; the PA>0 check is on his hitter row.
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
    """klab.project.RELIABILITY is a hard-coded fit. BB and H once carried
    WHIP's r=0.237 by copy-paste (docs/FINDINGS.md #28); this reruns the fit
    the dict represents."""
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


# --- evaluate_trade: had zero coverage until docs/FINDINGS.md #32.1 --------

def test_evaluate_trade_usd_per_point_is_required_and_live(board, trade_pair):
    """usd_per_point used to default to a silently-stale constant every
    caller forgot to override (docs/FINDINGS.md #32.1): it must be required,
    and verdict_score must actually move when it changes."""
    b, _, _ = board
    team_a, team_b, a_name, b_name = trade_pair
    with pytest.raises(TypeError):
        evaluate_trade(b, team_a, team_b, [a_name], [b_name])
    low = evaluate_trade(b, team_a, team_b, [a_name], [b_name], usd_per_point=1.0)
    high = evaluate_trade(b, team_a, team_b, [a_name], [b_name], usd_per_point=100.0)
    if abs(low["a"]["d_standings_points_2026"]) > 0.01:
        assert low["a"]["verdict_score"] != pytest.approx(high["a"]["verdict_score"])


def test_evaluate_trade_ros_basis_changes_win_now_numbers(board):
    """The win-now standings delta must actually respond to ros_basis."""
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
    assert (r1["a"]["d_standings_points_2026"] != pytest.approx(r2["a"]["d_standings_points_2026"])
           or r1["b"]["d_standings_points_2026"] != pytest.approx(r2["b"]["d_standings_points_2026"]))


# --- ros_value_over_replacement: rest-of-season value, not a full year ----

def _hitter_line(pa, avg=0.27, hr=0.04, r=0.13, rbi=0.13, sb=0.02):
    return pd.DataFrame([{
        "fg_id": 1, "role": "HIT", "PA": pa, "AB": pa * 0.9,
        "H": pa * 0.9 * avg, "HR": pa * hr, "R": pa * r, "RBI": pa * rbi, "SB": pa * sb,
        "IP": 0.0, "W": 0.0, "SV": 0.0, "K": 0.0, "ER": 0.0, "BB": 0.0, "H_allowed": 0.0,
    }])


def test_ros_value_over_replacement_scales_with_pt_and_ranks_rates():
    """Half the remaining PA at the same rates is roughly half the value over
    replacement (the baseline scales too); at equal PT a better rate line
    scores higher."""
    from klab.board import build_2027_scorer
    _, D, base, _ = build_2027_scorer()

    half = ros_value_over_replacement(_hitter_line(C.KEEPER_PA_FLOOR * 0.5), D, base, 4.78)
    full = ros_value_over_replacement(_hitter_line(C.KEEPER_PA_FLOOR), D, base, 4.78)
    assert half["remaining_frac"].iloc[0] == pytest.approx(0.5, abs=0.01)
    assert full["remaining_frac"].iloc[0] == pytest.approx(1.0, abs=0.01)
    ratio = half["ros_value_over_replacement"].iloc[0] / full["ros_value_over_replacement"].iloc[0]
    assert 0.4 < ratio < 0.6

    pa = C.KEEPER_PA_FLOOR * 0.3
    good = _hitter_line(pa, avg=0.31, hr=0.06, r=0.16, rbi=0.16, sb=0.03)
    bad = good.copy()
    bad[["H", "HR", "R", "RBI", "SB"]] *= 0.5
    g = ros_value_over_replacement(good, D, base, 4.78)
    b = ros_value_over_replacement(bad, D, base, 4.78)
    assert g["ros_value_over_replacement"].iloc[0] > b["ros_value_over_replacement"].iloc[0]


# --- ros_lines_for_basis: blended 2026 rest-of-season signal (FINDINGS #45) -

def test_prorated_to_date_lines_invariants():
    """Drop-in for ros_lines() (same columns, non-negative), a plausible
    remaining-games estimate, and no starter projected past a full season's
    IP -- dividing by his own G (starts, not team games) once projected 256
    more innings for an ace (LAB_NOTEBOOK.md (git history, commit 8353172) #24)."""
    from klab.trade import prorated_to_date_lines, ros_lines
    p = prorated_to_date_lines()
    r = ros_lines()
    assert set(p.columns) == set(r.columns)
    assert (p.drop(columns="fg_id") >= 0).all().all(), "prorated counting stats must be non-negative"
    assert 0.0 < p.attrs["remaining_games"] < C.SEASON_GAMES

    p26 = load_pitchers_history().query("season == 2026")
    starters = p26[(p26["GS"] > 10) & (p26["IP"] > 50)]
    assert len(starters) > 0, "test needs at least one qualifying starter"
    prorated = p.set_index("fg_id")
    for fid in starters["fg_id"]:
        if fid in prorated.index:
            assert prorated.loc[fid, "IP"] < C.SEASON_GAMES, \
                f"fg_id {fid} projected for an implausible {prorated.loc[fid, 'IP']:.0f} more innings"


def test_ros_lines_for_basis_blend_and_rejects_unknown():
    from klab.trade import ros_lines_for_basis, ros_lines, prorated_to_date_lines
    blend = ros_lines_for_basis("blend").set_index("fg_id")
    a = ros_lines().set_index("fg_id")
    b = prorated_to_date_lines().set_index("fg_id")
    common = a.index.intersection(b.index)
    assert len(common) > 0, "test needs at least one player in both ROS sources"
    fid = common[0]
    for col in ["PA", "IP"]:
        expected = (a.loc[fid, col] + b.loc[fid, col]) / 2.0
        assert blend.loc[fid, col] == pytest.approx(expected, abs=1e-6)
    with pytest.raises(ValueError):
        ros_lines_for_basis("preseason")


# --- playing-time / rate decoupling (docs/FINDINGS.md #51, #53) ---------------

def test_playing_time_caps_and_blend_weight():
    """PT weight is capped below the rate weight (pitchers especially, so an
    injury-shortened 2026 doesn't dock 2027 IP -- #51); pitcher cap < hitter
    cap; the exceeded-workload cap sits between them and 1.0 (#53); and
    _blend_weight accepts a per-player cap Series (elementwise clip)."""
    ip_a = pd.Series([200.0])   # a large sample, so both weights hit their cap
    rate_w = _blend_weight(ip_a, 70.0, cap=C.BLEND_W_2026)
    pt_w = _blend_weight(ip_a, 70.0, cap=C.PT_BLEND_CAP_PITCHER)
    assert pt_w.iloc[0] < rate_w.iloc[0]
    assert pt_w.iloc[0] == pytest.approx(C.PT_BLEND_CAP_PITCHER)
    assert C.PT_BLEND_CAP_PITCHER < C.PT_BLEND_CAP_HITTER
    assert C.PT_BLEND_CAP_PITCHER < C.PT_BLEND_CAP_PITCHER_EXCEEDED < 1.0

    cap = pd.Series([C.PT_BLEND_CAP_PITCHER, C.PT_BLEND_CAP_PITCHER_EXCEEDED])
    w = _blend_weight(pd.Series([200.0, 200.0]), 70.0, cap=cap)
    assert w.iloc[0] == pytest.approx(C.PT_BLEND_CAP_PITCHER)
    assert w.iloc[1] == pytest.approx(C.PT_BLEND_CAP_PITCHER_EXCEEDED)


def test_short_season_pitcher_projected_innings_lean_toward_zips():
    """End-to-end on real data: a starter whose 2026 innings fell well short
    of ZiPS's healthy total must land close to ZiPS's IP, not the 50/50
    midpoint. Finds whichever qualifying starter exists rather than naming one."""
    from klab.project import project_pitchers
    from klab.io import load_zips27_pitchers
    p = project_pitchers()
    z = load_zips27_pitchers().groupby("fg_id", as_index=False)["IP"].sum()
    m = p.merge(z, on="fg_id", suffixes=("", "_zips"))
    candidates = m[(~m["reliever"]) & (m["IP_zips"] > 140) & (m["w_2026"] < 0.99)
                  & (m["w_2026"] > 0.01) & (m["IP"] < m["IP_zips"] * 0.9)]
    assert len(candidates) > 0, "test needs at least one short-season qualifying starter"
    r = candidates.iloc[0]
    assert abs(r["IP"] - r["IP_zips"]) < r["IP_zips"] * 0.35, \
        f"{r['name']}: blended IP {r['IP']:.1f} strayed too far from ZiPS's {r['IP_zips']:.1f}"


def test_pitcher_who_exceeded_zips_leans_more_on_his_own_workload():
    """End-to-end: a pitcher whose real 2026 IP exceeds ZiPS's 2027 IP must
    ship with more IP than the single-cap pre-#53 formula would give.
    Reimplements project_pitchers()'s IP_a/IP_b merge, which doesn't survive
    onto its returned frame."""
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


# --- C/SS positional adjustment (docs/FINDINGS.md #52) -----------------------

def test_positional_adjustment_changes_only_catcher_and_shortstop_bars():
    """positional=True must actually change values -- min(pooled, pos)
    silently no-op'd since C/SS sit above pooled -- and a non-C/SS player's
    rp_above_repl must be identical on vs off (only the $/point rescale moves
    his dollars). Merge on (fg_id, role): a two-way player has two rows."""
    from klab.io import load_position_eligibility
    off, _, _ = value_players(None, positional=False)
    on, _, _ = value_players(None, positional=True)
    m = off[["fg_id", "role", "redraft_value", "rp_above_repl"]].merge(
        on[["fg_id", "role", "redraft_value", "rp_above_repl"]],
        on=["fg_id", "role"], suffixes=("_off", "_on"))
    changed = (m["redraft_value_off"] != m["redraft_value_on"]).sum()
    assert changed > 50, f"only {changed} players changed -- adjustment is probably a no-op"
    elig = load_position_eligibility()
    unaffected = m[~m["fg_id"].isin(elig["C"] | elig["SS"])]
    assert (unaffected["rp_above_repl_off"] == unaffected["rp_above_repl_on"]).all()


def test_positional_adjustment_budget_identity_both_settings():
    """positional=False must equal the default path exactly with the $2,600
    identity exact; positional=True keeps it within ~5% (a top-230 player
    can sit below his own position's bar -- see value_players())."""
    b1, _, m1 = build_board()
    b2, _, m2 = build_board(positional=False)
    assert (b1["redraft_value"] == b2["redraft_value"]).all()
    assert m1["budget_check_top230"] == pytest.approx(2600.0, abs=0.01)
    _, _, meta = build_board(positional=True)
    assert meta["budget_check_top230"] == pytest.approx(2600.0, rel=0.05)


def test_positional_adjustment_2028_actually_uses_the_position_specific_bar():
    """The same min()-based no-op bug was live in value_2028(): a shortstop's
    2028 value must move by the pooled-vs-SS replacement gap, not only by the
    leaguewide $/point rescale."""
    from klab.board import value_2028
    from klab.io import load_position_eligibility
    _, exch_on, meta_on = build_board(positional=True)
    players_on, _, _ = value_players(exch_on, positional=True)
    # groupby().max(), not set_index(): a two-way player has two rows per fg_id.
    sv27 = players_on.groupby("fg_id")["SV"].max() if "SV" in players_on else None
    # Same exch/meta for both calls isolates the replacement-level effect.
    v28_pooled_repl = value_2028(exch_on, meta_on, sv27, positional=False)
    v28_position_repl = value_2028(exch_on, meta_on, sv27, positional=True)

    ss_ids = load_position_eligibility()["SS"]
    m = v28_pooled_repl[["fg_id", "redraft_value_2028"]].merge(
        v28_position_repl[["fg_id", "redraft_value_2028"]],
        on="fg_id", suffixes=("_pooled", "_position"))
    ss_rows = m[m["fg_id"].isin(ss_ids) & (m["redraft_value_2028_pooled"] > 1.0)]
    assert len(ss_rows) > 0, "test needs at least one non-floored rostered-caliber shortstop"
    # SS replacement sits above pooled, so it must strictly lower every affected SS.
    assert (ss_rows["redraft_value_2028_position"]
           < ss_rows["redraft_value_2028_pooled"]).all()


# --- Monte Carlo standings simulator (docs/SESSION-LOG.md Phase 5) --------------

def _check_finish_odds_identities(out):
    finish_cols = [f"p_finish_{p}" for p in range(1, C.PAYOUT_SPOTS + 1)]
    assert out["p_money"].to_numpy() == pytest.approx(out[finish_cols].sum(axis=1).to_numpy())
    assert ((out[finish_cols + ["p_money"]] >= 0).all().all())
    assert ((out[finish_cols + ["p_money"]] <= 1).all().all())
    for col in finish_cols:
        assert out[col].sum() == pytest.approx(1.0, abs=1e-9)


def test_finish_odds_identities_and_leader_favored(board):
    """p_money == sum of per-place columns, every probability in [0,1], each
    place column sums to 1 across teams; and the real standings leader must
    beat the last-place team (a real head start dominates ROS noise)."""
    b, _, _ = board
    out = simulate_finish_odds(b, B=500, seed=0)
    assert len(out) == C.N_TEAMS
    _check_finish_odds_identities(out)
    leader = out.loc[out["current_points"].idxmax()]
    last = out.loc[out["current_points"].idxmin()]
    assert leader["p_money"] > last["p_money"]


def test_finish_odds_seed_and_zero_shock_are_deterministic(board):
    """A fixed seed is byte-identical run to run (the JS port's reference
    must be stable), and shock_scale=0 puts the same team in each place in
    literally every draw."""
    b, _, _ = board
    a = simulate_finish_odds(b, B=300, seed=7)
    c = simulate_finish_odds(b, B=300, seed=7)
    assert a["p_money"].equals(c["p_money"])
    out = simulate_finish_odds(b, B=50, seed=0, shock_scale=0.0)
    assert (out["p_finish_1"].isin([0.0, 1.0])).all()
    assert out["p_finish_1"].sum() == pytest.approx(1.0)


def test_swap_changes_the_odds_in_the_expected_direction(board):
    """Moving a valuable player raises the acquiring team's odds and lowers
    the sender's. Uses the two teams with p_money closest to 0.5 -- with
    PAYOUT_SPOTS=4 the top teams are already at a ceiling."""
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


# --- Stage 3: 2027 keeper-core finish odds (docs/SESSION-LOG.md Phase 5) --------

def test_keeper_finish_odds_identities_and_reassignment(board, fa):
    """Same identity checks for the 2027 keeper-core simulator, and moving a
    keeper via `keeper_override` must raise the receiving team's odds and
    lower the sending team's."""
    from klab.standings_sim import simulate_keeper_finish_odds
    b, _, meta = board
    repl = meta["replacement_rp"]
    before = simulate_keeper_finish_odds(b, fa, repl, B=600, seed=5)
    _check_finish_odds_identities(before)

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
