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

# PROJECTION_BASIS forks, shipped as three parallel payloads so the app can
# flip between them (docs/SESSION-LOG.md 2.2, docs/FINDINGS.md #42).
BASES = ["blend", "projection", "actuals"]

# Columns carried into the payload, in order. Kept explicit rather than
# "everything" so the file stays small and the schema is reviewable.
PLAYER_COLS = [
    "fg_id", "name", "team", "role", "il", "position", "mlb_team",
    "salary", "contract", "keeper_status", "keeper_cost",
    "keepable", "extension_used", "extension_option", "extension_years", "keep_2027",
    "roto_points", "roto_2026", "roto_move", "rp_above_repl", "redraft_value", "keep_value",
    # production_value is redraft_value renamed; market_price is the separate
    # auction-cost quantity, fitted since FINDINGS #57 (held-out MAE 5.76).
    "production_value", "market_price", "market_price_lo", "market_price_hi",
    "roto_points_ft", "redraft_value_ft", "keep_value_ft", "upside_ft", "upside_kind",
    "redraft_value_2028",
    "surplus_y2027", "surplus_y2028", "surplus_y2029", "surplus_multiyear",
    "pt_scale", "pt_scale_kind",
    "value_lo", "value_hi", "surplus_lo", "surplus_hi", "p_surplus_positive",
    "PA", "AB", "H", "HR", "R", "RBI", "SB", "AVG",
    "IP", "W", "SV", "K", "ER", "BB", "ERA", "WHIP",
] + [f"rp_{c}" for c in C.CATS] + [f"rp_{c}_26" for c in C.CATS] \
  + [f"rp_{c}_ft" for c in C.CATS]

ROS_COLS = ["AB", "H", "HR", "R", "RBI", "SB",
            "IP", "W", "SV", "K", "ER", "BB", "H_allowed"]

# The exchange-fit dropdown (FINDINGS #82): alternative estimators of the
# $-per-roto-point rate, shipped as per-row overlays of the keep-scale columns
# rather than full board copies (the columns below are the only ones that
# move). "keeper_adjusted" is the shipped default and needs no overlay. The
# two non-linear members failed the LOSO and rewound-backtest gates and are
# deliberately absent (docs/FINDINGS.md #82).
EXCHANGE_OPTIONS = ["pick_level", "pooled_2426", "median_two_stage"]
EXCH_COLS = ["keep_value", "keep_value_ft",
             "surplus_y2027", "surplus_y2028", "surplus_y2029",
             "extension_option", "extension_years", "surplus_multiyear",
             "surplus_lo", "surplus_hi", "p_surplus_positive"]

# The replacement-anchor dropdown (FINDINGS #62, #82): how good the best free
# player is assumed to be. Moves every redraft-scale price and zero keep/cut
# calls (KEEP_BASIS prices keeps off the exchange rate). "low" is the default.
ANCHOR_OPTIONS = ["medium", "high"]
ANCHOR_COLS = ["rp_above_repl", "redraft_value", "production_value",
               "redraft_value_ft", "upside_ft", "redraft_value_2028",
               "value_lo", "value_hi"]

