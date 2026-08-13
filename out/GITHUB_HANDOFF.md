# Handoff: put Keeper Lab on GitHub

**Read this whole file before running anything.** It is written to be executed
by a fresh Claude session with no memory of how this project was built.

Your job is **packaging and publishing only**. You are not being asked to
improve the model, rerun analyses, fix findings, or write new features. If you
find something you believe is a bug, write it down at the end and tell Josh —
do not fix it.

---

## 0. Before you start: where are the files?

This is the failure mode that wastes the most time. **The project does not
exist in your session by default.** It was built in a previous cloud container
that no longer exists.

Check, in this order:

1. **Is a folder from Josh's computer connected?** Call
   `mcp__remote-devices__device_list_dir` on the likely paths
   (`~/Documents`, `~/PycharmProjects`, `~/Dropbox`). If you can see file
   contents rather than just names, you have access. Look for a folder
   containing `klab/config.py` and `out/HANDOFF.md`.
2. **Did Josh attach `keeper_lab_v18.zip`?** Check the uploads directory. If so,
   unzip it into your working directory and work there — but note the results
   will need to be delivered back, so prefer option 1 or 3.
3. **Neither?** Ask Josh to either (a) connect the folder containing the
   project, or (b) attach the zip. Then stop and wait. **Do not reconstruct the
   project from documentation. Do not write code from scratch.** If the files
   are not present, there is nothing to publish.

**Strongly prefer working directly in the folder on Josh's computer** via
`mcp__remote-devices__device_bash`. That way the git repository lives on his
disk permanently and the zip cycle ends. If you can only work from the zip in
the cloud container, say so explicitly in your final message, because the
repository you create will disappear when the session ends unless it is pushed.

---

## 1. What you are publishing

A Python project that values fantasy baseball players for a specific keeper
league. Roughly:

```
klab/          9 Python modules — the model
scripts/       14 scripts — build, validate, analyse, build the app
tests/         35 pytest invariants
app/           template.html (the UI) + verify.mjs (browser-vs-pandas check)
R/             tidyverse translation of the statistical core
out/           documentation + generated CSVs + keeper_lab.html
data/          input CSVs (see §3 — probably excluded)
README.md
```

Sanity-check before publishing. From the project root:

```bash
PYTHONPATH=. python3 -m pytest tests/ -q     # expect: 35 passed
```

If tests fail, **stop and report**. Do not publish a broken build and do not try
to fix the model.

---

## 2. Josh's context (do not get this wrong)

- He is an applied behavioural scientist with a fresh PhD, job-searching. This
  repository is a **portfolio artifact** as much as a working tool. The README
  and the documentation in `out/` are the product; the code is the evidence.
- He knows statistics deeply and software conventions barely. Explain any git
  concept you invoke, in one clause, the first time.
- He is direct and dislikes padding. Report what you did, flag what you are
  unsure about, stop.
- **Never determine or reference which team in the league is his.** Use
  `Pookie 2.0` as the worked example if one is needed. This constraint has held
  across the whole project.

---

## 3. Decisions to make before pushing — ask Josh, do not guess

### 3a. Public or private repository?

Recommend **public** — the portfolio value is the point, and a private repo
cannot be linked in an application. But confirm with him.

### 3b. Does `data/` go in? (This one matters.)

The `data/` folder contains **FanGraphs projection exports (ZiPS, Depth
Charts)** and CBS league exports. FanGraphs' terms do not clearly permit
redistributing bulk projection data, and a public repo is redistribution.

**Default recommendation: exclude `data/` from a public repo.** Instead:

- add `data/` to `.gitignore`
- write `data/README.md` (this file *is* committed) listing exactly which
  exports are needed, with the FanGraphs page each comes from and the expected
  filename, so anyone can reproduce it
- confirm the repo still tells a complete story without the raw inputs — it
  does, because `out/` contains the generated results and the documentation

If Josh wants it public *and* self-contained, that is his call to make, not
yours. Ask.

### 3c. Repository name

Suggest `keeper-lab`. Confirm.

---

## 4. The mechanics

### 4.1 Git, in four sentences (for Josh, if he asks)

Git records **snapshots of a whole folder over time**. Each snapshot is a
*commit* with a message saying why. The folder on his computer is the
*repository*; GitHub holds a synchronised copy called the *remote*. `push`
sends local commits to GitHub; `pull` brings GitHub's back.

### 4.2 Authentication — you cannot do this part

You cannot log into GitHub as Josh. One of these has to happen:

