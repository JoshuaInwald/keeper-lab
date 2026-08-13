# Lab Notebook — what was tried, what failed, and why the code looks like this

Read this before changing a modelling decision. Most of the obvious
alternatives were tried and rejected for reasons that are not obvious.

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
