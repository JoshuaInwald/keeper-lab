# Keeper League Lab — valuation engine

**Status:** valuation engine built, validated, and producing 2027 keeper values.
Trade evaluator working. Built 2026-08-13.

The headline validation: rolling each team's *current* roster over its actual
2026 stats reproduces the real 2026 standings at Spearman 0.84 / Pearson 0.90,
and puts **Pookie 2.0 first — where they actually are**.

---

## 1. What a roto point costs

### Denominators

A denominator is how many units of a category buy one standings point. The
obvious estimator, `(max − min) / (N − 1)`, is determined by two of ten teams
and swings 25–75% year to year. Three alternatives were tested (trimmed range,
median gap, IQR-based); none was stable either, because the instability is in
the data, not the estimator.

The fix was to stop estimating per season. Each season's team totals are
divided by that season's league mean and pooled, so σ is estimated off 20
team-seasons instead of 10, and level shifts (the 2023 stolen-base rule change,
run-environment drift) wash out. Denominators for any target year are then
`σ_rel × that year's league level × 3.078/9`.

Fitted on **2024–2025 only** — the league's dispersion regime changed in 2024.
ERA σ_rel runs 13.8%, 5.5% in 2022–23 against 3.7%, 3.5% in 2024–25; only ~1.1x
of that is the mechanical effect of lower roster volume, the rest is the league
getting sharper.

**2027 denominators (1 standings point = this much production):**

| R | HR | RBI | SB | AVG | W | SV | K | ERA | WHIP |
|---|----|-----|----|----|---|----|---|-----|------|
| 39.4 | 15.4 | 38.7 | 20.4 | .0023 | 3.79 | 5.53 | 59.1 | .0431 | .0108 |

Implied cross-rates: 1 HR ≈ 1.3 SB ≈ 2.6 R. Saves are the cheapest points on
the board — 5.5 saves buys what 59 strikeouts does.

