# Permanent constraints

Violating any of these is a session failure regardless of what else got done.

- Never determine, state, or hint which league team is Josh's. The worked-example team is always `Pookie 2.0`.
- No emojis anywhere: code, docs, commits, chat. No em-dashes in docs (colons, commas, parentheses).
- Do not invent a number. Every figure comes from `out/`, `docs/`, or a rerun of the scripts. Say in the commit message when a rebuild changed committed outputs.
- Do not hand-calculate a value, a keeper cost, or a trade. Call the `klab/` functions (`docs/WORKFLOWS.md`). Hand calculation has produced wrong answers before.
- Do not rewrite a past finding to read better, and do not drop a retraction (`docs/FINDINGS.md` #16, #19, #30, #55).
- `data/` never enters git. FanGraphs exports and CBS league exports are not redistributable.
- Payout structure is 50% / 25% / 15% of the pot for 1st to 3rd and buy-in back for 4th (`PAYOUT_SPOTS`, `PAYOUT_SHARE`). It was once coded as top-2; do not regress.
- Extension rule: +$5 per year, one or two years, once per contract, only for code-`1` players. `F` players are not keepable or extendable.
- Aging curves: declined (2026-08-14). ZiPS already carries age; a second curve double-counts. Do not build one.
- Auto-refresh: left manual by choice. There is no ingestion step to schedule; do not add a cron that rebuilds stale data.
- Bug-history comments in `klab/` stay (compressed to <= 2 lines, FINDINGS #nn reference kept). Do not strip them.
- `out/keeper_lab.html`, `model_params.json`, `keeper_board_2027.csv`, `auction_sample.csv`, `price_features.csv`, `keeper_decisions.csv`, `price_model_holdout.csv`, `valuation_comparison.csv`, `trade_suggestions.json`, `app_reference.json`, `audit.txt`, `denominators_by_season.csv`, `sensitivity_*.csv` are committed on purpose. Everything else `run_all.py` writes is gitignored; do not add it back.
- Do not end a session with unpushed commits or with `~/Documents/Fantasy Baseball/keeper-lab/` (the read-only mirror) stale.
- Do not blend the comp-based auction estimate into `redraft_value` (superseded plan). Market price and production value stay separate quantities with separate names; see `docs/ROADMAP.md` item 1.
