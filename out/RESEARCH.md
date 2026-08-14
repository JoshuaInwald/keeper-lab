# Prior art — how the fantasy analytics world does this

Reviewed 2026-08-13. What follows is where this project agrees with
established practice, where it departs, and what it's missing.

---

## 1. The method used here is the mainstream one, and it wins on the evidence

The dominant approach to converting projections into dollars is **Standings
Gain Points (SGP)**: work out how many units of a category buy one standings
place, convert every player's line into standings points, then convert points
to dollars. That is exactly the architecture built here.

FanGraphs ran a head-to-head test of **13 valuation systems** against 50 real
leagues, correlating each system's dollar values with the standings those
rosters actually produced ([The Great Valuation System Test: The Results](https://fantasy.fangraphs.com/the-great-valuation-system-test-the-results/)):

| rank | system | correlation |
|---|---|---|
| 1 | **SGP** (Schechter denominators) | 0.9697 |
| 2 | Todd Zola replacement-level | 0.9672 |
| 3 | z-scores | 0.9670 |
| 4 | ESPN Player Rater | 0.9663 |
| 13 | Razzball with 100% positional adjustment | 0.9453 |

**Two conclusions that bear directly on this project.**

First, the same SGP method with *different denominators* finished **seventh**.
Denominator choice matters more than method choice — which retroactively
justifies the time spent on the pooling problem in `LAB_NOTEBOOK.md` §1.

Second, systems with larger positional adjustments performed monotonically
**worse**. Razzball, who tested four theoretical stances, settled on no
adjustment at all and concluded position adjustments have "very close to zero
impact" ([Position Adjustments](https://razzball.com/position-adjustments/)).
This is directly relevant: external review flagged missing positional
replacement as a first-order gap in this model. The published evidence says
otherwise. Worth testing on league data before building it.

## 2. Where this project departs from standard practice — for the better

Every published method derives denominators from standings and then converts
points to dollars by **assuming** the league's budget divides across a fixed
player pool. This project instead **regresses realised production on prices
actually paid in this league** (n=677 purchases, 2022–26).

That is not something the commercial tools do, and it buys three things:

- **Waste is priced in.** Busts, injuries and never-played picks stay in the
  sample at the price paid, so the slope is what a dollar *actually* returned,
  not what it would return if everyone stayed healthy.
- **It is league-specific.** Generic calculators price a $260 10-team mixed
  league identically for everyone. This one knows *this* league overpays for
  nothing in particular and underpays for saves.
- **It measures drift.** The 2022→2026 decay from $4.12 to $10.20 per roto
  point would be invisible to any static calculator.

Tanner Bell's *Smart Fantasy Baseball*, the most careful public treatment,
makes a point that independently supports the pooling fix here: "the raw value
of the SGP isn't very important, but rather the **ratio** of the values"
([How to Analyze SGP Denominators](https://www.smartfantasybaseball.com/2016/01/how-to-analyze-sgp-denominators-from-different-sources/)).
Normalising each season by its own league mean before pooling is exactly that
insight applied to the instability problem.

## 3. The significant gap: auction inflation

This is the one place where standard practice has a well-developed tool that
this project was missing entirely.

In a keeper league, kept players are held below market value. The money that
would have bought them stays in the auction, chasing a thinner pool. The
standard correction ([RotoGraphs](https://fantasy.fangraphs.com/on-surplus-and-inflation-in-keeper-leagues/),
[RotoWire](https://www.rotowire.com/baseball/advice/keeper-inflation.php)):

```
inflation = remaining auction budget ÷ remaining player worth
```

**Applied to this league for 2027:**

| | |
|---|---|
| league cap | $2,600 |
| keeper salaries (optimal sets, 85 players) | $797 |
| keeper worth | $1,420 |
| **aggregate keeper surplus** | **$623** |
| remaining auction budget | $1,803 |
| remaining player worth | $1,180 |
| **inflation rate** | **1.528 → +52.8%** |

A player this model values at $20 should be expected to **cost about $31** at
the 2027 auction.

The accounting is sound and the direction matches the observed exchange-rate
decay. **What is not established is causation** — see `FINDINGS.md` §19. With
five seasons, keeper count and calendar time are collinear (time fits better,
r=0.987), so "rising keepers cause rising prices" is a plausible story the
data cannot confirm.

A baseline check that *does* hold: 2026 kept 100 players across 10 teams, 6-12
each, all inside the league's 6-13 rule. A 2027 recommendation of ~85 is
conservative against that. The 2022-25 keeper files showing 25-29 fail two
accounting identities and are incomplete (`FINDINGS.md` §19).

## 4. Tools that already exist, and what they don't do

| tool | what it does | what it doesn't |
|---|---|---|
| [FanGraphs Auction Calculator](https://fantasy.fangraphs.com/using-the-auction-calculator-in-2022-a-beginners-guide/) | z-score dollar values, configurable league settings, multiple projection systems | no keeper contracts, no league-specific price calibration |
| [RotoWire Custom Auction Values](https://www.rotowire.com/baseball/auction-values.php) | custom league settings, ATC projections, earned-value tables | same |
| [RotoWire Keeper Inflation Calculator](https://www.rotowire.com/baseball/101/inflation.htm) | the inflation formula above | single-year only, no valuation engine behind it |
| [FantasyPros Auction Calculator](https://www.fantasypros.com/mlb/auction-values/calculator.php) | consensus projections → dollars | same |
| Dynasty trade calculators (Dynatyze, FantasyTradeLab, The Dynasty Dugout) | multi-year player rankings, trade "grades" | opaque, rankings-based rather than category-based, no salary/contract modelling |
| [Smart Fantasy Baseball](https://www.smartfantasybaseball.com/create-your-own-rankings/) | the best public tutorial on rolling your own SGP | a teaching resource, not a tool |

**Nothing found does the combination this project does:** category-level
valuation calibrated to a single league's realised auction prices, multi-year
surplus against a specific contract structure, and a trade evaluator that
reports both current-season standings impact and future asset value.

The dynasty trade calculators are the closest commercial analogue and they are
markedly less rigorous — consensus rankings converted to arbitrary point
scales, with no salary dimension at all. In a salary-cap keeper league that
omits the single most important variable.

## 5. Ideas worth stealing

1. **Inflation-adjusted display** — show every value both "true" and
   "what it will actually cost". §3 above.
2. **Earned vs projected values** — RotoWire publishes end-of-season *earned*
   auction values alongside preseason projections. The `leaderboard_2026.csv`
   hindsight column is the same idea; making it a permanent side-by-side would
   turn it into a manager-evaluation tool.
3. **Tiers rather than point estimates** — RotoWire's auction tiers exist
   because a $2 gap between players ranked 40th and 45th is noise. Given the
   ±16% error bar here, tiering is more honest than a precise ranking.
4. **Relative denominators as a sanity check** — Bell's cross-source table of
   *relative* denominators (RBI and K normalised to 1.00) is a free external
   validation: if this league's ratios diverge wildly from fourteen other
   leagues', that is a signal to re-examine rather than celebrate.
5. **Test positional adjustment rather than assume it** — §1.

## Sources

- [The Great Valuation System Test: The Results — RotoGraphs](https://fantasy.fangraphs.com/the-great-valuation-system-test-the-results/)
- [The Great Valuation System Test: The Process — RotoGraphs](https://fantasy.fangraphs.com/the-great-valuation-system-test-the-process/)
- [On Surplus and Inflation in Keeper Leagues — RotoGraphs](https://fantasy.fangraphs.com/on-surplus-and-inflation-in-keeper-leagues/)
- [How To Account For Keeper Inflation In Your Auction Draft — RotoGraphs](https://fantasy.fangraphs.com/how-to-account-for-keeper-inflation-in-your-auction-draft/)
- [Calculating Keeper League Inflation — RotoWire](https://www.rotowire.com/baseball/advice/keeper-inflation.php)
- [How to Analyze SGP Denominators from Different Resources — Smart Fantasy Baseball](https://www.smartfantasybaseball.com/2016/01/how-to-analyze-sgp-denominators-from-different-sources/)
- [Using Standings Gain Points to Rank Players and Create Dollar Values — Smart Fantasy Baseball](https://www.smartfantasybaseball.com/e-book-using-standings-gain-points-to-rank-players-and-create-dollar-values/)
- [Position Adjustments — Razzball](https://razzball.com/position-adjustments/)
- [Category Values — Razzball](https://razzball.com/category-values/)
- [The Standings Gain Points Approach — Bat Flips and Nerds](https://batflipsandnerds.com/2019/03/16/fantasy-roto-the-standard-gains-points-approach/)
- [SGP Theory, Todd Zola — Mastersball](https://www.mastersball.com/products/SGP%20Theory%202010.pdf)
- [Using the Auction Calculator: A Beginner's Guide — RotoGraphs](https://fantasy.fangraphs.com/using-the-auction-calculator-in-2022-a-beginners-guide/)
- [Custom Auction Values — RotoWire](https://www.rotowire.com/baseball/auction-values.php)
- [Keeper Value Calculator — RotoWire](https://www.rotowire.com/baseball/101/inflation.htm)
- [Auction Values Calculator — FantasyPros](https://www.fantasypros.com/mlb/auction-values/calculator.php)


---

## 6. Blindspot review — what this design cannot see

A systematic pass over the model's structure, ordered by how much damage each
gap could do. Several are shared with every published system; two are specific
to this build.

### 6.1 It has no concept of a season as a sequence

Every quantity is a full-season total. Real rotisserie is played week to week:
you can trade a hot streak, stream a two-start pitcher, or bank saves before a
closer loses his job. **A player worth 6 roto points as a full season and a
player worth 6 delivered entirely in April are priced identically**, and the
second is worth more because you can sell him.

No published system models this either, so it is not a competitive
disadvantage — but it is a real gap, and it is the likeliest explanation for
why free agency supplies 40% of this league's production while the model
treats the wire as a flat replacement level.

### 6.2 Category *balance* is invisible

Roto points add up linearly, so the model says a team indifferent between 20
more home runs and 20 more strikeouts. In truth the value of a category unit
depends on where you sit in it: a team third in saves gains a lot from five
more, a team tenth by 40 gains nothing. **This is the single largest
conceptual gap between a valuation model and actual roto strategy**, and it is
why the trade evaluator's win-now lens re-ranks the standings rather than
adding roto points.

Fixing it properly means a team-specific marginal value per category, which
turns one dollar value per player into ten. Some serious auction players do
exactly this. It would be a genuine differentiator.

### 6.3 Everything is a point estimate — DONE, 2026-08-13/14

Bootstrap bands (resampling the team-seasons the denominators are fit on) now
ship `value_lo`/`value_hi`, `surplus_lo`/`surplus_hi`, and
`p_surplus_positive` for every rostered player, shown in the app drawer and
board. The Model tab also now shows each denominator's own standard error.
Still not what this section originally meant, though: this is uncertainty in
*how to score a stat line* from a small sample of team-seasons, propagated
through the pricing math — not the ZiPS P10-P90 *talent* distribution this
section actually asked for, which still goes unused. A player projected for
6.0 roto points with a wide ZiPS band and one with a narrow one are still
identical to the model. That specific gap is still open.

### 6.4 Replacement level is a single number — PARTIALLY DONE, 2026-08-14

Built for catcher and shortstop specifically once real per-position
eligibility data existed (`out/FINDINGS.md` #52), off by default. The
predicted outcome in §1 above held on this league's actual data, in an even
stronger form: Razzball's "very close to zero impact" undersold it — both
adjusted positions came out *deeper* than pooled here, not scarcer, so
turning the toggle on mostly *lowers* C/SS values rather than protecting
them. The full spectrum (1B/2B/3B/OF) is still one pooled number; no
eligibility data exists yet for those positions the way it now does for C/SS.

### 6.5 Aging is absent

The 2028 leg is raw ZiPS. There is no explicit age curve, so a 23-year-old and
a 34-year-old with identical projections carry identical multi-year value.
That is wrong in an obvious direction and matters for exactly the decisions
the tool exists to make.

### 6.6 The draft is modelled as a price, not a game

The exchange rate treats auction dollars as buying production at a rate. Real
auctions are strategic: nomination order, dollar-endgame dynamics, other
managers' remaining budgets. None of that is here.

### 6.7 Manager behaviour is exogenous

Inflation is taken as a fixed 1.53 when it is the equilibrium outcome of
everyone's keeper decisions — including the ones this model recommends. If the
tool works and its advice is followed, its own inflation estimate becomes
wrong. **A fixed point exists and is not solved for.**

### 6.8 Small-n runs through everything

30 team-seasons for most denominators, 17-20 for ERA/WHIP/SV (±34%), 5 auctions for the exchange rate
(split-halves disagreeing threefold), 38 closers for the saves finding, 5
seasons for the trend extrapolation. Every headline rests on tens, not
thousands. The model is careful about this in the sense that it measures and
reports the uncertainty; it is not careful in the sense of having enough data.

---

## 7. How the design compares to published systems

| dimension | this build | FanGraphs / RotoWire / FantasyPros | dynasty calculators | Smart Fantasy Baseball |
|---|---|---|---|---|
| valuation core | SGP | z-score or SGP | rankings → arbitrary points | SGP |
| denominators | pooled from **this league's** standings | generic or user-configured | none | own league or published tables |
| dollar conversion | **regression on realised prices paid** | budget ÷ pool assumption | none | budget ÷ pool assumption |
| waste (busts, injuries) | **in the sample at the price paid** | not modelled | not modelled | not modelled |
| keeper contracts | **multi-year, option-valued, extension priced** | none | qualitative tiers | inflation calculator only |
| free agents | **priced with live draft contracts** | not modelled | not modelled | not modelled |
| positional adjustment | toggle, off, evidence-backed | usually on | implicit | user's choice |
| uncertainty | measured and reported, not propagated | none shown | none | none |
| category balance | **not modelled** | not modelled | not modelled | not modelled |
| in-season sequence | **not modelled** | not modelled | not modelled | not modelled |

**Where this is genuinely ahead:** calibrating to realised prices in one
league, pricing waste, and treating contracts as multi-year options. FanGraphs'
13-system test found that SGP with the right denominators beats everything
else (r=0.9697) and that *denominator choice matters more than method choice* —
which is precisely the axis this build invests in.

**Where it is behind:** the commercial tools have vastly more data, real
projection pipelines, positional eligibility, and daily updates. They also
have interfaces.

**Where everyone is equally blind:** category balance and in-season sequence.
Those are the two places where a better model could beat the market rather
than match it.

---

## 8. What the evidence says to build next

Ranked by expected value, given that the published literature already tells us
where the returns are. Updated 2026-08-14 — two of the original five are done.

1. **Team-specific category values (§6.2). Still the top recommendation,
   unchanged.** Nothing else on this list changes a decision as much, and no
   competitor does it. Still not built.
2. ~~Uncertainty bands (§6.3).~~ **Done, 2026-08-13/14** — bootstrap bands on
   every rostered player's dollar value, plus denominator standard errors on
   the Model tab. The ZiPS P10-P90 *talent* distribution this item actually
   meant is still unused, though — see the caveat now in §6.3.
3. **Aging curves (§6.5).** Still not built — and now confirmed genuinely
   blocked, not just undone: no age/birthdate data exists in any file this
   project has access to (checked directly). Needs a fresh FanGraphs export
   with an age or debut-date column before this is even startable.
4. **Waiver-value counterfactual (§6.4).** Still blocked on transaction-date
   data that doesn't exist anywhere in this project's files.
5. ~~Positional replacement.~~ **Done for C/SS, 2026-08-14** (`out/FINDINGS.md`
   #52), off by default. The literature's "expect little" prediction held,
   in a stronger form than expected: both adjusted positions came out
   *deeper* than pooled on this league's real data, not scarcer. Full
   spectrum (1B/2B/3B/OF) still blocked on missing eligibility data, same
   shape of gap #52 just closed for two positions.

**New since this list was written, not from the original literature review:**
a probability-weighted range for a non-closing reliever's saves upside
(agreed direction, not yet built — see `out/ROADMAP.md`), and the same kind
of external validation this section is built from, but for a public $-value
system instead of ordinal rank (checked feasibility, held off — see
`out/FINDINGS.md`'s discussion the same day #52 shipped; not worth the
build for what it'd add on top of the existing CBS-rank correlation, #21).
