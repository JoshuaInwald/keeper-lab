# Session handoff (current state only; history lives in docs/SESSION-LOG.md)

Last updated: 2026-09-08 (assessment phase, Phase B item 1 complete). Read `CONSTRAINTS.md` first, then "Next session: start here" at the bottom.

## What this project is for

**One objective: make the best possible keeper and auction decisions in the 2027 draft.** Everything in this repo is instrumental to that. The two decisions that carry real money are, in order:

1. **Keep or throw back**, for each of the ~27 contracts on the roster, at the 2027 deadline. This is decided before the auction and constrains everything after it.
2. **What to pay**, live in the 2027 auction, for the players the keeper round leaves on the table.

Three consequences for how work gets prioritised, and they should decide what the next session does.

- **A number only matters if it flips a decision.** The standing rule (CLAUDE.md) that a valuation change reports keep/cut FLIPS rather than correlations is the operational form of this. A 10-point reallocation of the budget between roles is worth chasing exactly as far as it moves keeps, cuts and bids, and no further.
- **The project's central claim is still untested.** `docs/FINDINGS.md` #66 scored the OWNERS and could not score the MODEL, because the board is a 2027 object. The out-of-sample keep/cut backtest (item 1 of "Next session") is the only work that tests whether this engine beats the room. It is the highest-value item open and should not keep being deferred behind cheaper diagnostics.
- **Precision beyond the decision is waste.** The auction is a live, noisy, ten-human event. Getting `usd_per_rp` to a third decimal changes nothing; knowing which twelve players are mispriced by more than $8 changes the draft.

Two dates bound the work: the 2027 keeper deadline (decision 1) and the 2027 auction (decision 2). Marcel 2027 will not exist before either (Baseball-Reference publishes after a season ends), so **the 2027 board stays ZiPS** and the Marcel path is a backtesting instrument only.

## Phase A ran. What it settled

The assessment phase's Phase A is done and its results are in FINDINGS #64, #65, #66 and the banner at the top of `docs/ASSESSMENT-BRIEF.md`. **Phase B did not ship a valuation change, on purpose.** One diagnostic shipped; every dollar figure is unchanged from the committed build.

