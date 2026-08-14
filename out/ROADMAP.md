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

**1.2 Uncertainty bands (0.5 session).** The honest error bar is ±34%
(bootstrapped) per category from n=30 team-seasons (20 for ERA/WHIP, 17 for
SV). Propagate it to dollar values and show a range, not a point. This is
also the single most credible thing to show an interviewer.

**1.3 Positional replacement — investigate, don't assume (0.5 session).**
External review flagged its absence as a first-order gap. The published
evidence disagrees: Razzball concluded position adjustments have "very close
to zero impact," and in FanGraphs' 13-system test the variants with the
largest positional adjustments finished *last*. Worth testing on this league's
own data before building. Cheap to test, and the answer is interesting either
way.

---

## Phase 2 — The app. ~~3–4 sessions~~ **done in 1**

Streamlit was the plan. It was the wrong plan: it needs a Python process
running to look at a number, which means the tool is only available at the desk
where the repo lives. The build target instead is **one self-contained HTML
file** — `out/keeper_lab.html`, ~300 KB, no server, no network, no
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

**2.2 Projection-basis selector.** `PROJECTION_BASIS` switches the whole board
between blend / projection-only / 2026-only and 17% of keeper calls depend on
it. Making it a control rather than a rebuild means shipping three payloads in
one file — cheap, and it turns the model's biggest fork into something you can
see rather than something you have to trust.

**2.4 Auto-refresh (0.5 session).** Scheduled task pulls fresh FanGraphs ROS
projections, rebuilds, writes a snapshot. Then the tool is live rather than a
thing you rerun by hand.

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

**3.6 Auction-price-estimator UI integration (0.5-1 session).** Built
2026-08-13 as a standalone tool (`klab/auction_estimator.py`,
`scripts/estimate_auction_price.py`, `out/FINDINGS.md` #35) — comp-based
next-auction price range, deliberately separate from `redraft_value`.
Currently CLI-only. Adding it to the app means: a player-card panel
showing the comp-adjusted range next to the regression fair value, and the
comp list itself (transparency — the estimate should never look like a
black box). Real blind spot to fix or document prominently in the UI: no
age/debut-year data anywhere in `data/`, so it can't do age-based comps.

**3.7 Young/rookie-player projection modeling (0.5-1 session to scope,
more to build).** Researched 2026-08-13, not implemented: the current
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
(3.3, three anchored levels), positional-adjustment investigation (1.3, tested
and left off), the app.

1. **Uncertainty bands (1.2)** — the ±34% error bar is in the footer as prose;
   it should be a range on every dollar figure. Half a session, and it is the
   single most credible thing to show an interviewer.
2. **Projection-basis selector (2.2)** — ship three payloads, let the user
   watch 17% of the keep/cut calls move. Half a session.
3. **Prospect / upside distribution (3.2)** — ZiPS percentile bands are already
   in the export; value the option rather than the mean.
4. **Auto-refresh (2.4)** — makes the tool live.
5. **Aging curves (3.4)**, then **transaction logs (3.5)** if you want the
   manager-skill analysis.

Items 1 and 2 are mechanical and belong on a cheap model. Items 3 and 5 are
modelling judgment and are worth the expensive one.

---

## Where this sits against what already exists

See `RESEARCH.md`. Short version: the commercial tools (FanGraphs Auction
Calculator, RotoWire, FantasyPros) all compute generic dollar values from
projections and let you tweak league settings. **None of them calibrate to
your league's own realised auction prices, and none model multi-year keeper
surplus against a specific contract structure.** That gap is the reason this
project is worth finishing — and it's the part that makes it a portfolio piece
rather than a reimplementation.
