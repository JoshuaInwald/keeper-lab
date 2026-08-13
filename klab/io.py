"""Loaders + player-name resolution.

Everything downstream joins on FanGraphs PlayerId (`fg_id`, int). The draft
CSVs for 2022/2023 carry names only, so this module owns the name matcher.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache, wraps

import pandas as pd

from .config import DATA


def cached(fn):
    """Memoise a zero-argument loader, handing back a copy each time.

    Every script rebuilds the board from scratch, and a single run was
    re-parsing the same CSVs three or four times: `build_board` calls
    `project_all_players` twice, `fit_exchange_rate` and `value_2028` each
    re-derive the scorer, and every script calls two or three of those in
    sequence. Copying on the way out keeps the cache immutable, so a caller
    that mutates its result cannot corrupt the next one.
    """
    cache = {}

    def _key(args, kwargs):
        """Hashable key, or None if any argument can't be one.

        Lists become tuples so `team_baselines([2024, 2025])` still caches.
        A DataFrame argument (sigma_rel, an exchange-rate dict) is not
        hashable and not worth hashing, so those calls bypass the cache
        rather than risk a stale or wrong hit.
        """
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
    return df


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
        # Lookup indices, built with one sort instead of a groupby per key.
        # Filtering an 11k-row frame inside every lookup was the hottest line
        # in the build (570 lookups x a full boolean scan); the obvious fix --
        # a dict of per-key sub-frames -- turned out to be worse, because
        # materialising ~14k tiny DataFrames costs more than it saves. Sorting
        # once by weight and keeping the first row per key gives the same
        # answer (highest-weight player wins ties) at a fraction of the cost.
        srt = self.pool.sort_values("weight", ascending=False)
        self._by_season = {s: g for s, g in self.pool.groupby("season")}

        def index(df, keycols):
            first = df.drop_duplicates(keycols)
            return dict(zip(map(tuple, first[keycols].to_numpy()), first["fg_id"]))

        # Two indices: one keyed on season alone and one that also keys on
        # role. Callers who know a player is a pitcher pass role=, and without
        # a role-aware index every one of those lookups fell through to a
        # DataFrame scan -- which was most of the 285 lookups per build.
        self._exact = index(srt, ["season", "nname"])
        self._keyed = index(srt, ["season", "nkey"])
        self._exact_r = index(srt, ["season", "role", "nname"])
        self._keyed_r = index(srt, ["season", "role", "nkey"])
        self._keyed_n = srt.groupby(["season", "nkey"]).size().to_dict()

    def _candidates(self, season):
        return self._by_season.get(season, self.pool.iloc[:0])

    def resolve(self, name, season, role=None):
        n, k = norm_name(name), name_key(name)

        # Dict lookups first, role-aware when a role is known. Only fall back
        # to scanning the frame if both miss.
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
