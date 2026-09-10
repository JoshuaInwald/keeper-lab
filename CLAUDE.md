# Keeper Lab: repo instructions for Claude

Read `CONSTRAINTS.md` and `HANDOFF.md` before doing anything. If the ask is a trade, a keeper call, a price, or "what should team X do", go straight to `docs/WORKFLOWS.md` and run the recipe; do not hand-calculate.

## What this repo is
- `klab/`: the engine. `scripts/run_all.py` rebuilds every output; `scripts/build_app.py` inlines a snapshot into `out/keeper_lab.html` (single file, no server, opens on a phone).
- `out/`: committed build artifacts (the app, `model_params.json`, two core tables, trade suggestions, audit). Everything else the scripts write is gitignored.
- `docs/`: METHODS (how), FINDINGS (results, numbered #1-#81, cited from code comments), MODEL-REVIEW (the 2026-09-09 bottom-up review: error sources, projection calendar), UI-REVIEW (same process on the presentation layer, same day), ROADMAP (next), WORKFLOWS (recipes), SESSION-LOG (history), EXPERT-REVIEW (question set for the league expert), ASSESSMENT-BRIEF (a closed phase, kept as a stub), constitution.txt (league rules).
- `data/`: gitignored working copy of raw exports; master copies in `~/Documents/Fantasy Baseball/`. `data/README.md` says what each file is and how often it needs refreshing.

## Three surfaces (keep in sync; a change that reaches one is not done)
1. **Working tree on the Mac**: `~/PycharmProjects/keeper-lab`. Where edits and commits happen. Python 3.11 venv at `.venv311/`.
2. **GitHub**: `JoshuaInwald/keeper-lab`, public, branch `main`, remote `origin`. Cloud/Cowork sessions and device_bash can fetch but cannot push (no credential); pushes run from Josh's own terminal.
3. **Read-only mirror**: `~/Documents/Fantasy Baseball/keeper-lab/`, an rsync of the tracked tree next to the raw exports. Never edit there.

Every session ends with: `./check_sync.sh` clean (or a "Run from your terminal" block with the exact `git push`), then the mirror refreshed:
```
rsync -a --delete --exclude='.git' --exclude='.venv311' --exclude='node_modules' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='*.pyc' --exclude='data/' ~/PycharmProjects/keeper-lab/ "$HOME/Documents/Fantasy Baseball/keeper-lab/"
```

## Runtime facts (do not guess)
- Needs Python 3.11+ or scipy >= 1.9 (older scipy returns `spearmanr` as a tuple; one test fails silently).
- Build: `PYTHONPATH=.:scripts python3 scripts/run_all.py` (~3 s cold). Tests: `PYTHONPATH=. python3 -m pytest tests/ -q` (64 tests, 3-6 min; `test_build_payload` dominates). App check: `cd app && npm i playwright@1.56.1 && cd .. && node app/verify.mjs` (23 checks; JS re-implementation must match pandas on 25 quantities). `build_app.py` takes several minutes since #82 (per-variant overlay rebuilds and bootstraps).
- `scripts/build_trade_suggestions.py` (~2 min) is not in `run_all.py`; rerun it after any roster change or the app serves stale suggestions.
- `team_reports.py`, `run_all.py`, `estimate_auction_price.py` need `PYTHONPATH=.:scripts`.
- Committed outputs match the documented numbers. If a rebuild changes them, say so in the commit message. Float noise at 1e-13 across platforms is normal; restore from HEAD rather than commit it.
- Snapshots (`klab.api.write_snapshot()`) go to `out/snapshots/`, gitignored, local archive only.
- The app's JS re-implements rest-of-season standings only; every dollar value is computed server-side once. `out/app_reference.json` is the byte-diff reference.

## Workflow rules
- One deliverable per session. Model changes get a `docs/FINDINGS.md` entry (next number) with the before/after numbers, a `docs/SESSION-LOG.md` line, and a `HANDOFF.md` update.
- Before changing a valuation formula: record the current board (`build_board()` to CSV), change, diff, and report flips in keep/cut calls, not just correlations.
- New empirical claims go through leave-one-season-out or split-half checks before they are called findings (FINDINGS #7 is the cautionary tale).
- Commit messages: imperative, one line, what changed. No emoji.
- Cosmetic UI problems get one attempt, then ship with a note.

## Style
- Docs: dense, tables, declarative, no hedging filler, no emoji, no em-dashes. Worked-example team is `Pookie 2.0`; never identify Josh's team.
- Code: comments state the invariant and the bug it guards in <= 2 lines with the FINDINGS #nn reference.

## Session playbook
- Start: read `HANDOFF.md` "Next session: start here"; `ls data/`; `git status`; `./check_sync.sh`.
- Cowork sessions: request folder access and delete permission for `~/PycharmProjects/keeper-lab` up front (git needs unlink for `index.lock`). device_bash has pandas/scipy after `pip3 install scipy statsmodels pytest`; Python there is 3.10, which is fine with scipy 1.15.
- Heavy reads (condensing docs, auditing modules) go to subagents with an explicit output shape and a cap; the main loop keeps writes and decisions.
- Cloud clone pattern (used 2026-09-07): clone origin in the cloud container, stage `data/*.csv` (29 files, ~5 MB) with `device_stage_files`, run tests and agents there, then move the result to the Mac as one `git format-patch` bundle applied with `git am`, commit on the Mac, Josh pushes.
- Close-out, every session: what was done; which surfaces were touched (Mac commit, GitHub push, mirror) and which were not; "Run from your terminal" block; three next-step options with size estimates.
