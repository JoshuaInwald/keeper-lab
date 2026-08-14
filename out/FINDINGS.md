# Findings

Empirical results about how this league actually behaves. Methods and caveats
in `LAB_NOTEBOOK.md`.

<details>
<summary><strong>Contents</strong> (53 sections — click to expand)</summary>

1. [Saves look underpriced — but only if you assume you're competing in them](#1-saves-look-underpriced--but-only-if-you-assume-youre-competing-in-them)
2. [Cheap players out-earn expensive ones — but this is mostly arithmetic, not a market inefficiency](#2-cheap-players-out-earn-expensive-ones--but-this-is-mostly-arithmetic-not-a-market-inefficiency)
3. [The auction exchange rate is decaying fast](#3-the-auction-exchange-rate-is-decaying-fast)
4. [Half the 5×5 categories barely repeat year to year](#4-half-the-55-categories-barely-repeat-year-to-year)
5. [Denominators: what one standings point costs (2027)](#5-denominators-what-one-standings-point-costs-2027)
6. [How much do the modelling choices actually matter?](#6-how-much-do-the-modelling-choices-actually-matter)
7. [The exchange rate is NOT stably estimated (and I should have checked sooner)](#7-the-exchange-rate-is-not-stably-estimated-and-i-should-have-checked-sooner)
8. [No evidence that bidders overpay for particular MLB teams](#8-no-evidence-that-bidders-overpay-for-particular-mlb-teams)
9. [What separates the good teams: efficiency, not spending](#9-what-separates-the-good-teams-efficiency-not-spending)
10. [Keep-vs-cash: cutting a player does not refund his value](#10-keep-vs-cash-cutting-a-player-does-not-refund-his-value)
11. [The projection source matters as much as any modelling knob](#11-the-projection-source-matters-as-much-as-any-modelling-knob)
12. [Which results use which seasons](#12-which-results-use-which-seasons)
13. [Contracts are options, not obligations (bug, now fixed)](#13-contracts-are-options-not-obligations-bug-now-fixed)
14. [Waiver value is now a three-way switch, and the high setting fails a smell test](#14-waiver-value-is-now-a-three-way-switch-and-the-high-setting-fails-a-smell-test)
15. [Positional adjustment: built as a toggle, off, and currently unusable](#15-positional-adjustment-built-as-a-toggle-off-and-currently-unusable)
16. [CORRECTION: the keeper-count "tension" was my error](#16-correction-the-keeper-count-tension-was-my-error)
17. [The auctions did not happen in the same world](#17-the-auctions-did-not-happen-in-the-same-world)
18. [Z-scores: an independent check, and a surprise about roster construction](#18-z-scores-an-independent-check-and-a-surprise-about-roster-construction)
19. [RETRACTION: the keeper-count mechanism is not identified](#19-retraction-the-keeper-count-mechanism-is-not-identified)
20. [Unrostered players worth having](#20-unrostered-players-worth-having)
21. [External validation against CBS's own roto rank](#21-external-validation-against-cbss-own-roto-rank)
22. [Experiments: real error bars on the headline numbers](#22-experiments-real-error-bars-on-the-headline-numbers)
23. [The constitution, finally read — three rule corrections](#23-the-constitution-finally-read--three-rule-corrections)
24. [The final-year extension was priced at one year when the rule allows two](#24-the-final-year-extension-was-priced-at-one-year-when-the-rule-allows-two)
25. [Two final-year contracts don't reconcile against the draft record — unresolved](#25-two-final-year-contracts-dont-reconcile-against-the-draft-record--unresolved)
26. [Partial-2026 denominator exclusion: the rate-vs-counting split was a proxy for something else](#26-partial-2026-denominator-exclusion-the-rate-vs-counting-split-was-a-proxy-for-something-else)
27. [Replacement level, revisited: the field-standard comparison, a new sanity check, and confirming the clean test is still genuinely blocked](#27-replacement-level-revisited-the-field-standard-comparison-a-new-sanity-check-and-confirming-the-clean-test-is-still-genuinely-blocked)
28. [Reliability refit found a real bug: BB and H were both silently set to WHIP's number](#28-reliability-refit-found-a-real-bug-bb-and-h-were-both-silently-set-to-whips-number)
29. [Depth-vs-stars, redone with share of production](#29-depth-vs-stars-redone-with-share-of-production-the-hypothesized-cleanup-only-half-worked)
30. [The headline ±38% uncertainty band was computed around the wrong point estimates](#30-the-headline-38-uncertainty-band-was-computed-around-the-wrong-point-estimates)
31. [A second, live copy of the same season-set bug: `teams_per_category`](#31-a-second-live-copy-of-the-same-season-set-bug-teams_per_category)
32. [General review of the modules the earlier fixes didn't touch](#32-general-review-of-the-modules-the-earlier-fixes-didnt-touch)
33. [Extension eligibility was applied to codes "2" and "3", not just "1"](#33-extension-eligibility-was-applied-to-codes-2-and-3-not-just-1)
34. [A win-now metric that isn't a team-standings swap: ROS value over replacement](#34-a-win-now-metric-that-isnt-a-team-standings-swap-ros-value-over-replacement)
35. [A comp-based next-auction price estimator — a deliberately separate tool](#35-a-comp-based-next-auction-price-estimator--a-deliberately-separate-tool)
36. [A retained-but-unused extension right has zero value in the model, for any non-final-year contract](#36-a-retained-but-unused-extension-right-has-zero-value-in-the-model-for-any-non-final-year-contract)
37. [Uncertainty bands were already done in the app — the roadmap said otherwise](#37-uncertainty-bands-were-already-done-in-the-app--the-roadmap-said-otherwise)
38. [Roster update — two real trades, one FA move, resolved cleanly against 268-of-277 players untouched](#38-roster-update--two-real-trades-one-fa-move-resolved-cleanly-against-268-of-277-players-untouched)
39. [F-contract players were never actually extendable right now — a bigger correction than #33](#39-f-contract-players-were-never-actually-extendable-right-now--a-bigger-correction-than-33)
40. [A trade-finder feature: precomputed suggestions, three scenarios, three real bugs caught building it](#40-a-trade-finder-feature-precomputed-suggestions-three-scenarios-three-real-bugs-caught-building-it)
41. [The trade finder was non-deterministic across identical reruns — caught checking auto-refresh safety](#41-the-trade-finder-was-non-deterministic-across-identical-reruns--caught-checking-auto-refresh-safety)
42. [A projection-basis selector — three payloads, swapped client-side, no rebuild](#42-a-projection-basis-selector--three-payloads-swapped-client-side-no-rebuild)
43. [Auction-estimator UI integration — a player-card panel, and a real bug it exposed on the way in](#43-auction-estimator-ui-integration--a-player-card-panel-and-a-real-bug-it-exposed-on-the-way-in)
44. [UI audit: a stale pre-#39 status string, a missing IL/LOCKED tag, and two confirmed false alarms](#44-ui-audit-a-stale-pre-39-status-string-a-missing-illocked-tag-and-two-confirmed-false-alarms)
45. [A blended 2026 rest-of-season signal, and a real bug in the first version](#45-a-blended-2026-rest-of-season-signal-and-a-real-bug-in-the-first-version)
46. [A rest-of-2026 basis toggle in the app — Standings and Trade only, never a dollar value](#46-a-rest-of-2026-basis-toggle-in-the-app--standings-and-trade-only-never-a-dollar-value)
47. [ROS value on the Keeper Board / Free Agents tables — a second toggle stacked on the first](#47-ros-value-on-the-keeper-board--free-agents-tables--a-second-toggle-stacked-on-the-first)
48. [Historical standings, 2022-2025, normalised to current franchise names](#48-historical-standings-2022-2025-normalised-to-current-franchise-names)
49. [2027 standings from keeper sets alone — and a bad replacement-line pick caught before shipping](#49-2027-standings-from-keeper-sets-alone--and-a-bad-replacement-line-pick-caught-before-shipping)
50. [The Intuition tab — manual player shading, sandboxed, split into an exact half and an approximate half](#50-the-intuition-tab--manual-player-shading-sandboxed-split-into-an-exact-half-and-an-approximate-half)
51. [Playing time gets its own weight, decoupled from the rate/talent blend](#51-playing-time-gets-its-own-weight-decoupled-from-the-ratetalent-blend)
52. [Positional adjustment for catchers and shortstops — and a surprise: both positions are deep, not scarce](#52-positional-adjustment-for-catchers-and-shortstops--and-a-surprise-both-positions-are-deep-not-scarce)
53. [Direction-aware pitcher playing-time trust, an upside_ft split, and a second copy of #52's own bug](#53-direction-aware-pitcher-playing-time-trust-an-upside_ft-split-and-a-second-copy-of-52s-own-bug)

</details>

---

## 1. Saves look underpriced — but only if you assume you're competing in them

**Revised 2026-08-13 after external review. The original version of this
finding was overstated; see the conditionality below before using it.**

Closers identified by **prior-season saves** — an observable available before
the auction — beat the price they command by **+2.23 roto points**
(HC1 t = 3.75, n = 38), at a mean price of $7.90.

| player type (ex ante) | n | mean $ | residual vs pooled fit |
|---|---|---|---|
| closer | 38 | 7.9 | **+2.23** |
| hitter | 401 | 11.8 | +0.09 |
| other pitcher | 238 | 10.9 | −0.58 |

Actual purchases: Aroldis Chapman $2 → 13.5 roto points; Trevor Megill $1 →
10.3; Raisel Iglesias $3 → 9.1.

**Why the conditional version is real.** Team save totals are sharply bimodal — 2025 ran
`[0, 57, 61, 70, 70, 72, 76, 82, 91, 98]`. One team punts, the other nine pack
into a 41-save band where about five saves buys a standings point. "Never pay
for saves" is fantasy orthodoxy; in a league where everyone believes it, saves
become the cheapest roto points available.

**The finding is conditional, not unconditional.** Everything above assumes
save-punting teams are excluded from the SV denominator. Rerun with all ten
teams in:

| SV denominator field | closer excess | t | significant? |
|---|---|---|---|
| punters excluded (SV < 15 dropped) | **+2.23** | 3.75 | yes |
| all ten teams included | **+0.92** | 1.82 | no |

Including punters does not "roughly halve" the effect as an earlier draft of
this document claimed — it removes two-thirds of it and all of the
significance. Read the result as *"saves are cheap for a team that intends to
compete in saves"*, not as an unconditional market inefficiency.

The effect is otherwise robust: it holds in every price band, survives
flexible price controls (+2.86, t=4.5), and survives clustering by player
(27 unique players).

**Two earlier errors in this test, both now fixed.** It originally classified
closers by *realized* saves, which selects on the outcome. And the SV
denominator applied the 10-team range constant to a field of 8–9 teams after
punters were dropped, overvaluing every save by 9–19%; correcting it moved the
headline from +2.67 to +2.23.

---

## 2. Cheap players out-earn expensive ones — but this is mostly arithmetic, not a market inefficiency

**Heavily revised 2026-08-13 after external review. The original framing
("all the draft surplus is at the bottom of the price chain") over-claimed.**

Every auction purchase 2022–26, paired with what its realized production was
worth on the redraft dollar scale:

| price paid | n | mean paid | value delivered | surplus | value per $ |
|---|---|---|---|---|---|
| $1 | 129 | $1.00 | $5.20 | **+$4.20** (t=5.2) | **5.20×** |
| $2–3 | 70 | $2.51 | $5.80 | +$3.29 (t=2.5) | 2.31× |
| $4–5 | 61 | $4.43 | $6.92 | +$2.50 | 1.56× |
| $6–10 | 131 | $7.99 | $9.76 | +$1.77 | 1.22× |
| $11–15 | 84 | $13.17 | $13.43 | +$0.27 | 1.02× |
| $16–20 | 76 | $17.96 | $14.69 | −$3.27 | 0.82× |
| $21–30 | 90 | $25.13 | $24.52 | −$0.61 | 0.98× |
| $31+ | 36 | $35.61 | $32.31 | −$3.30 | 0.91× |

**Break-even is $11–15.** Every dollar above that buys less than it costs.

### Why most of this gradient is not a discovered fact

External review established three things that gut the strong reading:

1. **Non-closer residuals from the price regression are flat across price
   bands** (−0.17, −0.20, −0.18, −0.11). The market buys expected production
   at a constant rate everywhere. There is no bottom-end inefficiency.
2. **The gradient is largely an identity.** Surplus per dollar is
   `usd_per_rp × slope − 1`, a constant negative wedge between two
   calibrations. The bucket pattern follows from that plus the $0 floor's
   Jensen lift, measured at +$7.7 for $1 players against +$4.5 at $31+. The
   bounded-downside asymmetry is not a footnote; it is roughly 40% of the
   spread.
3. **Median surplus is negative in every bucket.** 60% of $1 buys return
   exactly $0. And the top bucket flips sign by era: +$5.4 in 2022–23 against
   −$6.7 in 2024–26, n≈45 each.

**What actually survives:** big tickets do not out-earn their price, and the
surplus that exists is a fat right tail on cheap lottery tickets. That is a
portfolio-variance statement, not evidence of mispricing. "Break-even at
$11–15" is a property of the model's constants, not a market fact.

The strategic reading also has to respect the 23-slot constraint — you roster
players, not surplus-per-dollar, so "spread the money" does not follow
directly from the table.

**This still refutes the intuition that the price ceiling leaves value unclaimed.**
No individual player has ever gone above $45 (season maxima: 42, 45, 39, 36,
43), while the model says the best *known* player is worth $60–80. But that is
a hindsight number. Ex ante nobody knows who the best player will be, and the
$35 a team spends on a star buys an expected $32.31 because some stars break.
The ceiling is approximately rational.

**There is no scarcity premium to model.** Adding a quadratic term to
`roto_points ~ $` gives a coefficient of −0.00001, **t = −0.01**. Price buys
production at a constant rate across the whole range.

**Caveat.** These are realized (ex post) values, so they mix systematic
mispricing with the fact that cheap players have bounded downside — a $1 bust
costs $1, a $35 bust costs $35. Both effects are real and decision-relevant,
and a risk-neutral manager should care about the mean, which is what's shown.

---

## 3. The auction exchange rate is decaying fast

| | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| $ per roto point | 4.12 | 4.79 | 6.41 | 8.17 | 10.20 |
| free production at $0 (roto pts) | 1.71 | 2.43 | 3.42 | 3.59 | 3.52 |

A dollar bought 2.5× as much production in 2022 as in 2026, and the amount you
get for free has doubled. Both move the way you'd expect if keepers are
absorbing the elite talent and leaving the auction a scrum for replacement-level
players: eligible keepers went from 25 in 2022 to 100 in 2026.

**Implication.** Keeper surplus is worth more every year, and the gap between a
good keeper decision and a bad one is widening. If the trend continues, 2027
dollars buy about $13/point and every current keeper is more valuable than the
board says.

---

## 4. Half the 5×5 categories barely repeat year to year

Year-over-year reliability of player rates on this dataset:

| stat | r | | stat | r |
|---|---|---|---|---|
| SB/PA | 0.739 | | K/IP | 0.701 |
| HR/PA | 0.607 | | WHIP | 0.237 |
| AVG | 0.436 | | ERA | 0.176 |
| R/PA | 0.425 | | **W/IP** | **0.151** |
| RBI/PA | 0.380 | | | |

(hitters 250+ PA in consecutive years, n=693; pitchers 40+ IP, n=785)

**Wins carry essentially no signal** (R² = 0.023). A pitcher's win total tells
you about his team, not about him. ERA (0.176) and WHIP (0.237) are barely
better — for pitchers, only strikeouts genuinely persist.

**Practical consequences:**

- Never pay for a pitcher's ERA/WHIP/W track record; pay for strikeouts.
- Steals and home runs are the most projectable hitting categories, which is
  part of why speed is expensive.
- Any projection blending observed performance with a regressed projection
  must weight by reliability, or it launders noise as signal.

---

## 5. Denominators: what one standings point costs (2027)

| R | HR | RBI | SB | AVG | W | SV | K | ERA | WHIP |
|---|----|-----|----|----|---|----|---|-----|------|
| 39.4 | 15.4 | 38.7 | 20.4 | .0023 | 3.79 | 6.57 | 59.1 | .0431 | .0108 |

Cross-rates worth carrying around: **1 HR ≈ 1.3 SB ≈ 2.6 R ≈ 2.5 RBI.**
**6.6 saves = 59 strikeouts = 3.8 wins.** (The SV figure was 5.53 before the
field-size correction in §1 — every closer was 19% overvalued.) For a full-time hitter, ~30 points
of batting average is one standings point; for a 180-inning starter, ~0.34 of
ERA or ~0.086 of WHIP.


---

## 6. How much do the modelling choices actually matter?

Six judgment calls in this model had no clearly right answer. `scripts/sensitivity.py`
rebuilds the whole board under each alternative and counts how many keep-or-cut
decisions change — the only impact that reaches a decision.

**Rerun 2026-08-14** after this session's playing-time-decoupling (#51/#53) and
positional-adjustment (#52) work — both changed the model's shape enough to
move these numbers and, in one case, change which variant ranks highest. The
table below is the current, authoritative run; the paragraph after it is
kept for the record of what this looked like before.

| variant | keep/cut flips | % of roster | Spearman | median \|Δ$\| | max \|Δ$\| | biggest mover |
|---|---|---|---|---|---|---|
| flat 50/50 blend instead of reliability/PT-decoupled | **20** | 7.3% | 0.907 | $0.74 | $23.15 | Jacob Misiorowski |
| denominators 2022–25 instead of 2024–26 | **10** | 3.6% | 0.978 | $0.31 | $30.42 | Paul Skenes |
| SV punters included | 5 | 1.8% | 0.984 | $0.19 | $13.73 | Cade Smith |
| auction window 2022–26 | **0** | 0% | 1.000 | $0 | $0 | — |
| no playing-time floor | **0** | 0% | 1.000 | $0 | $0 | — |
| no future discount | **0** | 0% | 1.000 | $0 | $7.47 | Paul Skenes |
| heavy discount (0.6) | **0** | 0% | 0.999 | $0 | $10.71 | Paul Skenes |

**29 of 275 rostered players (11%) flip on at least one choice. The other 89%
are a keep — or a cut — under every variant, and can be trusted outright.**

Four things worth knowing, updated for the current run:

1. **The rate/playing-time blend is now the single highest-stakes call** —
   reverting this session's #51 decoupling (one flat 50/50 weight for both
   rate and playing time, instead of the current per-purpose caps) flips 20
   keep/cut calls, more than any other variant tested. That's the clearest
   evidence yet that #51 wasn't cosmetic: the choice it made is genuinely
   load-bearing for real decisions, not just for point values.
2. **The denominator window dropped to second and got smaller** — 10 flips
   now, down from 17 in the pre-#51/#52 run. Plausible read: some of what
   used to look like denominator-window sensitivity was actually the
   undecoupled blend amplifying it; with playing time and rate handled
   separately, the denominator choice has less to compound with.
3. **The save-punter rule still moves dollars far more than decisions** — the
   SV denominator swings from 6.57 to 11.06 (+68%, Model tab) with punters
   included, and closers lose real value, but only 5 of 275 keep/cut calls
   actually flip. Matters enormously for *pricing* a closer in a trade,
   barely at all for whether to keep one — same conclusion as before, still
   holds.
4. **Four knobs are now fully decision-irrelevant, up from two.** The auction
   window and playing-time floor were already at zero flips; the discount-rate
   variants (both light and heavy) joined them this run, down from 3 and 1
   flips respectively. Another point in favor of this session's fixes: the
   model is now robust to more of the arbitrary judgment calls it used to be
   sensitive to, not just re-tuned to look better on the same ones.

*For the record — the pre-#51/#52 run (superseded by the table above):*
denominators 2022-25 and flat 50/50 blend each flipped 17 (6.2%, Spearman
0.951/0.940); SV punters and no-future-discount each flipped 3 (1.1%); heavy
discount flipped 1; auction window and no-PT-floor flipped 0; 34 of 275 (12%)
flipped on at least one choice.


---

## 7. The exchange rate is NOT stably estimated (and I should have checked sooner)

Split-half reliability within each season — fit $/roto-point on odd-numbered
purchases, then on even-numbered:

| season | odd half | even half | 95% CI on the full-season estimate |
|---|---|---|---|
| 2022 | $4.32 | $3.96 | 3.41 – 5.33 |
| 2023 | $4.01 | $6.16 | 3.89 – 6.20 |
| 2024 | $5.03 | $8.21 | 4.96 – 8.86 |
| 2025 | $6.80 | $12.02 | 5.60 – 14.55 |
| 2026 | **$6.55** | **$20.38** | **6.67 – 19.79** |

The pooled 2022–26 estimate is tight ($5.83, CI 5.13–6.74). Every single-season
estimate is not, and it gets worse as the auction thins: **2026's two halves
disagree by a factor of three.**

The *trend* is still real — the slope falls monotonically across five seasons,
which is not something noise produces — and it is independently corroborated
by the inflation accounting (§ RESEARCH.md 3). But the headline **$7.56 per
roto point carries an error bar of roughly ±40%**, not the ±2% its two decimal
places imply. Anywhere a dollar figure depends on it, treat the ranking as
solid and the level as approximate.

---

## 8. No evidence that bidders overpay for particular MLB teams

Tested directly, because the league is known to contain several Mets fans.
Regressing each purchase's residual (production minus what its price
predicted) on MLB team:

- **New York Mets: +0.28 roto points, t = 0.57, p = 0.567.** If anything Mets
  players have been mild *bargains*, not overpays. The hypothesis is not
  supported.
- **Joint F-test on all 30 team dummies: R² = 0.065, F = 1.37, p = 0.094.**
  Not significant. Whatever team-level pattern exists is indistinguishable
  from noise.

Individual teams that look extreme — TEX (−1.29, t=−2.71) and CIN (−1.28,
t=−2.18) overpaid, TBR (+1.92, t=2.93) and NYY (+1.65, t=2.12) underpaid —
should be read against 30 simultaneous tests. Four results past |t|=2 out of 30
is close to what chance delivers, and the joint test says don't reach for a
story.

---

## 9. What separates the good teams: efficiency, not spending

Correlation with 2026 standings points:

| factor | r |
|---|---|
| roto points per dollar committed | **+0.648** |
| share of production from keepers | +0.354 |
| share from free agents | −0.109 |
| **share from the auction** | **−0.540** |

The strongest single predictor is efficiency, and the strongest *negative* one
is dependence on the auction. The last-place team (NPB No Stars) drew the
highest share of its production from the 2026 auction, 36.3%; the league leader
(Pookie 2.0) drew the lowest, 20.6%, and the highest share from keepers, 45.3%.

This is the same fact as §2 and §3 seen from the team level: the auction is
where value goes to die in this league, and the teams that win are the ones
that assembled their roster somewhere else.

---

## 10. Keep-vs-cash: cutting a player does not refund his value

The single most decision-relevant thing in this document.

Cutting a keeper does not hand you his market value. It hands you his
**salary**, which you must then spend into an auction running **+48.7%
inflation** — so a dollar of budget buys **$0.67** of production, not $1.00.
The correct rule is therefore not `value > cost` but:

```
    keep if   value  >  keeper_cost / inflation
```

**30 of 275 rostered players flip from cut to keep** once this is priced in.
The flips are exactly the expensive stars the naive rule was rejecting:

| player | cost | value | naive surplus | vs-cash surplus | verdict |
|---|---|---|---|---|---|
| Pete Alonso | $27 | $22.8 | −$4.2 | **+$4.6** | keep |
| Ronald Acuña Jr. | $26 | $20.0 | −$6.0 | **+$2.5** | keep |
| Bryce Harper | $21 | $15.6 | −$5.4 | **+$1.5** | keep |
| Julio Rodríguez | $43 | $27.2 | −$15.8 | −$1.7 | now nearly break-even |

**Two caveats, both real.** The rule is self-referential: inflation depends on
how many players get kept, so if everyone adopts it, more keeping raises
inflation and makes keeping better still, up to a fixed point this model does
not solve for. And it sits awkwardly against history — the keeper files show
only 25–29 players kept league-wide in 2022–25. If keeping is this profitable,
either managers have been leaving money on the table, or those files are
incomplete, or the model overstates keeper value. That should be resolved
before acting on the marginal cases.


---

## 11. The projection source matters as much as any modelling knob

`PROJECTION_BASIS` in `config.py` rebuilds the whole board on a different view
of 2027. Three bases, same everything else:

| basis | keepers flagged | replacement | $/roto pt | flips vs blend |
|---|---|---|---|---|
| blend (default) | 79 | 4.14 | $6.66 | — |
| projection only (ZiPS 2027) | 67 | 4.42 | $7.42 | **34 (12.4%)** |
| 2026 actuals + ROS only | 74 | 4.13 | $5.69 | 15 (5.5%) |

**47 of 275 players — 17% — have a keep/cut call that depends on which view of
2027 you take.** Biggest swings: Garrett Crochet moves ±$23 between bases,
Misiorowski ±$18, Judge ±$15.

That puts the projection source on par with the denominator window as the
highest-stakes choice in the model, and it is the one a user is most likely to
have an opinion about. It belongs as a visible control in the app, not a
constant buried in a config file.

**Switching to a different projection system** (Steamer, THE BAT, ATC, Depth
Charts) is now a filename change — `PROJ_2027_HITTERS` and friends — because
any FanGraphs export shares the same column names. What is *not* yet solved:
those systems publish current-season projections, and ZiPS is the only one
that publishes multi-year out-year lines. A 2027 board built on Steamer would
need a different source for 2028, or would have to drop the multi-year term.


---

## 12. Which results use which seasons

Worth stating plainly, because the windows differ by purpose.

| quantity | seasons used | why |
|---|---|---|
| **denominators** (relative dispersion) | **2024–25 only** | dispersion regime changed in 2024 |
| league levels for 2027 denominators | 2024–25 | same |
| team volume baselines | 2024–25 | same |
| **$/roto point** (exchange rate) | **2024–26** | the rate decays; recent window is the live opportunity cost |
| scoring a *past* auction purchase | that season's own level × 2024–25 dispersion | a 2022 player is scored against 2022 conditions |
| draft price-chain analysis (§2) | **all 2022–26** | needs n; only 112–163 purchases per season |
| MLB-team bias test (§8) | **all 2022–26** | same |
| exchange-rate stability table (§7) | shown per season and pooled | that is the point of the table |
| save-persistence model | 2022–25 transitions | needs consecutive-year pairs |
| stat reliability | 2022–26 consecutive pairs | same |

So: **denominators are strictly 2024–25 as agreed.** The analyses that pool all
five seasons are the *descriptive* ones, where the alternative is 130 rows.
Where a pooled analysis drives a decision, §6 reports what changes if the
window moves.

---

## 13. Contracts are options, not obligations (bug, now fixed)

Multi-year surplus was summing every contract year with its sign, which
charged a team for seasons it would simply decline. Kazuma Okamoto, $11 with
two years of control and a $0 projection for 2028, was booked at **−$12.8**:
−$3.5 for 2027 plus −$9.35 for a 2028 nobody would keep him for.

You re-decide every winter. A year you would not exercise costs nothing.
Later years now clip at zero, so Okamoto reads **−$3.45** — the honest number.

Direction of the error: every multi-year contract was being penalised for its
own length, and the penalty was largest exactly where a player's projection
declines — ageing veterans on long deals. Those were the contracts the model
was most wrong about.

---

## 14. Waiver value is now a three-way switch, and the high setting fails a smell test

`WAIVER_VALUE` sets what "free" is worth. Replacement level is the best player
available for nothing, so richer waivers mean a higher bar and lower player
values.

| setting | anchored on | replacement | $/roto pt | keepers | flips vs low |
|---|---|---|---|---|---|
| **low** (default) | 230th projection — one per active slot | 4.14 | $6.66 | 85 | — |
| medium | 300th projection — this league rosters 275 and churns | 3.79 | $5.45 | 82 | 11 |
| high | median production of actual 2026 FA pickups (5.04) | 5.04 | **$16.04** | 91 | 32 |

**The high setting produces $16.04 per roto point against $7.56 from the
auction regression.** That is a factor-of-two disagreement with independent
market evidence, and it is the model telling you the setting is wrong: the
5.04 anchor comes from players teams picked up *after* they started producing.
It is an upper bound on waiver value, not an estimate of it.

`low` stays the default. `medium` is the defensible alternative and moves 11
decisions. Resolving this properly needs the counterfactual — what was
available on the wire *before* anyone knew — which needs transaction logs.

---

## 15. Positional adjustment: built as a toggle, off, and currently unusable

`POSITIONAL_ADJUSTMENT` exists and defaults to **False**. Two reasons.

**Empirical.** FanGraphs' 13-system test found the variants with the largest
positional adjustments finished last; Razzball tested four stances and
measured "very close to zero impact". The theoretical case is much stronger
than the measured effect.

**Practical, and decisive here.** Positions come only from the auction files:
**51% coverage of rostered players, and just 6 identified catchers where there
must be at least 10.** Enabling it raises a `RuntimeError` rather than
computing a catcher replacement level from six observations.

Where it *would* plausibly matter in this format is exactly where you'd
expect — catcher and middle infield, the two genuinely thin pools. To turn it
on: get a roster export with a position column (CBS publishes one) or a
FanGraphs positional-eligibility file. The remaining work is then about twenty
lines — group by position, take the (slots × 10)th player in each group.


---

## 16. CORRECTION: the keeper-count "tension" was my error

Earlier sections flagged an apparent contradiction — the model recommends ~80
keepers while "the keeper files show only 25-29 kept in 2022-25". **That was
wrong.** `keepers_2026.csv` holds 100 players across 10 teams, 6 to 12 each,
every team inside the league's 6-13 rule. Those are *actual* keepers, not an
eligibility list, and I mislabelled them.

There is no tension. 2026 kept 100; a 2027 recommendation of 80-85 is
**conservative**, not aggressive. The 2022-25 files showing 25-29 with some
teams at zero cannot be actual keeper sets under a 6-keeper minimum — they are
either partial or from a different rule regime, and **2026 is the only
relevant baseline for predicting 2027 behaviour**.

Everything downstream that leaned on the "tension" should be read as
strengthened, not weakened: keeping really is this profitable, and inflation
really is running high.

---

## 17. The auctions did not happen in the same world

The single most consequential thing on this page.

| season | keepers withheld | auction picks | total spent | $/roto point |
|---|---|---|---|---|
| 2022 | 25 | 137 | $1,604 | $4.16 |
| 2023 | 28 | 136 | $1,607 | $4.78 |
| 2024 | 29 | 163 | $1,813 | $6.36 |
| 2025 | 29 | 129 | $1,377 | $8.09 |
| **2026** | **100** | **112** | **$1,236** | **$9.98** |

**corr(keepers withheld, $/roto point) = +0.796.** The exchange rate is not
drifting for mysterious reasons — it tracks how much talent was withheld from
the pool, which is exactly the inflation mechanism seen from the player side.

This breaks the old default. `AUCTION_SEASONS = [2024, 2025, 2026]` pooled two
auctions with 29 keepers withheld against one with 100, and produced $7.56 per
roto point. **2027 will look like 2026, not like 2024.**

New default, `EXCHANGE_BASIS = "keeper_adjusted"`: fit $/point on keeper count
across all five auctions, then predict at the expected 2027 count.

```
$/pt = 4.19 + 0.0589 × keepers_withheld      (R² = 0.633)
   at 100 keepers → $10.08      at 110 → $10.67      at 120 → $11.26
```

**The 2027 exchange rate is $10.08 per roto point, not $7.56** — a 33%
correction, using every auction rather than throwing four of them away. Two
alternatives remain available: `"pooled"` (the old behaviour) and `"recent"`
(2026 alone, right regime but n=112 and split-halves that disagree threefold).

---

## 18. Z-scores: an independent check, and a surprise about roster construction

Roto points come from *standings* dispersion. Z-scores come from the *player*
distribution. They are built from different data, so agreement is evidence the
engine measures something real.

**Distribution of 2026 value across 274 rostered players:** mean 5.53 roto
points, sd 2.75, **skew just 0.12** — very nearly symmetric. The fat right tail
that fantasy intuition expects is not there.

| threshold | players | % | per team |
|---|---|---|---|
| z ≥ +3 | 0 | 0.0% | 0.0 |
| z ≥ +2 | 7 | 2.6% | 0.7 |
| z ≥ +1.5 | 16 | 5.8% | 1.6 |
| z ≥ +1 | 42 | 15.3% | 4.2 |
| z ≥ 0 | 131 | 47.8% | 13.1 |

**The cross-check passes: Spearman(standings points, summed player z) = +0.855**,
against +0.842 from the roto-point engine's own validation. Two independent
constructions, same answer.

### The surprise

| predictor of 2026 standings | Spearman |
|---|---|
| summed z | **+0.855** |
| count of players at z ≥ 1 | **+0.840** |
| count of players **below** average | **−0.755** |
| count of players at z ≥ 2 | **+0.141** |

**Having superstars barely predicts winning. Having lots of above-average
players does, and having few bad ones does almost as much.**

Pookie 2.0 won with **one** z≥2 player and only 8 below-average players on a
27-man roster. Lisbon Long Balls had **two** z≥2 players and finished 5th, with
12 below average. The Fighting Phils and NPB No Stars each carried 19 sub-
average players and finished 6th and 10th.

Caveat worth stating: z≥2 counts range only 0-2 per team, so that correlation
rests on very little variance and should not be over-read. The z≥1 and
below-average results are on much firmer ground.

### What difference-makers actually cost

| band | n | roto pts | worth in hindsight | paid at auction | current salary |
|---|---|---|---|---|---|
| below average | 143 | 3.60 | $1.84 | $11.95 | $10.43 |
| z 0-1 | 89 | 6.69 | $12.32 | $14.31 | $12.13 |
| z 1-2 | 35 | 9.16 | $23.37 | $16.57 | $14.23 |
| **z 2+** | **7** | **11.98** | **$42.21** | **$21.00** | **$18.71** |

The market pays $21 for a player who turns out to be worth $42, and $12 for a
player who turns out to be worth $1.84. But that is hindsight — **the market
cannot tell them apart in advance**, which is why the below-average group
commands almost as much money as the z 1-2 group.

### What this means for the 2027 draft

1. **There are ~7 genuine difference-makers league-wide and you cannot
   identify them in advance.** Paying up for one is a lottery ticket with
   roughly a 1-in-5 hit rate at the top of the price range.
2. **Avoiding below-average players matters nearly as much as acquiring good
   ones** (−0.755 vs +0.840), and it is far more controllable. 143 of 274
   rostered players were below average; the good teams simply rostered fewer.
3. **Depth over stars.** The z≥1 count predicts standings; the z≥2 count
   barely does. Combined with §2 — surplus concentrated below $15 — the
   strategy is a wide base of $1-15 players who project above average, not two
   or three $35 bets.
4. **This is in tension with §10 (keep-vs-cash).** Inflation says keep your
   expensive stars rather than cash them; the z-score evidence says roster
   construction beats star concentration. The resolution: keep expensive
   players whose *projection* is above average, cut the ones whose isn't —
   which is what the model already does, but it means the marginal call
   should lean on projected z, not on salary.


---

## 19. RETRACTION: the keeper-count mechanism is not identified

§17 claimed the exchange rate is driven by how many keepers are withheld, on
corr = +0.796. **Two problems, found by the audit in `scripts/audit.py`.**

**The keeper counts were wrong.** Two accounting identities say so:

| season | keepers in file | auction picks | slots unexplained | implied $/keeper |
|---|---|---|---|---|
| 2022 | 25 | 137 | **68** | **$39.8** |
| 2023 | 28 | 136 | **66** | **$35.5** |
| 2024 | 29 | 163 | 38 | **$27.1** |
| 2025 | 29 | 129 | **72** | **$42.2** |
| 2026 | 100 | 112 | 18 | $13.6 |

Keepers plus auction picks must roughly fill 230 active slots, and keeper
salaries plus auction spend must equal $2,600. Only 2026 satisfies both. A
league where the average keeper costs $42 — in a format whose entire point is
keeping players at a discount — is not credible. **The 2022–25 keeper files
are incomplete.** Backing the real counts out of the identities gives roughly
67–101 per season, not 25–29, so the dramatic "25 → 100" rise never happened.

**Even with corrected counts, the mechanism is unidentified.** With five
observations:

| correlate of $/roto point | r |
|---|---|
| keeper count from the files (wrong) | +0.796 |
| keeper count estimated from slots | +0.569 |
| keeper count estimated from budget | +0.752 |
| **season (a bare time trend)** | **+0.987** |

**Time fits better than any keeper measure.** Keeper count and season are
collinear, and n=5 cannot separate them. The inflation theory is a good story
and the accounting supports the *direction*, but this data cannot establish
that keeper count is the cause rather than a fellow traveller of whatever else
changed since 2022.

**What survives:** the exchange rate has risen monotonically for five seasons
and 2026 came in at $9.98. Predicting ~$10 for 2027 is sound — it is
essentially "use last year, maybe a touch more". The *causal* dressing was
not.

`EXCHANGE_BASIS = "keeper_adjusted"` still produces $10.08, which is the right
number for the wrong stated reason. Read it as trend extrapolation.

---

## 20. Unrostered players worth having

**Best available for 2027** (projected, nobody's roster):

| player | 2027 roto | value | note |
|---|---|---|---|
| Spencer Schwellenbach | 5.82 | $12.20 | 126 IP, 3.41 ERA, 1.06 WHIP |
| Justin Crawford | 5.50 | $10.06 | 26 SB, .28 AVG |
| Esteury Ruiz | 5.43 | $9.64 | **45 SB** in 377 PA |
| Jakob Marsee | 5.36 | $9.16 | 31 SB |
| Steven Kwan | 5.26 | $8.49 | .28 AVG, 628 PA |

**Drafted in 2026, since dropped** — these carry a two-year contract at their
draft price if re-acquired, which is the cheapest keeper equity available:

| player | draft price | 2027 value | surplus if re-added |
|---|---|---|---|
| **Justin Crawford** | **$1** | $10.06 | **+$9** |
| Matt McLain | $1 | $7.38 | +$6.4 |
| Carter Jensen | $1 | $6.98 | +$6.0 |
| Ezequiel Tovar | $1 | $5.35 | +$4.4 |
| Alec Bohm | $2 | $5.90 | +$3.9 |
| Jakob Marsee | $8 | $9.16 | +$1.2 |

Whether a re-added player resumes his old contract or becomes a $10/$20 free
agent depends on a league rule this model does not encode — worth checking,
because at $1 with two years of control Crawford would rank inside the
league's top 40 keeper assets, and at $20 as a post-break FA pickup he would
not be worth holding.

**Best win-now adds** (rest-of-2026 roto points): Edwin Díaz (2.87, 6 saves),
Dustin May (2.64), Pete Fairbanks (2.34, 7 saves), Esteury Ruiz (2.13, 12 SB).
Three of the top four are relievers with saves — consistent with §1.


---

## 21. External validation against CBS's own roto rank

Josh supplied CBS's 2026 roto rank for 94 hitters — an independent valuation
computed by the platform, from the same categories, with no knowledge of this
model.

**Spearman(CBS rank, my roto points) = 0.893** across 93 matched hitters.

That is the strongest external check available: two systems built from
different starting points agreeing at 0.89 on the ordering of the league's
hitters. Together with the standings reproduction (0.842) and the z-score
cross-check (0.855), the engine now has three independent corroborations.

**A bug in the comparison, not the model.** The first pass showed Luis García
as a massive disagreement — CBS 41st, me 96th. The cause was a name collision
between Luis García Jr. (the Nationals infielder, 29 HR) and Luis García (the
reliever). The board itself is correct; my ad-hoc merge grabbed the wrong one.
Deduplicating raised the correlation from 0.863 to 0.893. **Every name-based
join outside `io.NameResolver` is a latent version of this bug.**

### The systematic disagreement is interpretable

| | mean AVG | mean HR | mean SB |
|---|---|---|---|
| 20 players CBS rates highest relative to me | **.280** | **12.7** | 11.8 |
| 20 players I rate highest relative to CBS | **.250** | **19.0** | 11.5 |

Stolen bases are identical; the split is entirely average against power. CBS
likes Luis Arraez (.313, 5 HR), Nick Gonzales (.307, 6 HR) and Freddie Freeman
(.306) far more than I do; I like Nick Kurtz (21 HR, .256) and Shea Langeliers
(23 HR, .263) far more.

**Two explanations, and they have different consequences:**

1. **My AVG denominator is too large**, so batting average is underweighted.
   The denominator is .0023 from pooled 2024–25 dispersion — and 2025 was an
   anomalously tight season for team batting average, which would push the
   pooled figure the wrong way.
2. **CBS's "Rank" is not this league's 5×5.** The export carries OBP and SLG
   columns, so the rank may come from a generic scoring system that rewards
   on-base skill — in which case the tilt is expected and means nothing.

**This is worth resolving and is the highest-value open check.** If CBS's rank
is the league's own 5×5, the AVG denominator needs re-examining, and it would
shift every high-average hitter in the league. Confirming which scoring system
that column reflects takes one look at the CBS page.


---

## 22. Experiments: real error bars on the headline numbers

`scripts/experiments.py`. Four tests aimed at the places the model has been
answering with point estimates.

### 22.1 The denominators are far less certain than advertised

Bootstrapping the estimator itself (2,000 resamples of the pooled
team-seasons) rather than quoting an analytic standard error:

| category | denominator | 95% interval |
|---|---|---|
| R | 39.4 | 14.0 – 59.6 |
| HR | 15.4 | 7.8 – 20.3 |
| RBI | 38.7 | 17.6 – 55.7 |
| SB | 20.4 | 14.4 – 24.3 |
| AVG | .0023 | .0013 – .0031 |
| W | 3.79 | 2.23 – 4.88 |
| SV | 6.57 | 3.88 – 8.68 |
| K | 59.1 | 33.5 – 79.5 |
| ERA | .0431 | .0282 – .0540 |
| WHIP | .0108 | .0074 – .0135 |

**The mean 95% interval is ±38% of the point estimate, not the ±16% quoted
elsewhere.** The analytic figure is the standard error of a standard
deviation on an idealised sample; the bootstrap accounts for the actual
n=20 and the punter filter. **±38% is the number that belongs next to a
dollar figure.**

Runs (±58%) and RBI (±49%) are the least certain; stolen bases (±24%) and
WHIP (±28%) the most. That ordering is itself useful: SB-heavy and
ratio-heavy players are priced more reliably than counting-stat compilers.

### 22.2 Pooling gets the ranking right and the price level wrong

Leave-one-season-out: fit the exchange rate on four auctions, predict the fifth.

| held out | pooled $/pt | that season's own $/pt | mean residual | RMSE |
|---|---|---|---|---|
| 2022 | 6.53 | 4.16 | −0.43 | 3.56 |
| 2023 | 6.19 | 4.78 | −0.04 | 3.25 |
| 2024 | 5.66 | 6.36 | +0.46 | 2.98 |
| 2025 | 5.53 | 8.09 | +0.18 | 3.25 |
| 2026 | 5.42 | 9.98 | −0.23 | 3.08 |

Residuals are small and **not** monotone in season (r = +0.29), so the pooled
fit is not biased in the residual. What it misses is the **level**: pooled
$/pt sits in a 5.4–6.5 band while the held-out season's own rate ranges
4.2–10.0. That is precisely the case for `EXCHANGE_BASIS` — pooling ranks
players correctly and prices them on the wrong scale.

### 22.3 The saves finding survives a properly constructed null

Permutation test, 5,000 draws, shuffling the closer label **within season and
price band** — so the null preserves both the time trend and the fact that
closers are cheap, which are the two obvious confounds.

- observed closer excess: **+2.23 roto points**
- null: mean +0.22, sd 0.50, 95% range [−0.76, +1.20]
- **two-sided p < 0.0001**

The observed effect is four standard deviations outside a null that already
concedes both alternative explanations. This is now the best-supported
finding in the project — stronger than the t-test, because the permutation
makes no distributional assumption and controls the confounds by design.

It remains conditional on the punter exclusion (§1).

### 22.4 The AVG denominator is not the source of the CBS disagreement

Rescaling the AVG denominator and re-checking agreement with CBS's independent
rank:

| multiplier | AVG denominator | Spearman vs CBS |
|---|---|---|
| 0.50 | .0011 | 0.755 |
| 0.75 | .0017 | 0.845 |
| **1.00 (current)** | **.0023** | **0.893** |
| 1.25 | .0029 | 0.911 |
| 1.50 | .0034 | **0.912** |
| 2.00 | .0046 | 0.901 |

The curve is flat between 1.0 and 2.0 and the best available gain is +0.019 —
noise at n=93. **There is no material evidence the AVG denominator is
mis-set**, and notably the direction that helps slightly is *less* weight on
average, the opposite of what the earlier average-versus-power split implied.

That leaves explanation (2) from §21 as the live one: **CBS's published rank
is probably not this league's 5×5.** Its export carries OBP and SLG columns,
and a rank built on those would favour exactly the high-on-base, low-power
hitters the comparison flagged, without any denominator being wrong. The
open question is answered as far as this data can answer it — the remaining
step is confirming what scoring system that column reflects.

### What changed as a result

`README.md` and `HANDOFF.md` now quote **±38%**, not ±16%. Nothing else moved:
the saves finding strengthened, the exchange-rate design was vindicated, and
the AVG question resolved in favour of leaving the model alone.


---

## 23. The constitution, finally read — three rule corrections

The league constitution sat in the project folder from the first message and
I worked from a second-hand summary instead. That was the wrong call: reading
it took two minutes and produced three corrections.

### 23.1 Extensions are +$5 PER YEAR, for one OR two years

> "owners must extend the player's contract by adding $5 for each additional
> year... If a player is entering the final year of his contract at $10, the
> owner can extend the player for one more season at $15 or two more seasons
> at $20."

The model priced extensions as always +1 year at +$5. The owner actually
chooses one or two years at +$5 each, so a genuinely good player can be locked
for **two** years at +$10 — an option the old code could not express. The
extension term now values both lengths and takes the better.

### 23.2 One extension per contract, ever

> "Players can only be extended once per contract (e.g. if Hank Aaron's
> original contract price was $30 and he is extended for an extra season at
> $35, owner X cannot further extend Aaron the following season)."

The model gave every `F` player an extension option. Players who have already
used theirs cannot extend, which for an `F` player means **he cannot be kept
at all**.

Detection: current salary above the last auction price, *by exactly $5 or
$10*, and not sitting on a free-agent price. That last filter matters — a
first pass flagged 13 players, but seven were $10 salaries, which is the
pre-All-Star free-agent price, i.e. dropped-and-reclaimed rather than
extended. The refined test finds **three**:

| player | contract | salary | draft price | status |
|---|---|---|---|---|
| Yoshinobu Yamamoto | 1 | $32 | $27 | extended, still has a year at salary |
| Andrés Muñoz | 2 | $13 | $8 | extended, two years at salary |
| **Bryce Harper** | **F** | **$16** | **$11** | **cannot be kept — free agent for 2027** |

Josh flagged Harper as a free agent two sessions ago and the model was still
offering him at $21. It now reports him unkeepable.

### 23.3 Everything else in the constitution checks out

23 active + reserve ✓ · $260 ✓ · 6–13 keepers ✓ · three-year contracts ✓ ·
$10 pre-break / $20 post-break free agents ✓ · waiver order by reverse
standings ✓ (not modelled, not needed).

One rule not modelled: **"Each team may purchase, at most, one minor league
player during the draft"**, counting as a reserve player. Irrelevant to
valuation, relevant if the tool ever advises on draft construction.

### 23.4 Unresolved: Skubal's salary

Skubal is code `3` at $38, last bought at auction in 2024 for $23. That is
**+$15**, which is not a legal extension (+$5 or +$10). Either the auction
match is wrong, or something happened to his contract the data does not
record. He is treated conservatively — no further extension option — which
costs him $3 of surplus and leaves him a clear keep at +$26.3.

### 23.5 CBS rank: confirmed not this league's scoring

Josh confirms the CBS rank includes OBP. That settles §21 and §22.4: the
average-versus-power disagreement was CBS measuring a different game, not a
mis-set AVG denominator. **No model change required** — and experiment 22.4
had already reached that conclusion from the data alone, which is a small
piece of evidence that the calibration test works.

### 23.6 Re-add rule confirmed

A dropped player keeps his draft-year contract on re-acquisition, so **Justin
Crawford at $1 with two years of control is genuinely available** — a +$30
asset for a waiver claim.

**Lesson for the notebook:** the primary source was in the folder the whole
time. Second-hand summaries of rules are exactly the class of assumption the
audit script cannot catch, because nothing about them is arithmetically
inconsistent — they are just wrong.

---

## 24. The final-year extension was priced at one year when the rule allows two

Found while building the app, which is the point of building an interface: the
player card printed *"extension option: $0.00"* for Shohei Ohtani, a $16
final-year player worth $72. That is not a number a $16 contract on a $72
player should produce.

**The rule.** §23.1 established that the constitution grants +$5 **per year**,
for one **or** two years, chosen once. `multiyear_surplus` implemented that
correctly for live contracts (codes 1–3), where the extension is a call option
on seasons after the deal expires. For final-year (`F`) players it did the
opposite of correct: it zeroed the option entirely, on the reasoning that

> An `F` player's extension is already inside `keeper_cost`.

which is true of the *one-year* extension and false of the two-year one. Every
final-year player in the league was forced into a one-year deal.

**The fix.** For an `F` player, price both branches and take the better:

```
1 year :  v2027 − (salary + 5)
2 years:  v2027 − (salary + 10)  +  0.85 × max(0, v2028 − (salary + 10))
```

The second year is worth buying iff `0.85 × (v2028 − salary − 10) > 5`. That
is the whole decision, and it is worth writing down because it is *not* "always
extend for the max" — the extra year costs $5 in 2027 money whether or not you
use it.

**What moved.** Three of the 35 final-year players clear the bar:

| player | salary | value 2027 | value 2028 | 1 yr | 2 yr | Δ |
|---|---|---|---|---|---|---|
| Shohei Ohtani | $16 | $71.9 | $61.5 | $50.9 | **$76.1** | **+$25.2** |
| Riley Greene | $3 | $19.8 | $20.5 | $11.8 | **$13.2** | +$1.4 |
| Elly De La Cruz | $15 | $30.9 | $31.9 | $10.9 | **$11.8** | +$0.9 |

$27.4 of surplus league-wide, 92% of it on one player. No keep/cut decision
flips — all three were comfortable keeps either way — so the board's *advice*
is unchanged. What changes is the **trade price of a final-year star**: Ohtani
is a $76 asset, not a $51 one, a 49% under-valuation in any deal involving him.

The board now also reports `extension_years` ∈ {0, 1, 2}: how many years to
actually buy. 52 players should buy one, 9 should buy two, 214 should not
extend at all.

**Lesson.** This is the same failure mode as §23 and it is worth naming: the
code implemented the *general* rule correctly and then special-cased the one
branch where the rule was hardest to see, with a comment that sounded right.
Nothing was arithmetically inconsistent, so neither the audit script nor the
32 invariants caught it. What caught it was rendering one player's numbers
side by side and asking whether they looked like a real contract.

**Superseded 2026-08-13, in two different ways (§39).** Ohtani's own $76.1
figure was already independently zeroed out before this session, by the
`NON_EXTENDABLE_NAMES` league-ruling override — unrelated timing to §39's
fix, already correct going into it. Riley Greene and Elly De La Cruz's
$13.2/$11.8 figures were not protected by any override and were both live,
real numbers on the board until §39 — both are among the ten players whose
`keep_2027` flag flips there. This section's closing claim, "no keep/cut
decision flips," no longer holds; it was true under the model as it stood
that day, not today.

### 24.1 A column collision the same build surfaced

`ros_lines()` returns a `PA` column; so does the projection. Merging them
without prefixing produced `PA_x`/`PA_y`, and the player card silently printed
a dash where playing time should be. Nothing raised. The export now prefixes
every rest-of-season column and asserts the two schemas are disjoint, and a
test checks that no exported row has a null in a field the interface reads.

Both bugs are the same species: **a wrong value that is not an invalid value**.
The defence is not more assertions on totals, it is looking at one row in full.

## 25. Two final-year contracts don't reconcile against the draft record — unresolved

Two players carry contract code `F` (2026 was the final year) whose draft
history says their standard 3-year clock should have expired earlier:

| player | drafted | draft price | current team | current salary | code | expected final year (3-yr std) | actual |
|---|---|---|---|---|---|---|---|
| Jacob deGrom | 2022, Milwaukee Beers | $21 | Pookie 2.0 | $21 | `F` | 2024 | 2026 |
| Brice Turang | 2023, New York Polar Bears | $9 | McBlocks | $9 | `F` | 2025 | 2026 |

The 3-year count follows the convention already established elsewhere in this
project (`klab/config.py`'s contract-code comment, verified against Judge/Witt/
Tucker: a 2024 draft reaches `F` in 2026, i.e. the draft year counts as year
one of three). By that same count deGrom is two years past expiry and Turang
one year past.

Two years remaining doesn't come from a hidden model: `already_extended()`
(`klab/keeper.py:150-175`) only recognizes an extension when the current
salary exceeds the last auction price by exactly the constitutional +$5/+$10
step. Both salaries are **unchanged** from the original draft price, so no
extension was paid, and the code applies no other rule that would grant extra
years.

**Hypothesis tested and rejected: a re-drafted player gets a fresh 3-year
clock.** If either player had been dropped and re-drafted later — say deGrom
in a 2024 supplemental draft — a fresh clock would explain an `F` in 2026.
Checked every `data/draft_2022.csv` through `draft_2026.csv` for both names:
**neither appears anywhere except their original draft row.** There is no
re-draft event in the record for either player. The hypothesis has nothing to
attach to, so it's rejected — see `out/LAB_NOTEBOOK.md` for the write-up.

That leaves the confirmed rule from §23.6 as the operative one — a re-added
player **keeps** his original draft-year contract, he doesn't get a fresh
one — which predicts the *opposite* of what's observed: both contracts should
already have expired, not still be running. Both players did leave their
drafting team and are absent from `keepers_2022.csv`–`keepers_2025.csv`, so a
drop-and-reacquisition happened at some point; but per §16/§19 those pre-2026
keeper files are already known to be incomplete (25-29 rows/season vs. a real
keeper set of 67-101), so their absence there is not evidence either way.

**What this is not:** an arithmetic inconsistency the audit script would
catch. `contracts_parsed.csv` provenance is already flagged elsewhere
(`out/METHODS.md:28-29`) as unverifiable — there is no `contracts_raw.txt` to
check it against. This is most likely either a data-entry artifact in that
file, or a commissioner ruling (trade dispute, injury settlement — the
constitution's §V gives commissioners discretion here) that predates this
project and was never written down anywhere the model can see.

**Practical stakes, current board:** per `out/sensitivity_keep_flags.csv`,
deGrom is a cut under all 8 sensitivity variants regardless (his 2027
projection is poor on its own merits), so the extra years don't change his
recommendation. Turang is a keep under all 8 variants **as `F`**; if his true
contract had actually expired after 2025, he'd need an extension payment
to be legally keepable at all in 2027, which would change his surplus by
exactly $5 (one extension year) — not large, but it's a live number, not a
hypothetical one.

**Recommendation:** this needs the primary source, not more code. Check the
CBS commissioner tools or email history for these two players' transaction
log. Until then, both are carried as-is (`F`, unchanged salary) because that
is what `contracts_parsed.csv` says, and the model has no basis to overrule
its own input.

## 26. Partial-2026 denominator exclusion: the rate-vs-counting split was a proxy for something else

`config.PARTIAL_SEASONS` treats 2026 as a 75%-complete season for the purpose
of pooling denominators, and `DENOM_EXCLUDE_PARTIAL_FOR_RATES` excluded 2026
for the three rate categories (AVG, ERA, WHIP) while including it raw for
every counting category. The comment justifying this checked five categories
against a "partial seasons are over-dispersed" mechanism and generalized to
"rate cats bad, counting cats fine." This was the judgment call the project
brief flagged as needing a proper test rather than an assumption.

**The test: measure single-season CV (std/mean across teams) for all ten
categories, 2024 and 2025 (full seasons) vs 2026 (partial), and see which
categories actually show partial-season inflation.**

| category | 2024 | 2025 | 2026 (f≈0.75) | inflated vs. both full seasons? |
|---|---|---|---|---|
| R | 0.142 | 0.063 | 0.054 | no |
| HR | 0.190 | 0.104 | 0.103 | no |
| RBI | 0.150 | 0.053 | 0.064 | no |
| SB | 0.341 | 0.301 | 0.127 | no (much lower, if anything) |
| AVG | 0.036 | 0.014 | 0.026 | **no** — between the two full seasons |
| W | 0.114 | 0.144 | 0.121 | no |
| SV | 0.254 | 0.177 | 0.328 | **yes** — higher than both |
| K | 0.090 | 0.164 | 0.085 | no |
| ERA | 0.037 | 0.035 | 0.073 | yes — ~2x |
| WHIP | 0.028 | 0.028 | 0.042 | yes — ~1.5x |

The rate-vs-counting split gets 8 of 10 categories right by accident and 2
wrong: **AVG isn't actually inflated**, and **SV is, despite being a counting
stat**. The mechanism isn't "rate stat" — it's whether the category's
denominator accumulates unevenly within a partial season. At-bats accumulate
at a stable, near-daily rate for every hitter, so AVG's volume is genuinely
~75% done and its dispersion behaves like a scaled-down full season. Saves
depend on a specific role (closer) that gets reassigned mid-season — a
partial season doesn't just have less save volume, it has *less-settled* save
volume, which is the same noise mechanism ERA and WHIP have from incomplete
innings.

Recomputed the pooled dispersion under three schemes — current (rate cats
excluded), include-2026-everywhere, and exclude-2026-everywhere — to size the
effect:

- **AVG**: including 2026 shifts the point estimate by only −2.0%, but tightens
  its standard error by ~21% (more team-seasons pooled for a stat that isn't
  contaminated). Clear win to include it.
- **SV**: excluding 2026 shifts the point estimate by −16.2% (0.250 → 0.209).
  That's about 1.2 standard errors under the current scheme — directionally
  consistent with the closer-role-churn mechanism and not something to ignore,
  but not overwhelming on its own either. Every other category was unaffected
  by the choice (counting cats other than SV are scale-invariant to a uniform
  2026 include/exclude, confirming the code's original cancellation argument;
  ERA/WHIP were already excluded either way in this comparison).

**Changed `config.py`**: replaced the `RATE_CATS`-keyed exclusion with an
explicit `PARTIAL_EXCLUDE_CATS = {"ERA", "WHIP", "SV"}`, decoupled from the
rate/counting classification. Reran the full pipeline:

| quantity | before | after | change |
|---|---|---|---|
| SV denominator | 7.16 | 6.00 | −16.2% (saves worth more) |
| AVG denominator | 0.002298 | 0.002252 | −2.0% |
| replacement level | 4.761 | 4.778 | +0.35% |
| $/roto pt (keeper) | $9.11 | $9.26 | +1.74% |
| $/roto pt (redraft) | $6.32 | $6.24 | −1.18% |
| every other denominator | — | — | unchanged |

**5 of 275 rostered players flip keep/cut**: Andrés Muñoz, Bryan Baker, Cam
Smith, and William Contreras flip to keep; Yoshinobu Yamamoto flips to cut
(the last one is the small ripple through the exchange rate, not a saves
effect directly). The saves-value shift itself is visible in every closer's
surplus — Cade Smith, Mason Miller, David Bednar, Jhoan Duran and similar all
gain roughly $5.50–$6.80 of keeper surplus. This is not a rounding-error
change; it is 5 real roster decisions and real money for every rostered
closer.

**What this doesn't resolve.** The SV shift is the weaker of the two changes
statistically (1.2 SE, not a clean multi-SE signal), so treat "SV joins the
excluded set" as the best current evidence rather than a closed question —
worth revisiting once 2026 is a complete season and there's a same-season
comparison point instead of an in-progress one.

## 27. Replacement level, revisited: the field-standard comparison, a new sanity check, and confirming the clean test is still genuinely blocked

`out/QA_ROUND.md` §A4 named a specific unrun test for replacement level
("take every player available on the wire on date X, measure realised
production forward, take the median — availability without survivorship")
and named its blocker: it needs transaction logs. First step here was
checking whether that's still true. It is — `data/` has no file with FA
transaction dates; `grep`ing for anything resembling one turns up nothing.
The blocker is confirmed, not assumed.

**The three existing routes, recomputed against the current pipeline**
(after §26's denominator fix, which moved every number slightly):

| route | value | what it is |
|---|---|---|
| auction regression intercept | 4.01 | extrapolation past the $1 floor — a lower bound |
| 230th-best projection (`WAIVER_VALUE="low"`) | 4.78 | one per active roster slot |
| median of players actually added via FA in 2026 | 5.04 | survivorship-biased upper bound |

All three moved by less than the §26 denominator change alone would predict,
confirming none of them silently drifted from anything but that change.

**Where the 230th-projection route sits relative to the field:** this is
functionally the "Last Player Picked" (LPP) methodology (Larry Schechter) —
replacement level defined as the value of the last player who'd actually be
rostered given the league's real roster construction, not an average or a
generic "freely available" fudge factor. LPP is treated as the more
defensible approach in the sabermetric literature specifically because it's
tied to actual roster math rather than an assumed talent cutoff. The model
already implements this; it just wasn't written down as a deliberate
methodological choice matching a named, respected approach.

**A test that doesn't need transaction logs and hadn't been run: is the
230th-projection number internally consistent with the free-agent pool it's
supposed to describe?** If replacement level is really "the value at which
supply of free agents roughly equals what's worth adding," then the pool of
currently unrostered players should have very few players priced above it,
and its best players should cluster right around that value. Checked against
`out/free_agent_board.csv` (1,714 unrostered projected players):

- Only **24 of 1,714** free agents (1.4%) project above the current
  replacement level of 4.78.
- The top of that pool decays smoothly — rank 10 at 5.09, rank 20 at 4.84,
  rank 30 at 4.55 — putting the estimate almost exactly at the elbow where
  the free-agent pool stops having plausible adds. There's no cliff or gap
  that would suggest the number is badly placed.

This passes. It's not proof the estimate is exactly right, but it rules out
"badly miscalibrated in either direction" — if replacement were meaningfully
too low, dozens of clearly-better free agents would be sitting unrostered; if
meaningfully too high, the model would be claiming almost nobody on waivers
is worth adding, which contradicts the fact that 118 players were actually
added via free agency in 2026 (`out/acquisition_channels_2026.csv`).

**One more thing worth recording:** recomputed the 5.04 actual-FA-median
figure directly from `acquisition_channels_2026.csv`'s free-agent-channel
rows (118 players) using the current, post-§26 denominators — got **5.037**,
matching the hardcoded `config.WAIVER_HIGH_RP` to three decimals. The
constant looked stale (no script derives it; it's just typed into `config.py`
with a comment) but turned out not to be — worth knowing it's still accurate
rather than assuming it drifted.

**Recommendation: keep `WAIVER_VALUE = "low"` (4.78) as the default.** It's
the field-standard method, it passes a new internal-consistency check the
project hadn't run, and the clean transaction-log-based test that could
displace it remains genuinely infeasible with the data on hand — not for
lack of trying, but because the data doesn't exist yet. Revisit if/when
transaction logs become available.

## 28. Reliability refit found a real bug: BB and H were both silently set to WHIP's number

`out/QA_ROUND.md` §A2 flagged `klab/project.py`'s `RELIABILITY` dict as a
one-time fit that "should be refit when 2026 closes. Not urgent." Refit it
directly: same method as the original (year-over-year Pearson r of each
per-PA or per-IP rate, hitters with 250+ PA in both years of a pair,
pitchers with 40+ IP, pooled across the (2022,2023)/(2023,2024)/(2024,2025)
season pairs — identical to `fit_save_model`'s own season pairs, for
consistency).

**Eight of ten values reproduced exactly**: HR 0.607, R 0.425, RBI 0.380,
SB 0.739, AVG 0.436, K 0.701, W 0.151, ER 0.174 (documented as 0.176, a
rounding difference, not a discrepancy). **Two did not**: `BB` and `H` are
both hard-coded to **0.237**, and refitting gets **BB = 0.463, H = 0.359** —
different from each other and from 0.237. Checked where 0.237 actually came
from: it's `WHIP`'s own year-over-year reliability
(`(BB+H)/IP` correlated year over year: r = 0.237 exactly, n=785). `WHIP` is
also a key in `RELIABILITY`, and `grep` confirms it is never read through
`rel_weight()` anywhere in `klab/` — WHIP is blended through its two
components (BB, H) the same way AVG is blended through H/AB, so the `WHIP`
entry is inert documentation. **BB and H were overwritten with WHIP's value
by what looks like a copy-paste across three related keys, and unlike WHIP,
BB and H are both live** — every 2027 projection has been discounting last
year's observed walk and hit rates as if they were as unreliable as WHIP
itself (0.237/0.739 relative weight) when they're actually meaningfully more
repeatable (0.463 and 0.359).

**Fixed in `klab/project.py`.** Reran the full pipeline:

| quantity | before | after |
|---|---|---|
| replacement level | 4.778 | 4.778 (unchanged) |
| $/roto pt (keeper) | $9.264 | $9.264 (unchanged) |
| $/roto pt (redraft) | $6.242 | $6.214 (−0.45%) |
| keep/cut flips | — | 1 (Yoshinobu Yamamoto) |
| mean \|Δ surplus\| across 275 rostered players | — | $0.16 |

The headline scalars barely move — this bug lived entirely inside
pitcher-level WHIP projections, not the league-wide denominators or
exchange rate. But individual pitchers move real money: Jacob Misiorowski
+$3.51, Cam Schlittler +$2.57, Drew Rasmussen +$1.98, Freddy Peralta −$1.92,
Garrett Crochet −$1.55 — all in the direction you'd expect once last year's
actual walk/hit rate is trusted more and ZiPS's regression-to-the-mean is
trusted correspondingly less.

**Robustness check, not adopted:** also refit including a fourth pair,
(2025, 2026), using 2026's partial season as the "year 2" observation. Every
value moved by less than 0.02 in either direction (e.g. BB 0.463→0.476, H
0.359→0.347, W 0.151→0.130) — consistent with each other and with the
existing fit, no reason to switch. Kept the original three-pair fit so this
change is isolated to fixing the BB/H error, not bundled with a second,
smaller decision about whether to use partial 2026 data here too.

**On "not urgent":** it wasn't wrong that a full refit could wait, since 8 of
10 values hadn't moved. But "should be refit eventually" and "has a live bug
in it right now" are different findings, and only checking the dict at
refit-time (rather than, say, a test that recomputes and compares) means
this class of error sits invisible for as long as nobody happens to rerun
the fit.

## 29. Depth-vs-stars, redone with share of production: the hypothesized cleanup only half worked

§18 built the "depth beats stars" case on raw player counts per team at each
z-threshold. `out/QA_ROUND.md` §A6 named the concern directly: a count is
partly a measure of *roster churn* (how many different players cycled
through a slot), not team quality, and proposed **share of team roto
production** at each threshold as the cleaner version. That test had not
been run. Ran it.

First, a housekeeping note: §18's own numbers have moved because of #26 and
#28 in this document (the SV denominator fix and the BB/H reliability fix)
— both change individual players' `roto_points`, which shifts every z-score
downstream. Refreshed baseline, same method as §18, same 274 rostered
players:

| predictor | §18 (documented) | refreshed (this session) |
|---|---|---|
| count at z ≥ 1 | +0.840 | +0.906 |
| count at z ≥ 2 | +0.141 | +0.141 |
| count below average | −0.755 | −0.772 |

Small moves, same story — good, since neither #26 nor #28 had anything to
do with z-scores specifically; this is just confirmation the pipeline is
internally consistent.

**Share of production, the actual new test:**

| predictor | count (raw) | share of production |
|---|---|---|
| ≥ z 1 | **+0.906** | +0.794 |
| ≥ z 2 | +0.141 | −0.019 |
| below average | −0.772 | **−0.879** |
| *(context)* total team roto points | — | **+0.939** |

The hypothesis was that share-of-production would be uniformly cleaner than
raw counts. It's not uniform: **share is a weaker predictor for both
above-average thresholds** (+0.794 and −0.019 vs. +0.906 and +0.141) but **a
stronger one for below-average** (−0.879 vs. −0.772). The likely mechanism:
a team that is deep-but-not-starry — lots of solidly-above-average
players, no z≥1 studs specifically — has genuinely good *share*-adjacent
quality, but "share above z≥1" as a ratio penalizes them for not having the
specific players that clear the threshold, same failure mode as the count
version, just expressed differently. The "how many did you avoid" side of
the question doesn't have that ambiguity — bad players hurt whether measured
by count or by the production they cost you — which is exactly why the share
version sharpens *that* side of the story.

**The finding that actually reframes the section**: total team roto
production, with no z-threshold at all, predicts standings (+0.939) better
than any single threshold metric tested, raw or share. That's worth sitting
with. Splitting a team's roster into "stars" and "depth" bins and asking
which bin predicts winning is answering a real question, but it's a noisier
version of "does this team have more production," which was available the
whole time without picking a threshold. None of this overturns §18's
headline claim — z≥1 count/share both beat z≥2 count/share by a wide margin
in every version tested, so "depth over stars" survives — but it should be
read as "depth over stars, and both are secondary to just having more total
production," not as a clean two-factor story.

**Caveat that applies to every number in this section, restated because it's
easy to lose sight of:** n = 10 teams. Every Spearman correlation here has a
wide standard error and none of them should be treated as more than
suggestive on their own.

## 30. The headline ±38% uncertainty band was computed around the wrong point estimates

Caught while reconciling every doc's numbers against the live pipeline after
#26 and #28. `scripts/experiments.py::exp1_bootstrap_denominators` — the
source of the "±38% per category" figure quoted in README.md, `out/HANDOFF.md`
and `out/ARCHITECTURE.md` as the honest uncertainty band on every dollar
figure — pools team-seasons with its own loop over `C.DENOM_SEASONS`,
written independently of `klab.denoms.pooled_relative_dispersion`. It never
had the partial-2026 exclusion logic at all: it included 2026 raw for every
category, always, including ERA/WHIP/SV. That means the bootstrap interval
was centered on a different set of point estimates than the ones the model
actually ships (confirmed directly: ERA came out to 0.0614 from this
script, against 0.0431 in `out/model_params.json`) — an uncertainty band
answering "how uncertain is a denominator computed a different way,"
not "how uncertain is the number in the app."

Fixed by applying the same `PARTIAL_EXCLUDE_CATS` / `PARTIAL_SEASONS` check
`klab/denoms.py` uses. Rerun: every denominator now matches
`model_params.json` exactly, and the mean interval width moves from ±38%
(the stale, pre-session number) to **±34%**. Smaller, not larger — SV's
narrower post-#26 team-season pool (n=17, not 26) turned out to matter less
for the *average* width than ERA and WHIP's estimates tightening slightly
now that their point estimates are computed the same way twice instead of
two different ways.

**Same species of bug as #10 and #12: a script that duplicates logic instead
of importing it, and drifts the moment the imported version changes.**
Checked every other script in `scripts/` for the same pattern
(`grep` for `DENOM_SEASONS`/`RATE_CATS`/`RELIABILITY`/`PARTIAL_SEASONS`):
`run_all.py` and `eval_trade.py` both call `pooled_relative_dispersion`
directly rather than reimplementing it, and `sensitivity.py` references
`klab.project.RELIABILITY` and `C.DENOM_SEASONS` live (it swaps them out
deliberately, as sensitivity variants — that's the point of the script).
`experiments.py` was the only one carrying an inline copy, and it's fixed
now.

## 31. A second, live copy of the same season-set bug: `teams_per_category`

Found while updating `out/HANDOFF.md`'s denominator table by hand and
double-checking each number against a fresh run rather than trusting the
arithmetic. `klab.denoms.teams_per_category()` — which feeds
`denominators_for_level`'s `c_n` range-constant lookup in **both**
`klab/board.py` and `klab/auction.py`, i.e. every dollar figure the model
ships, not a diagnostic script — averages the per-season punter-filtered SV
field size over every season in `C.DENOM_SEASONS` unconditionally. It never
had the `PARTIAL_EXCLUDE_CATS` check #26 added to
`pooled_relative_dispersion`. So the field-size constant (`n`, which decides
whether the model uses the 8-team or 9-team range constant) was computed
over a different set of seasons than the dispersion estimate (`sigma_rel`)
it's supposed to be scaling.

Only SV is affected — ERA and WHIP always compare all 10 teams (nobody
"punts" ERA), so their `n` is 10 regardless of which seasons are averaged.
For SV, including 2026 put the raw average at 8.667 team (rounds to 9,
`config.C_N[9]`); excluding it, matching #26, gives 8.5 (rounds to 8 under
Python's round-half-to-even, `config.C_N[8]`) — a different range constant
(2.970 vs 2.847) and thus a materially different SV denominator: **6.00 →
6.57**, a further 9.6% swing on top of #26's original 16.2% correction (net
effect of both fixes together vs. the pre-session baseline: SV denominator
7.16 → 6.57, about −8.2%, still a real loosening of the saves denominator,
just smaller than #26 looked like in isolation before this was caught).
`usd_per_rp_keep` moves from $9.26 to $9.17, `usd_per_rp_redraft` from
$6.21 to $6.29. One more keep/cut flip: Bryan Baker (Orange and Black
Attack), surplus $13.37 → $9.74, still comfortably positive but below his
team's 13th-keeper cutoff.

Fixed by giving `teams_per_category` the identical exclusion check
`pooled_relative_dispersion` uses (same code, not a shared helper — small
enough that a shared helper would be more indirection than the duplication
it prevents, but worth reconsidering if a third such check ever gets added).
Same lesson as #30, immediately: **fixing one occurrence of a duplicated
check does not fix the other occurrences**, and the honest response to
finding one instance of this bug shape is to grep for the exact same
unprotected constant everywhere, not to assume the fix generalized. Every
number in `out/HANDOFF.md`'s denominator table and every headline $/point
figure in this document reflects the numbers *after* this fix, not #26's
intermediate ones.

## 32. General review of the modules the earlier fixes didn't touch

Sent a fresh review pass at `klab/keeper.py`, `klab/trade.py`,
`klab/freeagents.py`, and `klab/io.py` — the four core modules #26/#28/#30/#31
never touched — specifically for the same bug shape found elsewhere this
session (a hardcoded or duplicated value silently out of sync with the live
model). Two real, verified findings; one confirmed-real logical gap left
undecided on purpose.

**32.1 Every trade evaluation ever run used a stale hardcoded $/point,
never the live one.** `klab/trade.py::evaluate_trade`'s `usd_per_point`
parameter defaults to `None`, which falls back to a hardcoded `7.6`
(`klab/trade.py:125`) — and neither real caller passed anything else:
`scripts/eval_trade.py:64` and `scripts/build_app.py:175` (the source of
`out/app_reference.json`, the ground truth `app/verify.mjs` diffs the
browser against) both called `evaluate_trade()` with the parameter left at
its default. The comment right above the fallback says "priced at what a
roto point costs at auction" — the live figure for that is $9.17
(`exch["usd_per_point"]`, currently in scope at both call sites and simply
never passed through). Every trade verdict's win-now component has been
computed against a number that was already stale (the pre-session live
value was $7.56) even before this session's #26/#31 fixes moved it further
to $9.17.

Fixed both call sites to pass the live value. Measured impact on the
reference trade in `_reference()`: verdict scores move about $0.5–1 per
side for this particular trade; the correction scales with
`contention_weight × Δstandings_points`, so a trade with a bigger win-now
swing moves more.

**Same bug also existed independently in the app's JavaScript.** `app/template.html`'s
trade tab re-implements this same formula in JS (necessarily — it recomputes
trade verdicts client-side for interactivity) and was *not* stale — it read
`D.constants.usd_per_roto_point_redraft` live — but on the **wrong basis**:
redraft scale ($6.29), not the auction scale ($9.17) the Python comment
documents as intended. So Python and JS have been computing two different
numbers for the same quantity, on two different, independently-arrived-at
bases, this whole time. Fixed the JS to use `usd_per_roto_point_auction`,
matching Python's documented intent. **Verified 2026-08-13 with `app/verify.mjs`**
after installing Node — `PASS  JS matches pandas on all 25 quantities`,
`PASS  no console errors across six tabs, drawer, filters, re-sort`. This had
shipped without Node available in the working environment, which is exactly
the situation the parity script exists to guard against — a JS/Python
mismatch that looks fine until someone actually runs the check.

**32.2 Free agents with no draft history understated their own contract
length.** `klab/freeagents.py`: a free agent with no live draft-year record
gets priced at the post-All-Star-break acquisition price
(`C.FA_SALARY_POST_ASB`, i.e. "acquired now, in 2026") but the code
defaulted his `contract` field to `"1"` rather than `"2"` — one year short
of what a 2026 acquisition should carry under `DRAFT_YEAR_TO_CODE[2026] =
"2"`, the same mapping used two lines above for players who *do* have a
2026 draft record. Fixed to `fillna(DRAFT_YEAR_TO_CODE[2026])`. **Zero
dollar impact on the current board** — checked all 1,630 affected players;
every one has `surplus_multiyear` clustered near the −$20 floor regardless
of contract length, so nothing currently displayed changes. Worth having
fixed anyway: the `contract`/`years_controlled` columns on the free-agent
board are user-facing, and a genuinely attractive future waiver pickup
would have shown one year short of real control.

**32.3 A real ambiguity in `already_extended()`, left undecided rather than
guessed at.** `klab/keeper.py:166`'s free-agent-price guard treats any
salary exactly equal to `$10` or `$20` as "this must be a re-add, not an
extension," which is how it tells a re-acquired-at-FA-price player apart
from a genuine extension. But those two things are **not always
distinguishable from salary alone**: a `$5` draft price plus a legal `+$5`
one-year extension also lands on exactly `$10`; a `$15` draft price plus
`+$5` lands on `$20`; a `$10` draft price plus a `+$10` two-year extension
also lands on `$20`. In each of those cases the current logic would
wrongly classify a real extension as a re-add, understating that player's
extension-used status. **Checked every current player against this exact
condition — nobody on the current board hits it**, so this is a dormant
edge case, not a live error. Not fixed, because there's no way to fix it
correctly with the data available: distinguishing "re-added at FA price"
from "extended to a salary that happens to equal the FA price" requires a
transaction date, which is the same missing-transaction-log blocker as §27
and §11 of `out/LAB_NOTEBOOK.md`. Documented here so it's a known,
findable gap rather than a silent one if it ever does trigger.

## 33. Extension eligibility was applied to codes "2" and "3", not just "1"

Josh flagged this directly: asked me to confirm the extension-option code
against his own description of the rule, which turned out not to match
what was implemented. The constitution is explicit and singular on this —
there is exactly one extension clause: *"Players **about to enter the final
year** of their contract eligibility can be retained for additional
seasons."* That phrase means one thing: a player with exactly one year of
guaranteed control left (contract code `"1"`). A player with two or three
years left (`"2"`, `"3"`) is not about to enter his final year — he has one
or two full seasons of guaranteed control before that question is even
live.

`klab/keeper.py::multiyear_surplus`'s `live` branch (the extension-pricing
path for non-`F` contracts) didn't check this. It applied the same
extension-option computation to every non-`F` contract uniformly — codes
`"1"`, `"2"`, and `"3"` all got priced as if the owner could extend them
right now. Confirmed on the current board: **9 players with 2-3 years of
already-guaranteed control were carrying a phantom extension option**,
$25.60 combined — Spencer Torkelson ($1 salary) +$7.20, Konnor Griffin
($20) +$5.43, Hunter Greene +$3.96, Chandler Simpson +$3.77, Bryan Woo
+$2.29, Sal Stewart +$1.66, Tarik Skubal +$0.94, Jac Caglianone +$0.04,
A.J. Ewing +$0.32.

**The math itself was correct where it applied** — for a genuine code-`"1"`
player, extending 1 year does give 2 total years of control (the 1 already
owed plus 1 extension year) and extending 2 years gives 3 total, exactly as
described in the constitution's worked example and confirmed line-by-line
against the discount exponents used (`years.clip(lower=0) + k`, which
correctly picks up right where the already-owed year's discount left off).
The bug was purely eligibility: `is_final` correctly distinguished `F` from
everything else, but "everything else" needed a second split — `years == 1`
eligible, `years ∈ {2, 3}` not — and didn't have one.

**Fixed**: `ext`/`ext_yrs` are now built starting from an all-zero baseline,
with `F` rows filled from the `final` candidates and only `years == 1` rows
filled from the `live` candidates. Reran the full pipeline: exactly the
same 9 players change, `extension_option` goes to exactly `0.0` for all of
them, **zero keep/cut flips** — every one of the 9 was already a clear keep
on the corrected number, this was overstated surplus on players who didn't
need it to justify keeping them, not a flip-changing error. Verified with
`node app/verify.mjs` (Node installed this session specifically to run
it): `PASS` on all 25 quantities, `PASS` on console errors across every tab.

## 34. A win-now metric that isn't a team-standings swap: ROS value over replacement

`evaluate_trade`'s `verdict_score` blends two things that shouldn't be
blended into one dollar figure: `d_surplus` (multi-year asset value, on the
league-average redraft scale — appropriate, since a keeper's future value
isn't tied to any specific team's current standing) and the 2026 win-now
term, which converts a team-specific standings-point delta into dollars
using one league-wide average $/point. That conversion has no sense of
*where* a team sits in a category — a marginal point is not worth the same
to a team about to pass a rival in SB as to one already locked into last
place there. Flagged directly by Josh; this is the same category-balance
blind spot `out/RESEARCH.md` §6.2 already names as shared across every
published system, applied here specifically to trade win-now pricing.

Josh asked for something more specific and more useful as a first step:
a **player-intrinsic** number — how much better is this player than a
replacement player, over exactly the playing time he individually has left
this season — separate from any specific team's standings context, and
dynamic per player rather than one global "season is X% over" constant.

**Built `klab.trade.ros_value_over_replacement()`.** Mechanically:

- Uses the *same* full-season denominators and team baseline as the 2027
  keeper board (`build_2027_scorer`) — these are stable "units per standings
  point" conversion factors, already validated, and don't need re-deriving
  for a partial season. (The old ad hoc version in `scripts/eval_trade.py`,
  now removed, built a *separate* set of denominators keyed to the 2026
  season's current level — an unnecessary complication that also happened
  to produce different numbers than the standard board for reasons that
  were never isolated. Not calling that a confirmed bug; it's gone now, in
  favor of reusing the already-validated calculation rather than
  maintaining two.)
- **What does need to scale down**: the marginal-team dilution baseline
  behind AVG/ERA/WHIP (`base_AB`, `base_H`, etc.). Diluting a six-week rest-
  of-season sample against a *full season's* team volume would shrink a
  rate stat's marginal impact by roughly 4x too much — the same shape of
  error considered (and ruled out, on inspection, for a different function)
  earlier this session. Each player's `remaining_frac` — his own ROS PA or
  IP as a fraction of the standard keeper-floor full season (600 PA / 150
  IP) — scales the team baseline down proportionally, so the "1 player
  diluting a 13/14-man team" ratio stays consistent regardless of how much
  season is actually left.
- The replacement comparator is `replacement_rp` (4.78, the board's own
  standard) prorated by that same `remaining_frac` — "what would a
  replacement player be worth over the same amount of time."

**Applied to both trades under review:**

| player | ROS frac of season left | ROS value over replacement |
|---|---|---|
| Cristopher Sánchez | 0.34 | +1.92 |
| Elly De La Cruz | 0.30 | +1.59 |
| Ketel Marte | 0.28 | +0.78 |
| Jesús Luzardo | 0.32 | +0.36 |
| Brandon Lowe | 0.25 | +0.26 |
| Kazuma Okamoto | 0.26 | +0.12 |
| Tarik Skubal | 0.31 | +4.99 |
| Freddie Freeman | 0.29 | +1.70 |
| Jordan Walker | 0.29 | +0.60 |
| Christian Scott | 0.23 | **−2.23** |

Trade 1: Spehr's Army nets **+3.55** ROS roto points over replacement
(receiving 4.29, sending 0.74); All-Stars nets **−3.55**. Trade 2: Spehr's
Army nets **+8.32** (receiving 6.69, sending −1.63, since Scott actively
grades below replacement); NPB No Stars nets **−8.32**. Both point the same
direction as the multi-year dollar surplus already reported for each trade
— this isn't a case where the two lenses disagree — but they're now two
separately legible numbers instead of one blended one, per the ask.

**What this doesn't do yet**: it's still not the team-specific marginal
value Josh originally asked about (a point's worth depending on where a
*specific* team sits in a *specific* category race). That's a bigger
build — a real per-category, per-team marginal value curve, not a
prorated replacement comparison — and is a roadmap item, not something
built this session. `ros_value_over_replacement` is the honest, smaller
piece: a fair player-vs-player comparison for "how good is this rest of
this year," decoupled from any specific trade partner's standings context.

## 35. A comp-based next-auction price estimator — a deliberately separate tool

Built at Josh's explicit request, and explicitly **not** integrated with or
allowed to change anything else: `klab/auction_estimator.py`,
`scripts/estimate_auction_price.py`, `tests/test_auction_estimator.py`.
Nothing in `board.py`, `auction.py`, or `keeper.py` was touched, and
`redraft_value` means exactly what it meant before this section.

**The question it answers, which `redraft_value` deliberately doesn't**:
`redraft_value` is a regression-based *fair-value* estimate — what a player
with this production *should* cost, on average, given this league's own
auction history. It has no way to know that a name, a big recent year, or
this league's own specific taste moves real prices around that fair value.
This tool finds the 15 nearest historical comps (by role, position group,
and per-category production profile) from all 677 real purchases across
2022-2026, and asks: did players who looked like this typically sell for
more or less than a pure production regression predicted, *in the season
they were actually bought*? That premium, applied to the target's own
`redraft_value`, is the comp-adjusted estimate.

**Freddie Freeman, worked example** (`regression_fair_value` = $15.42):
comp-adjusted range **$14.15–$38.46**, median **$23.18**. The single most
informative comp is *Freeman himself, one year ago* — drafted at $28 in
2025 against a $8.55 production-only prediction, a +192% premium. Two more
comps (Guerrero Jr. +265%, Devers +211%) show the same pattern for
name-brand corner-infield bats. That's a real, specific signal this
league's market pays a track-record premium for players like him that the
pure regression has no way to see — exactly the gap this tool exists to
surface. Tarik Skubal's range came back very wide ($3.60–$79.20) for a
different, equally honest reason: checked the actual comps, and elite
starting-pitcher prices in this league's history genuinely span from $1
(injury-discounted) to $33 (name value) at similar production levels — the
width is real market variance, not a bad match (closest comps were
Wheeler/Musgrove/Verlander/Kershaw, all sensible).

**Known limitation, by design, not an oversight**: no age or debut-year
data exists anywhere in `data/` (checked directly), so this can't do
age-based comps at all — a real, standard input for this kind of estimate.
Position and realized production level are the only axes available.

**Two potential improvements to *existing, established* code, found while
building this and deliberately not applied, per instruction:**

1. **A regression-methodology lesson that may generalize.** Building the
   season-by-season regression this tool needs, a plain OLS on raw-dollar
   salary gave a systematically negative median residual every season
   (typical player looked overpriced by 8-22%, balanced to a near-zero mean
   only by a handful of $30+ stars). Switching to log-salary flipped the
   bias to systematically *positive* instead (the standard
   retransformation/Jensen's-inequality effect of exponentiating a log-scale
   fit back to dollars). Fixed *for this tool* by recentering each season's
   residual to its own median rather than trusting either regression's
   absolute calibration. Whether `klab/auction.py`'s exchange-rate
   regression (`fit_exchange_rate`, which the whole board's dollar scale
   depends on) has a comparable issue was **not checked** — it uses a
   different, already-validated construction (production regressed on
   price, not price on production, specifically to handle attenuation bias
   the other direction) — but the general lesson, that this league's salary
   distribution doesn't sit nicely around a linear-in-dollars fit, seems
   worth a deliberate look sometime, not an assumption either way.
2. **111 of 668 historical purchases (17%) have no position data** in
   `out/auction_sample.csv` (`pos` is null) and fall back to role-only
   comps here. Whether this is fixable (a name-based lookup against a
   position source not currently joined in) or a genuine gap in what
   the auction exports carry was not investigated — flagging it because
   it silently affects comp-pool size for every position-specific search
   this tool runs, and would affect anything else built on that file later.

## 36. A retained-but-unused extension right has zero value in the model, for any non-final-year contract

Flagged directly by Josh while reviewing Trade 1 (Spehr's Army sends Lowe,
Okamoto, Luzardo for Sánchez, Marte, De La Cruz): the side receiving the
three `F`-contract players is receiving players who are about to *spend*
their one lifetime extension as part of realizing the deal's value, while
the side receiving the three live-contract players is giving up players
who *retain* their extension right, unused, for whenever they individually
reach their own final year. Checked with `already_extended()` — confirmed
none of the six have used it yet, so this asymmetry is real, not already
netted out somewhere.

**The retained option is worth exactly $0.00 in every current dollar
figure, for any player not currently coded `F`.** Not a discount, zero.
`multiyear_surplus`'s extension-pricing branch only activates for
`is_final` contracts — a player with 1-3 years of live control has no
mechanism anywhere in the pipeline that prices "and someday, when this
runs out, there will be an extension decision too." This isn't a bug in
the sense of computing something wrong; it's a structural consequence of a
finite forecast horizon (ZiPS only reaches 2028) intersecting with a
contract mechanism that can be exercised at a point in time the model
can't see yet for most players.

**Rough magnitude check, not a fix**: ran each of the three live-contract
players (Lowe, Okamoto, Luzardo) through the same extension-option formula
as if they were at `F` today, using their own current 2027/2028
projections as a stand-in for whatever season they actually reach it.
All three came back **$0.00** — none clear the extension cost at their
current projected production (Okamoto and Luzardo are already
net-negative surplus without an extension question at all). This likely
*understates* what's missing, since a real option's value comes partly
from the chance production improves before the decision point, which a
single point-estimate check doesn't capture — but it's evidence the
omitted value for these three specific players is probably modest, not a
hidden second star.

**What this means for Trade 1's headline $25 surplus gap**: it's an
accurate account of everything the model currently prices, not the whole
economic picture. The omission cuts one direction only (understates the
live-contract side), so the true gap is probably smaller than $25, not
larger — but by how much isn't something this model can currently
quantify, because doing so would require projecting extension-worthiness
for a season beyond the data it has. Flagging as a genuine, general
modeling gap — not specific to this trade, and not resolved here.

## 37. Uncertainty bands were already done in the app — the roadmap said otherwise

Asked to make sure uncertainty gets reflected in the app *and* in how
valuations are done generally. Checked the app first, expecting to build
the ROADMAP.md 1.2 item from scratch. It was already there: `klab/uncertainty.py`'s
bootstrap (±34% per category) has been fully wired into `app/template.html`
since before this session started — a "likely range" column, a
`p_surplus_positive` "Sure?" column, tooltips, and full ranges on the
player card. `out/ROADMAP.md` had been claiming this was undone ("the ±34%
error bar is in the footer as prose") in two separate places, and I
repeated that stale claim back to Josh in an earlier turn this session
without checking the code first — exactly the class of error this project
has been catching all session, just committed by me this time instead of
found in the code. Corrected both places in `out/ROADMAP.md`.

**What actually was missing, verified directly**: `bootstrap_bands()` was
only ever called from inside `scripts/build_app.py`'s payload merge.
`klab.board.build_board()`, `klab.api.snapshot()`, `out/keeper_board_2027.csv`,
`scripts/eval_trade.py`, and `scripts/team_reports.py` all showed point
estimates only — including every trade evaluation earlier in this session,
which never displayed a confidence range for any player. Wired in for
`scripts/run_all.py` (now in the main board CSV, and therefore every CSV
derived from it) and `scripts/eval_trade.py`'s per-player table.
`scripts/team_reports.py` and `klab/auction_estimator.py` still don't show
bands — not done, logged in `out/ROADMAP.md`.

**What the bands actually reveal, now that they're visible in a trade
evaluation**: re-ran Trade 2/3 (Spehr's Army sends Scott/Walker for
Skubal/Freeman) with bands attached. Tarik Skubal's $17.97 multiyear
surplus — the number carrying most of that trade's conclusion — is
positive in only **73%** of 1,000 bootstrap draws, with a 10th-90th
percentile range of **−$7.4 to +$37.7**. That's a real, wide range, not a
rounding footnote: roughly 1 in 4 draws would call him a net loss to keep
at $38. Jordan Walker's headline +$0.21 surplus (essentially a coin flip
on the point estimate alone) is positive in only 61% of draws. Christian
Scott and Freddie Freeman are both **0%** — confidently bad keeps, which
the point estimates already suggested and the bands now confirm rather
than complicate. The trade's directional conclusion (favors Spehr's Army)
doesn't change, but "Skubal makes this trade a clear win" is a
meaningfully overstated way to describe a number that's genuinely
uncertain 27% of the time.

## 38. Roster update — two real trades, one FA move, resolved cleanly against 268-of-277 players untouched

Updated `data/rosters_valued.csv`/`rosters_current.csv`/`contracts_parsed.csv`
against a fresh CBS roster export. Matched all 277 players by `name_key`
(first-initial + last name — already built for exactly this) with team-level
disambiguation for three collision cases (two "C Smith"s, two "W
Contreras"es, two "J Duran"s, each already on the correct respective teams).
Detected, not assumed: two real trades already executed —

- **Spehr's Army ⇄ All-Stars**: Brandon Lowe, Kazuma Okamoto, Jesús Luzardo
  to All-Stars; Ketel Marte, Elly De La Cruz, Cristopher Sánchez to Spehr's
  Army. This is exactly "Trade 1" evaluated earlier in this session as a
  hypothetical — it has since actually happened.
- **Orange and Black Attack ⇄ NPB No Stars**: Julio Rodríguez to Orange and
  Black Attack, Chase DeLauter to NPB No Stars. Not previously discussed.

Xander Bogaerts appeared on NPB No Stars with no prior record on that
franchise — his last draft was 2025 @ $2 under "Moben," which
`data/franchise_map.csv` resolves to Orange and Black Attack's old name, not
NPB No Stars. No transaction log to check (the same recurring blocker as
§27/§11 of `out/LAB_NOTEBOOK.md`), so asked directly: confirmed he was
drafted 2025, kept into 2026, dropped mid-season, and re-added — so per the
**already-established** re-add rule (§23.6: a re-added player keeps his
original contract, not a fresh one), he carries his $2/`F` contract, not a
new free-agent price. Colt Emerson dropped off every roster with no
replacement team — treated as released, removed from the roster files
(his contract history is untouched in `contracts_parsed.csv` and he
reverts to ordinary free-agent status).

## 39. F-contract players were never actually extendable right now — a bigger correction than #33

Flagged directly by Josh, framed precisely: *"a player w F is going to free
agency. If they were extendable, then they had to be extended before the
start of their walk year (technically before the draft of the walk year,
the extension must happen or not)."* Checked against the constitution's
actual clause — "Players **about to enter** the final year of their
contract eligibility can be retained for additional seasons" — and the
plain reading confirms it: the decision happens before that season starts,
not during or after it.

**Why this is a different, bigger bug than #33.** #33 corrected *which*
contract codes are eligible for a live extension (only code `"1"`, not `"2"`
or `"3"`) — it left `F` alone, still treated as "the extension is live right
now." That's the part that was still wrong. `contracts_parsed.csv` is a
mid-2026-or-later snapshot. A player coded `F` in it was, by construction,
already "about to enter" his final year months ago (around the 2026 keeper
deadline, before the 2026 draft) — that window is the one that's closed, not
one still open for 2027. Every `F` player currently in the data already
missed his one shot; he is confirmed for the open 2027 auction pool, not
offering a live keep-or-extend choice at all.

`klab.board.build_board`'s `keepable` flag used to read
`~(already_extended & is_final)` — only excluding an `F` player who had
*already* burned a prior extension. A first-time `F` player, the common
case, was incorrectly treated as extendable right now. Fixed:
`keepable = ~is_final`, unconditionally. `klab.keeper.multiyear_surplus`'s
`F`-branch computation is untouched and still correct as a piece of math —
it's now documented as informational-only ("what an extension would have
been worth, if that window were still open"), never applied, since
`build_board`'s zeroing catches every `F` row regardless of what this
branch computes.

**League-wide impact, measured directly**: 37 players currently carry code
`F`. 35 of them were incorrectly marked `keepable=True` before this fix (only
2 were already correctly excluded, via a prior-extension history). **10 were
actually flagged `keep_2027=True`** and all ten flip to `False`. Total
`surplus_multiyear` removed from the board: **$130.48**. Six of the ten
flips are on Spehr's Army alone — Elly De La Cruz (−$16.18), James Wood
(−$15.87), Cristopher Sánchez (−$12.67), Jarren Duran (−$8.53), Josh Naylor
(−$4.28), Michael Busch (−$0.89), **$58.42 combined**, none of it connected
to the trades discussed earlier in this session — these were already on the
roster, independently wrong. The other four: Riley Greene (Lisbon Long
Balls, −$15.00), Jackson Chourio (McBlocks, −$7.31), Jackson Merrill
(McBlocks, −$7.01), Brice Turang (McBlocks, −$5.82).

**What this means for §36 and every trade evaluation run so far this
session that involved an `F`-contract player**: the multi-year surplus
figures reported for Sánchez, Marte, and De La Cruz in "Trade 1" (now
confirmed real, per #38) assumed a live extension option none of them
actually have. Those numbers need to be, and will be, rerun. §36's
extension-option asymmetry finding (retained-but-unused rights on
live-contract players being worth $0) still stands on its own terms, but
it was analyzing a trade whose `F`-side valuations were themselves wrong in
a much bigger way — the two corrections compound rather than offset.

**Verified with a new test**, not just a rebuild:
`test_f_contract_players_are_never_keepable` asserts every `F` player on
the real board has `keepable=False`, `keep_2027=False`,
`extension_option==0`, and `surplus_multiyear==0` — not just the ones
`already_extended()` would have caught before. 47/47 tests pass.

## 40. A trade-finder feature: precomputed suggestions, three scenarios, three real bugs caught building it

Built after manually searching for good trades between two teams earlier
this session (the NPB No Stars / Spehr's Army analysis) and being asked
whether that search could become a UI feature. It can, with one
architectural constraint worth stating plainly: the app is a single static
HTML file with no server, and only one thing was previously re-implemented
in JS for that reason (already a source of real drift bugs twice this
session — #32.1, and indirectly #37). A live "generate trades on click"
button would need either a full JS port of the search (a third
re-implementation to keep in sync) or a server (which the app deliberately
doesn't have). Built as a **precompute step** instead:
`klab/trade_finder.py` (the search), `scripts/build_trade_suggestions.py`
(runs it for all 45 team pairs, ~135s, `out/trade_suggestions.json`),
`build_app.py` ships the result as static payload data — same pattern as
every other number in the app.

**Three scenarios, one shared search.** All three draw from the same
per-team shortlist and evaluate the same 1-for-1 candidates through
`evaluate_trade()` once; only the scoring differs:

1. **Win-now for future** — only considered when two teams' 2026 standings
   are ≥8 points apart. Maximize the buyer's standings gain, subject to the
   seller's multi-year surplus gain being positive.
2. **Challenge trade** — maximize the *minimum* of both teams' standings
   gains; both must be positive. For two teams both live in the race with
   complementary category needs.
3. **Mutual value swap** — maximize the minimum of both teams' multi-year
   surplus gains; both must be positive. For two teams both out of 2026
   contention.

**"No trade found" is a real, returned result, not a search failure** — of
45 pairs, 2 came back 0/3 (McBlocks/Spehr's Army, Pookie 2.0/Producers) and
most came back 1-2/3. Nothing forces a weak suggestion to fill a slot.

**Three real bugs, caught by testing against real data before shipping,
not found in review afterward:**

1. **Worthless-return scoring.** First version of Scenario 1 suggested
   Vladimir Guerrero Jr. (NPB, −$13.0 surplus, a bad contract) for James
   Wood (Spehr's Army, $0 surplus — an F-contract rental, per #39). Scored
   positive because the *outgoing* piece was such a bad contract that
   anything looked like an upgrade, including a player worth nothing
   coming back. Fixed by requiring the specific player returning to the
   seller have positive *standalone* `surplus_multiyear`, not just a
   positive net delta.
2. **Shortlist too narrow.** Top-10-by-`roto_points` alone put 6 of Spehr's
   Army's 10 shortlisted players at zero keeper value (F-contract rentals
   with real talent but no future surplus), crowding out their actual
   positive-surplus trade chips (Langeliers, Lile, Stott) entirely out of
   the search. Fixed: shortlist is the union of top-10-by-talent and
   top-10-by-surplus, so both "good rental" and "good keeper" candidates
   are always in the pool.
3. **HTML/JS quote collision in the UI.** Embedding player/team names
   (`Spehr's Army`, `O'Brien`) as `JSON.stringify()`'d string literals
   inside a double-quoted `onclick="..."` attribute breaks HTML parsing —
   the literal apostrophe in the name terminates the attribute early.
   Caught by a targeted click-through test, not the existing generic
   tab-walk in `app/verify.mjs` (which renders the panel but never clicks
   inside it). Fixed with `data-*` attributes instead of inline literals,
   and the click-through test is now permanently part of `verify.mjs`
   itself, not a throwaway script — it would have caught this before ship.

**UI audit, requested in the same pass**: checked whether the hover-tooltip
"explain this column" feature Josh asked about already existed before
building it. It did — `COL_HELP` and `sortableTable()`'s per-column `help`
strings already cover the board, free-agent, teams, and standings tables,
built before this session. Found and fixed two real gaps instead of
building a duplicate: the Model tab's small denominator table had no
header tooltips at all, and the footer text along with the `contract`
column's own tooltip both still said "±38%" / "F = final year: extend or
lose him" — stale relative to #26/#39 earlier in this session. Neither was
caught by `verify.mjs`, which checks for JS errors and JS/Python numeric
parity, not prose content.

## 41. The trade finder was non-deterministic across identical reruns — caught checking auto-refresh safety

Found while verifying the build pipeline (`build_trade_suggestions.py` →
`run_all.py` → `build_app.py`) is safe to run unattended on a schedule —
not by testing the trade finder itself. Reran the full chain twice on
identical `data/` with nothing changed, then diffed the two
`out/trade_suggestions.json` outputs: 28 of 45 team pairs changed. Some
diffs were bigger than cosmetic — one candidate for Orange and Black
Attack ↔ Pookie 2.0's challenge trade moved from a 3.5-point standings gain
to 5.5 between runs with no code or data change in between.

**Root cause.** `_shortlist()` in `klab/trade_finder.py` returned
`list(set_a | set_b)`. Set *membership* was stable — reran `build_board()`
three times and md5'd the CSV, byte-identical every time — but set
*iteration order* is not: Python randomises string hashing per process by
default, so the same set of names came out in a different order each run.
`_search_pair()` iterates the shortlist in that order, and the three
scenario pickers (`_pick_win_now`, `_pick_challenge`, `_pick_mutual_value`)
kept the first candidate that beat the running best on a strict `>`. That's
fine when the true best is unique — but ties on the primary score are
common (e.g. two different return players both move a team's standings by
exactly 1.5 points), and on a tie, "first encountered" is exactly the part
of the computation that iteration order controls. Confirmed directly:
`_search_pair()`'s full 240-candidate result set was byte-identical (sorted
md5) across three fresh-process reruns, so the candidate pool was never the
problem — only which tied candidate the picker happened to keep.

**Why this matters beyond auto-refresh.** This wasn't only a hypothetical
cron-job concern. It meant `scripts/build_trade_suggestions.py`'s own
documented usage — "run this after roster changes" — could hand back a
different, sometimes strictly worse, "best" trade for the same roster
depending on nothing but which process happened to run it. A tie-break
that silently discards a Pareto-better candidate (same gain for one side,
more for the other) is worse than an arbitrary one: it's not just unstable,
it's occasionally wrong on its own terms.

**Fix.** `_shortlist()` now returns `sorted(set_a | set_b)` — order no
longer depends on the hash seed. More importantly, the three pickers now
break ties on a real secondary criterion instead of first-seen: score is a
tuple `(primary, secondary)` compared lexicographically, where secondary is
the sum of both sides' deltas. That doesn't just make the output
stable — it changes what gets picked: for the Orange and Black
Attack/Pookie 2.0 case above, Bryan Woo↔JJ Wetherholt (5.5/1.5) Pareto-
dominates Bryan Woo↔Aaron Judge (3.5/1.5) — identical for one side, better
for the other — and is now the deterministic answer instead of a coin
flip. Verified: reran the full build chain twice more after the fix and
diffed `trade_suggestions.json` — byte-identical both times. Regression
tests added: `test_shortlist_is_sorted` and
`test_challenge_picks_pareto_better_candidate_on_a_tie` in
`tests/test_trade_finder.py`; the second constructs a synthetic tie
directly rather than relying on reproducing a hash-seed race, since a
single test process reuses one hash seed for its whole lifetime and
wouldn't reliably reproduce the original bug.

**Scope check.** `_pick_win_now`'s tie-break (buyer_gain, seller_gain) was
audited the same way but had no live example in this league's current data
to reproduce against — added defensively, on the same reasoning, not
because a concrete instance was found.

## 42. A projection-basis selector — three payloads, swapped client-side, no rebuild

`PROJECTION_BASIS` (`klab/config.py`) is the biggest live fork in the whole
model: it decides whether 2027 numbers come from a reliability-weighted
blend of 2026 form and the ZiPS 2027 projection ("blend", the default), the
projection alone ("projection"), or 2026 actuals + rest-of-season alone
("actuals"). Roughly 17% of keep/cut calls flip depending on which one is
active, and until now seeing that meant editing `config.py` and rerunning
the whole build — not something a person evaluating a keeper decision at
the draft table was ever going to do.

**Why three full payloads, not a smarter diff.** The naive version of this
feature ships only the columns that visibly change (roto_points,
redraft_value, surplus_*) and reuses everything else. That's wrong: almost
nothing downstream of the board is actually basis-invariant.
`klab.api.snapshot()`'s `s.teams` (keeper counts, keeper salary, keeper
worth, aggregate surplus per team) and `s.constants` (inflation, $/roto
point, replacement level) are both aggregates *of* the board, so they move
with it too. Checked directly rather than assumed: at "blend" the league's
projected inflation is +31%, keeper salary $1998 against $1525 of
remaining talent; at "actuals" it's +41%, $1944 against $1374. A selector
that swapped the per-player table but left those cards fixed would have
been internally inconsistent on the very screen (League tab) most likely to
get compared line-by-line. So the unit of variation is the whole
board+free-agents+teams+constants bundle, not a handful of columns — three
full copies, not a clever diff. Confirmed the one thing that correctly
*shouldn't* move also doesn't: live 2026 standings ("points now" in the
League tab) were identical to the decimal across all three bases in
manual testing, since those come from this season's actual results, not a
projection.

**Why three fresh processes, not one process flipping a global.**
`klab.io.cached()` (see its own docstring) memoises every loader on its
function arguments only — never on ambient state like
`C.PROJECTION_BASIS`. Building all three bases in one Python process by
mutating that global between calls would silently hand the second and
third basis back the first basis's cached intermediate results the moment
any shared loader got hit twice. (This is exactly the failure mode #41
found in a different module, from a different angle — `_shortlist()`'s
sets weren't a caching bug, but the underlying lesson, "don't trust
in-process state to reset itself between logically separate runs," is the
same one.) Fixed by giving `PROJECTION_BASIS` an env-var override
(`KLAB_PROJECTION_BASIS`) and having `scripts/build_app.py`'s
`_basis_variants()` compute the ambient basis directly and spawn a fresh
`python3 build_app.py --variant` subprocess for each of the other two —
empty cache every time, by construction, not by discipline.

**The app side.** `app/template.html`'s `BOARD`/`FA`/`byId`/`idByName`
stay `const` bindings but get their *contents* replaced in place
(`.length = 0; .push(...)`), and `D.teams`/`D.constants` likewise —
deliberately, so every function that closured over the original array/object
reference keeps working without being rewritten to re-read `D.basis_variants`
itself. A header `<select>` calls `setBasis(basis)`, which does the swap,
recomputes `INFL` (`let`, not `const`, specifically so this could reassign
it), and calls the existing `render()` — no new rendering path, the
existing one just runs against new data.

**One bug caught in manual testing, before it shipped**: the Model tab's
"Active settings" panel showed `projection basis: blend` even while the
header selector displayed "2026 only" and every number on the page had
already changed — because that panel read `D.settings.PROJECTION_BASIS`,
a build-time value that `setBasis()` never touches (`D.settings` isn't one
of the objects the selector mutates, on purpose — it also holds unrelated
config like `SV_PUNT_THRESHOLD` that genuinely doesn't vary with the
selector). Fixed by overriding just that one displayed key with the live
`S.basis` at render time rather than mutating `D.settings` itself. Caught
by screenshotting every tab after a basis switch, not by `verify.mjs` —
its basis check (added the same session) only asserts on `roto_points`
numbers and the `<select>`'s own value, not on prose elsewhere in the page,
same blind spot #40 and #26 already noted for that script.

**Testing.** `tests/` doesn't cover this (it's a pure front-end feature —
Python only produces the three payloads, and that part is exercised
indirectly by every existing board test running with each basis in
practice unchanged). `app/verify.mjs` gained a fourth permanent check:
switches to "projection" and "actuals" and back to "blend", asserts a
majority of players' `roto_points` actually changed on each switch (272 of
275 in this league's current data), and asserts the round trip back to
"blend" reproduces the original numbers exactly — round-tripping matters
because `setBasis()` mutates shared objects in place rather than
reassigning them, which is exactly the kind of code that can leave stale
leftovers behind if a clear-then-refill step is missed.

## 43. Auction-estimator UI integration — a player-card panel, and a real bug it exposed on the way in

Wires `klab/auction_estimator.py` (built earlier this session, #35 —
comp-based next-auction price, deliberately separate from `redraft_value`)
into the app, closing `out/ROADMAP.md` 3.6. Design wasn't discussed in
advance, so it's worth stating the two calls made and why.

**Precompute, not live, same reasoning as everything else in this app.**
`estimate_auction_price()` is fast per player (~1000 players/sec, checked
directly) but there's no server to call it from — same constraint that
made the trade finder (#40) and the basis selector (#42) both precompute-
and-ship rather than compute-on-click. `scripts/build_app.py`'s
`_auction_estimates()` runs it for every player with `roto_points > 0`
(~673 of 675 board+free-agent rows) and ships fair value, comp-adjusted
low/mid/high, and the top 8 comps, keyed by `fg_id`.

**Computed per basis, not once.** `estimate_auction_price()`'s own base
number is `regression_fair_value = row["redraft_value"]` — exactly the
column the projection-basis selector (#42) changes. Shipping one
auction-estimate payload pinned to "blend" while the rest of the page
followed the selector would have reproduced the identical bug #42 already
found and fixed for team/constant aggregates, in a feature built in the
same session as the fix. So `_auction_estimates()` was folded into the
existing per-basis `_variant_payload()` / `_basis_variants()` machinery
rather than computed once — it now runs three times (once per basis, same
fresh-subprocess pattern as everything else there) instead of being a
fourth special case.

**A real bug, not a design question: `allow_nan=False` caught a data gap
immediately.** The first full build crashed on `json.dumps`: "Out of range
float values are not JSON compliant." Root cause: `auction_sample.csv` has
a handful of historical purchases with a missing `pos` — pandas represents
that as `float('nan')`, not a string — and the comp-table serialization
only ran the existing `_round()` NaN-safety helper over the *numeric*
fields (`salary`, `premium_pct`), assuming `player`/`team`/`pos` were
always valid strings. They weren't, for several dozen of 673 players'
comp lists. Fixed by running every comp field through `_round()`
uniformly — it already has a `str`/`None` fallback for exactly this case,
the bug was just not using it everywhere. Same lesson as #33/#39's
category of bug: an assumption ("this column is always populated") that
was true often enough to never get tested until the full data volume ran
through it.

**Payload cost.** `out/keeper_lab.html` grew from 1.17 MB (after #42) to
3.74 MB — three bases × ~673 players × up to 8 comps each is the real
driver, not the summary numbers. Still well inside "opens on a phone,
attaches to an email" territory, but flagged here rather than silently
accepted: if a future feature adds a fourth expensive per-player,
per-basis payload, this is the point to reconsider trimming (fewer comps
shown, or shorter JSON keys) rather than letting it compound unnoticed.

**UI placement.** A new panel in the player-card drawer
(`app/template.html`'s `showPlayer()`), between "Money" and "Rest of
2026" — titled plainly as a second, independent estimate, not a
correction, with the same "no age/debut-year data exists" caveat the
Python module's own docstring states, so the gap is visible in the UI, not
just in a comment. Absent entirely (no empty panel, no placeholder) for
players below the `roto_points > 0` cutoff, same "don't force a weak
result to fill a slot" pattern as the trade finder's "no deal found."
`app/verify.mjs` gained a permanent check: the panel renders with comp
rows for a player who has an estimate, is absent for one who doesn't, and
its displayed fair value actually changes when the basis switches
(confirming the per-basis wiring above actually took effect, not just that
the code runs without crashing).

## 44. UI audit: a stale pre-#39 status string, a missing IL/LOCKED tag, and two confirmed false alarms

Requested directly ("really work hard on making sure that's solid, that
info is accessible") ahead of Josh testing the UI himself. Method: screenshot
every tab at desktop and mobile widths, exercise every filter/toggle/sort
combination, open the drawer for one example of each player archetype
(two-way, IL, F-contract, extension-eligible, free agent), fill out the
trade tab, and read every screenshot rather than trusting `verify.mjs`'s
green output alone — the same method that caught #42's stale settings
display. Two real bugs found and fixed; two more things looked wrong and
turned out not to be, worth recording so they aren't "found" again.

**Bug 1 — `keeper_status()` never got the #39 memo.** Opening an F-contract
player's card (Salvador Perez) showed the subheader "All-Stars · extension
+$5" directly under the team name — a live, specific extension price — while
the Money panel two inches below correctly showed `extension_option: $0.0`
and `multi-year surplus: $0.0`. Root cause: `klab/board.py`'s
`keeper_status()` returns a hardcoded `"extension +$5"` string for every
`C.EXTENSION_REQUIRED` contract code, unchanged since before #39's
correction that F-contract players are never extendable. #39 fixed every
*numeric* consequence of the wrong premise (`keepable`, `extension_option`,
`surplus_multiyear` all correctly zero) but nobody re-checked the *string*
against the corrected model, because it only surfaces in the app's own
prose, not in any number a test would compare. Fixed to `"free agent after
2026 (not extendable)"`, matching the `COL_HELP.contract` tooltip's own
language. New test: `test_f_contract_status_label_does_not_claim_an_extension_exists`
(`tests/test_invariants.py`) asserts no F-contract player's status string
contains a `$` sign, specifically so a future edit that reintroduces a
dollar figure here fails loudly.

**Bug 2 — the drawer had no IL/LOCKED indicator at all.** The board table
(`playerRow()`) has always shown `KEEP`/`IL`/`LOCKED`/`EXT`/`USED` tags next
to a player's name; the player-card drawer (`showPlayer()`) showed none of
them — opening a player's own detail view was the one place in the app that
couldn't tell you he was hurt or unkeepable without going back to the table
row. Fixed by adding the identical tag logic to the drawer's `<h2>`.

**False alarm 1 — mobile board table looked crushed and unreadable in a
`fullPage: true` Playwright screenshot.** A 390px-wide capture showed all 14
columns squeezed into illegible text across a ~9000px-tall page. Investigated
before concluding it was real: measured the actual rendered DOM (`th`
elements are present but `display:none`'d correctly by the existing
`@media(max-width:700px)` rule) and took a viewport-only (non-fullPage)
screenshot instead, which showed exactly the intended reduced column set
(`Player`/`Sal`/`Cost`/`Worth '27`), clean and legible. `fullPage`
screenshots of a page with an internally-scrolling/overflowing element
apparently don't reliably reflect the live-viewport rendering — worth
remembering for any future UI audit that leans on this technique.

**False alarm 2 — a free agent's drawer appeared to be missing the
"Next-auction estimate" and "Rest of 2026" panels entirely** in the same
kind of `fullPage` screenshot, cut off mid-page with a large blank area
below. Same root cause: `#drawer` is `position:fixed` with its own
`overflow:auto`, and a `fullPage` body screenshot doesn't capture that
element's internal scroll correctly. Confirmed via direct DOM inspection
(`$("dbody").innerHTML.includes(...)`) that both panels were present and
correctly populated all along — nothing to fix.

**Real gap surfaced but not fixed: free agents never get uncertainty
bands.** The free-agent table's "Likely range" and "Sure?" columns are
blank for all 400 rows — not a display bug, but a genuine, pre-existing
scope limit in `klab/uncertainty.py`'s `bootstrap_bands()`: it derives
`keep_ids` from `board["fg_id"]` (rostered players only) because it needs
each player's real contract (`keeper_cost`, `years_controlled`, `salary`,
`keepable`), fields a free agent's hypothetical "live draft contract" only
partially resembles. Extending it to free agents is a real modelling
decision (does a FA's listed salary mean the same thing a rostered
player's contract does, for this specific calculation?), not a UI fix, so
it wasn't attempted here. What *was* fixed: the blank dash previously had
no explanation anywhere a user could find it — `FA_NOTE` (shown under the
free-agent table) now states directly why those two columns are empty,
so it reads as a stated limitation instead of a possible bug. Logged as a
candidate for a future modelling session, not added to `out/ROADMAP.md`'s
numbered list since it's not yet scoped enough to size.

## 45. A blended 2026 rest-of-season signal, and a real bug in the first version

Requested directly: `ros_lines()` (ZiPS's own rest-of-season system) was the
only signal feeding the win-now standings engine and `ros_value_over_replacement`.
Added a second, independent signal and a way to blend them.

**The new signal** (`klab/trade.py`'s `prorated_to_date_lines()`): each
player's 2026 season-to-date rate, extended over however many games are
left in the season. "Games left" is a single, shared, league-wide estimate
— `C.SEASON_GAMES` (162) minus the `C.GAMES_PLAYED_PCTILE` (95th
percentile) of games played among hitters with PA > 300, since that's the
closest available proxy for "how many games has a healthy everyday
player's team played by now" without a per-team schedule lookup. As of
2026-08-13 that comes out to 119 team games played, 43 left.

**`ros_lines_for_basis(basis)`** dispatches between `"ros"` (default —
every existing caller's behavior is unchanged), `"prorated"`, and
`"blend"` (the two averaged 50/50). Wired into `win_now_delta()` and
`evaluate_trade()` via a new `ros_basis` parameter.

**No "pre-season 2026" option, and why not.** Asked for directly, checked
directly: no file in `data/` has a full-season 2026 projection made before
the season started. The ZiPS Depth Charts exports on hand
(`fg_zips_dc_2027_*`, `fg_zips_dc_2028_*`) are for the two out-years this
project already uses for keeper valuation, not 2026 itself, and
`data/README.md` lists nothing else that would qualify. Building this
option would mean sourcing a new export, not writing new code against data
already on hand — flagged rather than faked with e.g. the ROS-only line
relabeled, which would silently misrepresent what the number is.

**Real bug, caught before it reached any analysis:** the first version of
`prorated_to_date_lines()` divided each player's season-to-date stats by
his OWN `G` (games played) to get a per-game rate. Fine for hitters, whose
own `G` tracks team games reasonably well. Wrong for pitchers: a starter's
`G` counts his STARTS, not team games — Tarik Skubal's 18 starts and 107.2
IP gave a rate of ~5.96 IP per appearance, multiplied by the ~43 remaining
TEAM games as if he'd start in every one of them, projecting **256 more
innings** — more than a full season for anyone. Caught sanity-checking the
trade re-analysis below, not by a test (the tests written alongside this
function checked "non-negative" and "plausible remaining-games total," not
"is this specific player's number sane" — a lesson repeated from #41 and
#43 this same session: aggregate/range checks don't catch a per-player
outlier). Fixed by dividing every player's stat by the SHARED team-games-
played estimate instead of his own `G`. This has the right effect
automatically for both roles: it dilutes a starter's rate by the ~4 team
games he doesn't pitch in (since his to-date innings are now divided by
ALL team games played, not just his 18 starts), without needing separate
starter/reliever branches. Re-verified: Skubal now prorates to 38.7
remaining innings against ZiPS's own 46.0 — sane, and the two independent
methods landing in the same neighborhood is itself a useful cross-check.
See out/LAB_NOTEBOOK.md #24.

**Trade re-analysis using this** (NPB No Stars ↔ Spehr's Army / Pookie
2.0, requested with three specific framings: 2026 value via
`ros_value_over_replacement` — team-agnostic, not a specific acquiring
team's marginal standings swing — and 2027 value in both inflation-
adjusted and raw draft-dollar surplus terms, plus roto points on an
average-team basis via `d_roto_points_2027`) is written up in the
session log rather than here, since it's advice on specific trades, not a
model finding — matching how the earlier NPB/Spehr's Army and
Skubal/Pookie 2.0 explorations this session were handled.

## 46. A rest-of-2026 basis toggle in the app — Standings and Trade only, never a dollar value

Shipped #45's blended signal as a UI control rather than only a script
parameter, requested directly alongside it. Design questions worth stating,
since none were discussed in advance:

**Scope: which screens.** Only `#tbl`-adjacent rest-of-season math —
the Standings tab's projected-finish columns, and the Trade tab's win-now
delta — reads `ros_*` fields at all. Everything else (Keeper board, League,
Free agents, Model, and every dollar figure everywhere) is downstream of
`redraft_value`/`surplus_multiyear`, which come from the *2027* pipeline
and never touch this. So the control lives contextually in those two tabs'
own `.bar`, not the global header next to the projection-basis selector —
putting it there would imply it does something on every tab, which would
be wrong on four of six.

**Payload: independent of PROJECTION_BASIS, not multiplied by it.**
`scripts/build_app.py`'s `_ros_variants()` computes the three ROS bases
ONCE, not once per projection basis — unlike `_auction_estimates()`
(#43), nothing here is a function of a dollar value, so there's no
per-basis staleness hazard to guard against, and tripling it would have
been pure waste. Keyed by fg_id so the browser can overwrite a board row's
`ros_*` fields in place, the same pattern `setBasis()` already uses.
Payload cost: +~290 KB (out of 4.03 MB after this) — 3 variants × ~675
players × 13 fields, negligible next to the auction estimator's comps.

**Real interaction bug, caught before shipping — not a modelling bug this
time, a state-management one.** `setBasis()` (the projection-basis
selector) replaces `BOARD`/`FA` wholesale with a new basis-variant's rows,
and every basis-variant's board is built by merging the SAME default
(`"ros"`) rest-of-season signal — `PROJECTION_BASIS` has nothing to do
with which ROS basis is active. So switching projection basis while a
non-default ROS basis was selected would silently overwrite the `ros_*`
fields back to ZiPS-only, discarding the user's toggle choice with no
indication anything changed. Fixed by having `setBasis()` call
`setRosBasis(S.rosBasis)` as its last step, reapplying whatever was
active rather than assuming the reset. `app/verify.mjs`'s new check
covers exactly this: set ROS basis to "prorated", switch projection basis
to something else, assert `S.rosBasis` is still `"prorated"` — this is
the one case in the whole check that would have passed a naive "does the
toggle work" test and still shipped broken, since testing either toggle
in isolation looks fine.

**Testing.** `app/verify.mjs` gained a fifth permanent check: the toggle
recomputes `PROJ_PTS` (proves `recomputeProjections()` ran, not just that
the underlying data changed), round-trips back to the default exactly, and
survives an unrelated basis switch as described above.

## 47. ROS value on the Keeper Board / Free Agents tables — a second toggle stacked on the first

Requested directly: the rest-of-2026 basis toggle (#46) only lived on the
Standings and Trade tabs; the Keeper Board (and, since it shares the same
table code, Free Agents) had no rest-of-season value column at all —
everything there was 2027-only. Added a "ROS value" column
(`ros_value_over_replacement`, out/FINDINGS.md #34 — a player's intrinsic
rest-of-season value, not a team-standings swing) and put the same
rest-of-2026 basis picker in the board/FA control bar.

**The real complication this exposed**: `ros_value_over_replacement` isn't
a function of ONE toggle, it's a function of both. Its inputs are a
ROS-basis-dependent piece (which `ros_*` line — #45/#46) and a
PROJECTION_BASIS-dependent piece (the denominators/baseline/replacement
level that price it, all downstream of the 2027 pipeline). A value that's
only correct for one specific combination of the two toggles would be
subtly wrong the moment a user touched the other one. Handled the same way
#43 handled an analogous problem for the auction estimator: nest the
second toggle's computation inside each of the first toggle's three
per-basis subprocesses (`scripts/build_app.py`'s `_ros_values()`, called
from inside `_variant_payload()`), producing a full 3×3 grid rather than
computing it once and hoping the other toggle doesn't matter much.

**Read live, not mutated into the row array.** Unlike the raw `ros_*` stat
columns (which `setRosBasis()` overwrites directly on each board row so
`rosterAgg()` keeps working unchanged), the new column is looked up at
render time via `rosVal(r)` against `ROS_VALUES[S.rosBasis][fg_id]` — it
isn't a real board-row field, so `sortRows()` needed a one-line special
case (`k==="ros_value"` uses `rosVal` instead of the generic row-array
lookup `g()`) or sorting by the new column would have silently sorted
nothing, using `undefined` for every row. Caught before shipping by
actually testing the sort, not just that the column renders.

Payload cost: +~123 KB (small — one float per player per ROS-basis, not a
whole row). `app/verify.mjs` gained a permanent check for the sort
correctness and basis-responsiveness together.

## 48. Historical standings, 2022-2025, normalised to current franchise names

Requested directly — `data/standings_long_all.csv` already covers
2022-2026 and nothing surfaced the past seasons anywhere in the app.
Added a season picker on the Standings tab: "2026 — live + projected"
(the existing view, unchanged) plus one final-standings table per
completed season, computed once in `scripts/build_app.py`'s
`_historical_standings()` (basis-invariant — history doesn't move with
either toggle, so it isn't nested in the per-basis subprocess machinery
like #43/#47).

**Team names are shown under their CURRENT franchise name, not whatever
they were called that season**, using `data/franchise_map.csv`. This
league has renamed five franchises since 2021 (e.g. 2025's "Moben" is
today's Orange and Black Attack). Showing the historical name would be
literally accurate but useless for the actual question a history view
answers — "how has this team done over time" — since a viewer would have
to already know the rename chain to follow their own team's arc. Every
row is grouped by `franchise_id`, not by name.

## 49. 2027 standings from keeper sets alone — and a bad replacement-line pick caught before shipping

Requested directly, alongside #48. New calculation, not just a display of
existing numbers: `scripts/build_app.py`'s `_keeper_standings_2027()` sums
each team's KEPT players' 2027 stat lines, fills every roster slot not yet
occupied by a keeper with a replacement-level line, and runs the same
`standings_points()` ranking the rest of the app uses. Deliberately framed
as **keeper-core strength, not a forecast of who wins the real 2027
auction** — every team will also spend real money in that auction, and
this model doesn't attempt to predict what any specific team will do with
it (nothing else in the app does either). Basis-dependent (a team's kept
players' 2027 production moves with `PROJECTION_BASIS`), so it's nested
inside `_variant_payload()` like #43/#47, not computed once.

**Real bug in the first version, caught by eyeballing the output before
shipping, not by a test.** The replacement-level stat line (needed to fill
empty roster slots with something) was originally the SINGLE player
closest to `replacement_rp` by `roto_points`. That player turned out to be
a mediocre closer — saves are valuable enough that a so-so closer clears
replacement level on total roto_points even though a real generic
replacement-level pitcher is almost never a closer. Every team's empty
pitcher slots were getting **~25 saves each** injected into their
projected total, which would have wildly inflated SV across the board and
distorted every category's ranking that trades off against it. Fixed by
averaging a 15-player band around `replacement_rp` instead of taking the
single nearest match, separately for hitters and pitchers — smooths out
one player's idiosyncratic category profile. Sanity-checked the fixed
band average directly: SV dropped from 25.3 to a realistic 5.3.

## 50. The Intuition tab — manual player shading, sandboxed, split into an exact half and an approximate half

Requested directly: let a user layer their own read on a player ("the
model's wrong about him, up or down") on top of the model's numbers, and
see the impact — a "plus/minus on talent" control, plus a "force full
health" toggle, two-stage (set shades, then recalculate).

**The central design question, asked directly and answered before
building anything**: can a static HTML file with no server do this? Split
the answer in two, because the app's architecture forces the split:

- **2026 rest-of-season / standings impact: yes, exactly.** The win-now
  standings engine (`rosterAgg`/`catTotals`/`rotoPoints`) already runs
  entirely client-side — the one thing this app deliberately reimplements
  in JS. `rosterAgg()` gained an optional per-column multiplier map
  (`{fg_id: {colName: mult}}`, not one scalar per player) so a shade can
  be applied without touching `BOARD` at all: talent moves a player's
  PRODUCTION RATE (H, HR, K, etc.), health moves his PLAYING TIME (PA,
  IP), and the two are separate axes on purpose — conflating them would
  make "shade him up" ambiguously mean either "he'll play more" or "he'll
  play better."
- **2027 dollar impact: no, not a real re-run — and said so in the UI,
  not just in a comment.** A true re-derivation needs the denominators,
  the roto scorer, the auction exchange-rate regression, and multi-year
  surplus logic, all of which live only in Python. Porting that to JS so
  a shaded player's dollar value re-derives correctly would mean
  maintaining two implementations of the whole valuation model — the
  exact failure mode this project already got burned by once this
  session (the PA_x/PA_y JS/Python drift bug) and has deliberately kept
  server-side-only ever since (`out/ARCHITECTURE.md` §4.2). Instead, the
  2027 panel applies **transparent linear scaling**: the already-computed
  `redraft_value` times `(1 + talent_shade)`, with the *already-computed*
  `redraft_value_ft` (full-time projection) substituted in first if health
  is forced, rather than inventing a second scale-up. Labeled plainly in
  the UI as an approximation, not a new official number.

**Sandboxing.** Shading never touches `BOARD`, `PROJ_PTS`, or any other
tab — every other screen's numbers are unaffected by what's set here.
Verified in `app/verify.mjs`, not just assumed: the new check confirms a
shaded player's `ros_R` on `BOARD` and the league-wide `PROJ_PTS` total
are bit-identical before and after shading and recalculating.

**A real result worth knowing, not a bug**: shading one pitcher by a
realistic ±10-15% often shows "0.0 change" in team standings. This is
correct, not broken — roto standings are RANK-based, not continuous, so a
modest boost only moves a team's points if it's large enough to cross
another team's total in that specific category. Confirmed directly:
shading Tarik Skubal to the maximum (+30% talent, health forced) DOES
move NPB No Stars from 26 to 28 points (via K and WHIP crossing a
rank threshold), while a realistic +10%/health-forced shade shows no
movement at all for the same player. Added a note in the UI so a user
doesn't mistake "the standings math is genuinely insensitive to a small
shade" for "the feature doesn't work."

**Two small, real additions along the way**: defensive position (`board.position`, from `klab.keeper.position_map()` — an auction-history match, so it's `"?"` for anyone with no draft record on file, an honest gap rather than a guess) and a `playerTooltip()` helper showing 2027 roto points by category, ROS line, contract status, and position on hover — requested as a general design rule, not just for this tab: **sortable/scannable numbers belong in columns; everything else belongs in a tooltip**, so a table doesn't get cluttered with context nobody's comparing across rows. No age anywhere — no file in `data/` has one, same gap already stated for the auction estimator (#35).

## 51. Playing time gets its own weight, decoupled from the rate/talent blend

Found chasing down why Hunter Brown's 2027 value ($10.68) looked so much
lower than his 2028 value ($20.08) despite ZiPS's own raw 2027 and 2028
lines being nearly identical (163.3 IP / 3.09 ERA vs 162.7 IP / 3.15 ERA —
ZiPS isn't projecting improvement). The mechanism: `klab/project.py`'s
`_blend_weight()` computed **one weight** from 2026 sample size and used
it for both the rate blend (talent) and the playing-time blend (PA/IP) at
once. Brown made only 12 starts (63.2 IP) before the export date; his
2026-actual-plus-ROS full-season estimate came out to 107.2 IP against
ZiPS's own healthy 163.3 IP opinion for him. Because his sample already
cleared the (previously shared) 50%-weight cap, the blend landed at a flat
50/50 split — 135.25 IP — regardless of *why* his 2026 was short. The
model had no way to distinguish "he's just not a big-workload guy" from
"he got hurt and will be fine next year," and it was quietly assuming the
former for every shortened pitcher season in the league.

**Fix**: playing time now gets its own weight, capped separately and lower
than the rate/talent weight (`PT_BLEND_CAP_HITTER` = 0.30,
`PT_BLEND_CAP_PITCHER` = 0.15 — Josh's judgment calls, not fit from data,
stated as tunable in the config comment). The rate blend (and its existing
per-stat `RELIABILITY` discount, #28) is untouched — a short sample is
still real evidence about how good a player is; it's now treated as much
weaker evidence about how much he'll play in a healthy 2027. Pitchers get
a lower cap than hitters on purpose: an interrupted pitcher-season skews
injury-driven, while a shortened hitter-season is more often
role/platoon/performance-driven — information actually worth keeping
weight on. Verified directly: Brown's blended IP moved from 135.25 → 154.9
(much closer to ZiPS's 163.3), ERA/WHIP unchanged (3.15 / 1.19 exactly —
confirms the rate blend wasn't touched), `redraft_value` $10.68 → $16.92,
closing most of the gap to his $20.81 2028 figure.

**League-wide impact, measured**: 10 keep/cut flips (Oneil Cruz and Wyatt
Langford flip IN; Mike Trout, Yandy Díaz, Cam Smith, and others flip OUT,
among hitters too — this isn't pitcher-only, since hitters got the same
decoupling with a higher but still-lower cap). Total `surplus_multiyear`
shift across the rostered pool: **−$13.71**. Worth stating plainly: this
fix is **not one-directional**. It helps players whose 2026 playing time
undershot ZiPS's own expectation (Hunter Brown, Logan Webb — flips into
keep) and *hurts* players who threw/played *more* than ZiPS expected
(Yoshinobu Yamamoto — flips out of keep), since the model now trusts
ZiPS's playing-time opinion more in both directions, not just the
sympathetic one. That's the intended, symmetric consequence of "trust the
projection system's role expectation," not a one-sided patch — a
workhorse outperforming his own durability forecast is regressed toward
it exactly as an injured pitcher is.

**Deliberately not done in this pass**: using the `il` roster flag (merged
onto the board already, currently used only for the UI's "IL" tag) as a
targeted signal to push playing-time weight toward ZiPS specifically for
currently-injured players. That would need threading roster/IL status
into `klab/project.py`, which doesn't currently see it at all — a real,
scoped follow-up, not implemented here because it wasn't part of what was
explicitly asked for this pass.

## 52. Positional adjustment for catchers and shortstops — and a surprise: both positions are deep, not scarce

Prompted by the Dillon Dingler deep dive (#51's companion question): he's
this year's best-producing catcher by a wide margin, so shouldn't catcher
scarcity make him worth more than the pooled replacement-level system says?
Testing that required real position-eligibility data the model didn't have —
FanGraphs' "at least one PA at C" / "at least one PA at SS" exports for 2026
(`data/fg_catchers_2026.csv`, 106 players; `data/fg_shortstops_2026.csv`, 115
players), joined on `fg_id`. Scoped to these two positions only, not the full
defensive spectrum: they're the two positions this league's roster actually
forces a start at every week, and a `positional=True` full-spectrum version
already existed (`klab/keeper.py`'s `positional_replacement()`) but stayed
disabled — its lookup only covers ~52% of the player pool, short of the ~90%
a real replacement-level estimate needs, and nothing in this pass changed
that. The two-position version doesn't need that guard: `data/fg_*_2026.csv`
give an explicit eligibility set to check membership against, not a sparse
lookup to trust the coverage of.

**Mechanism** (`klab/keeper.py`'s new `two_position_replacement()`,
threaded through `value_players()`/`value_2028()`/`build_board()`/
`free_agent_board()`/`snapshot()` as a `positional: bool` argument — off by
default, on by toggle): for C and SS, replacement level is now the
10th-best-in-that-position score (`C.TWO_POS_SLOTS[pos] * C.N_TEAMS`)
instead of the pooled 230th-best-overall score. Every other position keeps
the pooled line unchanged.

**The surprise**: on this league's real 2026 data, BOTH positions came out
**deeper** than pooled, not scarcer —

| | roto points |
|---|---|
| pooled replacement | 4.80 |
| catcher replacement | 5.12 |
| shortstop replacement | 6.76 |

A higher replacement bar means a *smaller* gap between a given player's
production and "what you could get for free," which is a smaller dollar
value, not a bigger one. So turning positional adjustment on mostly
*lowers* catcher and shortstop values relative to today's pooled system —
the opposite of the scarcity premise the original ask assumed. Dillon
Dingler specifically: **$2.46 pooled → $0.24 positional**, not $10. He
isn't being underpaid for scarcity; on this league's numbers, the catcher
pool this year is deep enough that a below-average bat with playable
defense (which is most of what's behind Dingler in the FanGraphs export)
holds real value, dragging the position's own replacement level up past
the league-wide bar. Bobby Witt Jr., a shortstop who's nowhere close to
replacement level either way, still drops **$36.10 → $26.52** for the same
scale reason described next. This is worth saying plainly since it cuts
against what "scarcity" usually implies in fantasy analysis: scarcity
raises value only when the *replacement option* at a position is bad, and
this league's ten C-eligible and eleven SS-eligible rosters this year
don't produce a bad one.

**Everyone else moves too, and not always down.** Positional adjustment
shrinks the pool of total "points above replacement" that gets divided
among all 230 rostered players to reach the league's $2,600 budget
(`out/METHODS.md`'s calibration), so the leaguewide $/point rate rises
(**$6.58 → $7.56** per point) and every player *not* touched by the C/SS
override gets modestly more valuable in dollar terms even though his own
roto-point total hasn't changed. Tarik Skubal is the clean illustration:
**$52.12 pooled → $59.76 positional** — a pure scale effect, since he's
neither a catcher nor a shortstop.

**League-wide keep/cut impact, measured**: 15 flips. Six flip OUT, all
catchers or shortstops paying the higher position-specific bar (Otto
Lopez, Jeremy Peña, Geraldo Perdomo, JJ Wetherholt, Dansby Swanson, Drake
Baldwin); nine flip IN, all non-C/SS players benefiting from the
scale-wide rate increase (Roman Anthony, Kyle Schwarber, Yandy Díaz,
Ronald Acuña Jr., Pete Alonso, Xavier Edwards, Corbin Carroll, plus
pitchers Bryan Baker and Yoshinobu Yamamoto).

**Two real bugs found building this, both caught by direct comparison
testing before shipping, neither by a passing check going wrong quietly**:

1. **A `min()` that silently no-op'd.** The first version picked a
   player's effective replacement level as
   `np.minimum(pooled, positional)`, meant to let a player eligible for
   both adjusted positions take whichever was more favorable. The same
   `min()` also compared against the pooled default — and since *both*
   adjusted positions came out higher than pooled (the surprise above),
   `min()` always kept the pooled value. `positional=True` produced
   byte-identical output to `positional=False`, no error, no warning.
   Caught only by diffing Dingler's `redraft_value` on and off and finding
   it unchanged. Fixed by building the override as an explicit
   elementwise minimum across *only* the positions a player is eligible
   for, applied unconditionally via a mask, rather than folding the
   pooled default into the same `min()`.
2. **The budget identity broke after fixing bug 1.** Once values actually
   started moving, `budget_check_top230` jumped to $2,834.58 against a
   target of $2,600 — `dollars()` floors every player's value at $0
   (`.clip(lower=0.0)`), but the pool total feeding the $/point calibration
   was summing raw, unclipped `roto_points − replacement`. A player like
   Dansby Swanson can rank in the overall top 230 while sitting *below*
   his own position's (higher) bar — his `dollars()` value floors at $0,
   but the unclipped pool sum had still counted his negative contribution,
   breaking the linear calibration. Fixing the pool sum to clip the same
   way `dollars()` does brought the check to $2,572.86 — about 1% off,
   not exact. Left as an accepted approximation rather than chased
   further: getting it to exactly $2,600 would need iterative fitting,
   since the clip threshold and `dollars()`'s own `+$1` floor interact
   non-linearly, for a number whose only job is a sanity check.

**Shipped**: a checkbox in the app header (next to the projection-basis
selector, since — like that toggle — positional adjustment repriced
dollar values across every tab, not one) wired through
`app/template.html`'s `setPositionalAdjustment()`/`applyVariant()`, backed
by both settings shipping in the payload
(`D.basis_variants[basis].positional_variants.off/on`) so switching is a
re-render, same pattern as the projection-basis selector. Composes
correctly with that selector — switching either one reapplies the other's
current setting rather than silently resetting it, covered by a permanent
`app/verify.mjs` check. `AUCTION_EST`/`ROS_VALUES`/`KEEPER_STANDINGS_2027`
stay pinned to the pooled (`positional=False`) board regardless of the
toggle, a documented scope limit for cost reasons, consistent with how
#43/#47/#49 handled their own second toggle.

**Not done in this pass**: the full defensive spectrum (1B/2B/3B/OF)
stays on the pooled line — `positional_replacement()`'s ~52%-coverage gap
is unresolved, and closing it would need a similarly complete FanGraphs
eligibility export for every position, not just the two requested here.

## 53. Direction-aware pitcher playing-time trust, an upside_ft split, and a second copy of #52's own bug

Prompted by a specific complaint: Gerrit Cole $0, Zack Wheeler $3.41,
Cam Schlittler $4.91, next to Logan Webb at $26.68 — is good pitching
systematically undervalued by playing-time caution? Splitting each
pitcher's blended 2027 innings into its two ingredients (`IP_a` = 2026
actual + ZiPS rest-of-season, `IP_b` = ZiPS's own 2027 preseason opinion)
turned up two *different* mechanisms, not one:

- **Established/TJ-recovery arms** (Cole, Sandy Alcantara, Wheeler, Jacob
  deGrom): ZiPS's own 2027 opinion is *lower* than what they actually threw
  in 2026 (Cole 129.2 actual vs. 102.0 ZiPS; Alcantara 213.2 vs. 149.0) —
  real durability/decline skepticism baked into ZiPS itself, not something
  the blend invented. Cole and Alcantara's low value isn't a playing-time
  story at all: their blended *rate* stats are also below replacement (Cole
  ERA 4.08), so `redraft_value_ft` (the full-workload case) is $0 for both
  too. Trusting that is a real methodology choice, not a bug.
- **Young pitchers who already threw a full workload**: Cam Schlittler (187
  actual vs. 128 ZiPS), Jacob Misiorowski (175 vs. 116), Chase Burns (164
  vs. 106) — the opposite pattern. ZiPS's 2027 opinion is *below* what they
  already proved they could do, most likely a generic "don't jump a young
  arm's innings too fast" caution rather than an injury read. "He already
  did this in 2026" is stronger evidence than a system's generic caution
  about a sophomore workload jump.

**The fix (Josh's call, implemented as proposed): direction-aware trust.**
`project_pitchers()` now checks `IP_a > IP_b` per player. When true — he
already exceeded ZiPS's own number — the playing-time blend uses a new,
higher cap (`PT_BLEND_CAP_PITCHER_EXCEEDED = 0.40`, above
`PT_BLEND_CAP_HITTER`'s 0.30, since direct proof beats a hitter's
short-season role signal, but still short of full trust, since a team's
actual workload-management plan is real information too). When false —
he fell short, the Hunter Brown/#51 case — the existing, lower
`PT_BLEND_CAP_PITCHER` (0.15) is unchanged. `_blend_weight()`'s `cap`
parameter now accepts a per-player Series, not only a scalar, which is
what lets the two groups get different caps in the same pass.

**Verified directly**: Cam Schlittler's blended IP rose from 137.1 → 151.9
(`redraft_value` $4.91 → $8.53, closing his health-driven gap to
`upside_ft` = $0 — he's now valued at essentially his own full-time
number). Jacob Misiorowski $12.14 → $16.83, Chase Burns $1.82 → $5.74,
Zack Wheeler $3.41 → $5.53. Cole and Alcantara are unchanged, correctly —
`IP_a < IP_b` for both, so the exception never fires for them. **League-wide
impact, measured against the pre-fix committed board**: modest — one
keep/cut flip (Yoshinobu Yamamoto, $31.68 → $32.75, already a marginal
keeper), total `surplus_multiyear` shift across the rostered pool
**+$5.84** (a gain, the mirror image of #51's −$13.71, since this fix
only *adds* trust in a player's own proven workload, never removes it).
Smaller than #51 because it only touches the narrower group who already
exceeded ZiPS's number, not every short-2026-season pitcher.

**A caveat surfaced while building this, not part of the fix itself**:
Griffin Jax showed a $28 `upside_ft` even before this change, which turned
out to be a full-time-scaling artifact, not a playing-time story at all —
his 2026 `GS`/`G` ratio apparently doesn't clear the `reliever` heuristic's
threshold, so `pt_scale()` was treating him as a starter (150 IP floor)
rather than a reliever (25-save floor). A separate, pre-existing
data-quality question, not touched here.

### upside_ft was conflating two different kinds of upside

Investigating the board's `upside_ft`/`redraft_value_ft` columns (the
"what if he's fully healthy" case, already shipped — see the board's own
"IF FULL-TIME" column) turned up a second, distinct issue: for a reliever
already sitting on 5+ projected saves, "full time" means scaling him to
`KEEPER_SV_FLOOR` (25 saves) — a bet that he's **handed the closer job
outright**, not a bet that he stays healthy at his current role. That's
categorically different from a starter or hitter's health-driven upside,
and the board showed both under one number: Griffin Jax ($28), Grant
Taylor ($23–25 depending on the pitcher fix above), Devin Williams ($28–30),
Josh Hader ($21), Andrés Muñoz/Daniel Palencia all led the `upside_ft`
leaderboard for role reasons, not health ones.

**Fix**: `klab/keeper.py`'s `pt_scale()` (which decides the scaling factor)
now has a sibling, `pt_scale_kind()`, mirroring the exact same branch logic
to label which floor actually applied — `"role"` only for a reliever at
5+ saves scaled to the save floor, `"health"` for everyone else (hitter PA
floor, starter IP floor, two-way bat, or a low/zero-save reliever's own IP
floor). Threaded through `project_all_players()` → `value_players()` as a
new `upside_kind` column, surfaced in the app as a small `role` tag next
to the dollar figure (board cell and player drawer both), rather than a
second column — consistent with this app's stated design philosophy of
tooltips/tags over table clutter (#50). Column header tooltip updated to
explain the split. Permanent `app/verify.mjs` check added: at least one
real "role" case and one real "health" case must exist and be tagged
correctly, so the check can't vacuously pass if the split logic breaks.

### A second, live copy of #52's own bug, caught in the same pass

While re-reading `klab/board.py` for this work, `value_2028()`'s
positional-adjustment override turned out to still have the *exact* bug
#52 found and fixed in `value_players()`: `repl.where(~mask,
np.minimum(repl, r))` compares the position-specific replacement level
against the pooled default too, and since both catcher and shortstop come
out *above* pooled on this league's data, `np.minimum` always kept the
pooled value. `positional=True` was silently a no-op for every player's
**2028** valuation specifically — the 2027 fix in #52 never touched this
function. Caught by reverse-solving the replacement level implied by
Bobby Witt Jr.'s 2028 dollar figure under `positional=True` (came out to
4.81, the pooled number, not his own 6.76 shortstop bar) rather than by
any test failing, since nothing was testing `value_2028()`'s positional
path at all before this. Fixed with the same override/`any_mask` pattern
already used in `value_players()`; Witt's 2028 value correctly dropped
$34.96 → $25.42 once fixed, the same direction and rough magnitude as his
already-correct 2027 change. New regression test added
(`test_positional_adjustment_2028_actually_uses_the_position_specific_bar`)
so a third copy of this bug, if one gets introduced elsewhere, fails loudly
instead of shipping silently a second time.
