# UI review, bottom up (2026-09-09)

The same process as `docs/MODEL-REVIEW.md`, pointed at the presentation layer:
a full read of `app/template.html` (1,818 lines), `scripts/build_app.py` (560)
and `app/verify.mjs` (537), every user-facing string checked against what the
model now computes, dead code and payload weight hunted, and a guard added for
every reader-found defect class that had none. Three subagent reads produced
the candidate lists; every claim below was re-verified in the main loop against
the code or the built payload before anything was changed.

The standing trap (#78) is the frame: every defect a reader has ever found in
this app was presentation-layer fallout of a model change. This review is the
first systematic sweep of that layer since #70/#80 moved the model under it.

## 1. What was found and fixed (FINDINGS #81; sizes measured)

### 1.1 The League tab went blank on two of three projection bases

`build_payload()` stamped `points_2026` onto the top-level `teams` alias and
onto `positional_variants["on"]`, but for the two subprocess-built bases the
alias is a separate object from `positional_variants["off"]` after the JSON
round-trip, and `applyVariant()` reads only `positional_variants`. Result:
switch the basis selector to "projection only" or "2026 only" and the League
tab's "Points now" column showed em-dashes for all ten teams (verified in the
committed build: `off.points_2026 = null` for both). Nobody had found it
because the default basis was fine and the guard suite never rendered the
League tab off-default. Fixed structurally: the mutation now stamps both
positional settings explicitly and the aliases that hid the bug are gone
(1.3 below). `test_invariants.py` now asserts `points_2026` is non-null for
every basis and setting.

### 1.2 A split two-way player was half a player in the JS trade path

`#80.4` fixed the Python side (`find_player` combines a split player's two
rows into one asset). The JS side had the same defect unfixed: `byId` was
last-row-wins per `fg_id`, so the Trade tab's sums priced Ohtani at his
pitcher row alone ($4.95 of $83.66 `keep_value`), the picker listed him twice
(both entries adding the same half), and clicking his hitter row on the board
opened the pitcher drawer. Fixed with `rowsById` (all rows per id) plus
`assetVal()`, which mirrors `klab.trade._TWO_WAY_SUM_COLS`: value columns sum
across his rows, the single contract counts once. The picker dedupes on
`fg_id` and labels him H/P; `showPlayer()` takes the clicked row's role.
`verify.mjs` now asserts the whole convention on the live payload.

### 1.3 The payload shipped every board twice, and 2.4 MB of it was dead

| component | bytes | disposition |
|---|---|---|
| `basis_variants[b].{cols,board,fa,teams,constants}` | 1,199,931 | byte-identical copies of `positional_variants.off`, never read by the template. Deleted |
| top-level `board`/`fa`/`teams`/`constants`/`auction_estimates`/`ros_values`/`keeper_standings_2027`/`keeper_finish_odds` | ~1,217,000 | read only for the initial render. Deleted; startup now calls `applyVariant()`, the same code path as a basis switch |
| per-variant `cols` (6 copies) | ~6,600 | identical everywhere; ships once at top level |
| `years_controlled`, `surplus_redraft` (per row, 10 board copies), `finish_odds[..].current_points` | ~60,000 | computed, serialised, never read. Deleted |

Built file: **7,669,157 B before, 5,245,232 B after (-31.6%)**, including one
added column (1.5). No visible change; all 21 checks pass. The startup-equals-
basis-switch structure also means no future screen can read a stale alias,
which is what 1.1 was.

### 1.4 The stale-prose sweep (#71.1 class): sixteen strings

