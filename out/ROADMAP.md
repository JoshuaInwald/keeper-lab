# Roadmap — what's built, what's next, and what each thing costs

Effort is in focused working sessions, not calendar time. "1 session" ≈ a
couple of hours of concentrated work.

---

## Built and validated

Updated 2026-08-14 — several rows below were stale (this table predates the
app entirely in places). Current numbers only; rerun `scripts/validate.py` /
open the Model tab rather than trusting a copy of this that's more than a
session or two old.

| capability | state |
|---|---|
| Roto denominators from league standings | pooled dispersion, 2024–26 window, per-category standard errors shown on the Model tab |
| $/roto-point from the league's own auctions | $9.17 auction scale / $6.48 redraft scale |
| 2027 + 2028 player projections | reliability-weighted rate blend, DIRECTION-AWARE playing-time trust (#51/#53), saves persistence model |
| Keeper board, surplus, optimal keeper sets | expected-PT + full-time upside, split into health vs. closer-role upside (#53) |
| Multi-year surplus incl. extension option | discounted, contract-aware |
| Trade evaluator, two lenses | 2027 asset + 2026 win-now standings delta |
| Positional adjustment | catcher/shortstop only, toggle, off by default (#52) |
| 2026 leaderboard + hindsight auction prices | `leaderboard_2026.csv` |
| Acquisition-channel decomposition | auction vs keeper vs free agent |
| Auction inflation rate | +31.5% projected for 2027 (check the header — this moves with every rebuild) |
| Final-year extension, 1 vs 2 years | priced as an option; `extension_years` on the board |
| Uncertainty bands | bootstrap on every rostered player's dollar value + denominator standard errors |
| **The app** | single self-contained HTML file (~6 MB), 7 tabs, no server — board, league, trade, standings (live + historical + 2027 keeper-core), free agents, Intuition (manual shading), model internals |

---

## Phase 1 — Trust the numbers (do before any UI). ~1–2 sessions

**1.1 Sensitivity harness (1 session).** Rerun the board under each contested
choice and count how many keep/cut decisions flip: SV punters in/out,
denominator window, exchange-rate window, blend weights, PT floor, discount
rate. Output is one table. Without it the app displays point estimates from a
model with six live forks.

**1.2 Uncertainty bands — done, this item was stale.** `klab/uncertainty.py`'s
bootstrap (±34% per category, n=30 team-seasons; 20 for ERA/WHIP, 17 for SV)
was already fully wired into the app (`app/template.html`'s "likely range"
column, `p_surplus_positive` "Sure?" column, and full ranges on the player
card) — this item just hadn't been marked done. What genuinely wasn't wired
in until 2026-08-13: everything *outside* the app. `board.py`,
`api.snapshot()`, `out/keeper_board_2027.csv`, `scripts/eval_trade.py`, and
`scripts/team_reports.py` all showed point estimates only, with no way to
tell "confident" from "guessing" apart. Fixed for `run_all.py`'s board CSV
and `eval_trade.py`'s per-player table; `team_reports.py` and the new
`klab/auction_estimator.py` still don't show bands. Real finding from
wiring it in: Tarik Skubal's $17.97 multiyear surplus is positive in only
73% of bootstrap draws (range −$7.4 to +$37.7) — a materially less certain
number than the point estimate alone suggested. See `out/FINDINGS.md` #37.

**1.3 Positional replacement — investigate, don't assume — done for C/SS,
2026-08-14.** External review flagged its absence as a first-order gap. The
published evidence disagrees: Razzball concluded position adjustments have
"very close to zero impact," and in FanGraphs' 13-system test the variants
with the largest positional adjustments finished *last*. Tested on this
league's own data rather than assumed either way, once real eligibility
data existed to test it with (`data/fg_catchers_2026.csv`,
`data/fg_shortstops_2026.csv`). Scoped to C/SS only — the two positions
this roster forces a start at every week — not the full defensive
spectrum, which stays blocked on `klab/keeper.py`'s pre-existing
`positional_replacement()` covering only ~52% of the player pool. Shipped
as a header toggle (on/off, composes with the projection-basis selector).
The published skepticism held up on this league's numbers too, in an even
stronger form than "close to zero impact": both catcher and shortstop
replacement level came out *higher* than pooled, meaning the adjustment
mostly lowers C/SS values rather than raising them for scarcity, which
wasn't the expected direction going in. See `out/FINDINGS.md` #52.

---

## Phase 2 — The app. ~~3–4 sessions~~ **done in 1**

Streamlit was the plan. It was the wrong plan: it needs a Python process
running to look at a number, which means the tool is only available at the desk
where the repo lives. The build target instead is **one self-contained HTML
file** — `out/keeper_lab.html`, ~3.7 MB as of 2026-08-13 (grew from ~300 KB
once the basis selector and auction estimator started shipping three payload
copies each, see `out/FINDINGS.md` #42-43), no server, no network, no
dependencies. It opens on a phone at the draft table, and it can be emailed to
a league-mate or dropped in a portfolio without asking anyone to `pip install`.

```bash
PYTHONPATH=.:scripts python3 scripts/build_app.py   # writes out/keeper_lab.html
node app/verify.mjs                                 # diffs the browser against pandas
```

Shipped:

| screen | what it does |
|---|---|
| Keeper board | 275 rostered players, filter by team / role / keeper status, sort any column, `KEEP` `OPT` `EXT×2` `IL` `LOCKED` flags |
| Player card | projection line, roto points by category, both dollar scales, surplus by year, the extension decision in years |
| League | ten teams by keeper surplus, budget left, projected finish, the five headline constants |
| Trade | pick two teams and any number of players; Δ2027 surplus, Δmulti-year surplus, Δ2026 standings points by category, and the effect on the other eight teams |
| Standings | current roto points vs projected final, category by category |
| Free agents | top 400 unrostered, priced at their live draft contract |
| Model | denominators, fitted constants, active settings, and what the engine does that a generic calculator does not |

Plus an inflation-adjusted display toggle everywhere (was Phase 3.1).

**How the browser is kept honest.** One thing is re-implemented in JavaScript:
the rest-of-season standings calculation, so a trade can be re-scored without a
server. Re-implementations drift, so `scripts/build_app.py` writes
`out/app_reference.json` — pandas' answer for one real trade — and
`app/verify.mjs` loads the built page in headless Chromium and diffs all 25
quantities, then walks every tab and fails on any console error. That check
found the `PA_x`/`PA_y` column collision described in FINDINGS §24.1.

### Still open in Phase 2

**2.1 Snapshot store.** `api.write_snapshot()` already persists a dated parquet
copy; nothing yet reads the history back into the app. "How has Ohtani's keeper
value moved since June" needs a fourth-dimension chart, not a database.

**2.2 Projection-basis selector — done, 2026-08-13.** `PROJECTION_BASIS`
switches the whole board between blend / projection-only / 2026-only and 17%
of keeper calls depend on it. Shipped as a header control
(`app/template.html`'s `setBasis()`) backed by three full payloads
(`scripts/build_app.py`'s `_basis_variants()`) instead of a rebuild —
switching is a re-render. Board, free agents, per-team keeper summaries, and
every fitted constant that depends on the board (inflation, replacement
level, $/roto point) all swap together; live 2026 standings don't, correctly,
since they're not a projection. See `out/FINDINGS.md` #42.

**2.5 Rest-of-2026 basis toggle — done, 2026-08-13.** A second, independent
toggle from 2.2 above: which signal projects the REST of 2026 (Standings
tab, Trade tab's win-now delta) — ZiPS's own rest-of-season system
(default), each player's season-to-date pace extended over the games left
in the season, or a 50/50 blend of the two. Never touches a dollar value,
so it's scoped to those two tabs only, not the header. See
`out/FINDINGS.md` #45-46 for the new `klab/trade.py` functions
(`prorated_to_date_lines()`, `ros_lines_for_basis()`) and a real bug caught
in each layer (a starting pitcher's innings could get projected 5-6x too
high; the two toggles could silently fight each other on state).
No "pre-season 2026" option: no file in `data/` has one.

**2.6 Historical standings + 2027 keeper-only standings — done, 2026-08-13.**
Standings tab season picker: final standings for every completed season
2022-2025 (normalised to current franchise names across five renames), plus
a "2027 — keeper sets only" view (each team's current keepers' 2027
production + replacement-level fill for every open roster slot — keeper-core
strength, not a real-auction forecast). See `out/FINDINGS.md` #48-49.

**2.7 The Intuition tab (manual player shading) — done, 2026-08-13.** Shade
any player's talent up/down and/or force a "full health" assumption;
recalculates 2026 standings impact exactly (same client-side engine as the
Trade tab) and shows 2027 dollar impact as a transparently-labeled linear
scaling, not a full model re-run — the 2027 valuation pipeline stays
server-side only, on purpose, to avoid a second implementation that can
drift from the first. Fully sandboxed: never touches any other tab's
numbers. See `out/FINDINGS.md` #50.

**2.8 Direction-aware pitcher playing-time trust + an `upside_ft`
role/health split — done, 2026-08-14.** A pitcher whose real 2026 workload
already exceeds ZiPS's own 2027 opinion for him (Cam Schlittler, Jacob
Misiorowski, Chase Burns) now trusts his own proven workload more than a
pitcher who fell short of ZiPS's number (the #51 case) — a direction-aware
exception to the pitcher playing-time cap, not a blanket increase. Also
split `upside_ft` (the board's "if he's fully healthy" figure) into two
kinds that were previously conflated under one number: "health" (a starter
or hitter's own workload floor) and "role" (a reliever scaled to a full
closer's save total — a bullpen-decision bet, not a health one), tagged
inline on the board and in the drawer. Caught, incidentally, a second live
copy of #52's own `min()`-based no-op bug — this time in `value_2028()`,
which #52's fix never touched, silently making 2028 positional adjustment
a no-op for a full extra day. See `out/FINDINGS.md` #53.

**2.9 Per-category value breakdown, MLB team, denominator error bars —
done, 2026-08-14.** Hovering/clicking a player's Worth '27 now breaks the
dollar figure down by category, reconciled exactly (the naive per-category
split didn't sum to the total — real replacement-level/floor math folded
in as its own line to fix that). Real MLB team shown next to the CBS
fantasy team everywhere a player appears. Model tab's denominator table
shows each category's own standard error (already computed, previously
discarded before reaching the app). "Gain" renamed to "Surplus" throughout
for consistency with the underlying field names.

**2.10 FA tab's blank "likely range" — scoped, not started.** Currently
blank by design (`app/template.html`'s `FA_NOTE`): the uncertainty
bootstrap needs a real contract (cost/years/salary) to band
`surplus_multiyear`, and a free agent's contract is hypothetical. But
`value_lo`/`value_hi` alone don't need a contract and could be extended to
free agents relatively cheaply, reusing each FA's own hypothetical contract
fields from `free_agent_board()` for the parts that DO need one. Not
started — genuinely optional, not an obvious yes.

**2.11 A scrollable/searchable player-data tab — scoped, not started,
2026-08-14.** Would need to exist without an age column: no birthdate/age
data is in any file this project has (checked directly). Buildable today
on what already exists (MLB team, position, salary, contract, projected
stat line) if wanted on its own; more useful once a fresh FanGraphs export
with age/position-eligibility data exists (see the FG data-pull list in
this session's chat log / next `LAB_NOTEBOOK.md` entry).

**2.12 App homepage + 5-question router — done, 2026-08-14.** The "Model"
tab is now "Home," moved first, and is what the app opens on. A team
picker plus five buttons for the questions an owner actually asks ("who
should I keep," "is this trade fair," "what's my team worth," "how strong
is my 2027 keeper core," "which free agents should I grab") jump straight
to the right tab with the right filters already applied — reusing existing
state (`S.team`, `S.only`, `S.sort`, the trade tab's `T.a`) rather than
inventing a parallel set, so a question button and the destination tab's
own controls never disagree about what's currently filtered. The
model-internals content that used to be the whole tab is still there,
unchanged, just below the new panel and clearly labeled as optional. Not
done: mobile nav overflow (7 tabs on a narrow viewport) — explicitly
deprioritized, 2026-08-14, Josh's call.

**2.4 Auto-refresh — build pipeline is cron-safe, data ingestion is not
(checked 2026-08-13, not scheduled on purpose, still manual by choice).**
Two separate questions, worth not conflating:

- **Is the rebuild chain safe to run unattended?** Yes, verified directly:
  `scripts/build_trade_suggestions.py` → `scripts/run_all.py` (which calls
  `build_app.py` internally) ran end to end twice with no interactive
  prompts, no crashes, ~2m20s total. `grep`ed `klab/` and `scripts/` for
  `input()`/`sys.stdin` — none exist anywhere in the pipeline.
- **Is there anything to schedule it to pull?** No — and this is the actual
  gap, not a solved problem waiting for a cron entry. There is no FanGraphs
  scraper or API client anywhere in this codebase; `data/` is a hand-copied
  export from `~/Documents/Fantasy Baseball/` per `CLAUDE.md`'s three-places
  note. "Auto-refresh" in the sense of *the numbers change on their own* is
  not currently possible without writing an ingestion step that doesn't
  exist yet — a materially bigger task than wiring up a scheduler, and out
  of scope for now. Also worth knowing before scheduling anything:
  `build_trade_suggestions.py` is deliberately not called from
  `run_all.py` (its own docstring says why — it's the slow part), so a
  cron entry that only calls `run_all.py` would silently serve
  increasingly stale trade suggestions next to a freshly-rebuilt board.
  Any future scheduler has to call both, in that order.

Real bug found doing this check, unrelated to scheduling itself: rerunning
the chain twice on *identical* data produced different trade suggestions
for 28 of 45 team pairs — a non-determinism bug in `klab/trade_finder.py`'s
tie-breaking, not anything to do with automation. Fixed same day; see
`out/FINDINGS.md` #41. Good thing to have caught before ever running this
unattended, since a human rerunning it by hand would at least notice "why
did this change," while a cron job wouldn't.

Conclusion: safe to schedule the *rebuild* today if a fresher `data/` ever
shows up on disk by some other means; not worth scheduling anything until
there's an actual ingestion step to trigger. Left manual, per Josh's
preference (2026-08-13).

---

## Phase 3 — Modelling depth. ~4–5 sessions

**3.1 Auction inflation, applied — done.** Standard keeper-league
formula: `remaining budget ÷ remaining player worth`. Shown live in the app
header and recalculated on every rebuild (it moves with the model — check
the header, not a number pinned here). Every dollar value can be toggled
"true" vs "inflation-adjusted" via the board/FA/trade controls.

**3.2 Prospect / upside distribution (1 session).** Currently every player is
a point estimate. Breakouts are systematically undervalued. Minimum viable:
use ZiPS percentile bands (the export has P10–P90 columns already) to compute
a distribution of outcomes, then value the option rather than the mean.

**3.3 Waiver-wire value (1 session).** Free agents supply **40% of league roto
production** at $10–20 each. That is the largest single channel and the model
treats it as invisible. Quantifying it properly would sharpen replacement
level, which is the anchor for every dollar figure.

**3.4 Aging curves — will not build, explicit decision, 2026-08-14.** Josh's
call: ZiPS (and whichever projection system feeds an out-year in the
future) already bakes age-appropriate expectations into its own forecast
for that specific player at that specific age, as part of how those systems
are built. A separately-fit aging CURVE on top of that would risk
double-counting age rather than adding information the projection doesn't
already have — so the real fix isn't building a curve, it's making sure a
fresh out-year projection gets pulled before every keeper decision, which
is already this project's stated `data/README.md` refresh cadence, not new
work. This narrows, but doesn't fully close, one specific gap worth naming:
years beyond what ZiPS actually publishes (a 3-year keeper contract's final
year, e.g. 2029 when only 2027/2028 exist) still have no fresh per-player
projection at all -- `surplus_y2029` extrapolates the 2028 figure with a
flat discount rate, which has no age-awareness of its own. Not in scope
either, per the same reasoning (small dollar impact, discounted anyway, and
still second-order compared to getting *this* year's numbers right).

**3.5 Transaction logs → roster reconstruction (2 sessions).** Requires
scraping CBS. Unlocks: historical acquisition-channel analysis back to 2022,
manager skill evaluation (who converts draft dollars into production best),
and true "value added by trade" per manager.

**3.6 Auction-price-estimator UI integration — done, 2026-08-13.** Built
2026-08-13 as a standalone tool (`klab/auction_estimator.py`,
`scripts/estimate_auction_price.py`, `out/FINDINGS.md` #35) — comp-based
next-auction price range, deliberately separate from `redraft_value`. Now a
player-card panel (`app/template.html`'s `showPlayer()`) showing the
comp-adjusted range next to the regression fair value plus the top 8 comps
themselves (transparency — the estimate never looks like a black box), for
every player with a projection, computed fresh for all three projection
bases so it stays consistent with the selector (2.2). The age/debut-year
gap is stated directly in the panel's own caveat text, not just in code
comments. See `out/FINDINGS.md` #43.

**3.7 Young/rookie-player projection modeling (0.5-1 session to scope,
more to build) — parked by explicit decision, 2026-08-13.** Josh's call:
ZiPS is judged good enough at the rookie/debut-year case as-is, so this
isn't worth a session against the other open items right now. Researched
2026-08-13, not implemented: the current
`RELIABILITY` blend weights (`klab/project.py`) were fit exclusively on
players with an existing multi-year MLB track record, then applied
uniformly to first-full-season players too. The research (cited sources in
`out/FINDINGS.md`'s session log) doesn't support a simple "trust rookies
more" fix — the credible direction is routing noisy outcome stats like ERA
through their more-reliable components (K/BB/H) for players without a
qualifying prior season, or refitting a second reliability table
specifically on debut-year transitions. Concrete test case:
Christian Scott, whose model-blended 2027 ERA lands closer to a
conservative ZiPS forecast than to his own strong 78-inning 2026 sample.

**3.9 Team-specific category value (0.5-1 session to scope, more to build) —
identified but not started, 2026-08-14.** `out/RESEARCH.md` §6.2/§8 ranks
this the single highest-value gap left, ahead of everything else on this
list: roto points add up linearly today, so the model is indifferent
between 20 more HR and 20 more K, when the real value of a category unit
depends on where a specific TEAM sits in it (a team third in saves gains a
lot from five more; a team tenth by 40 gains nothing). Fixing it properly
means a team-specific marginal value per category, turning one dollar value
per player into ten (one per team) — a real scope jump from the rest of
this list, and the trade evaluator's win-now lens already works around this
by re-ranking standings rather than adding roto points, so the workaround
exists even though the general fix doesn't.

**3.10 Probability-weighted closer/reliever upside — DEPRIORITIZED,
2026-08-14, kept on the list at low priority (not eliminated).** Josh's
call: doesn't matter much to him. `upside_ft` currently assumes a reliever
already sitting on 5+ saves gets handed the closer job outright at a fixed
25-save floor, zero risk — flagged as the weakest part of the "role"
upside split (#53), and the agreed direction if this ever gets picked back
up is still: report a range (P10 / full-closer / incumbent-only) using the
SAME bootstrap infrastructure already built for `value_lo`/`value_hi`,
rather than a deterministic point estimate or a newly-fit "job security"
probability model. Sits below 3.9 (team-specific category value) and every
other open item on this list now — pick it up only if everything above it
is done and there's still appetite for it specifically.

**3.8 Trade-finder feature — done, 2026-08-13.** `klab/trade_finder.py` +
`scripts/build_trade_suggestions.py` + a "Suggested trades between these
two teams" panel in the app's Trade tab (`out/FINDINGS.md` #40). Three
scenarios per team pair (win-now-for-future, challenge trade, mutual value
swap), 1-for-1 only, precomputed for all 45 pairs since the app has no
server to search live from. **Maintenance note**: `out/trade_suggestions.json`
is a snapshot, not live — rerun `scripts/build_trade_suggestions.py`
(~135s) after roster changes or it'll suggest trades using stale rosters.
Not wired into `scripts/run_all.py`'s hot path on purpose (the search is
meaningfully slower than the rest of the build), so this is a manual step,
easy to forget. Natural next extension: 2-for-1/2-for-2 packages, currently
out of scope to keep the search tractable for a build step.

---

## Phase 4 — Portfolio polish. ~1–2 sessions

Write-up, methodology notebook, a couple of good charts, and a public README.
The intellectual content is already strong — the saves conditionality, the
exchange-rate decay, the reliability table. What's missing is presentation.

**Done:** public repo — [github.com/JoshuaInwald/keeper-lab](https://github.com/JoshuaInwald/keeper-lab).
`data/` excluded (FanGraphs terms + private league exports); `data/README.md`
documents every file needed to reproduce it. `out/` — including
`keeper_lab.html` — is committed deliberately as the readable artifact.
GitHub Pages not yet enabled; the app currently has to be downloaded and
opened locally.

---

## Suggested order from here

Done: sensitivity harness (1.1), inflation display (3.1), waiver-value settings
(3.3, three anchored levels), positional adjustment for C/SS (1.3, tested,
shipped as an on/off toggle, 2026-08-14), the app, uncertainty bands (1.2 —
done in the app for a while, extended to the board CSV and eval_trade.py
2026-08-13), projection-basis selector (2.2, 2026-08-13), auto-refresh
checked and documented (2.4, 2026-08-13 — the rebuild chain is cron-safe,
but there's no ingestion step to schedule yet, so it stays manual),
auction-estimator UI integration (3.6, 2026-08-13), direction-aware
pitcher playing-time trust + the `upside_ft` role/health split (2.8,
2026-08-14), per-category value breakdown + MLB team + denominator error
bars (2.9, 2026-08-14), the app homepage + 5-question router (2.12,
2026-08-14).

**Next up, by priority:** 3.9 (team-specific category value — the single
highest-value gap left per `out/RESEARCH.md` §8, not yet scoped in detail).
3.10 (probability-weighted closer upside) is deprioritized (2026-08-14, not
eliminated) — pick it up only after everything else is done.

**Deprioritized or declined by explicit decision:** 3.4, aging curves
(2026-08-14 — Josh's call: a fresh out-year projection close to the actual
keeper decision already carries age-appropriate expectations, so a
separate curve risks double-counting rather than adding information; see
3.4's own entry for the one narrower gap this doesn't close). 3.7,
young/rookie projection modeling (2026-08-13). Josh's call on 3.7: treat
ZiPS as already capturing the
rookie/debut-year case well enough, rather than spend a session building a
second reliability table for it. Left as a scoped-but-parked item below in
case that judgment changes later.

1. **Prospect / upside distribution (3.2)** — ZiPS percentile bands are already
   in the export; value the option rather than the mean.
2. **Aging curves (3.4)**, then **transaction logs (3.5)** if you want the
   manager-skill analysis.
3. **Young-player/rookie modeling (3.7)** — parked, see above.

Item 1 is mechanical and belongs on a cheap model. Item 2 is modelling
judgment and is worth the expensive one.

---

## Where this sits against what already exists

See `RESEARCH.md`. Short version: the commercial tools (FanGraphs Auction
Calculator, RotoWire, FantasyPros) all compute generic dollar values from
projections and let you tweak league settings. **None of them calibrate to
your league's own realised auction prices, and none model multi-year keeper
surplus against a specific contract structure.** That gap is the reason this
project is worth finishing — and it's the part that makes it a portfolio piece
rather than a reimplementation.

---

## Phase 5 — Threshold-aware valuation (top-2-only payouts). Proposed 2026-08-14, unscoped, nothing built

This league only pays out for 1st and 2nd place. Every number this tool
produces (`roto_points`, `redraft_value`, the $/point exchange rate) treats
a marginal standings point as worth the same amount everywhere in the
distribution -- correct only if the payoff is linear in final rank, which
it isn't when only two spots pay. The real payoff is closer to a step
function: crossing 3rd into 2nd is worth real money, moving from 5th to 4th
is worth nothing, and piling up points once comfortably in 1st is close to
worthless too. That means the RIGHT strategy is team-state-dependent
(minimize variance if safely ahead, seek variance if just below the
cutoff, ignore this year's standings entirely if hopelessly behind), and
nothing in the current pipeline knows which state any given team is in --
every team is priced off the same flat rate. Full reasoning and a concrete
illustration (2nd and 3rd currently separated by half a point) in this
session's chat log.

**5.1 P(finish top 2) simulator — the foundational piece, everything else
depends on it.** Extends the existing bootstrap machinery (already
resamples category dispersion 1000x for player-level value bands) to
simulate full-season standings across all 10 teams simultaneously and
tally how often each team lands top 2, instead of the single point-estimate
"projected finish" the Standings tab currently shows.

**5.2 A team-situation classifier** (contender / bubble / rebuild), derived
from 5.1, refreshed on every rebuild.

**5.3 Team-conditional marginal value**, replacing the single flat $/point
rate for team-specific views. Generalizes RESEARCH.md's already-identified
top open priority (§8 #1, team-specific category value) into team-specific
*standings-threshold* value -- a bigger version of the same underlying gap
(§6.2: roto points add up linearly today with no notion of where a team
actually sits in a category, let alone in the standings overall).

**5.4 Surface player-level variance as a first-class stat.** ZiPS's own
P10-P90 bands exist in the export and have gone unused (RESEARCH.md §6.3,
still open). Pairing that with 5.2/5.3 lets a bubble team filter for "high
variance, borderline talent" and a leader filter for "safest floor" --
the whole point once team situation is known. Directly reframes the
deprioritized closer/reliever upside item (3.10): a bubble team specifically
may value that exact kind of asset far more than the "doesn't matter much"
framing that deprioritized it assumed, since it wasn't conditioned on team
state. Not reopening 3.10 by itself -- just noting the two are connected.

**5.5 Trade evaluator upgrade: report Δ P(top-2) for a proposed trade, not
just Δ points.** The most literal translation of "does this actually help
me win," once 5.1 exists to compute it from.

**5.6 Research note, not a build item: revisit the flat-exchange-rate
finding (chat log, the FanGraphs comparison discussion) through this lens.**
Real hypothesis worth writing up once 5.1 gives real P(top-2) numbers to
check it against: with only 2 of 10 spots paying, the average team in most
seasons isn't a contender, so broad value-accumulation instead of
star-chasing may be this league's rational aggregate bidding behavior for
its own payout structure -- not a market inefficiency to correct.
