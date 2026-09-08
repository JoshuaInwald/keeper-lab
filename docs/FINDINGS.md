# Keeper Lab: Findings (condensed)

Condensed 2026-09-07 from the full research log (out/FINDINGS.md at commit 8353172, 3,000 lines, in git history). Original section numbers kept so code comments citing "FINDINGS #N" resolve here. Retractions and supersessions are stated inline.

**Orientation.** Private 10-team 5x5 roto keeper auction league: $260 per team ($2,600 league-wide), 23 active + reserve slots (230 active league-wide), 6 to 13 keepers per team, three-year contracts, one lifetime extension per contract at +$5 per year for one or two years, $10 pre-break / $20 post-break free-agent price, payout 50% / 25% / 15% of the pot for 1st / 2nd / 3rd and buy-in back for 4th. The engine converts projected production to standings points (per-category denominators fit on standings dispersion), prices a point from the league's own auction history, and subtracts replacement level to get dollar values and keeper surplus. Data: 677 auction purchases 2022-2026 (112 to 163 per season), standings 2022-2026 (2026 ~75% complete at build time), ZiPS Depth Charts 2027 and 2028, a CBS roster/contract export, 2026 season-to-date and ZiPS rest-of-season lines. Worked-example team: Pookie 2.0.

---

### 1. Saves are cheap, conditional on competing in them
Closers identified by prior-season saves (ex ante) beat their price by +2.23 roto points (HC1 t=3.75, n=38, mean price $7.90); hitters +0.09 (n=401), other pitchers -0.58 (n=238). Team saves are bimodal (2025: 0, 57, 61, 70, 70, 72, 76, 82, 91, 98): one punter, nine teams in a 41-save band. The effect depends on dropping punters (SV < 15) from the SV denominator: with all ten teams in, +0.92 (t=1.82, not significant). Robust otherwise (every price band, flexible price controls +2.86 t=4.5, 27 unique players). Two earlier errors fixed: classifying by realized saves; applying the 10-team range constant to an 8-9 team field (headline +2.67 to +2.23). Permutation null in #22.3 confirms. Read as "saves are cheap for a team that competes in saves", not an unconditional inefficiency.

### 2. Cheap players out-earn expensive ones, mostly by arithmetic
All 677 purchases 2022-26, realized production on the redraft dollar scale:

| price paid | n | value delivered | surplus | value per $ |
|---|---|---|---|---|
| $1 | 129 | $5.20 | +$4.20 (t=5.2) | 5.20x |
| $2-3 | 70 | $5.80 | +$3.29 (t=2.5) | 2.31x |
| $4-5 | 61 | $6.92 | +$2.50 | 1.56x |
| $6-10 | 131 | $9.76 | +$1.77 | 1.22x |
| $11-15 | 84 | $13.43 | +$0.27 | 1.02x |
| $16-20 | 76 | $14.69 | -$3.27 | 0.82x |
| $21-30 | 90 | $24.52 | -$0.61 | 0.98x |
| $31+ | 36 | $32.31 | -$3.30 | 0.91x |

Break-even at $11-15. External review gutted the strong reading: non-closer residuals are flat across bands (-0.17, -0.20, -0.18, -0.11); surplus per dollar is the identity `usd_per_rp x slope - 1` (a constant wedge between two calibrations) plus the $0 floor's Jensen lift (+$7.7 at $1 vs +$4.5 at $31+, ~40% of the spread); median surplus is negative in every bucket (60% of $1 buys return $0); the top bucket flips by era (+$5.4 in 2022-23, -$6.7 in 2024-26). No scarcity premium: quadratic term t=-0.01. Price ceiling: no player has ever gone above $45 (season maxima 42, 45, 39, 36, 43) while the best known player is worth $60-80 in hindsight; ex ante the $35 star buys an expected $32.31, so the ceiling is approximately rational. Survives: big tickets do not out-earn their price; cheap surplus is a fat right tail (variance, not mispricing).