BOOTSTRAP_DRAWS = 1000      # ~11s; the bands are stable well below this
FINISH_SIM_DRAWS = 2000     # ~10s per ROS basis, x3 bases -- klab/standings_sim.py
KEEPER_FINISH_SIM_DRAWS = 800   # ~15-20s per PROJECTION_BASIS, x3; costlier per draw
FINISH_SHOCK_SCALE = 0.35   # the app's JS sim reads finish_sim.shock_scale, so this is the single source


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
    """2027 standings from each team's CURRENT keeper set alone, with every
    open slot filled at replacement level -- keeper-core strength, not an
    auction forecast.

    The replacement line is a 15-player band average around `replacement_rp`,
    never the single nearest player: that once landed on a closer and added
    ~25 saves to every team's empty pitcher slots.
    """
    hit_cols = ["AB", "H", "HR", "R", "RBI", "SB"]
    pit_cols = ["IP", "W", "SV", "K", "ER", "BB", "H"]   # "H" IS hits allowed here

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
    """Final standings for every completed season (2022-2025), keyed by
    season; basis-invariant, so computed once. Team names are normalised to
    the CURRENT franchise name via data/franchise_map.csv."""
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
    """Alternate rest-of-2026 signals for the win-now toggle. Computed ONCE:
    nothing here touches a dollar value (docs/FINDINGS.md #45). Keyed by
    fg_id (string) then column so the browser can overwrite ros_* in place."""
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
    """ros_value_over_replacement (docs/FINDINGS.md #34) for every player
    under each ROS basis. Computed inside each PROJECTION_BASIS subprocess,
    not once: it mixes a ROS-basis input (#45) with basis-dependent
    denominators/replacement, so both toggles must agree."""
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
    """Monte Carlo in-the-money odds (klab.standings_sim, docs/SESSION-LOG.md
    Phase 5), one run per ROS basis. Payout is 50/25/15/breakeven for 1st-4th
    (C.PAYOUT_SPOTS/C.PAYOUT_SHARE; once wrongly top-2-only). Computed ONCE:
    PROJECTION_BASIS affects nothing the rest-of-2026 simulator touches."""
    from klab.standings_sim import simulate_finish_odds
    out = {}
    for basis in ROS_BASES:
        odds = simulate_finish_odds(board, ros_basis=basis, B=B, shock_scale=shock_scale)
        finish_cols = [f"p_finish_{p}" for p in range(1, C.PAYOUT_SPOTS + 1)]
        out[basis] = {row["team"]: {
            **{c: _round(row[c]) for c in finish_cols},
            "p_money": _round(row["p_money"]),
        } for _, row in odds.iterrows()}
    return out


def _keeper_finish_odds(board: pd.DataFrame, fa: pd.DataFrame,
                        replacement_rp: float, B: int = KEEPER_FINISH_SIM_DRAWS,
                        shock_scale: float = FINISH_SHOCK_SCALE) -> dict:
    """Monte Carlo in-the-money odds for each team's CURRENT KEEPER SET in a
    hypothetical 2027 (klab.standings_sim Stage 3). Computed INSIDE each
    PROJECTION_BASIS subprocess: keep_2027 flags depend on the basis (~17%
    move, docs/FINDINGS.md #42). Fewer draws: ~4x the per-draw cost."""
    from klab.standings_sim import simulate_keeper_finish_odds
    odds = simulate_keeper_finish_odds(board, fa, replacement_rp, B=B, shock_scale=shock_scale)
    finish_cols = [f"p_finish_{p}" for p in range(1, C.PAYOUT_SPOTS + 1)]
    return {row["team"]: {
        **{c: _round(row[c]) for c in finish_cols},
        "p_money": _round(row["p_money"]),
    } for _, row in odds.iterrows()}


