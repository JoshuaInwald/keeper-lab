# Roadmap

Effort in focused sessions (~2 hours each). Built-and-validated inventory is in `docs/METHODS.md` section 4; history in `docs/SESSION-LOG.md`. This file is only what is next, ranked.

## 1. Market-price recalibration (3-4 sessions; the priority)

**Status 2026-09-08: item 1 is complete. All five steps built; Steps 4 and 5 produced negative results and are not shipped as specified (`docs/FINDINGS.md` #56, #57).** `market_price` is live on the board, calibrated so the 126 lots the 2027 auction will sell sum to the $1,765 that will be in the room. Held-out 2026 MAE 5.76 against 6.84 for prior-salary and 7.20 for the comp estimator; P20-P80 coverage 55.4% after conformal calibration, against a nominal 60%. `keep_2027` still runs on the production basis: Step 4's market-arbitrage rewire keeps 104 players including 30 below replacement and cuts Skubal, so it ships as a second lens (`surplus_market`, `keep_2027_market`) rather than as the recommendation. Four claims in the diagnosis below did not survive contact with the data, and are corrected in #56 and #57: the 25% no-prior-line share is 80% censoring of 2022; the 2022-2025 keeper files are not keeper submissions; the market's implied inflation does NOT agree with `api._inflation()` (1.96 against 1.33); and the market pays no measurable premium for upside spread.

### The problem, stated precisely

A league-mate with ten years of this league's auctions reviewed the app (2026-08-15) and flagged the headline number ("Worth '27", `redraft_value`) as wrong for a cluster of players: young players with little track record read too cheap (McGonigle $8, Wetherholt $9, Dingler $2, Kurtz $23), an elite starter reads above anything ever paid (Skubal $52; `keep_value` $79; the league's ceiling is $45 for any player, $34 for a pitcher), an established veteran off a down year reads at replacement (Wheeler $6).

Diagnosis (2026-09-07, `out/auction_sample.csv`, 677 purchases): these are not player-level misses. The model prices the wrong quantity with the wrong estimator.

| symptom | cause | evidence |
|---|---|---|
| top end too high | dollar scale is the INVERSE of a regression of production on price (`fit_exchange_rate`). With R^2 ~0.23, inverting inflates $/pt by ~1/R^2 | E[price given production] slope is $1.25/pt; the inverted scale is $5.33/pt (pooled), $9.17 keeper-adjusted |
| production explains little of price | bidders pay for expectations, youth, name and anchors, not last year's roto points | prior-year roto points explain 11% of price variance; same-season realized production 23% |
| young/no-track-record players too cheap | 25% of purchases (n=167) are players with no prior MLB line; the market pays them $11.3 mean for $5.0 realized; the model has no upside distribution and no tenure feature | purchases with 0-1 ex-ante roto points sell for $10.5 mean, more than the 1-7 point bins |
| veterans off a down year too cheap | the 2026-actuals leg of the blend carries one bad season; the market anchors on the last contract | among re-auctioned players (n=227), prior salary carries coefficient 0.48 and doubles R^2 (0.25 to 0.45) |
| pitchers overpriced at the top | market pays pitchers ~0.5x the per-point rate of hitters and caps at $34 | hitters slope 1.10 $/pt (max $45); pitchers 0.48 $/pt (max $34) |
| wrong calibration identity | `redraft_value` normalises the top 230 to $2,600, a full-redraft counterfactual no auction here has ever run; the real auction has ~110-160 lots and $2,600 minus keeper salaries | 2026: 112 purchases, mean $11 |

Pushback on the review itself: a single owner's price sense is a noisy instrument with an endowment tilt (several flagged players sit on the reviewer's own roster), and auction prices have irreducible noise (nomination order, budget dynamics). The target is the league's revealed prices, validated out of sample, not agreement with any one owner's calls. The previous plan (blend the comp estimate into `redraft_value`, then rescale to $2,600) is withdrawn: it muddles two quantities that should stay separate.

### The approach

