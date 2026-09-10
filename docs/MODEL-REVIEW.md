# Model review, bottom up (2026-09-09)

A full read of the valuation chain against outside methodology (RotoGraphs, Smart Fantasy Baseball, BaseballHQ, Razzball, the projection-accuracy literature), framed as three named reviewers: Ben Clemens (FanGraphs, market-price and surplus-value work), Dan Szymborski (ZiPS), and Tyler Cowen (an economist reading for identification and equilibrium). Written for a quantitative social-science reader: the recurring vocabulary is measurement error, reliability, selection bias, and identification, because that is what most of these disputes actually are.

Three implementation defects were found and two are fixed in this session's commit; the third is a diagnostic. Everything else is either already answered by the project's own findings (cited) or recorded below as a live limitation with its size.

## 1. The chain, restated for a non-baseball reader

Each step estimates one quantity. Errors compound left to right.

| step | quantity | estimator | analogy |
|---|---|---|---|
| denominators | stat units per standings place, per category | sd of team totals pooled over 3 seasons, mean-normalised, times the expected range of a normal sample | converting raw scores to a common effect-size scale |
| projection | each player's 2027 stat line | reliability-weighted blend of 2026 form and ZiPS 2027, rates and playing time blended separately | shrinkage toward a prior, with the shrinkage weight set by test-retest reliability |
| exchange rate | roto points per auction dollar | OLS of delivered points on price over 677 real purchases, trend-projected to the 2027 keeper regime | hedonic price regression |
| replacement | the level available for free | the 140th hitter and 90th pitcher, per role | norming against the available population, not against zero |
| keep decision | keep iff replacing him would cost more than his salary | `keep_value = (points - intercept) / slope` vs cost, multi-year, option-valued | opportunity-cost framing, later years as call options |
| market price | what the auction will pay | log-price OLS on ex-ante features, budget-calibrated | a separate revealed-preference model, never blended with worth |

## 2. Three reviewers, step by step

### Ben Clemens (market vs production, the top end)

