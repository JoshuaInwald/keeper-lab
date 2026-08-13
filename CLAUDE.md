# Keeper Lab — project notes for future sessions

Player-valuation engine for a private 10-team 5×5 roto keeper auction league.
Full context lives in the docs, not here — read `README.md` first, then
`out/HANDOFF.md` (current state), `out/LAB_NOTEBOOK.md` (bugs found, forks
tested, why the code looks like this), `out/ROADMAP.md` (what's next),
`out/FINDINGS.md` (results). `out/ORIGINAL_HANDOFF.md` is the pre-build
planning doc — superseded, kept for history only.

## Three places, three jobs — don't blur them

1. **`~/Documents/Fantasy Baseball/`** — the master copy of every raw input
   (FanGraphs exports, CBS exports). Not this repo. Edited by hand when Josh
   re-exports something.
2. **This repo's `data/`** — a working copy, gitignored, never on GitHub.
   Copied from (1) when a fresh build is needed. See `data/README.md` for
   which file needs refreshing how often, and the source-of-truth table.
3. **This repo's everything else** (`klab/`, `scripts/`, `out/`, `README.md`,
   `R/`, `app/`) — tracked in git, pushed to
   [github.com/JoshuaInwald/keeper-lab](https://github.com/JoshuaInwald/keeper-lab)
   (public). This is what a future session sees whether it starts from this
   folder or from a fresh `git clone` — so it has to actually be pushed, not
   just saved locally.

## Before ending any session that touched tracked files

Run `./check_sync.sh`. It fails loudly if there are uncommitted changes or if
local `main` and `origin/main` have diverged. A session that edits
`out/*.md`, `README.md`, or code and then stops without pushing leaves the
next session (local or cloned from GitHub) looking at stale docs and doesn't
know it.

## Conventions worth knowing before editing

- `out/*.md` are committed on purpose — they're the portfolio artifact, not
  disposable build output. Editing them is fine when it's genuinely updating
  the record (as this file's history shows); don't rewrite past findings to
  make them read better, and don't silently drop a retraction someone already
  made.
- Comments in `klab/` explaining a past bug are load-bearing — they're the
  record of how a wrong answer was caught. Don't clean them out.
- Don't invent a number. If you need one, it's in `out/` or comes from
  rerunning a script — `PYTHONPATH=.:scripts python3 scripts/run_all.py`
  regenerates everything.
- Don't rerun `run_all.py` and commit different numbers without saying so —
  the committed outputs match the documented findings; a silent diff is
  confusing later. If you rebuild, say so in the commit message.
- Needs Python 3.11+ (or scipy ≥1.9 specifically — see `out/LAB_NOTEBOOK.md`
  §8 for what happens on an older interpreter, which looks like a test
  failure and isn't one).
- Never determine or reference which team in the league is Josh's. Use
  `Pookie 2.0` as the worked example if one is needed — this has held across
  the whole project.