Rate categories are converted by dropping the player into a league-average team
missing one slot (13/14 of a team's AB for hitters, 8/9 of its IP for pitchers)
and measuring how far he moves the team rate.

### Dollars per roto point

Every auction purchase 2022–2026 (n=677, 671 name-matched) was paired with the
production that player actually delivered that year, then regressed. Busts,
injuries and players who never took an MLB at-bat all stay in the sample at the
price paid, so the slope is waste-adjusted by construction.

**The exchange rate is deteriorating fast:**

| | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| $ per roto point | 4.58 | 5.39 | 6.67 | 8.37 | 11.60 |
| free production at $0 (roto pts) | 2.17 | 2.73 | 3.47 | 3.70 | 3.77 |

Both series move the way you'd expect if keepers are absorbing the elite talent
and leaving the auction a scrum for replacement-level players — eligible keepers
went from 25 in 2022 to 100 in 2026. Fitted on the recent window (2024–2026,
n=404): **slope 0.131 roto points per dollar, intercept 3.48, $7.64 per point.**

R² is 0.14. That is expected and not a defect: the regression estimates
`E[production | price]`, and realized production is enormously noisy. Noise in
the dependent variable does not bias the slope.

---

## 2. Two dollar scales

They answer different questions and the code reports both.

- **`keep_value`** — opportunity cost. What you would have to spend at auction
  to replace this player: `(roto_points − 3.48) / 0.131`. This is the
  keep-vs-cut number.
- **`redraft_value`** — the same ranking rescaled so the 230 rostered players
  clear exactly $2,600. This is what the player fetches in a full redraft, and
  it is the right scale for comparing two sides of a trade, because both teams
  face the same cap.

Both floor at $0. A player cannot be a negative asset — a bad arm gets benched
and the roster spot reverts to a waiver pickup. Unfloored, the model claimed an
injured $10 prospect was a −$38 liability when the real downside is the $10.

**The independent-estimate check that matters:** replacement level computed as
the 230th-best projected player is **4.25 roto points**. The auction regression
intercept — free production at $0, from completely separate data — is **3.48**.
Two unrelated routes to the same quantity, agreeing within 0.8 points.

---

## 3. 2027 projections

Two views per player, blended at the **rate × playing-time** level, never on raw
counting stats:

- **A** — 2026 full season (actuals through 121 games + ZiPS rest-of-season)
- **B** — ZiPS 2027 depth-chart projection

Blending counting stats directly double-counts ZiPS's durability haircut. ZiPS
docks Yordán Álvarez to 474 PA and gives Bobby Witt 656; averaging his *counting*
line against a healthy 2026 applies that penalty twice. Rates and playing time
are blended separately instead.

Source A's weight is `PA / (PA + 250)` capped at 0.5, so a prospect with 60 PA
leans on ZiPS while a 650-PA regular leans on his own season.

**Saves are modelled separately — the ZiPS 2027 export has no SV column at all.**
Fitted on 2022–2025: `SV_next = 0.51 + 0.652 × SV` (R²=0.43, n=1,637), fitted
across all pitchers rather than incumbent closers, because restricting to
SV≥10 produces a +5.0 intercept that hands five phantom saves to every mop-up
arm. The intercept is switched off for starters. Total projected 2027 saves:
1,271 against an MLB actual of roughly 1,250.

---

## 4. The finding worth acting on: this league underpays for saves

Classifying closers by **prior-season saves** — an observable available before
the auction — pitchers who enter the auction as closers beat their price by
**+2.67 roto points** (HC1 t = 4.3, n = 38), at a mean price of $7.90.

| player type (ex ante) | n | mean $ | mean roto pts | residual vs pooled fit |
|---|---|---|---|---|
| closer | 38 | 7.9 | 6.94 | **+2.67** |
| hitter | 401 | 11.8 | 5.02 | +0.09 |
| other pitcher | 238 | 10.9 | 4.19 | −0.58 |

Actual purchases: Aroldis Chapman at $2 returned 13.5 roto points; Trevor Megill
at $1 returned 10.3; Raisel Iglesias at $3 returned 9.1.

The first version of this test classified closers by *realized* saves, which
selects on the outcome and guarantees a positive residual. The finding survives
the ex-ante correction and survives restriction to 2024–2026 (+2.17).

Why it is real rather than a modelling artifact: team save totals are sharply
bimodal — 2025 ran `[0, 57, 61, 70, 70, 72, 76, 82, 91, 98]`. One team punts,
and the other nine pack into a 41-save band where roughly five saves buys a
standings point. "Never pay for saves" is fantasy orthodoxy; in a league where
everyone believes it, saves become the cheapest roto points available.

**Caveat:** n=38, and the punter-exclusion rule (drop teams under 15 SV before
computing the SV denominator) is what makes saves this valuable. Including
punters roughly halves closer value. That rule came from the handoff and is
defensible — it is the correct marginal rate *for a team that competes in
saves* — but it is the single biggest lever in the model.

---

## 5. Known limitations

1. **Elite players are probably undervalued.** The dollar scale is linear in
   roto points; real auctions are convex at the top. The price-bucket
   regressions show it — the $31+ tier pays more per point than the $16–30
   tier. Bobby Witt at $29 reads low against consensus for this reason.
2. **Aaron Judge at −$29 surplus is the model's most aggressive call**, and it
   rests entirely on a 450-PA projection driven by his 2026 injury. Worth
   overriding by hand if you think he's healthy.
3. **`contracts_raw.txt` is missing** from the folder; salaries come from
   `contracts_parsed.csv` (275 players). Three players carry contract `?` and
   are charged the worst case (salary + $5).
4. **Rostered salary totals $3,194 against a $2,600 cap** — mid-season IL and
   reserve artifacts. Doesn't affect keeper math, which only ever sums 6–13
   players per team, but it means the roster file is not cap-clean.
5. **Single-year horizon.** No aging curves, no discount rate, no multi-year
   contract value. A 3-year keeper window would change the ranking of young
   cheap talent materially.
6. **No waiver-wire value.** Teams fill ~10 of 23 slots from free agency;
   that production is invisible here and is why replacement level is as high
   as it is.

---

## 6. Files

| file | what |
|---|---|
| `keeper_board_2027.csv` | all 275 rostered players: projection, value, cost, surplus, keep flag |
| `optimal_keepers_2027.csv` | just the recommended keeper set per team |
| `player_values_2027.csv` | all 1,989 projected players, rostered or not |
| `auction_sample.csv` | every auction purchase 2022–26 with realized production |
| `auction_regression_battery.csv` | the full spec battery |
| `denominator_dispersion.csv`, `denominators_by_season.csv` | denominator fitting |
| `model_params.json` | every fitted constant |

Code: `klab/` — `config` (all knobs) · `io` · `denoms` · `auction` · `project` ·
`board` · `trade`. Run `PYTHONPATH=. python3 scripts/run_all.py`, then
`scripts/validate.py`.

```python
from klab.board import build_board
from klab.trade import evaluate_trade, format_trade
board, exch, meta = build_board()
print(format_trade(evaluate_trade(
    board, "Pookie 2.0", "Producers", ["Cade Smith"], ["Pete Crow-Armstrong"])))
```
