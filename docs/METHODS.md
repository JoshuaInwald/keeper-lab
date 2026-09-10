# Keeper Lab: methods

Valuation engine for a private 10-team 5x5 rotisserie keeper auction league (CBS): dollar values calibrated to this league's own auction and standings history, 2027 keeper decisions ranked by multi-year surplus, two-lens trade evaluation, finish-odds simulation. Numbers are from the committed build (`out/model_params.json`, `out/keeper_lab.html`); rerun `scripts/validate.py` and `scripts/sensitivity.py` before quoting them. Every constant named here lives in `klab/config.py`.

## 1. League rules that drive the math

| rule | value | config knob |
|---|---|---|
| teams, budget | 10 teams, $260 each, $2,600 league cap | `N_TEAMS`, `BUDGET` |
| active roster | 23 = 14 hitters (C,1B,2B,3B,SS,CI,MI,5xOF,2xUTIL) + 9 pitchers, plus reserves | `N_HIT_SLOTS`, `N_PIT_SLOTS`, `N_ACTIVE` |
| categories | R, HR, RBI, SB, AVG; W, SV, K, ERA, WHIP (ERA, WHIP lower is better) | `CATS`, `NEG_CATS`, `RATE_CATS` |
| contracts | 3 years at auction price; code = seasons remaining after the current one (`3`, `2`, `1`); `F` = final year already, confirmed free agent for the 2027 auction | `YEARS_REMAINING`, `EXTENSION_REQUIRED` |
| extension | +$5 per year, one or two years, once per contract, decided before the walk year's own draft; only code-`1` players hold a live option (FINDINGS #33, #39) | `EXTENSION_COST`, `EXTENSION_MAX_YEARS`, `NON_EXTENDABLE_NAMES` |
| keepers | 6 to 13 per team | `MIN_KEEPERS`, `MAX_KEEPERS` |
| free agents | $10 before the All-Star break, $20 after; a re-added player keeps his draft-year contract | `FA_SALARY_PRE_ASB`, `FA_SALARY_POST_ASB` |
| payout | 50% / 25% / 15% of the pot for 1st to 3rd, buy-in back for 4th | `PAYOUT_SPOTS`, `PAYOUT_SHARE` |
| two-way player | Ohtani auctioned as two assets (hitter, pitcher) from 2027; extension override applied | `TWO_WAY_SPLIT_NAMES`, `NON_EXTENDABLE_NAMES` |
| hand-entered contracts | Cam Smith, William Contreras, Jarren Duran (CBS export unreadable) | `CONTRACT_OVERRIDES` |

Contract codes were originally documented backwards (LAB_NOTEBOOK §2); `scripts/audit.py` checks them against acquisition year (83% of code-2 bought in 2026, 77% of code-1 in 2025, 88% of code-F in 2024).

## 2. Pipeline

Data flows one direction: `config` > `io` > (`denoms`, `project`, `auction`) > `board` (with `keeper`) > (`trade`, `freeagents`, `trade_finder`, `standings_sim`, `uncertainty`, `auction_estimator`) > `api.snapshot()` > `scripts/build_app.py` > `out/keeper_lab.html`. `io.cached` memoises loaders and fitted objects (returns copies); cold `build_board()` 2.7 s, warm 0.08 s.

### 2.1 Denominators: units of a category per standings point