### 3. The auction exchange rate is decaying
$ per roto point by season: 2022 4.12, 2023 4.79, 2024 6.41, 2025 8.17, 2026 10.20 (#17 reports 4.16/4.78/6.36/8.09/9.98 from a later run). Free production at $0: 1.71, 2.43, 3.42, 3.59, 3.52 roto points. A dollar bought 2.5x as much in 2022 as in 2026. The keeper-count explanation given here ("25 to 100 eligible keepers") was retracted in #16/#19; the trend stands (#7, #19, #22.2).

### 4. Half the 5x5 categories barely repeat
Year-over-year reliability r (hitters 250+ PA, n=693; pitchers 40+ IP, n=785): SB/PA 0.739, K/IP 0.701, HR/PA 0.607, AVG 0.436, R/PA 0.425, RBI/PA 0.380, WHIP 0.237, ERA 0.176, W/IP 0.151 (R^2 0.023). Wins carry no signal; only strikeouts persist for pitchers. Drives `RELIABILITY` in `klab/project.py` (refit in #28).

### 5. Denominators: units per standings point (2027)
R 39.4, HR 15.4, RBI 38.7, SB 20.4, AVG .0023, W 3.79, SV 6.57, K 59.1, ERA .0431, WHIP .0108. Cross-rates: 1 HR = 1.3 SB = 2.6 R = 2.5 RBI; 6.6 SV = 59 K = 3.8 W. SV was 5.53 before the #1 field-size correction, then 7.16 (pre-#26), 6.00 (#26), 6.57 (#31, current). Bootstrap intervals in #22.1.

### 6. Sensitivity: which modelling choices flip decisions
`scripts/sensitivity.py` counts keep/cut flips out of 275 rostered players per alternative. Current run (post-#51/#52/#53):

| variant | flips | Spearman | max abs delta $ |
|---|---|---|---|
| flat 50/50 blend (undo #51 decoupling) | 20 (7.3%) | 0.907 | $23.15 |
| denominators 2022-25 instead of 2024-26 | 10 (3.6%) | 0.978 | $30.42 |
| SV punters included (SV denom 6.57 to 11.06) | 5 (1.8%) | 0.984 | $13.73 |
| auction window 2022-26; no PT floor; no discount; discount 0.6 | 0 each | 0.999-1.000 | up to $10.71 |

29 of 275 (11%) flip on at least one choice. Superseded pre-#51/#52 run: denominators and flat blend 17 flips each, punters 3, no-discount 3, heavy discount 1, 34 of 275 (12%) total. The punter rule moves closer prices far more than decisions.

### 7. The single-season exchange rate is not stably estimated
Split-half fits (odd vs even purchases): 2022 $4.32/$3.96 (CI 3.41-5.33), 2023 $4.01/$6.16 (3.89-6.20), 2024 $5.03/$8.21 (4.96-8.86), 2025 $6.80/$12.02 (5.60-14.55), 2026 $6.55/$20.38 (6.67-19.79). Pooled 2022-26 is tight: $5.83 (CI 5.13-6.74). The 2026 halves disagree threefold. The then-headline $7.56/point carries roughly +/-40%: rankings solid, levels approximate.

### 8. No MLB-team bias in bidding
Purchase residuals regressed on MLB team: Mets +0.28 roto points (t=0.57, p=0.567). Joint F-test on 30 dummies: R^2 0.065, F=1.37, p=0.094. Extremes (TEX -1.29 t=-2.71, CIN -1.28, TBR +1.92 t=2.93, NYY +1.65) are what 30 simultaneous tests deliver.

### 9. Good teams are efficient, not big spenders
Correlation with 2026 standings points: roto points per dollar committed +0.648; share of production from keepers +0.354; from free agents -0.109; from the auction -0.540. Last place (NPB No Stars) drew 36.3% of production from the auction; the leader (Pookie 2.0) 20.6% from the auction and 45.3% from keepers.

### 10. Keep-vs-cash: cutting a player refunds his salary, not his value
Salary is spent into an auction running +48.7% inflation (that build), so a budget dollar buys $0.67 of production. Rule: `keep if value > keeper_cost / inflation`. 30 of 275 flipped cut to keep, all expensive stars (Alonso $27, value $22.8, naive -$4.2, vs-cash +$4.6; Acuna $26 +$2.5; Harper $21 +$1.5; Julio Rodriguez $43 -$1.7). Caveats: self-referential (more keeping raises inflation; fixed point unsolved); the "only 25-29 kept in 2022-25" tension cited here was an error (#16). Inflation later reads +31% at "blend", +41% at "actuals" (#42).

### 11. The projection source is a top-tier knob
`PROJECTION_BASIS`: blend (default) 79 keepers, replacement 4.14, $6.66/pt; projection-only (ZiPS 2027) 67 keepers, 4.42, $7.42, 34 flips (12.4%); 2026 actuals + ROS 74 keepers, 4.13, $5.69, 15 flips (5.5%). 47 of 275 (17%) have a basis-dependent keep/cut call; Crochet swings +/-$23, Misiorowski +/-$18, Judge +/-$15. UI selector in #42. Other systems publish no 2028 line.

### 12. Season windows by purpose
Denominators and baselines: 2024-25 (regime changed in 2024), later 2024-26 with 2026 excluded per category (#26). $/roto point: 2024-26, then `EXCHANGE_BASIS` (#17/#19). #2 and #8: all 2022-26 for n. Reliability: consecutive-year pairs.

### 13. Contracts are options, not obligations (bug fixed)
Multi-year surplus summed every contract year with sign, charging teams for years they would decline. Okamoto ($11, two years, $0 2028 projection) read -$12.8; later years now clip at zero and he reads -$3.45. Largest error on ageing veterans.

### 14. Waiver value is a three-way switch; "high" fails a smell test
`WAIVER_VALUE`: low (230th projection, one per active slot) replacement 4.14, $6.66/pt, 85 keepers; medium (300th) 3.79, $5.45, 82 keepers, 11 flips; high (median of actual 2026 FA pickups, 5.04) $16.04/pt, 91 keepers, 32 flips. $16.04 vs $7.56 from the auction regression is a factor-of-two disagreement: the 5.04 anchor is survivorship-biased. Default stays low. Revisited in #27.

### 15. Positional adjustment: built, off, unusable at the time
`POSITIONAL_ADJUSTMENT=False`. Positions came only from auction files: 51% coverage, 6 identified catchers where there must be 10; enabling raised a RuntimeError. Published tests (FanGraphs, Razzball) found positional variants add near-zero. Superseded for C and SS by #52; full spectrum still off.

### 16. CORRECTION: the keeper-count "tension" was the author's error
`keepers_2026.csv` holds 100 actual keepers (6-12 per team, inside the 6-13 rule); earlier text mislabelled it as an eligibility list. A 2027 recommendation of 80-85 keepers is conservative. The 2022-25 files showing 25-29 keepers cannot be real keeper sets under a 6-keeper minimum; 2026 is the only usable baseline. #19 shows those files are incomplete.

### 17. Auctions happened in different worlds (mechanism later retracted)
| season | keepers in file | auction picks | spent | $/pt |
|---|---|---|---|---|
| 2022 | 25 | 137 | $1,604 | $4.16 |
| 2023 | 28 | 136 | $1,607 | $4.78 |
| 2024 | 29 | 163 | $1,813 | $6.36 |
| 2025 | 29 | 129 | $1,377 | $8.09 |
| 2026 | 100 | 112 | $1,236 | $9.98 |

Claimed corr(keepers withheld, $/pt) = +0.796 and fit `$/pt = 4.19 + 0.0589 x keepers` (R^2 0.633; $10.08 at 100 keepers, $10.67 at 110, $11.26 at 120). Introduced `EXCHANGE_BASIS = "keeper_adjusted"` (alternatives "pooled" = old $7.56, "recent" = 2026 alone). **Causal claim RETRACTED in #19**; the $10.08 level survives as trend extrapolation only.

### 18. Z-scores: independent check, and depth beats stars
2026 value across 274 rostered players: mean 5.53 roto points, sd 2.75, skew 0.12 (7 at z >= 2, 42 at z >= 1, 143 below average). Spearman(standings, summed player z) = +0.855 vs +0.842 from the engine's own standings reproduction. Predictors of 2026 standings: summed z +0.855; count z >= 1 +0.840; count below average -0.755; count z >= 2 +0.141 (range 0-2 per team; do not over-read). Hindsight worth vs price: z 2+ (n=7) worth $42.21, paid $21.00; below average (n=143) worth $1.84, paid $11.95: the market cannot tell them apart in advance. Refined in #29.

### 19. RETRACTION: the keeper-count mechanism is not identified
Two identities (keepers + picks fill ~230 slots; keeper salary + auction spend = $2,600) fail for 2022-25: 38-72 slots unexplained, implied $27-42 per keeper. The 2022-25 keeper files are incomplete; real counts back out to 67-101 per season, so the "25 to 100" rise never happened. Correlates of $/pt: file counts +0.796, slot-implied +0.569, budget-implied +0.752, bare season trend +0.987. Keeper count and time are collinear at n=5. Survives: the rate rose monotonically to $9.98 in 2026 and ~$10 for 2027 is sound; `keeper_adjusted` still yields $10.08, the right number for the wrong reason.

### 20. Unrostered players worth having
Best 2027 free agents: Schwellenbach 5.82 pts / $12.20, Justin Crawford 5.50 / $10.06, Esteury Ruiz 5.43 / $9.64, Marsee 5.36 / $9.16, Kwan 5.26 / $8.49. Drafted in 2026 and dropped (re-add resumes the draft contract, #23.6): Crawford $1 (+$9), McLain $1 (+$6.4), Jensen $1 (+$6.0), Tovar $1, Bohm $2, Marsee $8. Best win-now adds: relievers with saves (Diaz 2.87, May 2.64, Fairbanks 2.34), consistent with #1.

### 21. External validation against CBS roto rank
Spearman(CBS 2026 hitter rank, model roto points) = 0.893 across 93 matched hitters (0.863 before deduplicating a Luis Garcia name collision; name joins outside `io.NameResolver` are latent bugs). Disagreement is entirely AVG vs power (CBS-favoured 20: .280 AVG, 12.7 HR; model-favoured 20: .250, 19.0 HR; SB identical). Resolved in #22.4/#23.5: CBS rank includes OBP; no model change.

### 22. Experiments: real error bars
22.1 Bootstrap of the denominator estimator (2,000 resamples, n=20 team-seasons): R 39.4 (14.0-59.6), HR 15.4 (7.8-20.3), RBI 38.7 (17.6-55.7), SB 20.4 (14.4-24.3), AVG .0023 (.0013-.0031), W 3.79 (2.23-4.88), SV 6.57 (3.88-8.68), K 59.1 (33.5-79.5), ERA .0431 (.0282-.0540), WHIP .0108 (.0074-.0135). Mean interval +/-38% (R +/-58%, RBI +/-49%, SB +/-24%, WHIP +/-28%), not the +/-16% analytic figure. **Corrected to +/-34% in #30.**
22.2 Leave-one-season-out: pooled $/pt sits at 5.4-6.5 while each held-out season's own rate ranges 4.2-10.0; residuals small and not monotone (r=+0.29). Pooling ranks correctly and prices on the wrong level, the case for `EXCHANGE_BASIS`.
22.3 Permutation test (5,000 draws, closer label shuffled within season and price band): observed +2.23 vs null mean +0.22, sd 0.50, 95% range [-0.76, +1.20]; p < 0.0001. Best-supported finding in the project, still conditional on the punter exclusion.
22.4 Rescaling the AVG denominator (0.5x to 2x) moves Spearman vs CBS only 0.755 to 0.912, flat from 1.0 to 2.0; AVG is not mis-set.

### 23. The constitution, finally read: three rule corrections
23.1 Extensions are +$5 per year for one or two years, chosen once; the model priced +1 year only (fixed, refined in #24). 23.2 One extension per contract ever: `already_extended()` detects a salary exactly +$5/+$10 above last auction price and not at a FA price ($10/$20); found Yamamoto (1, $32 vs $27), Munoz (2, $13 vs $8), Harper (F, $16 vs $11, unkeepable). 23.3 Everything else checks out; one unmodelled rule (max one minor leaguer per draft). 23.4 Skubal at $38 vs $23 auction (+$15, not a legal step) unresolved; treated as no further extension. 23.5 CBS rank includes OBP (closes #21). 23.6 A re-added player keeps his draft-year contract (Crawford at $1 is real).

### 24. Final-year extension priced at one year when the rule allows two
For `F` players the code zeroed the option. Fix: 1 year `v2027 - (salary+5)`; 2 years `v2027 - (salary+10) + 0.85 x max(0, v2028 - (salary+10))`; second year worth buying iff `0.85 x (v2028 - salary - 10) > 5`. Three of 35 `F` players cleared: Ohtani $50.9 to $76.1, Greene $11.8 to $13.2, De La Cruz $10.9 to $11.8; `extension_years` in {0,1,2} added (52 one, 9 two, 214 none). **Superseded by #39**: `F` players are not extendable; Ohtani was already zeroed by `NON_EXTENDABLE_NAMES`, Greene and De La Cruz flipped to cut. 24.1: a `PA_x`/`PA_y` merge collision blanked the player card; ROS columns now prefixed.

### 25. Two final-year contracts do not reconcile: unresolved
deGrom (drafted 2022 at $21) and Turang (2023 at $9) carry `F` for 2026 when a 3-year clock says 2024 and 2025. No re-draft event exists in any draft file; salaries unchanged, so no extension was paid. Likely a data-entry artifact or an unrecorded commissioner ruling. deGrom is a cut under all 8 sensitivity variants regardless; Turang's surplus would move by exactly $5. Carried as-is pending the transaction log.

### 26. Partial-2026 exclusion: the rate-vs-counting split was a proxy
Single-season CV (2024 / 2025 / 2026 partial): only SV (0.254 / 0.177 / 0.328), ERA (0.037 / 0.035 / 0.073) and WHIP (0.028 / 0.028 / 0.042) inflate in the partial season; AVG does not (0.036 / 0.014 / 0.026). Mechanism: unevenly accumulating volume (closer churn, incomplete innings). Replaced `DENOM_EXCLUDE_PARTIAL_FOR_RATES` with `PARTIAL_EXCLUDE_CATS = {"ERA","WHIP","SV"}`. SV denominator 7.16 to 6.00 (-16.2%, ~1.2 SE), AVG .002298 to .002252, replacement 4.761 to 4.778, $/pt keeper $9.11 to $9.26, redraft $6.32 to $6.24; 5 flips (Munoz, Baker, Cam Smith, W. Contreras in; Yamamoto out); closers gain $5.50-6.80 surplus. SV corrected again in #31.

### 27. Replacement level revisited
Three routes after #26: auction-regression intercept 4.01 (lower bound), 230th-best projection 4.78 (`WAIVER_VALUE="low"`, Last Player Picked method), median of actual 2026 FA adds 5.04 (survivorship upper bound; recomputed 5.037, matches `config.WAIVER_HIGH_RP`). Consistency check: only 24 of 1,714 unrostered players (1.4%) project above 4.78 and the pool decays smoothly (rank 10 at 5.09, rank 20 at 4.84, rank 30 at 4.55), so 4.78 sits at the elbow. Transaction-log test still blocked. Keep "low".

### 28. Reliability refit found a real bug: BB and H were set to WHIP's value
Refit reproduced 8 of 10 values; BB and H were both hard-coded 0.237 (WHIP's own r) and refit to BB 0.463, H 0.359. The `WHIP` key is inert; BB and H are live. Fixed in `klab/project.py`: replacement and keeper $/pt unchanged, redraft $6.242 to $6.214, 1 flip (Yamamoto), mean abs surplus change $0.16; Misiorowski +$3.51, Schlittler +$2.57, Peralta -$1.92, Crochet -$1.55. A four-pair refit including partial 2026 moved nothing by more than 0.02; not adopted.

### 29. Depth-vs-stars redone with share of production
Refreshed counts after #26/#28: z >= 1 count +0.906, z >= 2 +0.141, below average -0.772. Share-of-production version: z >= 1 +0.794, z >= 2 -0.019, below average -0.879; total team roto production alone +0.939, better than any threshold metric. "Depth over stars" survives but is secondary to total production. n=10; suggestive only.

### 30. The +/-38% band was computed around the wrong point estimates
`experiments.py::exp1_bootstrap_denominators` carried its own season loop without the partial-2026 exclusion (ERA came out 0.0614 vs 0.0431 shipped). Fixed to use `PARTIAL_EXCLUDE_CATS`/`PARTIAL_SEASONS`; every denominator now matches `model_params.json` and the mean interval is **+/-34%**, superseding the +/-38% in #22 and earlier docs.

### 31. A second live copy of the season-set bug: `teams_per_category`
The SV field-size constant `n` (choosing `C_N[8]` = 2.847 vs `C_N[9]` = 2.970) averaged over all `DENOM_SEASONS` without the #26 exclusion: 8.667 (rounds to 9) with 2026, 8.5 (rounds to 8) without. Fixed; SV denominator 6.00 to 6.57 (net vs pre-session 7.16: -8.2%), $/pt keeper $9.26 to $9.17, redraft $6.21 to $6.29, one more flip (Bryan Baker, surplus $13.37 to $9.74). All later headline figures reflect this fix.

### 32. Review of untouched modules
32.1 `evaluate_trade` defaulted `usd_per_point` to a hardcoded 7.6 and no caller passed the live $9.17; the app's JS used the redraft scale ($6.29) instead of the auction scale. Both fixed; verdicts move ~$0.5-1 per side; `app/verify.mjs` passes 25/25. 32.2 FAs with no draft history defaulted to contract "1" instead of "2"; fixed, zero dollar impact. 32.3 `already_extended()` cannot tell a $5 + $5 extension from a $10 FA re-add by salary alone; dormant, needs transaction dates.

### 33. Extension eligibility wrongly applied to codes "2" and "3"
Only code "1" ("about to enter the final year") may extend. Nine players with 2-3 years of control carried a phantom option worth $25.60 combined (Torkelson +$7.20, Griffin +$5.43, Greene +$3.96, Simpson +$3.77, Woo +$2.29, four others). Fixed; zero flips. See #39.

### 34. ROS value over replacement: a player-intrinsic win-now metric
`klab.trade.ros_value_over_replacement()` reuses the 2027 denominators and team baseline, scales the AVG/ERA/WHIP dilution baseline by each player's `remaining_frac` (ROS PA/600 or IP/150), and subtracts `replacement_rp` (4.78) prorated the same way. Skubal +4.99, Sanchez +1.92, De La Cruz +1.59, Christian Scott -2.23. Team-specific category marginal value: roadmap.

### 35. Comp-based next-auction price estimator (separate tool)
`klab/auction_estimator.py`: 15 nearest historical comps (role, position group, per-category profile) from all 677 purchases; their season-specific premium over a production-only regression is applied to the target's `redraft_value`. Freeman: fair value $15.42, comp range $14.15-$38.46, median $23.18; his own 2025 purchase ($28 vs $8.55 predicted, +192%), Guerrero (+265%) and Devers (+211%) show a name-brand corner-bat premium the regression cannot see. Skubal: $3.60-$79.20, because elite SP prices here span $1 (injury) to $33 (name) at similar production. No age data in `data/`. Noted, not applied: plain OLS on dollars gives a negative median residual every season (typical player 8-22% "overpriced"); log-salary flips it positive; this tool recenters residuals per season. `fit_exchange_rate` not checked for the same issue. 111 of 668 purchases (17%) lack position.

### 36. A retained-but-unused extension right is worth $0 in the model
`multiyear_surplus` prices extensions only for `is_final` rows; a player with 1-3 years of live control gets nothing for the extension he will someday hold (ZiPS reaches only 2028). Lowe/Okamoto/Luzardo priced as if at `F` today: $0.00 each. Trade 1's $25 gap is an upper bound; its `F`-side numbers were wrong per #39.

### 37. Uncertainty bands were already in the app
`klab/uncertainty.py` bootstrap (+/-34% per category) was already in the app ("likely range", `p_surplus_positive`); `docs/SESSION-LOG.md` wrongly said otherwise. Bands added to `run_all.py` CSVs and `eval_trade.py`. Skubal's $17.97 surplus is positive in only 73% of 1,000 draws (10th-90th: -$7.4 to +$37.7); Walker +$0.21 positive in 61%; Scott and Freeman 0%.

### 38. Roster update
Fresh CBS export matched 277 players by `name_key`; 268 untouched. Two real trades detected (Spehr's Army / All-Stars: Lowe, Okamoto, Luzardo for Marte, De La Cruz, Sanchez; Orange and Black Attack / NPB No Stars: Julio Rodriguez for DeLauter). Bogaerts is a re-add on his $2/`F` contract (#23.6); Colt Emerson released.

### 39. `F` players were never extendable now: a bigger correction than #33
The extension window closes before the walk year's draft; every `F` row in a mid-2026 snapshot already missed it. `keepable` changed from `~(already_extended & is_final)` to `~is_final`. 37 `F` players; 35 wrongly keepable; 10 flip `keep_2027` to False; $130.48 of surplus removed (Spehr's Army $58.42: De La Cruz -$16.18, Wood -$15.87, Sanchez -$12.67, Duran -$8.53, Naylor, Busch; Greene -$15.00, Chourio -$7.31, Merrill -$7.01, Turang -$5.82). Supersedes #24 and #36's trade numbers. Test `test_f_contract_players_are_never_keepable` added.

### 40. Trade finder (build)
`klab/trade_finder.py` precomputes 1-for-1 suggestions for all 45 team pairs (~135s) under three scenarios (win-now-for-future when standings differ by >= 8 points, challenge trade, mutual value swap); "no trade found" is a real result (2 of 45 pairs). Bugs fixed: worthless-return scoring (returned player must have positive standalone surplus), shortlist too narrow (now union of top-10 talent and top-10 surplus), apostrophes breaking inline `onclick`, stale "+/-38%" strings.

### 41. Trade finder was non-deterministic
28 of 45 pairs changed between identical reruns: `_shortlist()` returned `list(set)` and pickers kept the first candidate on strict `>`, so hash-seed order decided ties. Fixed with `sorted()` and a `(primary, secondary = sum of both sides' deltas)` score; Woo-Wetherholt (5.5/1.5) now beats Woo-Judge (3.5/1.5). Byte-identical across reruns; tests added.

### 42. Projection-basis selector (build)
Three full payloads (board, FA, teams, constants) built in fresh subprocesses via `KLAB_PROJECTION_BASIS` (`klab.io.cached()` memoises on arguments only). Inflation +31% at blend (keeper salary $1,998 vs $1,525 of remaining talent), +41% at actuals ($1,944 vs $1,374). 272 of 275 players' roto points change on switch; round trip exact. One stale-settings display bug fixed.

### 43. Auction estimator in the UI (build)
Estimates precomputed per basis for ~673 players; `allow_nan=False` caught NaN `pos` strings in comps. Payload 1.17 MB to 3.74 MB.

### 44. UI audit
`keeper_status()` still returned "extension +$5" for `F` players after #39; fixed, with a test forbidding `$` in `F` status strings. Drawer gained IL/LOCKED tags. Two `fullPage` screenshot artifacts were false alarms. Free agents have no uncertainty bands (`bootstrap_bands()` needs real contracts); `FA_NOTE` says so.

### 45. Blended 2026 rest-of-season signal
`prorated_to_date_lines()` extends season-to-date rates over remaining team games (162 minus the 95th percentile of games played among PA > 300 hitters; 119 played, 43 left on 2026-08-13). `ros_lines_for_basis()` dispatches "ros" (default), "prorated", "blend" (50/50). No pre-season 2026 projection exists in `data/`. Bug fixed: dividing by a starter's own `G` projected Skubal for 256 more innings; shared team games gives 38.7 vs ZiPS's 46.0.

### 46. Rest-of-2026 basis toggle (build)
Standings and Trade tabs only; never touches a dollar value. Computed once (+~290 KB). Bug fixed: `setBasis()` now reapplies `S.rosBasis` so a basis switch does not reset the ROS choice.

### 47. ROS value column on the board (build)
`ros_value_over_replacement` depends on both toggles, so it is computed as a 3x3 grid inside the per-basis subprocesses (+~123 KB); sorting needed a special case because the column is looked up, not stored.

### 48. Historical standings 2022-2025 (build)
Season picker on the Standings tab; rows grouped by `franchise_id` under current names via `data/franchise_map.csv` (five renames since 2021).

### 49. 2027 standings from keeper sets alone
`_keeper_standings_2027()` sums kept players' 2027 lines and fills open slots with a replacement line (keeper-core strength, not a forecast). Bug fixed: the nearest-to-replacement player was a closer, injecting ~25 saves per empty slot; now a 15-player band average per role, SV 25.3 to 5.3.

### 50. Intuition tab (build)
Client-side talent (rate) and health (playing time) shades via a per-column multiplier map in `rosterAgg()`; exact for 2026 standings, linear scaling of `redraft_value` for 2027 (labelled approximate). Sandboxed. Small shades often show 0.0 standings change because roto points are rank-based (Skubal at +30% and full health moves NPB No Stars 26 to 28).

### 51. Playing time gets its own blend weight
`_blend_weight()` used one weight for both rate and playing time, so Hunter Brown (12 starts, 63.2 IP) blended to 135.25 IP against ZiPS's 163.3. New caps `PT_BLEND_CAP_HITTER = 0.30`, `PT_BLEND_CAP_PITCHER = 0.15` (judgment calls); rate blend and `RELIABILITY` untouched. Brown 154.9 IP, $10.68 to $16.92. 10 flips (Cruz, Langford in; Trout, Yandy Diaz, Cam Smith out), total surplus -$13.71; symmetric (Yamamoto, who exceeded ZiPS, loses). Highest-stakes knob in #6.

### 52. Positional adjustment for C and SS: both are deep, not scarce
`two_position_replacement()` (off by default, UI toggle) sets C/SS replacement at the 10th-best eligible player from FanGraphs eligibility exports (106 C, 115 SS). Result: pooled 4.80, catcher 5.12, shortstop 6.76. Dingler $2.46 to $0.24; Witt $36.10 to $26.52. The points-above-replacement pool shrinks, so $/pt rises $6.58 to $7.56 and non-C/SS players gain (Skubal $52.12 to $59.76). 15 flips: 6 C/SS out (Lopez, Pena, Perdomo, Wetherholt, Swanson, Baldwin), 9 in. Two bugs: `np.minimum(pooled, positional)` was a silent no-op (both positions above pooled); the budget identity broke ($2,834.58 vs $2,600) because the pool sum was unclipped while `dollars()` clips at $0; clipped sum gives $2,572.86 (~1% off, accepted). Same no-op in `value_2028()` fixed in #53.

### 53. Direction-aware pitcher playing-time trust; upside_ft split
Two mechanisms behind low SP values: ZiPS itself is skeptical of Cole (129.2 actual IP vs 102.0 ZiPS) and Alcantara (213.2 vs 149.0) and their rates are below replacement (Cole ERA 4.08), so $0 is a methodology choice; young arms who already exceeded ZiPS (Schlittler 187 vs 128, Misiorowski 175 vs 116, Burns 164 vs 106) were capped by generic caution. When `IP_a > IP_b` the PT cap is `PT_BLEND_CAP_PITCHER_EXCEEDED = 0.40`, else 0.15. Schlittler $4.91 to $8.53, Misiorowski $12.14 to $16.83, Burns $1.82 to $5.74, Wheeler $3.41 to $5.53; 1 flip (Yamamoto), total surplus +$5.84. `pt_scale_kind()` labels `upside_ft` "role" (reliever scaled to the 25-save floor: Jax $28, Williams $28-30, Hader $21) vs "health". `value_2028()` still had #52's `np.minimum` no-op; fixed (Witt 2028 $34.96 to $25.42).

### 54. Check against FanGraphs' rest-of-season auction calculator
The export is rest-of-2026 (PA max 174, IP max 51, hitter dollars sum -$10,989), so compared with `ros_value`. Naive Spearman 0.491 is a floor artifact (FanGraphs goes to -$40; this model floors near $0). Among ADP < 400 players: hitters 0.678, pitchers 0.835. Systematic compression: mean `ros_value - Dollars` by FanGraphs quartile is +$18.6 / -$1.2 / -$9.6 / -$21.0 for hitters and +$0.6 / -$4.4 / -$11.4 / -$19.6 for pitchers. Hypothesis (unconfirmed; league settings not in the export): replacement level calibrated to a 10-team, 230-slot league flattens the curve vs a generic pool. No number changed.

### 55. Monte Carlo finish-odds simulator
**Correction, same day as shipping: the first version assumed a flat top-2 payout. The real structure is 50% / 25% / 15% for 1st / 2nd / 3rd and buy-in back for 4th (`PAYOUT_SPOTS`, `PAYOUT_SHARE`); everything now keys off `PAYOUT_SPOTS`.** `simulate_finish_odds()` jitters player outcomes with one shared hot/cold draw per player scaled by `1 - reliability` per category (saves borrow wins' 0.15); playing time not jittered. Rest-of-2026: Pookie 2.0 and Spehr's Army 100% in the money, McBlocks 99.9%, Orange and Black Attack 43%, All-Stars 32%, Fighting Phils 22%, Lisbon 3% (the last four ~0% under the wrong top-2 version). A dollar-neutral swap (Julio Rodriguez $29.92 for Soto $29.93) moves Orange and Black Attack 43% to 19% and the Phils 22% to 37%: category fit, which no dollar figure captures. JS and Python agree within 0.4-1.7 points (tolerance 8). `simulate_keeper_finish_odds()` (2027, per basis): Producers and Polar Bears 74% on keeper talent alone, Pookie 2.0 21%; Orange and Black Attack 0% with the same 7 keepers as Producers. Live 2027 trade odds not built.

### 56. Market price, fitted directly: it beats both baselines, and it is not shippable yet
ROADMAP item 1 Steps 0, 1, 1b, 2. Steps 3-5 not started; `market_price` is a column of NaN on purpose.

**56.1 The quantities are now separate (Step 0).** `production_value` is an exact alias of `redraft_value` (worth to a roster, budget scale); `market_price` is the auction cost and is its own column. The board's "Worth '27" label is gone. Nothing numeric moved: every shared column of `out/keeper_board_2027.csv` is byte-identical, 64 tests pass, `node app/verify.mjs` 15/15.

**56.2 Age exists now, and it is the largest single coefficient (Step 1).** `scripts/fetch_chadwick.py` pulls the Chadwick register to `data/chadwick_register.csv`: 21,200 players with a FanGraphs id, 98% of the 450 in the auction history. `scripts/price_features.py` writes `out/price_features.csv`, 677 purchases with prior-two-season production, playing time, per-category prior lines, tenure, last salary, role, position group, rookie flag and age. Holding production constant, the market discounts **8.0% per year of age** (t = -5.84). METHODS section 3 #18 declined an aging curve for lack of age data; that reason no longer applies to price, though it still applies to production, where ZiPS carries age already.

**56.3 The "25% of purchases have no prior MLB line" figure is 80% censoring.** The FanGraphs exports start in 2022, so 2022's 137 purchases have no prior-season line at all. The ROADMAP diagnosis counted them as rookies: 137 censored rows plus 30 genuine ones is the 167 (24.7%) it reported. On the observable window (2023-2026) the rookie rate is **5.6%, n=30**. The model set is 2023-2026; 2022 is excluded from the fit, not held out.

**56.4 `keepers_2022..2025.csv` are not keeper submissions (Step 1b).** The open question from HANDOFF is settled from the data, without the commissioner. `keepers_2025.csv` shares **zero** players with the 2024 auction class, the only contracts that could have been kept for 2025. `keepers_2026.csv` (100 rows) is sound: it agrees with the roster contract codes on 31 of 35 players in the 2025 class, with no contradictions. Keeper decisions are therefore reconstructed, not read: a player under a live contract who reappears in season S's auction was thrown back (the draft files are complete), and for 2026 a player in the keeper file or on the roster under a pre-2026 contract code was kept. 133 clean 2026 decisions, 73 kept and 60 thrown back, no contradictions. Reconstructed 2023-2025 decisions (n=202) are reported separately and carry a selection bias 2026 does not: before 2026, "kept" is only detectable when the player was later thrown back, so a player kept and held reads as unlabeled.

**56.5 Owners' revealed indifference price runs far below both dollar scales at the top.** `P(kept | prior roto points, salary, years of control, role)`, 2026, n=133, pseudo R^2 0.136: production +0.244 (z 3.51), salary -0.061 (z -3.04), years of control -0.819 (z -2.07). Salary at which P(kept) = 0.5, by prior-production decile, against what the engine says the same production is worth:

| decile | n | prior roto pts | kept | revealed P50 price | `production_value` | `keep_value` |
|---|---|---|---|---|---|---|
| 2 | 13 | 3.98 | 0.23 | $5.97 | $0.00 | $0.01 |
| 4 | 13 | 6.09 | 0.69 | $11.35 | $9.39 | $19.36 |
| 6 | 13 | 7.81 | 0.69 | $21.34 | $20.68 | $35.14 |
| 8 | 13 | 9.26 | 0.69 | $25.60 | $30.19 | $48.44 |
| 10 | 14 | 13.03 | 0.86 | $38.54 | $54.92 | $83.02 |

The three agree around 7-8 roto points and diverge from there. At the top decile the owners' own revealed price is **$38.54** against `production_value` $54.92 and `keep_value` $83.02, the number that decides keep-vs-cut. This is the ROADMAP's "top end too high" diagnosis confirmed from a direction that never touches an auction bid. At the bottom the sign reverses: owners pay $6 where the engine says $0.

**56.6 The price model beats both baselines (Step 2).** `scripts/price_model.py`: OLS on log(salary), season fixed effects, role interaction on the production terms, Duan smearing back to dollars, P20/P80 quantile fits, capped at the realised max for the role. Production transform chosen by leave-one-season-out inside 2023-2025 (linear 6.56 MAE, sqrt 6.86, log1p 7.10); 2026 was not consulted. Fit 2023-2025 (n=428), predict 2026 (n=112):

| model | MAE | RMSE | bias | Spearman |
|---|---|---|---|---|
| price model | **5.76** | 7.29 | -0.46 | 0.482 |
| baseline: prior salary + trend | 6.84 | 8.19 | +2.25 | 0.471 |
| baseline: comp estimator, training-only pool | 7.20 | 9.02 | -3.29 | 0.277 |

In-sample R^2 is 0.388. Calibration by predicted-price decile is within $3.21 for deciles 3 through 9 and misses at both ends: decile 2 +$4.77, decile 10 -$5.90 (predicts $30.90, market pays $25.00). The comp estimator is run as a re-implementation over training seasons only; calling the shipped module would have leaked 2026 into its own comp pool.

**56.7 Two design errors, both caught by the held-out season.** Neither is a modelling subtlety; both are worth keeping in view because each looked right and cost the model its first acceptance test.
- *Season effects.* A held-out future season has no dummy. Defaulting it to the omitted base level handed 2026 the 2023 price level and inflated every prediction by exp(0.90): MAE 8.76 against a 6.84 baseline, and $86.49 for a hitter in a league whose all-time high is $45. An unseen season now carries the most recent training season's effect.
- *Age missingness as a feature.* Mean-fill plus a missingness flag is the obvious design. The register misses a player only when his FanGraphs id is newer than the register: in 2023-2025 that was five unmatched $1 placeholders, in 2026 it is eight prospects and NPB imports sold for $1 to $20. The flag learned "missing age means $1" and applied it to the most expensive rookie class in the sample, predicting $1.68 against a realised $9.75. Removing the flag and imputing age from same-status players cut that segment's MAE from $8.20 to $5.96 and the overall from 5.91 to 5.76. This change is post-hoc, argued from the mechanism, and it is very slightly *worse* on leave-one-season-out inside the training seasons (6.59 vs 6.56), which is exactly what a training-period artifact looks like.

**56.8 What still fails, and why `market_price` stays empty.** The acceptance test is not passed.
- *P20-P80 coverage 38.4% against a nominal 60%.* In-sample coverage is 57.5%, so the quantile fits are fine where they were estimated and the bands do not transfer. The misses are asymmetric, 25.0% below P20 and 36.6% above P80: out of sample the upper tail is systematically underpriced, not just wide.
- *The top-end check passes only because of the cap.* Uncapped, the model predicts $55.38 for a hitter against a $45 ceiling; two hitters are capped. A price model that needs a hard ceiling is extrapolating at the top, which is the same failure `redraft_value` has, one order of magnitude smaller.
- *Rookies are still underpriced*, $5.29 predicted against $9.75 realised even after the age fix, on n=8.
Half the variance is unexplained and the ROADMAP said to expect that. But a column that fails its own coverage test does not belong on the board, and the level has not been calibrated to the 2027 budget (Step 3). `market_price` is NaN until it is.

### 57. Steps 3, 4 and 5: the level calibrates, the decision rewire does not, and the market does not pay for upside
ROADMAP item 1 finished. Two of the three remaining steps produced negative results, which is the finding.

**57.1 Step 5 rejected: no measurable premium for upside.** ZiPS P10-P90 columns exist only in the 2027 and 2028 exports, so a coefficient on ZiPS spread cannot be estimated from 2023-2026 purchases; no historical archive is in `data/`. Substituted a proxy computable on both sides: for each purchase, the spread (P90 minus P50) of realised roto points among the 25 nearest EARLIER purchases in ex-ante space. Both terms are insignificant (level -0.026, t -0.55; pitcher interaction +0.049, t +0.76), R^2 moves 0.3746 to 0.3755, and it loses on leave-one-season-out (MAE 6.59 to 6.81) and on held-out 2026 including the rookie segment (5.96 to 6.45). The ROADMAP's hypothesis was "yes for hitters, no for pitchers"; the point estimates run the other way and neither is distinguishable from zero. Not shipped.

**57.2 Step 2's GBM fallback also rejected.** A monotone gradient-boosted model cannot predict outside the observed price range, which is precisely the top-end problem the GLM needs a hard cap for. It solves that (max $37.04 hitter, $19.03 pitcher, both inside the ceiling) by shrinking the whole top end: bias -3.94 and LOSO MAE 7.04 monotone, 6.91 unconstrained, against 6.59 for the GLM. The cap stays a patch on a better model rather than being designed away by a worse one.

**57.3 Band coverage fixed by conformal calibration.** #56.8 left P20-P80 coverage failing at 38.4% against a nominal 60%. Two-sided split-conformal quantile regression, with the training SEASONS as folds (what fails to transfer is a season, not a random row), lifts held-out coverage to 55.4%. The two ends are calibrated separately: one shared widening left the misses lopsided at 19.6% below against 27.7% above, because the upper tail is what the model underprices. After: 25.0% below P20, 19.6% above P80 against a 20/20 target. The upper end transfers, the lower end still does not.

**57.4 Step 3: the level calibrates exactly, and the two inflation figures do not agree.** 70 keepers commit $636, leaving 126 lots and $1,765; rescaling the amount above the $1 minimum bid so those lots sum to the budget gives k = 0.837 and the identity holds to the cent. Solving it needs iteration, not algebra: the $1 floor, the role cap and the band repair are all non-linear, and a single algebraic pass shipped $1,853 against $1,964. The ROADMAP predicted the market's implied inflation would agree with `api._inflation()`'s remaining-budget / remaining-worth. It does not: **1.96 against 1.33**. The gap is the denominator. `_inflation()` assumes the production value left in the pool is `$2,600 minus keeper worth` = $1,481; the 126 lots that actually clear carry $1,001. The league will spend $1,765 on players holding $1,001 of modelled production, because it buys youth, name and last year's contract as well.

**57.5 Step 4 refuted by its own output.** Implemented as specified: keeper surplus becomes `market_price - keeper_cost`, summed over control years with a 2028 price from the same model, iterated to a fixed point (the price level depends on committed keeper salary, which depends on the keeper set). It converges at **104 keepers against 70, flipping 56 of 276 calls**, and it is wrong in both directions:

| | production basis | market arbitrage basis |
|---|---|---|
| keepers | 70 | 104 |
| keeps Mike Trout at $4 (4.64 roto pts, $0 production) | no | yes, on $0.39 of arbitrage |
| of its 45 extra keeps, projecting below replacement | n/a | 30 |
| mean production value of those extra keeps | n/a | $2.69 |
| keeps Tarik Skubal at $38 (12.57 roto pts) | yes | **no** |

`market_price - keeper_cost` measures the gain on a transaction, not the worth of a roster spot. It keeps replacement-level players whose only virtue is being cheap relative to what someone would bid, and it drops the best pitcher in the sample because the $34 pitcher ceiling caps his market price below his salary. Shipped as `surplus_market` / `keep_2027_market`, a second lens; `keep_2027` stays on the production basis and did not move. A third construction (production priced at the market's own marginal rate, $12.18 per roto point above replacement) fixes the sign errors (Skubal $94.52 keep, Trout cut) but overshoots the top harder than anything else, which is the same failure as `keep_value`, not a fix for it.

**57.6 Five systems, and the two anchored to league behaviour agree.** `out/valuation_comparison.csv`, 276 rostered players:

| system | total $ | mean | median | max | anchored to |
|---|---|---|---|---|---|
| `production_value` | 2,319 | 8.40 | 5.07 | 51.91 | the $2,600 budget identity |
| `keep_value` | 4,449 | 16.12 | 13.33 | 78.81 | the auction exchange rate |
| `market_price` | 3,047 | 11.04 | 8.50 | 45.00 | 677 revealed purchases |
| `comp_price` | 2,272 | 8.23 | 7.00 | 23.00 | 15 nearest comps' real salaries |
| `revealed_price` | 2,973 | 10.77 | 10.39 | 39.85 | 133 keeper decisions |

Rank agreement is high within the production family (`production_value` vs `keep_value` 0.985, vs `revealed_price` 0.929) and much lower against price (`market_price` vs `production_value` 0.594, vs `comp_price` 0.439). The systems split cleanly into "what is he worth" and "what will he cost", and the second pair does not rank players the way the first does.

The convergence worth reporting is at the top. For Skubal the two measures built from what this league actually did, from completely separate data, land on the same number: `market_price` **$34.00**, `revealed_price` **$34.31**. `production_value` says $51.91 and `keep_value` $78.81. The league-mate's original complaint (2026-08-15) was that $52 was too high for a pitcher in a league that has never paid more than $34 for one. Two independent instruments now say he was right.

**57.7 Where the systems disagree is the buy/sell signal.** Largest `production_value - market_price` gaps: Skubal +$17.91, Skenes +$17.78, Cade Smith +$16.96, Jhoan Duran +$16.35, Zach Neto +$15.69 (produce more than they will cost). Largest the other way: Ohtani's pitcher asset -$34.00, Cam Schlittler -$25.38, Gavin Williams -$19.33, Jordan Walker -$19.00, Nolan McLean -$19.52 (cost more than they produce). The sell list is almost entirely young pitchers, which is the market paying for prospect upside that the production model, correctly, does not see. Whether that is the market being wrong or the model being blind is the question Step 5 was meant to answer and could not.

### 58. Innings were read in thirds notation as decimals (bug, fixed)
FanGraphs writes innings pitched as `132.1` meaning 132 and one third, not 132.1. `klab/io.load_pitchers_history()` handed that straight to `denoms.py`, which sums it (`ppool["IP"].sum()`) and divides by it (`base_IP + ip` in `RotoScorer.pitchers()`) as a decimal. A pitcher with a `.1` fraction was short 0.233 innings and one with `.2` short 0.467, so a nine-man staff lost up to about 4 innings and every ERA and WHIP denominator sat on the wrong base.

Worse than the rounding: the three pitcher files were on two different conventions. Actuals (`fg_pitchers_2022_2026.csv`) use thirds (fractional parts .0/.1/.2 only); the rest-of-season export is whole innings; ZiPS 2027 uses true decimals (.0/.3/.7). `project.py` blends actuals against ZiPS, so it was mixing units.

Fixed at the loader: `IP = floor(IP) + frac x 10/3`. The check that it is right is that ERA and WHIP recomputed from the converted innings now reproduce FanGraphs' own columns exactly (Skubal 2026: derived 2.8564 / 0.9824 against stored 2.8564 / 0.9824; they did not match before).

**Impact is small and is reported as small.** Mean absolute change in projected roto points: pitchers 0.0069, hitters 0.0000. Max change in `production_value` $0.15. Zero keep/cut flips. `$/rp` keep 10.010 to 10.003, redraft 6.526 to 6.522, replacement 4.7333 unchanged. The error largely cancelled: it shrank each pitcher's innings and the league denominator built from those same innings by the same proportion. Fixed because it is wrong, not because it moved a decision.

### 59. Young breakouts: the projection already handles them, the keeper model did not
Josh's question, 2026-09-08: a 22-year-old and a 31-year-old with the same big 2026 are not the same 2027 bet, and ZiPS 2027 was pulled mid-season. Two separate questions, opposite answers.

**59.1 How much of a season carries forward, by age.** `scripts/age_persistence.py`, 3,038 player-seasons 2022-2025 with a real line (200+ PA or 40+ IP) and a known age, next season scored on its own denominators, a missing next season counted as zero roto points rather than dropped (survivor-only persistence is the classic way to overrate prospects; 8.5% of 33+ seasons have no next year against 7.0% at 23 and under).

Persistence `rp_next = a + b x rp_this` by age band, all-population:

| age | n | slope b | se | intercept | R^2 | survives |
|---|---|---|---|---|---|---|
| <=23 | 129 | 0.628 | 0.085 | 1.82 | 0.301 | 93.0% |
| 24-26 | 697 | 0.457 | 0.034 | 1.57 | 0.210 | 92.5% |
| 27-29 | 932 | 0.492 | 0.026 | 0.96 | 0.273 | 91.4% |
| 30-32 | 707 | 0.537 | 0.032 | 0.71 | 0.285 | 91.2% |
| 33+ | 573 | 0.504 | 0.032 | 0.23 | 0.308 | 85.2% |

The slope does NOT vary with age: a linear age interaction is +0.0010 (t=0.22, p=0.83), and a young-dummy interaction fails at every cutoff tested (age<=23 p=0.18, <=24 p=0.46, <=25 p=0.59). What varies is the LEVEL. Controlling for production, volume and role, being 25 or under is worth **+0.778 roto points** next season (t=3.31, p=0.0009). Restricting to top-quartile seasons, the share of production retained is 82.8% at 23 and under against 62.7% at 27-29, but that gap is intercept, not slope: young players are better on average, not better at holding a spike.

**59.2 The engine already applies almost exactly that premium, so nothing changed.** The same regression run on the engine's own 2027 projection against 2026 actuals gives a young-player coefficient of **+0.621** (age<=25, t=3.34) against the empirical **+0.778** (t=3.31). The two are within each other's standard errors. At age<=24 the engine is if anything generous: +0.755 against an empirical +0.633. Retention of a top-quartile 2026 season, engine against empirical: 24-26 74.9% / 69.3%, 27-29 75.0% / 62.7%, 30-32 67.1% / 68.8%, 33+ 64.2% / 57.2%.

This vindicates CONSTRAINTS.md's 2026-08-14 decision to decline an aging curve. ZiPS carries age, the blend inherits it, and the number it inherits is the right one. **No projection change was made.** The reviewer's "young players read too cheap" (ROADMAP item 1) is therefore not a projection error: it is the market paying more for youth than the production is worth, which is exactly what `market_price` now shows (#57.7 lists young pitchers as the whole sell side).

**59.3 Owners do price age, and the revealed-price model was blind to it.** In the 2026 keeper decisions (n=134, 74 kept), age carries **-0.127 per year** (t=-2.13, p=0.033) after production, salary, years of control and role; pseudo R^2 rises 0.144 to 0.169. Age belongs in THIS model and not in the board's keeper logic, and the distinction is the whole point: `keeper_revealed.py` is fit on last season's actuals, which carry no age information, so the effect is real signal; `production_value` gets its age adjustment from ZiPS, so a second one there would double-count. Age is now a term in the revealed-price curve.

Owners look close to binary on the young: of the 11 decisions on players 25 and under, the 5 with above-median prior production went 4 kept, and the 6 below-median went 0 kept. Suggestive of a "produce or be cut" rule that a continuous production scale cannot express, and far too small a cell (n=11) to claim; recorded as a thing to re-test when the 2027 decisions land.

### 60. Team-specific category value: the premise holds, the estimate does not
ROADMAP item 2, scoped and not built. `klab/teamvalue.py` and `scripts/team_category_value.py`.

The premise is not in doubt: `denoms.py` divides every player's units by ONE league-wide denominator, so a save is worth the same to the team with 106 of them and the team with 0. Built the correction the obvious way. `local_denominators()` measures how many units a team needs for one standings point from where it actually sits, as the mean gap between adjacent teams within two ranks either side (the raw next-team-up gap is 0.1 units when two teams are tied and 50 when a team is isolated, which would swing a player's value 100x on standings noise). `value_multipliers()` expresses that against the league-average team. The prize is large: within a season the multiplier runs 0.29 to 13.28.

**It is noise.** Year-over-year persistence of a team's multiplier in a category, pooled over the four transitions 2022-2026, n=32 per category:

| | R | HR | RBI | SB | AVG | W | SV | K | ERA | WHIP | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gap multiplier | -0.14 | +0.09 | -0.02 | -0.10 | -0.02 | -0.12 | -0.03 | +0.09 | -0.24 | -0.20 | **-0.07** |
| category rank | +0.46 | +0.22 | -0.07 | +0.49 | +0.33 | +0.18 | +0.31 | +0.56 | -0.20 | +0.18 | **+0.25** |

Whole-matrix correlations across consecutive seasons are -0.108, -0.026, +0.010, +0.054. Where a team sits relative to the pack is a property of one season's realised standings, not of the team. Pricing 2027 keepers with it would be fitting n=10 noise, the same instability METHODS section 3 #1 already rejected per-season denominators for.

What survives is coarser. Category RANK persists at +0.25 on average, usefully in K (+0.56), SB (+0.49), R (+0.46), AVG (+0.33) and SV (+0.31), and not at all in RBI (-0.07) or ERA (-0.20). That supports a contend-or-punt flag on five of ten categories, not a continuous per-team multiplier, and it is a much smaller build than item 2 as written.

Saves remain the one structural case and are already handled (#1): every season has one or two punters at 0-16 saves and the rest inside a 40-save band (2026: 0, 37, 46, 51, 56, 59, 61, 67, 73, 106). That bimodality is real and durable, which is exactly why #1's "saves are cheap conditional on competing" survived and a general version of the same idea does not.

**Not wired into the board.** `klab/teamvalue.py` is committed as the scoping artifact with the negative result attached, so the next person does not rebuild it. The in-season case is different and is already correct: `trade.win_now_delta()` re-ranks actual observed standings rather than projecting them, which is the one setting where the gap structure is known rather than estimated.

### 61. Half the roster had no position, so half the comp pools were wrong
`klab.keeper.position_map()` read positions from the auction files only, which means a player who arrived through free agency rather than the auction had none. That was **134 of 277 rostered players, 48%**, not the "some players (Cade Smith)" the roadmap recorded. `auction_estimator.find_comps()` falls back to the full role when it cannot match a position group, silently, so those players were comped against every hitter or every pitcher in league history instead of against their own position.

Fixed with `data/positions_2026.csv`: hitters take the primary position off the league's own contracts page, pitchers are classified SP or RP by career starts share (GS/G >= 0.5), which is derived rather than entered. Coverage went 143/277 to **277/277**, and UNKNOWN to zero.

| position group | before | after |
|---|---|---|
| SP | 40 | 91 |
| OF | 29 | 50 |
| CI | 23 | 54 |
| MI | 24 | 41 |
| RP | 16 | 25 |
| C | 5 | 14 |
| UTIL | 6 | 2 |
| UNKNOWN | **134** | **0** |

`comp_price` moved for 146 of 277 players, mean absolute change $3.81. The largest are exactly the players who had been comped against the wrong pool: Justin Crawford $18 to $6 and Caleb Durbin $14 to $2 (young hitters previously comped against all hitters, now against outfielders and third basemen), Drew Rasmussen $6 to $16 and Nick Pivetta $3 to $13 (starters previously pooled with relievers). No other dollar figure is affected: the comp estimator is deliberately separate from `redraft_value` (#35, CONSTRAINTS.md).

The position file is a data asset, not a code fix, and it will go stale as rosters churn. `data/README.md` records how to rebuild it.

### 62. Waiver-wire value: a fourth route to replacement level, and it disagrees with the third
ROADMAP item 4. `scripts/waiver_value.py`. No constant was changed.

Replacement level anchors every dollar figure and is not stable: it moved 4.811 to 4.599 to 4.733 across two data refreshes on one day. METHODS section 2.5 lists three routes and notes none is fitted to agree. This adds a fourth, the only behavioural one.

**What teams actually do.** Two roster snapshots 3.5 weeks apart (2026-08-13, 2026-09-07) give 34 adds and 33 drops of observed waiver activity, the first transaction data in the project (transaction-log scraping is declined on the roadmap; two snapshots are a cheap substitute).

| | n | 2026 roto pts, median | 2027 projection, median | above replacement (2027) |
|---|---|---|---|---|
| added off the wire | 34 | 4.15 | 4.42 | 41% |
| dropped to the wire | 33 | 4.10 | 4.36 | 33% |

Teams add and drop at the same level. The churn margin is **4.12 on actuals, 4.39 on projections**, and the engine's replacement is **4.733**, above both. The 300th-best projection, the `WAIVER_VALUE = "medium"` setting that has sat unused in `config.py`, is **4.381**: almost exactly the observed margin.

Switching to it is tempting and would look like a fix for the top of the board. `$/rp` falls 6.522 to 5.333 and Skubal falls **$52.75 to $45.20**, landing on the league's all-time $45 ceiling, which is the exact complaint that started ROADMAP item 1 and agrees with `market_price` ($34) and `revealed_price` ($34) in direction. Eight players' single-year keep surplus changes sign, all marginal (Oneil Cruz +1.35 to -0.48, Yamamoto +3.77 to -0.69, five others inside +/- $2).

**It was not switched, because the internal-consistency test points the other way.** FINDINGS #27 justified the 230th by counting unrostered players who project above it. Rerun on current data:

| candidate | level | unrostered above it |
|---|---|---|
| auction intercept | 3.980 | 168 of 1,751 |
| 300th (medium) | 4.381 | 106 |
| **230th (low, current)** | **4.733** | **59** |
| median FA pickup | 5.040 | 33 |

Replacement is supposed to be what a team can have for free. At 4.381 the model claims 106 free agents beat the marginal rostered player, which cannot be true of a level that is meant to be freely available. That argues replacement is too LOW at 4.381, while the churn data argues it is too HIGH at 4.733. The two behavioural readings genuinely conflict, and 4.733 sits between them.

The likely reconciliation, untested: deep free-agent projections are optimistic (playing time is assumed, prospects carry upside), which inflates the 106; and teams churn injured and slumping players rather than optimising, which drags the observed margin down. Both would need transaction logs WITH DATES to separate, so that what a team got from an add can be measured after the add. That is the one thing that would settle it and it is the roadmap's declined item.

**Left at `WAIVER_VALUE = "low"`.** The change is one line and reversible; the evidence does not currently support making it.

---

**Exchange-rate trail.** $7.56 (#7/#14); $10.08 (#17, mechanism retracted #19); $9.11/$6.32 keeper/redraft (pre-#26); $9.26/$6.24 (#26); $9.26/$6.21 (#28); $9.17/$6.29 (#31); $6.58 to $7.56 positional (#52). Pooled 2022-26 $5.83 (CI 5.13-6.74); single-season ~+/-40% (#7); denominators +/-34% (#30).
