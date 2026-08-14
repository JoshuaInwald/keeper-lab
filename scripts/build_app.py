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

# The three forks PROJECTION_BASIS can take (klab/config.py). Shipped as
# three parallel payloads rather than one, so the app can let a user flip
# between them instead of hiding the model's biggest fork behind a rebuild.
# See out/ROADMAP.md 2.2, out/FINDINGS.md #42.
BASES = ["blend", "projection", "actuals"]

# Columns carried into the payload, in order. Kept explicit rather than
# "everything" so the file stays small and the schema is reviewable.
PLAYER_COLS = [
    "fg_id", "name", "team", "role", "il",
    "salary", "contract", "keeper_status", "keeper_cost", "years_controlled",
    "keepable", "extension_used", "extension_option", "extension_years", "keep_2027",
    "roto_points", "rp_above_repl", "redraft_value", "keep_value",
    "roto_points_ft", "redraft_value_ft", "upside_ft",
    "redraft_value_2028", "surplus_redraft",
    "surplus_y2027", "surplus_y2028", "surplus_y2029", "surplus_multiyear",
    "pt_scale",
    "value_lo", "value_hi", "surplus_lo", "surplus_hi", "p_surplus_positive",
    "PA", "AB", "H", "HR", "R", "RBI", "SB", "AVG",
    "IP", "W", "SV", "K", "ER", "BB", "ERA", "WHIP",
] + [f"rp_{c}" for c in C.CATS]

ROS_COLS = ["AB", "H", "HR", "R", "RBI", "SB",
            "IP", "W", "SV", "K", "ER", "BB", "H_allowed"]

BOOTSTRAP_DRAWS = 1000      # ~11s; the bands are stable well below this


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


def _auction_estimates(board: pd.DataFrame, fa: pd.DataFrame) -> dict:
    """Comp-based next-auction price estimate for every player with a
    projection, keyed by fg_id (as a string -- JSON object keys are always
    strings). Computed per-basis, not once and reused: `regression_fair_value`
    inside `estimate_auction_price()` is the player's own `redraft_value`,
    which is exactly the number the basis selector changes -- pinning this
    panel to one basis while the rest of the page follows the selector
    would reproduce the same inconsistency out/FINDINGS.md #42 already
    found and fixed for team/constant aggregates.

    Deliberately still a separate, non-integrated tool per
    klab/auction_estimator.py's own docstring -- this only *displays* its
    output next to the regression fair value, it does not feed back into
    redraft_value or any keep/cut decision anywhere in klab/."""
    from klab.auction_estimator import estimate_auction_price
    players = pd.concat([board, fa], ignore_index=True)
    players = players[players["roto_points"] > 0]
    out = {}
    for name, fg_id in zip(players["name"], players["fg_id"]):
        try:
            est = estimate_auction_price(name, players, k=15)
        except Exception:
            continue   # ambiguous/unresolved name -- skip rather than fail the whole build
        comps = est["comps"].head(8).to_dict("records")
        out[str(int(fg_id))] = {
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
            "comps": [{"season": _round(c["season"]), "player": _round(c["player"]),
                       "team": _round(c["team"]), "salary": _round(c["salary"]),
                       "pos": _round(c["pos"]), "premium_pct": _round(c["premium_frac"] * 100)}
                      for c in comps],
        }
    return out


def _variant_payload() -> dict:
    """Board, free agents, team summaries and constants for whichever
    PROJECTION_BASIS is ambient in THIS process (klab/config.py's
    PROJECTION_BASIS, overridable via the KLAB_PROJECTION_BASIS env var).

    Deliberately does not try to flip C.PROJECTION_BASIS mid-process to get
    all three bases from one run: `klab.io.cached()` memoises every loader
    on its function arguments only, not on this global, so a second basis
    computed in the same process would silently return the first basis's
    cached intermediate results. See `_basis_variants()`, which runs this
    function in three separate fresh processes instead, and
    out/FINDINGS.md #42 for the version of this bug that was actually
    shipped and caught (klab/trade_finder.py, a different memoisation
    hazard, same root cause: process-global state and per-arg caching don't
    mix)."""
    s = snapshot()
    # Prefix EVERY ros column, not just the ones the win-now maths uses.
    # `ros_lines()` also carries PA, which silently collided with the board's
    # projected PA and turned it into PA_x/PA_y -- the drawer showed a dash.
    ros = ros_lines()
    ros = ros.rename(columns={c: f"ros_{c}" for c in ros.columns if c != "fg_id"})
    ros_cols = [f"ros_{c}" for c in ROS_COLS]
    assert not (set(ros.columns) - {"fg_id"}) & set(PLAYER_COLS), "column collision"

    board = s.board.merge(ros, on="fg_id", how="left")
    board[ros_cols] = board[ros_cols].fillna(0.0)
    # Bands come from resampling the team-seasons the denominators are fit on,
    # so every dollar figure can be shown as a range instead of a point.
    from klab.uncertainty import bootstrap_bands
    board = board.merge(bootstrap_bands(B=BOOTSTRAP_DRAWS).reset_index(),
                        on="fg_id", how="left")

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

    cols = PLAYER_COLS + ros_cols
    return {
        "cols": cols,
        "board": _rows(board, cols),
        "fa": _rows(fa, cols),
        # points_2026 isn't attached here -- it comes from live 2026
        # standings, which don't depend on PROJECTION_BASIS, so the caller
        # attaches it once from its own snapshot() rather than every
        # subprocess repeating an identical lookup.
        "teams_raw": json.loads(s.teams.reset_index().to_json(orient="records")),
        "constants": {k: _round(v) if not isinstance(v, dict) else
                      {kk: _round(vv) for kk, vv in v.items()}
                      for k, v in s.constants.items()},
        "auction_estimates": _auction_estimates(board, fa),
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
        for t in v["teams_raw"]:
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
                               "auction_estimates": v["auction_estimates"]}
                           for b, v in variants.items()},
        "trade_suggestions": trade_suggestions,
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
        "standings": json.loads(s.standings.reset_index().to_json(orient="records")),
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
