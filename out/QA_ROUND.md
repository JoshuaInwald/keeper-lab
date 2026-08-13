# Answers — diagnostic round

Ordered by how much they could change a number. No code written; several items
end in "this is a to-do" or "I need you to confirm a rule."

---

# A. Things that might be wrong

## A1. Ohtani and the extension — I need you to check this, not me

You said: *"ohtani is going to be a free agent at end of season, so shouldn't he
have no future surplus value bc he cant be extended?"*

**The model currently says he can be extended, and I cannot find a rule that
says otherwise.** Here is the evidence, so you can adjudicate:

- His contract code is `F` — final year, 2026 was the last season at $16.
- The constitution (which I extracted directly from your `.docx`, §Keeper
  Eligibility) says: *"owners must extend the player's contract by adding $5 for
  each additional year… extend the player for one more season at $15 or two more
  seasons at $20"* and *"Players can only be extended once per contract."*
- `already_extended()` scans for players whose current salary exceeds their last
  auction price by exactly +$5 or +$10 while not sitting on an FA acquisition
  price. It flags **three** players: Yamamoto, Muñoz, Harper. **Ohtani is not
  among them.**
- So on the data I have, Ohtani is a first-time extension candidate: keep at
  $21 for 2027, or $26 for 2027–28.

**Three possibilities, and only you can tell me which:**

1. `F` in your league means "gone, not extendable" and my reading of the
   constitution is wrong. → Then **every `F` player's future surplus is $0**,
   not just Ohtani's. That is 35 players, and it would be the largest single
   correction in the project. Ohtani goes from **$76 to $0** of keeper value and
   becomes a pure 2026 rental.
2. Ohtani specifically has already used his extension and the salary data
   doesn't show it (the detection is inference from salary-versus-draft-price,
   which is exactly the kind of second-hand reconstruction that has burned us
   twice already — see FINDINGS §23 on Harper).
3. You were thinking of real-life MLB free agency. Ohtani is signed with the
   Dodgers through 2033, so that is not it — but I mention it because *fantasy*
   `F` and *baseball* free agency are easy to conflate.

**Do not let me guess.** This is the same failure mode as the contract codes
being backwards and the Harper mistake: a rule error is arithmetically
consistent, so nothing in the test suite or the audit script can catch it.
Tell me which of the three, and it is a one-line fix either way.

## A2. Reliability weights — you were right to ask, and the code already does it

**Refit 2026-08-13, see `out/FINDINGS.md` #28.** Eight of ten values held
exactly; BB and H had been copy-pasted from WHIP's reliability (0.237
instead of their own 0.463/0.359) — a real bug, now fixed, with a
regression test added so it can't silently recur.

You asked whether reliability is player-year1 vs player-year2 correlation, and
whether it needs a playing-time adjustment because PT varies independently of
talent.

**It is already computed on rates, not counting totals.** From `project.py`:

> *"Year-over-year reliability of each **rate**, measured on this dataset
> (hitters 250+ PA in consecutive years, n=693; pitchers 40+ IP, n=785)."*

So `HR` is HR-per-PA, `W` is wins-per-IP, and so on. Playing time is divided
out before the correlation, and the 250 PA / 40 IP filters remove the
small-sample noise that would otherwise dominate. Your objection was the right
one to raise; the answer is that it was handled.

Two caveats worth keeping:

- The blend has a **separate** playing-time term — `PA/(PA+250)` capped at 0.5
  — so sample size and signal are handled by two different mechanisms rather
  than being conflated into one number. That's the right structure.
- The correlations are in-sample on 2022–26 and were computed once, then
  hard-coded. They should be refit when 2026 closes. Not urgent — these are
  stable quantities.

## A3. Pitcher wins at r = 0.151 — yes, really, and it's worse than you think

That figure is **wins per inning**, year over year, on pitchers with 40+ IP in
consecutive seasons (n=785). Not raw win totals.

Published research agrees. Pitcher W is roughly: team run support (not the
pitcher) × bullpen conversion (not the pitcher) × manager hook decisions (not
the pitcher) × some actual pitching. The *only* reason r isn't near zero is
that good pitchers cluster on good teams and pitch deeper into games.

This is the strongest argument in the project for the reliability weighting
existing at all. A flat 50/50 blend carried last year's win rate forward at
full strength and buried a pitcher who went 3–17 on a bad team — a player whose
underlying rate stats were fine.