The model moved to per-role replacement (#70), keep-basis bands (#80.2) and a
fitted market price (#57); these strings still described the old model. All
fixed, with the load-bearing ones listed:

| where | said | now |
|---|---|---|
| `CONST_HELP.replacement_level`, waiver-value help, budget-check help, League card, model-tab note | one league-wide replacement bar, "the 230th-best projected player", "top 230 budget check" | per-role: the 140th-best hitter and 90th-best pitcher; card and fitted-constants panel show `5.12 H / 3.53 P`; "budget check, fieldable pool" |
| drawer reconciliation row | "the same fixed adjustment for everyone", subtracting the scalar bar (the pitcher bar, so every hitter's row showed -3.53 where the server used -5.12) | the row's own bar, recovered exactly as `roto_points - rp_above_repl`, so the table reconciles per role and under positional adjustment too |
| footer | "Honest error bar is +/-34% per category", "n~677 purchases" attributed to the value scales | the denominator panel's own +/-13-18% standard errors; the 677 belongs to the price model, not the exchange rate (n=404), so the count is gone |
| `CONST_HELP.auction_intercept` | five sentences ending in "docs/FINDINGS.md #27", rendered in a title attribute | three sentences, no reference |
| trade panel | "Precomputed 1-for-1 search, docs/FINDINGS.md #40" visible to the reader | reference removed |
| auction-estimate note | "No age or debut-year data exists anywhere in this league's records" | ages exist (`data/chadwick_register.csv`); the note now states the real gap: comps are matched on production and tenure while the market pays ~8%/year for youth |
| combined-score note | "Slide it toward 1.0 if you are contending" (no such control exists) | "read the score as if the weight were nearer 1.0; a build-time setting, not a control here" |
| `FA_NOTE` | "(klab/uncertainty.py)", "the 275 rostered players" (roster count is 277 and drifts) | no file name, no count |
| `BASIS_HELP`, `SETTING_HELP` | bare "ZiPS"; positional help described "catcher, middle infield" while the live toggle is C/SS | "ZiPS 2027 (a public projection system)"; both positional descriptions now match the toggle |
| `value_lo` tooltip | "the range his value landed in" beside the keep-basis Replace $ column | names its basis: brackets Production $, not Replace $ |
| `redraft_value_2028` tooltip | "The same dollar value, one year further out" (which of the two scales unstated) | names the scale |
| `p_surplus_positive` tooltip vs `conf()` | tooltip said under 80% is a coin flip; the cell colors at 90/60 | tooltip states the actual thresholds |
| contention help, drawer ranges note | "denominator-fit question", "bootstrap resamples of the team-seasons the denominators are fit on" | plain language, per the #74 contract |
| stale comments | market_price "stays hidden/NaN until Step 3" (live since #57), the superseded first phone hide-list, "no file in data/ has age" | corrected or removed |
| typo | "with a everyday job" | fixed |

Verified correct and left alone: the drawer's 80% range under "value, redraft
scale" (the per-year band brackets `redraft_value` by design; only the
multi-year band is keep-basis, `klab/uncertainty.py:93`), the payout prose,
the JS Monte Carlo's negative-stat shock signs (#80.3), the keep-flag
invariance notes (#76), and the two-scales-never-blended language throughout.

### 1.5 The one client-side dollar computation is gone

`replV()`'s full-season branch derived a dollar in the browser from
`auction_intercept` and the $/point rate, the single exception to "every
dollar value is computed server-side once". `keep_value_ft` now ships from
`klab/board.py` beside `redraft_value_ft` and the browser reads it. The JS
finish-sim's `DEFAULT_SHOCK_SCALE` similarly now reads
`D.finish_sim.shock_scale` instead of hard-coding 0.35, making
`build_app.FINISH_SHOCK_SCALE` the single source it claimed to be.

### 1.6 Dead code removed

`--sel`/`tr.sel` CSS (no code ever sets the class), `S.fa` (written, never
read), a duplicated comment line, and the dead payload fields in 1.3.

## 2. Guards added (`verify.mjs`: 17 checks, now 21)

| new check | defect class it guards |
|---|---|
| phone hide-list by field name (renders at 390px, reads computed display per cell) | #73's fourth edit, the only one of the four with no guard; a column insertion silently hides the wrong columns on mobile |
| raw help-string audit (leak regex, jargon denylist, first-sentence length cap over `COL_HELP`/`CONST_HELP`/`SETTING_HELP`/misc) | the old check scanned only `[title]` attributes in the current DOM, which is how "docs/FINDINGS.md #27" reached the model tab (#74 contract) |
| bands bracket their headline (all 277 rows, both band pairs, 5% tail tolerance) | #80.2's class: a basis mix-up between draws and headline violates this near-everywhere. Current build: 0 misses |
| split-player asset convention (values sum, contract once, picker lists him once) | 1.2; skips with a printed note if no rostered two-way player exists |
| strengthened: trade-suggestion check now fails on an empty/missing `trade_suggestions.json` | the stale-build failure `CLAUDE.md` warns about used to pass silently (0 buttons = 0 loads) |

## 3. Diagnostics, recorded not fixed

- **The Trade tab's "delta surplus, 2027" is redraft-basis while the board's
  "Surplus '27" is keep-basis.** This matches the server (`evaluate_trade`
  defaults `value_col="redraft_value"`), so it is a labeling collision, not a
  UI bug; the row now carries a tooltip naming its scale. Whether
  `evaluate_trade` itself should move to `KEEP_BASIS` (as #80.6 moved the
  free-agent surplus) is a model question for a future session.
- **Intuition-tab shading keys on `fg_id`**, so shading a split player shades
  whichever half the map resolves; with two rows sharing an id the health/
  talent multipliers apply to both rows' stats but the dollar line reads one
  row. Blocked on the Intuition v2 decision (HANDOFF item 7) anyway.
- **Auction-estimate comps are ~3.1 MB, 60% of the remaining payload** (8
  comps x 7 fields x ~670 players x 4 copies). They render a visible table, so
  trimming is a product cut, not a cleanup; declined under the one-attempt
  cosmetic rule. If the payload needs to shrink again, this is the lever.
- **Float precision stays at 4dp**: `verify.mjs` diffs at 1e-3 and
  `app_reference.json` carries 6dp; coarser rounding needs that tolerance
  chain re-derived first.

## 4. What this review deliberately did not do

- No new columns, screens or toggles (the valuation-curve toggle set is the
  next session's deliverable and has its own scope notes in HANDOFF).
- No change to any number the model computes. `keep_value_ft` is a new
  serialisation of existing arithmetic, byte-identical to what the browser
  used to derive; it appears as one new column in `keeper_board_2027.csv`,
  and every pre-existing committed number is unchanged.
- No custom hover cards, no nth-child refactor to `:is()`, no comp trimming
  (#76's phone constraint and the one-attempt rule).