`denoms.pooled_relative_dispersion()` divides each team's category total by its season's league mean, pools the relative values across `DENOM_SEASONS = [2024, 2025, 2026]`, and takes the standard deviation (30 team-seasons; 20 for ERA/WHIP and 17 for SV, which drop the in-progress 2026 season via `PARTIAL_EXCLUDE_CATS`, FINDINGS #26). `denoms.denominators_for_level()` converts: `denominator = sigma_rel x league level (LEVEL_SEASONS 2024-25) x c_n / (n - 1)`, where `c_n` is the expected range of a normal sample (3.078 at n=10, 2.847 at n=8). `denoms.teams_per_category()` sets n per category; teams under `SV_PUNT_THRESHOLD = 15` saves are dropped before anything involving SV, so the SV field is 8 teams. `denoms.season_levels()` and `team_baselines()` (top 140 hitters by PA, top 90 pitchers by IP, rescaled by a realization factor) build the league-average team that rate stats are scored against. `RotoScorer` turns a stat line into roto points: counting stats divide by the denominator; rate stats drop the player into an average team with one slot open (13/14 of AB, 8/9 of IP) and measure the shift.

| R | HR | RBI | SB | AVG | W | SV | K | ERA | WHIP |
|---|---|---|---|---|---|---|---|---|---|
| 33.8 | 13.8 | 33.8 | 17.1 | .0023 | 3.67 | 6.57 | 52.6 | .0431 | .0108 |

### 2.2 Exchange rate: dollars per roto point

`auction.auction_sample()` pairs every auction purchase (677 over 2022-26; 671 names resolved by `io.NameResolver`) with the roto points that player delivered that season (`auction.score_season()`); busts and never-played picks stay in at the price paid. `auction.regress()` fits `roto_points ~ salary` (production on price, never the reverse) with robust errors. `board.fit_exchange_rate()` under `EXCHANGE_BASIS = "keeper_adjusted"` fits $/point and intercept per season against keepers removed (`KEEPERS_REMOVED`: 25, 28, 29, 29, 100) and predicts at `KEEPERS_EXPECTED_2027 = 100`. Current: `roto_points = 3.98 + 0.109 x $`, $9.17 per point, n=404 on `AUCTION_SEASONS` 2024-26. Alternatives: `pooled` ($7.56), `recent` (2026 alone, $9.98). `auction.spec_battery()` writes the alternative specifications to `out/auction_regression_battery.csv`.

### 2.3 Projections

`project.project_hitters()` / `project_pitchers()` blend A = 2026 actuals + ZiPS rest-of-season (`io.load_ros_*`) with B = ZiPS 2027 (`io.load_zips27_*`, `PROJ_2027_*`) at the rate x playing-time level, never on counting stats:

```
w_rate(stat) = min(PA/(PA+250), BLEND_W_2026=0.50) x RELIABILITY[stat] / max(RELIABILITY)     # project.rel_weight()
w_pt         = min(PA/(PA+250), PT_BLEND_CAP_HITTER=0.30 | PT_BLEND_CAP_PITCHER=0.15)          # FINDINGS #51
               PT_BLEND_CAP_PITCHER_EXCEEDED=0.40 when a pitcher's 2026 IP already exceeds ZiPS 2027 IP (FINDINGS #53)
stat_2027    = [w_rate x rate_A + (1-w_rate) x rate_B] x [w_pt x PT_A + (1-w_pt) x PT_B]
```

`RELIABILITY` (year-over-year r on rates, hitters 250+ PA n=693, pitchers 40+ IP n=785): SB .739, K .701, HR .607, BB .463, AVG .436, R .425, RBI .380, H .359, WHIP .237, ERA .176, W .151. A regression test refits it on every run (FINDINGS #28). Saves have no ZiPS column: `project.fit_save_model()` gives `SV_next = 0.51 + 0.652 x SV` (R2 0.43, n=1,637), intercept off for starters (`project.project_saves()`). `PROJECTION_BASIS` = `blend` (default) / `projection` / `actuals`, set by env `KLAB_PROJECTION_BASIS` so the app build can run one fresh subprocess per basis. 2028 is raw ZiPS via `keeper.project_2028()`, no blend and no aging curve. `project.projected_2027_levels()` supplies the league level for the 2027 denominators.

### 2.4 Dollar scales

`board.project_all_players()` scores every projected player; `board.value_players()` produces two scales, both floored at $0:

```
pool           = top 140 hitters + top 90 pitchers                   # POOL_RULE="slot_role"; "blind"=top 230 any role
replacement_rp = per role: 140th hitter, 90th pitcher                # WAIVER_VALUE="low"; "medium"=300th; "high"=5.04
usd_per_rp     = (10 x 260 - 230 x 1) / sum(pool rp - replacement_rp)
redraft_value  = max(0, (rp - replacement_rp) x usd_per_rp + 1)      # headline; the pool sums to exactly $2,600
keep_value     = max(0, (rp - intercept) / slope)                     # auction opportunity cost, $10.00/pt
```

The pool is role-constrained because a projection ranks 183 hitters and 47 pitchers into a role-blind top 230, a set no ten teams could field, which handed hitters 73.7% of the budget against a perfect-foresight 52-55% (FINDINGS #65, #68, #69). `meta["replacement_by_role"]` carries the pair and is used by `value_2028`, the bootstrap bands and the decision audit (FINDINGS #80); `meta["replacement_rp"]` stays the lower of the two for the remaining scalar consumers (the finish-odds sim's empty-slot fill, `ros_value_over_replacement`), a documented display-layer approximation (MODEL-REVIEW 4.9).

Current: replacement 5.12 HIT / 3.53 PIT, $6.21/rp redraft. Both are computed on expected playing time. `keeper.pt_scale()` / `to_full_time()` produce the counterfactual columns `redraft_value_ft` and `upside_ft` at `KEEPER_PA_FLOOR = 600`, `KEEPER_IP_FLOOR = 150`, `KEEPER_SV_FLOOR = 25`, `KEEPER_RP_IP_FLOOR = 65`, capped at `MAX_PT_SCALE = 2.0`; `keeper.pt_scale_kind()` tags each as `health` or `role` (reliever handed the closer job). `board.value_2028()` prices the out year on the same 2027 scale. `POSITIONAL_ADJUSTMENT` (off) swaps in `keeper.two_position_replacement()` for C and SS (`TWO_POS_SLOTS`); `keeper.positional_replacement()` is the full-spectrum version, disabled for lack of eligibility coverage.

`board.value_players()` also emits `production_value` (an exact alias of `redraft_value`: worth to a roster, not a price) and `market_price` (the auction cost, a separate quantity, filled by `board.attach_market_price()` from `klab/price.py`). Do not blend the two (CONSTRAINTS.md); see section 2.11 and FINDINGS #56, #57.

### 2.5 Replacement level

Three routes, none fitted to agree: the 230th projection (4.81), the auction intercept (3.98, what a $0 purchase returned), and the median 2026 free-agent pickup (5.04, survivorship-biased upward). The 230th projection is used; an internal-consistency check found only 24 of 1,714 unrostered players project above it (FINDINGS #27).

### 2.6 Multi-year surplus and the extension option

`keeper.years_controlled()`, `keeper.keeper_cost()` (salary for codes 1-3; `F` unkeepable, cost 0), `keeper.already_extended()` (salary exceeds last auction price by exactly $5 or $10 while not at an FA price), `keeper.multiyear_surplus()`:

```
y2027 = value_2027 - cost                                           (signed: the decision under evaluation)
y2028 = max(0, (value_2028 - cost) x 0.85)      if years >= 2       (FUTURE_YEAR_DISCOUNT)
y2029 = max(0, (value_2028 - cost) x 0.85^2)    if years >= 3
ext   = code-1 only: max over 1 or 2 extra years of max(0, (value_2028 - salary - 5) x 0.85^k); reports extension_years in {0,1,2}
surplus_multiyear = y2027 + y2028 + y2029 + ext
```

`value_2027` / `value_2028` are `keep_value` and `keep_value_2028` under `KEEP_BASIS = "replacement"`, and `redraft_value` / `redraft_value_2028` under `"redraft"`. The replacement basis is the identified one: keeping at $S forgoes $S of auction budget, which buys `intercept + S x slope` roto points, so the comparison is against what replacing him costs, not against a no-keeper redraft. Backtested at +$6.1 / +$124.6 / +$89.4 of captured keeper surplus across 2024-2026 (FINDINGS #69, #70).

Later years clip at zero because a contract is an option, not an obligation. A retained-but-unused extension right on a code-2 or code-3 contract is worth $0 (FINDINGS #36).

### 2.7 Keeper optimisation

`board.mark_optimal_keepers()`: per team, every player with positive `surplus_redraft`, best first, capped at `MAX_KEEPERS`; if fewer than `MIN_KEEPERS` clear zero, the least-bad six are forced. `api._inflation()`: `inflation = (cap - kept salary) / (cap - kept worth)` given every team keeps optimally; +33% in the current build (moves every rebuild). `freeagents.free_agent_board()` prices the unrostered pool with the contract each player would carry on re-add, multi-year surplus on the same `KEEP_BASIS` scale as the board (FINDINGS #80). `uncertainty.bootstrap_bands()` resamples pooled team-seasons (B=1000) for `value_lo/hi` (redraft scale), `surplus_lo/hi` and `p_surplus_positive` (the `KEEP_BASIS` scale, replacement refit per draw under `POOL_RULE`; the exchange fit is held fixed, FINDINGS #80).

### 2.8 Trade evaluation, two lenses

`trade.evaluate_trade(board, team_a, team_b, a_sends, b_sends, usd_per_point)` (no default for `usd_per_point`, FINDINGS #32.1). Asset lens: change in `redraft_value`, `keeper_cost`, `surplus_multiyear`, years of control per side. Win-now lens: `trade.win_now_delta()` swaps `trade.ros_lines()` (ZiPS ROS; `ros_basis="blend"` mixes in `prorated_to_date_lines()` current pace, FINDINGS #45) into each team's totals, rebuilds rate stats from implied volume, re-ranks all ten teams with `standings_points()`. `verdict_score = d_surplus + CONTENTION_WEIGHT (0.25) x d_standings_points x usd_per_point`. `trade.ros_value_over_replacement()` is the team-free win-now metric (FINDINGS #34). `trade_finder.suggest_trades()` precomputes three 1-for-1 scenarios per team pair (win-now-for-future, challenge, mutual value) from a sorted shortlist (union of top-10 by talent and by surplus) with a (min, sum) tie-break; the incoming player must have positive standalone value.

### 2.9 Finish-odds Monte Carlo

`standings_sim.simulate_finish_odds()` draws one shared hot/cold shock per player per simulated season, scaled per category by `1 - RELIABILITY` (SV borrows W), applied to rest-of-2026 lines; a hot draw LOWERS ER/BB/hits-allowed (FINDINGS #80.3); reports P(1st) to P(`PAYOUT_SPOTS`) and `p_money`. Playing time is not jittered. `simulate_keeper_finish_odds()` does the same for 2027 keeper cores with replacement fill held fixed, per projection basis. The JS port must agree within 8 points (observed 0.4 to 1.7).

### 2.10 Comp-based auction estimator

`auction_estimator.estimate_auction_price(name, players, k=15)`: `comp_pool()` fits a per-season log-salary regression on `roto_points` and recentres residuals to each season's median; `find_comps()` takes the k nearest by normalised Euclidean distance in per-category roto-point space (`_distance()`), preferring the same `position_group()` and, when `player_tenure() == 0`, other first-timers. `comp_adjusted_low/mid/high` = 25th/50th/75th percentile of the comps' own real salaries (FINDINGS #35, corrected 2026-08-15). Deliberately separate from `redraft_value`.

## 3. Judgment calls

Flip counts are keep/cut changes out of 275 rostered players (`scripts/sensitivity.py`, `out/sensitivity_keep_flags.csv`).

| # | call (current) | rejected alternative | why rejected |
|---|---|---|---|
| 1 | Pooled relative dispersion across seasons | per-season `(max - min)/9`, median gap, IQR, trimmed range, slope | all unstable (mean CV 0.35 to 0.45): the instability is in n=10 data; pooling doubles the sample and divides out level shifts (LAB_NOTEBOOK §1) |
| 2 | Denominator window 2024-26 | 2022-25 | rate-category dispersion broke in 2024 (ERA sigma_rel 13.8%/5.5% vs 3.7%/3.5%); 10 to 17 flips |
| 3 | Exclude partial 2026 for ERA/WHIP/SV only | exclude all rate cats | AVG is not inflated by a partial season, SV is; mechanism is uneven denominator accumulation, not rate vs counting (FINDINGS #26) |
| 4 | Drop teams under 15 SV before the SV denominator, use c_8 | include all ten teams | the saves finding is +2.23 (t=3.75) excluded, +0.92 (t=1.82) included; correct marginal rate for a team contesting saves; 3 to 5 flips |
| 5 | Regress production on price, invert the slope | price on production | attenuation from noisy production claims Ohtani is worth $23; `E[production given price]` is the keep-vs-auction conditional (LAB_NOTEBOOK §6) |
| 6 | `keeper_adjusted` exchange basis | `pooled` ($7.56), `recent` ($9.98) | auctions happened in different keeper regimes; but keeper count and calendar time are collinear (r 0.987), so treat as trend extrapolation (FINDINGS #19); 0 flips |
| 7 | Blend at rate x playing time | blend counting stats | ZiPS durability haircut applied twice buried Alvarez at $4 |
| 8 | Reliability-weighted blend | flat 50/50 | wins repeat at r=0.151; flat weight carried a 3-17 record forward (Christian Scott); 17 to 20 flips |
| 9 | Separate, lower playing-time weight (0.30/0.15/0.40) | one shared weight | a June injury was projecting fewer 2027 innings (Hunter Brown $10.68 to $16.92); caps are judgment, not fitted (FINDINGS #51, #53) |
| 10 | Saves model fit on all pitchers with a workload | fit on SV >= 10 | intercept of 5.01 handed phantom saves to every mop-up arm |
| 11 | Headline on expected playing time; full-time as separate columns | value keepers at full time against unscaled replacement | broke the budget identity ($3,854 vs $2,600); recalibrating flipped 42 of 107 flags (LAB_NOTEBOOK §7.1) |
| 12 | Two-way player scaled on the bat only | both floors | Ohtani's arm lifted 97 to 150 IP, +$20 |
| 13 | Values floor at $0 | signed values | an injured $10 prospect showed as -$38; a bad arm gets benched |
| 14 | `WAIVER_VALUE = "low"` (230th) | `high` (5.04 median pickup) | selected on outcome; implies $16/pt against $7.56 market; 32 flips |
| 15 | Later contract years clip at zero | obligations | Okamoto charged -$9.35 for a 2028 nobody would keep (FINDINGS #13) |
| 16 | `FUTURE_YEAR_DISCOUNT = 0.85` | 1.0 or 0.6 | 0 to 3 flips; low impact |
| 17 | Extension option for code-1 only; `F` unkeepable | option for codes 1-3; live +$5 choice for `F` | constitution: "about to enter the final year"; window closes before the walk-year draft; $130 phantom surplus, 10 flips (FINDINGS #33, #39) |
| 18 | 2028 = raw ZiPS, no aging curve | fit an age curve | ZiPS is age-aware; a second curve double-counts; no age data exists anyway (RESEARCH §6.5) |
| 19 | Positional adjustment off, C/SS only | on, full spectrum | published tests show adjustment hurts; here C and SS came out deeper than pooled (5.12, 6.76 vs 4.80); other positions lack eligibility data (FINDINGS #52) |
| 20 | Win-now lens re-ranks standings | add roto points | category value depends on where a team sits; linear points miss it |
| 21 | `CONTENTION_WEIGHT = 0.25` | 1.0 | rebuilder default: a 2026 standings point is worth a quarter of a 2027 surplus dollar |
| 22 | Monte Carlo jitters player outcomes by `1 - reliability` | reuse the denominator bootstrap | denominator uncertainty is the wrong source for "will my closer hold up" (FINDINGS #55) |
| 23 | Comp estimator anchored to comps' real salaries | percentage premium on `redraft_value` | inherited runaway extrapolation (Skubal $64 against a $34 all-time pitcher ceiling) |
| 24 | Per-season residuals recentred to their median | raw-dollar or log-salary OLS intercept | raw OLS median premium -8% to -22%; log OLS flips positive (retransformation bias) |
| 25 | Comp estimator kept separate from `redraft_value` | fold it in | `redraft_value` is a fair-value regression; blending is roadmap item 1, not done |
| 26 | Team baselines from top-140/top-90 pools rescaled by realization | published league averages | absorbs IL days and empty slots; moderate impact |
| 27 | Trade finder requires positive incoming value | net surplus only | Guerrero-for-Wood passed on net math while returning a $0 rental (LAB_NOTEBOOK §19) |
| 28 | Single HTML file, data inlined | Streamlit server | needs a live Python process; unusable on a phone or at a draft table |

### 2.11 Auction price model (separate, not wired in)

`scripts/price_features.py` rebuilds the ex-ante information a bidder had on auction day for all 677 purchases: prior two seasons' roto points and playing time from `auction.score_season()`, per-category prior line, tenure in this league's auctions, last salary and years elapsed, role, position group, rookie flag, and age from `data/chadwick_register.csv` (`scripts/fetch_chadwick.py`, 98% join on `fg_id`). `scripts/price_model.py` fits `log(salary)` by OLS with season fixed effects, a role interaction on the production terms, Duan smearing back to dollars, P20/P80 quantile fits and a cap at the realised max for the role; an unseen future season carries the most recent training season's effect. `scripts/keeper_revealed.py` fits `P(kept)` on 133 reconstructed 2026 keeper decisions as a second, bid-free calibration. `scripts/compare_valuations.py` puts all five dollar figures side by side.

`klab/price.py` is the production copy the board calls. `board.attach_market_price()` solves a fixed point: the price LEVEL is set by how much salary the keepers tie up, and under a market basis the keeper set is set by the price level. Calibration uses the auction pool (everyone projected who is not a keeper) so free agents count toward the lot count, then rescales the amount above the $1 minimum bid until the lots that clear sum to $2,600 minus committed keeper salary. `market_price_2028` runs the same model one year out with the board's own 2027 projection as the prior season.

Two keeper bases ship. `keep_2027` is production surplus and is the recommendation. `keep_2027_market` is `market_price - keeper_cost`, ROADMAP item 1 Step 4 as specified: it is a transaction-arbitrage lens, it keeps 104 players against 70, and it is documented in FINDINGS #57.5 as refuted for the headline call. Results, including three design errors the held-out season caught, are FINDINGS #56 and #57.

## 4. Validation

| check | result | source |
|---|---|---|
| current rosters rolled over 2026 actuals vs 2026 standings | Spearman 0.588, Pearson 0.691 (2026-09-09 rerun after the split-player dedup, #80.4; the 0.851 and 0.863 in older docs predate the 2026-09-07 evening actuals refresh and were stale). This check decays by construction as the season ages: it credits a team's CURRENT roster with full-season production, and in-season adds banked it elsewhere. Directional only | `scripts/validate.py` |
| replacement level, four routes, none fitted to agree | 5.121 HIT / 3.526 PIT (fieldable pool, used) vs 3.978 (auction intercept) vs 4.381 (300th) vs 4.12-4.39 (observed waiver churn, FINDINGS #62) | `out/model_params.json`, `scripts/waiver_value.py` |
| budget identity | the calibration pool's `redraft_value` sums to exactly $2,600 (caught a $3,854 build) | `scripts/audit.py`, pytest |
| budget identity, role split | The pool is the fieldable 140 hitters / 90 pitchers and allocates 54.2% to hitters, inside the 52.0-55.1% band that perfect foresight on completed seasons produces for the same rule. The league's 63-64% is auction SPEND over a different population and is not this quantity (FINDINGS #68 item 5); do not fix with a budget split, #64 refutes it | `scripts/validate.py` CHECK 5 |
| dollars per realised roto point, by role | hitters $2.092, pitchers $2.114 (ratio 0.99, 668 purchases, every season inside +/-15%): one dollar scale across roles is correct for this league | FINDINGS #64 |
| owners' keeper decisions, 336 scored | 2026 keeps 73.0% right ex ante and 55.4% realised; throw-backs 61.7% and 73.3%. Realised surplus $6.75 against $6.39 | FINDINGS #66, `scripts/decision_audit.py` |
| decision robustness | 92% of keep/cut calls hold across all variants (HANDOFF, 2026-08-14); recount of the committed `sensitivity_keep_flags.csv` gives 246/275 = 89% | `scripts/sensitivity.py` |
| external: CBS roto rank | 0.893 (residual is CBS scoring OBP) | FINDINGS #21 |
| external: FanGraphs ROS auction calculator | Spearman 0.68 to 0.84 on ordering; this scale runs flatter at the top | FINDINGS #54 |
| held-out auction price | fit 2023-25, predict 2026: MAE $5.76 vs $6.84 (prior salary) and $7.20 (comps); band covers 68.8% against a nominal 60% | FINDINGS #56, #63 |
| age effect, engine vs empirical | engine applies +0.621 roto pts to under-25s, empirical persistence says +0.778; indistinguishable | FINDINGS #59 |
| reliability table | refit on every test run reproduces 10 of 10 values | `tests/test_invariants.py` |
| browser vs pandas | 25 quantities, standings exact, dollars at 4-decimal tolerance; Monte Carlo within 8 points | `app/verify.mjs` |
| contract codes vs acquisition year | 83% / 77% / 88% for codes 2 / 1 / F | `out/audit.txt` |
| hand check | 10 players across the value spectrum | `scripts/validate.py` |
| test suite | 64 pytest invariants, ~2.5 min | `tests/` |

Error bars: bootstrap ±34% per category denominator (2,000 resamples; the analytic ±16% assumes normality); ±13% to ±18% per-category standard errors on the app's Model tab. A denominator error leaves within-category rankings intact and moves cross-category weights.

## 5. Known limitations

0. **The biggest one: the model does not beat this league's owners out of sample.** On 289 past keeper decisions, on the only season with clean labels, the owners are 71.6% right and beat a keep-everything baseline by $73.50 while the production rule is 68.7% and beats it by -$10.90. That test runs on a naive projection so it is a floor rather than a verdict, but the valuation machinery was held fixed, which points at the forecast rather than the pricing as the binding constraint (FINDINGS #69).
0b. Three consequences of the #70 changes are load-bearing and unresolved: `MAX_KEEPERS` binds for 6 of 10 teams so the model fills a cap rather than choosing at the margin; the keeper-count equilibrium is unclosed (the exchange rate assumes 100 withheld while the advice implies ~123); and `keep_value` runs rich at the top (Skubal $86.93 against a revealed $34.31).
1. The SV-punter exclusion is the single largest lever; every closer valuation rests on it.
2. Upside is a single counterfactual (`upside_ft`), not a probability-weighted expectation. A comp-dispersion spread feature was tested as a price predictor and rejected (insignificant, loses on LOSO, FINDINGS #57.1); ZiPS P10-P90 remain unused in the projection.
3. No aging curve by decision, and that decision is now empirically supported rather than merely inherited (FINDINGS #59). A 3-year contract's third year still reuses the 2028 figure with a flat discount.
4. Waiver-wire value is now measured from two roster snapshots and disagrees with the internal-consistency route; replacement level is genuinely contested between 4.38 and 5.04 (FINDINGS #62). Transaction data WITH DATES would settle it.
5. Rostered salary ($3,235) exceeds the league cap ($2,600) because $260 is the AUCTION budget for 23 active slots and reserve players sit outside it (constitution, roster composition). Not a discrepancy; the $2,600 identity is over the 230 active slots, which is the right frame (FINDINGS #75).
6. Uncertainty is propagated to `redraft_value` and `surplus_multiyear` (on the `KEEP_BASIS` scale since #80) only; the exchange fit inside the surplus draws is held fixed, so its own ~±40% (#7) is not in the bands; the comp estimator is a point estimate.
7. Positional replacement covers C and SS only, off by default; 1B/2B/3B/OF lack eligibility data.
8. `production_value` exceeds market prices at the TOP and falls short of them everywhere else: over all 277 rostered players it is 0.74x committed salary, but 1.39x across the top 50 and 0.19x across the bottom 157. Stars are underpriced and scrubs overpriced, which is why keeping is profitable. `market_price` is the only column comparable to a draft price (FINDINGS #75).
9. The comp estimator still has no age axis, though age now exists in `data/chadwick_register.csv` and is used by the price and keeper models. Position coverage is fixed: `position_map()` was blank for 48% of the roster and is now 100% (FINDINGS #61).
10. Exchange rate is poorly identified: 2026 split halves give $6.55 and $20.38; keeper-count mechanism not separable from time (n=5 auctions).
11. Small n everywhere: 17 to 30 team-seasons per denominator, 404 purchases, 38 closers.
12. No in-season sequence; roto points add linearly across categories and a per-team correction was built, measured and rejected as unestimable on ten teams (FINDINGS #60), leaving the win-now lens as the only workaround. Draft modelled as a price not a game; inflation fixed rather than solved as an equilibrium of the model's own advice (RESEARCH §6).
13. `already_extended()` cannot tell a $5 + $5 extension from a $10 FA re-add; dormant today (FINDINGS #32.3). deGrom and Turang `F` codes do not reconcile with the draft record (FINDINGS #25). Keeper files for 2022-25 fail two accounting identities (`out/audit.txt`).
14. `out/trade_suggestions.json` is a snapshot, rebuilt only by `scripts/build_trade_suggestions.py` (~135 s), not by `run_all.py`.

## 6. Prior art

Standings Gain Points is the mainstream method and the winner of FanGraphs' 13-system test against 50 real leagues (SGP with Schechter denominators r=0.9697; the same method with different denominators finished seventh, so denominator choice matters more than method choice). Systems with larger positional adjustments did monotonically worse; Razzball settled on none. Smart Fantasy Baseball's point that the ratio of denominators matters more than their level is what mean-normalised pooling implements.

Every published tool (FanGraphs Auction Calculator, RotoWire Custom Auction Values, FantasyPros) converts points to dollars by assuming the budget divides over a fixed pool. This engine regresses realised production on prices actually paid in this league, so waste is priced in, the rate is league-specific, and drift is measurable ($4.16/pt in 2022 to $9.98 in 2026). RotoWire's keeper-inflation calculator is single-year with no valuation behind it; dynasty trade calculators (Dynatyze, FantasyTradeLab) are rankings-based with no salary dimension. Nothing found combines league-calibrated category valuation, option-valued multi-year contracts with a priced extension, a priced free-agent pool, and a two-lens trade evaluator. Commercial tools are ahead on data volume, positional eligibility, and daily updates; everyone is equally blind on category balance and in-season sequence. Taken from the literature: inflation-adjusted display (built), earned-vs-projected values (`leaderboard_2026.csv`), tiers over point estimates, relative-denominator checks, and testing positional adjustment before assuming it (FINDINGS #52).

## 7. Module map

| file | role |
|---|---|
| `klab/config.py` | every league rule and modelling knob; nothing downstream hard-codes a rule |
| `klab/io.py` | CSV loaders, `cached` memoiser, `NameResolver` (671/677 draft names to FanGraphs ids), position eligibility, MLB team map |
| `klab/denoms.py` | pooled relative dispersion, denominators, field size per category, team baselines, `RotoScorer` |
| `klab/auction.py` | draft-to-production matching, auction sample, OLS regression, specification battery |
| `klab/project.py` | 2027 rate x playing-time blend, `RELIABILITY`, saves persistence model, 2027 league levels |
| `klab/keeper.py` | ZiPS 2028 loaders, full-time scaling, years controlled, keeper cost, extension detection, `multiyear_surplus`, positional replacement |
| `klab/board.py` | exchange rate, player valuation on two scales, 2028 values, `build_board`, optimal keeper sets |
| `klab/freeagents.py` | unrostered pool priced with the contract each player would carry |
| `klab/trade.py` | two-lens `evaluate_trade`, rest-of-season lines (ZiPS, pace, blend), `win_now_delta`, `ros_value_over_replacement`, `format_trade` |
| `klab/trade_finder.py` | precomputed 1-for-1 suggestions, three scenarios per team pair, deterministic tie-break |
| `klab/standings_sim.py` | Monte Carlo finish odds for rest-of-2026 and for 2027 keeper cores |
| `klab/uncertainty.py` | bootstrap bands on `redraft_value` and `surplus_multiyear`, `p_surplus_positive` |
| `klab/auction_estimator.py` | comp-based next-auction price estimate, tenure-aware, anchored to real salaries |
| `klab/api.py` | `snapshot(positional=False)`: the one object every interface reads; `write_snapshot`, `load_snapshots` (Parquet, gitignored) |
| `scripts/run_all.py` | rebuild every output in `out/` including the app (excludes trade suggestions) |
| `scripts/build_app.py` | inline three per-basis payloads plus standings, finish odds, comps into `app/template.html`; writes `out/app_reference.json` |
| `scripts/build_trade_suggestions.py` | precompute `out/trade_suggestions.json` for all 45 team pairs (~135 s) |
| `scripts/validate.py` | standings correlation, hand-checked players, budget identity, calibration-pool role split (CHECK 5) |
| `scripts/decision_audit.py` | scores the OWNERS on 336 past keeper decisions, ex-ante and realised verdicts separate (`out/decision_audit.csv`) |
| `scripts/audit.py` | roster accounting, salary cap, contract-code consistency, stats vs standings (`out/audit.txt`) |
| `scripts/sensitivity.py` | rebuild under each contested knob; `out/sensitivity_constants.csv`, `out/sensitivity_keep_flags.csv` |
| `scripts/eval_trade.py` | CLI: `"Team A" "Team B" "P1,P2" "P3,P4"` |
| `scripts/estimate_auction_price.py` | CLI: comp-based price for one player |
| `scripts/team_reports.py` | per-team keeper recommendations and 2026 acquisition channels |
| `scripts/leaderboard_2026.py` | 2026 realised value and hindsight auction prices |
| `scripts/lookup.py` | print board rows for named players |
| `app/template.html`, `app/verify.mjs` | the interface, and the headless-browser diff of its JS against pandas (17 checks; three of them exist only because a reader found a defect first, FINDINGS #73, #74) |
| `scripts/build_survey.py`, `app/verify_survey.mjs`, `scripts/ingest_survey.py` | the blind keep/cut survey for a human reviewer, its flow check, and the scorer (FINDINGS #77) |
| `out/keeper_lab.html` | the app: one 6.7 MB file, 7 tabs, no server |
| `out/keeper_board_2027.csv` | 275 rostered players with values, costs, surplus, bands, flags |
| `out/model_params.json` | fitted constants: exchange rate, save model, denominators, baselines, config |
| `out/app_reference.json` | pandas ground truth for `app/verify.mjs` |
| `out/trade_suggestions.json` | precomputed trade finder output |
| `out/auction_sample.csv` | one row per historical purchase with price and delivered roto points |
| `out/audit.txt` | data-integrity identities |
| `out/denominators_by_season.csv` | per-season denominators under each estimator |
| `out/sensitivity_constants.csv`, `out/sensitivity_keep_flags.csv` | sensitivity harness output |
