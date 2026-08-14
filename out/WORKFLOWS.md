# Workflows — copy-paste recipes for the four things people actually ask for

Written 2026-08-13 after a fresh session, asked cold to "evaluate a trade,"
hand-calculated an answer instead of using this code: it couldn't find
`data/` (never checked whether it existed), didn't use the rest-of-2026
actuals, and reasoned about contracts as flat liabilities instead of
options. None of that is a documentation gap in the sense of "the rule
isn't written down somewhere" — it's all in `out/HANDOFF.md` and the
docstrings in `klab/`. It's a *discovery* gap: nothing forces a fresh
session to find those docs, or to reach for the existing function instead
of estimating one from scratch. This file exists to close that gap with
recipes specific enough to run verbatim.

**The one rule above all the others: if you're about to hand-calculate a
stat line, a dollar value, or a keeper cost, stop. There is a function for
it.** This project's entire value proposition is that its numbers are
calibrated to this league's real auction and standings history — a
plausible-sounding hand estimate will be wrong in ways that are hard to
catch, and it defeats the point of the tool. Every recipe below routes
through `klab/`, never around it.

**Before any of this**, confirm the environment works:
```bash
ls data/           # if this is empty or missing, STOP — see data/README.md.
                    # Do not proceed with estimated stats. The raw exports
                    # live at ~/Documents/Fantasy Baseball/ (Josh's machine)
                    # and are gitignored on purpose (not ours to redistribute).
PYTHONPATH=. python3 -m pytest tests/ -q         # expect all passing
PYTHONPATH=.:scripts python3 scripts/build_app.py # confirms the pipeline runs end to end
```
If `data/` is missing, a fresh session cannot produce a real number for
anything below — not "will be less accurate," genuinely cannot, because
there's no ZiPS projection or standings history to compute from. Say so
explicitly rather than guessing.

---

## 1. Evaluate a trade

```bash
PYTHONPATH=. python3 scripts/eval_trade.py \
    "Team A" "Team B" "Player 1,Player 2" "Player 3,Player 4"
```

Or from Python, if you need the structured result rather than the printed
report:

```python
from klab.board import build_board
from klab.trade import evaluate_trade, format_trade

board, exch, meta = build_board()
res = evaluate_trade(board, "Team A", "Team B", ["Player 1"], ["Player 2"],
                     usd_per_point=exch["usd_per_point"])
print(format_trade(res))
```

`usd_per_point` has no default — pass `exch["usd_per_point"]` (or
`snapshot().constants["usd_per_roto_point_auction"]`). This isn't
optional convenience; leaving it out used to silently substitute a stale
hardcoded number for every trade this tool ever evaluated
(`out/FINDINGS.md` #32.1), and it's now a required argument specifically so
that mistake fails loudly (`TypeError`) instead of shipping a wrong
verdict quietly.

`evaluate_trade()` already accounts for rest-of-2026 (via `win_now_delta`,
which rebuilds each team's projected standings with the trade applied) and
multi-year contract value (via `surplus_multiyear`, which is already inside
`board`). Don't recompute either by hand.

## 2. A single keeper decision, in isolation

Every rostered player's recommendation is already computed. Look him up
rather than re-deriving anything:

```python
import pandas as pd
b = pd.read_csv("out/keeper_board_2027.csv")
b[b["name"] == "Player Name"][[
    "team", "salary", "contract", "years_controlled", "keeper_cost",
    "surplus_multiyear", "extension_years", "extension_option", "keep_2027",
]]
```

Read `keep_2027` as the recommendation, `surplus_multiyear` as the dollar
case for it, and `extension_years` for whether the model thinks buying an
extension (see `out/HANDOFF.md` §2 on the option-vs-obligation contract
model) is worth it *this specific player's* numbers, not a blanket rule.

If the player isn't rostered (a free-agent evaluation), the same columns
exist in `klab.freeagents.free_agent_board()` / the free-agent tab of the
app.

## 3. A keeper decision in league context — what everyone else will likely do

This is a real, already-computed workflow, not a hypothetical:

```python
from klab.api import snapshot
s = snapshot()

s.constants["inflation"]     # how much a remaining draft dollar buys,
                              # GIVEN every team keeps optimally per the model
s.constants["dollar_buys"]   # roto points per $1 of remaining budget
```

```python
import pandas as pd
opt = pd.read_csv("out/optimal_keepers_2027.csv")   # every team's model-recommended keeps
opt[opt["team"] == "Team A"]                         # what one team would keep, optimally
```

**What this does and doesn't tell you.** `inflation` and
`optimal_keepers_2027.csv` describe the world *if every team plays the
model's own recommendation* — a reasonable baseline, not a prediction of
what any specific manager will actually do. There is no per-manager
behavioral model here (see `out/RESEARCH.md` §6 for why that's a shared
blind spot, not unique to this project) — don't present `inflation` as "the
league will inflate 43%," present it as "if everyone keeps optimally, a
remaining draft dollar buys 0.7 roto points, versus 1.0 in a
no-keeper world."

## 4. "What would this player actually go for at next year's auction?"

Different question from #2/#3 above, and `redraft_value` deliberately
doesn't answer it — that's a fair-value regression, not a market-price
prediction. Use the comp-based estimator instead:

```bash
PYTHONPATH=. python3 scripts/estimate_auction_price.py "Player Name"
```

This is a genuinely separate tool (`klab/auction_estimator.py`) built
2026-08-13 — see `out/FINDINGS.md` #35 for the full writeup, including a
worked example where the top comp for a real 2027 target was that same
player's *own* price from a year ago. It has a real, known blind spot: no
age/debut-year data exists anywhere in `data/`, so it can't do age-based
comps at all, only position and production level. **Not wired into the app
yet** — it's designed to be addable later (see `out/ROADMAP.md`), but for
now it's CLI-only.

## 5. If you changed any code in `klab/` — get it into the app

The app (`out/keeper_lab.html`) is generated from the same `klab/` code
every script uses (see `out/ARCHITECTURE.md` §"One entry point") — there is
no separate UI codebase to keep in sync for the *Python* side. But the app
also re-implements a little arithmetic in JavaScript for client-side
interactivity, and that re-implementation drifts independently
(`out/FINDINGS.md` #32.1 is exactly this: the JS trade evaluator quietly
used a different dollar scale than Python for months). So after any change
to `klab/`, `scripts/build_app.py`, or `app/template.html`:

```bash
PYTHONPATH=. python3 -m pytest tests/ -q          # 1. logic still holds
PYTHONPATH=.:scripts python3 scripts/build_app.py # 2. rebuild the app
node app/verify.mjs                               # 3. confirm JS still agrees with pandas
```

Step 3 needs Node + Playwright once: `cd app && npm i playwright && npx
playwright install chromium`. Skipping step 3 because Node isn't installed
is a real, recurring failure mode of this project specifically (see
`out/LAB_NOTEBOOK.md` — it happened this session) — install it rather than
skip it, the whole point of `verify.mjs` is to catch exactly the class of
bug that doesn't show up any other way.
