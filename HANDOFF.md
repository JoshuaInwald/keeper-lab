# Session handoff (current state only; history lives in docs/SESSION-LOG.md)

Last updated: 2026-09-08 (assessment phase, Phase A complete). Read `CONSTRAINTS.md` first, then "Next session: start here" at the bottom.

## Phase A ran. What it settled

The assessment phase's Phase A is done and its results are in FINDINGS #64, #65, #66 and the banner at the top of `docs/ASSESSMENT-BRIEF.md`. **Phase B did not ship a valuation change, on purpose.** One diagnostic shipped; every dollar figure is unchanged from the committed build.

- **The hitter/pitcher budget split is refuted, not deferred.** It was the brief's strongest lead and its Phase B item 1. This league pays $2.092 per realised roto point for hitters and $2.114 for pitchers, a ratio of 0.99 across 668 purchases with no season outside +/-15%. Hitters take 63.9% of the dollars because they deliver 64.1% of the points. Four independent measures of the league's hitter share (roto points delivered 64.1%, auction spend 63.9%, full-roster salary 62.9%, active-roster proxy 63.3%) agree inside 1.2 points. **Do not build a budget split.** #64.
- **A real defect sits underneath it and is NOT fixed.** `board.value_players()` calibrates on the top 230 by roto points regardless of role. On the 2027 projection that pool is 183 hitters and 47 pitchers, which no ten teams could field, and it allocates 73.7% of the $2,600 to hitters against the league's 63-64%. Completed seasons give 129/101, 125/105, 131/99, 139/91, 130/100, so the defect is latent in the code and activated by the projection, not a property of the roto scale. #65.
- **The obvious repair was measured and rejected.** Slot-constraining the pool with role-specific replacement gives 54.2%, as far below the target as the status quo is above it. Slot-constraining with pooled replacement gives 71.6%. The reason is a second distortion: ZiPS Depth Charts smears innings, so the projection carries 1,151 pitchers of whom 223 clear 100 IP against 118-127 in real seasons, and the 90th-best projected pitcher sits at 3.53 roto points where completed seasons put him at 4.95-7.22. Fixing the pool without fixing the pitcher pool trades a known 10-point error for an unknown one.
- **The decision audit is interpreted** and answers Josh's named question. Owners' keeps look ten times better than their throw-backs when made (ex-ante surplus $13.17 against $1.21) and are worth the same afterwards ($6.75 against $6.39). Keeps go 73.0% right ex ante to 55.4% realised; throw-backs go 61.7% to 73.3%. #66.
- **`WAIVER_VALUE` is still open.** One reconciliation route was tested and refuted: the 106 free agents above 4.381 are 99 hitters and 7 pitchers, so the smeared pitcher pool does not explain the internal-consistency count. #62.

**The single highest-value thing to obtain: two seasons of historical ZiPS or Steamer projection archives.** It is now the binding constraint on three separate open questions: the blend weights (Link 1, never fitted), the pool rule (#65), and the only out-of-sample test of the keep/cut advice itself (#66). Ask FanGraphs or check for a saved export before attempting any of the three.

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
1. **One thing is now blocking, and it blocks three items: no historical projection archive.** `data/` holds only the 2027 and 2028 ZiPS pulls, so the blend weights cannot be fitted (Link 1), the calibration-pool rule cannot be chosen (#65), and the keep/cut advice has no out-of-sample test (#66). Two seasons of ZiPS or Steamer archives would unblock all three. Data current to 2026-09-07; ROADMAP items 1, 2 and 4 remain closed.
1.5. **The calibration pool allocates 73.7% of the budget to hitters against the league's 63-64%** (#65). Confirmed defect, deliberately unfixed: the candidate repair overshoots to 54.2%. `scripts/validate.py` CHECK 5 tracks it. Do not attempt a hitter/pitcher budget split; #64 refutes it on the league's own data.
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
- **Slot-constraining the calibration pool on its own**: measured at a 54.2% hitter share against a 63-64% target, an error as large as the one it fixes and in the other direction. #65.

## Next session: start here

Phase A of the assessment is complete (#64, #65, #66). No valuation changed. The
question is no longer "what is true"; it is "which of three blocked things do we
unblock". All three have the same blocker.

1. `git status`, `./check_sync.sh`, `ls data/`.
2. Read the banner at the top of `docs/ASSESSMENT-BRIEF.md`, then #64, #65, #66.
   The brief's original text is preserved below its banner and its strongest
   lead is refuted, so do not act on the original without the banner.
3. **The one thing worth chasing: two seasons of historical ZiPS or Steamer
   projection archives.** It is the binding constraint on all three of:
   - the blend weights, which have never been fitted and are four judgment calls
     (Link 1 of the brief, METHODS section 3 #9);
   - the pool rule, where a confirmed 10-point allocation error cannot be fixed
     because the candidate repair overshoots and the pitcher pool is smeared
     (#65);
   - the only out-of-sample test of the keep/cut advice, which is the thing the
     project is for and has never been measured (#66, and objection 6 in the
     brief).
   Try FanGraphs' archives, a saved export, or the Wayback Machine on the ZiPS
   leaderboard before concluding it is impossible. This is a data-acquisition
   errand, not a modelling session, and it unblocks more than any model change
   currently on the table.
4. If the archives cannot be had, the honest next-best items, in order:
   - **Test whether deep free-agent projections are optimistic on the HITTER
     side.** #62's tie now rests entirely on 99 unrostered hitters projecting
     above 4.381. That is the untested half of the reconciliation and it is the
     last route to settling `WAIVER_VALUE` without transaction logs.
   - **Link 3, the inverted regression.** R^2 = 0.156 and `keep_value` totals
     $4,778 against a $2,600 cap. Nobody has separated "aggregate keeper
     discount" from "inversion inflation", and the brief calls it the strongest
     methodological objection available. Untouched by Phase A.
   - **Roster-spot opportunity cost** on keeper decisions, which published
     practice says is the main thing surplus value misses, and which #57.5 found
     the hard way.
5. **Do not** build a hitter/pitcher budget split (#64 refutes it), do not
   slot-constrain the calibration pool on its own (#65 measured it overshooting),
   and do not touch `redraft_value`'s definition or promote `keep_2027_market`.
6. `scripts/validate.py` CHECK 5 now prints the role split every run. If the gap
   moves off +10.3%, something upstream changed; find out what before shipping.
