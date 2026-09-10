# Session handoff

Current state only; history is in `docs/SESSION-LOG.md`, evidence in `docs/FINDINGS.md`.
Last updated 2026-09-09. Read `CONSTRAINTS.md` first, then this. The full
bottom-up model review, with ranked error sources and the projection refresh
calendar, is `docs/MODEL-REVIEW.md`.

## What this project is for

**One objective: the best possible keeper and auction decisions in the 2027 draft.** Two decisions carry real money, in this order:

1. **Keep or throw back**, for each contract, at the 2027 deadline. Decided before the auction and constrains everything after it.
2. **What to pay**, live in the 2027 auction, for whatever the keeper round leaves.

Three consequences that should decide what a session does:

- **A number matters only if it flips a decision.** The rule that a valuation change reports keep/cut FLIPS rather than correlations is the operational form of this.
- **The projection is the binding constraint, not the valuation machinery.** #69 held the machinery fixed and the model still failed to beat the owners. The two machinery defects it exposed have since shipped (#70), so what is left is the forecast.
- **Precision beyond the decision is waste.** Knowing which twelve players are mispriced by more than $8 changes the draft; a third decimal on `usd_per_rp` does not.

Marcel 2027 will not exist before either date (Baseball-Reference publishes after a season ends), so **the 2027 board stays ZiPS** and the Marcel path is a backtesting instrument only.

