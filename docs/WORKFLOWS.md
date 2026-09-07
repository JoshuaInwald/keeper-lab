# Keeper Lab: workflows

**Warning.** Hand-calculating a stat line, a dollar value, or a keeper cost instead of calling the `klab/` functions has produced wrong answers before (a fresh session once skipped `data/`, ignored rest-of-2026 actuals, and treated contracts as flat liabilities). Every number is calibrated to this league's real auction and standings history; a plausible estimate is wrong in ways that are hard to catch. Every recipe below routes through `klab/`, never around it.

## 0. Environment check (run first)

If `data/` is empty or missing, stop: no real number can be produced (see `data/README.md`; raw exports are gitignored on purpose).

```bash
ls data/
PYTHONPATH=. python3 -m pytest tests/ -q          # expect all passing (~2.5 min)
PYTHONPATH=.:scripts python3 scripts/build_app.py # confirms the pipeline runs end to end
```

## 1. Evaluate a trade

CLI, printed report:

```bash
PYTHONPATH=. python3 scripts/eval_trade.py \
    "Team A" "Team B" "Player 1,Player 2" "Player 3,Player 4"
```

Python, structured result. `usd_per_point` is required (a missing value used to fall back to a stale constant, FINDINGS #32.1); `evaluate_trade()` already includes rest-of-2026 (`win_now_delta`) and multi-year contract value (`surplus_multiyear`).

```python
from klab.board import build_board
from klab.trade import evaluate_trade, format_trade

board, exch, meta = build_board()
res = evaluate_trade(board, "Team A", "Team B", ["Player 1"], ["Player 2"],
                     usd_per_point=exch["usd_per_point"])
print(format_trade(res))
```

## 2. A single keeper decision

Every rostered player's recommendation is precomputed; read `keep_2027` as the call, `surplus_multiyear` as the dollar case, `extension_years` as whether to buy an extension. Unrostered players: `klab.freeagents.free_agent_board()`.

```python
import pandas as pd
b = pd.read_csv("out/keeper_board_2027.csv")
b[b["name"] == "Player Name"][[
    "team", "salary", "contract", "years_controlled", "keeper_cost",
    "surplus_multiyear", "extension_years", "extension_option", "keep_2027",
]]
```

## 3. A keeper decision in league context

`inflation` and `optimal_keepers_2027.csv` describe the world if every team keeps optimally per the model (a baseline, not a prediction of any manager); present `dollar_buys` as roto points per remaining draft dollar, not as a league forecast.

```python
from klab.api import snapshot
s = snapshot()
s.constants["inflation"]     # remaining budget / remaining worth, given optimal keeps
s.constants["dollar_buys"]   # roto points per $1 of remaining budget
```

```python
import pandas as pd
opt = pd.read_csv("out/optimal_keepers_2027.csv")
opt[opt["team"] == "Pookie 2.0"]                     # one team's model-recommended keeps
```

## 4. Team report

Keeper recommendations plus 2026 acquisition-channel breakdown; no argument prints every team.

```bash
PYTHONPATH=. python3 scripts/team_reports.py "Pookie 2.0"
```

## 5. Next-auction price estimate

`redraft_value` is fair value, not a market price; the comp-based estimator (`klab/auction_estimator.py`, FINDINGS #35) answers "what will he go for", with the comps attached. Also on the app's player card. No age data exists, so comps use position, production, and tenure only.

```bash
PYTHONPATH=. python3 scripts/estimate_auction_price.py "Player Name"
```

## 6. Rebuild everything

`run_all.py` regenerates every `out/` file including the app; trade suggestions are a separate, slower step (~135 s) and go stale after roster changes if skipped.

```bash
PYTHONPATH=.:scripts python3 scripts/run_all.py
PYTHONPATH=.:scripts python3 scripts/build_trade_suggestions.py
```

Do not commit regenerated numbers without saying so in the commit message.

## 7. After changing `klab/`, `scripts/build_app.py`, or `app/template.html`

The app re-implements a little arithmetic in JavaScript, and that copy drifts independently (FINDINGS #32.1); step 3 is the only check that catches it.

```bash
PYTHONPATH=. python3 -m pytest tests/ -q          # 1. logic still holds
PYTHONPATH=.:scripts python3 scripts/build_app.py # 2. rebuild the app
node app/verify.mjs                               # 3. JS agrees with pandas
```

Step 3 needs Node and Playwright once: `cd app && npm i playwright && npx playwright install chromium`. Install it rather than skip it.

## 8. Before ending a session that touched tracked files

```bash
./check_sync.sh                                   # fails on uncommitted or diverged main
```
