"""Build the single-file HTML app.

Everything the interface needs is serialised out of `klab.api.snapshot()` and
inlined into one self-contained HTML document -- no server, no build step, no
network. Open the file and it works, including on a phone.

    PYTHONPATH=. python3 scripts/build_app.py

The design decision worth flagging: the rest-of-season category lines ship with
the payload, so the browser can re-run the win-now standings calculation for an
arbitrary trade. That is the only screen that genuinely needs to recompute, and
it is the same arithmetic as `trade.win_now_delta`, ported to JavaScript.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from klab import config as C
from klab.api import snapshot
from klab.denoms import team_baselines
from klab.io import load_standings_long
from klab.trade import ros_lines, standings_points
from klab.project import RELIABILITY, REL_MAX

# The three forks PROJECTION_BASIS can take (klab/config.py). Shipped as
# three parallel payloads rather than one, so the app can let a user flip
# between them instead of hiding the model's biggest fork behind a rebuild.
# See out/ROADMAP.md 2.2, out/FINDINGS.md #42.
BASES = ["blend", "projection", "actuals"]

# Columns carried into the payload, in order. Kept explicit rather than
# "everything" so the file stays small and the schema is reviewable.
PLAYER_COLS = [
    "fg_id", "name", "team", "role", "il", "position", "mlb_team",
    "salary", "contract", "keeper_status", "keeper_cost", "years_controlled",
    "keepable", "extension_used", "extension_option", "extension_years", "keep_2027",
    "roto_points", "rp_above_repl", "redraft_value", "keep_value",
    "roto_points_ft", "redraft_value_ft", "upside_ft", "upside_kind",
    "redraft_value_2028", "surplus_redraft",
    "surplus_y2027", "surplus_y2028", "surplus_y2029", "surplus_multiyear",
    "pt_scale", "pt_scale_kind",
    "value_lo", "value_hi", "surplus_lo", "surplus_hi", "p_surplus_positive",
    "PA", "AB", "H", "HR", "R", "RBI", "SB", "AVG",
    "IP", "W", "SV", "K", "ER", "BB", "ERA", "WHIP",
] + [f"rp_{c}" for c in C.CATS]

ROS_COLS = ["AB", "H", "HR", "R", "RBI", "SB",
            "IP", "W", "SV", "K", "ER", "BB", "H_allowed"]

BOOTSTRAP_DRAWS = 1000      # ~11s; the bands are stable well below this
FINISH_SIM_DRAWS = 2000     # ~10s per ROS basis, x3 bases -- klab/standings_sim.py
KEEPER_FINISH_SIM_DRAWS = 800   # ~15-20s per PROJECTION_BASIS, x3 bases -- higher
                                # per-draw cost than FINISH_SIM_DRAWS (see
                                # _keeper_finish_odds()), so fewer draws
FINISH_SHOCK_SCALE = 0.35   # klab.standings_sim.DEFAULT_SHOCK_SCALE, made explicit here
                            # so the payload's "finish_sim" metadata can't drift from
                            # what was actually run


def _round(v):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return round(float(v), 4)
    return str(v)


def _rows(df: pd.DataFrame, cols: list[str]) -> list[list]:
    d = df.reindex(columns=cols)
    return [[_round(v) for v in rec] for rec in d.itertuples(index=False, name=None)]


ROS_BASES = ["ros", "prorated", "blend"]


def _keeper_standings_2027(board: pd.DataFrame, fa: pd.DataFrame,
                           replacement_rp: float) -> list[dict]:
    """2027 standings projected from each team's CURRENT keeper set alone,
    with every roster slot NOT yet occupied by a keeper filled at
    replacement level. Answers "how strong is my keeper core on its own,"
    not "who will actually win the 2027 auction" -- this deliberately does
    not attempt to forecast what any team will do with its remaining
    budget, which differs team to team and isn't something this model
    predicts anywhere else either.

    Replacement line is a 15-player band average around `replacement_rp`
    (roto points), not the single nearest player: the first version used
    the single closest match and it happened to land on a closer, whose
    ~25 saves then got added to EVERY team's empty pitcher slots -- saves
    are valuable enough that a mediocre closer clears replacement level
    easily on overall roto_points even though he's a poor stand-in for a
    generic replacement-level pitcher. Averaging a band smooths that out.
    """
    from klab.trade import standings_points
    hit_cols = ["AB", "H", "HR", "R", "RBI", "SB"]
    # "H" for a pitcher IS hits allowed on the full-season board's own
    # native columns (unlike ros_lines()'s merged schema, which renames to
    # H_allowed to dodge a join collision -- no such collision here).
    pit_cols = ["IP", "W", "SV", "K", "ER", "BB", "H"]

    pool = pd.concat([board, fa], ignore_index=True)

    def repl_line(p, cols, n=15):
        d = (p["roto_points"] - replacement_rp).abs()
        return p.loc[d.nsmallest(n).index, cols].mean()

    repl_hit = repl_line(pool[pool["role"] != "PIT"], hit_cols)
    repl_pit = repl_line(pool[pool["role"] == "PIT"], pit_cols)

    kept = board[board["keep_2027"]]
    rows = []
    for team, grp in kept.groupby("team"):
        is_pit = grp["role"] == "PIT"
        empty_hit = max(C.N_HIT_SLOTS - int((~is_pit).sum()), 0)
        empty_pit = max(C.N_PIT_SLOTS - int(is_pit.sum()), 0)

        h = {c: float(grp.loc[~is_pit, c].sum()) + empty_hit * float(repl_hit[c])
             for c in hit_cols}
        p = {c: float(grp.loc[is_pit, c].sum()) + empty_pit * float(repl_pit[c])
             for c in pit_cols}

        rows.append({
            "team": team, "n_keep": int(len(grp)),
            "empty_slots_filled": int(empty_hit + empty_pit),
            "R": h["R"], "HR": h["HR"], "RBI": h["RBI"], "SB": h["SB"],
            "AVG": h["H"] / h["AB"] if h["AB"] else 0.0,
            "W": p["W"], "SV": p["SV"], "K": p["K"],
            "ERA": p["ER"] * 9.0 / p["IP"] if p["IP"] else 0.0,
            "WHIP": (p["BB"] + p["H"]) / p["IP"] if p["IP"] else 0.0,
        })

    wide = pd.DataFrame(rows).set_index("team")
    pts = standings_points(wide[C.CATS])
    out = []
    for team in wide.index:
        row = {"team": team, "points": _round(pts.loc[team, "TOTAL"]),
              "n_keep": _round(wide.loc[team, "n_keep"]),
              "empty_slots_filled": _round(wide.loc[team, "empty_slots_filled"])}
        row.update({c: _round(wide.loc[team, c]) for c in C.CATS})
        out.append(row)
    return sorted(out, key=lambda r: -r["points"])


def _historical_standings() -> dict:
    """Final standings for every completed season on record (2022-2025;
    2026 is still live and already has its own payload section), keyed by
    season. Basis-invariant -- history doesn't change with either toggle --
    so computed once, not nested in _variant_payload().

    Team names are normalised to the CURRENT franchise name via
    data/franchise_map.csv, not shown under whatever name a franchise was
    playing under that year: this league has renamed teams five times
    (e.g. "Moben" -> "Orange and Black Attack"), and the point of a
    history view is seeing one franchise's arc across that, not making a
    viewer mentally track name changes themselves."""
    fm = pd.read_csv(C.DATA / "franchise_map.csv")
    current_name = fm[fm["last_season"] == 2026].set_index("franchise_id")["team_name"]
    name_map = {row["team_name"]: current_name.get(row["franchise_id"], row["team_name"])
               for _, row in fm.iterrows()}

    st = load_standings_long()
    out = {}
    for season in sorted(s for s in st["season"].unique() if s < 2026):
        wide = st[st["season"] == season].pivot(index="team", columns="category",
                                                 values="total")
        wide.index = wide.index.map(lambda t: name_map.get(t, t))
        wide = wide.groupby(level=0).first()
        pts = standings_points(wide[C.CATS])
        ranked = pts.sort_values("TOTAL", ascending=False)
        rows = []
        for team, p in ranked.iterrows():
            row = {"team": team, "points": _round(p["TOTAL"])}
            row.update({c: _round(wide.loc[team, c]) for c in C.CATS})
            rows.append(row)
        out[int(season)] = rows
    return out


def _ros_variants(fg_ids) -> dict:
    """Alternates to the default 2026 rest-of-season signal
    (klab.trade.ros_lines()), for the Standings-tab / Trade-tab win-now
    toggle. Computed ONCE, not per PROJECTION_BASIS variant -- unlike
    `_auction_estimates()`, nothing here touches a dollar value, so there's
    no basis-consistency hazard to guard against (see out/FINDINGS.md #45).
    Keyed by fg_id (string) then column, so the browser can overwrite a
    board row's `ros_*` fields in place when the toggle switches, the same
    pattern setBasis() already uses for the projection-basis payload."""
    from klab.trade import ros_lines_for_basis
    out = {}
    for basis in ROS_BASES:
        r = ros_lines_for_basis(basis).set_index("fg_id").reindex(
            columns=ROS_COLS, fill_value=0.0)
        d = {}
        for fid in fg_ids:
            row = r.loc[fid] if fid in r.index else None
            d[str(fid)] = {c: (_round(row[c]) if row is not None else 0.0)
                          for c in ROS_COLS}
        out[basis] = d
    return out


def _ros_values(board: pd.DataFrame, fa: pd.DataFrame, D: dict, base: dict,
                replacement_rp: float) -> dict:
    """ros_value_over_replacement (out/FINDINGS.md #34) for every player,
    under each of the three ROS bases -- for the Keeper Board tab's
    rest-of-2026 value column.

    Computed inside THIS process's D/base/replacement_rp on purpose:
    `ros_value_over_replacement` mixes a ROS-basis-dependent input (which
    ros_* line -- see #45) with a PROJECTION_BASIS-dependent one (the
    denominators/baseline/replacement level that price it). Getting a
    number that's consistent under an arbitrary combination of BOTH
    toggles means nesting this inside each per-PROJECTION_BASIS subprocess
    (see `_variant_payload()`), not computing it once and reusing it --
    the same reasoning `_auction_estimates()` already applies for a
    different pair of toggles."""
    from klab.trade import ros_lines_for_basis, ros_value_over_replacement
    id_role = pd.concat([board[["fg_id", "role"]], fa[["fg_id", "role"]]],
                        ignore_index=True).drop_duplicates("fg_id")
    out = {}
    for basis in ROS_BASES:
        ros = ros_lines_for_basis(basis)
        p = id_role.merge(ros, on="fg_id", how="left")
        for c in ["PA"] + ROS_COLS:
            p[c] = p[c].fillna(0.0)
        rv = ros_value_over_replacement(p, D, base, replacement_rp)
        out[basis] = {str(int(fid)): _round(val) for fid, val in
                     zip(rv["fg_id"], rv["ros_value_over_replacement"])}
    return out


def _finish_odds(board: pd.DataFrame, B: int = FINISH_SIM_DRAWS,
                 shock_scale: float = FINISH_SHOCK_SCALE) -> dict:
    """Monte Carlo in-the-money-finish odds (klab.standings_sim,
    out/ROADMAP.md Phase 5), one run per ROS basis, for the Contention
    tab's precomputed current-roster view. Payout structure is
    50%/25%/15%/breakeven for 1st-4th (C.PAYOUT_SPOTS/C.PAYOUT_SHARE) --
    corrected 2026-08-14 from an earlier, wrong top-2-only build.

    Computed ONCE, not nested per PROJECTION_BASIS the way `_ros_values()`
    is: the simulator only touches rest-of-season stat lines and the
    already-realized 2026 standings, neither of which PROJECTION_BASIS
    affects -- that toggle is strictly about 2027 dollar valuation, and
    this feature has nothing to do with 2027. Any of the positional/basis
    board variants works as the roster source (team/fg_id don't change
    across those toggles, only dollar VALUES do), so the ambient snapshot's
    board is fine."""
    from klab.standings_sim import simulate_finish_odds
    out = {}
    for basis in ROS_BASES:
        odds = simulate_finish_odds(board, ros_basis=basis, B=B, shock_scale=shock_scale)
        finish_cols = [f"p_finish_{p}" for p in range(1, C.PAYOUT_SPOTS + 1)]
        out[basis] = {row["team"]: {
            **{c: _round(row[c]) for c in finish_cols},
            "p_money": _round(row["p_money"]), "current_points": _round(row["current_points"]),
        } for _, row in odds.iterrows()}
    return out


def _keeper_finish_odds(board: pd.DataFrame, fa: pd.DataFrame,
                        replacement_rp: float, B: int = KEEPER_FINISH_SIM_DRAWS,
                        shock_scale: float = FINISH_SHOCK_SCALE) -> dict:
    """Monte Carlo in-the-money-finish odds for each team's CURRENT KEEPER
    SET in a hypothetical 2027 season (klab.standings_sim's Stage 3, out/
    ROADMAP.md Phase 5) -- the Contention tab's "2027 (keeper core)" view.

    Computed INSIDE the per-PROJECTION_BASIS subprocess, same as
    `_keeper_standings_2027()` right above it and unlike `_finish_odds()`
    above: which players are flagged `keep_2027` depends on PROJECTION_BASIS
    (~17% of keep/cut calls move with it, out/FINDINGS.md #42), so this
    feature -- unlike the rest-of-2026 simulator, which only touches
    already-realized standings and rest-of-season lines neither of which
    PROJECTION_BASIS affects -- genuinely needs one run per basis, x3 total.
    Fewer draws than `_finish_odds()`'s (`KEEPER_FINISH_SIM_DRAWS` <
    `FINISH_SIM_DRAWS`): this one's per-draw cost is ~4x higher (a
    DataFrame rebuild + groupby every draw, not a single merge), and three
    basis-subprocess runs of it already add real build time."""
    from klab.standings_sim import simulate_keeper_finish_odds
    odds = simulate_keeper_finish_odds(board, fa, replacement_rp, B=B, shock_scale=shock_scale)
    finish_cols = [f"p_finish_{p}" for p in range(1, C.PAYOUT_SPOTS + 1)]
    return {row["team"]: {
        **{c: _round(row[c]) for c in finish_cols},
        "p_money": _round(row["p_money"]),
    } for _, row in odds.iterrows()}


def _auction_estimates(board: pd.DataFrame, fa: pd.DataFrame) -> dict:
    """Comp-based next-auction price estimate for every player with a
    projection, keyed by "{fg_id}_{role}" (fg_id as an int -- JSON object
    keys are always strings). Computed per-basis, not once and reused:
    `regression_fair_value` inside `estimate_auction_price()` is the
    player's own `redraft_value`, which is exactly the number the basis
    selector changes -- pinning this panel to one basis while the rest of
    the page follows the selector would reproduce the same inconsistency
    out/FINDINGS.md #42 already found and fixed for team/constant
    aggregates.

    Keyed on role as well as fg_id (not fg_id alone) because a true
    two-way player (config.TWO_WAY_SPLIT_NAMES) has two rows sharing one
    fg_id from 2027 on -- a fg_id-only key would let his second row
    silently overwrite the first with an identical (wrong-role) estimate,
    since `estimate_auction_price()` used to always resolve a name to its
    first matching row. Passing `role` through fixes that at the source;
    the key change here keeps both estimates addressable in the payload.
    Everyone else still has exactly one role per fg_id, so this is a
    no-op widening for them.

    Deliberately still a separate, non-integrated tool per
    klab/auction_estimator.py's own docstring -- this only *displays* its
    output next to the regression fair value, it does not feed back into
    redraft_value or any keep/cut decision anywhere in klab/."""
    from klab.auction_estimator import estimate_auction_price
    players = pd.concat([board, fa], ignore_index=True)
    players = players[players["roto_points"] > 0]
    out = {}
    for name, fg_id, role in zip(players["name"], players["fg_id"], players["role"]):
        try:
            est = estimate_auction_price(name, players, k=15, role=role)
        except Exception:
            continue   # ambiguous/unresolved name -- skip rather than fail the whole build
        comps = est["comps"].head(8).to_dict("records")
        out[f"{int(fg_id)}_{role}"] = {
            "fair": _round(est["regression_fair_value"]),
            "lo": _round(est["comp_adjusted_low"]),
            "mid": _round(est["comp_adjusted_mid"]),
            "hi": _round(est["comp_adjusted_high"]),
            "n_comps": est["n_comps"],
            "fallback": est["fallback_to_full_role"],
            "n_same_pos": est["n_same_position_available"],
            # _round() on every field, not just the numeric ones: a handful
            # of historical auction_sample.csv rows have a missing `pos`,
            # which pandas represents as float('nan') -- not a string, and
            # not caught unless it goes through the same NaN-safe helper
            # everything else does. json.dumps(allow_nan=False) surfaced it
            # immediately (673 players, several dozen with a NaN comp `pos`).
            "first_timer": bool(est["target_is_first_timer"]),
            "tenure_filtered": bool(est["tenure_filtered"]),
            "comps": [{"season": _round(c["season"]), "player": _round(c["player"]),
                       "team": _round(c["team"]), "salary": _round(c["salary"]),
                       "pos": _round(c["pos"]), "premium_pct": _round(c["premium_frac"] * 100),
                       "appearances": _round(c["appearances_to_date"])}
                      for c in comps],
        }
    return out


def _board_fa_teams_constants(positional: bool, ros: pd.DataFrame, ros_cols: list,
                              pos_map: pd.Series, team_map: pd.Series) -> dict:
    """Board, free agents, team summaries and constants for one
    `positional` setting (out/FINDINGS.md #52), within the PROJECTION_BASIS
    ambient in this process. Factored out of `_variant_payload()` so it can
    be called twice -- once per positional-adjustment setting -- without
    duplicating the ros/position merge logic."""
    s = snapshot(positional=positional)
    board = s.board.merge(ros, on="fg_id", how="left")
    board[ros_cols] = board[ros_cols].fillna(0.0)
    board["position"] = board["fg_id"].map(pos_map).fillna("?")
    board["mlb_team"] = board["fg_id"].map(team_map).fillna("?")
    # Bands come from resampling the team-seasons the denominators are fit on,
    # so every dollar figure can be shown as a range instead of a point.
    # NOT positional-aware (a documented scope limit, not an oversight): the
    # bootstrap describes denominator uncertainty, which doesn't change with
    # replacement level, and threading `positional` through it for exactness
    # would double an already-expensive 1000-draw resample for a band that
    # wouldn't move much anyway.
    from klab.uncertainty import bootstrap_bands
    board = board.merge(bootstrap_bands(B=BOOTSTRAP_DRAWS).reset_index(),
                        on=["fg_id", "role"], how="left")

    fa = s.free_agents.copy()
    fa["team"] = "(free agent)"
    fa["keep_2027"] = False
    fa["keepable"] = True
    fa["extension_used"] = False
    fa["keeper_status"] = fa.get("acquisition", "free agent")
    fa["il"] = False
    fa = fa[fa["roto_points"] > 0].nlargest(400, "roto_points")
    fa = fa.merge(ros, on="fg_id", how="left")
    fa[ros_cols] = fa[ros_cols].fillna(0.0)
    fa["position"] = fa["fg_id"].map(pos_map).fillna("?")
    fa["mlb_team"] = fa["fg_id"].map(team_map).fillna("?")

    cols = PLAYER_COLS + ros_cols
    return {
        "cols": cols,
        "board": _rows(board, cols),
        "fa": _rows(fa, cols),
        "teams_raw": json.loads(s.teams.reset_index().to_json(orient="records")),
        "constants": {k: _round(v) if not isinstance(v, dict) else
                      {kk: _round(vv) for kk, vv in v.items()}
                      for k, v in s.constants.items()},
    }


def _variant_payload() -> dict:
    """Everything for whichever PROJECTION_BASIS is ambient in THIS process
    (klab/config.py's PROJECTION_BASIS, overridable via the
    KLAB_PROJECTION_BASIS env var), under BOTH positional-adjustment
    settings (out/FINDINGS.md #52).

    Deliberately does not try to flip C.PROJECTION_BASIS mid-process to get
    all three bases from one run: `klab.io.cached()` memoises every loader
    on its function arguments only, not on this global, so a second basis
    computed in the same process would silently return the first basis's
    cached intermediate results. See `_basis_variants()`, which runs this
    function in three separate fresh processes instead, and
    out/FINDINGS.md #42 for the version of this bug that was actually
    shipped and caught (klab/trade_finder.py, a different memoisation
    hazard, same root cause: process-global state and per-arg caching don't
    mix). `positional` doesn't have that hazard (`snapshot()`/`build_board()`
    take it as a real argument, correctly cached per-value), so both
    settings are computed in-process here rather than needing their own
    subprocess split too.

    Auction estimates, ROS values, and the 2027 keeper-standings projection
    are NOT positional-aware -- a deliberate scope limit, not an oversight.
    They're built once, off the positional=False board/fa only, same as
    every other feature this session that's stayed pinned to the pooled
    board for cost reasons (#43, #47, #49 all note the same tradeoff for
    their own second toggle)."""
    from klab.board import build_board as _build_board_raw
    _, _, _meta = _build_board_raw()   # positional=False; _ros_values()/_keeper_standings_2027() stay pooled
    # Prefix EVERY ros column, not just the ones the win-now maths uses.
    # `ros_lines()` also carries PA, which silently collided with the board's
    # projected PA and turned it into PA_x/PA_y -- the drawer showed a dash.
    ros = ros_lines()
    ros = ros.rename(columns={c: f"ros_{c}" for c in ros.columns if c != "fg_id"})
    ros_cols = [f"ros_{c}" for c in ROS_COLS]
    assert not (set(ros.columns) - {"fg_id"}) & set(PLAYER_COLS), "column collision"

    # Defensive position, for the Intuition tab's player tooltips (#50) --
    # NOT the same thing as the C/SS eligibility driving positional
    # adjustment (that's load_position_eligibility(), used inside
    # value_players() itself). This is the broader, sparser auction-history
    # lookup, still just for display; "?" where there's no draft record.
    from klab.keeper import position_map
    pos_map = position_map()
    # Real MLB team, display only, never used in valuation (klab/io.py's
    # mlb_team_map()) -- distinct from `board["team"]`, which is the CBS
    # fantasy roster.
    from klab.io import mlb_team_map
    team_map = mlb_team_map()

    variants = {pos: _board_fa_teams_constants(pos, ros, ros_cols, pos_map, team_map)
               for pos in (False, True)}
    default = variants[False]

    # _auction_estimates()/_ros_values()/_keeper_standings_2027() need the
    # actual DataFrames, not the already-serialised row arrays -- rebuild
    # the positional=False board/fa once more rather than threading the
    # pre-serialisation DataFrames out of _board_fa_teams_constants().
    s = snapshot(positional=False)
    board_raw = s.board.merge(ros, on="fg_id", how="left")
    board_raw[ros_cols] = board_raw[ros_cols].fillna(0.0)
    board_raw["position"] = board_raw["fg_id"].map(pos_map).fillna("?")
    fa_raw = s.free_agents.copy()
    fa_raw["team"] = "(free agent)"
    fa_raw = fa_raw[fa_raw["roto_points"] > 0].nlargest(400, "roto_points")
    fa_raw = fa_raw.merge(ros, on="fg_id", how="left")
    fa_raw[ros_cols] = fa_raw[ros_cols].fillna(0.0)

    return {
        "cols": default["cols"],
        "board": default["board"],
        "fa": default["fa"],
        "teams_raw": default["teams_raw"],
        "constants": default["constants"],
        "positional_variants": {"off": variants[False], "on": variants[True]},
        "auction_estimates": _auction_estimates(board_raw, fa_raw),
        "ros_values": _ros_values(board_raw, fa_raw, _meta["denominators"], _meta["baseline"],
                                  _meta["replacement_rp"]),
        "keeper_standings_2027": _keeper_standings_2027(board_raw, fa_raw, _meta["replacement_rp"]),
        "keeper_finish_odds": _keeper_finish_odds(board_raw, fa_raw, _meta["replacement_rp"]),
    }


def _basis_variants() -> dict:
    """_variant_payload() under all three PROJECTION_BASIS settings. The
    ambient process computes its own basis in-process (typically "blend",
    the default); the other two run in fresh `python3 build_app.py
    --variant` subprocesses via an env-var override, each with its own
    empty caches, so there's no risk of one basis's cached loaders leaking
    into another's numbers."""
    out = {}
    for basis in BASES:
        if basis == C.PROJECTION_BASIS:
            out[basis] = _variant_payload()
            continue
        env = {**os.environ, "KLAB_PROJECTION_BASIS": basis}
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--variant"],
                           env=env, capture_output=True, text=True, check=True)
        out[basis] = json.loads(r.stdout)
    return out


def build_payload() -> dict:
    variants = _basis_variants()
    default = C.PROJECTION_BASIS

    s = snapshot()   # ambient basis; standings and trade suggestions don't
                      # vary by basis, so one snapshot covers all three
    pts_2026 = s.standings["points_2026"].to_dict()
    for v in variants.values():
        # teams_raw (positional=False) and positional_variants["off"]["teams_raw"]
        # are the same list object (see _variant_payload()), so this loop
        # already covers "off" once -- but positional_variants["on"] is a
        # separate dict and needs its own pass, or its League tab would show
        # blank points_2026 whenever positional adjustment is toggled on.
        for t in v["teams_raw"]:
            t["points_2026"] = pts_2026.get(t["team"])
        for t in v["positional_variants"]["on"]["teams_raw"]:
            t["points_2026"] = pts_2026.get(t["team"])

    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category",
                                         values="total")
    b26 = team_baselines([2026]).iloc[0]

    # Precomputed separately (scripts/build_trade_suggestions.py) -- a real
    # search across 45 team pairs is a couple minutes, not a build-step cost.
    # Missing file -> empty list rather than a crash, so a normal build_app
    # run still works if suggestions haven't been (re)generated yet.
    sugg_path = C.OUT / "trade_suggestions.json"
    trade_suggestions = json.loads(sugg_path.read_text()) if sugg_path.exists() else []

    fid_i = variants[default]["cols"].index("fg_id")
    fg_ids = {r[fid_i] for r in variants[default]["board"] + variants[default]["fa"]}
    ros_variants = _ros_variants(fg_ids)

    return {
        "built": date.today().isoformat(),
        "projection_basis": default,
        # Everything below marked (default basis) is a straight alias into
        # basis_variants[default] -- kept as top-level keys so every screen
        # that predates the selector keeps working unchanged; the selector
        # itself (app/template.html's setBasis()) is the only thing that
        # reads basis_variants directly.
        "basis_variants": {b: {"cols": v["cols"], "board": v["board"], "fa": v["fa"],
                               "teams": v["teams_raw"], "constants": v["constants"],
                               "auction_estimates": v["auction_estimates"],
                               "ros_values": v["ros_values"],
                               "keeper_standings_2027": v["keeper_standings_2027"],
                               "keeper_finish_odds": v["keeper_finish_odds"],
                               "positional_variants": v["positional_variants"]}
                           for b, v in variants.items()},
        "trade_suggestions": trade_suggestions,
        "ros_variants": ros_variants,
        "ros_basis_default": "ros",
        "band": {"lo": 10, "hi": 90, "draws": BOOTSTRAP_DRAWS},
        "cats": C.CATS,
        "neg_cats": sorted(C.NEG_CATS),
        "hit_cats": C.HIT_CATS,
        "pit_cats": C.PIT_CATS,
        "cols": variants[default]["cols"],                 # (default basis)
        "board": variants[default]["board"],                # (default basis)
        "fa": variants[default]["fa"],                      # (default basis)
        "teams": variants[default]["teams_raw"],             # (default basis)
        "auction_estimates": variants[default]["auction_estimates"],  # (default basis)
        "ros_values": variants[default]["ros_values"],      # (default proj basis; keyed by [rosBasis][fg_id])
        "keeper_standings_2027": variants[default]["keeper_standings_2027"],  # (default basis)
        "keeper_finish_odds": variants[default]["keeper_finish_odds"],  # (default basis)
        "standings": json.loads(s.standings.reset_index().to_json(orient="records")),
        "history_standings": _historical_standings(),
        "finish_odds": _finish_odds(s.board, B=FINISH_SIM_DRAWS),
        "finish_sim": {"draws": FINISH_SIM_DRAWS, "shock_scale": FINISH_SHOCK_SCALE,
                      "payout_spots": C.PAYOUT_SPOTS, "payout_share": C.PAYOUT_SHARE},
        "keeper_finish_sim": {"draws": KEEPER_FINISH_SIM_DRAWS, "shock_scale": FINISH_SHOCK_SCALE},
        # For the client-side port of klab.standings_sim's jitter (out/
        # ROADMAP.md Phase 5) -- ships the same numbers the Python
        # reference uses rather than hand-duplicating them in JS, so the
        # two can't silently drift on a future RELIABILITY refit.
        "reliability": {k: _round(v) for k, v in RELIABILITY.items()},
        "reliability_max": _round(REL_MAX),
        "cur_totals": {t: {c: _round(cur.loc[t, c]) for c in C.CATS}
                       for t in cur.index},
        "base26": {"AB": _round(b26["team_AB"]), "IP": _round(b26["team_IP"])},
        "constants": variants[default]["constants"],        # (default basis)
        "settings": {k: _round(v) if not isinstance(v, list) else v
                     for k, v in s.settings.items()},
        "league": {
            "n_teams": C.N_TEAMS, "budget": C.BUDGET,
            "min_keepers": C.MIN_KEEPERS, "max_keepers": C.MAX_KEEPERS,
            "extension_cost": C.EXTENSION_COST,
            "extension_max_years": C.EXTENSION_MAX_YEARS,
            "contention_weight": C.CONTENTION_WEIGHT,
        },
    }


