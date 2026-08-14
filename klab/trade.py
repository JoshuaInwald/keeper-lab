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


def prorated_to_date_lines(season_games: int | None = None,
                           games_played_pctile: float | None = None) -> pd.DataFrame:
    """Rest-of-2026 counting lines implied by each player's season-to-date
    rate PER TEAM GAME, extended over however many team games are left in
    the season -- a genuinely different signal from `ros_lines()`'s ZiPS
    system, meant for blending with it (see `ros_lines_for_basis`), not for
    use alone.

    Rate is per TEAM game, not per the player's own `G`, on purpose --
    real bug from the first version of this function, caught before it
    shipped (out/LAB_NOTEBOOK.md #24): a starting pitcher's own `G` counts
    his STARTS (roughly one every five team games), not team games played.
    Dividing his to-date innings by his own 18 starts and multiplying by ~43
    remaining TEAM games projected Tarik Skubal for 256 more innings --
    treating every remaining team game as a start. Dividing by team games
    played instead gives every player (hitter or pitcher, everyday or
    part-time) a consistent "production per team game," which correctly
    dilutes a starter's rate by the ~4 team games he doesn't pitch in, and
    is the same idea a per-PA or per-appearance rate is trying to
    approximate anyway -- just denominated in something that actually means
    "how much season is left" for every role at once.

    "Team games played to date" is a single, shared, league-wide estimate,
    not a per-team schedule lookup: the `C.GAMES_PLAYED_PCTILE` percentile
    of games played among hitters with PA > 300 (a few players below that
    are platoon/DH rotation, not proof their own team has played fewer
    games). `C.SEASON_GAMES` minus that is games left.

    Known limitation, stated directly rather than silently accepted: an
    injured player's healthy-pace rate gets extended over the FULL
    remaining schedule, because this method has no notion of an expected
    return date. That's not a bug to patch here -- it's exactly the blind
    spot `ros_lines()` (ZiPS, injury- and role-aware) covers, which is the
    whole reason to blend the two rather than pick one. See
    out/FINDINGS.md #45.
    """
    from .io import load_hitters_history, load_pitchers_history
    season_games = season_games or C.SEASON_GAMES
    pctile = games_played_pctile or C.GAMES_PLAYED_PCTILE

    h26 = load_hitters_history().query("season == 2026")
    p26 = load_pitchers_history().query("season == 2026")

    regulars = h26[h26["PA"] > 300]
    team_games_played = (regulars["G"].quantile(pctile)
                         if len(regulars) else float(season_games))
    remaining = max(season_games - team_games_played, 0.0)
    if team_games_played <= 0:
        team_games_played = float(season_games)   # avoid a div-by-zero on an empty/degenerate history

    hc = ["PA", "AB", "H", "HR", "R", "RBI", "SB"]
    H = (h26[hc] / team_games_played * remaining).fillna(0.0)
    H["fg_id"] = h26["fg_id"].values
    H = H.groupby("fg_id", as_index=False).sum()

    pc = ["IP", "W", "SV", "K", "ER", "BB", "H"]
    P = (p26[pc] / team_games_played * remaining).fillna(0.0)
    P["fg_id"] = p26["fg_id"].values
    P = P.groupby("fg_id", as_index=False).sum().rename(columns={"H": "H_allowed"})

    out = H.merge(P, on="fg_id", how="outer").fillna(0.0)
    out.attrs["remaining_games"] = remaining
    out.attrs["team_games_played_est"] = team_games_played
    return out


ROS_BASES = ("ros", "prorated", "blend")


def ros_lines_for_basis(basis: str = "ros") -> pd.DataFrame:
    """Dispatcher for which rest-of-2026 signal feeds the win-now standings
    engine and (via the caller) `ros_value_over_replacement`.

    "ros" (default -- every existing caller keeps this behavior unless it
    opts in): `ros_lines()`, the ZiPS rest-of-season system alone.
    "prorated": `prorated_to_date_lines()`, current pace only.
    "blend": the two averaged 50/50, at Josh's request -- a middle ground
    between "trust the projection system" and "trust what's actually
    happening right now." There is no "pre-season 2026" option: no file in
    `data/` has a full-season 2026 projection made before the season started
    (the ZiPS Depth Charts exports on hand are for 2027/2028 only) -- see
    `data/README.md` and out/FINDINGS.md #45.
    """
    if basis == "ros":
        return ros_lines()
    if basis == "prorated":
        return prorated_to_date_lines()
    if basis == "blend":
        cols = ["PA", "AB", "H", "HR", "R", "RBI", "SB",
               "IP", "W", "SV", "K", "ER", "BB", "H_allowed"]
        a = ros_lines().set_index("fg_id").reindex(columns=cols, fill_value=0.0)
        b = prorated_to_date_lines().set_index("fg_id").reindex(columns=cols, fill_value=0.0)
        idx = a.index.union(b.index)
        blended = (a.reindex(idx, fill_value=0.0) + b.reindex(idx, fill_value=0.0)) / 2.0
        return blended.reset_index()
    raise ValueError(f"unknown ROS basis {basis!r}, expected one of {ROS_BASES}")


