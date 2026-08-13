"""Step 6: trade evaluation.

Two independent lenses, because a trade in a keeper league is two trades:

  2027 asset view   Change in surplus (dollar value minus keeper cost) for
                    each side. This is the one that matters for a rebuilder.

  2026 win-now view Swap rest-of-season production into each team's current
                    category totals, re-rank all ten teams, and report the
                    change in standings points. This is what a contender buys.

A single verdict combines them using CONTENTION_WEIGHT.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .io import (load_ros_hitters, load_ros_pitchers, load_standings_long,
                 norm_name)


# --- roster / player lookup -------------------------------------------------

def find_player(board: pd.DataFrame, query: str) -> pd.Series:
    """Resolve a name (or fg_id) against the rostered player board."""
    q = str(query).strip()
    if q.isdigit():
        hit = board[board["fg_id"] == int(q)]
        if len(hit):
            return hit.iloc[0]
    n = norm_name(q)
    cand = board[board["name"].map(norm_name) == n]
    if len(cand) == 1:
        return cand.iloc[0]
    if len(cand) > 1:
        raise ValueError(f"'{query}' is ambiguous: {list(cand['name'])}")
    last = n.split()[-1] if n else ""
    cand = board[board["name"].map(norm_name).str.endswith(" " + last)]
    if len(cand) == 1:
        return cand.iloc[0]
    if len(cand) > 1:
        raise ValueError(f"'{query}' matches {list(cand['name'])} -- be specific")
    raise ValueError(f"'{query}' not found on any roster")


# --- 2026 rest-of-season standings impact -----------------------------------

def ros_lines() -> pd.DataFrame:
    """Rest-of-2026 counting lines per player, for the win-now view."""
    h = load_ros_hitters()
    hc = ["PA", "AB", "H", "HR", "R", "RBI", "SB"]
    H = h[["fg_id"] + hc].groupby("fg_id", as_index=False).sum()
    p = load_ros_pitchers().rename(columns={"SO": "K"})
    pc = ["IP", "W", "SV", "K", "ER", "BB", "H"]
    P = p[["fg_id"] + pc].groupby("fg_id", as_index=False).sum()
    P = P.rename(columns={"H": "H_allowed"})
    return H.merge(P, on="fg_id", how="outer").fillna(0.0)


def standings_points(wide: pd.DataFrame) -> pd.DataFrame:
    """Roto points from category totals: N points for best, 1 for worst.

    For a counting category the biggest total must earn the most points, so
    the rank is ascending (largest value -> rank N). ERA and WHIP invert.
    """
    pts = pd.DataFrame(index=wide.index)
    for c in C.CATS:
        asc = c not in C.NEG_CATS
        pts[c] = wide[c].rank(ascending=asc, method="average")
    pts["TOTAL"] = pts.sum(axis=1)
    return pts


def evaluate_trade(board: pd.DataFrame, team_a: str, team_b: str,
                   a_sends: list[str], b_sends: list[str],
                   contention_weight: float = C.CONTENTION_WEIGHT,
                   value_col: str = "redraft_value",
                   usd_per_point: float | None = None) -> dict:
    """Evaluate a proposed trade from both sides."""
    a_players = [find_player(board, x) for x in a_sends]
    b_players = [find_player(board, x) for x in b_sends]

    for p in a_players:
        if p["team"] != team_a:
            raise ValueError(f"{p['name']} is on {p['team']}, not {team_a}")
    for p in b_players:
        if p["team"] != team_b:
            raise ValueError(f"{p['name']} is on {p['team']}, not {team_b}")

    def side(out_players, in_players):
        def s(players, col):
            return sum(float(p[col]) for p in players)
        v_out, v_in = s(out_players, value_col), s(in_players, value_col)
        c_out, c_in = s(out_players, "keeper_cost"), s(in_players, "keeper_cost")
        rp_out, rp_in = s(out_players, "roto_points"), s(in_players, "roto_points")
        my_out = s(out_players, "surplus_multiyear")
        my_in = s(in_players, "surplus_multiyear")
        return {
            "value_in": v_in, "value_out": v_out, "d_value": v_in - v_out,
            "cost_in": c_in, "cost_out": c_out, "d_cost": c_in - c_out,
            "d_surplus": (v_in - c_in) - (v_out - c_out),
            "d_surplus_multiyear": my_in - my_out,
            "d_roto_points_2027": rp_in - rp_out,
            "d_salary_committed": c_in - c_out,
            "years_in": s(in_players, "years_controlled"),
            "years_out": s(out_players, "years_controlled"),
        }

    res = {
        "team_a": team_a, "team_b": team_b,
        "a_sends": [p["name"] for p in a_players],
        "b_sends": [p["name"] for p in b_players],
        "a": side(a_players, b_players),
        "b": side(b_players, a_players),
        "value_col": value_col,
    }

    win_now = win_now_delta(board, team_a, team_b, a_players, b_players)
    res["win_now"] = win_now
    # One 2026 standings point is priced at what a roto point costs at auction,
    # discounted by how much the team cares about this season.
    usd_per_standings_point = usd_per_point if usd_per_point else 7.6
    for t, key in ((team_a, "a"), (team_b, "b")):
        dp = float(win_now["delta_points"].get(t, 0.0))
        res[key]["d_standings_points_2026"] = dp
        res[key]["verdict_score"] = (res[key]["d_surplus"]
                                     + contention_weight * dp * usd_per_standings_point)
    res["contention_weight"] = contention_weight
    return res


def win_now_delta(board: pd.DataFrame, team_a: str, team_b: str,
                  a_players, b_players) -> dict:
    """Rest-of-2026 standings-point change for all ten teams after the swap."""
    ros = ros_lines()
    rosters = board[["team", "fg_id"]].copy()

    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category",
                                         values="total")

    def totals_from(vol_df):
        w = pd.DataFrame(index=cur.index)
        # counting categories: current total + rest-of-season contribution
        add = vol_df
        w["R"] = cur["R"] + add["R"]
        w["HR"] = cur["HR"] + add["HR"]
        w["RBI"] = cur["RBI"] + add["RBI"]
        w["SB"] = cur["SB"] + add["SB"]
        w["W"] = cur["W"] + add["W"]
        w["SV"] = cur["SV"] + add["SV"]
        w["K"] = cur["K"] + add["K"]
        # rate categories: rebuild from implied volume
        ab_now = add["AB_now"]; h_now = add["H_now"]
        w["AVG"] = (h_now + add["H"]) / (ab_now + add["AB"])
        ip_now = add["IP_now"]; er_now = add["ER_now"]; wh_now = add["WH_now"]
        w["ERA"] = (er_now + add["ER"]) * 9.0 / (ip_now + add["IP"])
        w["WHIP"] = (wh_now + add["BB"] + add["H_allowed"]) / (ip_now + add["IP"])
        return w

    # implied season-to-date volume behind each team's current rate stats,
    # anchored on the league-wide 2026 pace
    from .denoms import team_baselines
    b26 = team_baselines([2026]).iloc[0]
    add_base = pd.DataFrame(index=cur.index)
    add_base["AB_now"] = b26["team_AB"]
    add_base["H_now"] = cur["AVG"] * b26["team_AB"]
    add_base["IP_now"] = b26["team_IP"]
    add_base["ER_now"] = cur["ERA"] * b26["team_IP"] / 9.0
    add_base["WH_now"] = cur["WHIP"] * b26["team_IP"]

    def build(rosters_df):
        m = rosters_df.merge(ros, on="fg_id", how="left").fillna(0.0)
        g = m.groupby("team")[["AB", "H", "HR", "R", "RBI", "SB",
                               "IP", "W", "SV", "K", "ER", "BB",
                               "H_allowed"]].sum()
        g = g.reindex(cur.index).fillna(0.0)
        return pd.concat([g, add_base], axis=1)

    before = totals_from(build(rosters))

    moved = rosters.copy()
    a_ids = [int(p["fg_id"]) for p in a_players]
    b_ids = [int(p["fg_id"]) for p in b_players]
    moved.loc[moved["fg_id"].isin(a_ids), "team"] = team_b
    moved.loc[moved["fg_id"].isin(b_ids), "team"] = team_a
    after = totals_from(build(moved))

    p_before = standings_points(before)
    p_after = standings_points(after)
    delta = (p_after["TOTAL"] - p_before["TOTAL"])

    cat_delta = {}
    for t in (team_a, team_b):
        cat_delta[t] = {c: float(p_after.loc[t, c] - p_before.loc[t, c])
                        for c in C.CATS}

    return {
        "points_before": p_before["TOTAL"].to_dict(),
        "points_after": p_after["TOTAL"].to_dict(),
        "delta_points": delta.to_dict(),
        "category_point_delta": cat_delta,
        "totals_before": before, "totals_after": after,
    }


def format_trade(res: dict) -> str:
    a, b = res["team_a"], res["team_b"]
    L = []
    L.append(f"TRADE:  {a}  <->  {b}")
    L.append(f"  {a} sends: {', '.join(res['a_sends']) or '(nothing)'}")
    L.append(f"  {b} sends: {', '.join(res['b_sends']) or '(nothing)'}")
    L.append("")
    hdr = f"{'':<26}{a[:22]:>22}{b[:22]:>22}"
    L.append(hdr)
    L.append("-" * len(hdr))
    rows = [
        ("2027 value in", "value_in", "$%.1f"),
        ("2027 value out", "value_out", "$%.1f"),
        ("net 2027 value", "d_value", "%+.1f"),
        ("keeper $ committed", "d_salary_committed", "%+.1f"),
        ("NET 2027 SURPLUS", "d_surplus", "%+.1f"),
        ("NET MULTI-YR SURPLUS", "d_surplus_multiyear", "%+.1f"),
        ("contract yrs in", "years_in", "%.0f"),
        ("contract yrs out", "years_out", "%.0f"),
        ("2027 roto pts", "d_roto_points_2027", "%+.2f"),
        ("2026 standings pts", "d_standings_points_2026", "%+.1f"),
    ]
    for label, key, fmt in rows:
        L.append(f"{label:<26}{fmt % res['a'][key]:>22}{fmt % res['b'][key]:>22}")
    return "\n".join(L)
