# Keeper Lab — what it is, how it fits together, and how you'd ship it

Written for someone who is strong on statistics and new to software plumbing.
Jargon gets defined the first time it appears.

---

# Part 1 — The modelling, in order

The engine answers one question — *what is a player worth, in dollars, in this
league* — and it does it in six steps. Each step's output is the next step's
input, and each is independently checkable.

## 1.1 The unit problem

Rotisserie scoring is ordinal. You get 10 points for finishing first in home
runs and 1 for finishing last. So "how many home runs is a player worth" is
meaningless until you know **how many home runs move you up one place in the
standings.** That quantity is the *denominator*, and it is different for every
category and every season.

The naive estimate is the spread of team totals in one season across ten teams.
That is a standard deviation from n=10 — hopelessly noisy.

**What we do instead — pooled relative dispersion.** Divide every team's
category total by that season's league mean, which puts 2024 and 2025 on the
same scale despite different offensive environments. Pool the normalised
values. Now dispersion is estimated off 20 team-seasons instead of 10. Multiply
back by the target season's expected level to get units.

Then convert dispersion to a standings-point denominator using `c_n`, the
expected range of a normal sample of size n (3.078 for n=10). One standings
point ≈ range ÷ (n−1).

**The saves subtlety.** Two teams punt saves entirely — they carry no closers.
Including them inflates the spread, because you are measuring the distance
between competitors *and* abstainers. Teams below 15 saves are dropped, which
makes it an 8-team field, so the constant changes from 3.078 to 2.847. That is
an **+18.9% correction to the SV denominator**, and it was a real bug for a
while.

Current denominators (units per standings point): R 39.4 · HR 15.4 · RBI 38.7 ·
SB 20.4 · AVG .0023 · W 3.79 · SV 6.57 · K 59.1 · ERA .0431 · WHIP .0108.

Read one: **one extra home run is worth 1/15.4 = 0.065 standings points.**

## 1.2 Rate stats need a marginal, not an average

A .300 hitter does not add .300 to your team average. He *replaces* someone.
The marginal contribution is computed against a full team's at-bats: what does
team AVG become with 13 average hitters plus him, versus 14 average hitters?
Same logic for ERA and WHIP against 8 vs 9 pitcher-innings. This is why AVG and
ERA contributions are small numbers and why a part-time .320 hitter is worth
much less than his slash line suggests.

## 1.3 Dollars: the part that is different from every commercial tool

FanGraphs, RotoWire, FantasyPros all do the same thing: take projections,
assume the league budget divides across a fixed pool, hand you dollar values.
That is a **budget-allocation** model. It tells you what a player *should* cost
in an idealised auction.

This engine does something else. It regresses **realised roto production on the
price actually paid, in this league**, across 677 purchases and five auctions:

```
roto_points = 3.51 + 0.132 × $     →     $7.56 per roto point
```

Busts, injuries, guys who never played — all stay in the sample at the price
paid. So the coefficient is what a dollar *genuinely returned*, not what it
would return if everyone stayed healthy.

Two things fall out for free:

- **The intercept is a replacement-level estimate.** A $0 player returned 3.51
  roto points. Computed a completely different way — the 230th-best projection,
  one per active roster slot — replacement is 4.14. Those two numbers were
  never fitted to agree. Their agreement is the single strongest validation in
  the project.
