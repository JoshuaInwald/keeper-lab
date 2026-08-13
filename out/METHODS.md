# Methods — every intermediate quantity, step by step

Each step lists what it computes, the exact arithmetic, which parts are
**modular** (a config knob), and which are **judgment calls** that could
reasonably go the other way. Judgment calls are graded by how much they move a
keep-or-cut decision, measured in `scripts/sensitivity.py`.

Legend: **[MOD]** configurable · **[JUDGE]** debatable · **[RISK]** known
weak point.

---

## Step 0 — Inputs

| input | source | used for |
|---|---|---|
| team category totals, 2022–26 | `standings_long_all.csv` | denominators |
| auction prices, 5 seasons, 677 buys | `draft_*.csv` | exchange rate |
| player stats 2022–26 | `fg_hitters/pitchers_*.csv` | realised production |
| ZiPS rest-of-2026 | `fg_ros_*.csv` | finishing this season |
| ZiPS 2027 / 2028 | `fg_zips_dc_*.csv` | out-year projection **[MOD]** |
| salaries + contract codes | `contracts_parsed.csv` | keeper cost |

**[MOD]** `PROJ_2027_HITTERS` etc. — any FanGraphs export works (Steamer, THE
BAT, ATC), because they share column names. ZiPS is the only system publishing
multi-year lines, so switching costs you the 2028 leg.

**[RISK]** `contracts_raw.txt`, referenced by the original handoff, does not
exist. Salaries come from a parsed file whose provenance I cannot verify.

---

## Step 1 — Denominators: what one standings point costs

**Computes:** for each category, how many units buy one place in the standings.

1. Drop save-punters: any team under 15 SV is removed before anything
   involving saves. **[JUDGE, high impact on pricing]**
2. Divide each team total by its own season's league mean → a unitless
   relative value.
3. Pool those across the fitting seasons and take the standard deviation →
   `σ_rel`. Estimated on **2024–25** (20 team-seasons). **[MOD `DENOM_SEASONS`]
   [JUDGE, highest impact: 17 keeper decisions flip if widened to 2022–25]**
4. Convert to units:
   `denominator = σ_rel × (2027 league level) × c_n / (n − 1)`
   where `c_n` is the expected range of a normal sample of size *n*
   (3.078 for 10 teams; **2.847 for the 8 that actually contest saves**).

**Why pooled and not per-season:** the textbook `(max − min)/(N − 1)` rests on
two of ten observations and swings 25–75% year to year. Five estimators were
tried; all were unstable, because the instability is in the data. Pooling
relative values doubles the sample and divides out level shifts like the 2023
stolen-base rule.

**2027 output:** R 39.4 · HR 15.4 · RBI 38.7 · SB 20.4 · AVG .0023 · W 3.79 ·
SV 6.57 · K 59.1 · ERA .0431 · WHIP .0108

**[RISK]** ±16% standard error per category from n=20. Wider than most knobs
being debated.

---

## Step 2 — Roto points: a stat line becomes a score

**Computes:** how many standings points a player's season is worth.

- **Counting stats:** `stat ÷ denominator`. Direct.
- **Rate stats:** you cannot divide an average. Instead drop the player into a
  league-average team with one slot empty — 13/14 of its at-bats for a hitter,
  8/9 of its innings for a pitcher — and measure how far he moves the team
  rate:

```
rp_AVG  = [ (base_H + H) / (base_AB + AB)  −  league_team_AVG ] ÷ denom_AVG
rp_ERA  = [ league_team_ERA − (base_ER + ER)×9 / (base_IP + IP) ] ÷ denom_ERA
```

ERA and WHIP flip sign: allowing less is worth more.

**Team baselines** are reconstructed by taking the players who would fill the
league's slots (top 140 hitters by PA, top 90 pitchers by IP) and rescaling
their playing time by how much of their counting production the league
actually banked — absorbing IL days and empty slots. **[JUDGE, moderate]**

---

## Step 3 — Exchange rate: what a draft dollar buys

**Computes:** dollars per roto point, in this league.

1. Pair each of 677 auction purchases with the production that player actually
   delivered that season. Busts, injuries and never-played picks stay in at
   the price paid.
2. Regress `roto_points ~ salary`.
3. Invert the slope.

**Direction matters.** Production is regressed *on* price, never the reverse.
Price is measured exactly; realised production is enormously noisy, so
regressing price on production is attenuated — it claims Ohtani is worth $23.
`E[production | price]` is also the decision-relevant conditional: the
alternative to keeping a player is spending his salary at auction.

**[MOD `EXCHANGE_BASIS`]**
- `keeper_adjusted` (default): fit $/point against keeper count across all
  five auctions, predict at the expected 2027 count → **$10.08**
- `pooled`: straight fit on 2024–26 → $7.56
- `recent`: 2026 alone → $9.98

**[RISK, serious]** The rate is poorly identified in any single season. 2026's
odd- and even-numbered purchases give **$6.55 and $20.38**. And the mechanism
behind `keeper_adjusted` is *not* identified: keeper count correlates +0.75
with $/point, but season correlates **+0.987**, and n=5 cannot separate them.
Treat $10.08 as trend extrapolation, not causal inference.

---

## Step 4 — Projections: what 2027 looks like