def ros_value_over_replacement(players: pd.DataFrame, D: dict, base: dict,
                               replacement_rp: float) -> pd.DataFrame:
    """Rest-of-season roto value over a replacement player, for the SAME
    remaining playing time -- not a full season, not a team-standings swap.

    This answers a different question than `win_now_delta`: not "what does
    this trade do to two specific teams' 2026 standings" but "how much
    better is this player than a replacement-level guy, for however much of
    the season he individually has left." Dynamic per player on purpose --
    `remaining_frac` comes from each player's own ROS playing time (already
    ZiPS-forecast-specific to his own team's remaining schedule and his own
    role), not a single league-wide "season is X% over" constant.

    Uses the SAME full-season denominators (`D`) and baseline (`base`) as the
    2027 keeper board -- these are stable, already-validated "units per
    standings point" conversion factors and don't need re-deriving for a
    partial season. What DOES need to scale down is the marginal-team
    dilution baseline (`base_AB`/`base_H`/etc.): comparing a 6-week rest-of-
    season sample against a FULL season's team volume would dilute a rate
    stat's marginal impact by roughly 4x too much. Scaling the baseline by
    each player's own `remaining_frac` keeps the "1 player diluting a
    13/14-man team" ratio consistent with how the full-season board computes
    it, just at a smaller volume.
    """
    from .denoms import RotoScorer

    out = players.copy()
    is_hit = out["role"] == "HIT"
    frac_hit = (out["PA"] / C.KEEPER_PA_FLOOR).clip(lower=0.02, upper=1.0)
    frac_pit = (out["IP"] / C.KEEPER_IP_FLOOR).clip(lower=0.02, upper=1.0)
    out["remaining_frac"] = frac_hit.where(is_hit, frac_pit)

    rp = pd.Series(0.0, index=out.index)
    repl = pd.Series(0.0, index=out.index)
    for frac, grp in out.groupby(out["remaining_frac"].round(3)):
        scaled_base = dict(base)
        for k in ("team_AB", "team_IP"):
            scaled_base[k] = base[k] * frac
        scaled_base["team_H"] = scaled_base["team_AB"] * base["team_AVG"]
        scaled_base["team_ER"] = scaled_base["team_IP"] * base["team_ERA"] / 9.0
        scaled_base["team_WH"] = scaled_base["team_IP"] * base["team_WHIP"]
        sc = RotoScorer(D, scaled_base)
        h = sc.hitters(grp[["PA", "AB", "H", "HR", "R", "RBI", "SB"]])
        p = sc.pitchers(grp.rename(columns={"H_allowed": "H_scorer"})
                        [["IP", "W", "SV", "K", "ER", "BB", "H_scorer"]]
                        .rename(columns={"H_scorer": "H"}))
        rp.loc[grp.index] = h["roto_points"].where(is_hit.loc[grp.index], p["roto_points"])
        repl.loc[grp.index] = replacement_rp * frac

    out["ros_rp"] = rp
    out["ros_replacement_rp"] = repl
    out["ros_value_over_replacement"] = rp - repl
    return out


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
                   usd_per_point: float,
                   contention_weight: float = C.CONTENTION_WEIGHT,
                   value_col: str = "redraft_value",
                   ros_basis: str = "ros") -> dict:
    """Evaluate a proposed trade from both sides.

    `usd_per_point` has no default on purpose (out/FINDINGS.md #32.1): this
    used to fall back to a hardcoded, silently-stale constant that every
    real caller forgot to override. Pass `exch["usd_per_point"]` from
    `klab.board.build_board()`, or `snapshot().constants["usd_per_roto_point_auction"]`
    if you're working from a `Snapshot`. A wrong number here is wrong in a
    way nothing else in this function would catch.

    `ros_basis` controls which rest-of-2026 signal the win-now half uses --
    see `ros_lines_for_basis`. Default "ros" (ZiPS alone) matches every
    existing caller's established behavior; pass "blend" for the
    50/50-with-current-pace read. `d_roto_points_2027` in each side's dict is
    the *context-free* roto-point swing (this league's fixed denominators,
    not either team's current category profile) -- the number to read when
    the question is "how much is this player worth to an average team," as
    opposed to `win_now`'s team-specific standings-point delta.
    """
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

    win_now = win_now_delta(board, team_a, team_b, a_players, b_players, ros_basis=ros_basis)
    res["win_now"] = win_now
    # One 2026 standings point is priced at what a roto point costs at auction,
    # discounted by how much the team cares about this season.
    usd_per_standings_point = usd_per_point
    for t, key in ((team_a, "a"), (team_b, "b")):
        dp = float(win_now["delta_points"].get(t, 0.0))
        res[key]["d_standings_points_2026"] = dp
        res[key]["verdict_score"] = (res[key]["d_surplus"]
                                     + contention_weight * dp * usd_per_standings_point)
    res["contention_weight"] = contention_weight
    return res


