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

**One reconciliation route tested and refuted (assessment phase, see #65).** The projected pitcher pool is demonstrably smeared: 1,151 pitchers, 223 above 100 IP against 118-127 in real seasons. If the 106 free agents above 4.381 were mostly part-time arms the projection invented, the internal-consistency objection would dissolve and the churn margin would win. They are not. The 106 split **99 hitters and 7 pitchers**, and only 4 of those 7 clear 100 IP. The count is a hitter phenomenon and the pitcher-pool distortion does not explain it. The tie stands, and the "deep free-agent projections are optimistic" half of the reconciliation above still needs testing on the hitter side.

### 62.5 The role cap survives a third challenger
Closes the "role cap is still a patch" item from #57.2 and #57.8. The uncapped price model predicts $55.38 for a hitter against a $45 league ceiling, and two designed-in fixes had already lost on leave-one-season-out (concave predictor transforms, monotone GBM). Tried a third with a different mechanism: bound the RESPONSE rather than the predictor, fitting `logit(price / CAP)` so predictions asymptote to CAP by construction and no clipping is possible.

It wins on LOSO at every cap tested (MAE 6.49-6.52 against 6.59 for log-price) and loses on the held-out season (6.17 against 5.76, bias -3.27). Its maximum 2026 prediction is $31.44 for a hitter when the realised maximum was $43. Same failure as the GBM: it buys top-end safety by declining to predict high at all.

Three approaches, one conclusion. **The top-end overshoot and top-end accuracy are the same knob.** Any model that cannot predict $55 also cannot predict $43. The cap keeps the accuracy and bounds only the two players per season who breach, which is the right trade until there is a mechanism that distinguishes "this player is worth $50" from "this player is worth $30 and the model is extrapolating". Noted also: LOSO preferred the bounded model and the held-out season contradicted it, a reminder that leave-one-season-out on three seasons is itself noisy and the held-out test is the acceptance criterion (ROADMAP item 1 Step 2).

### 63. The $1 minimum bid is a point mass, and the band could not see it
Closes the lower-tail coverage failure left open in #57.3.

**Diagnosis.** Held-out P20-P80 coverage was 55.4% against a nominal 60%, with the misses lopsided: 25.0% below P20 against 19.6% above P80. The upper end was calibrated, the lower was not. Listing the misses made the cause obvious: **19 of the 28 below-P20 misses sold for exactly $1**, and $1 purchases are 19.6% of the training seasons and 19.6% of 2026. A continuous quantile regression cannot represent a point mass. It put P20 at a median of $1.50 for players who were always going to cost the minimum bid; their actual $1 then fell below their own 20th percentile, by construction.

**Fix.** A hurdle: a logistic on the same design matrix for `P(salary = $1)`, and P20 set to $1 wherever that probability reaches 0.20. If a fifth of a player's probability mass sits on the minimum bid, his twentieth percentile IS the minimum bid, whatever the continuous fit says above it. This is the "Tobit at the $1 floor" that ROADMAP item 1 Step 2 offered as the alternative to log-price; log-price was chosen for the point estimate and the floor was left unhandled, which is what showed up here.

| | coverage | below P20 | above P80 | median width |
|---|---|---|---|---|
| before | 55.4% | **25.0%** | 19.6% | $13.74 |
| after | 68.8% | **11.6%** | 19.6% | $14.17 |

The point estimate is untouched (MAE 5.76, Spearman 0.482). The conformal widening is now calibrated with the hurdle active, so the widths are fitted against the band that actually ships rather than a different object.

**The threshold is theory, not a tuned parameter, and that is deliberate.** Calibrating it on the training folds picks 0.50 (LOSO lower-tail miss 18.7%, closest to the 20% target), but 0.50 reproduces the old held-out result exactly (25.0% below) because at that threshold almost nobody gets the floor. The folds and the held-out season disagree, which on three seasons of about 130 purchases each is not surprising. 0.20 is what the definition of a twentieth percentile requires, so 0.20 is what ships. The cost is that the band now over-covers: 68.8% against a nominal 60%. Under-covering was a calibration failure; over-covering is conservative, and the lower tail is honest about the minimum bid.

**Also fixed here: a duplicated model.** `klab/price.py` was extracted from `scripts/price_model.py` earlier in the same session, but the script kept its own copy of `design`/`fit_price_model`/`predict`. The script therefore reported the OLD band numbers after the hurdle went into the real model, which is how the duplication was caught. The script now imports the core it is meant to be testing.

---

**Exchange-rate trail.** $7.56 (#7/#14); $10.08 (#17, mechanism retracted #19); $9.11/$6.32 keeper/redraft (pre-#26); $9.26/$6.24 (#26); $9.26/$6.21 (#28); $9.17/$6.29 (#31); $6.58 to $7.56 positional (#52). Pooled 2022-26 $5.83 (CI 5.13-6.74); single-season ~+/-40% (#7); denominators +/-34% (#30).

### 64. One dollar scale across hitters and pitchers is correct for this league
Assessment phase, Phase A. `docs/ASSESSMENT-BRIEF.md` carried this as its strongest lead and queued a hitter/pitcher budget split as Phase B item 1. The measurement refutes it. No constant was changed.

The brief's case was that standard SGP practice splits the budget 65/35 or 70/30 before converting to dollars, that Smart Fantasy Baseball argues hitter and pitcher SGP are not directly comparable, and that this project pools them. The test that settles it uses realised prices and realised production only, so no projection, no regression inversion and no replacement level enters it: what does this league pay per roto point actually delivered, by role?

| | dollars | roto points delivered | $ per realised roto point |
|---|---|---|---|
| hitters | 4,862 | 2,324.6 | **2.092** |
| pitchers | 2,752 | 1,301.6 | **2.114** |

A ratio of 0.99 on 668 purchases across 2022-2026. Per season the ratio is 0.909, 0.938, 1.150, 0.934, 0.988: no trend, no season outside +/-15%. The league prices a hitter roto point and a pitcher roto point the same.

That also explains the split that looked like a divergence. Hitters take 63.86% of auction dollars because they deliver 64.11% of the roto points, not because the league applies a hitting-budget convention. Four independent measures of the league's hitter share agree:

| measure | hitter share |
|---|---|
| realised roto points delivered, drafted pool 2022-2026 | 64.11% |
| auction dollars spent, 2022-2026 | 63.86% |
| current full rosters (276 players, salary) | 62.94% |
| active-roster proxy (top 23 per team by salary) | 63.31% |

**A budget split must not be built.** It would impose a convention the league's own behaviour does not use, on top of an exchange rate that is already right. This closes the brief's Phase B item 1 as refuted rather than deferred.

Recorded for the record because it points the other way and is the weaker object: regressing roto points on salary separately by role does give different slopes (implied $6.35/rp for hitters against $4.18 for pitchers, interaction t = 2.82, p = 0.005). That is the same inverted, attenuated regression Link 3 already distrusts, and per season it is unusable: 2026 alone gives $15.34/rp for hitters against $5.25 for pitchers. The raw ratio above is the identified quantity; the regression slope is not.

### 65. The calibration pool is not fieldable, and the obvious fix overshoots
Same phase, same session as #64. A real defect, diagnosed but deliberately not fixed. No constant was changed.

`board.value_players()` calibrates the budget identity on `base_players.nlargest(230, "roto_points")`, the top 230 by roto points regardless of role. On the 2027 projection that pool is **183 hitters and 47 pitchers**. The league fields 140 and 90 by rule and 134 and 96 in the observed active rosters. The pool that sets `usd_per_rp` is therefore a set of players no ten teams could legally roster, and pitchers are priced against 47 slots when 90 exist.

The consequence is the 10-point split error #64 measured the target for: the model allocates **73.70%** of the $2,600 to hitters where every measure of the league says 63-64%.

**The defect is latent in the code and activated by the projection.** Scoring each completed season on its own scale and taking the top 230 by realised roto points:

| season | HIT | PIT |
|---|---|---|
| 2022 | 129 | 101 |
| 2023 | 125 | 105 |
| 2024 | 131 | 99 |
| 2025 | 139 | 91 |
| 2026 | 130 | 100 |
| 2027 projection | **183** | **47** |

Five completed seasons all land near the fieldable 140/90. Only the projection does not, so this is not a property of the roto scale, which is what #64 independently confirms.

**The obvious fix was measured and rejected.** Constraining the pool to the top 140 hitters and top 90 pitchers with role-specific replacement moves `usd_per_rp` 6.5216 to 6.2130 and the hitter share to **54.21%**, which is as far below the league's 63-64% as the status quo is above it. Constraining the pool but keeping pooled replacement gives 71.55%. None of the three candidates is right, so no change ships.

The reason the fix overshoots is a second distortion, in the projected pitcher pool rather than the dollar scale. ZiPS Depth Charts spreads innings across the full depth chart, so the projection carries 1,151 pitchers of whom 223 clear 100 IP and 33 clear 150 IP, against 118-127 and 39-71 in real seasons. The 90th-best projected pitcher therefore sits at **3.527** roto points where completed seasons put him at 4.95 to 7.22. Role-specific replacement built on that pool hands pitchers a bar that is too low, which is why their dollar share doubles.

The pitcher shortfall is concentrated and measurable. Selecting the top 90 on the projection and evaluating the same 81 matched players on their 2026 actuals, so selection is identical on both sides:

| | W | SV | K | ERA | WHIP | total |
|---|---|---|---|---|---|---|
| projected | 2.301 | 0.752 | 2.426 | 0.031 | 0.090 | 5.600 |
| 2026 actual | 2.282 | 1.242 | 2.427 | 0.851 | 0.583 | 7.385 |

W and K are calibrated to within 0.02. The entire 1.79-point gap is ERA, WHIP and SV. The same comparison for hitters gives 6.612 projected against 6.399 actual, every category within 0.19: the hitter side needs nothing. Pitchers carry two of the five rate categories and hitters one, so any rate-category level error hits pitchers about twice as hard.

The clearest single symptom: the projected top-90 pitchers pool to a **3.597 ERA against a league baseline team ERA of 3.613**, while the actual top-90 pool to 2.97-3.08. The model believes the ninety best arms available are indistinguishable from an average fantasy staff.

**What is not established, and why nothing shipped.** Part of that rate gap is legitimate. A projection regressed to the mean SHOULD show less rate spread than a realised season, and ERA is the least projectable category in the set, so a humble ERA projection may be the correct expectation rather than an error. Separating "correctly humble" from "wrongly compressed" needs a historical ZiPS or Steamer archive to backtest against, which `data/` does not have, and which Link 1 of the brief already names as the blocker on the blend weights. Acting on the 73.70% without that would mean trading a known 10-point error for an unknown one, which is how all four retractions in this file happened.

Ranked next steps, in order: obtain two seasons of projection archives; then refit the blend and retest this; only then choose a pool rule.

**Partly superseded by #68** (archive obtained, question answered). The 183/47 pool, the 73.70% share and all three candidate measurements stand and reproduce exactly. Two claims above do not. The innings-smearing mechanism is refuted: Marcel has a near-realistic innings distribution and still produces 184/46, so smearing is not what removes pitchers from the pool. And "the obvious fix overshoots" does not hold: slot-constraint with role-specific replacement gives 54.21% where perfect foresight on completed seasons gives 52.0-55.1% for the same rule. The 63-64% comparison in this entry is against a different population; see #68 item 5.

### 66. The decision audit: owners defend their throw-backs better than their keeps
Josh's named unbuilt analysis, `scripts/decision_audit.py`, interpreted. Scores the owners, not the model. 336 decisions.

**2026, clean labels, n = 134.**

| | n | mean salary | right ex ante | right realised | mean surplus ex ante | mean surplus realised |
|---|---|---|---|---|---|---|
| kept | 74 | 11.45 | 73.0% | 55.4% | 13.17 | 6.75 |
| thrown back | 60 | 15.40 | 61.7% | 73.3% | 1.21 | 6.39 |

The pattern is the same in both directions and it is the headline. Keeps look strong when they are made and half their expected surplus evaporates: 73.0% right ex ante falls to 55.4% realised, and $13.17 of expected surplus becomes $6.75. Throw-backs look marginal and improve: 61.7% becomes 73.3%, and $1.21 becomes $6.39. By realised surplus the two decisions are worth the same, $6.75 against $6.39, despite the keeps looking ten times better at the time.

**2023-2025, reconstructed labels, n = 202. Selection-biased, and the bias runs the same way as the finding.**

| | n | right ex ante | right realised | mean surplus ex ante | mean surplus realised |
|---|---|---|---|---|---|
| kept | 65 | 50.8% | 43.1% | 8.64 | -0.29 |
| thrown back | 137 | 60.6% | 72.3% | 1.98 | 4.49 |

Kept players return negative mean realised surplus here. This cannot be read at face value: pre-2026 a keep is only detectable when the player was LATER thrown back (#56.5), so the reconstructed kept sample is enriched for players who went on to fail. The direction agrees with the clean 2026 sample; the magnitude does not survive the bias.

**He said no, the room said yes.** Of the 60 players thrown back in 2026 at a mean declined salary of $15.40, the auction re-bought them at a mean of $13.73, and the room paid more than the owner had declined in 23 of 60. Owners' throw-backs are ratified by the market about five times in eight.

**Luck against judgment.** The ex-ante and realised verdicts agree on 84 of 134 decisions in 2026 (63%) and 119 of 202 in 2023-2025 (59%). Roughly two decisions in five are scored differently by what was knowable and by what happened, which is the size of the noise any single-season verdict carries and the reason the two columns are reported separately.

**What this does not answer, and it is the biggest gap in the project.** Whether the MODEL would have beaten the owners is still unmeasured. It needs the model's own keep/cut call as of each past deadline, which needs a projection built from data as of that date. The board is a 2027 object and cannot be rewound. This is the same missing artefact as #65 and Link 1: without projection archives the product's central claim has no out-of-sample test.

### 67. The blocker is gone: three seasons of ex-ante projections are now in `data/`
Same day as #64-#66, after Phase A named the missing artefact. No constant was changed and no finding was re-run; this entry records the archive and its traps so the session that uses it does not rediscover them.

Phase A ended with three open questions and one blocker common to all of them: the blend weights have never been fitted (Link 1), the calibration-pool rule cannot be chosen (#65), and the keep/cut advice has never been tested out of sample (#66). Each needs a projection made BEFORE a season that has since been played, and `data/` carried only the ZiPS 2027 and 2028 pulls.

Baseball-Reference publishes Marcel projections per season and keeps the pages up. `data/` now holds six files covering **2024, 2025 and 2026**, all three of which have actuals. `klab/marcel.py` reads them; `scripts/validate_marcel.py` checks them.

**Marcel is not ZiPS and must not be swapped in for it.** Marcel is Tom Tango's deliberately naive baseline: a three-year weighted average, regressed to the league mean, with a flat age adjustment. It is the bar a real projection system is expected to clear. What it provides here is not accuracy but an *honest ex-ante* line, which is the only property a backtest needs. Blend weights fitted against Marcel describe the Marcel blend; treat the result as a shape, not a transfer to ZiPS.

**Provenance.** Baseball-Reference returns HTTP 403 to automated fetches, so these came out of a logged-in browser session against `/leagues/majors/{year}-projections.shtml`, extracted from the table DOM and written to disk over loopback. They were not transcribed by hand.

**Verification, because the extraction was not a plain download.** Baseball-Reference publishes derived columns that are algebraically determined by the counting stats, so `scripts/validate_marcel.py` re-derives all of them: `WHIP`, `ERA`, `H9`, `BB9`, `SO9`, `SO/W` for pitchers and `BA`, `TB`, `SLG`, `OPS` for hitters. **All ten identities hold on all six files, zero violations**, every residual inside published rounding. Row counts independently match the pasted source tables exactly (514/623/504/611/644/750 before de-duplication).

| | 2024 | 2025 | 2026 |
|---|---|---|---|
| hitters, rows after de-dup | 493 | 504 | 644 |
| pitchers, rows | 610 | 611 | 750 |
| `fg_id` join coverage | 100% | 100% | 100% |

**Three traps, all encoded in `klab/marcel.py`.**

1. **The file year is the projected season, not the source page.** BR files the 2026 projections under `2025-projections.shtml`. Off-by-one here would silently score a projection against the wrong season and every downstream number would look plausible.
2. **The pitcher id is in the DOM but not in the rendered table.** Copy-pasting the pitcher table off the page loses `Name-additional` and forces fuzzy name matching. Extracted from the DOM it is present, and the bbref-to-`fg_id` join through `key_bbref` is exact at 100% on all six files. `scripts/fetch_chadwick.py` now keeps `key_bbref`; it did not before.
3. **Marcel writes whole innings.** `157.0`, never thirds notation. The conversion `io.py` applies to FanGraphs innings (#58) would corrupt these, so `_read_pitchers` raises if it ever sees a `.1`/`.2` rather than trusting a comment.

**One result falls straight out of the archive, before any analysis.** Marcel's `Rel` column is its reliability weight: the share of a projection carried by the player's own record rather than regression to the league mean.

| | median rel | p10 | share below 0.30 |
|---|---|---|---|
| hitters (2024-2026) | 0.70-0.72 | 0.21-0.32 | 8-15% |
| pitchers (2024-2026) | 0.47-0.49 | 0.12-0.18 | 21-26% |

**Marcel trusts a pitcher's own record about half as much as a hitter's, and a fifth to a quarter of pitcher rows are mostly league mean wearing a player's name.** This is independent corroboration, from a projection system with no connection to this project, of the pitcher-side compression #65 measured in the ZiPS blend: pitcher performance is simply less projectable, so any system regresses it harder, so pitchers cluster toward the middle and fall out of a pool selected on projected roto points. #65 diagnosed that as possibly a ZiPS artefact. It is not: it is a property of pitching.

The consequence for the work ahead is a warning. A backtest that scores every Marcel row as a forecast is, for a quarter of pitchers, scoring the league mean and calling it a projection. `rel` must be carried through and reported, and low-`rel` rows either weighted or excluded with the count stated.

### 68. The pool pathology is general to projections, and #65 judged its repair against the wrong benchmark
Assessment phase, Phase B item 1, the first use of the Marcel archive (#67). Diagnostic only. No constant changed, no committed output moved, `scripts/validate.py` CHECK 5 still prints 73.7%. `scripts/marcel_pool_test.py` reproduces every number below, including four of #65's own as controls: 131/99, 139/91, 130/100, 183/47, 73.70%, 54.21% and 71.55% all come back exact.

#65 found the 2027 calibration pool is 183 hitters / 47 pitchers where completed seasons run 125-139 / 91-105, and could not tell whether that is a property of projections in general or an artefact of ZiPS Depth Charts. Marcel is an independent ex-ante line for three seasons that have since been played, so it answers the question directly. Every arm below is scored with the SAME `RotoScorer` as its season's actuals, so only the stat lines differ.

**1. It reproduces. The pathology is general to projections, and the blend is not the cause.**

| arm | HIT | PIT | 90th-best pitcher, roto pts |
|---|---|---|---|
| 2024 actual | 131 | 99 | 5.217 |
| 2024 Marcel | **184** | **46** | 3.092 |
| 2025 actual | 139 | 91 | 4.955 |
| 2025 Marcel | **155** | **75** | 4.081 |
| 2026 actual | 130 | 100 | 5.433 |
| 2026 Marcel | **160** | **70** | 4.664 |
| 2027 ZiPS blend | 183 | 47 | 3.526 |
| 2027 ZiPS, blend weights zeroed | 191 | 39 | 3.463 |

Marcel 2024 lands within one player of the ZiPS 2027 pool. Removing the 2026 actuals entirely makes the ZiPS pool worse, not better, so the blend is not what does it. In every completed season the 90th-best pitcher and the 140th-best hitter sit within 0.58 roto points of each other, which is why a role-blind top 230 lands near the fieldable 140/90 on realised data. Under every projection the pitcher side of that pair collapses.

**2. #65's proposed mechanism is refuted. Smeared innings are not what empties the pool.**

| arm | pitchers | IP >= 100 | IP >= 150 |
|---|---|---|---|
| actual 2024-2026 | 851-873 | 118-127 | 40-71 |
| Marcel 2024-2026 | 609-750 | 142-154 | 46-55 |
| 2027 ZiPS blend | 1,151 | 223 | 33 |
| 2027 ZiPS, blend weights zeroed | 1,151 | 243 | 21 |

Marcel's innings distribution is close to a real season and nothing like ZiPS's: it carries roughly the right number of 100-inning arms and MORE 150-inning arms than ZiPS, which is the signature of a projection that does not spread innings across a depth chart. It still produces 184/46. #65 was right that ZiPS Depth Charts smears innings and wrong that the smearing is what removes pitchers from the pool.

**3. The mechanism is rate-category compression, and the category format decides which role it hits.**
sd(projected) / sd(actual) per category, over every player carrying both a Marcel line and a realised line. No top-N filter: selecting on the projection would truncate the projected distribution from below and shrink its sd for reasons unrelated to compression.

| season | R | HR | RBI | SB | AVG | W | SV | K | ERA | WHIP |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | 0.639 | 0.700 | 0.646 | 0.703 | 0.714 | 0.665 | 0.504 | 0.766 | 0.576 | 0.575 |
| 2025 | 0.593 | 0.622 | 0.599 | 0.812 | 0.713 | 0.699 | 0.542 | 0.787 | **0.433** | 0.484 |
| 2026 | 0.696 | 0.795 | 0.719 | 0.894 | 0.787 | 0.762 | 0.584 | 0.839 | 0.581 | 0.604 |

ERA, WHIP and SV compress hardest in all three seasons; W and K sit with the hitter categories. **Pitchers carry three of the four most-compressed categories and hitters carry one.** Any projection regresses the least predictable stats hardest, so pitcher roto points cluster toward the middle and drop out of a pool selected on projected value. #67's reliability split (pitchers 0.47 against hitters 0.71) is the same fact stated from the projection's own side. Whole-role dispersion follows: sd ratio 0.52-0.61 for pitchers against 0.60-0.73 for hitters.

**4. No pool rule reaches 63-64% under perfect foresight, so that was never the benchmark for this quantity.**
Hitter dollar share under #65's three candidate rules. The `actual` rows are perfect foresight: the season is over and the stat lines are the real ones.

| season | arm | blind (status quo) | slot + pooled repl | slot + role repl |
|---|---|---|---|---|
| 2024 | actual | 0.5213 | 0.5254 | 0.5511 |
| 2025 | actual | 0.5180 | 0.5184 | 0.5249 |
| 2026 | actual | 0.4642 | 0.4695 | 0.5198 |
| 2027 | ZiPS | **0.7370** | **0.7155** | **0.5421** |

The entire perfect-foresight range is 46.4% to 55.1%. #65 rejected slot-constraint-with-role-specific-replacement because its 54.21% was "as far below the league's 63-64% as the status quo is above it". **54.21% is where perfect foresight puts that rule** (52.0-55.1%, and 52.5-55.1% on the two complete seasons). It is the only one of the three candidates whose output on the projection agrees with its output on realised data; the other two miss their own perfect-foresight values by 20 points.

**5. The mis-split enters at the dollar conversion, not the projection.**
#64's 63-64% is measured over the players this league rosters, not over the top 230 by projected points. Both quantities on both populations, from the committed 2027 board:

| population | quantity | hitter share |
|---|---|---|
| rostered (276) | projected roto points | **65.20%** |
| rostered (276) | `redraft_value` | 71.78% |
| calibration top-230 | projected roto points | 77.95% |
| calibration top-230 | `redraft_value` | 73.70% |

The projection's role split on the rostered set is 65.20% against #64's 64.11% of roto points actually delivered: right to within 1.1 points. The dollar conversion then moves it to 71.78%. Subtracting one pooled replacement level from a compressed distribution takes a larger fraction of a pitcher's value than of a hitter's, which is the same compression again, now priced. #65's 73.70% is that conversion evaluated on the hitter-skewed pool the compression itself creates, which is why it reads 8 points worse than the same conversion on the rostered set.

**What is not established, and why nothing ships this session.**
- Marcel is the naive baseline (#67). The magnitudes describe the Marcel blend; only the shape transfers to the ZiPS path. The shape is what items 1-4 above turn on, and item 4's benchmark comes from realised seasons rather than from Marcel, so it does not carry that caveat.
- Three seasons, one partial. 2026 actuals are ~75% of a season, so the perfect-foresight benchmark rests mainly on 2024 and 2025.
- **Nothing here shows slot + role-specific replacement is the right rule.** It shows the stated reason for rejecting it does not hold. Choosing a pool rule is a valuation change and still owes the before/after keep/cut flip diff CLAUDE.md requires. That is the next session's work, not this one's.
- The hitter/pitcher budget split stays refuted (#64). Nothing here reopens it: this is a replacement-level and pool-selection question, not an exchange-rate one.

### 69. The out-of-sample keep/cut test: the model does not beat the owners
The test #66 named as the biggest gap in the project, run for the first time. `klab/rewind.py` rebuilds a board for a past season from pre-season data only; `scripts/backtest_keepers.py` scores it against what owners did and what then happened, on 289 decisions across 2024, 2025 and 2026. No constant changed and no committed valuation moved. This is a negative result and it is the honest one.

**The instrument.** A rewound board takes its projection from Marcel FOR that season (#67), its dispersion from completed seasons before it, its league level and baselines from the two completed seasons before it, and its field size from the same window. The $2,600 identity and the 14/9 roster shape are league rules and are not rewound. Coverage of decided players is 97%, 100%, 100%.

**Two corrections had to be made before any number meant anything.**

1. **The truth scale.** Scoring a keep against `redraft_value` asks what the player would fetch in a no-keeper redraft, which is a cheaper market than the one a keeper is actually traded against. On that scale only **23%** of these 289 decisions read as correct keeps while owners kept 47-55%, so any caller that keeps less wins for free, and the model keeps less. The correct denominator is the auction opportunity cost: keeping at $S forgoes $S of budget, and $S buys `intercept + S x slope` roto points, so keeping is right exactly when realised production beats that, which is `replace_cost > salary`. On that scale **54%** of the decisions are correct keeps. This is `scripts/decision_audit.py`'s open question 3, now fixed rather than flagged.
2. **The baseline.** Keeping EVERYTHING captures most of the available surplus in this league, because withholding 100 keepers leaves contracts cheap on average. Every dollar figure below is reported against that baseline, not against zero. A caller with a large positive total can still be destroying value.

**The result, against keep-everything.**

| season | n | owner | model_redraft | model_replace | model_matched_k | perfect |
|---|---|---|---|---|---|---|
| 2024 | 64 | **+240.9** | +199.9 | +206.0 | +219.2 | +478.1 |
| 2025 | 91 | -310.8 | -180.8 | **-56.2** | -196.0 | +402.8 |
| 2026 | 134 | +73.5 | -10.9 | **+78.6** | +0.9 | +578.2 |

Accuracy on the same decisions:

| season | owner | model_redraft | model_replace | model_matched_k |
|---|---|---|---|---|
| 2024 | **71.9%** | 64.1% | 65.6% | 65.6% |
| 2025 | 50.5% | **60.4%** | 57.1% | 57.1% |
| 2026 | **71.6%** | 68.7% | 64.9% | 62.7% |

**The owners win 2024 and 2026 on accuracy and 2024 on dollars; the model's only clear win is 2025, which is the season whose labels are most biased against the owners** (pre-2026 a keep is only detectable when the player was LATER thrown back, so the observed kept class is enriched for failures, #56.4). On 2026, the only season with clean labels, the owners are 71.6% right and beat keep-everything by $73.5; the production rule is 68.7% right and beats it by -$10.9. `model_matched_k`, which keeps exactly as many players as the owner and therefore tests ranking with the threshold removed, lands at +$0.9 against the owner's +$73.5.

**What this does and does not establish.** It is a FLOOR, not an estimate. Marcel is the deliberately naive baseline (#67) and the real board runs on ZiPS, so the honest statement is that **the engine's decision logic, driven by a naive projection, does not beat this league's owners.** It does not show the ZiPS board fails to. It does show that the edge, if there is one, comes from the projection rather than from the valuation machinery, because the valuation machinery is what was held fixed here. 2026 outcomes are also a partial season (~75%), which favours durable players on both sides.

**Two things the test settles on its own terms.**

**The keep threshold is on the wrong scale.** `board.py` runs `surplus_multiyear` off `redraft_value`. Priced against the opportunity cost instead, the same board captures more in all three seasons: +$6.1 (2024), +$124.6 (2025), +$89.4 (2026). Accuracy moves the other way in 2025 and 2026 because the opportunity-cost rule keeps far more (56-62% against 20-43%), and dollars is the metric that matters. This is a candidate change to the production rule, not a shipped one; it needs the keep/cut flip diff and it interacts with #57.5, which rejected a different permissive rewire for keeping 30 players below replacement.

**The pool rule question gets an independent answer, and it agrees with #68.** Scored on decisions rather than on the perfect-foresight benchmark:

| pool rule | 2024 $ | 2025 $ | 2026 $ | 2026 accuracy |
|---|---|---|---|---|
| blind (production) | 77.7 | 318.8 | 739.0 | 61.2% |
| slot_pooled | 77.7 | 318.8 | 781.8 | 62.7% |
| **slot_role** | 63.6 | **324.3** | **857.2** | **68.7%** |

`slot_role` wins the clean season by $118 and 7.5 accuracy points, wins 2025 by a hair and loses 2024. #68 argued for it from a benchmark; this argues for it from decisions, and the two agree.

**A structural note that reorganises the open work.** The pool rule moves `redraft_value` and therefore only affects `model_redraft`; `replace_cost` is set by the auction exchange rate and is pool-independent, so all three pool rules give identical `model_replace` results. **The pool rule is a PRICING question (what to bid) and the exchange rate is the KEEP/CUT question.** They have been treated as one problem and they are two.

**Housekeeping.** `MAX_KEEPERS` binds on 0 of 289 decisions (the most any team keeps is 9 against a cap of 13), so the roster constraint separates nothing here. `MIN_KEEPERS` is deliberately not applied: the recoverable decision set is a partial view of each team's keepable contracts, so forcing six out of it would invent choices. Only 1 of 289 decided players sits below Marcel's 0.30 reliability bar, so #67's low-`rel` warning does not bite on this population.

### 70. Two changes ship: the keep decision moves to the opportunity-cost scale, and the pool becomes fieldable
The first valuation change since the assessment phase began. Both were argued in #68 and #69 and are shipped here together because they interact. Committed outputs moved: `keeper_board_2027.csv`, `model_params.json`, `keeper_lab.html`, `trade_suggestions.json`, `app_reference.json`. 64 tests pass, 15 app checks pass, the JS still matches pandas on all 25 quantities.

**Change 1: `KEEP_BASIS = "replacement"`.** `board.build_board` built `surplus_multiyear` from `redraft_value`, which is what a player fetches in a full redraft with no keepers withheld. A keeper is not traded against that market. Keeping at $S forgoes $S of auction budget, and $S buys `intercept + S x slope` roto points, so the identified comparison is `keep_value` against the keeper cost. #69 backtested it at +$6.1, +$124.6 and +$89.4 of captured surplus across 2024-2026.

**Change 2: `POOL_RULE = "slot_role"`.** `value_players` calibrated the $2,600 identity on the top 230 by roto points regardless of role, which on the 2027 projection is 183 hitters and 47 pitchers (#65). It now calibrates on the fieldable top 140 hitters plus top 90 pitchers, with replacement read per role. #68 showed this reproduces perfect foresight (52.0-55.1% hitter share on completed seasons against its 54.21% here) where the old rule missed by 20 points; #69 showed it makes better keep/cut calls out of sample.

**What moved.**

| quantity | before | after |
|---|---|---|
| calibration pool | 183 HIT / 47 PIT | **140 / 90** |
| hitter share of $2,600 | 73.70% | **54.21%** |
| `usd_per_rp_redraft` | 6.522 | **6.213** |
| replacement, roto points | 4.733 pooled | **5.121 HIT / 3.526 PIT** |
| median `redraft_value`, hitters | 9.18 | **6.38** |
| median `redraft_value`, pitchers | 0.00 | **4.09** |
| players flagged keep | 70 | **123** |

`usd_per_rp_keep` ($10.00) is unchanged: it comes from the auction regression and never saw the pool.

**The flip diff, which is the part that reaches a decision.** 47 flips on 277 rostered players, **all of them cut-to-keep, none the other way**. Decomposing the two changes shows they are complementary rather than additive:

| POOL_RULE | KEEP_BASIS | keeps | of which below replacement |
|---|---|---|---|
| blind | redraft | 76 | 0 |
| blind | replacement | 123 | **4** |
| slot_role | redraft | 86 | 0 |
| **slot_role** | **replacement** | **123** | **0** |

The keep-basis change alone would introduce four keeps projecting below replacement, which is the objection that sank `keep_2027_market` in #57.5. Role-specific replacement removes all four, because those players are pitchers who sit above the pitcher bar and below the pooled one. **#57.5's objection does not apply to this pair.**

The new keeps are not marginal. The largest are Logan Webb ($27 cost, $44.10 replacement cost), Pete Alonso ($27, $43.20), Acuna ($26, $41.60), Corbin Carroll ($36, $51.60), Soto ($36, $51.20) and Schwarber ($20, $34.40). **The old rule cut a $36 Soto projecting 9.1 roto points**, which is the error the change is there to fix: $36 of auction budget does not buy 9.1 roto points at this league's exchange rate.

**Feasibility, checked because a permissive rule can advise the impossible.** The new keeper sets cost a mean of $139 of the $260 cap and leave $121 across 10.7 open slots, $11.30 per slot, against $12.80 under the old rule. No team is left unable to fill its roster; the worst has $73 for eleven slots. Keeps run 12.3 per team against the league's observed 10 in 2026 and the old rule's 7.6, so the advice now brackets revealed behaviour from above where it used to sit below.

**Three things this does not settle, recorded so they are not rediscovered as surprises.**
1. **`MAX_KEEPERS` binds for 6 of 10 teams.** Those teams are told to keep 13 because they have 13 positive-surplus contracts, so the model is filling a cap rather than discriminating. That is a real consequence of keeping being profitable in this league, not obviously an error, but it means the marginal keeper is no longer being chosen.
2. **The equilibrium is not closed.** The exchange rate is fitted at `KEEPERS_EXPECTED_2027 = 100`. If the league acted on this advice it would withhold ~123, thinning the auction further and raising the rate, which would raise `keep_value` again. The model advises one team against a fixed expectation; it does not solve the fixed point.
3. **The top end is still rich on this scale.** #57 recorded Skubal at `keep_value` $78.81 against a `market_price` of $34.00 and a revealed price of $34.31. He is now $86.93 and the keep decision runs on that number. The decision only needs `keep_value > cost` and $86.93 clears $38 as decisively as $50 would, so the ordering is safe even though the level is not. Do not read `keep_value` as a price.

**Not changed: the blend weights.** METHODS section 3 #9's unfitted constants were swept for the first time (`scripts/fit_blend.py`). Turning the blend off is costly, $36.1 against $98.3 of captured surplus per season, so the blend earns its place. The curve is then flat: 0.5 gives $98.3, 0.6 $100.4, 0.7 $105.8, 0.8-1.0 $103.6. Leave-one-season-out picks 0.6, 0.7 and 0.7 on the other two seasons and gains $0.0, $6.5 and $0.0 against production, a mean of $2.2 per season. The playing-time caps do worse: LOSO picks 0.15, 0.15 and 0.00 with held-out gains of +16.2, +19.9 and -55.0, a mean loss. **`BLEND_W_2026 = 0.50` sits inside the flat region and no alternative survives out of sample, so all four constants stand.** A judgment call vindicated rather than changed, as in #59.

**One premise corrected along the way.** The ZiPS 2027 export was assumed to predate the 2026 season. It does not. Regressing its projected rates on 2025 and 2026 actual rates for the 184 players with 300+ PA in both gives 2026 coefficients of 0.162 (HR/PA, t=4.9) and 0.159 (SB/PA, t=4.5) against 2025 coefficients of 0.597 and 0.650. It carries 2026 at roughly a quarter of 2025's weight, reproducing the earlier check that found loadings of 0.107 against 0.45. Blending 2026 actuals in therefore double-counts mildly, which is a reason the blend curve flattens above 0.5 rather than a reason to change it.

### 71. Two UI defects found by the first user pass over the #70 board
Josh opened the rebuilt app and asked two questions. Both were right, and the first was a bug this session introduced.

**1. The surplus column had no visible arithmetic.** Zach Neto showed `Production $19.98` and a 2027 surplus of `$40.98`, which reads as broken. It is not: the surplus runs off `keep_value` ($41.98), not `production_value`, since #70 moved the keep decision to the opportunity-cost scale. The two scales differ because the league withholds ~100 keepers, so the real 2027 auction sells about 126 lots for about $1,765 and a roto point costs $10.00 there against $6.21 on the full-redraft scale.

The board showed one scale and computed the decision on the other, with nothing on screen connecting them. Worse, the `Surplus '27` tooltip still read **"Production $ minus cost"**, which #70 made false and did not update: the app was stating arithmetic that does not reproduce its own number. Fixed by adding a `Replace $` column (`keep_value`, already in the payload), spelling the subtraction out in the drawer, and correcting both surplus tooltips. The phone CSS `nth-child` hide-list was re-counted for the inserted column, which shifts everything from `likely range` onward by one; `Replace $` stays visible on a phone because it is the number the decision is made on.

**Rule this establishes:** a change to `KEEP_BASIS` or `POOL_RULE` is not done when the tests pass. The app states the arithmetic in prose and the prose is not covered by `app/verify.mjs`.

**2. Standings and Contention were not redundant, but were indistinguishable.** Standings was a point estimate (roll rosters forward, re-rank, show per-category detail); Contention was a Monte Carlo reporting how often each team finishes in the money. Those answer different questions, and the difference matters because the league pays 50/25/15/breakeven, so two teams tied on projected points can have very different odds depending on roster volatility. That was the whole reason Contention was built.

But both rendered a ten-row team table with a projection, and a reader could not tell them apart. Merged into one Standings tab with **money odds as the second column, ahead of projected points**, so the ordering encodes which number decides something. The per-place columns (`P(1st)`, `P(2nd)`, ...) came across; the 2026/2027 scope folded into the existing season picker; the table now defaults to sorting by money odds. `app/verify.mjs` gained a check that the odds column leads both standings seasons and that the Contention tab is gone, replacing the check that tested the removed tab.

**What this costs.** One less place to look, and the odds are now one column among many rather than a view of their own. The mitigation is position: first after the team name, with the point estimate demoted to context behind it.

### 72. A user challenge to two suspicious numbers: both hold, and the reliability discount is vindicated
Josh read the rebuilt board and challenged two figures on Michael Wacha, plus asked for the header strip to go. No code error was found, but the audit produced one new empirical result and localises the disagreement precisely.

**The ERA question, and the premise correction.** The board showed Wacha at 2.52 roto points with `rp_ERA = -1.66`, against a 2026 year-to-date ERA of 3.36. Those are different quantities: the board is a **2027 projection**, and it projects Wacha at a **4.27 ERA**, not 3.36. Against a league-average fantasy staff at 3.613 that is correctly negative.

The 4.27 is essentially ZiPS's own number. The blend gives a pitcher's own prior-season earned runs only **11.9%** weight (`0.50` sample-size cap times `RELIABILITY["ER"] = 0.176 / REL_MAX = 0.739`), so the projection is 88% ZiPS's 4.383 and 12% his recent 3.43 form. ZiPS marks him up 1.02 runs over his 2026 ERA, the 85th percentile of markups among the 116 pitchers with 100+ IP in 2026, where the median markup is +0.17. He turns 36 in 2027. **This is ZiPS regressing an aging pitcher who has outperformed, not an arithmetic fault.**

**The ERA scorer itself was validated end to end.** Mean `rp_ERA` by projected-ERA bucket for starters at 120+ IP: 2.39, 1.05, 0.29, -0.38, -1.04, -1.95. Monotonic, and the zero crossing sits between the buckets centred on 3.498 and 3.769, which brackets the 3.613 baseline exactly as the formula requires. Skubal at a 2.69 ERA scores +2.64.

**New result: trusting a pitcher's recent ERA more would have made WORSE decisions.** The obvious response to the above is that 11.9% is too little weight on a full season. That is now testable. Sweeping `RELIABILITY` as `REL_MAX x (r / REL_MAX) ** alpha`, where `alpha = 1` is production and `alpha = 0` removes the discount entirely, and scoring on captured keeper surplus (#69's metric):

| alpha | 2024 | 2025 | 2026 | mean |
|---|---|---|---|---|
| 0.00 (no discount) | 162.2 | 15.7 | 110.3 | 96.1 |
| 0.50 | 146.0 | 14.7 | 111.3 | 90.7 |
| **1.00 (production)** | 146.0 | 21.5 | 127.3 | **98.3** |
| 1.50 | 146.0 | 24.5 | 86.3 | 85.6 |
| 2.00 | 146.0 | -1.0 | 74.4 | 73.1 |

Production is the maximum. The curve is flat between 0 and 1 and falls off above it, so the discount is not doing much harm in either direction, but there is **no evidence it should be relaxed**. Same caveat as #70: this runs on the Marcel path, and Marcel already averages three prior seasons internally, so the prior-season blend carries less here than it would against ZiPS. Read the shape.

**The wins question, and it runs the other way.** Wacha's 9.55 projected wins score 2.70 roto points, implying 3.54 wins per standings place, which Josh read as too generous. Tested directly by adding 10 wins to each of the 30 team-seasons in 2024-2026 and counting places actually climbed: **the mean is 3.27 places, against the model's 2.82.** Team win totals are tightly bunched (2026: 62, 72, 72, 74, 77, 79, 79, 82, 87, 91), so wins are a higher-leverage category than they look and **the model is conservative, not generous**. The same test on ERA gives 3.83 places for a 0.20 improvement against the model's 4.64, so ERA is mildly aggressive in the other direction. Both are inside the year-to-year spread of the raw estimators (W range/9 runs 3.22 to 5.22 across the three seasons).

**Header strip removed.** `10-team 5x5 roto keeper auction - $260/team - built ... - $/roto pt - projected auction inflation` sat above every tab. It restated league rules the only user already knows and two constants that mean nothing without their definitions, which are on the Home tab where there is room for them. The `#hdr` element is gone rather than blanked, so it leaves no gap.

**What this changes about the plan.** Nothing was wrong, and that is itself the finding: the scale, the denominators and the blend weights have now each been challenged and held. The disagreement that remains is with **ZiPS's projection of a 36-year-old**, which is exactly the binding constraint #69 identified. A user who thinks ZiPS is wrong about Wacha should say so in the Intuition tab rather than expect the valuation layer to disagree on his behalf.

### 73. The board shows a projection with nothing beside it, so `Roto '26` ships
Josh's request, and the right diagnosis of #72. He read Wacha's `rp_ERA = -1.66` as a scoring fault because the only number on screen was a 2027 projection with no 2026 reference next to it. Once the two sit side by side the case answers itself: **Wacha produced 7.11 roto points in 2026 and is projected for 2.52 in 2027.** The argument is with a -4.59 projection move, not with the ERA formula. No valuation changed; the board gains one column.

**What the column is.** `roto_2026` is the full 2026 season, banked actuals plus the ZiPS rest-of-season projection for the weeks still to play, converted to roto points. That line is not new: it is exactly the projection's own **source A**, previously built inline inside `project_hitters` and `project_pitchers` and thrown away. It is now `project.lines_2026_hitters()` / `lines_2026_pitchers()`, called by both the projection and the new scorer, so there is one definition. The board was verified **byte-identical across that refactor**: zero difference on all 58 numeric columns.

**The scale decision, which is the only real choice here.** `roto_2026` is scored with the **2027** scorer, not 2026's. The column exists to be read across against `Roto '27` and subtracted from it, and two numbers on different denominators cannot be. So it means "his 2026 production, valued in 2027 money" and it will not tie out against the 2026 standings, which the Standings tab already shows. Stated in the tooltip rather than left to be discovered.

**It is immediately legible, which is the test a diagnostic column has to pass.** Largest projected declines: Misiorowski 17.17 to 7.32, Schlittler 15.14 to 6.31, Eduardo Rodriguez 9.66 to 2.13, Sale 14.23 to 6.83. Largest improvements: Crochet -0.25 to 7.92, Greene -0.78 to 4.86, Senga -2.86 to 1.97, Strider 0.23 to 4.57. Every large decline is a pitcher who just had an unsustainable season and every large improvement is one who was hurt or ineffective. That is what regression to the mean is supposed to look like, and until now none of it was visible. Median move -0.48, mean -0.62.

**Placement.** `Roto '26` sits immediately left of the 2027 figure, which is renamed `Roto '27` because "Roto pts" no longer identifies which season. On a phone BOTH roto columns are hidden, as `Roto pts` always was, and the drawer carries the comparison instead as three lines (2026 production, 2027 projection, what the projection does) where a narrow screen has room. The phone CSS `nth-child` hide-list was re-counted for the second time in two sessions; it is now up to nine indices and is the standing hazard of adding a board column.

**Why this matters more than one column suggests.** #69 found the model's binding constraint is the projection rather than the valuation machinery, and #72 found the only live disagreement is with ZiPS's read of a 36-year-old. Both are arguments about the 2027 line. The board previously offered no way to see that line as a MOVE from something, so every such argument arrived as a suspected arithmetic bug. `Roto '27 - Roto '26` is the projection's opinion made explicit, and it is the number to disagree with.

### 74. `Roto '26` moves to 2026's own scale, and the difference gets its own column
Josh corrected the scale decision in #73 and he is right. #73 scored 2026 production on the 2027 scale, arguing the two columns had to share denominators to be subtractable. That argument is wrong, and the reason is worth stating because it governs every cross-season comparison this project will make.

**A roto point is a standings place.** Dividing each category by its own season's denominator is precisely the operation that makes a 2026 home run and a 2027 home run commensurable. The output unit is already common. So each season's production belongs on its own season's scale, the two columns still subtract, and the difference becomes a statement about the PLAYER rather than a statement about which denominators were used. Scoring 2026 production against 2027 denominators was a hybrid that was less accurate about 2026 and bought nothing.

**The complication, and how it is handled.** The 2026 standings are a partial season, so scoring a full-season line against them would inflate every counting category by the missing fraction. `project.season_completion_2026()` estimates the fraction banked as playing time to date over playing time for the whole season, restricted to players who actually have a 2026 line: **0.8849 for hitters, 0.8789 for pitchers**. `board.scorer_2026_full()` divides the counting levels and the team volume baselines by it and leaves AVG, ERA and WHIP alone, since rates do not accumulate.

The estimate is corroborated by the levels themselves. 2026 sits at 0.895, 0.916, 0.893, 0.885 and 0.907 of the 2024-25 mean for HR, R, RBI, W and K, which brackets 0.88. It sits at 0.798 and 0.800 for SB and SV, and that is **genuine league drift, not unplayed games** -- the estimator correctly does not absorb it, which a naive "scale everything by the observed level ratio" approach would have.

**Validated by an invariance that has to hold.** Roto points are scale-invariant when numerator and denominator move together, so a full-season line on a full-season scale must agree with a to-date line on a to-date scale. Across 1,445 players: **median difference -0.009, mean -0.022, correlation 0.9975.** The small negative residual on stars (Ohtani -0.85, Misiorowski -1.25) is correct and expected: ZiPS regresses their rates over the remaining weeks, so a projected full season is slightly worse per unit than their pace to date.

**`Move` ships as its own column.** Josh: "the difference is quite key." `roto_move = roto_points - roto_2026`, sortable, sitting immediately right of the pair. It answers the question the trio exists for: which players does the model most disagree with the present about?

| | Roto '26 | Roto '27 | Move |
|---|---|---|---|
| Misiorowski | 17.25 | 7.32 | **-9.93** |
| Schlittler | 15.32 | 6.31 | -9.01 |
| Eduardo Rodriguez | 10.04 | 2.13 | -7.91 |
| Sale | 14.40 | 6.83 | -7.56 |
| Wacha | 7.59 | 2.52 | **-5.07** |
| Strider | 0.42 | 4.57 | +4.16 |
| Senga | -2.32 | 1.97 | +4.29 |
| Greene | -0.61 | 4.86 | +5.47 |
| Crochet | -0.07 | 7.92 | **+7.99** |

Every large decline is a pitcher coming off an unsustainable season and every large gain is one who was hurt or ineffective, which is what regression to the mean should look like and none of which was visible two sessions ago.

**Dollars stay in their own columns.** Josh: "estimating the value of 27 dollars accurately is nice, but not the main point." `Roto '26`, `Roto '27` and `Move` are roto points and nothing else; `Production $`, `Market $` and `Replace $` are the dollar columns and are separate. The #73 tooltip phrase "valued in 2027 money" was doubly wrong, since the scale question is about denominators rather than dollars, and it is gone.

**Phone layout.** `Move` is VISIBLE on a phone, the only member of the trio that is: it stands alone without its two parents, where a bare `Roto '26` does not. Both roto columns stay hidden as `Roto pts` always was, and the drawer carries all three lines. Third `nth-child` re-count in three sessions; the hide-list is now nine indices and adding a board column without re-counting it is the standing hazard.

### 75. The board's headers and its cells are two lists, and they silently drifted apart twice
A rendering bug, shipped twice, found by the reader both times. No valuation was wrong: every number in `out/keeper_board_2027.csv` was correct throughout. The board simply printed them under the wrong headings.

**The mechanism.** `boardView()` builds the header row by mapping over `BOARD_COLS`. `playerRow()` builds the cells as a hand-written positional list of `<td>` elements. Nothing links the two. Insert a column into `BOARD_COLS` without inserting the matching cell into `playerRow`, and every column to the right of the insertion renders one field too far left, under a heading that belongs to its neighbour.

It happened on `Replace $` (#70) and again on the `Roto '26` / `Move` pair (#74), for three headers with no cells. What the reader saw on Max Clark:

| heading | showed | should have shown |
|---|---|---|
| `Roto '26` | 4.3 | 1.7 (it was rendering `roto_points`) |
| `Roto '27` | $20 | 4.3 (it was rendering `salary`) |
| `Move` | 2 | +2.6 (it was rendering `contract`, hence the integers) |

"Why is Move only ever an integer" was the sharpest clue in the report: contract years are 1, 2, 3 or F. A dollar sign appearing in a roto-point column was the other. Both tabs that use `boardView` were affected, the keeper board and free agents.

**Why nothing caught it.** `app/verify.mjs` had 15 checks and none of them read a rendered board cell. The check added in #71 compared HEADER text and passed, because the headers were right; it was the cells underneath that had moved. `JS matches pandas on all 25 quantities` passed too, because it compares computed values in the payload, never what is drawn. **The app was verified everywhere except the one place a reader actually looks.**

**Two guards, because one was clearly not enough.**
1. `assertBoardRowShape()` throws on render if `playerRow` emits a different number of cells than `BOARD_COLS` declares. That turns a silent visual corruption into a loud failure.
2. `app/verify.mjs` now renders a real row and compares the cell TEXT, column by column, against the payload run through the app's own formatters (`nf`, `sgn`, `usd`, `money`). Formatter-based comparison rather than numeric tolerance, because a misaligned column shows a different field entirely and an exact string check cannot be defeated by rounding. Confirmed to fail on the broken build and pass on the fixed one; the suite is now 16 checks.

**The rule.** Adding a board column means four edits, not one: `BOARD_FIELDS` in `scripts/build_app.py`, `BOARD_COLS`, a `<td>` in `playerRow` at the same index, and the phone CSS `nth-child` hide-list. Three of the four are silent when forgotten. #70 and #74 each forgot the third.

**Standing back.** Three of the four defects a reader found in this app today were in the presentation layer rather than the model: a tooltip describing arithmetic the model no longer used (#71), two tabs that were distinct but looked identical (#71), and this. The engine has 64 tests and a 25-quantity JS/pandas cross-check; the layer that decides what a number MEANS to the person reading it had almost none. That is the coverage gap worth closing next, not another valuation refinement.

### 76. The tooltip pass: a contract, a decomposition, and the first tests this layer has had
Josh's ask after four reader-found defects in two sessions, three of them in the presentation layer rather than the model. Prose rewrite plus one real feature. No valuation changed.

**What was wrong, measured rather than asserted.** 46 user-facing strings were extracted and scanned. Four carried internal references into the UI (`docs/FINDINGS.md #26` twice, `docs/METHODS.md section 2.1`, `klab/standings_sim.py`), which is a leak of the repo's own bookkeeping into a product surface. Undefined jargon included "bootstrap draws", "replacement level", "denominator", "walk-year", "dispersion estimate" and "roto points" itself, which was used throughout without ever being glossed. Several entries ran 85 words or more.

**A contract, written into the code above `COL_HELP` so it survives the next edit.**
1. First sentence says what the number IS, in words a person who has never read a baseball stats site would understand, under about 15 words.
2. At most two more sentences: how to read it, or the one caveat that would mislead. Not the derivation.
3. No unglossed jargon. "Roto points" is always "places in the standings". Never "replacement level", "bootstrap", "denominator", or a bare "ZiPS".
4. Never a file or finding reference.
5. If a number needs a breakdown to be believed, the CELL carries the evidence and the HEADER carries the explanation.

**The feature, which is the part that matters: value decomposition.** The board showed totals and could not answer "is this coming from homers or steals". It can now, because the per-category split for 2026 was being computed and discarded. `roto_2026_lines()` keeps `rp_<cat>_26` alongside the total; naming them with the `rp_` prefix means `project_all_players` sums them for two-way players automatically. Hovering a value cell gives the split, sorted biggest-first, with the categories spelled out and zero rows dropped:

```
His 2026 season, 7.6 points, comes from:
  strikeouts   +3.0  ████████
  wins         +2.8  ████████
  ERA          +0.9  ██
  WHIP         +0.9  ██
```

**The `Move` tooltip is the one that pays.** It shows both seasons side by side, sorted by the size of the change, and it answers the question that started this whole thread (#72, #73, #74) in four lines:

```
What the 2027 projection changes:
              2026    2027   change
  ERA           0.9    -1.7     -2.6
  WHIP          0.9    -0.9     -1.7
  strikeouts    3.0     2.4     -0.6
  wins          2.8     2.7     -0.1
```

Wacha's whole -5.07 is ERA and WHIP. A reader can now see that in a hover instead of asking whether the ERA formula is broken.

**Three tests, because this layer had none.** `app/verify.mjs` gains a check that every board column has non-empty help, that no element's `title` contains an internal reference, and that the per-category breakdown SUMS to the total it claims to explain (within the slack from 1dp rounding and dropped near-zero rows). Confirmed to fail on a deliberately reintroduced blank tooltip and a deliberately reintroduced `docs/` reference before being accepted. The suite is now 17 checks, up from 15 at the start of the day.

**What is deliberately not done.** Native `title` tooltips render in a proportional font, so the bars are a rough magnitude cue rather than an aligned chart, and they do not exist at all on a phone. A real hover card would fix both and is a bigger change; the drawer already carries the same information for touch, so the gap is cosmetic on desktop and covered on mobile. Flagged rather than built.
