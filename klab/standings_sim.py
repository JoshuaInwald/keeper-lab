"""Step 6b: Monte Carlo standings simulation.

`klab.trade.win_now_delta()` answers "what does a specific swap do to the
point-estimate standings." This answers a different question: "how often
does each team actually finish in the money," given real player-outcome
uncertainty -- the question that matters in a league that only pays out
for a top-`C.PAYOUT_SPOTS` finish (out/ROADMAP.md Phase 5).

Deliberately does NOT reuse `klab.uncertainty`'s existing bootstrap: that
resamples DENOMINATOR uncertainty (how many units of a stat buy a
standings point), not player-OUTCOME uncertainty (how much a given player
actually produces). Denominator uncertainty is the wrong source for "will
my closer's saves hold up" -- the question this module exists to answer.

`p_money` is P(finish in the top `C.PAYOUT_SPOTS` places), a single
threshold. The real payout (50/25/15/breakeven -- `C.PAYOUT_SHARE`) isn't
flat across those spots, and a single in-the-money probability discards
that -- 4th is structurally a break-even outcome, not a scaled-down 1st.
Not modeled here yet; see `out/ROADMAP.md` Phase 5's note on this.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .io import load_standings_long
from .project import RELIABILITY, REL_MAX
from .trade import (_season_baseline, _team_volume, _totals_from,
                    ros_lines_for_basis, standings_points)

DEFAULT_SHOCK_SCALE = 0.35
DEFAULT_DRAWS = 2000

# Which rest-of-season counting-stat column gets shocked, and which roto
# category's RELIABILITY governs how much it can move. AVG/ERA/WHIP are
# rebuilt downstream from these in _totals_from() and are NOT shocked
# directly -- shocking H and AB independently (or IP and ER independently)
# would let a rate move by more than its own component's real uncertainty
# implies. Playing time (AB/IP) is not shocked either: this simulates
# PERFORMANCE variance, not injury/role variance, a separate and unbuilt
# question.
_SHOCK_CATEGORY = {
    "H": "H", "HR": "HR", "R": "R", "RBI": "RBI", "SB": "SB",
    "W": "W", "K": "K", "ER": "ER", "BB": "BB", "H_allowed": "H",
}
# Saves have no RELIABILITY entry -- klab.project never blends them through
# rel_weight(), since 2027 saves come from a separate persistence model
# instead. Wins' reliability (0.151, the lowest of anything actually in the
# table) is the closest available proxy: both are famously context- and
# opportunity-driven rather than skill-driven, and both are known to swing
# on a single role change -- exactly the volatility a save-total needs to
# reflect here.
_SV_RELIABILITY = RELIABILITY["W"]


def _jitter_ros(ros: pd.DataFrame, rng: np.random.Generator,
                shock_scale: float) -> pd.DataFrame:
    """One shared per-player "hot/cold" talent shock, scaled per stat by how
    unreliable that stat is. A player running hot tends to run hot across
    HR/R/RBI together, not independently per stat -- hence one shared draw
    per player, not one draw per stat -- and a less-reliable stat should
    swing further for the same underlying shock than a more-reliable one
    (a hot month moves W more than it moves SB, and RELIABILITY already
    measures exactly that ordering for this league's own data)."""
    out = ros.copy()
    t = rng.normal(0.0, 1.0, size=len(out))
    for col, cat in _SHOCK_CATEGORY.items():
        if col not in out:
            continue
        unreliability = 1.0 - RELIABILITY[cat] / REL_MAX
        mult = np.clip(1.0 + t * shock_scale * unreliability, 0.0, None)
        out[col] = out[col].to_numpy() * mult
    if "SV" in out:
        unreliability = 1.0 - _SV_RELIABILITY / REL_MAX
        mult = np.clip(1.0 + t * shock_scale * unreliability, 0.0, None)
        out["SV"] = out["SV"].to_numpy() * mult
    return out


def simulate_finish_odds(board: pd.DataFrame, swap: dict | None = None,
                         ros_basis: str = "ros", B: int = DEFAULT_DRAWS,
                         seed: int = 0, shock_scale: float = DEFAULT_SHOCK_SCALE,
                         payout_spots: int = C.PAYOUT_SPOTS) -> pd.DataFrame:
    """Monte Carlo odds of finishing in each of places 1..payout_spots, plus
    p_money (finishing in ANY of them), in the rest of 2026.

    `swap` -- {fg_id: new_team}, fg_id as int -- lets this answer "what
    would a hypothetical trade do to my odds." Same override mechanism
    `win_now_delta()` uses for the same reason: one function serves both
    the standalone Contention tab (swap=None) and the Trade tab's what-if
    view, rather than two implementations that could disagree.

    Each draw jitters `ros_lines_for_basis(ros_basis)` (see `_jitter_ros`),
    rebuilds team totals with the exact arithmetic `win_now_delta()` uses
    (`_totals_from`/`_team_volume`/`_season_baseline`, imported from
    `klab.trade` rather than re-derived, so the two can't silently drift
    apart), and ranks with `standings_points()` -- the same function
    everything else in this project uses to convert category totals into
    standings points.
    """
    rosters = board[["team", "fg_id"]].copy()
    if swap:
        for fid, new_team in swap.items():
            rosters.loc[rosters["fg_id"] == int(fid), "team"] = new_team

    ros = ros_lines_for_basis(ros_basis)
    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category",
                                         values="total")
    add_base = _season_baseline(cur)

    rng = np.random.default_rng(seed)
    teams = list(cur.index)
    finish_count = {place: {t: 0 for t in teams} for place in range(1, payout_spots + 1)}

    for _ in range(B):
        jittered = _jitter_ros(ros, rng, shock_scale)
        vol = pd.concat([_team_volume(rosters, jittered, cur.index), add_base], axis=1)
        w = _totals_from(cur, vol)
        order = standings_points(w[C.CATS])["TOTAL"].sort_values(ascending=False)
        for place in range(1, payout_spots + 1):
            finish_count[place][order.index[place - 1]] += 1

    out = pd.DataFrame({
        "team": teams,
        "current_points": [float(standings_points(cur[C.CATS])["TOTAL"][t]) for t in teams],
    })
    for place in range(1, payout_spots + 1):
        out[f"p_finish_{place}"] = [finish_count[place][t] / B for t in teams]
    out["p_money"] = out[[f"p_finish_{p}" for p in range(1, payout_spots + 1)]].sum(axis=1)
    return out.sort_values("p_money", ascending=False).reset_index(drop=True)