def _auction_estimates(board: pd.DataFrame, fa: pd.DataFrame) -> dict:
    """Comp-based next-auction estimate for every projected player, keyed
    "{fg_id}_{role}". Per-basis, since regression_fair_value IS the basis-
    dependent redraft_value (docs/FINDINGS.md #42). Keyed on role too: a
    two-way player's second row would otherwise overwrite the first.
    Display only -- never feeds back into redraft_value or keep/cut."""
    from klab.auction_estimator import estimate_auction_price
    players = pd.concat([board, fa], ignore_index=True)
    players = players[players["roto_points"] > 0]
    out = {}
    for name, fg_id, role in zip(players["name"], players["fg_id"], players["role"]):
        try:
            est = estimate_auction_price(name, players, k=15, role=role)
        except Exception:
            continue   # ambiguous/unresolved name -- skip rather than fail the whole build
        # 5 comps, was 8: the comp block is ~60% of the payload and is the
        # designated relief valve (docs/UI-REVIEW.md section 3); the #82
        # overlay variants bought their bytes here.
        comps = est["comps"].head(5).to_dict("records")
        out[f"{int(fg_id)}_{role}"] = {
            "fair": _round(est["regression_fair_value"]),
            "lo": _round(est["comp_adjusted_low"]),
            "mid": _round(est["comp_adjusted_mid"]),
            "hi": _round(est["comp_adjusted_high"]),
            "n_comps": est["n_comps"],
            "fallback": est["fallback_to_full_role"],
            "n_same_pos": est["n_same_position_available"],
            # _round() on every field: a missing comp `pos` is float('nan')
            # and json.dumps(allow_nan=False) rejects it.
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
    """Board, free agents, team summaries and constants for one `positional`
    setting (docs/FINDINGS.md #52) under the ambient PROJECTION_BASIS."""
    s = snapshot(positional=positional)
    board = s.board.merge(ros, on="fg_id", how="left")
    board[ros_cols] = board[ros_cols].fillna(0.0)
    # A split player has two rows per fg_id but one ROS line; zero the
    # duplicate or the JS rosterAgg sums his 2026 line twice (FINDINGS #80).
    board.loc[board.duplicated(subset=["fg_id"], keep="first"), ros_cols] = 0.0
    board["position"] = board["fg_id"].map(pos_map).fillna("?")
    board["mlb_team"] = board["fg_id"].map(team_map).fillna("?")
    # Bootstrap bands are NOT positional-aware (documented scope limit):
    # denominator uncertainty doesn't change with replacement level.
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
        "board": _rows(board, cols),
        "fa": _rows(fa, cols),
        "teams_raw": json.loads(s.teams.reset_index().to_json(orient="records")),
        "constants": {k: _round(v) if not isinstance(v, dict) else
                      {kk: _round(vv) for kk, vv in v.items()}
                      for k, v in s.constants.items()},
    }


def _overlay_rows(frames: list[pd.DataFrame], cols: list[str],
                  keys: set[str]) -> dict:
    """Per-row column overlay, keyed "{fg_id}_{role}" like auction_estimates
    (a split player has two rows per fg_id). Only rows the shipped board/fa
    actually carry are serialised; dollars at 2dp, they render at 0-1dp."""
    out = {}
    for df in frames:
        for _, r in df.iterrows():
            key = f"{int(r['fg_id'])}_{r['role']}"
            if key not in keys or key in out:
                continue
            vals = []
            for c in cols:
                v = r.get(c)
                v = _round(v)
                vals.append(round(v, 2) if isinstance(v, float) else v)
            out[key] = vals
    return out


def _clear_overlay_caches() -> None:
    """Caches keyed on hashable args that `sensitivity.knob` does not know
    about; stale entries here would serve default-anchor numbers under a
    variant (the FINDINGS #80 failure class)."""
    import klab.freeagents
    import klab.uncertainty
    klab.freeagents.free_agent_board.cache_clear()
    klab.uncertainty.bootstrap_bands.cache_clear()


def _exchange_overlays(keys: set[str], default_board: pd.DataFrame) -> dict:
    """One overlay per non-default exchange fit: the keep-scale columns under
    that fit, its constants, and each team's keeper surplus re-summed over the
    DEFAULT keeper set (keep flags follow the shipped default only, #76)."""
    from klab.board import build_board
    from klab.exchange import fit_variant
    from klab.freeagents import free_agent_board
    from klab.uncertainty import bootstrap_bands

    kept_keys = {f"{int(f)}_{r}" for f, r in zip(
        default_board.loc[default_board["keep_2027"], "fg_id"],
        default_board.loc[default_board["keep_2027"], "role"])}
    out = {}
    for name in EXCHANGE_OPTIONS:
        v = fit_variant(name)
        board, _, _ = build_board(exch=v)
        fa = free_agent_board(exch=v)
        bands = bootstrap_bands(B=BOOTSTRAP_DRAWS, exch=v).reset_index()
        board = board.merge(bands, on=["fg_id", "role"], how="left")
        key = [f"{int(f)}_{r}" for f, r in zip(board["fg_id"], board["role"])]
        bd = board.assign(_k=key)
        team_surplus = (bd[bd["_k"].isin(kept_keys)]
                        .groupby("team")["surplus_multiyear"].sum())
        out[name] = {
            "vals": _overlay_rows([board, fa], EXCH_COLS, keys),
            "constants": {"usd_per_roto_point_auction": _round(v["usd_per_point"]),
                          "auction_intercept": _round(v["intercept"]),
                          "exchange_basis": name},
            "teams": {t: {"surplus": _round(s)} for t, s in team_surplus.items()},
        }
    return out