## A4. Replacement level — your instinct that it needs more validation is correct

**Revisited 2026-08-13, see `out/FINDINGS.md` #27.** The clean test named
below is still blocked — confirmed directly, not just assumed, that no
transaction-log data exists. Ran the best feasible alternative instead: an
internal-consistency check against the full free-agent pool (only 24 of
1,714 project above the current estimate, and the pool's shape has no gap
or cliff near it). The numbers below have also since moved with `out/FINDINGS.md`
#26/#31's denominator fixes — current live values are 3.98 (intercept) and
4.78 (230th projection); the table below is what this round of Q&A actually
saw and is left as-is for that record.

Three estimates of "what a free player is worth," from independent data:

| route | value | what it is |
|---|---|---|
| auction regression intercept | **3.51** | what a $0 purchase returned |
| 230th-best projection | **4.14** | one per active roster slot |
| median of players actually picked up from FA in 2026 | **5.04** | realised |

Your framing is right: **a $0 player does not exist.** Minimum auction bid is
$1; the genuinely free player is the waiver claim. So the intercept is an
*extrapolation past the edge of the data*, and it should be read as a lower
bound.

The 5.04 figure is an upper bound, and deliberately so — those pickups were
selected *after* they started producing. It is survivorship, not availability.

**So true replacement is probably 4–5, and we use 4.14.** That is mildly
conservative, which means the model slightly *over*values rostered players.
Every dollar figure is a touch generous to your own roster.

The clean test I have not run: take every player available on the wire on date
X, measure their realised production forward from X, and take the median. That
is availability without survivorship. **It needs the transaction logs**, which
is the same blocker as several other items. Worth doing once those exist.

Note this is exactly what `WAIVER_VALUE = "low"/"medium"/"high"` exposes as a
knob — the three settings are 230th / 300th / 5.04. Flipping it to "high" shows
you how much the answer moves.

## A5. The 2026 calibration question — you are right, and here's the wrinkle

**Partially resolved 2026-08-13, see `out/FINDINGS.md` #26.** The "include
2026" proposal below is now implemented — but as raw partial *actual*
standings data (no ROS projections blended in), not the "70% actual + 30%
projected, scaled to full season" construction this section describes. That
matters: the compression-bias worry below is specifically about projected
data pulling dispersion down, and it doesn't apply to what got built, since
nothing here is projected. What #26 tested instead was whether a partial
*real* season is over- or under-dispersed per category (it's over-dispersed
for ERA/WHIP/SV, not under — the opposite direction from this section's
worry, and the reason those three specifically get excluded rather than
scaled). **The specific experiment proposed two paragraphs down — reconstruct
2024/2025 at 70% complete and compare to their own realised full season —
was not run.** It would still be worth doing, since it's a cleaner test of
compression specifically and #26 doesn't fully substitute for it.

**Confirmed: denominators are fit on 2024 and 2025 only. 20 team-seasons.**
`DENOM_SEASONS = [2024, 2025]`. That was your call earlier in the project
(league skill/volume regime changed in 2024), and I implemented it literally.

Your proposal — add 2026 season-to-date + ROS as a third full-season-equivalent,
getting to 30 team-seasons — would cut the standard error on the dispersion
estimate by about 18%. That is a real gain and the ±38% error bar is the
project's weakest number.

**The wrinkle: projections are compressed.** Any projection system shrinks
toward the mean, so a team's *projected* final total has less spread across
teams than its *realised* total will. Feed compressed totals into a dispersion
estimate and the dispersion comes out too small → denominators too small →
**every player looks more valuable than he is.** The bias runs one direction
and it inflates the whole board.

How bad? 2026 is ~70% complete, so only ~30% of each team-season is projected.
The compression applies to that 30%. My guess is the bias is small relative to
the 18% precision gain — but it is a guess, and it is testable:

> Take 2024 and 2025. Reconstruct what "season-to-date at 70% + ROS" would have
> looked like at that point, compute dispersion, and compare to the realised
> full-season dispersion. That measures the compression directly, on data where
> we know the answer.

That is a half-session experiment and it settles the question rather than
arguing it. Three options once we know the answer:

1. **Include 2026 raw.** Simplest. Accept a small downward bias.
2. **Include 2026 with a compression correction** estimated by the experiment
   above. Best if the bias turns out to be material.
