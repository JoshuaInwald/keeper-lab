"""Loaders + player-name resolution.

Everything downstream joins on FanGraphs PlayerId (`fg_id`, int). The draft
CSVs for 2022/2023 carry names only, so this module owns the name matcher.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from functools import wraps

import numpy as np
import pandas as pd

from .config import DATA


def cached(fn):
    """Memoise a loader on its arguments, handing back a copy each time.

    Copying on the way out keeps the cache immutable, so a caller that
    mutates its result cannot corrupt the next one. Keys on args only, not
    on module globals such as config.PROJECTION_BASIS (docs/FINDINGS.md #42).
    """
    cache = {}

    def _key(args, kwargs):
        """Hashable key, or None if any argument can't be one (lists become
        tuples; DataFrame/dict arguments bypass the cache)."""
        try:
            norm = tuple(tuple(a) if isinstance(a, list) else a for a in args)
            kv = tuple(sorted(
                (k, tuple(v) if isinstance(v, list) else v)
                for k, v in kwargs.items()))
            key = (norm, kv)
            hash(key)
            return key
        except TypeError:
            return None

    @wraps(fn)
    def wrapper(*args, **kwargs):
        key = _key(args, kwargs)
        if key is None:
            return fn(*args, **kwargs)
        if key not in cache:
            cache[key] = fn(*args, **kwargs)
        out = cache[key]
        return out.copy() if isinstance(out, (pd.DataFrame, pd.Series)) else out

    wrapper.cache_clear = cache.clear
    return wrapper

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}


def norm_name(s: str) -> str:
    """Accent-stripped, punctuation-free, suffix-free, lowercase name."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().replace("&nbsp;", " ")
    s = re.sub(r"[^a-z\s]", " ", s)
    parts = [p for p in s.split() if p and p not in SUFFIXES]
    return " ".join(parts)


def name_key(s: str) -> str:
    """First-initial + last name, e.g. 'b witt'. Collision-prone but useful."""
    n = norm_name(s)
    if not n:
        return ""
    parts = n.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0][0]} {parts[-1]}"


# --- FanGraphs stat loads ---------------------------------------------------

@cached
def load_hitters_history() -> pd.DataFrame:
    df = pd.read_csv(DATA / "fg_hitters_2022_2026.csv")
    df = df.rename(columns={"PlayerId": "fg_id", "Season": "season", "Name": "name"})
    df["fg_id"] = pd.to_numeric(df["fg_id"], errors="coerce")
    df = df.dropna(subset=["fg_id"])
    df["fg_id"] = df["fg_id"].astype(int)
    df["role"] = "HIT"
    return df


@cached
def load_pitchers_history() -> pd.DataFrame:
    df = pd.read_csv(DATA / "fg_pitchers_2022_2026.csv")
    df = df.rename(
        columns={"PlayerId": "fg_id", "Season": "season", "Name": "name",
                 "H_allowed": "H"}
    )
    df["fg_id"] = pd.to_numeric(df["fg_id"], errors="coerce")
    df = df.dropna(subset=["fg_id"])
    df["fg_id"] = df["fg_id"].astype(int)
    df["role"] = "PIT"
    # FanGraphs writes innings in thirds notation: 132.1 is 132 + 1/3, not
    # 132.1. Everything downstream sums and divides IP as a decimal, so a
    # 9-pitcher staff lost up to ~4 innings and every ERA/WHIP denominator was
    # computed on the wrong base. The ROS export is whole innings and ZiPS uses
    # true decimals (.3/.7), so the actuals were the one file on a different
    # convention and were being blended against the others (docs/FINDINGS.md #58).
    ip = df["IP"].astype(float)
    df["IP"] = np.floor(ip) + (ip - np.floor(ip)) * 10.0 / 3.0
    return df


@cached
def mlb_team_map() -> pd.Series:
    """fg_id -> current (2026) real MLB team, for display only -- never used
    in valuation. The FanGraphs "- - -" combined row for a traded player is
    dropped; the single-team row with the most games wins (an approximation
    for a very recent trade -- no transaction-date file exists)."""
    h = load_hitters_history()
    p = load_pitchers_history()
    both = pd.concat([h[h["season"] == 2026], p[p["season"] == 2026]], ignore_index=True)
    both = both[both["Team"] != "- - -"]
    both = both.sort_values("G", ascending=False)
    return both.drop_duplicates("fg_id", keep="first").set_index("fg_id")["Team"]


def _read_fg_projection(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.replace("﻿", "").strip() for c in df.columns]
    df = df.rename(columns={"PlayerId": "fg_id", "Name": "name"})
    df["fg_id"] = pd.to_numeric(df["fg_id"], errors="coerce")
    df = df.dropna(subset=["fg_id"])
    df["fg_id"] = df["fg_id"].astype(int)
    return df


@cached
def load_ros_hitters():
    return _read_fg_projection(DATA / "fg_ros_hitters.csv")


@cached
def load_ros_pitchers():
    return _read_fg_projection(DATA / "fg_ros_pitchers.csv")


@cached
def load_position_eligibility() -> dict:
    """fg_id sets for catcher and shortstop (docs/FINDINGS.md #52). Each file
    is a FanGraphs leaderboard export pre-filtered by position; the export
    carries no position column, so the file a player came from IS the label.
    A player in both files is eligible for both -- `two_position_replacement()`
    decides which applies.
    """
    c = _read_fg_projection(DATA / "fg_catchers_2026.csv")
    ss = _read_fg_projection(DATA / "fg_shortstops_2026.csv")
    return {"C": set(c["fg_id"]), "SS": set(ss["fg_id"])}