def _anchor_overlays(keys: set[str]) -> dict:
    """One overlay per non-default replacement anchor and positional setting:
    the redraft-scale columns, the recalibrated constants (the $2,600 identity
    re-solves inside each anchor), and each team's keeper worth."""
    from sensitivity import knob
    from klab.api import _inflation
    from klab.board import build_board
    from klab.freeagents import free_agent_board
    from klab.uncertainty import bootstrap_bands

    out = {}
    for anchor in ANCHOR_OPTIONS:
        with knob(WAIVER_VALUE=anchor):
            _clear_overlay_caches()
            # Bands are not positional-aware (scope limit above), so one
            # bootstrap per anchor covers both settings.
            bands = bootstrap_bands(B=BOOTSTRAP_DRAWS).reset_index()
            per_pos = {}
            for positional, tag in ((False, "off"), (True, "on")):
                board, _, meta = build_board(positional=positional)
                board = board.merge(bands, on=["fg_id", "role"], how="left")
                fa = free_agent_board(positional=positional)
                worth = (board[board["keep_2027"]]
                         .groupby("team")["redraft_value"].sum())
                per_pos[tag] = {
                    "vals": _overlay_rows([board, fa], ANCHOR_COLS, keys),
                    "constants": {
                        "usd_per_roto_point_redraft": _round(meta["usd_per_rp_redraft"]),
                        "replacement_roto_points": _round(meta["replacement_rp"]),
                        "replacement_by_role": {k: _round(vv) for k, vv in
                                                meta["replacement_by_role"].items()},
                        "budget_check_top230": _round(meta["budget_check_top230"]),
                        **{k: _round(vv) for k, vv in _inflation(board).items()},
                    },
                    "teams": {t: {"keeper_value": _round(s)}
                              for t, s in worth.items()},
                }
            out[anchor] = per_pos
        _clear_overlay_caches()
    return out


