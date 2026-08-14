# Roadmap — what's built, what's next, and what each thing costs

Effort is in focused working sessions, not calendar time. "1 session" ≈ a
couple of hours of concentrated work.

---

## Built and validated

| capability | state |
|---|---|
| Roto denominators from league standings | pooled dispersion, 2024–25 window |
| $/roto-point from the league's own auctions | n=404, 2024–26 |
| 2027 + 2028 player projections | reliability-weighted blend, saves model |
| Keeper board, surplus, optimal keeper sets | expected-PT + full-time upside columns |
| Multi-year surplus incl. extension option | discounted, contract-aware |
| Trade evaluator, two lenses | 2027 asset + 2026 win-now standings delta |
| 2026 leaderboard + hindsight auction prices | `leaderboard_2026.csv` |
| Acquisition-channel decomposition | auction vs keeper vs free agent |
| Auction inflation rate | +52.8% projected for 2027 |
| Final-year extension, 1 vs 2 years | priced as an option; `extension_years` on the board |
| **The app** | single self-contained HTML file, six screens, no server |

---

## Answering the questions you asked, automatically

Everything you asked in this session is already computable from the engine.
The gap is not analysis, it's that each answer currently requires me to run a
script. The work below is about making them self-serve and time-aware.

| your question | computable now? | what's missing for the app |
|---|---|---|
| Keeper value for every roster | yes | a UI and a refresh trigger |
| Who should team X keep | yes | same |
| Value of a dollar in this league | yes | display + trend chart |
| Draft vs keeper vs waiver contribution | yes, for 2026 | history back to 2022 needs transaction logs |
| Trade evaluation | yes | a picker instead of a CLI call |
| Live standings projections | **no** | needs the projection→standings simulator wired to current rosters |
| Tracking any of this over time | **no** | needs a snapshot store; nothing is persisted between runs |

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

**3.1 Auction inflation, applied (0.5 session).** Standard keeper-league
formula: `remaining budget ÷ remaining player worth`. For 2027 this league
projects **+48.7%** inflation. Every dollar value should be displayed both
"true" and "inflation-adjusted", because the latter is what you'll actually
pay. Cheap, and it's the single biggest gap between my numbers and what the
auction will feel like.

**3.2 Prospect / upside distribution (1 session).** Currently every player is
a point estimate. Breakouts are systematically undervalued. Minimum viable:
use ZiPS percentile bands (the export has P10–P90 columns already) to compute
a distribution of outcomes, then value the option rather than the mean.

**3.3 Waiver-wire value (1 session).** Free agents supply **40% of league roto
production** at $10–20 each. That is the largest single channel and the model
treats it as invisible. Quantifying it properly would sharpen replacement
level, which is the anchor for every dollar figure.

**3.4 Aging curves (0.5 session).** The 2028 leg is raw ZiPS. Fit age curves
on the 2022–26 panel.

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
auction-estimator UI integration (3.6, 2026-08-13).

**Deprioritized by explicit decision (2026-08-13):** 3.7, young/rookie
projection modeling. Josh's call: treat ZiPS as already capturing the
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
