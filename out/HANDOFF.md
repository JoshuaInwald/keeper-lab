# Keeper League Lab — Handoff

**What it is:** a valuation engine for Josh's Legends League (CBS, 10-team
5×5 roto keeper auction) that prices players in dollars grounded in *this
league's* auction history, ranks 2027 keeper decisions by surplus, and
evaluates trades from both a win-now and an asset perspective.

**Status:** built, validated, in use. Numbers are trustworthy subject to §6.

**Companion docs:**
- `WORKFLOWS.md` — asked to evaluate a trade or a keeper decision? Start
  there, not here. Tested recipes, not narrative.
- `LAB_NOTEBOOK.md` — what was tried, what failed, why the structure is what
  it is. Read this before changing any modelling decision.
- `FINDINGS.md` — research results (saves mispricing, draft value chain,
  stat reliability). The intellectual content.
- `ROADMAP.md` — what's next, kept current. This file's own "next steps"
  section used to duplicate it and drifted out of sync; §7 below now just
  points there instead of maintaining a second list.

---

## 1. League rules that drive the math

- 10 teams, auction, **$260/team**. First keeper year 2022.
- Active **23** = 14 hitters (C,1B,2B,3B,SS,CI,MI,5×OF,2×UTIL) + 9 pitchers,
  plus a reserve list. 5×5: R/HR/RBI/SB/AVG · W/SV/K/ERA/WHIP.
- Keep **6–13**. FA acquisition costs $10 before the All-Star break, $20 after.
- 3-year contracts; a player in his final year can be extended for **+$5/yr**.

### Contract codes

The code is the number of seasons remaining **after** the current one:

| code | meaning | 2027 cost |
|---|---|---|
| `3` | 2027, 2028, 2029 at salary | salary |
| `2` | 2027, 2028 at salary | salary |
| `1` | 2027 only, at salary | salary |
| `F` | confirmed free agent after 2026, not extendable | n/a — not keepable |

This was previously documented backwards. The evidence for the correction is
in `LAB_NOTEBOOK.md` §2. Three players carry `?` and are charged the worst
case. Getting this wrong understates every multi-year contract by a season.

**`F` is not a live extension choice — CORRECTED 2026-08-13, `out/FINDINGS.md`
#39.** The extension clause covers a player "about to enter" his final
year, meaning the decision happens *before that season's own draft*. A
player still coded `F` in a mid-2026-or-later snapshot already missed that
window — he's confirmed for the open 2027 auction, not a keeper option at
all. `keeper_cost`/`surplus_multiyear`/`extension_option` are all `0` for
every `F` player and `keepable` is `False`, unconditionally. The one
genuinely live extension decision on the whole board belongs to a code-`1`
player (one guaranteed year left) — he's the one actually "about to enter"
his final year, for the upcoming 2027 deadline.

---

## 2. How the valuation works

Four steps, each independently checkable.