- **Attenuation bias is handled by direction.** Price is measured with error
  (it embeds the buyer's beliefs). Regressing production on price biases the
  slope toward zero; regressing price on production biases it the other way.
  We only ever run production-on-price and treat the slope as a lower bound on
  what a dollar buys. Inverting a regression you did not fit is a common and
  silent error.

## 1.4 Two dollar scales, and why you need both

- **Auction scale ($10.08/pt).** Opportunity cost. What the league's own
  bidding says a roto point costs. Use it to judge whether a *price* was good.
- **Redraft scale ($6.66/pt).** Budget normalisation: the top 230 players'
  values are forced to sum to exactly $2,600 (10 teams × $260). Use it to
  compare *players*, because it is the only scale under which the values add up
  to the money that actually exists.

The board reports both. `audit.py` checks the $2,600 identity every run — it
caught a build where the total came out $3,854 because the calibration pool and
the valuation pool had drifted apart.

## 1.5 Projections

Three sources, blended:

1. 2026 actuals to date
2. ZiPS rest-of-season 2026
3. ZiPS pre-season 2027

Blended 50/50 between (1+2) and (3), **per statistic, weighted by that
statistic's measured year-over-year reliability**. Reliability is fitted from
the league's own panel and it varies enormously:

| stat | reliability | reading |
|---|---|---|
| SB | 0.739 | speed persists; trust this year's number |
| K | 0.701 | strikeout ability is a skill |
| HR | 0.607 | mostly skill |
| AVG | 0.436 | half noise |
| R | 0.425 | depends on teammates |
| RBI | 0.380 | mostly context |
| WHIP | 0.237 | |
| ER | 0.176 | |
| **W** | **0.151** | **pitcher wins are almost pure noise** |

Pitcher wins at 0.151 means this year's win total tells you almost nothing
about next year's. The blend correctly shrinks W hard toward the projection.

**Saves get their own model** because the ZiPS export has no SV column. Saves
are fitted on persistence — prior-season saves predict next-season saves, with
a role-change discount. Closers are the most volatile assets in fantasy and
this is the weakest link in the projection chain.

**Playing-time floor.** Nobody keeps a part-timer. Keeper value is computed at
full-season workload (600 PA / 150 IP / 25 SV): hold rates fixed, scale volume
up, capped at 2× so a 250-PA projection never becomes a full-time star. This
prevents ZiPS' durability haircuts from burying a genuine breakout. The
un-scaled value is kept alongside as `upside_ft` so you can see the gap.

## 1.6 Contracts as options, not obligations

This is the conceptual core and it took two corrections to get right.

A keeper contract is **an option you may decline**, not a liability you must
carry. So:

- Year 1 (2027) carries its sign — that is the decision under evaluation.
- Later years **clip at zero** — a year you would not exercise costs nothing.
- Future years discount at 0.85/yr for churn, injury and drift.

Before this, Kazuma Okamoto was charged −$9.35 for a 2028 season nobody would
keep him for, turning a −$3.50 contract into −$12.80. **Every multi-year deal
was being penalised for its own length.**

**The extension.** Any contract in its final year extends at +$5 **per year**,
for one *or* two years, once ever. That is a call option, and pricing it
properly moved cheap young stars a lot — Jhoan Duran at $4 gained ~$34.

The most recent fix (FINDINGS §24): final-year (`F`) players had the option
zeroed entirely, on the grounds it was "already in keeper_cost" — true of one
year, false of two. Ohtani went from $51 to **$76** of surplus. The rule, once
written down, is one line:

```
buy the second year iff  0.85 × (value_2028 − salary − 10) > 5
```

Nine players clear it. It is not "always extend for the max."

---

# Part 2 — What the league's spending actually says

These are the empirical findings, and they are the part a generic calculator
structurally cannot produce.

## 2.1 A dollar buys less every year

| season | $ per roto point |
|---|---|
| 2022 | $4.16 |
| ... | |
| 2026 | $9.98 |

**A dollar bought 2.5× as much production in 2022 as in 2026.** The mechanism
is keeper count: 25 players were withheld from the 2022 auction, 100 from the
2026 one. Elite talent is being absorbed into cheap long-term contracts and
never reaches the auction, so the auction is bidding on a thinner pool with the
same $2,600.

This is why the exchange rate is fitted as a *function of keeper count* and
predicted at the expected 2027 count, rather than pooled across five auctions
that happened in different worlds. Pooling would understate what 2027 costs.

## 2.2 Inflation is +52.8% and it is not optional arithmetic

Standard keeper-league formula:

```
inflation = remaining budget ÷ remaining player worth
          = $1,803 ÷ $1,180 = 1.528
```

Ten teams will keep $797 of salary that buys $1,420 of value. The $623 of
surplus does not vanish — it comes out of the auction, where $1,803 chases
$1,180 of talent. **Every auction dollar buys 65 cents of value.**

Practical consequences:

- A player worth $20 will cost about $31 at auction.
- **Keep anyone whose value exceeds `cost ÷ 1.528`.** That rule flips 30
  players versus the naive `value > cost` test.
- Surplus is worth more than cash. A $1 contract on a $14 player is a better
  asset than $13 of auction budget, because the $13 only buys $8.50 of talent.

## 2.3 The league underpays for saves

Closers return **+2.23 roto points** more than their price predicts
(permutation test, p < 0.0001). But the finding is **conditional**: it only
holds once teams punting saves are excluded. Among teams competing in the
category, buying saves is the single best-priced thing on the board.

This was almost reported wrong twice — first by selecting closers on
current-season saves (selecting on the outcome), then fixed by using
prior-season saves.

## 2.4 Depth beats stars

Correlation of team roto finish with:

- count of players at **z ≥ 1** (good): **r = +0.840**
- count of players at **z ≥ 2** (elite): **r = +0.141**

Roster construction, not star acquisition, is what separates this league.
The mechanism is roto structure: ten categories, ten teams, and you cannot bank
surplus in a category you already lead. A team of eight good players beats a
team of three elite ones and five holes.

Corollary: the free-agent wire supplied **40% of all 2026 roto production** at
$10–20 per pickup. That is the largest single acquisition channel and the model
treats it as nearly invisible — the biggest known gap.

## 2.5 Honest error bars

Bootstrap, 2,000 resamples of the pooled team-seasons: **±38% per category.**
The analytic ±16% is optimistic. That is wider than most of the knobs the model
argues about, and it should be read alongside every dollar figure. 88% of
keep/cut calls survive all six modelling variants — the decisions are more
robust than the point estimates.

---

# Part 3 — What is built, and how the pieces talk

## 3.1 The dependency chain

Data flows one direction. Nothing calls backwards. This matters: it means you
can reason about any module knowing only what feeds it.

```
data/*.csv  (FanGraphs exports, CBS exports, the constitution)
      │
      ▼
config.py ─────────────────────────────► every module reads constants from here
      │                                    (no league rule is hard-coded elsewhere)
      ▼
io.py            loaders · memoisation · name resolution
      │          (671/677 draft names matched to FanGraphs IDs)
      ├──────────────┬──────────────┬───────────────┐
      ▼              ▼              ▼               ▼
 denoms.py      project.py     auction.py      (standings)
 standings →    projections →  draft ↔         team totals
 denominators   2027/2028      production →
                stat lines     $/roto point
      └──────────────┴──────────────┘
                     ▼
                 board.py          stat lines → roto points → dollars → surplus
                     │             (uses keeper.py for PT scaling + multi-year)
                     ▼
                 keeper.py         full-time scaling · 2028 lines · extensions
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
  trade.py      freeagents.py    (scripts/)
  two-lens      the wire,        leaderboard, sensitivity,
  evaluation    priced           audit, backtest, z-scores…
      └──────────────┴──────────────┘
                     ▼
                  api.py           snapshot() — ONE object with everything
                     │
                     ▼
          scripts/build_app.py     serialise to JSON, inline into HTML
                     │
                     ▼
            out/keeper_lab.html    the app
                     │
                     ▼
             app/verify.mjs        diffs the browser's JS against pandas
```

## 3.2 The two ideas that make it maintainable

**One config file.** Every league rule and every modelling knob lives in
`config.py`. Nothing downstream hard-codes a rule. Switching projection systems
(Steamer, THE BAT, ATC) is a filename change. Turning positional adjustment on
is a boolean. This is what makes the sensitivity harness possible at all — it
just re-runs the board with different constants.

**One entry point.** `api.snapshot()` returns a single object with the board,
free agents, team summaries, standings and every fitted constant. The CLI
scripts use it, the app build uses it, a notebook would use it. If you ever
write a second interface, it talks to `snapshot()` and nothing else.

**Memoisation** (`io.cached`) means a cold build is 2.4s and a second build in
the same process is 0.08s. The decorator returns *copies* — an early version
handed out the cached DataFrame itself, so a caller mutating the result
corrupted every subsequent call.

## 3.3 The verification layer

Three independent checks, none of which was fitted to agree with the others:

| check | result |
|---|---|
| current rosters → 2026 standings | Spearman **0.842**; predicted leader finished 1st |
| replacement level, two routes | 4.14 (projection) vs 3.51 (auction intercept) |
| budget identity | top 230 sum to exactly **$2,600** |
| external: CBS's own roto rank | **0.893** (the residual is CBS including OBP) |

Plus 35 pytest invariants (~4s) and `app/verify.mjs`, which loads the built
page in a headless browser and diffs 25 numbers against pandas.

---

# Part 4 — The app: how it uses all this

## 4.1 What it actually is

`out/keeper_lab.html` is **one file, ~300 KB.** Inside it: the CSS, the
JavaScript, and the data — 275 rostered players, 400 free agents, every fitted
constant — serialised as JSON and pasted into the middle of the file at build
time.

That means: no server, no network, no install, no database. Double-click it.
It works on a plane. It works on your phone.

**The build** (`scripts/build_app.py`, ~3 seconds):

1. call `api.snapshot()`
2. merge in rest-of-season stat lines
3. round every float to 4 decimals (halves the file size, costs nothing)
4. serialise to compact JSON — column names once, then rows as arrays
5. string-replace it into `app/template.html`
6. write `out/app_reference.json` for the verifier

## 4.2 What the browser computes vs what it looks up

This distinction is the whole design.

**Looked up** (precomputed by Python, just displayed): every dollar value,
every surplus figure, the keeper flags, the projections, the constants. The
browser does no modelling.

**Computed in the browser**: exactly one thing — the rest-of-season standings
calculation. Sum each roster's ROS lines, add to current totals, rebuild the
rate stats from implied volume, re-rank all ten teams. That is what lets the
trade evaluator show live standings deltas without a server.

Re-implementations drift, so that one piece is diffed against pandas on every
build. 20 standings totals at exact equality, 5 dollar figures at rounding
tolerance.

## 4.3 Update cadence — what changes when

| input | changes | who supplies it |
|---|---|---|
| CBS rosters, standings, salaries | daily in season | you, by export |
| ZiPS rest-of-season | daily-ish in season | FanGraphs export |
| ZiPS pre-season 2027 / 2028 | ~annually, one mid-season refresh | FanGraphs export |
| auction results | once a year, at the auction | you |
| denominators, exchange rate | once a year | refitted from the above |
| league rules | ~never | the constitution |

**Realistic cadence:** weekly during the season if you rebuild by hand; daily if
you automate it. The keeper board only truly matters between October and the
February auction, and the trade evaluator matters at the deadline.

**The bottleneck is not compute, it is the export step.** FanGraphs has a CSV
download button. CBS does not have a clean one — getting rosters and standings
out is manual copy-paste today. Automating that is a scraper, which is the most
annoying and most fragile part of any project like this. Budget a full session
for it and expect it to break when CBS changes their HTML.

## 4.4 What is left on the interface

Ranked by value-per-effort:

1. **Uncertainty bands.** The ±38% is currently prose in the footer. It should
   be a range on every dollar figure. Half a session, and it is the single most
   credible thing to show an interviewer — it says "I know what my numbers are
   worth."
2. **Projection-basis selector.** `PROJECTION_BASIS` switches the board between
   blend / projection-only / 2026-only, and 17% of keep/cut calls depend on it.
   Right now that fork is invisible. Ship three payloads in one file and make it
   a dropdown — the user *watches* the model's biggest disagreement move.
3. **History chart.** `api.write_snapshot()` already persists a dated copy.
   Nothing reads it back. "How has Ohtani's value moved since June" is one line
   chart away.
4. **Auction-day mode.** A live board that tracks remaining budget and
   recomputes inflation as players come off — genuinely useful for four hours a
   year.

Items 1–3 are mechanical. Put a cheap model on them.

---

# Part 5 — Deployment, sharing, and cost

You know almost no CS, so here is the ladder from "works on your laptop" to
"works for everyone, always current." Each rung costs more effort. **You are
already on rung 1 and rung 1 may be enough.**

## Rung 1 — a file (where you are). Cost: $0

`keeper_lab.html` is a document, like a PDF. Email it, AirDrop it, put it in
Dropbox. Whoever opens it sees the app. It contains its own data, so it works
offline forever — and it is frozen at the moment you built it.

This is the right answer for: sharing with league-mates, attaching to a job
application, opening on your phone at the draft.

## Rung 2 — a URL. Cost: $0

"Static hosting" means a server that only hands out files and never runs code —
so it is nearly free and nearly unbreakable. Options: **GitHub Pages**,
**Netlify**, **Cloudflare Pages**. All have free tiers that comfortably cover
this.

You upload the HTML file; you get `https://something/keeper-lab.html`. Anyone
with the link sees it. Updating = uploading a new file.

Worth knowing: **the data is inside the file, so the link is public.** For
fantasy baseball that is fine. If it were salary data it would not be.

## Rung 3 — a URL that updates itself. Cost: $0

**GitHub Actions** is a free robot that runs your code on a schedule. You give
it a file that says "every morning at 6am, install pandas, run
`scripts/build_app.py`, publish the result." Free for public repos; 2,000
minutes/month free for private ones, and your build takes ~30 seconds, so you
would use about 15 minutes a month.

This is the correct end state for this project. The only thing that blocks it
is the CBS export problem in §4.3 — the robot can fetch FanGraphs, but it
cannot log into CBS and copy-paste for you.

## Rung 4 — a real server. Cost: $0–7/month

Only needed if users must **change model settings and see the model re-run** —
flip `PROJECTION_BASIS`, re-fit with a different denominator window. That
requires Python running somewhere, live.

Options: Streamlit Community Cloud (free, public, sleeps when idle),
Render/Railway/Fly.io (~$5–7/month for an always-on small instance).

**My recommendation: don't.** The set of settings people actually want to
toggle is small enough to precompute. Shipping three payloads in one static
file gets you 90% of the benefit for 0% of the operating cost, and a thing with
no server cannot go down.

## Rung 5 — a product. Cost: real money

Accounts, logins, per-user leagues, a database, someone's credit card on file.
$20–100/month minimum and a permanent maintenance obligation. Not this project.

## The distribution answer

| you want | do this | cost |
|---|---|---|
| show your league | email the HTML | $0 |
| put it in a portfolio | GitHub repo + Pages link | $0 |
| always current | GitHub Actions rebuild + Pages | $0 |
| let people change model settings live | Streamlit Cloud or a $7 VPS | $0–7/mo |

For a job interview, **rung 2 plus the public repo is strictly better than a
live app**. What gets you hired is `FINDINGS.md` and `LAB_NOTEBOOK.md` — the
retractions, the ±38% error bar, the two independent replacement-level
estimates. A hiring manager reads five minutes of that and knows more about how
you think than any dashboard could tell them.

---

# Part 6 — The plumbing: how data is stored, and the SQL question

## 6.1 How it works today

There is **no database.** Here is the whole storage story:

- **Inputs:** flat CSV files in `data/` — FanGraphs projection exports, CBS
  roster/standings/draft exports — plus the constitution as a `.docx`.
- **In flight:** pandas DataFrames in memory. A DataFrame is a table that lives
  in RAM: rows, typed columns, and a large library of operations. Think of it
  as a spreadsheet you manipulate with code.
- **Outputs:** CSVs and JSON in `out/`, plus dated **Parquet** snapshots.

Every run reads the CSVs from scratch and recomputes everything. Cold: 2.4
seconds.

**Parquet** is worth knowing about: a file format that stores data by column
instead of by row, compressed and typed. A CSV of the board is ~400 KB and
every value is a string until something parses it; the Parquet is ~80 KB and
knows `salary` is an integer. Every tool in this ecosystem reads it.

## 6.2 Do you need SQL? Honestly, no — and here is the reasoning

SQL earns its keep when at least one of these is true:

1. **The data does not fit in memory.** Yours: 275 rostered players, ~2,000
   projections, 677 auction purchases, 50 team-seasons. That is roughly 2 MB.
   Your laptop has 16,000 MB.
2. **Many processes or people share one store and must not corrupt each
   other.** Yours: one person, one process, one folder.
3. **You need to query across history that is too large to just load.** Yours:
   *this one will eventually be true.* At one snapshot a day for a season you
   have ~180 files. Still small, but "show me every player whose value dropped
   more than $10 in the last month" is genuinely nicer in SQL than in a loop.

So the honest answer: SQL is not a fix for a problem you have. It is a
convenience for a problem you will have — **querying your own history.**

## 6.3 What it would look like, concretely

Use **DuckDB.** It is SQL that runs *inside your program* — no server, no
install, no port, no password. The entire database is one file. Think "SQLite
for analytics." `pip install duckdb` and you are done.

The key trick, and the reason this is nearly free to adopt: **DuckDB queries
Parquet files directly.** You do not need to import anything. The snapshots you
are already writing become queryable as-is:

```sql
SELECT name,
       MAX(redraft_value) - MIN(redraft_value) AS swing
FROM 'out/snapshots/*/board.parquet'
GROUP BY name
ORDER BY swing DESC
LIMIT 20;
```

That is a complete answer to "whose value has moved most this season," running
over every snapshot you have ever written, with no migration step.

If you later want a persistent file, `klab.duckdb` in the project folder, with
tables `board`, `standings`, `auctions`, `snapshots` — each carrying a
`snapshot_date` column. It sits next to the CSVs, gets backed up with them, and
is a single file you can copy.

## 6.4 The question you actually asked: is it called every time?

**No, and this is the important architectural point.**

There are two very different jobs, and conflating them is the classic mistake:

| | **Compute** | **Archive** |
|---|---|---|
| what | fit denominators, price players, evaluate a trade | remember what the answer was on 12 June |
| lives in | pandas, in memory, from CSVs | Parquet / DuckDB, on disk |
| speed | 2.4 seconds cold | instant |
| needed to run the model? | yes | **no** |

The model would **not** read from SQL to run. It reads the CSVs, computes, and
then *writes* a snapshot to the archive. Running a trade evaluation never
touches the database at all — `snapshot()` is already in memory and warm calls
are 0.08 seconds.

The database is a **write-target for results and a read-source for history.**
It is not in the critical path. If you deleted it tomorrow, every number in the
app would still be computed correctly; you would just lose the ability to ask
"how has this changed."

That is the general principle, and it is worth internalising because it applies
far beyond this project: **put the database where the data needs to outlive the
process, not where the data needs to be fast.** Small analytic workloads belong
in memory. Databases are for persistence, sharing, and concurrency — and you
have a persistence need and neither of the other two.

## 6.5 If you want the SQL practice anyway

It is a defensible reason on its own — "computational social science" job
descriptions ask for SQL constantly, and a project you understand deeply is the
best possible place to learn it. In that case:

- Point DuckDB at your existing Parquet snapshots (§6.3). Zero migration.
- Write the five queries you would actually want: biggest value swings, team
  surplus over time, which categories each team has gained or lost, free agents
  who crossed a value threshold, keeper decisions that flipped.
- That is a genuine SQL portfolio artifact and it costs about an hour.

Do not migrate the compute path into SQL. It would be slower, harder to read,
and impossible to unit-test.

---

# Part 7 — Why zip files instead of editing your folder

Fair question, and the answer is about where this session physically runs.

**This session runs in a cloud container, not on your Mac.** The project lives
at `/root/klab` on a Linux machine in Anthropic's cloud. It is not your disk. I
can reach your computer only through a bridge, and that bridge only sees
folders you have explicitly connected to *this specific session*.

Right now, nothing is connected — I can see the *names* of your home folders
(Documents, Dropbox, PycharmProjects…) but not their contents, and I cannot
write into them. Folder grants do not carry over between sessions. So the zip
is the delivery mechanism of last resort: it is the only way to get a full
directory tree onto your disk without access to your disk.

Two things follow, and the second one matters more:

**1. You can fix this.** Either connect the folder yourself when you start a
session, or ask me to request access to a specific path — you get one approval
dialog, and after that I read and write your real files directly. No zips, no
re-syncing, and I can see the edits you made between sessions. That is a
strictly better workflow and it is what I would do next time.

**2. The container is temporary.** It gets reclaimed after the session ends.
Anything I have not delivered to you is gone. That is the real reason for
packaging at the end of every session, and it is why the handoff documents
exist: **the documentation is the memory.** A fresh session reads
`HANDOFF.md`, `METHODS.md` and `LAB_NOTEBOOK.md` and picks up where this one
stopped, because nothing else survives.

Which is also, incidentally, the strongest argument for putting this in **git**
— a version-control system, i.e. a tool that stores every version of every file
plus a message about why it changed. The project has no git repository yet.
With one:

- your Mac holds the authoritative copy
- every session's changes are a labelled commit you can read or undo
- a public GitHub repo *is* the portfolio artifact, and it is where rung 2 and
  rung 3 of Part 5 start

That is roughly twenty minutes of setup and it would end the zip cycle
permanently. It is the highest-value non-modelling thing left on the list.
