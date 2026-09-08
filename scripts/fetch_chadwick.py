"""Download the Chadwick Bureau register and keep the FanGraphs-keyed subset.

Age is the one bidder-visible feature no file in `data/` carries (docs/METHODS.md
section 3 #18 notes the gap). The register is the public crosswalk: it maps
`key_fangraphs` (this repo's `fg_id`) to a birth date, which is all the price
model needs (docs/ROADMAP.md item 1 Step 1).

Writes `data/chadwick_register.csv` with seven columns and only the ~21k rows
that carry a FanGraphs id: the full register is 16 shards and ~120 MB, which
does not belong in a working tree that is already gitignored. `key_mlbam` rides
along as a second join path (`MLBAMID` is in the FanGraphs history exports).

    PYTHONPATH=.:scripts python3 scripts/fetch_chadwick.py
"""
from __future__ import annotations

import io
import sys
import urllib.request

import pandas as pd

from klab import config as C

BASE = ("https://raw.githubusercontent.com/chadwickbureau/register/"
        "master/data/people-{shard}.csv")
SHARDS = "0123456789abcdef"
KEEP = ["key_fangraphs", "key_mlbam", "name_first", "name_last",
        "birth_year", "birth_month", "birth_day"]


def fetch() -> pd.DataFrame:
    frames = []
    for shard in SHARDS:
        url = BASE.format(shard=shard)
        with urllib.request.urlopen(url, timeout=120) as r:
            raw = r.read()
        d = pd.read_csv(io.BytesIO(raw), usecols=KEEP, low_memory=False)
        d = d[d["key_fangraphs"].notna()]
        frames.append(d)
        print(f"  people-{shard}.csv: {len(d):>6} rows with a FanGraphs id")
    out = pd.concat(frames, ignore_index=True)
    # fg_id is an int everywhere else in this repo; the register stores it as a
    # float because most rows have no FanGraphs entry at all.
    out["key_fangraphs"] = out["key_fangraphs"].astype(int)
    return out.drop_duplicates(subset=["key_fangraphs"]).sort_values("key_fangraphs")


def main() -> int:
    d = fetch()
    path = C.DATA / "chadwick_register.csv"
    d.to_csv(path, index=False)
    print(f"wrote {path}  ({len(d)} players, "
          f"{d['birth_year'].notna().sum()} with a birth year)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
