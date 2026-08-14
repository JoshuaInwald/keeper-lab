# Lab Notebook — what was tried, what failed, and why the code looks like this

Read this before changing a modelling decision. Most of the obvious
alternatives were tried and rejected for reasons that are not obvious.

<details>
<summary><strong>Contents</strong> (19 sections — click to expand)</summary>

1. [Denominators: four estimators tried, all unstable, fixed by pooling](#1-denominators-four-estimators-tried-all-unstable-fixed-by-pooling)
2. [Contract codes: the correction, and how it was established](#2-contract-codes-the-correction-and-how-it-was-established)
3. [Projections: three things that had to be right](#3-projections-three-things-that-had-to-be-right)
4. [Bugs found and fixed (in order of severity)](#4-bugs-found-and-fixed-in-order-of-severity)
5. [Open forks — the things a sensitivity analysis needs to test](#5-open-forks--the-things-a-sensitivity-analysis-needs-to-test)
6. [Things deliberately not done](#6-things-deliberately-not-done)
7. [External review (2026-08-13) — what it found and what changed](#7-external-review-2026-08-13--what-it-found-and-what-changed)
   - [Building the interface (session 5)](#building-the-interface-session-5)
8. [Publishing to GitHub (2026-08-13) — two false alarms, one real gap](#8-publishing-to-github-2026-08-13--two-false-alarms-one-real-gap)
9. [Rejected: "re-drafted players get a fresh 3-year clock"](#9-rejected-re-drafted-players-get-a-fresh-3-year-clock-2026-08-13)
10. [The partial-season exclusion rule generalized from 5 of 10 categories](#10-the-partial-season-exclusion-rule-generalized-from-5-of-10-categories-2026-08-13)
11. [Rejected: median of the full free-agent pool as a survivorship-free replacement estimate](#11-rejected-median-of-the-full-free-agent-pool-as-a-survivorship-free-replacement-estimate-2026-08-13)
12. [BB and H reliability were copy-pasted from WHIP](#12-bb-and-h-reliability-were-copy-pasted-from-whip-2026-08-13)
13. [Fixing #26 didn't fix all of #26](#13-fixing-26-didnt-fix-all-of-26-2026-08-13)
14. [Extension eligibility applied to the wrong contract codes — caught by Josh, not by review](#14-extension-eligibility-applied-to-the-wrong-contract-codes--caught-by-josh-not-by-review-2026-08-13)
15. [Building the auction-price estimator: two forks tried and rejected in the regression itself](#15-building-the-auction-price-estimator-two-forks-tried-and-rejected-in-the-regression-itself)
16. [I repeated a stale claim from out/ROADMAP.md without checking the code first](#16-i-repeated-a-stale-claim-from-outroadmapmd-without-checking-the-code-first-2026-08-13)
17. [The app's self-test reference trade broke the moment a real trade happened](#17-the-apps-self-test-reference-trade-broke-the-moment-a-real-trade-happened-2026-08-13)
18. [F was never actually extendable right now, and #33 didn't catch it](#18-f-was-never-actually-extendable-right-now-and-33-didnt-catch-it-2026-08-13)
19. [Building the trade finder: a bad suggestion that looked good on paper](#19-building-the-trade-finder-a-bad-suggestion-that-looked-good-on-paper-2026-08-13)

</details>

---

## 1. Denominators: four estimators tried, all unstable, fixed by pooling

**The problem.** A denominator is how many units of a category buy one
standings point. The textbook estimator is `(max − min)/(N − 1)`. In a
10-team league that is determined by **two** of ten observations, and it
swings violently:

| category | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| HR (range est.) | 11.9 | 11.0 | 21.1 | 12.7 |
| R | 24.1 | 27.9 | 62.1 | 24.7 |
| ERA | .183 | .076 | .049 | .044 |

**Estimators tried,** mean coefficient of variation across 2022–25:

| estimator | mean CV |
|---|---|
| median gap | 0.346 |
| sd-based (`sd × 3.078/9`) | 0.369 |
| range | 0.386 |
| slope (regress standings points on stat total) | 0.394 |
| IQR-based | 0.418 |
| trimmed range | 0.450 |

**None of them helped.** The instability is in the data, not the estimator —
IQR and trimmed range were *worse*, because throwing away observations in an
n=10 sample costs more than the outlier robustness buys.

**Does it matter?** Yes. Scoring the same 2025 players under different years'
denominators gives Spearman correlations of 0.72–0.96 against each other. Not
innocuous.

**The fix that worked.** Divide each season's team totals by that season's
league mean, then pool the normalised values across seasons. σ is estimated
off 20–40 team-seasons instead of 10, and level shifts (the 2023 stolen-base
rule change, run-environment drift) wash out because everything is relative.
Denominators for a target year are `σ_rel × that year's league level × 3.078/9`.
The constant 3.078 is E[range] for a normal sample of 10.

**Window choice: 2024–25 only** (Josh's call). There is a genuine regime break
in rate-category dispersion: ERA σ_rel runs 13.8%, 5.5% in 2022–23 against
3.7%, 3.5% in 2024–25. Roster volume rose too (team IP 1176 → 1445), but that
mechanically explains only ~1.1× of a 3.7× drop. The league got sharper.

**Cross-check that failed to discriminate.** I hoped auction-regression R²
would pick the window empirically (better denominators → prices explain
production better). It doesn't: R² is 0.253 vs 0.217 across windows, and the
comparison is confounded because the wider window also changes the sample.

---

## 2. Contract codes: the correction, and how it was established

The original handoff read code `2` as *one* more year and treated `3` as a
final year. Both wrong. The code is **seasons remaining after the current
one**. Three independent tells in `contracts_parsed.csv`:

1. `$10` and `$20` salaries — exactly the pre- and post-All-Star-break FA
   acquisition prices — cluster almost entirely in code `2`. Those are 2026
   in-season pickups, and a 3-year deal signed in 2026 leaves 2027 and 2028.
2. Code `F` holds the big **2024** auction prices: Judge $39, Witt $39,
   Tucker $33, Tatis $34, Devers $30. 2024 + 3 years → final year is 2026.
3. Only Skubal ($38) and Cal Raleigh ($16) carry `3`, which fits the +$5/yr
   extension having been exercised, and does not fit `3` meaning a final year.

Cost of the error: every multi-year contract understated by a season, and
code-`3` players charged a $5 extension fee they don't owe.

---

## 3. Projections: three things that had to be right

### 3.1 Blend at rate × playing time, never on counting stats

ZiPS applies a player-specific durability haircut — it gives Álvarez 474 PA
and Witt 656. Averaging a player's *counting* line against a healthy 2026
applies that haircut twice and buries him. This is what produced the prior
session's "Yordán Álvarez is worth $4". Rates and playing time are blended
separately.

### 3.2 Weight each stat by its reliability, not 50/50 across the board

The 2026 leg is raw observed performance; ZiPS is already regressed. Giving
both 50% weight injects noise wherever a stat doesn't repeat. Measured
year-over-year reliability on this dataset:

| stat | r | | stat | r |
|---|---|---|---|---|
| SB/PA | 0.739 | | K/IP | 0.701 |
| HR/PA | 0.607 | | WHIP | 0.237 |
| AVG | 0.436 | | ERA | 0.176 |
| R/PA | 0.425 | | **W/IP** | **0.151** |
| RBI/PA | 0.380 | | | |

(hitters 250+ PA in consecutive years, n=693; pitchers 40+ IP, n=785)

**Wins are essentially noise.** Carrying a pitcher's observed win rate forward
buried Christian Scott, who went 3–17 on a bad team despite a 3.27 FIP and
11.3 K/9. Each stat's weight on the 2026 leg is now scaled by its reliability
relative to the most repeatable stat.

### 3.3 Saves need their own model — ZiPS has no SV column at all

Both the 2027 and 2028 ZiPS exports have SV entirely null. Fitted
`SV_next = 0.51 + 0.652 × SV` (R²=0.43, n=1,637).

**Failed first attempt:** fitting only on pitchers with SV ≥ 10 gave
`5.01 + 0.534 × SV` (R²=0.14) — an intercept that hands five phantom saves to
every mop-up arm in baseball. Fitting across all pitchers with a real workload
fixes the intercept. It is also switched off for starters. Total projected
2027 saves: 1,271 against an MLB actual of roughly 1,250.

### 3.4 Full-season playing time for keeper decisions

Nobody keeps a part-time player, so keeper value holds rates fixed and scales
playing time to 600 PA / 150 IP / 25 SV, capped at 2× extrapolation.

**Interaction bug this created — and the wrong fix.** Scaling *everyone* to
full time raises replacement level and compresses every value (Julio Rodríguez
fell $24.1 → $20.0). I "fixed" it by calibrating replacement on unscaled
projections while valuing keepers at full time. **That was wrong** and broke
the budget identity badly; see §7.1 for what external review found and how it
was actually resolved. The compression was not a bug: if every keeper gets a
full season, so does every alternative.

**Second interaction bug:** Ohtani collected both the 600 PA and the 150 IP
floor, lifting his arm from 97 to 150 IP and adding $20 of value from a
workload nobody expects. Two-way players are now scaled on their bat only.

---

## 4. Bugs found and fixed (in order of severity)

1. **Standings ranks inverted.** `rank(ascending=False)` gave the biggest HR
   total 1 point instead of 10. Caught only because Josh mentioned Pookie 2.0
   was leading and the model had them last. Every category was backwards.
2. **Closer test selected on the outcome.** The first version of the
   saves-mispricing test classified closers by *realized* saves, which
   guarantees a positive residual. Redone with prior-season saves, a
   pre-draft observable. The finding survived (see `FINDINGS.md` §1).
3. **Elite-convexity claim, asserted then retracted.** I claimed elite players
   were undervalued by the linear dollar scale, citing the $31+ price bucket
   regressing at $19.68/roto point vs $7.64 pooled. That was a within-bucket
   slope on restricted range with R²=0.004 — noise. The proper test is a
   quadratic term on the full sample: coefficient −0.00001, **t = −0.01**.
   There is no convexity. Two downstream claims were wrong and were retracted.
4. **Negative player values.** Unfloored, the model called an injured $10
   prospect a −$38 liability. A player cannot be a negative asset: a bad arm
   gets benched and the roster spot reverts to a waiver pickup. Values floor
   at $0, so the true downside is the salary you declined to stop paying.
5. **Pitchers appearing as two-way players.** The FanGraphs hitter export
   carries a zero-PA row for every pitcher, so every starter was tagged `TWO`.
   Filtered at 20 PA / 5 IP.
6. **Ohtani double-counted** in the leaderboard — he has two rows in
   `contracts_parsed.csv` (batter and pitcher) sharing one FanGraphs id.
7. **Minor-league FanGraphs ids** (`sa3020472`) broke integer casts.

---

## 5. Open forks — the things a sensitivity analysis needs to test

Each of these is a defensible choice that materially moves numbers. None has
been stress-tested.

| fork | current choice | alternative | expected impact |
|---|---|---|---|
| SV punter exclusion | drop teams < 15 SV | include all 10 | roughly halves closer value |
| denominator window | 2024–25 | pooled 2022–25 | shifts ace SP vs slugger balance ~2× on ERA |
| exchange-rate window | 2024–26 | pooled 2022–26 | $7.64 vs $5.84 per point, i.e. all values ±30% |
| blend weights | reliability-scaled | flat 50/50 | moves noisy-stat players (W-dependent SPs) |
| PT floor | 600/150/25, cap 2× | no floor | part-time and breakout players |
| future discount | 0.85/yr | 1.0 or 0.7 | multi-year contract rankings |

---

## 6. Things deliberately not done

- **Reverse regression `E[$ | roto points]` for pricing.** Tried; useless.
  Realized production is a noisy proxy for the talent the market priced, so
  the attenuation is severe — it claims Ohtani is worth $23. The forward
  direction `E[production | $]` is the right one because price is measured
  without error.
- **DuckDB and Streamlit.** In the original plan; deferred. Plain pandas is
  fast enough at this data size and easier to audit.
- **Low R² panic.** The auction regression sits at R² ≈ 0.14. That is expected
  and not a defect: it estimates `E[production | price]`, and noise in the
  dependent variable does not bias the slope.

---

## 7. External review (2026-08-13) — what it found and what changed

An independent model reviewed the code and docs cold, with no access to the
build conversation. Its top findings, all reproduced before acting:

### 7.1 The dollar scale was calibrated on one pool and applied to another

Replacement level and $/roto-point were computed from **unscaled** projections
and then applied to **full-time-scaled** roto points. The stated budget
identity was therefore false in the shipped numbers: the top 230 summed to
**$3,854**, not $2,600. 146 of the top 230 carried a playing-time scale-up
(mean 1.42×), so most of the board was priced at a counterfactual workload
against a replacement level built from real, injury-shortened seasons.
Recalibrating consistently flipped **42 of 107 keeper flags**.

§3.4 above had treated the resulting value compression as a bug ("Julio fell
$24.1 → $20.0 for no real reason"). There was a reason: if every keeper is
credited a full season, so is every alternative, and replacement really does
rise. That paragraph was wrong.

**Resolution (Josh's call): report both.** The headline `redraft_value` and
`keep_value` now use expected playing time with a scale calibrated on the same
pool — the identity holds at exactly $2,600. `redraft_value_ft` and
`upside_ft` carry the full-season counterfactual as separate columns, so a
breakout like DeLauter still shows his $10 upside without distorting the price
scale everyone else is measured against.

### 7.2 The extension option was ignored for every contract except `F`

Any contract reaching its final year can be extended at salary + $5. The code
modelled that for `F` players but gave code-1 players exactly one year, making
them rentals. They are not: a code-1 player is one year at salary plus a call
option on a second. Jhoan Duran at $4 was understated by roughly $25; Skenes,
Cade Smith and Zach Neto by $7–21. Now priced as an option, clipped at zero
so it is only exercised when worth exercising.

### 7.3 The range constant ignored the actual field size

`denominators_for_level` always applied `c_n = 3.078` (E[range] for n=10). But
after save-punters are dropped the SV field is 8 or 9 teams, where the correct
constants are 2.847 and 2.970 over a smaller divisor. **Every save was
overvalued by 19%.** The SV denominator moves 5.53 → 6.57, and the headline
saves finding drops from +2.67 to +2.23.

### 7.4 The saves and draft-chain findings were both overstated

- Saves: with punters *included*, the effect is +0.92, t=1.82 — not
  significant. The earlier claim that inclusion "roughly halves" it was wrong;
  it removes two-thirds and all significance. `FINDINGS.md` §1 now presents
  the result as conditional.
- Draft chain: non-closer residuals are **flat** across price bands, the
  bucket gradient is largely the arithmetic identity
  `usd_per_rp × slope − 1` plus the $0 floor's Jensen lift (~40% of the
  spread), median surplus is negative in every bucket, and the top bucket
  flips sign by era. `FINDINGS.md` §2 was rewritten.

### 7.5 ZiPS 2027 double-count: refuted, worry closed

Regressing ZiPS-2027 rates on prior observed rates gives loadings of **0.45 on
2025, 0.23 on 2024, and only 0.107 on 2026-to-date** (same pattern for K/IP).
If 2026 were inside ZiPS's window as the most recent season its coefficient
would dominate, not sit at a quarter of 2025's; partial-season attenuation
(~12%) cannot explain the gap. ZiPS 2027 is substantively a through-2025
projection, so the 50% weight on the 2026 leg is doing real work rather than
double-counting.

### 7.6 Smaller bugs fixed

- `value_2028` re-introduced the two-way scaling bug fixed one function
  earlier, and was also full-time scaling the out year while 2027 had moved to
  expected PT — it now does neither.
- `project_2028` passed `reliever=True` for every pitcher, handing each
  starter the 0.51-save intercept.
- `trade.py` read `res.get("usd_per_point", 7.6)` where the key never existed,
  so the win-now verdict always used the hardcoded fallback. Now a parameter.
- `score_season` aggregated `role` with `"last"`, tagging any hitter who threw
  an inning as a pitcher. Fixing it naively broke the other way — the hitter
  export carries zero-PA rows for every pitcher — so both frames are now
  filtered to real playing time before scoring.
- `SEASON_FRACTION_2026` was a dead knob; removed.

### 7.7 Verified as sound — stop re-litigating

Pooled relative dispersion is valid inside the 2024–25 window (team AB 7,629
vs 7,798; IP 1,445 vs 1,409 — no volume drift). Empirical range/sd ratios run
2.9–3.3 against the normal-theory 3.078. The forward regression plus inversion
is the right construction for replacement cost, and rejecting the reverse
regression (§6) was correct. The convexity retraction was correct, confirmed
independently by flat residuals across price bands. The name resolver is clean
— all 5 fuzzy matches correct, and the 6 unmatched are genuine zero-production
buys. The draft files contain no embedded keeper contracts. Contract-code
semantics check out.

**The honest error bar** from fitting dispersion on n=20 team-seasons is about
**±16% per category** — wider than most of the knobs being debated, and it
should be printed next to every dollar figure.

### 7.8 Still open

**Positional replacement is missing entirely.** Replacement is the 230th
player overall with no positional adjustment. A replacement catcher or middle
infielder is far worse than the 230th-best player, so scarce-position keepers
are systematically undervalued against OF/1B. Standard first-order term in
auction valuation. Not yet implemented.

---

## Building the interface (session 5)

**Streamlit was the plan and it was wrong.** The roadmap called for Streamlit
across 3–4 sessions. Streamlit needs a live Python process, which means the
tool exists only at the desk where the repo is checked out — useless at a draft
table, unusable on a phone, and un-sharable without asking someone to install
things. The build target became one self-contained HTML file with the data
inlined. It cost one session instead of four and it is strictly more portable.

The tradeoff is real and worth stating: **the model cannot be re-run from the
interface.** Changing `PROJECTION_BASIS` means rebuilding the file. That is
acceptable because the rebuild is 3 seconds and the alternative was a server.
Where it will bite is the projection-basis selector (ROADMAP 2.2), which will
have to ship three payloads in one file.

**What the interface caught that the tests did not.** Two bugs, both invisible
to 32 passing invariants, both found by rendering one player's numbers in full:

1. `extension option: $0.00` on a $16 final-year player worth $72 — the
   two-year extension was never priced for `F` contracts. Worth $25 on Ohtani
   alone. FINDINGS §24.
2. `PA: —` on the same card — `ros_lines()` and the projection both export a
   `PA` column, and the un-prefixed merge produced `PA_x`/`PA_y`. Nothing
   raised; the value was simply absent. FINDINGS §24.1.

Both are the same species: **a wrong value that is not an invalid value.**
Totals still reconciled, the budget identity still held at $2,600, every
invariant still passed. The defence is not more assertions on aggregates — it
is looking at one row in full, which is exactly what a player card is.

**Verifying a re-implementation.** The browser re-implements one thing: the
rest-of-season standings calculation, so trades can be re-scored client-side.
Rather than trust it, the build writes `out/app_reference.json` (pandas' answer
for a real trade) and `app/verify.mjs` loads the page in headless Chromium and
diffs 25 quantities — 20 standings totals at exact equality, 5 dollar figures
at the payload's 4-decimal rounding tolerance. It also walks all six tabs and
fails on any console error, which is how the column collision surfaced.

Getting the tolerance right mattered: the first run "failed" on three dollar
figures differing in the 5th decimal, which is the payload rounding, not a bug.
Standings points must match exactly; sums of rounded dollars must not be asked
to.

---

## 8. Publishing to GitHub (2026-08-13) — two false alarms, one real gap

Before publishing, `pytest` reported 5 failed / 11 passed / 19 errors on
Josh's default interpreter (Anaconda Python 3.9). Neither of the two apparent
causes was a modelling bug.

**False alarm 1: scipy version, not the model.** `test_category_sign_conventions_hold_every_season`
called `spearmanr(...).statistic` — that attribute was only added in scipy
1.9; Josh's env had 1.7.3, where `spearmanr()` returns a plain named tuple.
Building a Python 3.11 venv with current scipy fixed it with zero code
changes. Lesson: a stats-library version pin is invisible until a specific
attribute access breaks, and it will look exactly like a test bug.

**False alarm 2: stale bytecode.** `__pycache__` held a mix of
`.cpython-39.pyc` and `.cpython-311.pyc` side by side — not itself the cause
of the failures, but the kind of thing that causes real import-confusion bugs
later. Cleared before diagnosing further, on principle.

**Real gap: two input files were missing from `data/`.** All remaining 19
errors and 4 failures traced to one `FileNotFoundError`:
`fg_zips_dc_2028_hitters_projections.csv`. The 2027 ZiPS files were present;
the 2028 pair (used for the out-year leg of multi-year keeper surplus,
`klab/keeper.py::project_2028`) simply hadn't made it into the delivered
`data/` folder, even though `data/HANDOFF.md` documents them as delivered.
Recovered from `~/Documents/Fantasy Baseball/` (the original working
directory) — bytes matched every other file that exists in both locations, so
this was a copy gap, not a data problem. **35/35 pass once both files are
present.** Nothing in `klab/`, `scripts/`, or the test suite was touched to
get there.

## 9. Rejected: "re-drafted players get a fresh 3-year clock" (2026-08-13)

Working hypothesis going into this session, for the deGrom/Turang final-year
puzzle (`out/FINDINGS.md` §25): both are coded `F` in 2026 despite being
drafted too early (2022, 2023) for a standard 3-year contract to still be
running. If either had been dropped and re-drafted later, the new draft would
start a fresh clock and explain it.

**Rejected on the evidence, not on principle.** Grepped `data/draft_2022.csv`
through `draft_2026.csv` for both names. Each appears exactly once — their
original draft row — and nowhere else. There is no re-draft event for either
player anywhere in the record this project holds. A hypothesis that requires
an event with zero supporting rows isn't a live hypothesis, it's a guess that
happened to be checkable, so it's closed.

It's also worth noting the hypothesis pointed the wrong direction anyway:
§23.6 already established, independently, that a re-added player *keeps* his
original contract rather than resetting it. So even setting the missing
re-draft event aside, "fresh clock" was never consistent with the project's
own confirmed rule — it would have needed a second retraction on top of the
first. Left the underlying anomaly open in FINDINGS §25 rather than force a
resolution the data doesn't support.

## 10. The partial-season exclusion rule generalized from 5 of 10 categories (2026-08-13)

`config.py`'s comment justifying `DENOM_EXCLUDE_PARTIAL_FOR_RATES` (out/FINDINGS.md
§26) showed a CV table for ERA, WHIP, R, HR, SB — five categories — found the
two rate cats inflated in the partial 2026 season and the three counting cats
not, and generalized to "exclude rate cats, include counting cats." That's a
real pattern in the five categories checked. It just isn't the actual
mechanism, and checking the other five exposed it: AVG (a rate cat) shows no
inflation, and SV (a counting cat) shows the most inflation of any category
in the entire table (0.328 vs. 0.177–0.254 in the two full seasons).

**Why this is the same species of bug as §23/§24, not a different one.**
Nothing here was arithmetically wrong — the five-category check was computed
correctly, and "rate stats have accumulating denominators" is a real and
correct mechanism. The mistake was closing the case at 5/10 categories
because the pattern looked clean, rather than checking whether the
*classification* (rate vs. counting) was doing the explanatory work or just
correlated with it in the categories sampled. It wasn't — the real driver is
"does this category's denominator accumulate evenly," and AVG/SV are the two
categories in the whole set where rate-vs-counting and
evenly-vs-unevenly-accumulating come apart.

**Lesson for next time a judgment call ships with a supporting table:** if
the table doesn't cover every category in `C.CATS`, say so explicitly in the
comment, because "this table looks conclusive" and "this table is complete"
read identically to the next person extending the code.

## 11. Rejected: median of the full free-agent pool as a survivorship-free replacement estimate (2026-08-13)

Trying to substitute for the transaction-log test QA_ROUND §A4 wants (see
out/FINDINGS.md §27): if realised production of *actually added* players is
survivorship-biased upward, why not take the median of the *entire* unrostered
pool's projections instead — no conditioning on being picked up at all?

Computed it: median roto_points across all 1,714 players in
`out/free_agent_board.csv` is **1.10** — nowhere near any of the three
existing estimates (4.0–5.0). Rejected immediately, and the reason is worth
keeping: the full free-agent pool is overwhelmingly deep-minors filler that
nobody would ever actually roster. A median over that pool answers "what does
a random unrostered player project for," which isn't the question —
replacement level is about the *marginal* addition, not a random one. Any
version of this test needs a restriction to a plausible-add-sized subset of
the pool, and choosing that subset's size just re-derives "one per active
slot" or some other rank cutoff arbitrarily — it doesn't add new information
over the 230th-projection route already in use. Redirected the effort into an
internal-consistency check instead (FINDINGS §27), which used the same free-
agent-board data more usefully: not "what's the median," but "how many free
agents actually clear the current bar, and does the bar sit at a sensible
point in the pool's shape."

## 12. BB and H reliability were copy-pasted from WHIP (2026-08-13)

Refitting `klab/project.py`'s `RELIABILITY` dict (out/FINDINGS.md #28)
reproduced 8 of 10 values to three decimals on the first try, using the same
method and season pairs the original comment describes. `BB` and `H` didn't
reproduce -- both are hard-coded to 0.237, and a fresh fit gives 0.463 and
0.359. 0.237 turned out to be `WHIP`'s own year-over-year r exactly, and
`WHIP` never gets read anywhere live (`grep rel_weight.*WHIP` in `klab/`
returns nothing -- WHIP is blended through its BB/H components, same as AVG
through H/AB). So this shipped as: compute WHIP's reliability correctly,
then paste that number into BB and H's slots too, and leave WHIP's own slot
sitting unused. Two of three related keys got the wrong, too-low value; the
one that got the *right* value doesn't matter because it's never read.

**Why the existing invariant tests didn't catch it.** Nothing about a
too-low reliability weight is arithmetically invalid -- it's a valid weight,
just discounting real signal more than it should. This is the same species
of bug as the deGrom/Ohtani-adjacent findings elsewhere in this notebook: a
wrong value that is not an invalid value. The defence, again, is not more
assertions on the output, it's re-deriving an input from scratch and
diffing it against what's hard-coded. Added
`test_reliability_weights_match_a_fresh_refit` (`tests/test_invariants.py`)
to do exactly that on every test run, rather than only when someone happens
to remember to refit by hand.

## 13. Fixing #26 didn't fix all of #26 (2026-08-13)

Caught this one by refusing to hand-type a number into a doc without
regenerating it first. Updating `out/HANDOFF.md`'s denominator table after
#26's fix, the plan was: pull the fresh numbers, paste them in, done.
Instead, checking `klab.denoms.teams_per_category` (which decides the
8-vs-9-team range constant for SV) turned up the exact same bug #26 had just
fixed one call site of: an unconditional loop over `C.DENOM_SEASONS` with no
`PARTIAL_EXCLUDE_CATS` check. It's a second, independent occurrence of the
same shape, in a function that (unlike #30's bootstrap script) feeds the
live pipeline directly.

**Why fixing one occurrence didn't fix the other:** #26 touched exactly the
two places that raised errors when tested (`denoms.py`'s dispersion loop and
`uncertainty.py`'s copy of it) because those were the two places the test
suite and the rebuild actually exercised. `teams_per_category` is a third,
separate function that happens to duplicate the same seasons-and-exclusion
logic in miniature, and nothing forced it to be checked at the same time.
There is no test that would have caught this on its own — `denominators
are positive and sane` doesn't distinguish a SV denominator of 6.00 from
6.57, both are perfectly sane numbers.

**The actual defence that worked here wasn't a test, it was a documentation
habit:** writing a number into a doc is a commitment that it's traceable to
a specific rerun, and refusing to do that by hand (typing what looks about
right) instead of copy-pasting straight from a fresh script's output is what
surfaced this. Worth remembering next time a doc update feels like a
formality — it's also a free audit if you make yourself actually run the
thing instead of remembering the number from three fixes ago.

## 14. Extension eligibility applied to the wrong contract codes — caught by Josh, not by review (2026-08-13)

Worth being direct about how this one was found, because it's different
from #10, #12, #13: those were caught by re-deriving a number from scratch
and diffing it against what shipped. This one was caught because Josh
described the extension rule in his own words, in enough detail to be
checkable, and asked for a line-by-line confirmation against the code
rather than taking a prior summary on faith. Two full review passes this
session (the general code review that produced #32, and everything before
it) read `klab/keeper.py::multiyear_surplus` and didn't catch that the
`live` extension-pricing branch applies to contract codes `"1"`, `"2"`, and
`"3"` uniformly, when the constitution's only extension clause restricts it
to a player "about to enter the final year" — code `"1"` alone.

**Why review missed it:** the function's own docstring and inline comments
describe the F-vs-live split in detail and are *correct* about that split
(`F` gets `final` candidates, everything else gets `live` candidates) — the
bug is one level down, in an eligibility check the comments don't mention
needing at all. Nothing about "everything else" being further split by
`years == 1` was flagged anywhere as a thing to check, so a review reading
top-to-bottom for internal consistency had no reason to ask the question.
The invariant tests didn't catch it either, for the usual reason: a $25.60
phantom extension option spread across 9 players is a valid-looking number,
not an invalid one.

**Lesson, stated plainly:** re-deriving numbers from scratch (the method
behind #10/#12/#13/#30/#31) catches drift between a stored value and a
fresh computation. It does not catch a rule that was **implemented with the
wrong scope** from the start, where the computation was internally
consistent the whole time. The defense for that class of bug is exactly
what happened here — a domain expert (the actual commissioner-level
knowledge of the rule) checking the code against their own understanding,
not the code checking itself. Neither method substitutes for the other.

## 15. Building the auction-price estimator: two forks tried and rejected in the regression itself

Building `klab/auction_estimator.py` (`out/FINDINGS.md` #35), the first
version of `comp_pool()`'s per-season regression used raw-dollar OLS
(`salary ~ roto_points`). Sanity-checked the resulting `premium_frac`
before trusting it and found every season's median sitting at -8% to -22%
— the typical historical purchase looked systematically overpriced, with
only a handful of $30+ stars pulling the mean back toward zero. That's not
a real market pattern, it's OLS on a right-skewed, $1-floored salary
distribution getting dominated by its own outliers.

**Fork 1, rejected: log-salary OLS.** Fit `log(salary) ~ roto_points`
instead, expecting a better-behaved residual. Checked it before trusting
it too: the bias flipped sign instead of disappearing — every season's
median premium came back systematically *positive* (median comp looked
underpriced). This is the standard retransformation bias from
exponentiating a log-scale fit back to dollars (`E[exp(x)] != exp(E[x])`)
— textbook, not a coding mistake, but still not a usable center.

**What actually worked: stop trying to get the regression's intercept
right, and recenter each season's residuals to their own median.** This
sidesteps the raw-vs-log distributional argument entirely — "premium
relative to the typical comp at this production level" is well-defined
regardless of which functional form the underlying fit uses, as long as
you don't lean on its absolute calibration. Kept the log-salary version as
the base fit (better residual shape even if the center needed correcting)
purely because it can't predict a negative dollar price for a bad line,
which a raw-dollar OLS can.

**A separate bug, not a modeling fork:** the first working version of
`_distance()` crashed with `'numpy.float64' object has no attribute
sqrt'`. Cause: `target` is a row sliced out of a mixed-dtype DataFrame
(name/role are strings), so the Series itself silently comes back
`dtype=object` even though the specific values being read out of it are
floats — the object dtype propagated into the subtraction and `np.sqrt`
choked trying to call `.sqrt()` as a method on a plain float. Fixed with an
explicit `.astype(float)`. Worth remembering as a category of bug distinct
from the modeling ones above: pandas silently downgrading a numeric slice
to `object` because *some other column in the same row* was a string.

## 16. I repeated a stale claim from out/ROADMAP.md without checking the code first (2026-08-13)

Recommended "uncertainty bands (1.2)" as the top next-roadmap item in an
earlier turn this session, quoting `out/ROADMAP.md`'s own description
("the ±34% error bar is in the footer as prose; it should be a range on
every dollar figure") without opening `app/template.html` to check whether
that was still true. It wasn't — the app has had a full "likely range"
column, a `p_surplus_positive` confidence column, tooltips, and player-card
ranges for a while. The doc was stale, and I passed the staleness straight
through instead of catching it, the same failure mode this notebook has
documented happening to the *project* several times this session (#10,
#13), just now happening to me specifically, in a conversational answer
rather than a code change.

**What actually caught it**: being asked to "make sure uncertainty gets
updated in the app," which meant actually opening the app's code to plan
the work, instead of trusting a doc's own status claim about itself.
Same lesson as #13's closing line, worth restating because it applied to
me this time: a doc describing its own state is a claim, not a fact, and
the only way to know if it's still true is to check the thing it's
describing.

## 17. The app's self-test reference trade broke the moment a real trade happened (2026-08-13)

Updated rosters after real league trades (`out/FINDINGS.md` #38) and
`scripts/run_all.py` crashed: `build_app.py::_reference()` hardcodes a
specific trade (Cade Smith/Hoerner for De La Cruz/Buxton, Pookie 2.0 vs
All-Stars) as the ground-truth pandas answer `app/verify.mjs` diffs the
browser against. De La Cruz had actually been traded to Spehr's Army by
the time this ran, so `evaluate_trade()` correctly raised
(`"is on Spehr's Army, not All-Stars"`) rather than silently computing
something wrong — a real, working guardrail, not a bug. Swapped De La Cruz
for Mike Trout (confirmed still on All-Stars) and moved on. Worth a note
for whoever eventually revisits this: hardcoding real player names into a
"forever" self-test is a real, if minor, maintenance cost every time the
league's actual rosters move, and the failure mode here (loud crash) is
the right one -- a stale hardcoded trade going undetected and silently
diffing wrong data would be much worse.

## 18. F was never actually extendable right now, and #33 didn't catch it (2026-08-13)

#33 (this notebook's #14) fixed *which* contract codes get a live extension
option -- only code `1`, not `2` or `3`. It left `F` completely alone,
because "F players can extend right now" read as an established, tested
fact by that point: FINDINGS §24 had already fixed the 1-vs-2-year pricing
for exactly this case, the whole `multiyear_surplus` F-branch was built
around it, and Ohtani's corrected $76 surplus was a named, celebrated
result. Nothing about #33's own investigation had reason to question
*whether* F was live at all -- only whether the eligibility rule had been
applied to the right set of codes.

It took Josh stating the actual constitutional timing plainly -- the
extension has to be decided before the walk year's own draft, not during
it -- to reveal that the premise under #24, under the whole F-branch, and
under three trade evaluations already run this session, was wrong the
same way every time: treating an observed mid-season snapshot as if it
still had a live decision in it, when the window described by "about to
enter the final year" had already closed months earlier. See
`out/FINDINGS.md` #39 for the fix and the league-wide numbers ($130.48 of
phantom surplus, 10 keep/cut flips, 6 of them on Spehr's Army alone).

**Why review didn't catch this either.** Every review pass this session
(the general code review that produced #32, the extension-eligibility fix
in #33/this notebook's #14) read `multiyear_surplus` and `keeper_status`
and found them internally consistent with each other and with
`config.py`'s own documented semantics. The bug wasn't an inconsistency
between the code and its own stated rules -- it was that the *documented
rule itself* was simply wrong about when the extension decision happens,
and every downstream piece of code correctly implemented that wrong rule.
No amount of internal-consistency checking catches a premise everyone
involved, including two rounds of dedicated review, shared.

## 19. Building the trade finder: a bad suggestion that looked good on paper (2026-08-13)

The first working version of the win-now scenario search
(`klab/trade_finder.py`, `out/FINDINGS.md` #40) suggested trading Vladimir
Guerrero Jr. for James Wood. On its own terms the score was real: NPB's
surplus went up. It just went up because Guerrero was such a bad contract
that NOTHING coming back could fail to look like an improvement by the net
math — including Wood, who is an F-contract rental worth exactly $0 to
whoever holds him. The search wasn't wrong about the arithmetic. It was
answering a subtly different question than the one it was supposed to:
"does this net improve the seller's position" instead of "does the seller
actually receive something of value."

**Caught by looking at the actual suggested trade, not by reviewing the
scoring formula in the abstract.** The formula (`seller_surplus_delta >
0`) reads correct in isolation -- it's a totally reasonable thing to
require. It just isn't SUFFICIENT on its own, and that only became visible
once a specific, real, checkable trade came out of it and looked wrong to
a human. Fixed by adding a second condition: the specific player coming
back has to have positive standalone value, not just make the net number
work out. Same lesson as several entries in this notebook already --
arithmetic consistency and correctness are different properties, and only
one of them shows up by staring at the formula.

**A second, unrelated bug found the same way**: the shortlist feeding the
search (top-10-by-`roto_points` per team) put 6 of Spehr's Army's 10
candidates at zero keeper value, because raw talent and keeper value are
different things for a team loaded with unkeepable-but-talented rentals.
The search wasn't broken, its INPUT was too narrow to contain the answer.
Widened to the union of top-10-by-talent and top-10-by-surplus.

**A third bug, this one a UI mechanics trap, not a modeling one**: player
and team names containing an apostrophe (Spehr's Army itself!) broke the
"load into picker" button, because `JSON.stringify()`-ing a name into a
JS literal embedded inside a double-quoted HTML `onclick` attribute
produces a raw `'` that HTML doesn't know is supposed to be data, not
markup. `app/verify.mjs`'s existing tab-walk didn't catch it because it
renders the trade tab but never clicks anything inside the new panel.
Wrote a targeted click-through check, confirmed it actually failed before
the fix and passed after, then folded it permanently into `verify.mjs`
rather than leaving it as a one-off script -- the whole point of a
regression test is that the NEXT session gets it for free.

## 20. Trade finder gave a different "best" trade on every identical rerun (2026-08-13)

Not found by testing the trade finder -- found by checking a completely
different thing, whether the build pipeline was safe to schedule
unattended. Ran `build_trade_suggestions.py` -> `run_all.py` twice back to
back on unchanged data as part of that check, diffed the two
`trade_suggestions.json` outputs out of habit (CLAUDE.md: "don't rerun and
commit different numbers without saying so"), and 28 of 45 pairs had
actually changed. Some by a lot -- one candidate's standings gain moved
from 3.5 to 5.5 points between runs with zero inputs different.

Traced it to `_shortlist()` handing `list(a_set | b_set)` to the search
loop. Set membership was provably stable (md5'd the board three ways,
identical every time) but set *iteration order* isn't -- Python randomises
string hashing per process -- and the three scenario pickers kept
"whichever candidate beat the running best first," which only matters on a
tie. Ties on the primary score turn out to be common (lots of different
return players move a team's standings by the exact same round number).
So the bug wasn't really "unstable order," it was "the tie-break logic
never existed -- it was implicitly 'whatever iteration order says,' and
nobody had written a real one."

Fixed both halves: sorted the shortlist (removes the hash-seed dependency)
and gave all three pickers a real secondary criterion -- sum of both
sides' deltas -- so a tie now resolves toward the Pareto-better candidate
instead of an arbitrary one. Reran the full chain twice more after the
fix: byte-identical output both times. Full writeup in
`out/FINDINGS.md` #41.

Two things worth remembering about how this was caught: (1) it had nothing
to do with what I was actually testing -- I was checking cron-safety, not
trade-finder correctness, and the bug only surfaced because rerunning
things twice and diffing is a cheap habit worth keeping even when it's not
the point of the exercise; (2) an in-process regression test
(`suggest_trades()` called twice in the same pytest run) would NOT have
caught this, because one process reuses one hash seed for its whole
lifetime -- the two tests I actually wrote instead check the sortedness
directly and construct a synthetic tie to exercise the tie-break logic,
which is the part that was actually wrong.

## 21. Projection-basis selector: the League tab almost lied about itself (2026-08-13)

Building the basis selector (`out/FINDINGS.md` #42), the first design I
almost shipped only swapped the per-player board table -- roto_points,
redraft_value, surplus -- and left `D.teams`/`D.constants` (keeper counts,
keeper salary, aggregate surplus, inflation) fixed at whatever basis the
page happened to build with. Caught before writing any code by asking
"which of these fields are actually just aggregates of the board" --
answer: nearly all of them -- and confirmed by actually computing both:
inflation is +31% at blend, +41% at actuals; keeper salary $1998 vs $1944.
A selector that changed the board but left the League tab's cards fixed
would have been quietly self-contradictory on exactly the screen someone
would use to sanity-check the switch.

Second thing caught, this time in manual screenshot testing after the
feature worked: the Model tab's "active settings" panel kept displaying
`projection basis: blend` no matter what the header selector showed,
because it read `D.settings.PROJECTION_BASIS` -- a value baked in at
build time that the selector never touches. `verify.mjs`'s new basis check
didn't catch this either; it asserts on `roto_points` numbers and the
`<select>` element itself, not on prose text elsewhere in the page. Same
blind spot as the earlier "±38%" staleness (`out/FINDINGS.md` #40's UI
audit) and the same lesson: a numeric-parity test doesn't read English.
Fixed by overriding the one displayed key with the live client-side state
at render time.

Neither bug would have been "wrong" in a way that crashed anything or
failed a test -- both are the specific kind of mistake that only shows up
when you actually look at the rendered page with the feature turned on,
which is the reason screenshotting every affected tab after a UI change
stayed part of the routine rather than trusting `node app/verify.mjs`'s
green output alone.

## 22. Auction estimator UI: a NaN `pos` field crashed the build the first time (2026-08-13)

Wiring `klab/auction_estimator.py` into the app (`out/FINDINGS.md` #43),
the first full `build_app.py` run crashed with `ValueError: Out of range
float values are not JSON compliant`. Cause: some rows in
`auction_sample.csv` have no recorded position, which pandas reads as
`float('nan')`, and the comp-table serialization only ran the existing
`_round()` NaN-guard over the numeric columns (salary, premium_pct),
leaving `player`/`team`/`pos` passed through raw on the assumption they'd
always be real strings. 673 players' worth of comp lists (8 comps each)
was enough real volume to hit the several dozen affected rows immediately.
`json.dumps(..., allow_nan=False)` (already set, for good reason -- a
silent `NaN` in the payload would just render as the literal text "NaN" in
the browser, wrong and not obviously wrong) turned this into a build-time
crash instead of a shipped bug. Fixed by running every comp field through
`_round()`, not just the ones I assumed needed it.

Worth remembering: this is the second time this session a bug got caught
specifically because something ran across the FULL player pool instead of
a hand-picked test case (`_pick_challenge`'s tie-break, #41's ~28-of-45
pairs, was the first) -- both were "worked fine on the players I checked
by hand, broke on player #340."

## 23. UI audit: a screenshot technique that lies about mobile, twice (2026-08-13)

Requested pass over the whole app before Josh tests it himself
(`out/FINDINGS.md` #44). Two real bugs found (a stale "extension +$5"
status string surviving the #39 correction; the player-card drawer never
showed IL/LOCKED tags at all, unlike the board table) -- both fixed and
worth remembering on their own. The more useful thing to write down here
is a tooling lesson: Playwright's `fullPage: true` screenshot option
produced TWO convincing-looking false alarms in a row, both from the same
root cause.

First: a 390px mobile screenshot of the board table looked like a totally
broken, illegibly-crushed 14-column table. Second: a free agent's drawer
looked like it was missing two whole panels, cut off mid-page. Both were
elements with their own internal scroll/overflow (`.wrap{overflow:auto}`
on the table; `#drawer{position:fixed;overflow:auto}` on the drawer) --
and in both cases, a `fullPage` capture didn't reflect what a real user
would actually see. Confirmed by (1) re-screenshotting at the true
viewport size without `fullPage`, which showed the correct, clean,
already-working rendering in both cases, and (2) directly querying the
live DOM (`getComputedStyle`, `innerHTML.includes(...)`) rather than
trusting any screenshot at all for the free-agent case.

The lesson isn't "don't use fullPage screenshots" -- it's "when a
screenshot shows something surprising, verify against the DOM/computed
styles before writing it up as a bug." Two out of four things this audit
flagged as "wrong" were artifacts of the audit's OWN tooling, not of the
app. Reported as bugs anyway without that check, this session would have
"fixed" a mobile layout and a missing panel that were never actually
broken -- wasted work chasing the audit method's blind spot instead of the
app's.
