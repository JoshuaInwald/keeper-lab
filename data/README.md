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
| `fg_catchers_2026.csv`, `fg_shortstops_2026.csv` | FanGraphs batting leaderboard, filtered to every player with ≥1 PA at C / at SS in 2026 — the eligibility set the positional-adjustment toggle checks membership against (`docs/FINDINGS.md` #52). No Position column; eligibility is which file a player's row appears in, not a labeled field. |

## Public reference data

| file | what it is |
|---|---|
| `chadwick_register.csv` | Chadwick Bureau player register, filtered to the ~21k players carrying a FanGraphs id. Columns: `key_fangraphs` (this repo's `fg_id`), `key_mlbam`, `key_bbref` (the join for the Marcel archive), name, birth date. The only source of **age** in the project — no FanGraphs or CBS export here carries it (`docs/METHODS.md` section 3 #18). Feeds `scripts/price_features.py`. Unlike everything else in `data/`, this one is public and scripted: rebuild with `PYTHONPATH=.:scripts python3 scripts/fetch_chadwick.py`. Covers 98% of players in the auction history; the misses are 2026 prospects and NPB imports whose FanGraphs ids postdate the register. |

## Marcel projection archive (Baseball-Reference, public)

| file | what it is |
|---|---|
| `marcel_2024_hitters.csv`, `marcel_2024_pitchers.csv` | Marcel projections **for the 2024 season**, published before it was played |
| `marcel_2025_hitters.csv`, `marcel_2025_pitchers.csv` | Marcel projections for the 2025 season |
| `marcel_2026_hitters.csv`, `marcel_2026_pitchers.csv` | Marcel projections for the 2026 season |

The file year is the season being **projected**, not the Baseball-Reference page it came from: BR files the 2026 projections under `/leagues/majors/2025-projections.shtml`. Read them through `klab/marcel.py`, never with a bare `read_csv` (see `docs/FINDINGS.md` #67 for the three traps).

These are the first ex-ante projections in the project for seasons that have since been played, which is what unblocks the blend weights, the pool rule, and the only out-of-sample test of the keep/cut advice. **Marcel is not ZiPS**: it is Tom Tango's deliberately naive baseline (three-year weighted average, regressed to the mean, flat age adjustment) and is the bar a real system is supposed to clear, not a substitute for one.

Every row carries `Name-additional`, a Baseball-Reference player id, which joins to `fg_id` through `key_bbref` in `chadwick_register.csv` at 100% coverage on all six files. The id is in the page DOM but **not** in the visible pitcher table, so copy-pasting that table off the page loses it.

`Rel` is Marcel's reliability weight: the share of the projection carried by the player's own record rather than regression to the league mean. Kept as `rel` on a 0-1 scale. Median is 0.70-0.72 for hitters and 0.47-0.49 for pitchers, and 21-26% of pitcher rows sit below 0.30, which is mostly league mean wearing a player's name. Any backtest that scores those rows as forecasts is scoring the league mean.

Refresh: not needed for the seasons above; BR keeps historical pages up. To add a season, see the extraction note in `docs/FINDINGS.md` #67 (BR returns 403 to automated fetches, so this came out of a browser session).

## League exports (CBS Sports, private league)

Not obtainable from anywhere but this league's own CBS commissioner tools —
auction results, keeper submissions, and standings pages.

| file | what it is |
|---|---|
| `draft_2022.csv` … `draft_2025.csv` | Per-year auction results (price paid per player, by team) |
| `draft_salaries_all.csv` | Combined multi-year auction results with FanGraphs player IDs matched in |
| `keepers_2022.csv` … `keepers_2026.csv` | Keeper submissions by season |
| `positions_2026.csv` | `fg_id` → primary position for every rostered player. Hitters are the primary position off the league's contracts page; pitchers are classified SP/RP by career starts share (GS/G ≥ 0.5), derived rather than entered. Feeds `klab.keeper.position_map()`, which previously left 48% of the roster with no position at all (`docs/FINDINGS.md` #61). Rebuild whenever rosters change materially. |
| `standings_long_all.csv` | Tidy long-format standings, all categories, all seasons |
| `cbs_rank_2026.csv` | CBS's own player rankings, 2026 |
| `contracts_parsed.csv` | Current salary + contract year (1/2/3/F) per rostered player, parsed from the league's contracts dump |
| `rosters_current.csv`, `rosters_valued.csv` | Current-season rosters by team |
| `franchise_map.csv` | Team name → franchise ID (CBS retroactively applies current names to historical pages, so this resolves renamed franchises across seasons) |

## Where the master copies live, and how to refresh them

The editable master copy of almost every file above lives in
**`~/Documents/Fantasy Baseball/`** on Josh's machine — not in this repo
(`data/` is gitignored) and not uniquely in this project's `data/` folder
either. This project's `data/` is a **working copy**: when a file changes in
Documents, copy it into `data/` here before rebuilding
(`PYTHONPATH=.:scripts python3 scripts/run_all.py`). Nothing auto-syncs.

**Exception — six files exist only in this project's `data/`, nowhere
else:** `contracts_parsed.csv`, `rosters_current.csv`, `rosters_valued.csv`,
`cbs_rank_2026.csv`, `fg_catchers_2026.csv`, `fg_shortstops_2026.csv`. The
first four were produced directly here (`contracts_parsed.csv`
via LLM-assisted parsing of a CBS contracts dump — see `docs/METHODS.md` section 1
§2 for the parsing rules that were reverse-engineered) and never copied back
to Documents. The raw contracts dump they were parsed from (`contracts_raw.txt`
in the old handoff docs) no longer exists on disk anywhere. The last two
were downloaded straight from FanGraphs into this project's `data/`
(2026-08-13) and never routed through Documents either. Since `data/` isn't
in git, these six files currently have **no backup** — worth copying into
Documents, or committing somewhere private, before this folder is ever
wiped.

| file(s) | source | refresh trigger | how |
|---|---|---|---|
| `fg_2026_hitters.csv`, `fg_2026_pitchers.csv` | FanGraphs leaderboard export | in-season, whenever you want current standings to reflect games actually played; stale within days | manual CSV export from FanGraphs |
| `fg_ros_hitters.csv`, `fg_ros_pitchers.csv` | FanGraphs ZiPS rest-of-season | in-season only; ROS projections drift as playing time is used up — refresh weekly-ish if you're actively trading | manual export |
| `fg_zips_dc_2027_*`, `fg_zips_dc_2028_*` | FanGraphs ZiPS Depth Charts, full-year | FanGraphs reruns these a handful of times a year; refresh before any keeper decision or the auction itself | manual export |
| `chadwick_register.csv` | Chadwick Bureau register on GitHub | once a season, or when a newly-drafted prospect misses the age join | `PYTHONPATH=.:scripts python3 scripts/fetch_chadwick.py` (the only scripted refresh in this table) |
| `fg_hitters_2022_2026.csv`, `fg_pitchers_2022_2026.csv` | FanGraphs multi-year leaderboard | once a season, after it closes — append the year that just finished | manual export |
| `fg_catchers_2026.csv`, `fg_shortstops_2026.csv` | FanGraphs batting leaderboard, filtered by position | once a season is enough — eligibility (who has played the position at all) rarely changes mid-season; refresh if a new player debuts there | manual export from FanGraphs, filtered to the position in the leaderboard query |
| `draft_20XX.csv`, `draft_salaries_all.csv` | CBS auction results | once a year, right after the auction | manual export from CBS |
| `keepers_20XX.csv` | CBS keeper submissions | once a year, at the keeper deadline | manual export |
| `standings_20XX.csv`, `standings_long_all.csv` | CBS standings page | in-season if you want live trade evaluation to be accurate; final once the season ends | manual export |
| `contracts_parsed.csv` | CBS contracts dump | whenever a contract changes — trade, extension, FA signing | no standalone script; paste the raw dump to an LLM session and re-derive using the code-semantics in `docs/METHODS.md` section 1 §2 |
| `rosters_current.csv`, `rosters_valued.csv` | CBS rosters | whenever rosters move, ideally right before any fresh valuation run | manual export |
| `positions_2026.csv` | league contracts page (hitters) + FanGraphs GS/G (pitchers) | whenever a player joins the league who has never been bought at auction | hitters transcribed from the contracts dump, pitchers derived; see `docs/FINDINGS.md` #61 |
| `cbs_rank_2026.csv` | CBS's own rankings | optional, informational only | manual export |
| `franchise_map.csv` | hand-maintained | only when a franchise renames | manual edit |

## Reproducing it for a different league

The FanGraphs exports are the general-purpose half and transfer as-is. The
CBS exports are specific to a 10-team, 5×5, $260-budget keeper auction league
(rules in `klab/config.py`) — to point this at a different league, replace
the CBS files with equivalent exports from that league's own commissioner
tools, matching the columns the loaders in `klab/io.py` expect.