def _season_baseline(cur: pd.DataFrame) -> pd.DataFrame:
    """Implied season-to-date volume behind each team's current rate stats,
    anchored on the league-wide 2026 pace. Shared by `win_now_delta()` and
    `klab.standings_sim`'s Monte Carlo simulator, so both compute standings
    totals with the exact same arithmetic rather than two hand-written
    copies that can silently drift apart."""
    from .denoms import team_baselines
    b26 = team_baselines([2026]).iloc[0]
    add_base = pd.DataFrame(index=cur.index)
    add_base["AB_now"] = b26["team_AB"]
    add_base["H_now"] = cur["AVG"] * b26["team_AB"]
    add_base["IP_now"] = b26["team_IP"]
    add_base["ER_now"] = cur["ERA"] * b26["team_IP"] / 9.0
    add_base["WH_now"] = cur["WHIP"] * b26["team_IP"]
    return add_base


def _team_volume(rosters_df: pd.DataFrame, ros: pd.DataFrame, cur_index) -> pd.DataFrame:
    """Sum each team's rest-of-season counting-stat volume from a roster map
    (fg_id -> team) and a rest-of-season stat-line table. Shared the same
    way `_season_baseline` is."""
    m = rosters_df.merge(ros, on="fg_id", how="left").fillna(0.0)
    g = m.groupby("team")[["AB", "H", "HR", "R", "RBI", "SB",
                           "IP", "W", "SV", "K", "ER", "BB",
                           "H_allowed"]].sum()
    return g.reindex(cur_index).fillna(0.0)


def _totals_from(cur: pd.DataFrame, vol_df: pd.DataFrame) -> pd.DataFrame:
    """Full-season-to-date category totals: current totals + rest-of-season
    volume. Rate categories are rebuilt from implied volume, not averaged as
    raw rates -- averaging ignores how much support each rate has, the same
    mistake #45 fixed in a different layer. `vol_df` is `_team_volume()`'s
    output concatenated with `_season_baseline()`'s -- both live in one
    frame because every rate reconstruction needs both. Shared the same way
    the two functions above are."""
    w = pd.DataFrame(index=cur.index)
    add = vol_df
    w["R"] = cur["R"] + add["R"]
    w["HR"] = cur["HR"] + add["HR"]
    w["RBI"] = cur["RBI"] + add["RBI"]
    w["SB"] = cur["SB"] + add["SB"]
    w["W"] = cur["W"] + add["W"]
    w["SV"] = cur["SV"] + add["SV"]
    w["K"] = cur["K"] + add["K"]
    ab_now = add["AB_now"]; h_now = add["H_now"]
    w["AVG"] = (h_now + add["H"]) / (ab_now + add["AB"])
    ip_now = add["IP_now"]; er_now = add["ER_now"]; wh_now = add["WH_now"]
    w["ERA"] = (er_now + add["ER"]) * 9.0 / (ip_now + add["IP"])
    w["WHIP"] = (wh_now + add["BB"] + add["H_allowed"]) / (ip_now + add["IP"])
    return w


def win_now_delta(board: pd.DataFrame, team_a: str, team_b: str,
                  a_players, b_players, ros_basis: str = "ros") -> dict:
    """Rest-of-2026 standings-point change for all ten teams after the swap.

    `ros_basis` -- see `ros_lines_for_basis` -- selects which rest-of-season
    signal drives this. Default "ros" preserves every existing caller's
    established numbers.
    """
    ros = ros_lines_for_basis(ros_basis)
    rosters = board[["team", "fg_id"]].copy()

    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category",
                                         values="total")
    add_base = _season_baseline(cur)

    def build(rosters_df):
        return pd.concat([_team_volume(rosters_df, ros, cur.index), add_base], axis=1)

    before = _totals_from(cur, build(rosters))

    moved = rosters.copy()
    a_ids = [int(p["fg_id"]) for p in a_players]
    b_ids = [int(p["fg_id"]) for p in b_players]
    moved.loc[moved["fg_id"].isin(a_ids), "team"] = team_b
    moved.loc[moved["fg_id"].isin(b_ids), "team"] = team_a
    after = _totals_from(cur, build(moved))

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
