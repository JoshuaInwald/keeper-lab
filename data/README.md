# Data

Not included in this repository. FanGraphs' terms don't clearly permit
redistributing bulk projection/stats exports, and several files are exports
from a private CBS Sports fantasy league (auction prices, keeper lists,
standings) that aren't public data. `out/` contains the generated results and
documentation, so the repo tells a complete story without these — this file
lists exactly what `klab/` expects in `data/` so the pipeline can be
reproduced from scratch.

Every filename below is a hard-coded path in `klab/io.py`, `klab/keeper.py`,
or `scripts/`.

## FanGraphs exports

Custom leaderboard/projection exports, downloaded as CSV from fangraphs.com
(Leaderboards / Projections pages — hitters and pitchers are separate exports
there).

| file | what it is |
|---|---|
| `fg_2026_hitters.csv`, `fg_2026_pitchers.csv` | 2026 season actuals to date |
| `fg_hitters_2022_2026.csv`, `fg_pitchers_2022_2026.csv` | All FG stats, 2022–2026, one row per player-season |
| `fg_ros_hitters.csv`, `fg_ros_pitchers.csv` | ZiPS rest-of-season 2026 projections |
| `fg_zips_dc_2027_hitters_projections.csv`, `fg_zips_dc_2027_pitchers_projections.csv` | ZiPS Depth Charts full-year 2027 projections |
| `fg_zips_dc_2028_hitters_projections.csv`, `fg_zips_dc_2028_pitchers_projections.csv` | ZiPS Depth Charts full-year 2028 projections (out-year, used for multi-year keeper surplus) |

## League exports (CBS Sports, private league)

Not obtainable from anywhere but this league's own CBS commissioner tools —
auction results, keeper submissions, and standings pages.

| file | what it is |
|---|---|
| `draft_2022.csv` … `draft_2025.csv` | Per-year auction results (price paid per player, by team) |
| `draft_salaries_all.csv` | Combined multi-year auction results with FanGraphs player IDs matched in |
| `keepers_2022.csv` … `keepers_2026.csv` | Keeper submissions by season |
| `standings_long_all.csv` | Tidy long-format standings, all categories, all seasons |
| `cbs_rank_2026.csv` | CBS's own player rankings, 2026 |
| `contracts_parsed.csv` | Current salary + contract year (1/2/3/F) per rostered player, parsed from the league's contracts dump |
| `rosters_current.csv`, `rosters_valued.csv` | Current-season rosters by team |
| `franchise_map.csv` | Team name → franchise ID (CBS retroactively applies current names to historical pages, so this resolves renamed franchises across seasons) |

## Reproducing it for a different league

The FanGraphs exports are the general-purpose half and transfer as-is. The
CBS exports are specific to a 10-team, 5×5, $260-budget keeper auction league
(rules in `klab/config.py`) — to point this at a different league, replace
the CBS files with equivalent exports from that league's own commissioner
tools, matching the columns the loaders in `klab/io.py` expect.