**1. Denominators — what one standings point costs.** Team totals are divided
by their season's league mean and pooled across 2024–26, so dispersion is
estimated off 30 team-seasons rather than 10 for most categories — 20 for
ERA/WHIP and 17 for SV, which exclude the in-progress 2026 season because a
partial season measurably inflates their dispersion (`config.PARTIAL_EXCLUDE_CATS`,
`out/FINDINGS.md` #26).

| R | HR | RBI | SB | AVG | W | SV | K | ERA | WHIP |
|---|----|-----|----|----|---|----|---|-----|------|
| 33.8 | 13.8 | 33.8 | 17.1 | .0023 | 3.67 | 6.57 | 52.6 | .0431 | .0108 |

1 HR ≈ 1.2 SB ≈ 2.4 R. ~30 points of personal BA over 600 AB = 1 point.
~0.34 of ERA over 180 IP = 1 point. 6.6 saves = 52.6 strikeouts. The SV field is
8 teams after punters are dropped, so it uses the 8-team range constant.

**2. Exchange rate — what a draft dollar buys.** Every auction purchase
2022–2026 paired with the production actually delivered; busts and injuries
stay in at the price paid, so the slope is waste-adjusted. Fitted on 2024–26
(n=404): **roto_points = 3.98 + 0.109 × $**, i.e. **$9.17 per point**.

**3. Projections.** 2027 = blend of (2026 actuals + ZiPS rest-of-season) and
ZiPS 2027, blended at the rate × playing-time level, with each stat's weight
on the 2026 leg scaled by that stat's year-over-year reliability. 2028 comes
straight from ZiPS 2028. Both use expected playing time; the full-season
counterfactual is reported separately (see step 4).

**4. Dollars and surplus.** Two scales, both floored at $0:

- `keep_value` — opportunity cost, `(roto_points − intercept)/slope`. What
  you'd spend at auction to replace him.
- `redraft_value` — same ranking rescaled so the 230 best players clear
  exactly $2,600. **This is the headline number and what keeper flags use.**

Both are computed on **expected** playing time, and the dollar scale is
calibrated on that same pool, so the budget identity holds exactly.
`redraft_value_ft` and `upside_ft` show the counterfactual if the player takes
a full season's workload (600 PA / 150 IP / 25 SV) — use it to spot breakouts
the point projection buries, not as a price.

`surplus_multiyear` sums `value − cost` over the years the contract controls,
discounting 0.85/yr past 2027, **plus the extension option**: any contract
reaching its final year can be extended at +$5 **per year** for one or two
years, so a code-1 player is one year plus a call option, not a rental. Which
of one or two years to buy is priced, not assumed — `extension_years` says
(0, 1 or 2). For a final-year (`F`) player the one-year price is already inside
`keeper_cost`, so `extension_option` there is the *incremental* value of buying
two years instead of one. See FINDINGS §24: this was wrong until the app made
it visible, and it was worth $25 on Ohtani alone.

---

## 3. Validation

| check | result |
|---|---|
| Current rosters → 2026 standings | Spearman **0.863**, Pearson **0.889**; Pookie 2.0 predicted 1st, actually 1st |
| Replacement level, two independent routes | 4.81 roto pts (230th projection) vs 3.98 (auction intercept) |
| Budget identity | top 230 redraft values sum to **exactly $2,600** (was $3,854 before the calibration fix) |
| Decision robustness | 92% of keep/cut calls hold under all six modelling variants (`scripts/sensitivity.py`) |
| Hand check | 10 players across the value spectrum, `scripts/validate.py` |

Numbers above are as of 2026-08-14, after this session's positional-adjustment
(`FINDINGS.md` #52) and playing-time (`FINDINGS.md` #51/#53) work — both moved
the replacement level and standings correlation slightly. Rerun
`scripts/validate.py` and `scripts/sensitivity.py` rather than trusting a
stale copy here if it's been a while.

---

## 4. Running it

Everything below is optional. **The app is the front door**: open
`out/keeper_lab.html` in any browser, including a phone. It is one
self-contained file with the data inlined — no server, no network, no install.

Needs Python 3.11+ (or scipy ≥1.9 specifically — older scipy's `spearmanr()`
lacks `.statistic` and fails one test silently rather than loudly; see
`LAB_NOTEBOOK.md` §8).

```bash
pip install pandas numpy scipy statsmodels
PYTHONPATH=.:scripts python3 scripts/run_all.py  # builds everything, incl. the app
PYTHONPATH=.:scripts python3 scripts/build_app.py # just the app (~3s)
node app/verify.mjs                              # diff the browser against pandas
PYTHONPATH=. python3 scripts/validate.py         # the four checks above
PYTHONPATH=. python3 scripts/leaderboard_2026.py # 2026 value + hindsight prices
PYTHONPATH=. python3 scripts/draft_surplus.py    # where auction surplus lives
PYTHONPATH=. python3 scripts/eval_trade.py "Team A" "Team B" "P1,P2" "P3,P4"
PYTHONPATH=. python3 scripts/team_reports.py [team ...]  # keeper sets + channels
PYTHONPATH=. python3 scripts/sensitivity.py      # how much do the knobs matter
PYTHONPATH=. python3 -m pytest tests/ -q         # 71 invariants, ~55s
```

A cold run takes ~2.7s; a second build in the same process is ~0.08s (loaders
and fitted constants are memoised in `io.cached`).

```python
from klab.board import build_board
from klab.trade import evaluate_trade, format_trade
board, exch, meta = build_board()
print(format_trade(evaluate_trade(
    board, "NPB No Stars", "Spehr's Army",
    ["Julio Rodríguez", "Tarik Skubal"], ["Christian Scott", "Brandon Lowe"])))
```

### Code map

```
klab/config.py    every knob: league constants, contract semantics, PT floors,
                  denominator/auction windows, discount rate
klab/io.py        loaders + name resolver (671/677 draft names matched)
klab/denoms.py    pooled dispersion -> denominators; RotoScorer
klab/auction.py   draft<->production matching, regression battery
klab/project.py   2027 blend, reliability weights, save persistence model
klab/keeper.py    full-time PT scaling, 2028 lines, multi-year surplus
klab/board.py     dollar values, keeper costs, optimal keeper sets
klab/trade.py     two-lens trade evaluation
klab/api.py       snapshot() -- one object with everything an interface needs
app/template.html the interface; the build inlines the data into it
app/verify.mjs    diffs the browser's JS arithmetic against pandas
```

### Outputs (`out/`)

**`keeper_lab.html`** — the app · `keeper_board_2027.csv` (275 rostered
players) · `optimal_keepers_2027.csv` · `player_values_2027.csv` (~2,000
projected) · `leaderboard_2026.csv` · `auction_sample.csv` ·
`auction_regression_battery.csv` · `draft_surplus_sample.csv` ·
`model_params.json` · `app_reference.json` (ground truth for `verify.mjs`)

---

## 5. Data

All in `/Users/JoshInwald/Documents/Fantasy Baseball/`.

| file | role |
|---|---|
| `standings_long_all.csv` | team category totals 2022–26 → denominators |
| `draft_2022..2025.csv`, `draft_salaries_all.csv` | auction prices → exchange rate |
| `fg_hitters_2022_2026.csv`, `fg_pitchers_2022_2026.csv` | realized production |
| `fg_ros_*.csv` | ZiPS rest-of-2026 |
| `fg_zips_dc_2027_*`, `_2028_*` | out-year projections (no SV column) |
| `contracts_parsed.csv`, `rosters_valued.csv` | salaries, contract codes, rosters |
| `keepers_2022..2026.csv` | eligibility lists, not selections |

`contracts_raw.txt` referenced by the original handoff is **not present**;
`contracts_parsed.csv` is the salary source.

---

## 6. Known limitations — read before trusting a number

1. **Save-punter exclusion is the single biggest lever.** Dropping teams under
   15 SV before computing the SV denominator is what makes the saves finding
   significant at all (+2.23, t=3.75 excluded; +0.92, t=1.82 included).
   Defensible — it is the right marginal rate for a team competing in saves —
   but every closer valuation rests on it. See `FINDINGS.md` §1.
2. **No prospect-upside term as a probability.** `upside_ft`/`redraft_value_ft`
   report what a player is worth on a full healthy/full-role workload
   (out/FINDINGS.md #53 splits this into a "health" case and, for a
   non-closing reliever, a separate and much less grounded "role" case),
   but it's a single counterfactual number, not a probability-weighted
   expectation. Real breakout *talent* upside (a young player outperforming
   his own rate projection, not just playing more) is still just the point
   projection.
3. **No aging curves.** The 2028 leg is raw ZiPS. No birthdate/age data
   exists in any file this project has (checked directly, not assumed).
4. **No waiver-wire value.** Teams fill ~10 of 23 slots from FA; that
   production is invisible and is why replacement level sits as high as it
   does. Still blocked on transaction-date data (`out/FINDINGS.md` #27).
5. **Rostered salary exceeds the cap** ($3,194 vs $2,600) — mid-season IL and
   reserve artifacts. Doesn't affect keeper math (only ever 6–13 players).
6. **Uncertainty is measured but not fully propagated everywhere.** Bootstrap
   bands exist for `redraft_value`/`surplus_multiyear` (board, app drawer,
   `p_surplus_positive`) and the Model tab now shows each denominator's own
   standard error too — but a few secondary figures (`keep_value`, the
   auction estimator's comps) are still point estimates. Honest error bar on
   a single category's scale is roughly **±16-18%** for the thinnest-sampled
   categories (SV, ERA, WHIP) down to **±13%** for the rest (Model tab); the
   bootstrapped whole-figure error bar quoted in the app footer is **±34%**.
7. **Positional replacement covers catcher and shortstop only, off by
   default.** `out/FINDINGS.md` #52 built this once real C/SS eligibility
   data existed, as a toggle rather than a default — the published evidence
   (Razzball, FanGraphs' 13-system test, both cited in `RESEARCH.md` §1) says
   positional adjustment barely moves outcomes, and this league's own data
   agreed in an even stronger form: both adjusted positions came out
   *deeper* than pooled, not scarcer. The full spectrum (1B/2B/3B/OF) is
   still on the pooled line, blocked the same way this was until #52 — no
   full-position eligibility export exists yet.
**Closed:** the worry that ZiPS 2027 already incorporates 2026 (double-counting
it in the blend) was tested and refuted — see `LAB_NOTEBOOK.md` §7.

---

## 7. Next steps

See `out/ROADMAP.md` — this section used to keep its own numbered list and
it drifted out of sync with reality across enough sessions that it was
actively misleading (it still said the app/UI, uncertainty bands, and the
sensitivity harness were future work; all three have been done for a while).
One list, kept current, beats two that disagree.