def _selftest(payload: dict) -> None:
    """The JS win-now maths must reproduce `standings_points` on the current
    rosters. Verify the Python side of that identity here so a mismatch in the
    browser is unambiguously a JavaScript bug."""
    idx = {c: i for i, c in enumerate(payload["cols"])}
    cur = pd.DataFrame(payload["cur_totals"]).T
    agg = {}
    for r in payload["board"]:
        t = r[idx["team"]]
        d = agg.setdefault(t, dict.fromkeys(ROS_COLS, 0.0))
        for c in ROS_COLS:
            d[c] += r[idx[f"ros_{c}"]] or 0.0
    add = pd.DataFrame(agg).T.reindex(cur.index).fillna(0.0)
    ab0, ip0 = payload["base26"]["AB"], payload["base26"]["IP"]
    w = pd.DataFrame(index=cur.index)
    for c in ["R", "HR", "RBI", "SB", "W", "SV", "K"]:
        w[c] = cur[c] + add[c]
    w["AVG"] = (cur["AVG"] * ab0 + add["H"]) / (ab0 + add["AB"])
    w["ERA"] = (cur["ERA"] * ip0 / 9.0 + add["ER"]) * 9.0 / (ip0 + add["IP"])
    w["WHIP"] = (cur["WHIP"] * ip0 + add["BB"] + add["H_allowed"]) / (ip0 + add["IP"])
    pts = standings_points(w[C.CATS])
    assert abs(pts["TOTAL"].sum() - C.N_TEAMS * (C.N_TEAMS + 1) / 2 * len(C.CATS)) < 1e-6
    print(f"  self-test: projected standings leader = "
          f"{pts['TOTAL'].idxmax()} ({pts['TOTAL'].max():.1f} pts)")


