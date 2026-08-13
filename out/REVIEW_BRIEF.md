# Review brief — Keeper League Lab

Paste this as the opening message to a fresh reviewer session, with
`keeper-league-lab-v5.zip` attached (or the folder connected).

---

You are reviewing a fantasy baseball valuation engine written by another
model. Attached is the full source and outputs. **Do not read any prior
conversation — everything you need is in the code and the three docs.**

**Orientation, in this order (~20 min of reading):**

1. `out/HANDOFF.md` — what the system does, league rules, how the four
   modelling steps fit together.
2. `out/LAB_NOTEBOOK.md` — what was tried and rejected, bugs found, and §5's
   list of open modelling forks. This is where the reasoning lives.
3. `out/FINDINGS.md` — the four empirical claims made from the data.
4. `klab/config.py` — every knob in one file. Read this before any other code.
5. Then `klab/denoms.py` → `auction.py` → `project.py` → `keeper.py` →
   `board.py`. Roughly 900 lines total.

**The setting.** A 10-team 5×5 rotisserie keeper auction, $260/team, 23 active
roster spots, 3-year contracts. The engine prices players in dollars using the
league's own auction history, ranks 2027 keeper decisions by surplus, and
evaluates trades. Data: 5 seasons of standings (10 teams × 10 categories),
5 auctions (677 purchases), FanGraphs player stats 2022–26, ZiPS projections
for 2027 and 2028.

## What I want from you

Rank by how much it would change a decision, not by how easy it is to spot.
Be adversarial about the statistics; the author is a social scientist who
wants real pushback, not validation.

**Priority 1 — is the inferential chain sound?**

The core logic is: *standings dispersion → what a category unit is worth in
standings points → regress realized production on auction price → dollars per
roto point → apply to projections → surplus vs keeper cost.* Each link is a
place to smuggle in an error. Specifically:

- `denoms.py::pooled_relative_dispersion` normalises each season's team totals
  by that season's mean and pools them, to estimate σ off 20 team-seasons
  instead of 10. Is that pooling valid given the seasons differ in roster
  volume? Is the constant `3.078/9` (E[range] for n=10, converted to an
  average adjacent gap) the right bridge from σ to "units per standings point"?
- `auction.py` regresses realized roto points on price paid and inverts the
  slope to get $/point. The claim is that this is unbiased because price is
  measured without error while production is noisy. Is the *inversion*
  legitimate, and is `E[production | price]` the right conditional for a
  keep-vs-cut decision (versus the reverse, which was tried and rejected —
  see LAB_NOTEBOOK §6)?
- `board.py::value_players` calibrates replacement level on unscaled
  projections but values keepers at full-season playing time. Is that
  consistent, or does it double-count anything?

**Priority 2 — are the four findings in `FINDINGS.md` actually supported?**

Especially §1 (the league underpays for saves, n=38, t=4.3) and §2 (all draft
surplus sits below $15). For each: is there a selection effect, a mechanical
artifact, or a confound that would explain it without the substantive claim?
§2 in particular compares realized value against price paid, which embeds a
bounded-downside asymmetry — is the conclusion robust to that?

**Priority 3 — code correctness in the places that would be silent.**

Merges that could duplicate or drop rows, groupby aggregations over the
hitter/pitcher concat (Ohtani shares one player id across both files), the
name resolver in `io.py`, sign conventions on ERA/WHIP (lower is better) and
on standings ranks. An inverted rank sign was already found and fixed once;
assume there are more.

**Priority 4 — what's missing.** The known gaps are listed in HANDOFF §6.
More useful is anything *not* on that list.

## Known-weak spots — confirm or refute rather than rediscover

- The SV-punter exclusion is the largest single lever and rests on a judgment
  call. LAB_NOTEBOOK §5.
- A convexity claim was made and then retracted on a quadratic test
  (t = −0.01). LAB_NOTEBOOK §4.3. Was the retraction correct?
- ZiPS 2027 was exported mid-2026 and may already incorporate 2026 to date,
  in which case the 50/50 blend with 2026 actuals double-counts that season.
  Unverified. Can you tell from the data whether it does?
- Denominators are fitted on 2 seasons (2024–25) on the theory that the league
  changed in 2024. n=20 team-seasons. Too few?

## Output format

A ranked list. For each: what's wrong, the failure mode in concrete terms
(which player or decision comes out wrong and by how much), your confidence,
and the minimal fix. Say plainly if a claim is fine — false positives cost me
more than misses here.