3. **Include 2026 season-to-date only, scaled to full-season volume.** No
   projection contamination at all — you scale a 70% real season up by 1/0.70.
   Adds noise (it assumes the remaining 30% looks like the first 70%) but adds
   no bias. **This is my preferred option** and I would not have thought of it
   without your question.

One more thing to flag: 2026 team totals are also what the roster→standings
validation is scored against (Spearman 0.842). Using 2026 in the denominators
makes that validation mildly circular. Not fatal — different quantities — but
it should be noted in the write-up if we do it.

## A6. z-score thresholds — agreed, with one caveat

**Partially done 2026-08-13, see `out/FINDINGS.md` #29.** The share-of-
production test described two paragraphs down was run. It's not the clean
win predicted: share is a *weaker* predictor than raw counts at both z≥1 and
z≥2, though a *stronger* one for "share below average." The threshold move
(1.5/0.5 instead of 2.0/1.0) described in this paragraph was **not** done —
only the counts-vs-share axis was tested, not the threshold axis. Both were
proposed together below; only one got done.

You want stars at z ≥ 1.5 and depth at z ≥ 0.5 rather than 2.0 and 1.0. Fair,
and it's a one-line change in `scripts/zscores.py`.

Expect the contrast to **attenuate**. The current result is r = +0.840 (count
of z≥1) versus r = +0.141 (count of z≥2). Moving the thresholds inward makes
the two measures overlap more, so they will correlate with each other and their
correlations with finish will converge. The qualitative finding — depth beats
stars — should survive; the dramatic gap will shrink.

**The caveat that matters more than the threshold:** count of z≥0.5 players is
partly a measure of *roster activity*, not roster quality. A manager who churns
the wire accumulates more qualifying player-seasons than one who sits still,
independent of skill. At z≥2 that contamination is small (nobody streams their
way into a z=2 season); at z≥0.5 it is substantial.

The cleaner version of the test uses **share of team roto production** from
players above each threshold, rather than raw counts. That is activity-neutral.
Worth doing at the same time as the threshold change.

## A7. Waiver pickups and future options — you're right, my hedge was sloppy

Your reasoning: acquisition was free, options can only be declined, therefore
option value is weakly positive, therefore the 2026 decision to pick someone up
should not depend on the contract at all.

**That is correct and I agree without qualification.** An option with a
non-negative payoff and zero acquisition cost cannot make a pickup worse. The
2026 add is justified on 2026 production alone; the contract is a free call
option on top.

The "corollary" hedge in the earlier document was about a **different**
question — whether *surplus is worth more than cash at the auction* — and I let
the two run together. They are separate:

- **Free pickup:** contract options are pure upside. Ignore them in the decision.
- **Auction dollar vs surplus contract:** genuinely a trade-off, because the
  dollar has an alternative use. This is where inflation bites.

Where the option *does* matter for a pickup is **priority between two available
players**: at similar 2026 value, take the one with more years of cheap control.
It breaks ties; it never reverses the decision to add someone.

---

# B. Mechanics you asked me to explain properly

## B1. `c_n` and where 3.078 comes from

Start with what a roto standing physically is. Ten teams, one category, ranked.
The distance from 1st to 10th is a **range**, and one standings point is
one-ninth of that range.

So I need to convert a *dispersion* (a standard deviation, which is what I can
estimate well) into an *expected range* across ten draws.

For a sample of size n from a normal distribution:

```
E[range] = c_n × σ
```

`c_n` is a tabulated constant. It has a long history in statistical process
control, where it's called **d₂** — the constant that converts the average
range of small samples into a standard-deviation estimate for control charts.
Same constant, opposite direction.

Values:

| n | c_n | used for |
|---|---|---|
| 8 | 2.847 | saves (2 teams punt and are dropped) |
| 9 | 2.970 | — |
| 10 | **3.078** | all other categories |

**Why it grows with n:** more draws means a better chance of pulling an extreme
value, so the expected gap between the largest and smallest widens. It grows
slowly — roughly like √(2 ln n) — which is why 8 and 10 differ by only 8%.

The chain, end to end:

```
pooled relative dispersion  (unitless, from 20 team-seasons)
  × expected 2027 league level  → σ in real units (e.g. runs)
  × c_n = 3.078                 → expected 1st-to-10th spread
  ÷ (n − 1) = 9                 → units per standings point
```

For runs that lands at **39.4**. Which answers your next question:

