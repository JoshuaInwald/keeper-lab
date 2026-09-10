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
- Build `PYTHONPATH=.:scripts python3 scripts/run_all.py`; tests `PYTHONPATH=. python3 -m pytest tests/ -q` (64 pass); app check `node app/verify.mjs` (23 pass since #82). `build_app.py` now takes several minutes: the overlay variants rebuild the board under two anchors and three exchange fits per basis, bootstrap included.
- `data/` current to 2026-09-07 (2026 season ~88% played at that pull). Refresh cadence in `data/README.md`.
- Committed numbers after #70: **$10.00** per roto point (auction scale), **$6.21** (redraft scale), replacement **5.12 HIT / 3.53 PIT**, 123 flagged keep. All move on a rebuild; quote from `out/model_params.json`.

## State of the model
- Two dollar scales plus a price. `production_value` (alias of `redraft_value`) is worth to a roster on the $2,600 budget scale. `keep_value` is auction opportunity cost and totals far more than $2,600 on purpose: that excess is the keeper discount. `market_price` is the only one comparable to a draft price, fitted on 677 purchases, held-out MAE 5.76 against 6.84 (prior salary) and 7.20 (comps). **Never blend them** (`CONSTRAINTS.md`). #75 has the full reconciliation.
- `keep_2027` runs on `keep_value` (`KEEP_BASIS = "replacement"`, #70); the old redraft basis is still selectable. The calibration pool is the fieldable 140/90 (`POOL_RULE = "slot_role"`, #70).
- `keep_value` runs rich at the top: Skubal $86.93 against a revealed $34.31. The decision only needs it to clear his cost, so the ordering is safe and the level is not.
- The app carries `Roto '26`, `Roto '27` and `Move` in standings places (#72), a `playing time` selector (#76), and per-category decomposition on hover (#74).
- Since 2026-09-09 (#80): 2028 values and the owner audit use per-role replacement; the bootstrap bands follow `POOL_RULE` and `KEEP_BASIS` (they bracket the headline surplus now); the Monte Carlo shock sign is fixed for pitcher negative stats; Ohtani counts once in every roster sum and is tradeable in the finder; free-agent surplus is on the keep scale.
- Since 2026-09-09 evening (#81, `docs/UI-REVIEW.md`): the app payload is de-aliased (5.0 MB, was 7.3; startup runs `applyVariant()` like a basis switch), the League tab survives every basis, a split player is one asset in the JS trade path, the drawer reconciles per role, and the presentation prose matches the post-#70/#80 model. `verify.mjs` grew to 21 checks that session (23 since #82).
- Since 2026-09-09 late (#82): the exchange-rate estimator family is built and scored (`klab/exchange.py`, `scripts/exchange_lab.py`); the app carries an "auction fit" dropdown (keeper_adjusted default, pick_level, pooled_2426, median_two_stage) and a "free-player bar" dropdown (low default, medium, high) as column overlays; the anchors are recoded so the pool stays 140/90 and only the bar moves ("medium" used to no-op, "high" used to revert the pool); tiered inflation (0.85x/1.00x/2.19x) sits beside the scalar; comps are 5 per player (was 8). The pick-level fit validates $10.00 at $10.38 with zero flips and +/-$2.76; no curve survived LOSO or the rewound backtest; the projected-points hedonic is refuted. Level uncertainty is real and now visible; ordering is stable.
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
| `exchange_lab.py` | scores the #82 exchange-rate estimator menu: board flips, rewound backtest, LOSO, anchors. Rerun before adding an estimator to the app menu |
| `fetch_chadwick.py`, `price_features.py`, `keeper_revealed.py`, `price_model.py`, `compare_valuations.py` | the item-1 price chain, in that order |
| `fetch_marcel.js` | rebuilds the Marcel archive from a browser session; `data/` is gitignored so a fresh clone needs it |

## Next session: start here

**The 2026-09-09 variant-set deliverable shipped (#82): estimator menu built and scored, two header dropdowns live, anchors recoded, tiered inflation shipped, curves tried and declined on their gates.** What the evidence settled: the shipped $10.00/pt is validated by the family's best-identified member (pick-level, zero flips, +/-$2.76); the level is genuinely uncertain (menu brackets $7.04-$16.36) and that uncertainty is now a visible toggle instead of a buried constant; no non-linear curve and no projected-points fit survived LOSO or the rewound backtest (#82.2-82.3), so the linear delivered-points scale stands ON EVIDENCE now, not by default.

Next, in order:

0. **The survey (`docs/WORKFLOWS.md` 6b) is still Josh's own task and still first if he is present.**
1. **October, week 1: refresh 2026 final actuals; ~November: ingest Steamer 2027 as `PROJ_2027_*` and rerun `fit_blend.py` plus the flip diff.** The projection is the binding constraint (#69) and the refresh calendar in `docs/MODEL-REVIEW.md` section 5 is the fix; nothing model-side beats waiting for a 2026-aware system.
2. **If a session happens before October:** the punter item (#1/#6: no SB equivalent of the SV exclusion; punting detected by threshold, not intent), or the `evaluate_trade` keep-basis question (UI-REVIEW section 3), both small.

Rules that bite if anyone extends the variant menus: an estimator enters the app only through `scripts/exchange_lab.py` first (flips + rewound backtest + LOSO; the curve family FAILED these gates and must not ship on in-sample fit); keep flags follow the shipped default only (#76); overlays restore-or-record pristine rows in `applyVariant()` (mutating shared arrays without recording is the bug class `verify.mjs` checks 22-23 exist for); bands are recomputed per variant server-side, never translated client-side.

## Open, in priority order

0. **Run the survey (`docs/WORKFLOWS.md` 6b). It is the only item here that can be done today.** `out/keeper_survey.html` collects blind keep/cut calls from Pookie 2.0's owner and from Josh; `scripts/ingest_survey.py` scores them against the model and each other. #69 makes a good owner a benchmark rather than a reviewer, and the role-split price calibration is the test of the model's most falsifiable claim (20 of its 25 biggest bargains are pitchers).
1. ~~Re-score the #70 combination~~ **Done, #79.1**: the MAX_KEEPERS cap changes zero of 289 backtest calls, so the shipped rule scores as `model_replace` in #69: it edges the owners on 2026 dollars (+$78.6 vs +$73.5 vs keep-everything) and trails on accuracy (64.9% vs 71.6%). It wins by sizing, not classification.
2. **Attack the projection, on this calendar (`docs/MODEL-REVIEW.md` section 5).** No 2026-aware 2027 projection exists anywhere before ~Nov 2026. First week of Oct: refresh 2026 final actuals. ~Nov: Steamer 2027 lands on FanGraphs, first 2026-aware system; ingest as `PROJ_2027_*` (a filename switch). Nov-Jan: fresh ZiPS 2027 + DC. ~Feb: ATC (an accuracy-weighted aggregate; aggregates beat every single system in every published test). FanGraphs CSV export is members-only now; budget the membership.
3. **Two consequences of #70 still carry weight; the third is measured and small.** `MAX_KEEPERS` binds for 6 of 10 teams, so the model fills a cap rather than choosing at the margin. `keep_value` is rich at the top. The keeper-count equilibrium is now closed by measurement (#79.35): the loop converges at 121 keeps against the shipped 123, flipping only Brooks Lee and Kyle Stowers, so it is a two-flip worry, not a structural one.
4. **`WAIVER_VALUE`: the toggle shipped (#82.4), the evidence tie stands.** All three anchors are live and frame-consistent now (pool fixed at 140/90, only the bar moves), and they flip zero keep calls, so the stake is pricing/trade display only. Transaction logs WITH DATES remain the only thing that would pick a winner.
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
