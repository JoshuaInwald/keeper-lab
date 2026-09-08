# Assessment phase: how much of this do we actually believe?

Written 2026-09-08 at the end of a build phase, for a fresh session that will do
nothing but assess. Read `CONSTRAINTS.md`, then this, then `docs/METHODS.md`
sections 4 and 5. Everything cited as `#nn` is `docs/FINDINGS.md`.

## What this phase is for

Twelve months of building produced a chain: a stat line becomes roto points,
roto points become dollars, dollars become a keep-or-cut call. Every link has
been validated against something. No one has ever asked how the errors compound,
or which link is load-bearing, or whether a link that passes its own test is
answering the right question.

That is this phase. **The deliverable is a judgment, not a commit.**

### Ground rules

- **Change no constant and no formula.** If the assessment concludes something
  should change, write it down with the evidence and the expected flip count;
  the change is a later session's deliverable. The one exception is a
  demonstrable bug, which follows the usual before/after board diff.
- Anything asserted as a finding goes through leave-one-season-out or split-half
  first. #7 is the cautionary tale: a single-season exchange rate that looked
  fine and was not identified.
- Distinguish three things that get conflated: **the model is wrong**, **the
  model is right and the data is thin**, and **the model answers a different
  question than the one being asked of it**. The third is the most common
  failure here and the hardest to see.

## The chain, link by link

Confidence below is a claim about evidence, not a feeling. Each says what would
move it.

### Link 1. Stat line for 2027 (`project.py`)

Blend of 2026 actuals with ZiPS 2027, mixed at the rate x playing-time level,
weighted by per-category reliability. METHODS 2.3.