## System
- Repo `~/PycharmProjects/keeper-lab` on the Mac, GitHub `JoshuaInwald/keeper-lab` (`main`), read-only mirror at `~/Documents/Fantasy Baseball/keeper-lab/`. Three-surface rule in `CLAUDE.md`.
- Build `PYTHONPATH=.:scripts python3 scripts/run_all.py`; tests `PYTHONPATH=. python3 -m pytest tests/ -q` (64 pass); app check `node app/verify.mjs` (21 pass since #81).
- `data/` current to 2026-09-07 (2026 season ~88% played at that pull). Refresh cadence in `data/README.md`.
- Committed numbers after #70: **$10.00** per roto point (auction scale), **$6.21** (redraft scale), replacement **5.12 HIT / 3.53 PIT**, 123 flagged keep. All move on a rebuild; quote from `out/model_params.json`.

## State of the model
- Two dollar scales plus a price. `production_value` (alias of `redraft_value`) is worth to a roster on the $2,600 budget scale. `keep_value` is auction opportunity cost and totals far more than $2,600 on purpose: that excess is the keeper discount. `market_price` is the only one comparable to a draft price, fitted on 677 purchases, held-out MAE 5.76 against 6.84 (prior salary) and 7.20 (comps). **Never blend them** (`CONSTRAINTS.md`). #75 has the full reconciliation.
- `keep_2027` runs on `keep_value` (`KEEP_BASIS = "replacement"`, #70); the old redraft basis is still selectable. The calibration pool is the fieldable 140/90 (`POOL_RULE = "slot_role"`, #70).
- `keep_value` runs rich at the top: Skubal $86.93 against a revealed $34.31. The decision only needs it to clear his cost, so the ordering is safe and the level is not.
- The app carries `Roto '26`, `Roto '27` and `Move` in standings places (#72), a `playing time` selector (#76), and per-category decomposition on hover (#74).
- Since 2026-09-09 (#80): 2028 values and the owner audit use per-role replacement; the bootstrap bands follow `POOL_RULE` and `KEEP_BASIS` (they bracket the headline surplus now); the Monte Carlo shock sign is fixed for pitcher negative stats; Ohtani counts once in every roster sum and is tradeable in the finder; free-agent surplus is on the keep scale.
- Since 2026-09-09 evening (#81, `docs/UI-REVIEW.md`): the app payload is de-aliased (5.0 MB, was 7.3; startup runs `applyVariant()` like a basis switch), the League tab survives every basis, a split player is one asset in the JS trade path, the drawer reconciles per role, and the presentation prose matches the post-#70/#80 model. `verify.mjs` carries 21 checks.
- Age exists (`data/chadwick_register.csv`); the market discounts 8.0% per year holding production constant. This does not reopen the aging-curve decision for production, which `CONSTRAINTS.md` declines.
- Ohtani is two 2027 assets. `F` contracts are unkeepable. Payout 50/25/15/breakeven.
- Unresolved data questions: Skubal's +$15 salary step and the deGrom/Turang contract clocks (#23.4, #25).

## Diagnostics (none are in `run_all.py`; run on demand, `PYTHONPATH=.:scripts`)
| script | what it does |
|---|---|
| `validate.py` | five checks including CHECK 5, the pool's role split. Must print 140/90, $2,600, 54.2% |
| `validate_marcel.py` | re-derives ten published identities on the Marcel archive. Run before trusting it |
| `marcel_pool_test.py` | the #68 pool analysis; asserts seven published numbers as controls |
| `backtest_keepers.py` | the out-of-sample keep/cut test on 289 decisions (#69), built on `klab/rewind.py` |
| `fit_blend.py` | sweeps the blend constants with leave-one-season-out (#70) |
| `build_survey.py` | writes `out/keeper_survey.html`, the blind keep/cut survey for a human reviewer (#77) |
| `ingest_survey.py` | scores returned survey answers against the model and against each other (#77) |
| `sensitivity.py` | exports `knob()`, which overrides config and clears every cache both ways |
| `fetch_chadwick.py`, `price_features.py`, `keeper_revealed.py`, `price_model.py`, `compare_valuations.py` | the item-1 price chain, in that order |
| `fetch_marcel.js` | rebuilds the Marcel archive from a browser session; `data/` is gitignored so a fresh clone needs it |

## Next session: start here

**Deliverable: the valuation-curve and exchange-rate variant set, as user-facing toggles.** Josh's ask (2026-09-09, expanded the same evening after reading the MODEL-REVIEW report): the exchange rate is the most suspect link in the chain, so do not just bend the rp-to-$ curve; build ALTERNATIVE EXCHANGE-RATE ESTIMATORS too, give the same scrutiny to `market_price` where it is cheap, and surface the replacement-level anchor as a visible toggle with the best option as default. Every variant is scored the same way: keep/cut FLIPS against the shipped board (`backtest_keepers.py` re-scored where the variant touches the decision), never correlations.

1. **Alternative rp-to-$ curves (the original ask).** The dollar scales are linear in roto points; three instruments say the market is concave at the top and the $1 floor bends the bottom (#56.5 revealed keeper price $38.54 vs `keep_value` $83.02 at the top decile; #57.6 Skubal $34.00/$34.31 market/revealed vs $86.93; #75 tier ratios 1.39x/0.93x/0.19x; #2 band table and the $45 all-time ceiling). The prior art is all on the PRICE model and all three non-linear attempts there LOST out of sample (#57.2 monotone GBM, #62.5 bounded logit, concave transforms; the recorded conclusion: top-end overshoot and top-end accuracy are the same knob). The only non-linearity that ever shipped is #63's $1-point-mass hurdle. The VALUE-side curve is untried: monotone splines (shape-constrained, knots at the tails), LOSO before anything ships, and the $2,600 identity recalibrated inside each variant (`scripts/audit.py`) or the budget check fails.
2. **Alternative exchange-rate estimators (Josh's addition).** The current estimator is two stacked OLS fits: points-on-salary per season, then $/pt-on-keeper-count across n=5 seasons, predicted at 100 keepers (`fit_exchange_rate` in `klab/board.py`, `EXCHANGE_BASIS = "keeper_adjusted"`). Candidates to build and score: a tiered exchange (separate $/pt by salary or points tier; the #75/#2 evidence is already tiered, so this is near-free); window variants (2024-25 only, 2024-26 pooled, 2026 alone: the "recent" basis exists in config and has never been surfaced); partial pooling (shrink per-season fits toward the pooled $5.83 instead of choosing a basis); robust or median regression against the $1 mass and right skew. Identification caveat no new fit escapes: keeper count and calendar time are collinear at n=5 (#19), so every variant is a different extrapolation of the same five points, not new information; the decision test is the only arbiter.
3. **`market_price`, same feedback, narrower scope.** The cap attacks are settled negatives; do not re-run them (#57.2, #62.5). The open, cheap refinement is tiered inflation (MODEL-REVIEW section 2, Clemens): the app's headline inflation is one scalar over a phenomenon the league's own data says is tiered (stars 1.39x, scrubs 0.19x, #75).
4. **Replacement level as a visible toggle.** The board HAS a fixed anchor since #70: per-role bars, the 140th-best hitter (5.121) and 90th-best pitcher (3.526), `WAIVER_VALUE = "low"`. What stays contested is the anchor family, #62's measured tie: the behavioural churn margin says ~4.38 (the "medium" 300th-rank setting), internal consistency says 4.73 ("low": at 4.38 the model calls 106 free agents better than the marginal rostered player, which free cannot mean), and the median FA pickup says 5.04 ("high", known optimistic). Only dated transaction logs would settle it (declined). So do what Josh asked: keep "low" as the shipped default, expose the three anchors as a dropdown in the ship-both-variants pattern, and report the flips (from #62: the medium switch moved $/rp 6.52 to 5.33 and Skubal $52.75 to $45.20 on the then-current build; eight sign changes, all marginal).
5. **Punters, for the record (Josh asked).** The SV exclusion exists and is load-bearing: closers beat their price only because the SV denominator uses the 8-team competing field (#1); putting punters back in moves 5 keep/cut calls and mostly closer PRICES, not decisions (#6). Open but small: there is no SB equivalent, and punting is detected by a fixed realised-saves threshold (`SV_PUNT_THRESHOLD = 15`) rather than intent. Not part of this deliverable unless a variant makes it bind.

Session rules that bite here: keep flags follow the shipped default only (#76); the payload has NO top-level board aliases since #81, so every variant ships inside the `basis_variants` shape and the template initialises through `applyVariant()`; payload budget is 5.0 MB now and each replacement/curve variant adds a board+fa+teams core (~400 KB x 3 bases), with the ~3.1 MB of auction comps as the relief valve (UI-REVIEW section 3); four edits per new column, all four now guarded; tooltips under the #74 contract, and the raw-string audit fails on jargon or file references.

The survey (item 0 below) is still Josh's own task and still first if he is present.

## Open, in priority order

0. **Run the survey (`docs/WORKFLOWS.md` 6b). It is the only item here that can be done today.** `out/keeper_survey.html` collects blind keep/cut calls from Pookie 2.0's owner and from Josh; `scripts/ingest_survey.py` scores them against the model and each other. #69 makes a good owner a benchmark rather than a reviewer, and the role-split price calibration is the test of the model's most falsifiable claim (20 of its 25 biggest bargains are pitchers).
1. ~~Re-score the #70 combination~~ **Done, #79.1**: the MAX_KEEPERS cap changes zero of 289 backtest calls, so the shipped rule scores as `model_replace` in #69: it edges the owners on 2026 dollars (+$78.6 vs +$73.5 vs keep-everything) and trails on accuracy (64.9% vs 71.6%). It wins by sizing, not classification.
2. **Attack the projection, on this calendar (`docs/MODEL-REVIEW.md` section 5).** No 2026-aware 2027 projection exists anywhere before ~Nov 2026. First week of Oct: refresh 2026 final actuals. ~Nov: Steamer 2027 lands on FanGraphs, first 2026-aware system; ingest as `PROJ_2027_*` (a filename switch). Nov-Jan: fresh ZiPS 2027 + DC. ~Feb: ATC (an accuracy-weighted aggregate; aggregates beat every single system in every published test). FanGraphs CSV export is members-only now; budget the membership.
3. **Two consequences of #70 still carry weight; the third is measured and small.** `MAX_KEEPERS` binds for 6 of 10 teams, so the model fills a cap rather than choosing at the margin. `keep_value` is rich at the top. The keeper-count equilibrium is now closed by measurement (#79.35): the loop converges at 121 keeps against the shipped 123, flipping only Brooks Lee and Kyle Stowers, so it is a two-flip worry, not a structural one.
4. **`WAIVER_VALUE` is open and now matters more.** Replacement is a per-role pair since #70 (5.121 HIT / 3.526 PIT). The #62 tie (4.381 from waiver churn against the internal-consistency objection) should be re-asked in that frame. Transaction logs WITH DATES would settle it.
5. **The projection-source toggle.** Build last; `PROJECTION_BASIS` is the precedent. Backward-facing only, since Marcel 2027 does not exist.
6. **`data/positions_2026.csv` goes stale.** A roster-time snapshot; rebuild when comp pools look wrong.
7. **Intuition tab v2 is blocked on Josh, not on work**: sandboxed overrides, or overrides that propagate through the 2027 pipeline. The propagating version is materially larger.

## Deliberately NOT built, with the evidence
- **A hitter/pitcher budget split.** The league pays the same per realised roto point for both roles (2.092 against 2.114). Refuted on its own data. #64.
- **Per-team category multipliers.** 0.29x-13.28x within a season, persistence -0.07 across. Implementation kept in `klab/teamvalue.py` so nobody rebuilds it. #60.
- **An upside/spread price feature.** Both terms insignificant, loses on LOSO. #57.1.
- **Removing the role cap.** Three mechanisms tried, all trade top-end accuracy for safety. #62.5.
- **An aging curve on the projection.** The engine already applies +0.621 roto points to under-25s against an empirical +0.778. #59.
- **`keep_2027_market` as the headline call.** Keeps 104 including 30 below replacement, and cuts Skubal. #57.5.
- **Changing the blend weights.** Swept in #70: the curve is flat from 0.5 to 1.0 and no alternative survives leave-one-season-out. `scripts/fit_blend.py` is the harness; do not re-sweep without new seasons.
- **Relaxing the reliability discount** so recent ERA counts for more. Swept; production is the maximum. #71.3.
- **A custom hover card** for the tooltips. Native tooltips use a proportional font and there is no hover on a phone; the drawer covers touch. #76.

## The standing trap (#78, four defects on 2026-09-08; #80.2 was the same class)

**A change to a dollar scale, a column, or a decision basis is not finished when the tests pass. It is finished when the thing a reader sees has been looked at.** Every defect a reader has found was presentation-layer fallout of a model change; the guards that exist (`assertBoardRowShape()`, the rendered-cell check, the tooltip checks) each exist because a human found the defect first.

## Rules that bite
- **Adding a board column takes FOUR edits** (#73): `BOARD_FIELDS` in `scripts/build_app.py`, `BOARD_COLS`, a `<td>` in `playerRow()` **at the same index**, and the phone CSS `nth-child` hide-list. Three of the four fail silently; forgetting the `<td>` shifts every column right of it under the wrong heading, which shipped twice.
- **The tooltip contract** (#74), written above `COL_HELP` and enforced by three `verify.mjs` checks: what the number is in under ~15 words, at most two more sentences, no unglossed jargon ("roto points" is always "places in the standings"), **never a file or finding reference**.
- **A `KEEP_BASIS` / `POOL_RULE` change is not done when the tests pass** (#71.1). The app states its arithmetic in prose and prose is untested by default; grep `app/template.html` for the affected labels whenever a dollar scale changes hands.
- **Score keeps on the opportunity-cost scale, never `redraft_value`** (#69). The latter is a no-keeper market and makes only 23% of past decisions read as correct keeps against 54% on the right scale.
- **Read dollar totals against keep-everything, not zero** (#69).
- **2024-25 keeper labels are reconstructed and biased against the owners** (#56.4); **2026 outcomes are a partial season**. No season has both. Never pool them.
- **Marcel is not ZiPS** (#67). Constants fitted against it describe the Marcel blend; report shapes.
- `scripts/validate.py` CHECK 5 must print 140/90 and a 54.2% hitter share, and warns outside 52-58%.