## B2. "Every 40 runs is one roto point?"

**Yes.** 39.4 runs, to be exact. Equivalently, one run = 0.025 standings points.
One home run = 1/15.4 = 0.065 points. One stolen base = 1/20.4 = 0.049.

This is also why the SV correction mattered so much: 6.57 saves per point means
saves are the most concentrated category on the board, and getting the
denominator 19% wrong moves every closer's valuation 19%.

## B3. Rate stats are **not** computed on 600 PA / 150 IP

Two different things share the "full season" idea and I should have separated
them:

**The rate-stat marginal** is computed against a **full team's volume.** A
hitter's AVG contribution is: what does team batting average become with 13
average hitters plus him, versus 14 average hitters? Team AB is roughly 6,000 —
derived from the top `14 × 10` hitters by PA in that season, summed, times a
realisation factor, divided by ten teams. The base is `team_AB × 13/14`.
Pitchers use `team_IP × 8/9`.

**The 600 PA / 150 IP / 25 SV floor** is a completely separate mechanism — it is
the *playing-time scaling for keeper valuation*. Hold a player's rates fixed,
scale his volume up to the floor, capped at 2×. It exists so ZiPS' durability
haircuts don't bury a breakout, and it answers "what if he plays a full year,"
not "how much does his batting average move my team."

Confusing the two would make every rate contribution about ten times too large.

## B4. Are $10.08 and $6.66 the anchors? Yes — and they answer different questions

Both come from the same regression, scaled differently.

- **$10.08/roto point — auction scale.** The inverse of the fitted slope. What
  the league's own bidding says a point costs. Use it to judge whether a *price*
  was good, and to price a 2026 standings point in a trade.
- **$6.66/roto point — redraft scale.** The top 230 players' values are forced
  to sum to exactly $2,600 (10 × $260). Use it to compare *players*, because it
  is the only scale where the values add up to money that exists.

The gap between them is not an error — it is the **surplus the league extracts
from keepers**. Auction dollars buy production at $10.08; the total value on
rosters divided by total money is $6.66. The difference is what cheap contracts
are worth.

Everything on the board uses **redraft** unless labelled otherwise.

## B5. What ±38% actually is, and what it doesn't cover

It is a **bootstrap confidence interval on the denominators.** Mechanically:
resample the 20 pooled team-seasons with replacement, 2,000 times; refit the
dispersion each time; look at the spread of the resulting denominators. The
typical category's denominator moves ±38% across resamples.

The analytic ±16% (from the χ² distribution of a variance estimate at n=20) is
narrower because it assumes normality and independence across team-seasons.
Neither holds well. Take the bootstrap.

**What it applies to:**

- the units-per-standings-point conversion for each category
- therefore the *relative weighting between categories* — whether a stolen base
  is worth more or less than a home run
- therefore each player's total roto points, and his dollar value

**What it does NOT apply to:**

- **The $2,600 budget identity.** That holds by construction at any
  denominators. It is not an estimate.
- **Rank ordering within a single category.** Scaling a category by a constant
  doesn't reorder anyone. If the R denominator is wrong by 30%, every player's R
  contribution is wrong by 30% and the R ranking is unchanged.
- **Keep/cut decisions**, mostly. 88% survive all six modelling variants — a
  decision only flips when surplus is near zero, and most aren't.
- **Projection error.** This is the big one. ±38% is uncertainty in *how to
  score a stat line*. It says nothing about whether the stat line is right.
  Projection error is separate, additional, and probably larger for any
  individual player.

The right way to read it: **treat category weights as approximate and rankings
as solid.** "Ohtani is worth about $70, definitely more than Skubal" is
supported. "Ohtani is worth $71.9" is not.

## B6. The flow chart, in prose

Ignore the ASCII art. It's a **pipeline** — a chain where each stage's output is
the next stage's input, and nothing calls backwards.

1. **Raw files come in.** CSV exports from FanGraphs (projections) and CBS
   (rosters, standings, draft results). Plus the constitution.
2. **`config.py` holds every rule and knob.** Every other file reads from it.
   Nothing hard-codes a league rule anywhere else.
3. **`io.py` loads the files** and matches names to FanGraphs IDs (671 of 677
   draft picks matched). It also caches, so repeated calls are free.
4. **Three modules each compute one thing from the loaded data, independently:**
   - `denoms.py`: standings → how many units buy a standings point
   - `project.py`: projections → each player's 2027 and 2028 stat line
   - `auction.py`: draft prices + realised production → dollars per roto point
