# Keeper Lab: session log

Reverse chronological. Dates are commit dates. Undated entries predate the GitHub repository. Sources LN (LAB_NOTEBOOK.md), QA_ROUND.md and CODEBASE_REVIEW.md are in git history at commit 8353172; FINDINGS numbers refer to docs/FINDINGS.md. One line per item: built, bug, or declined.

## 2026-09-08

| type | item |
|---|---|
| built | ROADMAP item 1 Steps 0, 1, 1b, 2: `production_value`/`market_price` split, Chadwick age join, ex-ante feature table, keeper decisions reconstructed, price model held out on 2026 (MAE 5.76 vs 6.84 and 7.20 baselines). Coverage fails at 38.4%/60%; `market_price` left NaN (FINDINGS #56) |
| bug | Held-out season defaulted to the omitted season dummy, handing 2026 the 2023 price level: MAE 8.76 and an $86 hitter against a $45 ceiling (FINDINGS #56.7) |
| bug | Age-missingness flag learned "$1" from five unmatched placeholders and applied it to eight 2026 prospects (FINDINGS #56.7) |
| bug | Two different Max Muncys share fg_id 13301 and were both bought in 2026; a (season, fg_id) merge cartesian-joined them |
| built | R port (`R/keeper_lab.R`) removed: duplicated the pandas core and would drift; in history at a1d156c |

## 2026-08-15

| type | item |
|---|---|
| built | Ohtani split into two 2027 auction and keeper assets (hitter, pitcher), `TWO_WAY_SPLIT_NAMES`; past auctions still scored as one purchase |
| built | Track-record signal in the comp estimator: `player_tenure()`, `appearances_to_date`, first-timers comped against first-timers |
| built | Comp estimate re-anchored to the comps' own real historical salaries instead of a percentage on top of `redraft_value` |
| built | Board shows playing-time assumptions (PA/IP, health vs role scaling tag); roto columns grouped before dollar columns |
| built | ROADMAP top-10 rewritten from a league-mate's player-by-player review; read-only local mirror at `~/Documents/Fantasy Baseball/keeper-lab` documented |
| bug | Comp estimate could exceed any price ever paid (Skubal $64 vs a $34 pitcher ceiling); latent regressions from an earlier fix cleaned up |
| bug | `position_map()` returns UNKNOWN for some players (Cade Smith), thinning comp pools; logged as ROADMAP item 9 |
| declined | Blending the comp anchor into headline `redraft_value` (Skubal still $51): ROADMAP item 1, not built |
| declined | "Name-brand / good-team" market premium: no MLB standings data in `data/`, scope the data need first |
| declined | Intuition tab v2 (numeric entry, presets, all 230 players by team): open question whether overrides propagate or stay sandboxed, decision pending |
| declined | Mobile nav overflow for 7 tabs: deprioritised |

## 2026-08-14

| type | item |
|---|---|
| built | Monte Carlo finish odds, `klab/standings_sim.py`; Contention tab; delta P(money) on the Trade tab (FINDINGS #55) |
| built | 2027 keeper-core finish odds on a season toggle; keeper-core strength does not track 2026 standing |
| built | App homepage with a 5-question router; FanGraphs auction-calculator comparison (FINDINGS #54, Spearman 0.68 to 0.84) |
| built | Per-category value breakdown, MLB team display, denominator standard errors on the Model tab |
| built | Direction-aware pitcher playing-time trust (`PT_BLEND_CAP_PITCHER_EXCEEDED`), `upside_ft` split into health vs role (FINDINGS #53) |
| built | C/SS positional adjustment as an off-by-default toggle; both positions came out deeper than pooled (FINDINGS #52) |
| built | Playing-time weight decoupled from the rate blend, `PT_BLEND_CAP_HITTER/PITCHER` (FINDINGS #51); Hunter Brown $10.68 to $16.92, 10 flips |
| built | Doc harmonisation pass: stale numbers fixed, resolved gaps closed |
| bug | Payout structure was coded as top-2-only; real structure is 50/25/15/breakeven for 1st to 4th, now `PAYOUT_SPOTS`/`PAYOUT_SHARE` (FINDINGS #55) |
| bug | `value_2028()` positional override used `np.minimum` and was a silent no-op for every 2028 value; Witt 2028 $34.96 to $25.42 (FINDINGS #53) |
| bug | One shared blend weight let a June injury project fewer 2027 innings (FINDINGS #51) |
| declined | Aging curves: ZiPS is already age-aware, a second curve double-counts; no age data exists (RESEARCH §6.5, ROADMAP 3.4) |
| declined | Probability-weighted closer/reliever upside: deprioritised, direction agreed (bootstrap range), ROADMAP 3.10 |
| declined | Live 2027 keeper-core odds on the Trade tab: `keeper_override` parameter exists, wiring not done |
| declined | Threshold-aware valuation (payout-shaped marginal points) proposed and recorded, not built |

## 2026-08-13

| type | item |
|---|---|
| built | Repository published to GitHub; `data/` gitignored; `check_sync.sh`, `CLAUDE.md`, `data/README.md` added |
| built | `docs/WORKFLOWS.md`: tested recipes after a fresh session hand-calculated a trade answer |
| built | `ros_value_over_replacement`, a player-intrinsic win-now metric (FINDINGS #34) |
| built | Comp-based auction estimator as a separate tool (FINDINGS #35), then wired into the app player card (FINDINGS #43) |
| built | Trade finder, three scenarios per team pair, precomputed for 45 pairs (FINDINGS #40) |
| built | Projection-basis selector, three payloads swapped client-side (FINDINGS #42) |
| built | Blended rest-of-2026 signal (ZiPS ROS x current pace), ROS basis toggle, ROS column on Board/FA tables (FINDINGS #45, #46, #47) |
| built | Historical standings 2022-25; 2027 standings from keeper sets alone (FINDINGS #48, #49) |
| built | Intuition tab: manual player shading, sandboxed (FINDINGS #50); visual redesign; Model-tab tooltips |
| built | Uncertainty bands extended to the board CSV and `eval_trade.py` (FINDINGS #37) |
| built | Roster update after two real trades and one FA move (FINDINGS #38) |
| bug | `F` contracts were never a live extension choice (window closes before the walk-year draft); $130 phantom surplus, 10 flips (FINDINGS #39, LN §18) |
| bug | Extension eligibility applied to codes 2 and 3, not just 1; caught by the owner's own rule description, not review (FINDINGS #33, LN §14) |
| bug | `evaluate_trade()` silently fell back to a hardcoded $7.6/pt; JS used the redraft scale; now a required argument (FINDINGS #32.1) |
| bug | Free agents without draft history got a 1-year contract instead of 2 (FINDINGS #32.2); `already_extended()` $10/$20 ambiguity left documented (FINDINGS #32.3) |
| bug | `teams_per_category` lacked the partial-season exclusion, a second live copy of #26 (FINDINGS #31, LN §13) |
| bug | Bootstrap script never had the partial-season exclusion; ±38% band was centred on the wrong estimates, now ±34% (FINDINGS #30) |
| bug | `RELIABILITY` for BB and H copy-pasted from WHIP (0.237 vs 0.463/0.359); refit test added (FINDINGS #28, LN §12) |
| bug | Partial-2026 exclusion rule generalised from 5 of 10 categories; AVG not inflated, SV inflated; now `PARTIAL_EXCLUDE_CATS` (FINDINGS #26, LN §10) |
| bug | Trade finder non-deterministic across identical reruns (set iteration order, no tie-break); 28 of 45 pairs changed (FINDINGS #41, LN §20) |
| bug | Trade finder suggested Guerrero for a $0 rental; incoming player now needs positive value; apostrophes broke the picker button (LN §19) |
| bug | `prorated_to_date_lines()` divided by a pitcher's own starts, projecting Skubal for 256 more IP (FINDINGS #45, LN §24) |
| bug | NaN `pos` field crashed the app build under `allow_nan=False` (FINDINGS #43, LN §22) |
| bug | Model tab showed the build-time basis regardless of the selector; League-tab aggregates almost left fixed across bases (LN §21) |
| bug | Stale "extension +$5" status string and missing IL/LOCKED drawer tags; two screenshot false alarms from `fullPage` capture (FINDINGS #44, LN §23) |
| bug | Self-test reference trade crashed after a real trade moved De La Cruz; swapped to Trout, loud failure kept (LN §17) |
| bug | pytest 5 failed / 19 errors on Anaconda Python 3.9: scipy 1.7 lacks `spearmanr().statistic`; two 2028 ZiPS files missing from `data/` (LN §8) |
| bug | Stale roadmap claim ("uncertainty bands not in app") repeated without checking the code (FINDINGS #37, LN §16) |
| bug | Third-party CBS data accidentally copied into `out/`; removed |
| declined | Auto-refresh: rebuild chain verified cron-safe, but no ingestion step exists; left manual by choice (ROADMAP 2.4) |
| declined | Young/rookie projection modelling: ZiPS judged good enough; parked (ROADMAP 3.7); reopened as a scoping item 2026-08-15 |
| declined | "Re-drafted players get a fresh 3-year clock" for deGrom/Turang: no re-draft rows exist; anomaly left open (FINDINGS #25, LN §9) |
| declined | Median of the full free-agent pool as replacement (1.10 rp): pool is deep-minors filler; consistency check used instead (FINDINGS #27, LN §11) |
| declined | 2026-in-denominators compression experiment (reconstruct 2024/25 at 70%): not run; raw partial 2026 shipped instead (QA A5) |
| declined | z-score threshold move (1.5/0.5): share-of-production tested, threshold axis not (FINDINGS #29, QA A6) |
| declined | Snapshot Parquet history stays gitignored; history chart not built |

## Before publication (undated)

| type | item |
|---|---|
| built | Single-file HTML app replaced the Streamlit plan; `app/verify.mjs` diffs 25 quantities against pandas (LN "session 5") |
| built | External review reproduced and acted on: expected-PT headline with full-time counterfactual columns, extension option for code-1, c_8 for SV (LN §7) |
| built | Performance pass, 10.7 s to 2.67 s cold and 2.2 s to 0.075 s warm: `io.cached` memoiser returning copies (loaders and fits were running 2 to 3x) |
| built | Same pass: name resolver rebuilt as dict lookups after a per-key DataFrame split made it worse; two per-group lambdas vectorised (CODEBASE_REVIEW) |
| declined | Same pass: pruning 74-column ZiPS exports to the 9 used (P10-P90 bands reserved for upside work) |
| built | QA round: Ohtani extension resolved via `NON_EXTENDABLE_NAMES` (QA A1); `c_n` and rate-stat mechanics documented (QA B1-B5) |
| bug | Dollar scale calibrated on unscaled projections but applied to full-time-scaled points; top 230 summed to $3,854; 42 of 107 flags flipped (LN §7.1) |
| bug | Extension option ignored for code-1 contracts; Duran at $4 understated ~$25 (LN §7.2) |
| bug | Range constant ignored the 8-team SV field; every save overvalued 19% (LN §7.3) |
| bug | Saves and draft-chain findings overstated; saves result now conditional on punter exclusion (LN §7.4) |
| bug | `value_2028` re-introduced the two-way scaling bug; `project_2028` gave starters the save intercept; `score_season` mis-tagged roles (LN §7.6) |
| bug | Final-year extension priced at one year when the rule allows two; `PA_x/PA_y` column collision found by rendering one player card (FINDINGS #24, #24.1) |
| bug | Contract codes documented backwards; every multi-year contract understated by a season (LN §2) |
| bug | Standings ranks inverted (`ascending=False`); caught only because Pookie 2.0 was leading and the model had them last (LN §4) |
| bug | Closer test selected on realised saves; redone with prior-season saves (LN §4) |
| bug | Elite-convexity claim retracted: quadratic term t = -0.01 (LN §4) |
| bug | Negative player values, pitchers tagged two-way from zero-PA rows, Ohtani double-counted, minor-league ids broke integer casts (LN §4) |
| bug | Save model fit on SV >= 10 gave every mop-up arm five phantom saves (LN §3.3) |
| bug | Ohtani collected both the PA and IP floors, +$20 (LN §3.4) |
| declined | Reverse regression `E[$ given roto points]`: attenuation, Ohtani $23 (LN §6) |
| declined | DuckDB and Streamlit deferred; pandas is fast enough at this size (LN §6, ARCHITECTURE Part 6) |
| declined | ZiPS 2027 double-counting worry: tested and refuted, 2026 loading 0.107 vs 0.45 for 2025 (LN §7.5) |
