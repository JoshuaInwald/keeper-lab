# Session handoff (current state only; history lives in docs/SESSION-LOG.md)

Last updated: 2026-09-07 (compaction pass). Read `CONSTRAINTS.md` first, then "Next session: start here" at the bottom.

## System
- Repo: `~/PycharmProjects/keeper-lab` on the Mac, GitHub `JoshuaInwald/keeper-lab` (public, `main`), mirror at `~/Documents/Fantasy Baseball/keeper-lab/`. See `CLAUDE.md` for the three-surface rule.
- Build: `PYTHONPATH=.:scripts python3 scripts/run_all.py`; tests: `PYTHONPATH=. python3 -m pytest tests/ -q` (64 pass, 2026-09-07); app check: `node app/verify.mjs` (15 pass).
- Data: `data/` current as of 2026-08-15 exports (2026 season ~75% complete at that pull). ZiPS 2027 and 2028 Depth Charts loaded. Refresh cadence in `data/README.md`.
- Committed build numbers: $9.17 per roto point (keeper-adjusted auction scale), $6.56 (redraft scale), replacement 4.81 roto pts, +33% projected 2027 inflation, Spearman 0.851 vs 2026 standings. Every one moves on a rebuild; quote from `out/model_params.json`.

## State of the model
- Headline `redraft_value` is a production scale normalised to top-230 = $2,600. It is NOT a market price and is known to overshoot at the top (Skubal $52 vs a $45 league ceiling) and undershoot young/no-track-record players. `docs/ROADMAP.md` item 1 is the fix, diagnosed 2026-09-07 with numbers; nothing has been built yet.
- The comp-based auction estimator (`klab/auction_estimator.py`) is anchored to comps' real salaries and shown in the player drawer; it is a separate estimate, not blended in.
- Ohtani is two 2027 assets. `F` contracts are unkeepable. Payout is 50/25/15/breakeven.
- Open data questions: Skubal's +$15 salary step and the deGrom/Turang contract clocks (FINDINGS #23.4, #25) remain unresolved.

## Compaction pass, 2026-09-07
- Docs: 13 files / ~7,500 lines in `out/*.md` replaced by `docs/` (METHODS 212, FINDINGS 209, ROADMAP, WORKFLOWS 109, SESSION-LOG 107) plus root README / CLAUDE / CONSTRAINTS / HANDOFF. Original section numbers in FINDINGS preserved. Full text remains in git history (commit 8353172 and earlier). `out/SQL_GLOSSARY.md` dropped (learning aid, not project doc; in history).
- Code: klab 3,955 to 3,128 lines; scripts 2,293 to 1,464 (five one-off analysis scripts deleted: experiments, market_analysis, draft_surplus, zscores, backtest); tests 1,203 to 912 with every assertion kept (68 to 49 test functions in `test_invariants.py`). Dead code removed: `positional_replacement()`, `_find()`/`_UPLOADS` fallback, seven unused config knobs (`RATE_CATS`, `COUNT_CATS`, `KEEPABLE_AT_SALARY`, `EXTENSION_ALREADY_USED_IF_SALARY_ABOVE_DRAFT`, `SB_PRE_REGIME_WEIGHT`, `BLEND_W_ZIPS27`, `POSITION_SLOTS`). Board output byte-identical before and after.
- Outputs: 15 regenerable `out/` files untracked and gitignored by name. `constitution_text.txt` moved to `docs/constitution.txt`. `leaderboard_2026.py` exposes `build_leaderboard()`; `team_reports.py` calls it in-process; `estimate_auction_price.py` and its test build players from `value_players()` instead of the untracked CSV.

## Next session: start here
1. `git status`, `./check_sync.sh`, `ls data/`.
0. Open question for Josh before Step 1b: were keeper limits different in 2022-2025 (files show 2-6 keepers per team) or are those files partial? Answer decides whether historical keeper decisions are usable as revealed-preference data.
2. If starting ROADMAP item 1: begin at Step 0 (rename columns) and Step 1 (feature table). The diagnostic script that produced the numbers in the ROADMAP is not committed; rebuild it as `scripts/price_diagnostics.py` from `out/auction_sample.csv` plus `klab.auction.score_season` for prior-season roto points, and commit it with its output.
3. Do not touch `redraft_value`'s definition until Step 2's held-out test exists; add columns beside it.