**Validated:** the reliability table refits on every test run and reproduces 10
of 10 values (#28). Ordering agrees with three external systems at Spearman
0.85-0.89 (#21, #54). The age effect embedded in it is empirically correct:
the engine applies +0.621 roto points to under-25s where measured persistence
says +0.778, indistinguishable (#59).

**Not validated, and this is the weak point:** the blend weights themselves.
`BLEND_W_2026 = 0.50`, `PT_BLEND_CAP_HITTER = 0.30`, `PT_BLEND_CAP_PITCHER =
0.15`, `PT_BLEND_CAP_PITCHER_EXCEEDED = 0.40` are judgment calls (METHODS
section 3 #9 says so outright: "caps are judgment, not fitted"). They cannot be
backtested, because backtesting needs historical ZiPS archives and `data/` has
only the 2027 and 2028 pulls. **Confidence: moderate on ordering, low on the
weights.**

**What would move it:** historical ZiPS or Steamer archives, even two seasons.
Then the blend is a fitted quantity rather than four numbers someone chose.
Worth asking whether FanGraphs' archives or a saved export exists before
concluding it is impossible.

### Link 2. Roto points from a stat line (`denoms.py`)

Units per standings point, per category, from pooled relative dispersion over
2024-26.

**Validated:** sensitivity is measured (#6: 10 flips for the window choice, 5
for the saves-punter rule, 0 for most others). Bootstrap error bars exist
(±34% per denominator, #30, and note #30 is itself a retraction of bands
computed around the wrong point).

**Weak:** n = 10 teams x 3 seasons. The saves-punter exclusion is named in
METHODS section 5 as "the single largest lever; every closer valuation rests on
it" and rests on dropping teams under 15 saves (judgment call #4). **Confidence:
moderate.**

**This is where Josh's "each category is distributed differently" question
lands, and it is half-answered.** Denominators already give each category its
own units-per-point, so per-category *dispersion* is handled. What is not
handled is that the categories are not independent and not equally contestable,
and a per-team correction for exactly that was built, measured and rejected:
per-team multipliers swing 0.29x to 13.28x within a season and persist across
seasons at **-0.07** (#60). Category *rank* persists at +0.25, and only in K,
SB, R, AVG and SV. Re-examine whether the right object was tested.

### Link 3. Roto points to dollars (`board.py`)

Two scales. `production_value` normalises the top 230 to $2,600.
`keep_value` inverts the auction regression at $10.00 per point.

**This is the least defensible link and it should get the most attention.**

- The auction regression is `roto_points ~ salary` with **R^2 = 0.156**, and
  `keep_value` inverts it. Judgment call #5 defends regressing production on
  price rather than the reverse, on attenuation grounds. Inverting a
  relationship that explains 16% of the variance is a strong operation and the
  ROADMAP's own diagnosis says it inflates $/point by roughly 1/R^2.
- The consequence is visible: `keep_value` totals **$4,778** across 276 rostered
  players against a league cap of $2,600 (#57.6). METHODS calls the excess "the
  aggregate keeper discount". Is it, or is it inversion inflation? Nobody has
  separated those.
- Single-season exchange rates are not identified: 2026's split halves give
  $6.55 and $20.38 (#7).
- Replacement level is contested and moves on every refresh (4.599, 4.733,
  4.811 in one day). Four routes now exist and two of them point in opposite
  directions (#62): observed waiver churn says ~4.4, the internal-consistency
  count says ~5.0.

**Confidence: low on levels, high on ordering.** The project has always said
"rankings solid, levels approximate" (#7). The assessment should decide whether
that caveat is doing enough work, given every keep/cut call is a level
comparison against a salary.

**Josh's waiver-wire question is exactly this link**, and #62 is the whole state
of play: churn margin 4.12-4.39, engine 4.733, and at 4.381 the model would
claim 106 unrostered players beat replacement, which a freely-available level
cannot mean.

### Link 4. What owners will actually pay (`price.py`)

Fitted on 677 revealed purchases from ex-ante features only.

**Validated properly, and it is the best-tested link:** fit 2023-25, predict
2026. MAE $5.76 against $6.84 for prior-salary-plus-trend and $7.20 for the comp
estimator. Specification chosen by leave-one-season-out inside the training
seasons, never on the test season. Two design errors were caught by the held-out
season and are documented rather than quietly fixed (#56.7).

**Weak:** in-sample R^2 is 0.375, so roughly 60% of price variance is
unexplained, and the ROADMAP predicted that ceiling. The top end needs a hard
cap; three mechanisms for removing it were tried and all trade top-end accuracy
for top-end safety (#62.5). The band over-covers at 68.8% against a nominal 60%
(#63). **Confidence: good, with a known and stated ceiling.**

### Link 5. What owners actually keep (`keeper_revealed.py`)

`P(kept)` on 134 reconstructed 2026 decisions. Pseudo R^2 0.169.

**Validated:** labels are reconstructed from auction reappearance plus the
keeper file plus roster contract codes, and the two kept-sources agree on 31 of
35 with zero contradictions (#56.4). This also settled a question the roadmap
said to ask the commissioner: `keepers_2025.csv` shares zero players with the
2024 auction class, so those files are not keeper submissions.

**Weak:** n = 134 from one season. Pre-2026 reconstructions carry a selection
bias (kept is only detectable when the player was LATER thrown back). The
`years_control_left` coefficient is negative, which is backwards, and is a known
artifact of how the eligible set is built (#56.5); it is frozen at its mean in
the comparison rather than fixed. **Confidence: moderate, and it is the newest
and least stress-tested link.**

## Josh's questions, mapped

| question | where it stands | what is missing |
|---|---|---|
| confidence in production to roto points | Link 1 + 2 above | the blend weights have never been fitted |
| are we right about waiver-wire talent | #62, unresolved and contested | transaction data with dates |
| does a single points-to-dollars number make sense given per-category dynamics | #60 rejected the per-team version; per-category dispersion IS handled by denominators | whether the right object was tested; category correlations are unexamined |
| owners' real auction tendencies | #56, #57, best-tested link | 60% of variance unexplained |
| who was kept vs let go, and how they turned out | **not built** (see below) | this is the highest-value unbuilt analysis |

### The unbuilt analysis Josh named, scoped

> "who was kept in past year auctions vs who was let go for their salary and how
> those players ended up doing (ie in production, was their redraft price lower
> or higher than the amount the owner declined to pay to keep)"

This is a **decision-quality audit**, and it is the one analysis that scores the
owners rather than the model. Everything needed exists:

- `out/keeper_decisions.csv` already holds kept / thrown-back with the salary at
  stake, for 2026 (clean labels, n=134) and 2023-25 (reconstructed, n=202,
  selection-biased, and say so).
- `auction.score_season()` gives what each player then produced, on that
  season's own scale.
- `out/price_features.csv` gives what the market paid for the ones who went
  back into the auction, which is the counterfactual price of the same player.

The clean design: for every player thrown back at salary S, compare S against
(a) what he was re-bought for, and (b) what he then produced in dollars. For
every player kept at S, the same. That yields a per-decision surplus and a
league-wide hit rate, and it answers "are owners good at this" with the league's
own data. It also produces the first honest test of whether the model's keep/cut
advice would have beaten the owners', which is the thing the whole project is
for and has never been measured.

**Caveat to state up front:** realised production is a noisy scorer of a decision
made ex ante. A thrown-back player who then got hurt does not prove the owner
right. Report the ex-ante expectation and the realised outcome separately.

## The outside-analyst lens

Josh asked how a Ben Clemens or Dan Szymborski would come at this. The useful
version of that is not style, it is the objections such a reader would raise
first. Anticipate these:

1. **"You inverted a regression with an R^2 of 0.16."** Link 3. The strongest
   methodological objection available and it is not currently answered.
2. **"Your replacement level is a choice, not a measurement, and it moves your
   whole scale."** #62 already shows two defensible routes disagreeing.
3. **"SGP versus z-scores."** This project is standings-gain-points by
   construction. #18 ran z-scores as an independent check and got Spearman 0.855
   against the engine's own 0.842, but the two have never been reconciled as
   competing frameworks, which is a live debate in the public fantasy literature.
4. **"Roto categories are correlated and you add them linearly."** Power and
   average trade off; strikeouts and ERA co-move. Never examined here. #60
   killed the per-team version but not the correlation question.
5. **"n = 10 teams and 5 seasons."** True of everything. The honest response is
   the sensitivity work (#6) and the bootstrap bands, and the honest admission
   is that several constants rest on 17-30 team-seasons.
6. **"Where is the out-of-sample test of the thing you actually sell?"** Price
   has one (#56). Keep/cut advice does not. That is the audit scoped above.

Comparing against published work is legitimate and mostly unavailable offline:
`data/` has no external benchmark beyond the FanGraphs ROS calculator already
used in #54. Treat "what do other analysts find" as a research question needing
sources, not something to assert from memory.

## What NOT to spend the session on

- Rebuilding per-team category multipliers. Measured, rejected, implementation
  preserved in `klab/teamvalue.py` (#60).
- Removing the role cap. Three mechanisms, same trade-off (#62.5).
- An aging curve on the projection. Vindicated as unnecessary (#59).
- Promoting `keep_2027_market`. It keeps 104 including 30 below replacement and
  cuts Skubal (#57.5).

## Orientation

- Constants: `out/model_params.json`. Currently replacement 4.733, $/rp redraft
  6.522, $/rp keep 10.003, auction regression R^2 0.156 on n=404.
- Everything the model says, per player: `out/valuation_comparison.csv` (five
  dollar figures side by side) and `out/keeper_board_2027.csv`.
- Decisions: `out/keeper_decisions.csv`. Purchases with ex-ante features:
  `out/price_features.csv`.
- Recipes: `docs/WORKFLOWS.md`. Never hand-calculate a value (CONSTRAINTS.md).
- Rebuild: `PYTHONPATH=.:scripts python3 scripts/run_all.py` (~3 s). Tests:
  `PYTHONPATH=. python3 -m pytest tests/ -q` (64, ~2.5 min).
