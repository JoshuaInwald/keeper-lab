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

### Two phases, in this order, and do not blend them

**Phase A: assess. Change nothing.** Work out what is true. Every claim goes
through leave-one-season-out or split-half. The output is a ranked list of
findings, each with its evidence, the constant or formula it implicates, and the
expected keep/cut flip count if acted on. A demonstrable BUG is the only thing
that may be fixed during Phase A, and it follows the usual before/after board
diff.

**Phase B: act on what Phase A confirmed, one change at a time.** Same session
is fine. Per change: record the board to CSV, make the change, diff, report the
flips in keep/cut calls rather than correlations, write the `docs/FINDINGS.md`
entry with before/after numbers, commit. Never act on something Phase A did not
confirm, and never batch two changes into one diff.

The reason for the split is on the record. `docs/FINDINGS.md` carries four
retractions (#16, #19, #30, #55) and the common thread is concluding and acting
in one motion, so the error shipped with the conclusion. Phase A is what makes
Phase B safe rather than a constraint on it.

**A likely Phase B queue, if Phase A confirms these** (do not treat as
pre-approved; each needs its own case made):

1. The hitter/pitcher budget split, and whether the top-230 pool should be
   constrained by roster slots (140 hitters, 90 pitchers) rather than taken as
   the top 230 by roto points regardless of role. See the published-practice
   section. Touches every dollar figure, so it goes first or not at all.
2. `WAIVER_VALUE`, which is a live one-line question with evidence pointing both
   ways (#62). Needs a tiebreaker, not another measurement of the same two things.
3. Whether `keep_value`'s inverted regression should survive in its current form
   given R^2 = 0.156 (Link 3).
4. Anything the decision audit shows the model would have gotten wrong.
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
| who was kept vs let go, and how they turned out | **not built**; `scripts/decision_audit.py` is scaffolded and runnable | interpretation, and the ex-ante versus realised split |
| does one dollar scale work across hitters and pitchers | **new lead, measured**: model splits 73.7/26.3, the league spends 64/36 | see the published-practice section |

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

`data/` has no external benchmark beyond the FanGraphs ROS calculator used in
#54, so the comparison below was researched on 2026-09-08 and is sourced. Do not
extend it from memory: confident-sounding recall of public fantasy research is
the most likely place for a fresh session to invent something.

## Where this project sits against published practice (researched 2026-09-08)

### The core architecture is the one that wins the public bake-off

RotoGraphs ran 13 valuation systems against 50 completed leagues, correlating
each system's dollar values against teams' actual final standings points. SGP
with league-specific denominators finished first (r = 0.9697, R^2 = 0.9403),
ahead of Todd Zola's REP method (0.9672) and z-scores (0.9670); the whole field
spanned 0.9453 to 0.9697. The stated conclusion was that "the denominators you
choose when employing the SGP method are extremely important".

This project is SGP with denominators fit to its own league's standings, which
is precisely the winning configuration. That is real external support for the
architecture, and it also sharpens where the risk actually lives: not in the
method but in the denominators, which here rest on 10 teams x 3 seasons and
carry +/-34% bootstrap bands (#30).

It also reframes objection 3 in the list above. SGP and z-scores land within
0.003 of each other in that test, so the SGP-versus-z-score debate is not where
the uncertainty is. #18's z-score cross-check (0.855 against the engine's 0.842)
is consistent with that and can be treated as settled rather than reopened.

### The dollar formula is the standard one, character for character

Smart Fantasy Baseball's published formula is `([TOTAL SGP] - [REPLACEMENT LEVEL
SGP]) * $ PER USEFUL SGP + $1`. `board.value_players()` computes
`(rp - replacement_rp) * usd_per_rp + 1.0`. Same object. The $1 floor is
convention, not an invention here.

That source also stresses updating replacement level as the player pool changes,
which is the instability #62 documents rather than a defect unique to this
league.

### The one place this project diverges from standard practice, and it is measurable

Standard SGP practice splits the budget into a hitting pool and a pitching pool
before converting to dollars, commonly 65-35 or 70-30 in favour of hitters.
Smart Fantasy Baseball argues hitter and pitcher SGP are **not** directly
comparable and that pooling them on one scale silently imposes a 50-50 split.

**This project pools them.** One `usd_per_rp` covers everyone. Measured on the
current build:

| | share of the $2,600 |
|---|---|
| model's implied split (top-230 `production_value`) | **73.7% hitters / 26.3% pitchers** |
| this league's actual auction spend, 2022-2026 | 62% / 38%, 64/36, 65/35, 62/38, 68/32 |

The model allocates about 10 points more to hitters than the league actually
spends. And the composition is stranger than the split: the top 230 by roto
points contains **183 hitters and 47 pitchers**, while the league must roster
140 hitters and 90 pitchers. The budget identity is being satisfied by a pool
teams cannot legally field, so pitchers are priced against 47 slots when 90
exist. Note that `POSITION_SLOTS` was a config knob removed as unused in the
2026-09-07 compaction pass; the roster constraint it implies has never bound.

This is the strongest single lead in the brief. It is measurable, it has a
public methodological literature behind it, it plausibly explains why the
role interaction in the price model is so large (pitchers paid roughly half the
per-point rate of hitters, #56.6), and it is upstream of every dollar figure.
Whether the fix is a budget split, a roster-slot constraint on the pool, or
separate hitter and pitcher replacement levels is exactly what an assessment
should work out.

### On keeper decisions specifically

RotoGraphs' "Looking beyond surplus value for keeper decisions" argues that
value-minus-salary is insufficient on its own, and that the missing axes are
roster construction, positional scarcity, and the opportunity cost of the roster
spot. That is independent confirmation of what #57.5 found the hard way: pricing
a keeper decision on transaction arbitrage alone keeps replacement-level players
because it never asks what else the spot could hold.

Inflation-adjusting the value side before comparing to salary is standard
practice in keeper leagues (a $28 player at 15% inflation is worth $32 against
his salary). `api._inflation()` computes the league's rate; whether it is applied
consistently at the decision margin is worth checking.

Sources: [The Great Valuation System Test: The Results](https://fantasy.fangraphs.com/the-great-valuation-system-test-the-results/),
[The Great Valuation System Test: The Process](https://fantasy.fangraphs.com/the-great-valuation-system-test-the-process/),
[Are Hitter SGPs Directly Comparable to Pitcher SGPs?](https://www.smartfantasybaseball.com/2014/12/are-hitter-sgps-directly-comparable-to-pitcher-sgps/),
[How To Use SGP To Rank and Value Players During the Season, Part 6: Adjust Replacement Level](https://www.smartfantasybaseball.com/2014/05/how-to-use-sgp-to-rank-and-value-players-during-the-season-part-6-adjust-replacement-level/),
[Automated SGP Rankings and Dollar Values](https://www.smartfantasybaseball.com/2019/01/new-excel-tool-automated-sgp-rankings-and-dollar-values/),
[Looking beyond surplus value for keeper decisions](https://fantasy.fangraphs.com/looking-beyond-surplus-value-for-keeper-decisions/),
[On Surplus and Inflation in Keeper Leagues](https://fantasy.fangraphs.com/on-surplus-and-inflation-in-keeper-leagues/),
[Creating Your Rankings? Start with Z-Scores](https://fantasy.fangraphs.com/creating-your-rankings-start-with-z-scores/).

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