@cached
def load_zips27_hitters():
    from . import config as C
    return _read_fg_projection(DATA / C.PROJ_2027_HITTERS)


@cached
def load_zips27_pitchers():
    from . import config as C
    return _read_fg_projection(DATA / C.PROJ_2027_PITCHERS)


# --- League data ------------------------------------------------------------

@cached
def load_standings_long() -> pd.DataFrame:
    df = pd.read_csv(DATA / "standings_long_all.csv")
    df["category"] = df["category"].replace({"BA": "AVG"})
    return df


@cached
def load_drafts() -> pd.DataFrame:
    """All auction results 2022-2025 plus the 2026 rows in draft_salaries_all."""
    frames = []
    for year in (2022, 2023, 2024, 2025):
        d = pd.read_csv(DATA / f"draft_{year}.csv")
        d = d.rename(columns={"Season": "season", "Team": "team",
                              "Player": "player", "Salary": "salary",
                              "Pos": "pos"})
        frames.append(d[["season", "team", "player", "salary", "pos"]])

    allsal = pd.read_csv(DATA / "draft_salaries_all.csv")
    d26 = allsal[allsal["year"] == 2026].rename(
        columns={"year": "season", "fantasy_team_raw": "team"}
    )
    d26["pos"] = None
    frames.append(d26[["season", "team", "player", "salary", "pos", "fg_id"]])

    out = pd.concat(frames, ignore_index=True)
    if "fg_id" not in out:
        out["fg_id"] = pd.NA
    out["fg_id"] = pd.to_numeric(out["fg_id"], errors="coerce")
    return out


@cached
def load_draft_ids() -> pd.DataFrame:
    """The prior session's name->fg_id map for 2024-2026 drafts (authoritative).

    Some ids are FanGraphs minor-league keys ('sa3020472'); those players have
    no MLB stat line to join to, so they are dropped and fall through to the
    name resolver.
    """
    d = pd.read_csv(DATA / "draft_salaries_all.csv")
    d["fg_id"] = pd.to_numeric(d["fg_id"], errors="coerce")
    d = d.dropna(subset=["fg_id"])
    d["fg_id"] = d["fg_id"].astype(int)
    return d.rename(columns={"year": "season", "fantasy_team_raw": "team"})


@cached
def load_contracts() -> pd.DataFrame:
    p = DATA / "contracts_parsed.csv"
    df = pd.read_csv(p)
    df["fg_id"] = pd.to_numeric(df["fg_id"], errors="coerce")
    df = df.dropna(subset=["fg_id"])
    df["fg_id"] = df["fg_id"].astype(int)
    return df


@cached
def load_rosters() -> pd.DataFrame:
    p = DATA / "rosters_valued.csv"
    df = pd.read_csv(p)
    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce")
    df = df.dropna(subset=["player_id"])
    df["player_id"] = df["player_id"].astype(int)
    return df.rename(columns={"player_id": "fg_id"})


# --- Name resolution --------------------------------------------------------

class NameResolver:
    """Resolve free-text player names to FanGraphs ids within a season pool."""

    def __init__(self, pool: pd.DataFrame):
        """pool needs columns: season, fg_id, name, role, and a size column
        `weight` used to break ties toward the more prominent player."""
        self.pool = pool.copy()
        self.pool["nname"] = self.pool["name"].map(norm_name)
        self.pool["nkey"] = self.pool["name"].map(name_key)
        # Dict indices built from one weight-sorted pass: first row per key
        # = highest-weight player wins ties, without a frame scan per lookup.
        srt = self.pool.sort_values("weight", ascending=False)
        self._by_season = {s: g for s, g in self.pool.groupby("season")}

        def index(df, keycols):
            first = df.drop_duplicates(keycols)
            return dict(zip(map(tuple, first[keycols].to_numpy()), first["fg_id"]))

        # Role-aware variants so a role= lookup never falls through to a scan.
        self._exact = index(srt, ["season", "nname"])
        self._keyed = index(srt, ["season", "nkey"])
        self._exact_r = index(srt, ["season", "role", "nname"])
        self._keyed_r = index(srt, ["season", "role", "nkey"])
        self._keyed_n = srt.groupby(["season", "nkey"]).size().to_dict()

    def _candidates(self, season):
        return self._by_season.get(season, self.pool.iloc[:0])

    def resolve(self, name, season, role=None):
        n, k = norm_name(name), name_key(name)

        # Dict lookups first; scan the frame only if both miss.
        ex = self._exact_r.get((season, role, n)) if role else self._exact.get((season, n))
        if ex is not None:
            return int(ex), "exact", 1.0
        ky = self._keyed_r.get((season, role, k)) if role else self._keyed.get((season, k))
        if ky is not None:
            cnt = self._keyed_n.get((season, k), 1)
            tag = "initial_last" if cnt == 1 else "initial_last_ambig"
            return int(ky), tag, 0.9 if cnt == 1 else 0.7

        cand = self._candidates(season)
        if role:
            cand = cand[cand["role"] == role]
        if cand.empty:
            return None, "no_pool", 0.0

        last = n.split()[-1] if n else ""
        sub = cand[cand["nname"].str.endswith(" " + last) | (cand["nname"] == last)]
        if len(sub) == 1:
            return int(sub.iloc[0]["fg_id"]), "lastname", 0.8

        scored = [
            (SequenceMatcher(None, n, r.nname).ratio(), r.fg_id, r.weight)
            for r in cand.itertuples()
        ]
        scored.sort(key=lambda t: (t[0], t[2]), reverse=True)
        if scored and scored[0][0] >= 0.86:
            return int(scored[0][1]), "fuzzy", float(scored[0][0])
        return None, "unmatched", float(scored[0][0]) if scored else 0.0