def _variant_payload() -> dict:
    """Everything for the PROJECTION_BASIS ambient in THIS process (env var
    KLAB_PROJECTION_BASIS), under BOTH positional settings (docs/FINDINGS.md #52).

    Never flip C.PROJECTION_BASIS mid-process: klab.io.cached() keys on args,
    not this global, so a second basis would return the first's cached
    results (docs/FINDINGS.md #42) -- `_basis_variants()` uses subprocesses.
    `positional` is a real argument, so both settings run in-process.
    Auction estimates, ROS values and the 2027 keeper standings are NOT
    positional-aware (scope limit, same tradeoff as #43, #47, #49)."""
    from klab.board import build_board as _build_board_raw
    _, _, _meta = _build_board_raw()   # positional=False; _ros_values()/_keeper_standings_2027() stay pooled
    # Prefix EVERY ros column: ros PA once collided with projected PA (PA_x/PA_y).
    ros = ros_lines()
    ros = ros.rename(columns={c: f"ros_{c}" for c in ros.columns if c != "fg_id"})
    ros_cols = [f"ros_{c}" for c in ROS_COLS]
    assert not (set(ros.columns) - {"fg_id"}) & set(PLAYER_COLS), "column collision"

    # Display-only position (auction history, #50) -- NOT the C/SS
    # eligibility driving positional adjustment -- and real MLB team.
    from klab.keeper import position_map
    pos_map = position_map()
    from klab.io import mlb_team_map
    team_map = mlb_team_map()

    variants = {pos: _board_fa_teams_constants(pos, ros, ros_cols, pos_map, team_map)
               for pos in (False, True)}

    # The pooled-board features below need DataFrames, not serialised rows.
    s = snapshot(positional=False)
    board_raw = s.board.merge(ros, on="fg_id", how="left")
    board_raw[ros_cols] = board_raw[ros_cols].fillna(0.0)
    # Same split-player dedup as _board_fa_teams_constants (FINDINGS #80).
    board_raw.loc[board_raw.duplicated(subset=["fg_id"], keep="first"), ros_cols] = 0.0
    board_raw["position"] = board_raw["fg_id"].map(pos_map).fillna("?")
    fa_raw = s.free_agents.copy()
    fa_raw["team"] = "(free agent)"
    fa_raw = fa_raw[fa_raw["roto_points"] > 0].nlargest(400, "roto_points")
    fa_raw = fa_raw.merge(ros, on="fg_id", how="left")
    fa_raw[ros_cols] = fa_raw[ros_cols].fillna(0.0)

    # Every "{fg_id}_{role}" the shipped board/fa rows carry, across both
    # positional settings, so the overlays cover exactly the visible rows.
    fid_i, role_i = PLAYER_COLS.index("fg_id"), PLAYER_COLS.index("role")
    keys = {f"{int(r[fid_i])}_{r[role_i]}"
            for v in variants.values() for r in v["board"] + v["fa"]}

    return {
        # One copy of the column list: identical across every basis and
        # positional setting, so it ships once at the payload top level.
        "cols": PLAYER_COLS + ros_cols,
        "positional_variants": {"off": variants[False], "on": variants[True]},
        "auction_estimates": _auction_estimates(board_raw, fa_raw),
        "ros_values": _ros_values(board_raw, fa_raw, _meta["denominators"], _meta["baseline"],
                                  _meta["replacement_rp"]),
        "keeper_standings_2027": _keeper_standings_2027(board_raw, fa_raw, _meta["replacement_rp"]),
        "keeper_finish_odds": _keeper_finish_odds(board_raw, fa_raw, _meta["replacement_rp"]),
        # Column overlays for the exchange-fit and replacement-anchor
        # dropdowns (FINDINGS #82). Built LAST: the anchor pass rebuilds the
        # whole valuation under sensitivity.knob and clears every cache on
        # the way in and out, so nothing above may run after it.
        "exchange_variants": _exchange_overlays(keys, s.board),
        "anchor_variants": _anchor_overlays(keys),
    }