**Step 0. Split the quantities and rename the columns (0.5 session). [BUILT]** Keep `production_value` (roto points above replacement on a budget scale: what a player is worth to a roster) and add `market_price` (what he will cost at this league's auction). The gap between them is the buy/sell signal and belongs on the board as its own column. Drop "Worth '27" as a label.

**Step 1. Ex-ante feature set (1 session). [BUILT]** Bidders see projections, not realized production. Build, for every purchase 2022-2026, the information available on auction day: prior two seasons' stat lines (available in `fg_*_2022_2026.csv`), a rookie/new-to-league flag, tenure in this league's auctions (`player_tenure()`), last contract salary and years elapsed (`draft_salaries_all.csv`), role, position group, and age. Age is missing from every file: pull birth year by `fg_id` from the Chadwick register (one CSV join). If historical preseason projections can be obtained (FanGraphs ZiPS/Steamer archives, or the owner's own saved exports), they replace the prior-season proxy and should raise R^2 materially.

**Step 1b. Keeper decisions as revealed preference (0.5-1 session, Josh's idea 2026-09-08). [BUILT]** Every keep/throw-back is a censored observation of the owner's value: kept at salary S means value >= S, released means value < S. Build the eligible set per season (everyone bought in the two prior auctions plus prior keepers, minus known departures), join the keeper file, and fit `P(kept | production features, salary, years of control left)`; the salary at which P(kept) = 0.5 for a given production level is the owners' implied price, a second calibration independent of auction bids and the exact margin the tool decides on. Data caveat to settle first: `keepers_2022..2025.csv` hold 25-29 players per season (2-6 per team) against 100 in 2026; either the 6-13 keeper rule is new in 2026 (then the early files are a complete top-3 ranking per team, an even stronger signal) or the files are partial (then rebuild them from CBS preseason rosters before using them). FINDINGS #16/#19 already flagged this ambiguity; resolve it with the commissioner, do not infer it.

**Step 2. Price model, fit directly (1 session). [BUILT]** `log(price)` or a Tobit at the $1 floor, regressed on the Step 1 features with season fixed effects (inflation) and role interactions. Start with a GLM; try a monotone gradient-boosted model only if the GLM's held-out error is poor. Add quantile fits (P20/P80) for the range the comp panel shows today. Acceptance: leave-one-season-out on 2026 (fit 2022-2025), report MAE, Spearman, calibration by price decile, coverage of the P20-P80 band, and the top-end check (no prediction above the realized max for the role). Baseline to beat: the current comp estimator and a naive prior-salary-plus-inflation rule.

**Step 3. Calibrate the level to the actual auction (0.5 session). [BUILT]** Predicted prices for the projected 2027 auction pool (rostered non-keepers plus the free-agent pool) must sum to the projected budget: $2,600 minus committed keeper salaries, spread over the expected lot count. This replaces the top-230 identity for `market_price`; `production_value` keeps its own identity. Report the implied inflation next to the existing `remaining budget / remaining worth` figure; they should agree.

**Step 4. Rewire the decisions (1 session). [BUILT, NOT ADOPTED AS THE HEADLINE]** Keeper surplus becomes `market_price - keeper_cost` (the cost to replace him at auction), summed over control years with `market_price_2028` from the 2028 projection and the same price model. Trade evaluation keeps both lenses and adds a market lens. Optimal keeper sets, `surplus_multiyear`, the Contention tab, and the comp panel all read the new column; the comp estimator becomes a diagnostic view of the residuals rather than a separate price.

**Step 5. Upside as a feature, not an afterthought (1 session, can follow 1-4). [TESTED AND REJECTED]** ZiPS P10-P90 columns are already in the export. Add spread (P90 minus P50) to the price model; test whether the market pays for it (hypothesis: yes for hitters under tenure 2, no for pitchers). This is the principled version of "rookies are undervalued" and subsumes the parked rookie item.

**What to expect.** Even a good model will leave roughly half the price variance unexplained; report that ceiling rather than tune to the reviewer's list. The ordering of players by `production_value` is already validated (Spearman 0.85-0.89 against three external systems); what changes is the dollar level and the identity of who is cheap relative to market.

## 2. Team-specific category value (1 session to scope)
Roto points add linearly today; the marginal value of a category unit depends on where a team sits in it. Turn one value per player into one per team. The trade evaluator's win-now lens already re-ranks standings; the general fix is unbuilt. Highest-value gap after item 1.

## 3. Intuition tab v2 (scope needs a decision)
Show each player's PA/IP and per-category rates; three ways to adjust (+/- buttons, direct entry, presets such as full-time); all 230 rostered players grouped by team with contract fields. Open decision: sandboxed (as now) or a propagating override that flows through the 2027 pipeline. The propagating version is a materially larger change; decide before scoping.

## 4. Waiver-wire value (1 session)
Free agents supply ~40% of roto production at $10-20 each. Quantify it to sharpen replacement level, the anchor for every dollar figure.

## 5. Uncertainty ranges on Board/Trade/Standings tabs (design pass)
Per-cell tooltip reusing the existing bootstrap bands.

## 6. Small, contained
- `position_map()` returns UNKNOWN for some players (Cade Smith), thinning comp pools.
- 2027 odds live in the Trade tab (`simulate_keeper_finish_odds(keeper_override=...)` already accepts the input).
- FA tab "likely range" is blank by design; `value_lo/value_hi` could be extended cheaply.

## Declined or parked (do not reopen without a reason)
Aging curves (ZiPS carries age). Auto-refresh (no ingestion step exists). Probability-weighted closer upside (low priority; if built, report a range via the existing bootstrap). Name-brand / good-MLB-team premium (no MLB standings data in `data/`; item 1 Step 1's tenure and prior-salary features cover the tractable part). Mobile nav overflow. Transaction-log scraping (2 sessions, unlocks manager-skill analysis; nice to have).
