# Keeper Lab

Player-valuation engine for a private 10-team 5x5 roto keeper auction league (CBS Sports). It prices every player in dollars from the league's own auction and standings history, ranks 2027 keeper decisions by multi-year contract surplus, evaluates trades on two lenses (this season's standings, future assets), and simulates each team's odds of finishing in the money. Public repo: [github.com/JoshuaInwald/keeper-lab](https://github.com/JoshuaInwald/keeper-lab).

## Quickstart

```bash
pip install pandas numpy scipy statsmodels pytest      # Python 3.11+ (scipy >= 1.9)
PYTHONPATH=.:scripts python3 scripts/run_all.py         # rebuild every output into out/ (~3 s)
PYTHONPATH=. python3 -m pytest tests/ -q                # 64 invariants, ~3-6 min
open out/keeper_lab.html                                # the app: one file, no server
```

`data/` is not in the repo (FanGraphs terms, private league exports). `data/README.md` lists every file and its refresh cadence; the master copies live in `~/Documents/Fantasy Baseball/`.

## What it does that a generic auction calculator does not

| generic tool | this engine |
|---|---|
| budget divided across a fixed pool of projected players | dollar scale regressed on 677 real purchases in this league (2022-2026), busts included |
| one season | contract-aware: 3-year salaries, the +$5/yr extension priced as an option (1 or 2 years) |
| linear roto points | Monte Carlo P(1st..4th) under the league's 50/25/15/breakeven payout |
| static prices | measured drift: a dollar bought 2.5x the production in 2022 as in 2026; +33% projected 2027 inflation |

## Validation (committed build)

| check | result |
|---|---|
| rostered players to 2026 standings | Spearman 0.851, Pearson 0.885 (2026-09-07 rerun; 0.863 in older docs was stale) |
| replacement level, per role | 5.12 hitters / 3.53 pitchers (fieldable pool) vs 3.98 (auction intercept) |
| budget identity | the calibration pool's `redraft_value` sums to exactly $2,600 |
| decision robustness | ~90% of keep/cut calls hold across six modelling variants |
| error bar | +/-34% per category (bootstrap); wider than most modelling knobs |
| out-of-sample keep/cut | the model does NOT beat this league's owners on 289 past decisions (FINDINGS #69) |

Known gap: the model has been tested out of sample for the first time and **it does not beat this league's owners** on 289 past keeper decisions (`docs/FINDINGS.md` #69). That test ran on a naive projection, so it is a floor rather than a verdict, but the valuation machinery was held fixed, which points at the forecast rather than the pricing as the binding constraint.

Three dollar columns do three different jobs and are never blended: `production_value` is worth to a roster, `keep_value` is what replacing a player would cost at this league's auction, and `market_price` is the only one comparable to a draft price. #75 reconciles them.

## Layout

```
klab/            the engine (config, io, denoms, auction, project, keeper, board, trade,
                 freeagents, trade_finder, standings_sim, uncertainty, auction_estimator, api)
scripts/         run_all, build_app, validate, audit, sensitivity, team_reports, eval_trade,
                 estimate_auction_price, build_trade_suggestions, leaderboard_2026, lookup
tests/           invariants (64 tests)
app/             template.html + verify.mjs (headless Chromium diffs the JS re-implementation against pandas)
out/             keeper_lab.html, model_params.json, keeper_board_2027.csv, auction_sample.csv,
                 trade_suggestions.json, app_reference.json, audit.txt, sensitivity_*.csv
docs/            METHODS, FINDINGS, ROADMAP, WORKFLOWS, SESSION-LOG, constitution.txt
```

## Documentation

| file | read it when |
|---|---|
| `docs/WORKFLOWS.md` | asked to evaluate a trade, a keeper, a price, a team: tested recipes, run first |
| `docs/METHODS.md` | how every number is computed, judgment calls, limitations, module map |
| `docs/FINDINGS.md` | the 55 empirical results, condensed, retractions preserved |
| `docs/ROADMAP.md` | what is next, starting with the market-price recalibration |
| `docs/SESSION-LOG.md` | what was built and broken, by date |
| `HANDOFF.md` | current state, next session start here |
| `CONSTRAINTS.md` | permanent decisions; violating one is a session failure |
| `CLAUDE.md` | session playbook for Claude |

## From code

```python
from klab.api import snapshot
s = snapshot()            # ~3 s cold, instant warm
s.board                   # rostered players, valued
s.free_agents             # unrostered players priced at their live draft contract
s.teams                   # keeper sets, budget left, surplus
s.constants               # every fitted number, incl. inflation
s.keepers("Pookie 2.0")   # recommended keeper set
```
