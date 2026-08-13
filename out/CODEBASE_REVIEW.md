# Codebase review — what I changed, how I found it, and whether it mattered

Method: profile first, then fix what the profile actually shows. Every change
below was verified to leave the output **byte-identical** (275 rows × 57
columns, zero numeric differences beyond float noise), and name matching
unchanged at 671/677.

**Net result: a full script run went from 10.7s to 2.67s (4×). A second
`build_board()` in the same process went from 2.2s to 0.075s (29×).**

---

## 1. Everything was computed three or four times — memoisation. *Significant.*

**How I found it.** I wrapped the top-level functions in counters and ran one
`build_board()`. The result: `pooled_relative_dispersion`, `team_baselines`,
`season_levels`, `teams_per_category` and `fit_save_model` each ran **3×**;
`project_hitters` and `project_pitchers` **2×**. A typical script calls
`fit_exchange_rate` → `value_players` → `build_board`, so the same CSVs were
being parsed and the same regressions refitted up to a dozen times.

The structural cause: `build_board` calls `project_all_players` twice (once
scaled, once not), `value_2028` rebuilds the scorer, and each of those
re-derives the denominators from scratch. Nothing was wrong — each function is
pure and self-sufficient, which is good design — but nothing memoised either.

**Fix.** A small `cached` decorator in `io.py` on the loaders and the pure
derived objects. Two details matter:

- **It returns a copy.** Handing out the cached DataFrame itself would let one
  caller's mutation corrupt the next caller's data — the classic shared-mutable
  bug. Copying costs microseconds and makes the cache safe.
- **It degrades gracefully.** Keys are built from the arguments, with lists
  normalised to tuples; if any argument is unhashable (a DataFrame, a config
  dict) the call bypasses the cache rather than risking a wrong hit.

**Impact:** the largest single win, and the one that compounds — warm rebuilds
are now effectively free, which is what makes an interactive UI viable.

---

## 2. The name resolver rescanned an 11k-row frame on every lookup. *Significant — and my first fix made it worse.*

**How I found it.** `cProfile` sorted by cumulative time put
`io.py:173(resolve)` at **2.5 of 7.7 seconds** — a third of the whole build,
for 570 name lookups.

The cause was `self.pool[self.pool["season"] == season]` inside `resolve`: a
full boolean scan of every row, 570 times.

**First attempt, which backfired.** I pre-split the pool into a dict of
per-key sub-DataFrames. Re-profiling showed 14,573 `nargsort` and 14,334
`_chop` calls — materialising ~14,000 tiny DataFrames at construction cost
more than the scans it saved. **A good instinct implemented at the wrong
granularity.**

**Fix that worked.** Sort the pool by weight once, then build plain
`dict[(season, name)] → fg_id` lookups, keeping the first row per key
(highest weight wins ties, which is the same tie-break as before). Each
lookup becomes a dict hit; construction is one sort.

**Impact:** removed the single hottest line, and the failed intermediate is
the useful lesson — always re-profile after optimising.

---

## 3. Two `groupby` aggregations ran Python callbacks per group. *Moderate.*

**How I found it.** The second profile still showed heavy time in
`_aggregate_series_pure_python` — pandas' fallback when an aggregation can't
be vectorised.

The culprits were two lambdas:

```python
agg["role"] = lambda s: "TWO" if s.nunique() > 1 else s.iloc[0]   # ~2,000 groups
agg["role"] = lambda r: "HIT" if "HIT" in set(r) else "PIT"       # ~12,000 groups
```

Each forces pandas out of its C path and into a Python call per group.

**Fix.** Carry the information as numeric flags (`is_hit`, `_hit`/`_pit`),
aggregate with `max`, and resolve the label afterwards with `np.where`. Same
answer, vectorised throughout.

---

## 4. Data storage — one real finding, deliberately not acted on

The ZiPS and rest-of-season exports are **74 columns wide and we read 9 of
them**. They account for 1.78 MB of the 3.28 MB data directory; pruning to the
used columns would cut that to ~0.23 MB.

**I did not do this**, for two reasons. The unused columns are the P10–P90
percentile bands, which are the input for the planned prospect-upside work
(roadmap 3.2) — pruning them now would mean re-downloading later. And with
loaders memoised, each file is parsed once per process, so the parse cost is
already amortised to near zero. The bloat is real but it is neither a
performance problem nor free to reverse.

Worth doing eventually: `pd.read_csv(..., usecols=...)` gives the parse saving
without deleting anything.

**Genuinely unused files** in `data/`: `fg_2026_hitters.csv`,
`fg_2026_pitchers.csv` (superseded by the 2022–26 files; retained because the
peripheral columns — FIP, xERA — were what settled the Christian Scott
question), `rosters_current.csv`, `franchise_map.csv`, `keepers_*.csv`,
`league_report.html`, `legends_league_v14.xlsx`. None are loaded by `klab/`.
They cost 1.5 MB and nothing else; keeping them is fine, but they should not
be mistaken for live inputs.

---

## 5. What I looked at and found healthy

- **Module boundaries.** `config → io → denoms → auction → project → keeper →
  board → trade` is a clean dependency chain with no cycles. Every league rule
  lives in `config.py` and nothing downstream hard-codes one.
- **Purity.** Functions take data and return data; nothing writes global state.
  This is what made memoisation a five-line change rather than a refactor.
- **No premature abstraction.** No class hierarchy where a function would do.
  `RotoScorer` is the only class and it earns its place by holding fitted
  constants across two methods.

## 6. What I would do next, if the goal is engineering quality

1. **Tests.** There are none. The highest-value ones are cheap: the budget
   identity (top 230 = $2,600), replacement-vs-intercept agreement, and a
   golden-file test on ten known players. Those three would have caught the
   calibration bug external review found.
2. **`usecols=` on the wide exports** (§4).
3. **Persist the built board** so scripts don't rebuild across processes —
   this is the DuckDB snapshot store already on the roadmap, and it turns the
   2.67s cold start into a ~50 ms read.