5. **`board.py` joins those three.** Stat line → roto points (using the
   denominators) → dollars (using the exchange rate) → surplus (minus contract
   cost). It calls `keeper.py` for playing-time scaling and multi-year logic.
6. **`trade.py` and `freeagents.py` consume the board.** They don't recompute
   anything; they rearrange it.
7. **`api.py` wraps all of it in `snapshot()`** — one function, one object.
8. **`scripts/build_app.py` serialises that object into the HTML file.**

The only thing worth remembering: **rules live in one file, everything flows one
direction, and everything is reachable through `snapshot()`.**

## B7. Yes — `snapshot()` is the answer, and it is what feeds the UI

Exactly right. `snapshot()` runs the whole model and returns one object holding
the valued board, the free agents, the team summaries, the standings, and every
fitted constant. Cold: 2.4 seconds. Warm: 0.08 seconds.

The UI build calls it, serialises the result, and pastes it into the HTML. The
CLI scripts call it too. **Any second interface you ever write should talk to
`snapshot()` and nothing else** — that's the point of having it.

## B8. "CLI scripts"

**CLI = Command-Line Interface.** A program you run by typing its name in a
terminal, with arguments, and it prints text. No windows, no buttons.

```bash
PYTHONPATH=. python3 scripts/eval_trade.py "NPB No Stars" "Spehr's Army" \
    "Julio Rodríguez,Tarik Skubal" "Christian Scott,Brandon Lowe"
```

That's a CLI script: name, four arguments, text output. The fourteen files in
`scripts/` are all of this shape. They're the interface that existed before the
app, and they're still the fastest way to answer a one-off question or to
rebuild everything.

---

# C. Software questions

## C1. The most revealing tests

Of the 35, four earn their keep. Note what they have in common: **none of them
checks a specific number.** They check *properties that must hold whatever the
numbers are*, which is why they keep working when the model changes.

**1. Category sign conventions, every season.** For all five seasons and all ten
categories: does a bigger counting total earn more standings points, and does a
lower ERA earn more? Checks `|ρ| = 1.0` against the actual standings.

This one is here because **the ranks were inverted for a while.** The bug was
invisible — every team still had a plausible-looking point total, they were just
in the wrong order. It was caught only because you mentioned in passing that
Pookie 2.0 was leading and my output disagreed. A human noticing a discrepancy
in conversation is not a testing strategy. Now it's a test.

**2. A contract can never be worth less for having more years.** Give the
function two identical players, one with one year of control and one with two.
Assert the two-year player is worth at least as much.

This encodes the *conceptual* fix — a contract is an option, not an obligation.
Before it, Okamoto was charged $9.35 for a 2028 season nobody would keep him
for. The test would fail loudly if anyone ever reintroduced that.

**3. The budget identity.** Top 230 players sum to exactly $2,600. Caught a
build where the number came out $3,854 because the calibration pool and the
valuation pool had silently drifted apart. This is the cheapest, highest-value
test in the project: one line, catches an entire class of error.

**4. The browser-versus-pandas diff** (`app/verify.mjs`). The app re-implements
the standings calculation in JavaScript. So the build writes down what pandas
says about one real trade, then a headless browser loads the page, runs the same
trade, and diffs 25 numbers. Standings points must match exactly; dollar sums
get a tolerance because the payload rounds to four decimals.

This is a **differential test** — two independent implementations of the same
thing, checked against each other. It's the strongest form of test available
when you have a reference implementation, and it caught a real bug (the
`PA_x`/`PA_y` column collision) within an hour of existing.

## C2. Is this normal in industry? Partly.

Honest answer:

- **Unit tests** (does this function return the right value for this input) are
  universal. Every serious company has them.
- **Property/invariant tests** (does this relationship hold for *all* inputs) —
  what most of yours are — are less common. Well-run data and finance teams do
  them; most product teams don't.
- **Differential testing** against a reference implementation is standard in
  compilers, databases, cryptography, and numerical libraries. Rare elsewhere,
  because you usually don't have a second implementation to check against.

**Where testing is genuinely weak across the industry is exactly where you
live: analytics and data science.** Notebooks mostly aren't tested at all. The
usual excuse is that outputs are judgment calls, which is half true and half
laziness — the budget identity is not a judgment call.