# --- Stage 3: 2027 keeper-core finish odds (out/ROADMAP.md Phase 5) --------
# Genuinely different from the rest-of-2026 simulator above, not a copy with
# a different input: there is no already-realized baseline to anchor
# against here -- the entire 2027 season is in the future, so a KEPT
# player's own full-season projected line is what gets jittered (not an
# increment on top of known partial-season totals), while the replacement-
# level fill for a team's open roster slots is left FIXED. That fill is a
# 15-player band average (see `_keeper_standings_2027` in
# scripts/build_app.py, which this mirrors for its deterministic point
# estimate), not one real player's own outcome, so there's no principled
# distribution to draw it from.
_KEEPER_HIT_COLS = ["AB", "H", "HR", "R", "RBI", "SB"]
# "H" on the full-season board IS hits allowed for a pitcher row (unlike
# ros_lines()'s merged schema, which renames it to H_allowed to dodge a
# join collision) -- no separate H_allowed column exists here, and none is
# needed: klab.project already prices a pitcher's hits-allowed off the same
# "H" RELIABILITY entry a hitter's own hit rate uses, so one shared shock
# column is correct, not an oversight.
_KEEPER_PIT_COLS = ["IP", "W", "SV", "K", "ER", "BB", "H"]
_KEEPER_SHOCK_CATEGORY = {
    "H": "H", "HR": "HR", "R": "R", "RBI": "RBI", "SB": "SB",
    "W": "W", "K": "K", "ER": "ER", "BB": "BB",
}


def _jitter_keeper_lines(kept: pd.DataFrame, rng: np.random.Generator,
                         shock_scale: float) -> pd.DataFrame:
    """Same one-shared-shock-per-player mechanism as `_jitter_ros`, applied
    to each kept player's full-2027-season projected counting stats rather
    than a rest-of-season increment."""
    out = kept.copy()
    t = rng.normal(0.0, 1.0, size=len(out))
    for col, cat in _KEEPER_SHOCK_CATEGORY.items():
        if col not in out:
            continue
        unreliability = 1.0 - RELIABILITY[cat] / REL_MAX
        mult = np.clip(1.0 + t * shock_scale * unreliability, 0.0, None)
        out[col] = out[col].to_numpy() * mult
    if "SV" in out:
        unreliability = 1.0 - _SV_RELIABILITY / REL_MAX
        mult = np.clip(1.0 + t * shock_scale * unreliability, 0.0, None)
        out["SV"] = out["SV"].to_numpy() * mult
    return out