**Computes:** each player's expected 2027 line.

Two views, blended at the **rate × playing-time** level, never on counting
stats:

- **A:** 2026 actuals + ZiPS rest-of-season
- **B:** ZiPS 2027

```
w_stat   = [PA / (PA + 250)]  capped at 0.5,  × reliability(stat) / max_reliability
PA_2027  = w × PA_A + (1−w) × PA_B
rate     = w_stat × (stat_A / PA_A) + (1−w_stat) × (stat_B / PA_B)
stat     = rate × PA_2027
```

**Why rate × PT:** ZiPS applies a player-specific durability haircut (Álvarez
474 PA, Witt 656). Averaging *counting* lines applies that haircut twice.

**Why reliability weights:** the 2026 leg is raw performance while ZiPS is
already regressed, so a flat 50/50 launders noise. Measured year-over-year
reliability on this data:

| SB .739 | K .701 | HR .607 | AVG .436 | R .425 | RBI .380 | WHIP .237 | ERA .176 | **W .151** |

Wins carry essentially no signal — a pitcher's win total describes his team.

**Saves get their own model** because the ZiPS export has no SV column at all:
`SV_next = 0.51 + 0.652 × SV` (R²=0.43, n=1,637), intercept switched off for
starters.

**[MOD `PROJECTION_BASIS`]** `blend` / `projection` / `actuals`.
**[JUDGE, high]** 47 players (17%) have a keep/cut call that depends on this.

**2028** is raw ZiPS, no blend — there is no in-season evidence two years out.
**[RISK]** No aging curve.

---

## Step 5 — Dollars

**Computes:** two dollar scales, both floored at $0.

```
replacement_rp   = roto points of the Nth-best projection      [MOD WAIVER_VALUE]
usd_per_rp       = (10 × $260 − 230 × $1) / Σ(top 230 − replacement)
redraft_value    = max(0, (rp − replacement) × usd_per_rp + 1)
keep_value       = max(0, (rp − intercept) / slope)
```

- `redraft_value` — the headline. Rescaled so the 230 best players clear
  exactly $2,600. **The budget identity is a test, not an assumption**: it
  failed at $3,854 once and caught a real bug.
- `keep_value` — opportunity cost: what you'd spend at auction to replace him.

**[MOD `WAIVER_VALUE`]** `low` (230th, default) / `medium` (300th) /
`high` (5.04, the median actual FA pickup). **[RISK]** `high` produces
$16.04/roto point against $7.56 from the auction — a factor-of-two
disagreement with market evidence, because the anchor is selected on outcome.

**Floors at $0** because a player cannot be a negative asset: a bad arm gets
benched and the spot reverts to a waiver pickup.

**Full-time columns** (`redraft_value_ft`, `upside_ft`) re-score each player at
600 PA / 150 IP / 25 SV, capped at 2× extrapolation. Counterfactual, not a
price — the headline stays on expected playing time so the budget identity
holds.

---

## Step 6 — Keeper cost and surplus

```
keeper_cost      = salary                (codes 1, 2, 3)
                 = salary + $5           (code F, extension)
years_controlled = 1, 2, 3               (the code is seasons remaining)
```

**Contract codes were originally documented backwards.** Verified against
acquisition year: 83% of code-2 players were bought in 2026, 77% of code-1 in
2025, 90% of code-F in 2024.

```
y2027            = value_2027 − cost                    (signed)
y2028, y2029     = max(0, (value_2028 − cost) × 0.85^k) (options)
extension        = max(0, (value_2028 − salary − 5) × 0.85^years)
surplus_multiyear = y2027 + y2028 + y2029 + extension
```

**Later years clip at zero because a contract is an option, not an
obligation.** You re-decide every winter. As obligations, this charged Okamoto
−$9.35 for a 2028 nobody would keep him for.

**[MOD `FUTURE_YEAR_DISCOUNT`]** 0.85/yr. **[JUDGE, low]** 1–3 flips.

---

## Step 7 — Free agents

Dropped players keep their draft-year contract on re-acquisition, so the
waiver wire is an inventory of priced assets. 2026 buys carry two years, 2025
buys one, anything older reverts to the $20 post-break price.

**Result:** Justin Crawford at $1 for two years is worth **+$30.1** — a
top-10 keeper asset sitting unrostered.

---

## Step 8 — Trades and standings

- **2027 asset view:** change in `surplus_multiyear` for each side.
- **2026 win-now view:** swap rest-of-season lines into current team totals,
  re-rank all ten teams, report the change in standings points. Rate
  categories are rebuilt from implied volume, not averaged.

---

## The judgment calls, ranked by decision impact

| call | current | alternative | keep/cut flips |
|---|---|---|---|
| denominator window | 2024–25 | 2022–25 | **17** |
| projection basis | blend | ZiPS only | **34** |
| blend weights | reliability | flat 50/50 | **17** |
| waiver value | low | high | **32** |
| SV punter exclusion | excluded | included | 3 |
| future discount | 0.85 | 1.0 / 0.6 | 3 / 1 |
| exchange window | keeper-adjusted | pooled | 0 |
| playing-time floor | 600/150/25 | none | 0 |

**88% of keeper decisions hold under every variant.** The 12% that don't are
listed in `sensitivity_keep_flags.csv`.