So: 35 invariant tests on a personal analytics project is above the industry
norm for data work and roughly par for good software engineering. **This is a
point worth making in an interview**, because "I test my analysis code" is a
differentiator for a research role in a way it wouldn't be for a backend role.

## C3. Why JSON and not CSV or SQL for the UI

**Because the browser speaks JSON natively and speaks nothing else natively.**

JSON is *JavaScript* Object Notation — it is, near enough, JavaScript's own
syntax for data. A browser parses it with one built-in instruction. To use CSV I
would have to ship a parser and handle quoting and type-guessing; to use SQL I
would have to ship a database engine (this exists — DuckDB compiles to
WebAssembly — and it would add several megabytes to solve a problem you don't
have).

Second reason: **it has to be a single file.** A CSV would be a separate file
the HTML fetches, which means either a web server or the browser blocking the
request for security reasons. Inlining JSON into the HTML is what makes the
"double-click it and it works, offline, on a plane" property possible.

It's stored compactly, too: column names appear once, then each player is a flat
array. That's ~40% smaller than the obvious object-per-player encoding.

## C4. Why HTML and not "a real frontend framework"

**HTML/CSS/JavaScript *is* the frontend.** React, Vue, Svelte, Next.js — all of
them produce HTML, CSS and JavaScript. They're organisational tools for large
apps, not alternatives to the underlying technology.

What a framework buys you: component reuse across dozens of screens, state
management for complex apps, a large team working without collisions. What it
costs: a build step, `node_modules` (typically 200+ MB), a package manager,
version churn, and a deployment story.

You have six screens and one developer. The framework would be pure overhead,
and — decisively — it would **break the single-file property**. A React app is a
folder that needs building and serving. It cannot be emailed.

Streamlit, which was the original plan, is worse still for your case: it needs a
live Python process, so the tool would only exist at the desk where the repo is
checked out.

## C5. Does the HTML do the drag-and-drop dashboard thing?

**Partly. Let me be precise about what exists.**

It has: sortable columns (click a header), live filters (team, role, keeper
status, text search), a click-to-open player card, an inflation toggle, and a
trade builder where you click players to add them and click a chip to remove
them — with the standings recomputing live as you do.

It does **not** have: literal drag-and-drop, charts of any kind, or resizable
panels.

Drag-and-drop is achievable — the browser has a built-in API for it — but it is
genuinely worse than click-to-add on a phone, which is where you'll use this at
a draft. **Charts are the real gap**, and the two worth building are the value
history line (§C7) and a category-strength bar chart per team. Both are a few
hours with a small charting library.

---

# D. Automation, deployment, storage

## D1. Can the data pipeline be automated? Partly — and your plan is the right one

Source by source:

| source | automatable? | how |
|---|---|---|
| **Real MLB stats to date** | **Yes, cleanly** | MLB's Stats API is public, free, undocumented-but-stable, no key required. This is a solved problem. |
| **FanGraphs ROS / ZiPS** | **Yes, with care** | No official public API. The CSV export button hits a URL you can call directly. It works; it is not a supported interface, so it can change without notice. Rate-limit yourself and cache. |
| **CBS rosters / standings / transactions** | **No clean path** | No public API. Private leagues sit behind a login. Scraping means handling authentication and breaks whenever CBS touches their HTML. |

**Your proposed workflow — copy-paste the raw text from the CBS page, have an
LLM parse it into the standard standings/roster format, drop that into
`data/` — is the correct answer.** Reasons:

- Weekly cadence means about 90 seconds of your time per week. A scraper is a
  full session to build and a recurring maintenance tax.
- It degrades gracefully. When CBS redesigns their page, a scraper silently
  breaks or, worse, silently returns wrong data; an LLM reading pasted text just
  keeps working.
- Parsing semi-structured text into a fixed schema is genuinely what LLMs are
  best at.

The one thing to build alongside it: a **validator** that checks the parsed
output before it overwrites anything — ten teams present, category totals within
plausible bounds, no duplicated players, roster sizes sane. `scripts/audit.py`
is already most of this. The failure mode you're guarding against is an LLM
silently mis-parsing one row, and a schema check catches it instantly.

**RPA software** (UiPath, and similar tools that drive a browser like a human)
is the wrong tool here — enterprise pricing, heavyweight, and it breaks on UI
changes exactly like a scraper does.

