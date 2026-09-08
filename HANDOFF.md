# Session handoff

Current state only; history is in `docs/SESSION-LOG.md`, evidence in `docs/FINDINGS.md`.
Last updated 2026-09-08. Read `CONSTRAINTS.md` first, then this.

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
- Build `PYTHONPATH=.:scripts python3 scripts/run_all.py`; tests `PYTHONPATH=. python3 -m pytest tests/ -q` (64 pass); app check `node app/verify.mjs` (17 pass).
- `data/` current to 2026-09-07 (2026 season ~88% played at that pull). Refresh cadence in `data/README.md`.
- Committed numbers after #70: **$10.00** per roto point (auction scale), **$6.21** (redraft scale), replacement **5.12 HIT / 3.53 PIT**, 123 flagged keep. All move on a rebuild; quote from `out/model_params.json`.

## State of the model
- Two dollar scales plus a price. `production_value` (alias of `redraft_value`) is worth to a roster on the $2,600 budget scale. `keep_value` is auction opportunity cost and totals far more than $2,600 on purpose: that excess is the keeper discount. `market_price` is the only one comparable to a draft price, fitted on 677 purchases, held-out MAE 5.76 against 6.84 (prior salary) and 7.20 (comps). **Never blend them** (`CONSTRAINTS.md`). #75 has the full reconciliation.
- `keep_2027` runs on `keep_value` (`KEEP_BASIS = "replacement"`, #70); the old redraft basis is still selectable. The calibration pool is the fieldable 140/90 (`POOL_RULE = "slot_role"`, #70).
- `keep_value` runs rich at the top: Skubal $86.93 against a revealed $34.31. The decision only needs it to clear his cost, so the ordering is safe and the level is not.
- The app carries `Roto '26`, `Roto '27` and `Move` in standings places (#72), a `playing time` selector (#76), and per-category decomposition on hover (#74).
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

## Open, in priority order

1. **The model does not beat the owners out of sample (#69), and #70 has not been re-scored.** #69 measured each change in isolation; the shipped combination has never been run through `backtest_keepers.py` at the new defaults. Cheapest first move of any session.
2. **Attack the projection.** The blend constants are fitted and flat (#70), so the gains are in the SOURCE: a fresh ZiPS 2027 export incorporating the finished 2026 season is the highest-value data refresh available before the auction. Steamer or THE BAT as a second opinion is the next step after that.
3. **Three consequences of #70 are now load-bearing.** `MAX_KEEPERS` binds for 6 of 10 teams, so the model fills a cap rather than choosing at the margin. The keeper-count equilibrium is not closed: the exchange rate assumes 100 withheld while the advice implies ~123. And `keep_value` is rich at the top. None is obviously an error; all three now carry weight.
4. **`WAIVER_VALUE` is open and now matters more.** Replacement is a per-role pair since #70 (5.121 HIT / 3.526 PIT). The #62 tie (4.381 from waiver churn against the internal-consistency objection) should be re-asked in that frame. Transaction logs WITH DATES would settle it.
5. **The projection-source toggle.** Build last; `PROJECTION_BASIS` is the precedent. Backward-facing only, since Marcel 2027 does not exist.
6. **`data/positions_2026.csv` goes stale.** A roster-time snapshot; rebuild when comp pools look wrong.
7. **An expert review is scoped and unrun.** `docs/EXPERT-REVIEW.md` holds the question set for Pookie 2.0's owner, blind-first so the answers are scoreable rather than a review. Highest-value question is playing time (44 keeper calls flip on it alone); biggest testable claim is that 20 of the model's 25 largest bargains are pitchers.
8. **Intuition tab v2 is blocked on Josh, not on work**: sandboxed overrides, or overrides that propagate through the 2027 pipeline. The propagating version is materially larger.

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

## Rules that bite
- **Adding a board column takes FOUR edits** (#73): `BOARD_FIELDS` in `scripts/build_app.py`, `BOARD_COLS`, a `<td>` in `playerRow()` **at the same index**, and the phone CSS `nth-child` hide-list. Three of the four fail silently; forgetting the `<td>` shifts every column right of it under the wrong heading, which shipped twice.
- **The tooltip contract** (#74), written above `COL_HELP` and enforced by three `verify.mjs` checks: what the number is in under ~15 words, at most two more sentences, no unglossed jargon ("roto points" is always "places in the standings"), **never a file or finding reference**.
- **A `KEEP_BASIS` / `POOL_RULE` change is not done when the tests pass** (#71.1). The app states its arithmetic in prose and prose is untested by default; grep `app/template.html` for the affected labels whenever a dollar scale changes hands.
- **Score keeps on the opportunity-cost scale, never `redraft_value`** (#69). The latter is a no-keeper market and makes only 23% of past decisions read as correct keeps against 54% on the right scale.
- **Read dollar totals against keep-everything, not zero** (#69).
- **2024-25 keeper labels are reconstructed and biased against the owners** (#56.4); **2026 outcomes are a partial season**. No season has both. Never pool them.
- **Marcel is not ZiPS** (#67). Constants fitted against it describe the Marcel blend; report shapes.
- `scripts/validate.py` CHECK 5 must print 140/90 and a 54.2% hitter share, and warns outside 52-58%.