- **Preferred:** Josh runs `gh auth login` in his own terminal (the GitHub CLI;
  install with `brew install gh` on a Mac) and follows the browser prompt. Then
  `gh` works for you afterwards in that folder.
- **Alternative:** Josh creates an empty repository at github.com/new and gives
  you the URL. You then set the remote and push — he will be prompted for
  credentials on the first push.

Ask which he prefers. Do not attempt to store, request, or handle a personal
access token in the transcript.

### 4.3 The `.gitignore`

Create this at the project root **first**, before `git add`. It lists files git
should never track — generated artifacts, dependencies, OS clutter.

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.ipynb_checkpoints/
venv/
.venv/

# Node (the app's verifier)
app/node_modules/
app/package-lock.json

# OS
.DS_Store

# Raw data — see data/README.md for how to regenerate.
# Third-party projection exports are not ours to redistribute.
data/

# Generated outputs are committed deliberately: the documentation in out/
# is the portfolio artifact and must be readable without running anything.
```

Note the last comment is doing real work — **`out/` is intentionally committed.**
The normal convention is to ignore generated files; here the generated files are
the point. Keep `out/*.md`, `out/*.csv`, `out/keeper_lab.html`. You may exclude
`out/snapshots/` if it is large.

### 4.4 Commands

Run from the project root. If working on Josh's machine, run these through
`mcp__remote-devices__device_bash`.

```bash
git init
git add .
git status                    # READ THIS. Confirm no data/ and no node_modules.
git commit -m "Keeper Lab: league-calibrated valuation engine for a 5x5 roto keeper auction"

# after Josh has authenticated (§4.2):
gh repo create keeper-lab --public --source=. --remote=origin --push
# or, if he made the repo manually:
git remote add origin https://github.com/<his-username>/keeper-lab.git
git branch -M main
git push -u origin main
```

**Check `git status` output before committing.** If it lists thousands of files
or anything under `data/` or `node_modules/`, the `.gitignore` is not working —
fix it before the commit, because removing files from git history afterwards is
genuinely painful.

### 4.5 GitHub Pages (optional, free, do it if Josh wants a link)

Publishes `out/keeper_lab.html` at a public URL. Static hosting only — it serves
files, it never runs Python.

1. In the repo on github.com: **Settings → Pages → Source: Deploy from a
   branch → `main` → `/ (root)` → Save.**
2. Wait ~2 minutes.
3. The app is at `https://<username>.github.io/keeper-lab/out/keeper_lab.html`

Tell Josh the URL. Note that the page is **public and contains the league's
data** — that is fine for fantasy baseball but he should know.

---

## 5. The README

The repo has a `README.md` already and it is good. **Do not rewrite it.** Make
only these edits:

1. If `data/` is excluded, add one line under the install block:
   *"Raw projection and league exports are not redistributed — see
   `data/README.md` for the exact files needed."*
2. Add the GitHub Pages link near the top, if Pages was set up.
3. Verify every relative link in the README resolves (`out/HANDOFF.md`,
   `out/FINDINGS.md`, etc.). GitHub renders these as clickable; a broken one
   looks careless.

Do not add badges, a licence, a contributing guide, or a code of conduct unless
Josh asks. They are noise on a portfolio repo.

---

## 6. What "done" looks like — verify, then report

Check each and report the result:

- [ ] `PYTHONPATH=. python3 -m pytest tests/ -q` → 35 passed
- [ ] `git status` clean after commit; `data/` and `node_modules/` untracked
- [ ] repository visible at its GitHub URL
- [ ] README renders on GitHub with working links to `out/*.md`
- [ ] `out/keeper_lab.html` present in the repo (it is the headline artifact)
- [ ] if Pages enabled: the URL loads and the app is interactive
- [ ] the git repository lives on Josh's own disk, not only in a cloud container

Final message to Josh: the URL, what was excluded and why, and anything you
noticed but did not touch. Keep it to a few sentences.

---

## 7. Do not

- Do not modify anything in `klab/`, `scripts/`, `tests/`, or `R/`.
- Do not rerun `run_all.py` and commit different numbers. The committed outputs
  match the documented findings; regenerating them creates a diff nobody asked
  for. If you must rebuild, rerun the tests and say so.
- Do not edit `out/*.md`. Those documents are the deliverable and they were
  written deliberately, retractions and all.
- Do not add a licence file without asking. It is a legal choice, not a
  formatting one.
- Do not "clean up" the code. The comments explaining past bugs are load-bearing
  — they are the record of how the model got right.
- Do not invent numbers. If you need a figure, read it from `out/`.