**GitHub Actions** can run the FanGraphs and MLB pulls on a schedule for free.
It can't do the CBS step, because that needs your login. So the realistic
weekly loop is:

```
Monday: you paste CBS text (90 seconds)
     → LLM parses + validator checks
     → data/ updated in your project folder
     → rebuild runs (3 seconds)
     → new keeper_lab.html + a dated snapshot
```

## D2. The history chart — yes, exactly what you described

It would show each player's dollar value as a line over the season, so you can
see the value move as real production accumulates and the projection systems
revise their rest-of-season numbers in response.

You'd read three things off it:

- **Trajectory** — is this a breakout that's still climbing, or a hot April
  that's decaying?
- **Trade timing** — sell into a spike, buy a dip that ROS hasn't caught up to.
- **Model behaviour** — how fast does your own blend react to new information?
  That's a diagnostic on the reliability weights.

The data is already being written (`api.write_snapshot()` persists a dated
Parquet copy). Nothing reads it back yet. It's a chart and a query.

## D3. Multi-level data — a fair push, and a partial concession

You're right that you have entities at multiple levels — players, teams,
seasons, snapshots, transactions — and that the interesting questions cross
them.

**Where I concede:** as the number of entity types grows, a declarative query
language gets meaningfully easier than procedural merges. "For each team, in
each snapshot, the share of roto production from players acquired after opening
day" is one SQL statement and about fifteen lines of pandas. Once transaction
logs exist, you'll have five or six related tables and that gap widens fast.

**Where I'd still push back:** *relational structure* is a reason for
relational *modelling* — thinking in tables and keys — not necessarily for a
database *engine*. pandas does joins. The engine earns its keep on size,
concurrency, and durable persistence, and you have a persistence need and
neither of the other two.

**Practically this distinction doesn't matter, because DuckDB gives you the
query language without the engine overhead.** It reads your existing Parquet
snapshots directly — no server, no import, no migration:

```sql
SELECT name, MAX(redraft_value) - MIN(redraft_value) AS swing
FROM 'out/snapshots/*/board.parquet'
GROUP BY name ORDER BY swing DESC LIMIT 20;
```

So: adopt SQL for **querying history and crossing entity levels**. Keep the
modelling in pandas, where it can be unit-tested. That split is the standard
one in analytics work and it's the right shape here.

## D4. GitHub from Cowork — no, and here's the specific reason

You're right to ask, and the answer is a hard constraint rather than a
preference.

I have two shells, and neither can do the job:

- **`device_bash`** runs on your Mac, inside the Cowork workspace, and can see
  your connected folders — but it has **no network access**. It cannot reach
  github.com. Git works locally (`init`, `add`, `commit`); `push` cannot.
- **`Bash`** runs in this cloud container and *does* have network — but it
  doesn't have your files (they'd have to be copied up), and it can't
  authenticate as you. The only way it could push is if you handed over a
  credential, which you should not do in a chat transcript.

**So: use Claude Code for this**, running in a terminal on your Mac. It has your
filesystem *and* your network *and* your existing GitHub authentication, and git
is a first-class workflow there rather than something being worked around.

The handoff document I wrote is still correct — retarget it at Claude Code
rather than "a Cowork session," and drop §0 (finding the files), since Claude
Code starts in the folder. Everything else stands: the `.gitignore`, excluding
`data/`, deliberately committing `out/`, the "do not clean up the code"
instruction.

`brew install gh && gh auth login` first, then hand it the doc.

---

# E. Queue, agreed

In your stated order:

1. **Uncertainty bands** — propagate the ±38% to displayed dollar values and
   show ranges. First thing when you send me back into go mode.
2. **Projection-basis dropdown** in the app — ship three payloads, one control.
3. Then, from this round: the **2026-in-denominators experiment** (A5), the
   **z-threshold change with production shares** (A6), and whatever you tell me
   about **Ohtani's extension** (A1).

A1 is the only one that could invalidate a headline number. It's also free to
resolve — you just have to read the rule.

**Status as of 2026-08-13:** A1 resolved (`config.NON_EXTENDABLE_NAMES`,
also see `out/FINDINGS.md` §24). A5 partially done (#26) — the raw-2026
version shipped, the compression-specific experiment described in A5's body
did not run. A6 partially done (#29) — production shares tested, threshold
move not. Items 1 (uncertainty bands in the app) and 2 (projection-basis
dropdown) are still not done.
