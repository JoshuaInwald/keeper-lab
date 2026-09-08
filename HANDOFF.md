# Session handoff (current state only; history lives in docs/SESSION-LOG.md)

Last updated: 2026-09-08 (ROADMAP item 1 complete, Steps 0-5). Read `CONSTRAINTS.md` first, then "Next session: start here" at the bottom.

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
Run order is fetch_chadwick -> price_features -> {keeper_revealed, price_model, compare_valuations}.
`klab/price.py` is the production model `board.py` calls; the scripts are research harnesses on top of it. scikit-learn is an optional dependency (the GBM comparison skips without it).

## Settled this session
- The 2022-2025 keeper files are **not** keeper submissions: `keepers_2025.csv` shares zero players with the 2024 auction class. Nothing needs asking the commissioner; labels are reconstructed from the auction and roster files instead (FINDINGS #56.4). `keepers_2026.csv` is sound.
- The ROADMAP's "25% of purchases have no prior MLB line" is 137 censored 2022 rows plus 30 real rookies. The observable rookie rate is 5.6% (FINDINGS #56.3).

## Open, in priority order
1. **Nothing blocking.** `market_price` ships as a board column ("Market $") next to Production $, with the P20-P80 range and the buy/sell gap on hover, plus an auction-price block in the player drawer. Adding it exposed a stale `nth-child` list in the phone CSS that had been hiding Production $, the one number its own comment says the phone keeps; fixed in the same pass.
2. **The role cap is still a patch.** Uncapped, the model predicts $55 for a hitter against a $45 ceiling; 3 players sit at the cap. Both designed-in fixes lost on LOSO (concave transforms, monotone GBM), so this needs a different idea, not another sweep.
3. **Lower-tail band coverage does not transfer.** Conformal calibration fixed the upper end exactly (19.6% against a 20% target) and left the lower at 25%. 55.4% overall against a nominal 60%.
4. **Step 4 needs the right object.** `market_price - keeper_cost` is transaction arbitrage; `production_value - keeper_cost` ignores that the money has an alternative use. The construction that fixes both is production priced at the market's own marginal rate, but at $12.18 per roto point it overshoots the top worse than `keep_value` does. This is ROADMAP item 2 territory (team-specific category value), not a fifth dollar scale.

## Next session: start here
1. `git status`, `./check_sync.sh`, `ls data/`.
2. Item 1 is done. The ranked list above is what it left open; ROADMAP item 2 (team-specific category value) is the next unbuilt priority.
3. Do not touch `redraft_value`'s definition and do not promote `keep_2027_market` to the headline call.
