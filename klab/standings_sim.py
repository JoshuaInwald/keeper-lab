"""Step 6b: Monte Carlo standings simulation.

"How often does each team finish in the money" under player-OUTCOME
uncertainty (docs/SESSION-LOG.md Phase 5). Deliberately not `klab.uncertainty`'s
bootstrap, which resamples DENOMINATOR uncertainty -- the wrong source for
"will my closer's saves hold up."

`p_money` is P(top `C.PAYOUT_SPOTS`); the 50/25/15/breakeven weighting
(`C.PAYOUT_SHARE`) is not modeled yet.
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

# Shocked column -> RELIABILITY category. Rates are rebuilt downstream in
# _totals_from(), and playing time is not shocked (performance variance only).
_SHOCK_CATEGORY = {
    "H": "H", "HR": "HR", "R": "R", "RBI": "RBI", "SB": "SB",
    "W": "W", "K": "K", "ER": "ER", "BB": "BB", "H_allowed": "H",
}
# Saves have no RELIABILITY entry (a separate persistence model projects
# them); wins' r is the closest proxy -- both opportunity-driven, role-swingy.
_SV_RELIABILITY = RELIABILITY["W"]


def _jitter_ros(ros: pd.DataFrame, rng: np.random.Generator,
                shock_scale: float) -> pd.DataFrame:
    """One shared per-player "hot/cold" shock (a hot player runs hot across
    HR/R/RBI together), scaled per stat by 1 - reliability."""
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
    p_money (any of them), in the rest of 2026.

    `swap` -- {fg_id: new_team} -- answers "what would a trade do to my
    odds." Each draw jitters `ros_lines_for_basis(ros_basis)` and rebuilds
    totals with `klab.trade`'s own helpers so the two cannot drift apart.
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


# --- Stage 3: 2027 keeper-core finish odds (docs/SESSION-LOG.md Phase 5) --------
# No realized baseline here: each KEPT player's full-season line is jittered;
# the replacement fill (a 15-player band average) stays fixed.
_KEEPER_HIT_COLS = ["AB", "H", "HR", "R", "RBI", "SB"]
# "H" on the full-season board IS hits allowed for a pitcher row (no
# H_allowed column here); it shares the "H" RELIABILITY entry on purpose.
_KEEPER_PIT_COLS = ["IP", "W", "SV", "K", "ER", "BB", "H"]
_KEEPER_SHOCK_CATEGORY = {
    "H": "H", "HR": "HR", "R": "R", "RBI": "RBI", "SB": "SB",
    "W": "W", "K": "K", "ER": "ER", "BB": "BB",
}


def _jitter_keeper_lines(kept: pd.DataFrame, rng: np.random.Generator,
                         shock_scale: float) -> pd.DataFrame:
    """`_jitter_ros`'s shared-shock mechanism on full-2027-season lines."""
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
    a real-auction forecast (see `_keeper_standings_2027` in build_app.py).

    `keeper_override` -- {fg_id: new_team} -- reassigns an already-kept
    player's team; it does not decide keep/cut for anyone.
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
