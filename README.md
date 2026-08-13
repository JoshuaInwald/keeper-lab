# Keeper League Lab

[github.com/JoshuaInwald/keeper-lab](https://github.com/JoshuaInwald/keeper-lab)

A player-valuation engine for a 10-team 5×5 rotisserie keeper auction, built
on the league's **own** auction history rather than generic dollar values.

It prices every player in dollars, ranks 2027 keeper decisions by multi-year
surplus, and evaluates trades on two independent lenses — what they do to this
season's standings, and what they do to future assets.

Requires **Python 3.11+** (or any scipy ≥1.9 — older scipy returns
`spearmanr()` as a plain tuple without `.statistic`, which breaks one test
silently rather than loudly).

```bash
pip install pandas numpy scipy statsmodels pytest
PYTHONPATH=.:scripts python3 scripts/run_all.py   # build everything into out/
PYTHONPATH=. python3 -m pytest tests/ -q          # 35 invariants, ~4s
open out/keeper_lab.html                          # the app — no server needed
```

Raw projection and league exports are not redistributed — see
`data/README.md` for the exact files needed, where the master copies live,
and how/how often each one needs refreshing.

## The app

`out/keeper_lab.html` is one self-contained file, ~300 KB, no server and no
network. Six screens — keeper board, player card, league, trade evaluator,
projected standings, free agents, model — plus an inflation-adjusted toggle.
It opens on a phone, which is where a keeper decision actually gets made.

One thing is re-implemented in JavaScript: the rest-of-season standings
calculation, so a trade can be re-scored client-side. Re-implementations drift,
so the build writes `out/app_reference.json` — pandas' answer for one real
trade — and `app/verify.mjs` loads the page in headless Chromium, diffs all 25
quantities, walks every tab and fails on any console error.

```bash
cd app && npm i playwright && cd ..
PYTHONPATH=.:scripts python3 scripts/build_app.py
node app/verify.mjs
#   PASS  JS matches pandas on all 25 quantities
#   PASS  no console errors across six tabs, drawer, filters, re-sort
```

## What makes it different from an off-the-shelf auction calculator

Commercial tools (FanGraphs, RotoWire, FantasyPros) convert projections into
dollars by assuming a league budget divides across a fixed player pool. This
one **regresses realised production on prices actually paid in this league** —
677 purchases across five auctions. Busts, injuries and never-played picks
stay in the sample at the price paid, so the exchange rate is what a dollar
genuinely returned, not what it would return if everyone stayed healthy.

That buys three things a generic calculator cannot give you:

- **League-specific mispricing.** This league underpays for saves by +2.23
  roto points per closer (t=3.75) — conditional on competing in the category.
- **Drift.** A dollar bought 2.5× as much production in 2022 as in 2026, as
  keepers absorbed the elite talent. A static calculator cannot see this.
- **Contract-aware surplus.** Multi-year value against a real salary
  structure, with the +$5/yr extension priced as an option — including the
  choice between one year and two, which is worth $25 on a single player.

## How it works

1. **Denominators** — how many units of a category buy one standings point.
   Team totals are normalised by their season's league mean and pooled, so
   dispersion is estimated off 30 team-seasons instead of 10 (20 for
   ERA/WHIP/SV, which are excluded for the in-progress season — see
   `config.PARTIAL_EXCLUDE_CATS`).
2. **Exchange rate** — regress realised roto points on price paid.
   `roto_points = 3.98 + 0.109 × $`, i.e. **$9.17 per point**.
3. **Projections** — 2026 actuals + ZiPS rest-of-season, blended with ZiPS
   2027 at the rate × playing-time level, each stat weighted by its measured
   year-over-year reliability. Saves get their own persistence model because
   the ZiPS export has no SV column.
4. **Dollars and surplus** — two scales (opportunity cost and redraft), both
   floored at $0, summed across contract years with a discount.

Full detail in `out/HANDOFF.md`. The statistical core is also written in R at
`R/keeper_lab.R` if you'd rather read tidyverse than pandas.

## Documentation

| file | what's in it |
|---|---|
| `out/HANDOFF.md` | how the system works, league rules, validation, limitations |
| `out/LAB_NOTEBOOK.md` | what was tried and rejected, every bug found, and why |
| `out/FINDINGS.md` | empirical results, with the sensitivity analysis |
| `out/RESEARCH.md` | how this compares to published fantasy-analytics practice |
| `out/CODEBASE_REVIEW.md` | performance work: 10.7s → 2.7s, and how it was found |
| `out/METHODS.md` | **every intermediate quantity, step by step, with the judgment calls flagged** |
| `out/ROADMAP.md` | what's left to build and what it costs |
| `out/audit.txt` | data-integrity identities you can check with a calculator |
| `out/ORIGINAL_HANDOFF.md` | the pre-build planning doc, kept for history — several calls in it were later superseded |

## Validation

| check | result |
|---|---|
| current rosters → 2026 standings | Spearman **0.842**, Pearson 0.899; league leader predicted 1st |
| replacement level, two independent routes | 4.78 roto pts (projection) vs 3.98 (auction intercept) |
| budget identity | top 230 sum to **exactly $2,600** |
| decision robustness | 88% of keep/cut calls hold under all six modelling variants |

Honest error bar: **±34% per category** (bootstrap, 2,000 resamples of the
pooled team-seasons; the analytic ±16% is optimistic). That is wider than most of the knobs the model debates, and it
should be read alongside every dollar figure.

## Scripts

| script | does |
|---|---|
| `run_all.py` | rebuild every output |
| `validate.py` | the four checks above |
| `team_reports.py [team…]` | keeper recommendations + acquisition-channel breakdown |
| `eval_trade.py "A" "B" "P1,P2" "P3,P4"` | evaluate a trade both ways |
| `leaderboard_2026.py` | 2026 value earned + perfect-foresight prices |
| `draft_surplus.py` | where auction surplus sits on the price chain |
| `sensitivity.py` | how much each modelling choice actually matters |
| `audit.py` | data-integrity identities — run this before trusting anything |
| `zscores.py` | player value as z-scores, team totals, difference-makers |
| `market_analysis.py` | market biases, team characteristics, keep-vs-cash |
| `backtest.py` | does the engine explain seasons other than 2026 |
| `build_app.py` | serialise the snapshot into `out/keeper_lab.html` |

Cold run ≈ 2.7s; a second build in the same process ≈ 0.08s.

## Using it from code

```python
from klab.api import snapshot
s = snapshot()          # ~2s cold, instant warm
s.board                 # 275 rostered players, valued
s.free_agents           # unrostered players with live draft contracts
s.teams                 # keeper sets, budget left, surplus
s.constants             # every fitted number, incl. inflation
s.keepers("Pookie 2.0") # recommended keeper set
```

`write_snapshot()` persists a dated copy so values can be tracked over time.
Snapshots live in `out/snapshots/` as a local archive only — gitignored, not
pushed to GitHub, since they're binary and meant to accumulate indefinitely.

## Layout

```
klab/config.py   every league rule and modelling knob, in one file
klab/io.py       loaders, memoisation, name resolution
klab/denoms.py   pooled dispersion → denominators; RotoScorer
klab/auction.py  draft ↔ production matching, regression battery
klab/project.py  2027 blend, reliability weights, save persistence
klab/keeper.py   playing-time scaling, 2028 lines, multi-year surplus
klab/board.py    dollar values, keeper costs, optimal keeper sets
klab/trade.py    two-lens trade evaluation
klab/freeagents.py  the waiver wire, priced with live draft contracts
klab/api.py      single entry point for any interface + snapshot store
app/template.html  the interface; the build inlines the data into it
app/verify.mjs     diffs the browser's arithmetic against pandas
```
