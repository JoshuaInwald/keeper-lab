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
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from klab import config as C
from klab.api import snapshot
from klab.denoms import team_baselines
from klab.io import load_standings_long
from klab.trade import ros_lines, standings_points

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


def build_payload() -> dict:
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

    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category",
                                         values="total")
    b26 = team_baselines([2026]).iloc[0]

    teams = s.teams.reset_index()
    teams["points_2026"] = teams["team"].map(s.standings["points_2026"])

    cols = PLAYER_COLS + ros_cols
    # Precomputed separately (scripts/build_trade_suggestions.py) -- a real
    # search across 45 team pairs is a couple minutes, not a build-step cost.
    # Missing file -> empty list rather than a crash, so a normal build_app
    # run still works if suggestions haven't been (re)generated yet.
    sugg_path = C.OUT / "trade_suggestions.json"
    trade_suggestions = json.loads(sugg_path.read_text()) if sugg_path.exists() else []

    return {
        "built": date.today().isoformat(),
        "trade_suggestions": trade_suggestions,
        "band": {"lo": 10, "hi": 90, "draws": BOOTSTRAP_DRAWS},
        "cats": C.CATS,
        "neg_cats": sorted(C.NEG_CATS),
        "hit_cats": C.HIT_CATS,
        "pit_cats": C.PIT_CATS,
        "cols": cols,
        "board": _rows(board, cols),
        "fa": _rows(fa, cols),
        "teams": json.loads(teams.to_json(orient="records")),
        "standings": json.loads(s.standings.reset_index().to_json(orient="records")),
        "cur_totals": {t: {c: _round(cur.loc[t, c]) for c in C.CATS}
                       for t in cur.index},
        "base26": {"AB": _round(b26["team_AB"]), "IP": _round(b26["team_IP"])},
        "constants": {k: _round(v) if not isinstance(v, dict) else
                      {kk: _round(vv) for kk, vv in v.items()}
                      for k, v in s.constants.items()},
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
    main()
