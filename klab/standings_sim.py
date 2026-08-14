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
