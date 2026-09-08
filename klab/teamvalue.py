"""Team-specific category value (docs/ROADMAP.md item 2).

Roto points add linearly today: `denoms.py` divides a player's units in a
category by ONE league-wide denominator, so a stolen base is worth the same to
every team. It is not. A team 20 steals behind fourth place gains a standings
point from the next ten steals; a team already first in steals gains nothing at
all from them.

The fix reuses the whole existing machinery. `rp_c = units / denominator_c`
already; this replaces the pooled `denominator_c` with a LOCAL one per team:
how many units THIS team needs to gain one standings point from where it
actually sits. Everything downstream (dollars, surplus, trade evaluation) then
works unchanged, because it is still roto points.

The local denominator is the mean gap between adjacent teams in a window around
the team's own rank, not the single gap to the next team up. A raw
next-team-up gap is unusable: it is 0.1 units when two teams are tied and 50
when a team is isolated, so it would swing a player's value by 100x on standings
noise. A window of +/- `WINDOW` ranks (four gaps by default) keeps the real
signal, which is "tight pack versus isolated", and drops the spikes.

Nothing here is wired into the board. This is the scoping build ROADMAP item 2
asks for; `scripts/team_category_value.py` reports what it would change.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .trade import standings_points

WINDOW = 2          # ranks either side; 2 -> up to four adjacent gaps
HIT_COLS = ["AB", "H", "HR", "R", "RBI", "SB"]
PIT_COLS = ["IP", "W", "SV", "K", "ER", "BB", "H"]      # "H" is hits allowed


def team_volumes_2027(board: pd.DataFrame, fa: pd.DataFrame,
                      replacement_rp: float) -> pd.DataFrame:
    """Each team's projected 2027 category volumes from its keeper core, every
    open slot filled at replacement level.

    Same construction as `build_app._keeper_standings_2027`, including the
    15-player replacement BAND rather than the single nearest player (that once
    landed on a closer and gave every team 25 free saves), but it returns the
    raw volumes so they can be perturbed.
    """
    pool = pd.concat([board, fa], ignore_index=True)

    def repl_line(p, cols, n=15):
        d = (p["roto_points"] - replacement_rp).abs()
        return p.loc[d.nsmallest(n).index, cols].mean()

    repl_hit = repl_line(pool[pool["role"] != "PIT"], HIT_COLS)
    repl_pit = repl_line(pool[pool["role"] == "PIT"], PIT_COLS)

    rows = []
    for team, grp in board[board["keep_2027"]].groupby("team"):
        is_pit = grp["role"] == "PIT"
        eh = max(C.N_HIT_SLOTS - int((~is_pit).sum()), 0)
        ep = max(C.N_PIT_SLOTS - int(is_pit.sum()), 0)
        r = {"team": team}
        r.update({c: float(grp.loc[~is_pit, c].sum()) + eh * float(repl_hit[c])
                  for c in HIT_COLS})
        r.update({f"p_{c}": float(grp.loc[is_pit, c].sum()) + ep * float(repl_pit[c])
                  for c in PIT_COLS})
        rows.append(r)
    return pd.DataFrame(rows).set_index("team")


def rate_totals(v: pd.DataFrame) -> pd.DataFrame:
    """Category totals in the units standings are kept in."""
    out = pd.DataFrame(index=v.index)
    for c in ("R", "HR", "RBI", "SB"):
        out[c] = v[c]
    out["AVG"] = v["H"] / v["AB"].replace(0, np.nan)
    for c in ("W", "SV", "K"):
        out[c] = v[f"p_{c}"]
    ip = v["p_IP"].replace(0, np.nan)
    out["ERA"] = v["p_ER"] * 9.0 / ip
    out["WHIP"] = (v["p_BB"] + v["p_H"]) / ip
    return out[list(C.CATS)]


def local_denominators(totals: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Units this team needs to gain one standings point, per category.

    Mean absolute gap between adjacent teams within `window` ranks either side
    of the team's own position. Degenerate cases (every team tied) fall back to
    the pooled spread so nothing divides by zero.
    """
    out = pd.DataFrame(index=totals.index, columns=list(C.CATS), dtype=float)
    for c in C.CATS:
        s = totals[c].sort_values()
        gaps = np.diff(s.to_numpy(float))
        pooled = (s.max() - s.min()) / max(len(s) - 1, 1)
        for i, team in enumerate(s.index):
            lo, hi = max(0, i - window), min(len(gaps), i + window)
            w = gaps[lo:hi]
            w = w[np.isfinite(w)]
            d = float(np.mean(w)) if len(w) and np.mean(w) > 0 else float(pooled)
            out.loc[team, c] = d if d > 0 else float(pooled)
    return out


def value_multipliers(totals: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """How much more (or less) a unit of each category is worth to each team
    than the league-average team. 1.0 = the pooled denominator is right."""
    d = local_denominators(totals, window)
    return d.mean(axis=0) / d          # a SMALLER local denominator = worth MORE


def team_player_value(player_rp: pd.DataFrame, mult: pd.DataFrame) -> pd.DataFrame:
    """Re-price every player for every team: the same per-category roto points
    the board already computes, each scaled by that team's multiplier.

    `player_rp` needs the `rp_<cat>` columns; returns one column per team.
    """
    cols = [f"rp_{c}" for c in C.CATS]
    out = {}
    for team in mult.index:
        m = np.array([mult.loc[team, c] for c in C.CATS], dtype=float)
        out[team] = (player_rp[cols].to_numpy(float) * m).sum(axis=1)
    return pd.DataFrame(out, index=player_rp.index)