def _basis_variants() -> dict:
    """_variant_payload() under all three PROJECTION_BASIS settings: the
    ambient basis in-process, the other two in fresh `--variant` subprocesses
    so no basis's cached loaders leak into another's numbers."""
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
    # Stamp BOTH positional settings explicitly. The old top-level alias got
    # this mutation while the subprocess bases' "off" object (a separate dict
    # after the JSON round-trip) did not, which blanked the League tab's
    # "Points now" column on every non-default basis (FINDINGS #81).
    for v in variants.values():
        for setting in ("off", "on"):
            for t in v["positional_variants"][setting]["teams_raw"]:
                t["points_2026"] = pts_2026.get(t["team"])

    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category",
                                         values="total")
    b26 = team_baselines([2026]).iloc[0]

    # Precomputed by scripts/build_trade_suggestions.py; missing file -> [].
    sugg_path = C.OUT / "trade_suggestions.json"
    trade_suggestions = json.loads(sugg_path.read_text()) if sugg_path.exists() else []

    dboard = variants[default]["positional_variants"]["off"]
    fid_i = variants[default]["cols"].index("fg_id")
    fg_ids = {r[fid_i] for r in dboard["board"] + dboard["fa"]}
    ros_variants = _ros_variants(fg_ids)

    return {
        "built": date.today().isoformat(),
        "projection_basis": default,
        # No per-basis or top-level aliases of board/fa/teams/constants: the
        # template initialises through applyVariant() like any basis switch,
        # so every screen reads positional_variants and nothing ships twice.
        # The aliases cost ~2.4 MB and hid a stale-copy bug (FINDINGS #81).
        "basis_variants": {b: {"auction_estimates": v["auction_estimates"],
                               "ros_values": v["ros_values"],
                               "keeper_standings_2027": v["keeper_standings_2027"],
                               "keeper_finish_odds": v["keeper_finish_odds"],
                               "positional_variants": v["positional_variants"],
                               "exchange_variants": v["exchange_variants"],
                               "anchor_variants": v["anchor_variants"]}
                           for b, v in variants.items()},
        # Overlay column lists ship once; the option order is the dropdown
        # order and the first entry of each is the shipped default.
        "exchange_cols": EXCH_COLS,
        "anchor_cols": ANCHOR_COLS,
        "exchange_options": ["keeper_adjusted"] + EXCHANGE_OPTIONS,
        "anchor_options": ["low"] + ANCHOR_OPTIONS,
        "trade_suggestions": trade_suggestions,
        "ros_variants": ros_variants,
        "ros_basis_default": "ros",
        "band": {"lo": 10, "hi": 90, "draws": BOOTSTRAP_DRAWS},
        "cats": C.CATS,
        "neg_cats": sorted(C.NEG_CATS),
        "hit_cats": C.HIT_CATS,
        "pit_cats": C.PIT_CATS,
        "cols": variants[default]["cols"],   # identical across variants; shipped once
        "standings": json.loads(s.standings.reset_index().to_json(orient="records")),
        "history_standings": _historical_standings(),
        "finish_odds": _finish_odds(s.board, B=FINISH_SIM_DRAWS),
        "finish_sim": {"draws": FINISH_SIM_DRAWS, "shock_scale": FINISH_SHOCK_SCALE,
                      "payout_spots": C.PAYOUT_SPOTS, "payout_share": C.PAYOUT_SHARE},
        "keeper_finish_sim": {"draws": KEEPER_FINISH_SIM_DRAWS, "shock_scale": FINISH_SHOCK_SCALE},
        # For the JS port of klab.standings_sim's jitter: ship RELIABILITY
        # rather than hand-duplicate it, so the two can't drift.
        "reliability": {k: _round(v) for k, v in RELIABILITY.items()},
        "reliability_max": _round(REL_MAX),
        "cur_totals": {t: {c: _round(cur.loc[t, c]) for c in C.CATS}
                       for t in cur.index},
        "base26": {"AB": _round(b26["team_AB"]), "IP": _round(b26["team_IP"])},
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
    board = payload["basis_variants"][payload["projection_basis"]][
        "positional_variants"]["off"]["board"]
    agg = {}
    for r in board:
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
    # Chosen from the current board rather than hard-coded: the names that used
    # to sit here (Cade Smith, Nico Hoerner) were traded away mid-season and the
    # whole build died on a data refresh. Top two keepable by roto points per
    # side is deterministic, so the reference stays stable between refreshes.
    def _two(team):
        g = s.board[(s.board["team"] == team) & s.board["keepable"]]
        return list(g.nlargest(2, "roto_points")["name"])

    a_sends, b_sends = _two("Pookie 2.0"), _two("All-Stars")
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
    pv = payload["basis_variants"][payload["projection_basis"]]["positional_variants"]["off"]
    print(f"  {len(pv['board'])} rostered + {len(pv['fa'])} free agents")
    print(f"  wrote {out}  ({len(html)/1024:.0f} KB)")
    print(f"  wrote {ref}  -- check the browser with: node app/verify.mjs")


if __name__ == "__main__":
    if "--variant" in sys.argv:
        # Worker mode for _basis_variants(): ONLY the JSON payload on stdout.
        print(json.dumps(_variant_payload(), separators=(",", ":"), allow_nan=False))
    else:
        main()