**Phase B item 1 has since run (#68) and it changed what #65 means.** Still no valuation change and no committed output moved; see "Open, in priority order" item 1.5 and "Next session: start here".

- **The hitter/pitcher budget split is refuted, not deferred.** It was the brief's strongest lead and its Phase B item 1. This league pays $2.092 per realised roto point for hitters and $2.114 for pitchers, a ratio of 0.99 across 668 purchases with no season outside +/-15%. Hitters take 63.9% of the dollars because they deliver 64.1% of the points. Four independent measures of the league's hitter share (roto points delivered 64.1%, auction spend 63.9%, full-roster salary 62.9%, active-roster proxy 63.3%) agree inside 1.2 points. **Do not build a budget split.** #64.
- **A real defect sits underneath it and is NOT fixed.** `board.value_players()` calibrates on the top 230 by roto points regardless of role. On the 2027 projection that pool is 183 hitters and 47 pitchers, which no ten teams could field, and it allocates 73.7% of the $2,600 to hitters against the league's 63-64%. Completed seasons give 129/101, 125/105, 131/99, 139/91, 130/100, so the defect is latent in the code and activated by the projection, not a property of the roto scale. #65.
- **The obvious repair was measured and rejected.** Slot-constraining the pool with role-specific replacement gives 54.2%, as far below the target as the status quo is above it. Slot-constraining with pooled replacement gives 71.6%. The reason is a second distortion: ZiPS Depth Charts smears innings, so the projection carries 1,151 pitchers of whom 223 clear 100 IP against 118-127 in real seasons, and the 90th-best projected pitcher sits at 3.53 roto points where completed seasons put him at 4.95-7.22. Fixing the pool without fixing the pitcher pool trades a known 10-point error for an unknown one. **#68 withdraws this bullet's reasoning**: the smearing mechanism is refuted and 54.2% is what the same rule produces on realised seasons. The 71.6% and 54.2% measurements stand. See item 1.5.
- **The decision audit is interpreted** and answers Josh's named question. Owners' keeps look ten times better than their throw-backs when made (ex-ante surplus $13.17 against $1.21) and are worth the same afterwards ($6.75 against $6.39). Keeps go 73.0% right ex ante to 55.4% realised; throw-backs go 61.7% to 73.3%. #66.
- **`WAIVER_VALUE` is still open.** One reconciliation route was tested and refuted: the 106 free agents above 4.381 are 99 hitters and 7 pitchers, so the smeared pitcher pool does not explain the internal-consistency count. #62.

**That blocker is now cleared.** `data/` holds Marcel projections for 2024, 2025 and 2026, all three with actuals (#67). Historical ZiPS was never found; Marcel is Baseball-Reference's naive baseline rather than a ZiPS substitute, but it is a genuine ex-ante line, which is the only property a backtest needs. All three questions above are unblocked: see "Next session: start here".

## System
- Repo: `~/PycharmProjects/keeper-lab` on the Mac, GitHub `JoshuaInwald/keeper-lab` (public, `main`), mirror at `~/Documents/Fantasy Baseball/keeper-lab/`. See `CLAUDE.md` for the three-surface rule.
- Build: `PYTHONPATH=.:scripts python3 scripts/run_all.py`; tests: `PYTHONPATH=. python3 -m pytest tests/ -q` (64 pass, 2026-09-07); app check: `node app/verify.mjs` (15 pass).
- Data: `data/` current as of 2026-08-15 exports (2026 season ~75% complete at that pull). ZiPS 2027 and 2028 Depth Charts loaded. Refresh cadence in `data/README.md`.
- Committed build numbers: $9.17 per roto point (keeper-adjusted auction scale), $6.56 (redraft scale), replacement 4.81 roto pts, +33% projected 2027 inflation, Spearman 0.851 vs 2026 standings. Every one moves on a rebuild; quote from `out/model_params.json`.

## State of the model
- `docs/ROADMAP.md` item 1 is complete (FINDINGS #56, #57). Five dollar figures now exist and `out/valuation_comparison.csv` puts them side by side.
- `production_value` is an exact alias of `redraft_value` (worth to a roster). `market_price` is live: fitted on 677 revealed purchases, calibrated so the 126 lots the 2027 auction sells sum to $1,765. Held-out MAE 5.76 vs 6.84 (prior salary) and 7.20 (comps); P20-P80 coverage 55.4% against a nominal 60%.
- **`keep_2027` is still the production basis and has not moved.** Step 4's market-arbitrage rewire (`surplus_market`, `keep_2027_market`) keeps 104 against 70, of which 30 project below replacement, and cuts Skubal. It ships as a second lens. Do not promote it without fixing what it measures (FINDINGS #57.5).
- The two league-anchored measures agree where the model does not: Skubal `market_price` $34.00, `revealed_price` $34.31, against `production_value` $51.91 and `keep_value` $78.81. The 2026-08-15 reviewer was right about the top end.
- Age now exists in the project: `data/chadwick_register.csv`, rebuilt by `scripts/fetch_chadwick.py`. The market discounts 8.0% per year of age holding production constant. This does not reopen the aging-curve decision for *production*, which CONSTRAINTS.md still declines.
- The comp-based auction estimator (`klab/auction_estimator.py`) is anchored to comps' real salaries and shown in the player drawer; it is a separate estimate, not blended in.
- Ohtani is two 2027 assets. `F` contracts are unkeepable. Payout is 50/25/15/breakeven.
- Open data questions: Skubal's +$15 salary step and the deGrom/Turang contract clocks (FINDINGS #23.4, #25) remain unresolved.

## Compaction pass, 2026-09-07
- Docs: 13 files / ~7,500 lines in `out/*.md` replaced by `docs/` (METHODS 212, FINDINGS 209, ROADMAP, WORKFLOWS 109, SESSION-LOG 107) plus root README / CLAUDE / CONSTRAINTS / HANDOFF. Original section numbers in FINDINGS preserved. Full text remains in git history (commit 8353172 and earlier). `out/SQL_GLOSSARY.md` dropped (learning aid, not project doc; in history).
- Code: klab 3,955 to 3,128 lines; scripts 2,293 to 1,464 (five one-off analysis scripts deleted: experiments, market_analysis, draft_surplus, zscores, backtest); tests 1,203 to 912 with every assertion kept (68 to 49 test functions in `test_invariants.py`). Dead code removed: `positional_replacement()`, `_find()`/`_UPLOADS` fallback, seven unused config knobs (`RATE_CATS`, `COUNT_CATS`, `KEEPABLE_AT_SALARY`, `EXTENSION_ALREADY_USED_IF_SALARY_ABOVE_DRAFT`, `SB_PRE_REGIME_WEIGHT`, `BLEND_W_ZIPS27`, `POSITION_SLOTS`). Board output byte-identical before and after.
- Outputs: 15 regenerable `out/` files untracked and gitignored by name. `constitution_text.txt` moved to `docs/constitution.txt`. `leaderboard_2026.py` exposes `build_leaderboard()`; `team_reports.py` calls it in-process; `estimate_auction_price.py` and its test build players from `value_players()` instead of the untracked CSV.

## Item 1 scripts (none are in `run_all.py`; they are diagnostics, run on demand)
- `scripts/fetch_chadwick.py` writes `data/chadwick_register.csv` (network; ~1 min).
- `scripts/price_features.py` writes `out/price_features.csv` (677 purchases, ex-ante features).
- `scripts/keeper_revealed.py` writes `out/keeper_decisions.csv` (133 clean 2026 decisions plus 202 reconstructed).
- `scripts/price_model.py` writes `out/price_model_holdout.csv` and prints the acceptance battery, including the rejected alternatives (Step 5 upside, monotone GBM).
- `scripts/compare_valuations.py` writes `out/valuation_comparison.csv`: all five systems plus both keeper calls, per rostered player.
- `scripts/validate_marcel.py` re-derives ten published identities on the Marcel archive and reports `fg_id` coverage and `rel` distribution. Run it before trusting the archive.
- `scripts/marcel_pool_test.py` answers #65 with the Marcel archive: pool composition, the three candidate pool rules, dispersion by role and category, and a controls block asserting seven published numbers. Needs `PYTHONPATH=.:scripts` (it imports `knob` from `scripts/sensitivity.py`).
- `scripts/fetch_marcel.js` rebuilds the archive from a browser session (Baseball-Reference 403s automated fetches). `data/` is gitignored, so a fresh clone needs this.
Run order is fetch_chadwick -> price_features -> {keeper_revealed, price_model, compare_valuations}.
`klab/price.py` is the production model `board.py` calls; the scripts are research harnesses on top of it. scikit-learn is an optional dependency (the GBM comparison skips without it).

## Settled this session
- The 2022-2025 keeper files are **not** keeper submissions: `keepers_2025.csv` shares zero players with the 2024 auction class. Nothing needs asking the commissioner; labels are reconstructed from the auction and roster files instead (FINDINGS #56.4). `keepers_2026.csv` is sound.
- The ROADMAP's "25% of purchases have no prior MLB line" is 137 censored 2022 rows plus 30 real rookies. The observable rookie rate is 5.6% (FINDINGS #56.3).

## Open, in priority order
1. **Nothing is blocking.** The projection-archive blocker was cleared by the Marcel import (#67): 2024, 2025 and 2026 ex-ante projections are in `data/`, verified, and joined to `fg_id` at 100%. The blend weights, the pool rule and the out-of-sample keep/cut test are all now runnable. Data current to 2026-09-07; ROADMAP items 1, 2 and 4 remain closed.
1.5. **The calibration pool defect is now diagnosed and ready to fix** (#65 measured it, #68 explains it). Still unfixed, deliberately, because fixing it is a valuation change and owes a keep/cut flip diff. What #68 settled:
   - The 183/47 pool is **general to projections**, not a ZiPS artefact. Marcel gives 184/46, 155/75, 160/70 on 2024-2026. The repair belongs in `board.value_players()`, not in `klab/project.py`.
   - #65's innings-smearing mechanism is **refuted**. The real mechanism is rate-category compression: sd(projected)/sd(actual) is 0.43-0.60 for ERA and WHIP and 0.50-0.58 for SV, against 0.67-0.84 for W and K. Pitchers carry three of the four most-compressed categories.
   - **#65's rejection of its own repair does not hold.** Slot-constraint with role-specific replacement gives 54.21% on the 2027 projection and 52.0-55.1% on realised seasons: a match, not an overshoot. No pool rule reaches 63-64% under perfect foresight (range 46-55%), so that was never the benchmark for this quantity.
   - The mis-split enters at the **dollar conversion**, not the projection: on the rostered 276 the projection gives hitters 65.20% of roto points against #64's 64.11% delivered, and `redraft_value` moves it to 71.78%.
   `scripts/validate.py` CHECK 5 still prints 73.7%. Do not attempt a hitter/pitcher budget split; #64 refutes it on the league's own data.
2. **`WAIVER_VALUE` is a live one-line question, deliberately left alone.** Observed waiver churn says replacement should be ~4.4 (the unused `"medium"`, 4.381) and would put the top of the board at $45.20, the league ceiling. The internal-consistency test says the opposite: at 4.381, 106 unrostered players beat replacement. `docs/FINDINGS.md` #62 has both sides. Transaction logs WITH DATES would settle it.
3. **Step 4 still needs the right object.** `market_price - keeper_cost` is transaction arbitrage; `production_value - keeper_cost` ignores that the money has an alternative use. Production priced at the market's own marginal rate fixes the sign errors but overshoots the top worse than `keep_value`. Not a fifth dollar scale; see #60's contend-or-punt flag instead.
4. **`data/positions_2026.csv` will go stale.** It is a roster-time snapshot and rosters churn (38 adds in 3.5 weeks). Rebuild when comp pools start looking wrong; `data/README.md` says how.
5. **Intuition tab v2 is blocked on Josh, not on work.** Sandboxed overrides or overrides that propagate through the 2027 pipeline. The propagating version is materially larger. Nothing else needs a decision.

## What is deliberately NOT built, with the evidence
- **Per-team category multipliers** (ROADMAP item 2 as written): 0.29x-13.28x within a season, persistence -0.07 across seasons. Implementation kept in `klab/teamvalue.py` so nobody rebuilds it. #60.
- **An upside/spread price feature** (item 1 Step 5): both terms insignificant, loses on LOSO. #57.1.
- **Removing the role cap**: three mechanisms tried, all trade top-end accuracy for safety. #62.5.
- **An aging curve on the projection**: the engine already applies +0.621 roto points to under-25s against an empirical +0.778. CONSTRAINTS.md's decision is vindicated, not merely inherited. #59.
- **`keep_2027_market` as the headline call**: keeps 104 including 30 below replacement, and cuts Skubal. #57.5.
- **A hitter/pitcher budget split**: the league pays the same per realised roto point for both roles (2.092 against 2.114, ratio 0.99). Refuted on the league's own data, not deferred. #64.
- **Slot-constraining the calibration pool on its own**: #65 measured 54.2% against a 63-64% target and rejected it. **#68 withdraws that reason**: 63-64% is the league's spend share over a different population, and 54.2% is what the same rule produces on realised seasons. The rule is now a live candidate rather than a rejected one, and it is the next session's work. It is listed here because the old entry is cited elsewhere.

## Next session: start here

Phase B item 1 is done (#68). This is a fresh-context session: read `CONSTRAINTS.md`, then "What this project is for" above, then #64, #65, #66, #67, #68, then this.

**Do not re-run Phase A or item 1.** #64 (one dollar scale), #65 (pool not fieldable), #66 (owners scored) and #68 (pathology is general; benchmark was wrong) are measured and recorded. `scripts/marcel_pool_test.py` reproduces all of #65's and #68's numbers on demand and is the harness to extend, not to rebuild.

### What is already built and verified
- `klab/marcel.py` reads the archive. Never `read_csv` these files directly; three traps are encoded there (#67).
- `scripts/validate_marcel.py` re-derives ten published identities. All hold, zero violations, `fg_id` join 100% on all six files. Rerun it first as a smoke test.
- `scripts/marcel_pool_test.py` scores any of four arms (realised, Marcel, ZiPS 2027, ZiPS with the blend zeroed) on a shared per-season roto scale and prints pool composition, the three candidate pool rules, dispersion by role and by category, and a controls block that fails loudly if a published number stops reproducing.
- `scripts/sensitivity.py` exports `knob()`, which overrides config constants and clears every cache on the way in and out. Use it for any "what if this constant were different" arm.

### Three standing cautions
1. **Marcel is not ZiPS.** Weights or levels fitted against it describe the Marcel blend. Report them as a shape. #68's benchmark is the exception: it comes from realised seasons, not from Marcel.
2. **Carry `rel`.** A quarter of pitcher rows sit below 0.30 reliability, which is mostly league mean (#67). A backtest scoring those as forecasts is scoring the league mean. Weight or exclude, and state the count.
3. **2026 actuals are a partial season** (~75% at the 2026-09-07 pull). 2024 and 2025 are complete. Prefer them; if 2026 is used, prorate and say so.

### The work, in the order that pays

**1. The out-of-sample keep/cut test. This is now the top item and it should not slip again.**
It is the only work that tests whether the model beats the room, which is the thing the project exists to do (see "What this project is for"). #66 scored the owners on 336 decisions and could not score the model because the board is a 2027 object. With Marcel it can be rewound: build a board for 2024 and for 2025 from data available before those seasons, generate the model's keep/cut calls, and compare against what owners actually did and what then happened. `out/decision_audit.csv` holds the owner side already.
- Scope it its own session; it is the largest item open.
- The honest comparison is model-against-owner on the SAME decisions, ex ante and realised kept separate, exactly as #66 reports them.
- State up front what the Marcel board is not: it is a naive-projection board, so it sets a FLOOR on the model's edge, not an estimate of the ZiPS board's edge.

**2. Fix the calibration pool (#65, #68). Small, well understood, and now unblocked.**
The diagnosis is complete and the candidate is identified: slot-constrain the pool to the top 140 hitters and top 90 pitchers with role-specific replacement. #68 shows that rule reproduces perfect foresight (52.0-55.1% on realised seasons, 54.21% on the 2027 projection) where the status quo misses by 20 points.
- **This is a valuation change, so CLAUDE.md's protocol is mandatory**: record the current board to CSV first, change, diff, and report the KEEP/CUT FLIPS, not just dollar movement or a correlation. Expect pitcher values to rise materially; check what it does to Skubal and to the closers before shipping.
- Check `out/valuation_comparison.csv` and the `market_price` side afterwards. `market_price` is fitted on revealed purchases and does not move, so the production-minus-market gap shifts for every pitcher, and that gap drives the app's buy/sell signal.
- Update `scripts/validate.py` CHECK 5's expected share when it ships, and say in the commit message that committed outputs moved.
- If the flips look wrong, do not ship. #57.5 and #62.5 are the precedents for a measured improvement that still should not be promoted.

**3. Fit the blend weights (Link 1, never fitted).**
`BLEND_W_2026 = 0.50` and the three `PT_BLEND_CAP_*` constants are judgment calls METHODS section 3 #9 admits are unfitted. Blend season T-1 actuals with Marcel-for-T, score against actual T, sweep the weights, leave-one-season-out across 2024/2025/2026. Caveat to state up front: Marcel already internally weights three prior seasons, so blending prior actuals into it double-counts them more than blending into ZiPS would. The SHAPE of the optimum transfers (is the cap binding? is 0.50 far off?); the level does not. `knob()` in `scripts/sensitivity.py` is the sweep mechanism.

**4. The projection-source toggle.**
Josh's ask: pick ZiPS or Marcel as the anchor for backward-facing calculations, so a past decision can be scored against in-season performance and against what each system said at the time. Build last, after 1-3 establish that the Marcel path produces trustworthy numbers. The asymmetry that constrains the design: **Marcel 2027 does not exist yet**, so the toggle is backward-facing only and the 2027 board stays ZiPS. Do not add a knob implying otherwise. `PROJECTION_BASIS` in `config.py` is the existing precedent.

### Still true regardless
Do not build a hitter/pitcher budget split (#64 refutes it on the league's own data). Do not touch `redraft_value`'s definition or promote `keep_2027_market` (#57.5). `scripts/validate.py` CHECK 5 prints the role split every run; until item 2 ships it must read 73.7%, and if it moves on its own, find out what changed before shipping anything.