def simulate_keeper_finish_odds(board: pd.DataFrame, fa: pd.DataFrame,
                                replacement_rp: float,
                                keeper_override: dict | None = None,
                                B: int = DEFAULT_DRAWS, seed: int = 0,
                                shock_scale: float = DEFAULT_SHOCK_SCALE,
                                payout_spots: int = C.PAYOUT_SPOTS
                                ) -> pd.DataFrame:
    """Monte Carlo odds of a team's CURRENT KEEPER SET finishing in the
    money in a hypothetical 2027 season -- keeper-core strength alone, not
    a real-auction forecast (every team will also spend a full 2027
    budget on top of its keepers, same scope note `_keeper_standings_2027`
    already makes for its point-estimate version of this).

    `keeper_override` -- {fg_id: new_team}, fg_id as int -- reassigns which
    team's keeper SET an already-kept player counts toward, the same
    override shape `simulate_finish_odds()`'s `swap` uses, for "what if
    this keeper were on a different roster" questions. Does not decide
    keep/cut for anyone; the player must already be a keeper somewhere.
    """
    pool = pd.concat([board, fa], ignore_index=True)

    def repl_line(p, cols, n=15):
        d = (p["roto_points"] - replacement_rp).abs()
        return p.loc[d.nsmallest(n).index, cols].mean()

    repl_hit = repl_line(pool[pool["role"] != "PIT"], _KEEPER_HIT_COLS)
    repl_pit = repl_line(pool[pool["role"] == "PIT"], _KEEPER_PIT_COLS)

    kept = board[board["keep_2027"]].copy()
    if keeper_override:
        for fid, new_team in keeper_override.items():
            kept.loc[kept["fg_id"] == int(fid), "team"] = new_team

    rng = np.random.default_rng(seed)
    teams = sorted(kept["team"].unique())
    finish_count = {place: {t: 0 for t in teams} for place in range(1, payout_spots + 1)}

    for _ in range(B):
        jittered = _jitter_keeper_lines(kept, rng, shock_scale)
        rows = []
        for team, grp in jittered.groupby("team"):
            is_pit = grp["role"] == "PIT"
            empty_hit = max(C.N_HIT_SLOTS - int((~is_pit).sum()), 0)
            empty_pit = max(C.N_PIT_SLOTS - int(is_pit.sum()), 0)
            h = {c: float(grp.loc[~is_pit, c].sum()) + empty_hit * float(repl_hit[c])
                 for c in _KEEPER_HIT_COLS}
            p = {c: float(grp.loc[is_pit, c].sum()) + empty_pit * float(repl_pit[c])
                 for c in _KEEPER_PIT_COLS}
            rows.append({
                "team": team,
                "R": h["R"], "HR": h["HR"], "RBI": h["RBI"], "SB": h["SB"],
                "AVG": h["H"] / h["AB"] if h["AB"] else 0.0,
                "W": p["W"], "SV": p["SV"], "K": p["K"],
                "ERA": p["ER"] * 9.0 / p["IP"] if p["IP"] else 0.0,
                "WHIP": (p["BB"] + p["H"]) / p["IP"] if p["IP"] else 0.0,
            })
        wide = pd.DataFrame(rows).set_index("team")
        order = standings_points(wide[C.CATS])["TOTAL"].sort_values(ascending=False)
        for place in range(1, payout_spots + 1):
            finish_count[place][order.index[place - 1]] += 1

    out = pd.DataFrame({"team": teams})
    for place in range(1, payout_spots + 1):
        out[f"p_finish_{place}"] = [finish_count[place][t] / B for t in teams]
    out["p_money"] = out[[f"p_finish_{p}" for p in range(1, payout_spots + 1)]].sum(axis=1)
    return out.sort_values("p_money", ascending=False).reset_index(drop=True)
