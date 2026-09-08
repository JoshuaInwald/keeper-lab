# Roadmap

What is next, and only that. The ranked priority list lives in `HANDOFF.md`;
this file holds the items too small or too far out to sit there, plus what has
been declined. Evidence for anything closed is in `docs/FINDINGS.md`.

**Closed, 2026-09-08.** Item 0 (obtain a projection archive) is done: Marcel for
2024-2026 is in `data/` (#67). Item 1 (market-price recalibration) is complete
across all five steps, two of them negative results that did not ship (#56,
#57). Item 2 (per-team category value) is scoped and refused (#60). Item 4
(waiver-wire value) is measured and left at `"low"` (#62). The full diagnosis
that motivated item 1, including the league-mate's 2026-08-15 review of the
headline number, is in git history and its conclusions are in #56 and #57.

## Live

**Intuition tab v2 (scope needs a decision, blocked on Josh).**
Show each player's PA/IP and per-category rates; three ways to adjust (+/-
buttons, direct entry, presets such as full-time); all 230 rostered players
grouped by team with contract fields. **The open decision is sandboxed (as now)
against a propagating override that flows through the 2027 pipeline.** The
propagating version is a materially larger change; decide before scoping.

**Contend-or-punt flag.** What survives of item 2: a flag on the five
categories where rank persists, feeding the trade evaluator rather than the
dollar scale. The in-season case already works through `trade.win_now_delta()`,
which re-ranks observed standings instead of projecting them. #60.

**Uncertainty ranges on the Board / Trade / Standings tabs.** A design pass
reusing the bootstrap bands the board already carries.

**Small and contained.**
- 2027 odds inside the Trade tab; `simulate_keeper_finish_odds(keeper_override=...)` already accepts the input.
- The free-agent tab's "likely range" is blank by design; `value_lo`/`value_hi` could be extended cheaply.

## Declined or parked (do not reopen without a reason)
Aging curves (ZiPS carries age, #59). Auto-refresh (no ingestion step exists).
Probability-weighted closer upside (low priority; report a range via the
existing bootstrap if ever built). Name-brand or good-MLB-team premium (no MLB
standings data in `data/`; tenure and prior salary cover the tractable part).
Mobile nav overflow. Transaction-log scraping (2 sessions; it is also the one
thing that would settle `WAIVER_VALUE`, so it is a nice-to-have with a real
payoff attached).
