"""One entry point for any interface — UI, notebook, or script.

Everything a front end needs comes from `snapshot()`. It returns a single
object with the board, the free-agent pool, league summaries, model constants
and the projected standings, all built once and cached, so a UI can re-render
without recomputing.

    from klab.api import snapshot
    s = snapshot()
    s.board            # 275 rostered players, valued
    s.free_agents      # unrostered players with their live contracts
    s.teams            # per-team keeper sets, budget, inflation
    s.constants        # every fitted number, for display
    s.standings        # 2026 actual + projected finish

Rebuilding costs ~2.7s cold and ~0.1s warm. `write_snapshot()` persists a
dated copy so values can be tracked over time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from . import config as C
from .board import build_board, fit_exchange_rate, value_players
from .freeagents import free_agent_board
from .io import cached, load_standings_long
from .trade import standings_points


@dataclass
class Snapshot:
    board: pd.DataFrame
    free_agents: pd.DataFrame
    teams: pd.DataFrame
    standings: pd.DataFrame
    constants: dict
    settings: dict = field(default_factory=dict)

    def team(self, name: str) -> pd.DataFrame:
        return self.board[self.board["team"] == name].sort_values(
            "surplus_multiyear", ascending=False)

    def keepers(self, name: str) -> pd.DataFrame:
        d = self.team(name)
        return d[d["keep_2027"]]


def _team_summary(board: pd.DataFrame) -> pd.DataFrame:
    k = board[board["keep_2027"]]
    t = k.groupby("team").agg(
        n_keep=("name", "size"),
        keeper_salary=("keeper_cost", "sum"),
        keeper_value=("redraft_value", "sum"),
        surplus=("surplus_multiyear", "sum"))
    t["auction_budget"] = C.BUDGET - t["keeper_salary"]
    t["roster_size"] = board.groupby("team").size()
    t["committed_salary"] = board.groupby("team")["salary"].sum()
    return t.sort_values("surplus", ascending=False)


def _inflation(board: pd.DataFrame) -> dict:
    k = board[board["keep_2027"]]
    sal, worth = k["keeper_cost"].sum(), k["redraft_value"].sum()
    cap = C.N_TEAMS * C.BUDGET
    rem_sal, rem_worth = cap - sal, cap - worth
    rate = rem_sal / rem_worth if rem_worth else np.nan
    return {
        "keeper_salary": float(sal), "keeper_worth": float(worth),
        "aggregate_surplus": float(worth - sal),
        "remaining_budget": float(rem_sal), "remaining_worth": float(rem_worth),
        "inflation": float(rate),
        "dollar_buys": float(1 / rate) if rate else np.nan,
    }


@cached
def snapshot(positional: bool = False) -> Snapshot:
    """`positional=True` (out/FINDINGS.md #52) prices catchers and
    shortstops against their own position's replacement level instead of
    the pooled one; every other position is unaffected. Cached per
    argument value like everything else `klab.io.cached()` wraps, so
    `snapshot()` and `snapshot(positional=True)` are two independent,
    correctly-separate cache entries, not one that flips underneath you."""
    board, exch, meta = build_board(positional=positional)
    fa = free_agent_board(positional=positional)

    st = load_standings_long()
    cur = st[st["season"] == 2026].pivot(index="team", columns="category",
                                         values="total")
    pts = standings_points(cur[C.CATS])
    standings = pd.DataFrame({"points_2026": pts["TOTAL"]}).join(
        pts[C.CATS].add_suffix("_pts")).sort_values("points_2026", ascending=False)

    constants = {
        "usd_per_roto_point_auction": exch["usd_per_point"],
        "usd_per_roto_point_redraft": meta["usd_per_rp_redraft"],
        "auction_intercept": exch["intercept"],
        "replacement_roto_points": meta["replacement_rp"],
        "budget_check_top230": meta["budget_check_top230"],
        "denominators": meta["denominators"],
        "exchange_basis": exch.get("basis"),
        **_inflation(board),
    }
    settings = {k: getattr(C, k) for k in [
        "DENOM_SEASONS", "AUCTION_SEASONS", "EXCHANGE_BASIS", "PROJECTION_BASIS",
        "WAIVER_VALUE", "POSITIONAL_ADJUSTMENT", "FUTURE_YEAR_DISCOUNT",
        "SV_PUNT_THRESHOLD", "MAX_PT_SCALE"]}

    return Snapshot(board=board, free_agents=fa, teams=_team_summary(board),
                    standings=standings, constants=constants, settings=settings)


def write_snapshot(tag: str | None = None) -> str:
    """Persist a dated copy so values can be tracked over time.

    Parquet rather than DuckDB for now: no extra dependency, and a directory
    of dated files is enough to answer "how has this moved" until there is a
    reason for a real database.
    """
    s = snapshot()
    stamp = tag or date.today().isoformat()
    out = C.OUT / "snapshots" / stamp
    out.mkdir(parents=True, exist_ok=True)
    for name, df in [("board", s.board), ("free_agents", s.free_agents),
                     ("teams", s.teams.reset_index()),
                     ("standings", s.standings.reset_index())]:
        df.to_parquet(out / f"{name}.parquet", index=False)
    pd.Series(
        {k: str(v) for k, v in {**s.constants, **s.settings}.items()}
    ).to_frame("value").to_parquet(out / "constants.parquet")
    return str(out)


def load_snapshots() -> pd.DataFrame:
    """Every persisted snapshot's board, stacked, with a `snapshot` column."""
    root = C.OUT / "snapshots"
    if not root.exists():
        return pd.DataFrame()
    frames = []
    for d in sorted(root.iterdir()):
        f = d / "board.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            df["snapshot"] = d.name
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
