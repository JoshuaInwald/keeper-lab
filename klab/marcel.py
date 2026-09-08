"""The Marcel projection archive: a second projection source, for backtesting.

Why this exists. Every open question in `docs/ASSESSMENT-BRIEF.md` that Phase A
could not answer was blocked on the same missing artefact: a projection made
BEFORE a season that has since been played. `data/` carries only the ZiPS 2027
and 2028 pulls, so the blend weights were never fitted (Link 1), the pool rule
could not be chosen (#65), and the keep/cut advice had no out-of-sample test
(#66). Baseball-Reference publishes Marcel projections for every season and
keeps them up; three seasons (2024, 2025, 2026) are now in `data/`, and actuals
exist for all three.

Marcel is NOT ZiPS and must not be presented as a substitute for it. Marcel is
Tom Tango's deliberately naive baseline: a weighted average of the prior three
seasons, regressed to the league mean, with a flat age adjustment. It is the
"minimum competence" projection that any real system is expected to beat. What
it gives this project is not a better forecast but a HONEST EX-ANTE ONE, which
is the only thing a backtest needs. Weights fitted against Marcel describe the
Marcel blend, not the ZiPS blend; treat them as a shape, not a transfer.

Three file quirks, all encoded below.

1. Both files carry `Name-additional`, a Baseball-Reference player id, so both
   roles join exactly through `key_bbref` in `data/chadwick_register.csv`. No
   name matching is involved. (The id is in the page DOM but not in the visible
   pitcher table, so a copy-paste of that table loses it; these files were
   extracted from the DOM and keep it.)
2. Baseball-Reference repeats the header row every ~35 lines when rendering.
   The extractor skips those, but the guard stays in case a file is ever
   re-made by hand.
3. Marcel writes whole innings (`157.0`), never thirds notation. The conversion
   `io.py` applies to FanGraphs innings (docs/FINDINGS.md #58) would corrupt
   these. `_read_pitchers` asserts the file has no fractional innings rather
   than trusting the comment.

The `Rel` column is Marcel's reliability weight: the share of the projection
carried by the player's own record against regression to the league mean. It is
kept as `rel` on a 0-1 scale. A 2%-reliability line is almost entirely league
mean wearing a player's name, and any backtest that scores such rows as if they
were forecasts is measuring the league mean.

    from klab.marcel import load_marcel
    h = load_marcel(2025, "HIT")     # projections FOR the 2025 season
"""
from __future__ import annotations

import pandas as pd

from .io import DATA, cached

# Season here is always the season being PROJECTED, not the Baseball-Reference
# page it came from: BR files the 2025 projections under "2024 majors".
SEASONS = (2024, 2025, 2026)

_HIT_RENAME = {"BA": "AVG", "Name-additional": "bbref_id", "Name": "name",
               "Age": "age", "Rel": "rel"}
_PIT_RENAME = {"SO": "K", "Name": "name", "Age": "age", "Rel": "rel",
               "Name-additional": "bbref_id"}

_HIT_COLS = ["PA", "AB", "R", "H", "HR", "RBI", "SB", "AVG"]
_PIT_COLS = ["IP", "W", "SV", "K", "ER", "BB", "H", "ERA", "WHIP"]


def _rel_to_float(s: pd.Series) -> pd.Series:
    """'86%' -> 0.86. Marcel's reliability weight, not a percentage of anything
    else; kept because a low-rel row is mostly league mean (see module docstring).
    """
    return pd.to_numeric(s.astype(str).str.rstrip("%"), errors="coerce") / 100.0


def _read_hitters(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.replace("﻿", "").strip() for c in df.columns]
    df = df.rename(columns=_HIT_RENAME)
    df["rel"] = _rel_to_float(df["rel"])
    for c in _HIT_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # BR lists a traded player once per team plus a combined row; the combined
    # rows are exact duplicates on the id, so last-wins is safe here.
    df = df.drop_duplicates(subset=["bbref_id"], keep="first")
    df["role"] = "HIT"
    return df


def _read_pitchers(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.replace("﻿", "").strip() for c in df.columns]
    df = df.rename(columns=_PIT_RENAME)
    # The header repeats every ~35 rows in BR's rendering; those rows re-read as
    # data with the literal string "Rk" in the rank column.
    df = df[df["Rk"].astype(str).str.strip() != "Rk"]
    df["rel"] = _rel_to_float(df["rel"])
    for c in _PIT_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Marcel rounds to whole innings. If that ever stops being true the thirds
    # question (docs/FINDINGS.md #58) reopens for this source, so fail loudly.
    frac = (df["IP"].dropna() % 1).round(6)
    bad = frac[(frac > 0) & (frac.isin([0.1, 0.2]))]
    if len(bad):
        raise ValueError(
            f"{path}: {len(bad)} innings look like thirds notation (.1/.2). "
            "Marcel is expected to write whole innings; see FINDINGS #58 "
            "before converting anything.")
    df = df.drop_duplicates(subset=["bbref_id"], keep="first")
    df["role"] = "PIT"
    return df


@cached
def load_marcel(season: int, role: str) -> pd.DataFrame:
    """Marcel projections FOR `season`. role is 'HIT' or 'PIT'.

    Raises rather than returning empty: a silently missing projection file would
    make a backtest look like it ran on a season it never saw.
    """
    if role not in ("HIT", "PIT"):
        raise ValueError(f"role must be HIT or PIT, got {role!r}")
    kind = "hitters" if role == "HIT" else "pitchers"
    path = DATA / f"marcel_{season}_{kind}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. Marcel archive files are named for the season "
            f"they PROJECT; see klab/marcel.py and data/README.md.")
    return _read_hitters(path) if role == "HIT" else _read_pitchers(path)


@cached
def marcel_fg_ids(season: int, role: str) -> pd.DataFrame:
    """Marcel rows with an `fg_id` attached, so they join to the rest of the repo.

    Both roles go through `key_bbref` in the Chadwick register, which is an
    exact id-to-id map. The unmatched count is returned on the frame as an
    attribute rather than dropped quietly: a player with no FanGraphs id in the
    register is invisible to the rest of the repo and that has to be visible.
    """
    df = load_marcel(season, role).copy()
    reg = pd.read_csv(DATA / "chadwick_register.csv")
    if "key_bbref" not in reg.columns:
        raise ValueError(
            "chadwick_register.csv has no key_bbref column. Rerun "
            "scripts/fetch_chadwick.py; the Marcel join needs it.")
    reg = reg.dropna(subset=["key_bbref"])
    xwalk = dict(zip(reg["key_bbref"], reg["key_fangraphs"].astype(int)))
    df["fg_id"] = df["bbref_id"].map(xwalk)

    df.attrs["n_unmatched"] = int(df["fg_id"].isna().sum())
    df.attrs["n_total"] = int(len(df))
    return df