**Would endorse:** the strict separation of `production_value` and `market_price`. His $/WAR program is exactly this architecture: an empirical market-price model fitted on observed contracts, kept distinct from the projection, with surplus as the difference. The project reinvented his design and then validated it (#56, #57: the price model beats both baselines held out; the two families rank players differently, Spearman 0.59).

**Would press on:** linearity at the top. His free-agent work finds the market pays a rising rate per unit of value in the star tier, while every dollar scale here is linear in roto points. The project has three independent instruments agreeing the top end runs rich on the production side (revealed keeper price $38.54 vs `keep_value` $83.02 at the top decile, #56.5; Skubal $34/$34.31 market/revealed vs $86.93 keep, #57.6). The decision survives because ordering, not level, drives keep/cut (#70), but any use of `keep_value` as a price is wrong, and HANDOFF already says so. A tier-shaped (convex-in-points) market model is the one Clemens-style upgrade not yet tried; the failed attempts so far (#57.2, #62.5) attacked the cap, not the shape.

**Would also press on:** flat inflation. `api._inflation()` is a single scalar; the literature (Murphy, Vibber, Kalkman) and this league's own data (#75: stars 1.39x, scrubs 0.19x) agree inflation concentrates on the elite. The engine partially escapes because the keep rule prices against the auction directly rather than through an inflation multiplier, but the app's headline inflation number is a scalar summary of a tiered phenomenon.

### Dan Szymborski (the projection)

**Would endorse:** using ZiPS DC rather than raw ZiPS (raw ZiPS deliberately assumes a full-time role; DC grafts depth-chart playing time). The engine goes further and makes playing time its own blend axis with its own caps (#51, #53), which is the correct reading of what a mid-season DC export can and cannot know. Would also endorse declining the aging curve: ZiPS carries age via comps, and the engine's implied young-player premium matches the empirically measured one within standard errors (#59).

**Would warn, and the project already knows:** the 2027 export is an out-year of the 2026 run. Multi-year ZiPS regresses harder to the mean, has no real playing-time model of its own, and Szymborski frames those boards as median talent estimates with wide error bars, not forecasts. That is the projection half of HANDOFF's open item 2, and the outside answer is now concrete (section 5): no 2026-aware 2027 projection exists anywhere until roughly November, so the blend is the correct interim and the refresh calendar is the fix.

**Would dispute one label:** "the ZiPS 2027 export does not incorporate 2026" was already corrected in #70: it carries 2026 at about a quarter of 2025's weight. The blend then adds 2026 on top at reliability-scaled weights, so the current board is a 2026-aware object, just not as 2026-aware as a fresh post-season run will be.

**Rate-category compression is a property of pitching, not a ZiPS defect:** Marcel shows the same compression from an unrelated method (#67, #68). The pool rule (#70) is the correct repair site, and this session verified the multi-year consequence too (section 4.4).

### Tyler Cowen (identification, equilibrium, incentives)

**The exchange rate is the weakest identified parameter in the chain, and the most load-bearing.** n = 5 auctions; keeper count and calendar time correlate at 0.987 (#19); split halves of 2026 give $6.55 and $20.38 (#7). The keep decision is monotone in it: a higher $/point makes every keeper look better. The project treats the $10.00 level as a trend extrapolation and says so, but a reviewer should be clear that most of the model's aggressive keep count (123, cap-bound for 6 of 10 teams) rests on this one noisy series. The sensitivity harness covers denominators and blend weights more thoroughly than it covers this parameter.

**The equilibrium was not closed, and this review closed it by measurement (#79.35).** The exchange rate is fitted at 100 keepers withheld; the advice implies ~123; more keepers withheld means a thinner auction and a higher $/point, which makes keeping more attractive: a positive feedback loop that had never been iterated. Refitting at assumed counts 100 through 130: $/pt rises 10.00 to 11.94, but the advice moves 123 to 121 and stays there for every count from 110 up. The loop is self-limiting because the marginal keeps are cap-bound or far from the threshold. The fixed point is 121 keeps at $11.36/pt; only Brooks Lee and Kyle Stowers flip (to cut). So the Lucas-critique worry, real in direction, is worth exactly two marginal players in magnitude. The n=5 identification of the trend line remains the deeper problem.

**Goodhart risk is real but bounded.** The model is calibrated on the league's revealed behaviour (prices, keeps); if its output changes that behaviour, the calibration decays. The mitigation is already in place: out-of-sample scoring against the owners (#69) rather than in-sample fit, and a blind human survey (#77) rather than model-anchored review.

**Small-n honesty is above field standard.** 17-30 team-seasons per denominator with bootstrap bands (±34%), retractions kept on the record (#16, #19, #30, #55), and negative results shipped (#69). A social scientist would recognise the file-drawer discipline; most fantasy tools publish none of this.

## 3. Where the outside literature would object, and the status of each

From the SGP/valuation literature (McGee; Bell/Smart Fantasy Baseball; Schechter; Gamble/Razzball; Zola; The Process):

| objection | status |
|---|---|
| own-league denominators from 4-5 seasons are noise-dominated; use pooled multi-source denominators | half-answered. Pooling relative dispersion across seasons is this project's version of the remedy, and Bell's own result (dollar values insensitive to denominator source, ranks stable) cuts both ways. Live residual: cross-category ratios (1 HR = 2.6 R etc.) carry ±34% and no external denominator set has ever been diffed against these. Cheap next step: score the board once with BaseballHQ/SFB-style published denominators and count flips |
| sum of positive values must equal the budget | built (`scripts/audit.py`, exact) |
| each category should carry equal aggregate value | measured this session, and the imbalance is structural, not a bug: the calibration pool's roto points split R 305 / RBI 301 / K 215 / W 207 / HR 200 / SB 101 / SV 62 (rate categories are marginal-vs-average and sum near zero by construction). Category sums are inversely proportional to relative dispersion, which is what SGP intends, but it means the cross-category weights are the model's least-verifiable claim. Recorded as a limitation, not changed |
| replacement should include bench slots (last drafted, not last fielded) | answered by league structure: the $260 auction buys 23 active slots only, reserves sit outside the auction (#75), so the fieldable 230 is the right pool here, unlike in standard leagues |
| position-level replacement (catcher scarcity) | tested and correctly declined: C and SS came out deeper than pooled (#52), and published tests find positional adjustments add nothing |
| hitter/pitcher budget split (65/35 convention, or market-derived) | refuted on this league's own data at the realised level ($2.09 vs $2.11 per delivered point, #64); the fieldable-pool rule (#70) fixed the projection-side distortion |
| inflation belongs at auction time, not in stored values | matches practice here; the tiered-inflation refinement is live (section 2, Clemens) |
| pitchers need an extra multi-year haircut (injury incidence +34%, ERA r ~0.18, TINSTAAPP) | **verified this session, no change needed** (section 4.4): the engine's out-year already haircuts pitchers harder than hitters by more than the league's own year-over-year retention gap |

## 4. What this review found in the code (all sizes measured)

### 4.1 Fixed: 2028 values priced hitters against the pitcher replacement bar

`value_2028()` read the scalar `meta["replacement_rp"]`, which under `POOL_RULE = "slot_role"` is min(HIT 5.121, PIT 3.526) = the pitcher bar. Every 2028 hitter value was inflated by (5.121 - 3.526) x $6.21 = **$9.90**. Zero keep/cut flips (the decision runs on `keep_value_2028`, which comes from the exchange rate and never touches replacement), but the displayed out-year column, the redraft-basis alternative, and the free-agent 2028 leg were all wrong. Fixed with per-role bars; mean absolute change in `redraft_value_2028` $4.44, max $9.90, all hitters down, pitchers byte-identical.

### 4.2 Fixed: the uncertainty bands described a different model than the one shipped

Two mismatches, both #70 fallout of the class #78 warns about. (a) `bootstrap_bands()` refit replacement inside each draw with the old role-blind top-230 rule while the point estimates use `slot_role`; the bands bracketed an estimator the board no longer uses. (b) The surplus draws ran on the redraft basis while the headline `surplus_multiyear` they are displayed under is keep-basis, so the drawer showed a keep-basis dollar with a redraft-basis "range" and "% of draws positive" beneath it. Both fixed: draws now follow `POOL_RULE` and `KEEP_BASIS` (exchange fit held fixed across draws; its own ±40% error is reported separately, #7). Bands now bracket their headline (Skubal surplus $113.5, band $96-$176); 9 of 123 recommended keeps sit below 80% confidence.

### 4.3 Closed: HANDOFF open item 1, the shipped combination re-scored

`backtest_keepers.py` re-run at the shipped defaults, plus the `MAX_KEEPERS` cap on the replacement basis (the one piece of the shipped rule the published #69 table had not scored). The cap changes **zero** of 289 calls (no team exceeds 12 keeps in the backtest window), so the shipped combination scores exactly as `model_replace` in #69: dollars captured vs keep-everything, owner / model: 2024 +$240.9 / +$206.0; 2025 -$310.8 / -$56.2; 2026 +$73.5 / **+$78.6**. On the clean season the shipped rule now edges the owners on dollars while trailing on accuracy (64.9% vs 71.6%): it wins by sizing, not by classification. The multi-year leg remains untestable ex ante (no historical out-year projection exists) and is recorded as such.

### 4.4 Verified, no change: the flat future-year discount survives the pitcher objection

The sharpest live objection from the literature: a flat `FUTURE_YEAR_DISCOUNT = 0.85` treats a $30 pitcher and a $30 hitter as equally durable keeper assets, against pitcher injury incidence and an ERA year-over-year r of 0.18. Measured on this league's own scoring scale (1,863 roster-relevant player-seasons, 2022-2026): next-season retention is **0.751 for hitters vs 0.526 for pitchers** (slope interaction t = -4.07). But the engine's out-year already carries the differential: on the decision scale the implied 2028/2027 ratio is **0.873 HIT vs 0.556 PIT**, a relative pitcher haircut of 0.64 against the empirical 0.70. ZiPS 2028 regresses pitchers harder and the convex dollar transform amplifies it. A role-specific discount on top would double-count, the same structure as the declined aging curve (#59). Verified rather than assumed, which closes the objection.

### 4.5 Fixed: the Monte Carlo hot/cold shock had the wrong sign for pitcher negative stats

A "hot" draw multiplied a pitcher's ER, BB and hits allowed UP together with his W and K, with innings unshocked: a quality gain and a quality decline in the same draw. The two halves cancel inside the ERA/WHIP rebuild, so pitching-quality dispersion was suppressed and a team's K/W points were artificially positively correlated with its ERA/WHIP points across draws, compressing the money odds of pitching-heavy teams. Fixed in both the Python simulator and its JS port (the keeper-core sim needed a per-role flip because one column holds hitter hits and pitcher hits allowed).

### 4.6 Fixed: the two-way split double-counted one player in every roster sum

A split player (Ohtani) carries two board rows per fg_id. Three consumers merged those rows against one-row-per-player tables and counted him twice: `_team_volume` (every win-now trade evaluation and every finish-odds draw credited his team his full 2026 line twice), `validate.py` check 1 (the standings-reproduction correlation the project quotes), and the app payload plus the JS basis switch. A fourth consequence was worse: `find_player` raised "ambiguous" on his duplicate name and the trade finder's batch loop swallowed that error, so the league's most valuable asset could never appear in a suggested trade. All fixed; `find_player` now returns the two rows combined into one asset (values sum, the single contract carries over).

### 4.7 Fixed: the owner audit priced hitters against the pitcher bar

`decision_audit.py`, the instrument behind #66's owner scoreboard, read the scalar `replacement_rp` (the pitcher bar after #70) for every player, overstating each hitter's realised and ex-ante value by about $10. Now per-role bars. The #66 headline pattern (keeps decay, throw-backs improve) is directional and survives; the dollar levels in that entry predate #70's per-role replacement and should be re-read from a fresh run.

### 4.8 Fixed: two smaller ex-ante and consistency defects

The backtest's rewound exchange rate scored past purchases with the SV field size from the 2024-26 window, a future-information leak into the file whose whole point is ex-ante honesty; numerically neutral here (the scoreboard reproduces to the decimal after the fix), fixed for the principle. `free_agent_board` computed its multi-year surplus on the redraft scale while the rostered board it is displayed beside uses the keep scale; it now follows `KEEP_BASIS`. `sensitivity.knob()`'s cache-clear list gained `scorer_2026_full` and `roto_2026_lines` (their staleness only touched unprinted columns, found before it bit). `ros_lines`/`prorated_to_date_lines` are now memoised, which removes the largest redundant work inside the ~2-minute trade-finder rebuild. The doubled `@cached` on `lines_2026_pitchers` (harmless) was removed.

### 4.9 Diagnostic, not fixed: remaining single-scalar replacement consumers, and two script nits

`trade.ros_value_over_replacement()` and the standings-sim empty-slot fill still read the scalar `replacement_rp` (= the pitcher bar). For the win-now column this overstates hitters relative to pitchers by a constant ~1.6 roto points times the prorated fraction; for the sim fill it seats a below-hitter-replacement bat in empty hitter slots. Both are display-layer, neither feeds a dollar or a keep call, and the per-role plumbing touches four signatures; documented here so the next reader does not rediscover it.

Two script nits left as documented: `fit_blend.py`'s playing-time-cap section labels the symmetric (0.30, 0.30) point "production" when the shipped pair is (0.30, 0.15), so its `gain_vs_production` column is against a near-production baseline rather than the exact one (its own section 5 scores the exact pair); and `waiver_value.py` shows a two-way player's larger role rather than the sum, inconsistent with `score_season`'s convention (no two-way player appears in the churn windows measured).

## 5. The projection question, answered with dates

The distrust of the current ZiPS 2027 export is well-founded and also currently unfixable: **no projection system anywhere publishes a 2026-aware 2027 line until after the season.** The engine's blend (2026 actuals + ROS folded in at reliability-scaled weights) is the best available interim object, and #70 measured that it earns its keep (+$36-62/season vs projection-only).

Refresh calendar (timing from published history; FanGraphs CSV export is members-only now, which is the one purchase worth budgeting):

| when | what | action |
|---|---|---|
| ~Oct 2026, week 1 | 2026 final actuals | refresh `data/` actuals; blend becomes fully 2026-complete |
| ~late Oct / Nov 2026 | **Steamer 2027** on FanGraphs, first 2026-aware system | ingest as `PROJ_2027_*` (config is filename-switchable by design); rerun `fit_blend.py` and the flip diff |
| ~mid-Nov 2026 to Jan | **ZiPS 2027** (intro ~Nov 12 pattern), DC playing time by Dec-Jan | replace the stale export; this is HANDOFF item 2's "fresh ZiPS" |
| ~early Feb 2027 | **ATC 2027** (accuracy-weighted aggregate; top of the FantasyPros accuracy table nearly every year, behind only the Zeile consensus) | if the keeper deadline allows, make ATC or a Steamer/ZiPS/BAT average the final board's source; aggregates beating single systems is the most replicated result in the accuracy literature |
| Jan-Mar | THE BAT/X, OOPSY, PECOTA (paywalled) | optional second opinions; BAT X strongest on hitter rates, ATC on pitcher ratios |

## 6. Ranked sources of error in the current valuations

1. **The projection source** (stale out-year ZiPS). Binding constraint by the project's own test (#69); fix arrives on the calendar above, not from more modeling.
2. **The exchange-rate level** ($10.00/pt from n = 5 auctions, ±40%). Drives the keep count; ordering robust, level not. Its feedback loop through the keeper count is now measured at two flips (#79.35), so the residual risk is the level itself, not the equilibrium.
3. **Top-end level of `keep_value`** (linear scale vs a market three instruments say is capped/concave up top). Safe for keep/cut ordering, unsafe as a price; the survey's price section (#77) is the designed test.
4. **Cross-category weights** (±34% per denominator; category pool shares span 62 to 305 rp). Within-category rankings are immune; cross-category trades and the SV/SB-dependent calls are not. The punter exclusion (#1) remains the largest single lever.
5. **Replacement level** (contested between 4.38 and 5.04 by two behavioural measurements, #62). One line to change, evidence tied; transaction logs with dates would settle it.
6. **Playing-time caps** (0.30/0.15/0.40, judgment). LOSO says the fitted alternatives are worse (#70); the survey's playing-time flips are the human check.

## 7. What was deliberately not done in this review

- No blend-weight re-sweep (#70 swept it; flat curve; do not re-run without new seasons).
- No budget split, no aging curve, no per-team multipliers, no upside feature (#64, #59, #60, #57.1; all refuted on data).
- No new keep-basis or pool rule (#69/#70 chose them out of sample; this session's re-score confirms).
- No swap of `WAIVER_VALUE` (#62's tie stands).
- FINDINGS.md was not compacted further: it is one condensation old already, the constraint protects retractions, and the entries earn their tokens as the project's institutional memory.
