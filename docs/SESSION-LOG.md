# Keeper Lab: session log

Reverse chronological. Dates are commit dates. Undated entries predate the GitHub repository. Sources LN (LAB_NOTEBOOK.md), QA_ROUND.md and CODEBASE_REVIEW.md are in git history at commit 8353172; FINDINGS numbers refer to docs/FINDINGS.md. One line per item: built, bug, or declined.

## 2026-09-09 (bottom-up model review)

| type | item |
|---|---|
| built | `docs/MODEL-REVIEW.md`: the full chain read against outside methodology (SGP literature, projection-accuracy studies, keeper-inflation treatments), framed as three reviewers; ranked error sources; projection refresh calendar. Two web-research passes and one code-review subagent behind it |
| built | HANDOFF item 1 closed: the shipped #70 combination re-scored through `backtest_keepers.py`; the MAX_KEEPERS cap changes zero of 289 calls, so the shipped rule scores as `model_replace` in #69 (edges owners on 2026 dollars +78.6 vs +73.5, trails on accuracy). #79.1 |
| declined | Role-specific future-year discount (the sharpest outside objection): measured league retention 0.751 HIT / 0.526 PIT, engine already implies 0.873 / 0.556 on the decision scale; a second haircut would double-count. #79.2 |
| bug | 2028 values priced every hitter against the pitcher replacement bar (+$9.90 each); same scalar overstated hitters ~$10 in the owner audit. Zero keep flips (decision scale never saw it). #80.1 |
| bug | Bootstrap bands used the pre-#70 role-blind pool and the redraft basis under a keep-basis headline; both now follow config. Bands bracket their headline; 9 of 123 keeps below 80% confidence. #80.2 |
| bug | Monte Carlo hot/cold shock raised a hot pitcher's ER/BB/hits-allowed along with his W/K; sign flipped for negative stats in Python and the JS port. #80.3 |
| bug | Ohtani double-counted in `_team_volume` (every win-now evaluation and finish-odds draw), `validate.py` check 1, and the app payload; trade finder silently skipped him via a swallowed "ambiguous" error. `find_player` now combines split rows into one asset. #80.4 |
| bug | Rewound exchange scored 2022-23 purchases with the 2024-26 SV field size, an ex-ante leak in the backtest; numerically neutral, fixed for the principle. #80.5 |
| bug | Free-agent multi-year surplus ran on the redraft scale beside a keep-basis board; now follows `KEEP_BASIS`. #80.6 |
| built | `ros_lines`/`prorated_to_date_lines` memoised (trade-finder rebuild ~135s to ~100s); `sensitivity.knob()` clear-list completed; doubled `@cached` removed. #80.7 |
| built | Projection question answered with dates: no 2026-aware 2027 projection exists anywhere until ~Nov 2026 (Steamer first, ZiPS Nov-Jan, ATC Feb; aggregates beat single systems in every published test); refresh calendar in MODEL-REVIEW section 5 and HANDOFF |
| built | The keeper-count equilibrium closed by measurement: refitting the exchange rate at 100-130 assumed keepers moves $/pt 10.00-11.94 but the advice converges at 121 keeps (vs 123 shipped), flipping only Brooks Lee and Kyle Stowers. A two-flip worry, not structural. #79.35 |
| bug | The finder's shortlist and win-now picker also treated split rows as separate half-strength assets (name-keyed `set_index` returned a Series and crashed the batch); both aggregate per name now. #80.4 |
| bug | The quoted CHECK 1 standings correlation (0.851) was stale: it predates the 2026-09-07 evening actuals refresh. Current: 0.527 pre-fix, 0.588 after the dedup, and the check decays by construction late in a season. Docs trued. #80.65 |
| declined | Building the valuation-curve toggles same-session (Josh's next ask, near the token boundary): seeded instead as HANDOFF "Next session: start here" with scope notes (splines at the tails, budget identity per variant, ship-both-variants UI pattern), followed by a UI review pass mirroring MODEL-REVIEW |

## 2026-09-08 (assessment phase B, then a reader pass over the result)

One long session. Phase A had run earlier the same day (below); B answered its
three open questions, shipped the first valuation change of the phase, and then
spent the second half fixing what a reader found in the result.

**Phase B: the three questions Phase A could not answer**

| type | item |
|---|---|
| built | `scripts/marcel_pool_test.py`. The top-230 pool pathology REPRODUCES under Marcel (184/46, 155/75, 160/70 against ZiPS 2027's 183/47 and realised 131/99, 139/91, 130/100), so it is general to projections and the repair belongs in the pool rule. #68 |
| bug | #65's smeared-innings mechanism refuted: Marcel's innings distribution is near-realistic (142-154 arms over 100 IP against 118-127 real; ZiPS has 223) and it still produces 184/46. The mechanism is rate-category compression, sd ratio 0.43-0.60 for ERA/WHIP and 0.50-0.58 for SV against 0.67-0.84 for W/K. #68 |
| bug | #65's rejection of its own repair does not hold: slot-plus-role-replacement gives 54.21% where perfect foresight on realised seasons gives 52.0-55.1%. No pool rule reaches 63-64% under perfect foresight, so that was never the benchmark. #68 |
| built | `klab/rewind.py` + `scripts/backtest_keepers.py`: the out-of-sample keep/cut test #66 named as the biggest gap, on 289 decisions. **Negative result: the model does not beat the owners.** On the clean 2026 season owners are 71.6% right and beat keep-everything by $73.5; the production rule is 68.7% and beats it by -$10.9. A floor, since Marcel is the naive projection. #69 |
| bug | Two measurement errors fixed first: scoring keeps against `redraft_value` (a no-keeper market) makes only 23% read as correct keeps against 54% on the opportunity-cost scale, which would have handed the model a free win; and dollar totals are meaningless against zero when keeping everything already captures most of the surplus. Closes `decision_audit.py`'s open question 3 |
| built | Structural split found: the pool rule moves `redraft_value` only and `replace_cost` is pool-independent, so **the pool rule is a pricing question and the exchange rate is the keep/cut question.** They had been treated as one. #69 |
| built | **Shipped `KEEP_BASIS = "replacement"` and `POOL_RULE = "slot_role"`.** Pool 183/47 to 140/90, hitter share 73.7% to 54.2%, `usd_per_rp_redraft` 6.522 to 6.213, replacement 4.733 pooled to 5.121 HIT / 3.526 PIT. 47 flips, all cut-to-keep, keeps 70 to 123. The two are complementary: the keep-basis alone adds 4 keeps below replacement and role-specific replacement removes all 4. The old rule was cutting a $36 Soto projecting 9.1 roto points. #70 |
| declined | Changing the blend weights. `scripts/fit_blend.py` sweeps them for the first time: turning the blend off costs $62/season so it earns its place, but the curve is flat from 0.5 to 1.0 and leave-one-season-out gains only $2.2/season on the rate cap and LOSES on the playing-time caps. All four constants stand. #70 |
| bug | Premise corrected: the ZiPS 2027 export does NOT predate the 2026 season. Regressing its rates on 2025 and 2026 actuals gives 2026 coefficients of 0.16 (t~5) against 0.60 for 2025 |
| bug | `validate.py` CHECK 5 reimplemented the pool selection inline and kept printing 183/47 after the rule changed. Now reads the shipped board |

**The reader pass: four defects, three of them presentation-layer**

| type | item |
|---|---|
| bug | The `Surplus '27` tooltip still said "Production $ minus cost" after #70 moved the decision to `keep_value`, so the app stated arithmetic that did not reproduce its own number. Added a `Replace $` column and the explicit subtraction in the drawer. #71.1 |
| built | Standings and Contention merged into one tab with **money odds as the second column**. Not redundant (point estimate against Monte Carlo odds) but indistinguishable, both being ten-row team tables. #71.2 |
| declined | Wacha's negative `rp_ERA` is not a bug: a 4.27 projected ERA against a 3.613 league-average staff, 88% of it ZiPS's own number. ERA scorer validated as monotonic and crossing zero at the baseline. Relaxing the reliability discount was swept and rejected (production is the maximum). The wins denominator is CONSERVATIVE: +10 wins gains 3.27 places empirically against 2.82 modelled. #71.3 |
| built | `Roto '26` and `Move` columns: the season the player is actually having, next to the projection, and the difference. Scored on 2026's own scale after a correction (a roto point is a standings place, so the unit is already common). Season completion measured at 0.8849 hitters / 0.8789 pitchers; validated by scale invariance at correlation 0.9975. #72 |
| bug | **The board printed correct numbers under the wrong headings.** Headers come from `BOARD_COLS`, cells from a hand-written positional list in `playerRow`, with nothing linking them; three headers were added without their cells. `Move` was rendering contract years. No valuation was wrong. Guards added: a load-time shape assert and a `verify.mjs` check comparing rendered cell text to the payload. #73 |
| built | Tooltip pass: a written contract above `COL_HELP`, four leaked internal doc references removed, undefined jargon removed, and per-category value decomposition on hover. The `Move` tooltip answers the Wacha question in four lines. First three tests this layer has had; suite 15 to 17 checks. #74 |
| built | Answered why the dollar values look higher than draft costs: over all 277 rostered, Production $ / salary is **0.74**. The board is sorted by surplus, so a reader only ever sees the top tier, where the ratio is 1.39; the bottom 157 cost $1,429 and produce $272. `market_price` is the only column comparable to a draft price. #75 |
| built | `playing time: as projected / full season` selector, so the reader chooses the workload assumption rather than the model baking it in. Devin Williams goes 4.9 points / -$4 surplus to 9.8 / +$45. Keep flags deliberately do not move with it. Bars removed from the tooltips. #76 |
| built | `scripts/build_survey.py` / `out/keeper_survey.html`: a blind one-player-at-a-time keep/cut survey for a human reviewer, ordered by information (44 playing-time flips first, then close calls by dollars at stake). Shows NO model output; `app/verify_survey.mjs` asserts that and drives the whole flow. `scripts/ingest_survey.py` scores returned answers against the model and against each other, with price calibration split by role, which is the test of the pitcher-bargain claim. #77 |
| built | Session reflection recorded as FINDINGS #78: every defect a reader found today was in the presentation layer, and every one came from changing the model without chasing the change through to what a reader sees. Rule written into `HANDOFF.md` and `README.md`; three guards now exist because of those four defects |
| built | `README.md` opens with a ranked next-session block; the survey is item 0 because it is the only thing on the list that can be done today. `docs/METHODS.md` limitations now lead with the out-of-sample failure and the three load-bearing consequences of #70 |
| built | Docs compaction: `ASSESSMENT-BRIEF.md` 381 lines to a 20-line closed-phase stub, today's findings consolidated, this log's seven same-day blocks merged into one |

## 2026-09-08 (assessment phase, Phase A)

| type | item |
|---|---|
| built | Marcel projection archive imported: `data/marcel_{2024,2025,2026}_{hitters,pitchers}.csv`, three ex-ante seasons with actuals, which clears the blocker Phase A named on all three of its open questions. Ten published identities re-derived, zero violations; `fg_id` join 100% on all six files. `klab/marcel.py`, `scripts/validate_marcel.py`, `scripts/fetch_marcel.js` (FINDINGS #67) |
| built | `scripts/fetch_chadwick.py` now keeps `key_bbref`, the exact join from Baseball-Reference ids to `fg_id`. The Marcel pitcher id is in the page DOM but not the rendered table, so it survives DOM extraction and is lost by copy-paste |
| built | Marcel's own reliability weights corroborate #65 from an unrelated system: it trusts a pitcher's record about half as much as a hitter's (median rel 0.47 against 0.71), with 21-26% of pitcher rows under 0.30. Pitcher compression is a property of pitching, not a ZiPS artefact (FINDINGS #67) |
| declined | The hitter/pitcher budget split, the brief's strongest lead and its Phase B item 1: REFUTED, not deferred. The league pays $2.092 per realised roto point for hitters and $2.114 for pitchers (ratio 0.99, 668 purchases, stable every season); hitters take 63.9% of the dollars because they deliver 64.1% of the points. One scale is correct (FINDINGS #64) |
| bug | Found underneath it and deliberately NOT fixed: the calibration pool is the top 230 by roto points regardless of role, which on the 2027 projection is 183 hitters and 47 pitchers, a set no ten teams could field. Allocates 73.7% to hitters against the league's 63-64%. Completed seasons give 129/101 to 139/91, so it is latent in the code and activated by the projection. The obvious repair overshoots to 54.2% because the projected pitcher pool is smeared (223 arms over 100 IP against 118-127 real). Blocked on projection archives (FINDINGS #65) |
| built | Decision audit interpreted, Josh's named question answered: owners' keeps look ten times better than their throw-backs when made (ex-ante surplus $13.17 against $1.21) and are worth the same afterwards ($6.75 against $6.39). Keeps 73.0% right ex ante fall to 55.4% realised; throw-backs 61.7% rise to 73.3% (FINDINGS #66) |
| built | `scripts/validate.py` CHECK 5: tracks the role split of the calibration pool against the league's revealed 63.4% so the known gap cannot drift silently |
| declined | One reconciliation route for `WAIVER_VALUE` tested and refuted: the 106 free agents above 4.381 are 99 hitters and 7 pitchers, so the smeared pitcher pool does not explain the internal-consistency count. Tie stands, still at "low" (FINDINGS #62) |
| built | `scripts/decision_audit.py`: scores the owners rather than the model on 336 past keeper decisions, ex-ante and realised verdicts kept separate. 2026 owners' throw-backs vindicated 73.3% against keeps at 55.4% |
| built | Sourced comparison against published fantasy-valuation practice in the brief. Lead finding: the model pools hitters and pitchers on one scale (73.7/26.3) where the league spends 64/36 and standard SGP practice splits the budget |
| built | `docs/ASSESSMENT-BRIEF.md`: the chain link by link with a confidence claim and what would move each, Josh's questions mapped to evidence, the outside-analyst objections, and a scoped decision-quality audit. Next phase is assessment, not building |
| bug | METHODS validation and limitations tables had gone stale (test count, replacement level, four items superseded by FINDINGS #57-#63); trued up |
| built | Data refresh to 2026-09-07: standings, rosters and contracts re-derived from CBS pastes, ZiPS rest-of-season re-exported. 38 players added, 39 dropped, 2 contract changes. $/rp keep 9.17 to 10.86, redraft 6.56 to 7.00, replacement 4.811 to 4.599; keepers 70 to 75, 5 keep/cut flips |
| bug | `_reference()` in build_app.py hard-coded a trade whose players had been traded away; the whole build died on refresh. Now picks the top two keepable per side |
| bug | Two tests and one app check were pinned to data, not behaviour: a golden value on a dropped player, and two assertions on standings POINTS (ranks) that a small change legitimately leaves at zero. Re-pointed at category totals and standings levels |
| built | $1-minimum-bid hurdle on the price band: lower-tail misses 25.0% to 11.6% against a 20% target (FINDINGS #63) |
| declined | Bounded logit-link price model, the third attempt at the role cap: wins on LOSO, loses held out (6.17 vs 5.76), tops out at $31 when the real max was $43 (FINDINGS #62.5) |
| bug | `scripts/price_model.py` kept its own copy of the model after the core moved to `klab/price.py`, so it reported stale band numbers; now imports what it tests |
| built | ROADMAP item 4 (waiver-wire value): 34 adds / 33 drops from two roster snapshots give a churn margin of 4.12-4.39 against replacement 4.733. Conflicts with the internal-consistency test (106 FAs would beat 4.381), so `WAIVER_VALUE` left at "low" (FINDINGS #62) |
| bug | `position_map()` had no position for 134 of 277 rostered players (48%, not "some"), so half the comp pools fell back to the full role. `data/positions_2026.csv` takes coverage to 100%; comp_price moved for 146 players, mean $3.81 (FINDINGS #61) |
| declined | ROADMAP item 2 as written: per-team category multipliers range 0.29x-13.28x within a season and persist at -0.07 across seasons. Scoping build kept in `klab/teamvalue.py` with the negative result (FINDINGS #60) |
| built | Age-conditional persistence study (`scripts/age_persistence.py`): young premium is a level effect (+0.778 roto pts for age<=25, p=0.0009), not a slope effect; the engine already applies +0.621, so no projection change (FINDINGS #59) |
| built | Age added to the revealed keeper-price model: -0.127/yr (p=0.033), pseudo R^2 0.144 to 0.169 |
| built | 2026 actuals refreshed from Standard-view exports (hitters 1373 to 1447 rows, pitchers 795 to 851). $/rp keep 10.86 to 10.01, redraft 7.00 to 6.53, replacement 4.599 to 4.733; keepers 75 to 76, 9 more keep/cut flips |
| bug | FIXED (FINDINGS #58): FanGraphs writes IP in thirds notation (132.1 = 132 1/3) and `denoms.py` sums and divides it raw. ZiPS projections use true decimals (.3/.7), so actuals and projections were blended on different conventions. Converted at the loader; derived ERA/WHIP now reproduce FanGraphs' columns exactly. Impact small: max $0.15, zero flips |
| bug | `F` players showed a $0 keeper cost, which read as "free to keep" rather than "cannot be kept"; Cost is now blank for them on the board and in the drawer |
| built | "Market $" board column and drawer block, with the P20-P80 range and the production-minus-price gap on hover |
| bug | Phone CSS nth-child list had drifted and was hiding Production $, the column its own comment names as one the phone keeps |
| built | ROADMAP item 1 Steps 3, 4, 5: market_price calibrated to the 2027 budget (126 lots, $1,765, identity exact); market keeper lens shipped alongside, not instead; five-system comparison in out/valuation_comparison.csv (FINDINGS #57) |
| bug | Quantile crossing put P20 above P80 (Crow-Armstrong $41.53 vs $39.73); band ends now sorted |
| bug | Budget identity missed by $7 because the band repair clipped the point estimate after the solve; solver now scores through the same function the output uses |
| declined | Step 5 upside feature: both terms insignificant, loses on LOSO 6.59 to 6.81 (FINDINGS #57.1) |
| declined | Monotone GBM fallback: LOSO 6.91-7.04 against 6.59, and shrinks the top end (FINDINGS #57.2) |
| declined | Step 4 as specified (keep on market arbitrage): keeps 104 including 30 below replacement, cuts Skubal; keep_2027 left on the production basis (FINDINGS #57.5) |
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