def _reference() -> dict:
    """Ground truth for `app/verify.mjs`: what pandas says about one real
    trade. The browser re-implements the win-now standings calculation in
    JavaScript, so the two must be diffed rather than assumed equal."""
    from klab.trade import evaluate_trade
    s = snapshot()
    # Deliberately avoids unkeepable players: their `surplus_multiyear` is NaN
    # by design, which is correct on the board and useless as a reference value.
    a_sends, b_sends = ["Cade Smith", "Nico Hoerner"], ["Mike Trout", "Byron Buxton"]
    res = evaluate_trade(s.board, "Pookie 2.0", "All-Stars", a_sends, b_sends,
                         usd_per_point=s.constants["usd_per_roto_point_auction"])
    w = res["win_now"]
    return {
        "team_a": "Pookie 2.0", "team_b": "All-Stars",
        "a_sends": a_sends, "b_sends": b_sends,
        "points_before": {k: round(v, 6) for k, v in w["points_before"].items()},
        "points_after": {k: round(v, 6) for k, v in w["points_after"].items()},
        "a_dS": round(res["a"]["d_surplus"], 6),
        "b_dS": round(res["b"]["d_surplus"], 6),
        "a_dMY": round(res["a"]["d_surplus_multiyear"], 6),
        "a_dP": round(res["a"]["d_standings_points_2026"], 6),
        "b_dP": round(res["b"]["d_standings_points_2026"], 6),
    }


def main() -> None:
    payload = build_payload()
    _selftest(payload)
    ref = C.OUT / "app_reference.json"
    ref.write_text(json.dumps(_reference(), indent=1))
    tpl = (Path(__file__).resolve().parents[1] / "app" / "template.html").read_text()
    blob = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    html = tpl.replace("/*__DATA__*/null", blob)
    out = C.OUT / "keeper_lab.html"
    out.write_text(html)
    print(f"  {len(payload['board'])} rostered + {len(payload['fa'])} free agents")
    print(f"  wrote {out}  ({len(html)/1024:.0f} KB)")
    print(f"  wrote {ref}  -- check the browser with: node app/verify.mjs")


if __name__ == "__main__":
    if "--variant" in sys.argv:
        # Worker mode for _basis_variants(): print ONLY the JSON payload to
        # stdout, so the parent process's subprocess.run(capture_output=True)
        # can parse it directly. KLAB_PROJECTION_BASIS is read by
        # klab/config.py at import time.
        print(json.dumps(_variant_payload(), separators=(",", ":"), allow_nan=False))
    else:
        main()
