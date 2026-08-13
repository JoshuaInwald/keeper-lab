> **Superseded — kept for history.** This is the planning doc written before
> the valuation engine existed: the agreed methodology, the league rules as
> first understood, and the data inventory at that point. For current state
> read `HANDOFF.md`, `LAB_NOTEBOOK.md`, and `FINDINGS.md` instead — several
> calls made here (e.g. contract-code semantics in §2, Streamlit as the app
> plan in §8) were later found wrong or changed; see those files for what
> actually shipped and why. Moved here from `data/HANDOFF.md`, which isn't in
> git, on 2026-08-13 so it wouldn't be lost.

# Keeper League Lab — Project Handoff

**Status:** Data layer substantially expanded; **valuation engine not yet built** — methodology agreed, implementation next.
**Owner:** Josh (Legends League, CBS, 10-team 5×5 roto keeper auction).
**Last updated:** 2026-08-13 — data collection complete (keepers 2022–2026, drafts 2022–2025, standings 2022–2026, FG stats 2022–2026). Valuation engine next.

---

## 1. Project goals (what Josh actually wants)

Build a keeper-league analytics tool that is both **useful for real decisions** and a **portfolio piece for job interviews** (Python + DuckDB + Streamlit).

Concrete features, roughly in priority order:
1. **Player/contract valuation grounded in *this* league** — what a draft dollar actually buys in roto points, derived from historical auction data and league standings.
2. **Keeper decisions** — who to keep/extend vs. cut, by surplus (dollar value − keeper cost) for 2027.
3. **Trade calculator** — live changes in expected category totals + standings points + value/surplus for each side.
4. **Backward-looking value attribution** — where each team's production came from (draft vs. waiver vs. trade), and how efficiently owners convert draft $ into production. (Phase 2.)
5. **Historical roster reconstruction** — from transaction logs, show rosters at any point in history. (Phase 2.)
6. **Dynamic** — refreshes with new projections + in-season performance.

**Josh's framing that must shape the model:**
- He is currently a **rebuilder**: shedding expensive expiring veterans, loading cheap controllable talent for next season. Future surplus matters more than 2026 win-now production; the tool should support a "contention weight."
- Value must reflect **what a draft dollar actually buys at auction** (accounting for wasted dollars on busts/IL/releases), not a theoretical SGP ideal.
- Value primitive = **marginal roto points** ("how much roto score does one more HR/SB/W contribute"), converted to dollars via auction regression.

**Coding preferences:** Python-first, DuckDB, Streamlit. Keep it auditable.

---

## 2. League rules that drive the math (from the constitution)

- 10 teams, auction, **$260/team** budget. League switched from NL-only to all-MLB in 2021; no keepers in 2021 (inaugural all-MLB draft); first keeper year = 2022.
- **2021 franchise names:** Hard 8's → New York Polar Bears; Schmets → Milwaukee Beers → Wax Kandels → NPB No Stars. See `franchise_map.csv`.
- Active roster **23** = C,1B,2B,3B,SS,CI,MI,5×OF,2×UTIL (**14 hitters**) + **9 pitchers**; plus a reserve (minors/IL) list.
- 5×5 categories: **R, HR, RBI, SB, AVG** (hit) · **W, SV, K, ERA, WHIP** (pitch). Lower is better for ERA/WHIP.
- **Keepers:** 3-year contracts; salary set at auction. Extend a player in their **final year** for **+$5/yr** (once per contract, max +2 yrs = +$10). For MVP purposes, model extensions as **+1 year at salary+$5**.
- **Contract year interpretation:** 1 = two more years at current salary (keepable); 2 = one more year (keepable); 3/F = final year, must extend at +$5 to keep, otherwise walks to free agency. F players who aren't extended are **not keeper candidates**.
- Keep **6–13** players.
- **FA acquisition salary:** $10 before the All-Star break, $20 after.
- IL/reserve players contribute 0.

---

## 3. Current status — what works and what doesn't

### Works (trust these)
- **Historical standings: 5 full seasons** (2022–2026). 2026 is in-progress (~70% season); 2022–2025 are complete.
- **FanGraphs player stats: 2022–2026** for all MLB hitters and pitchers. Counting stats derived from rate stats where FG export lacked raw columns (AB ≈ PA×0.91; K, ER, BB derived from rate×IP). Approximations are fine for roto calcs since AVG/ERA/WHIP are exact.
- **Draft auction data: 2023–2026** (parsed per-year CSVs with team pick order). 2024–2026 also have FG IDs matched in `draft_salaries_all.csv`.
- **Authoritative salaries + contracts** parsed from the CBS contracts dump (`contracts_raw.txt`). This is correct; the earlier draft-history salary reconstruction was **wrong** (missed extensions) — do not use it for current salary.
- **ZiPS projections** for ROS 2026, full-year 2027, full-year 2028.
- **App scaffold** (Streamlit) in `keeper-league-lab.zip`: trade calculator, keeper board, player values, standings — all wired, but valuations are not yet reliable.

### Does NOT work / not yet built
- **The valuation engine.** Prior session's SGP calibration was broken at every stage (see §6 error ledger). New methodology agreed (see §4) but not yet implemented.
- All dollar values, surplus numbers, keeper board rankings, and trade calculator magnitudes from the prior session are **not trustworthy**.

---

## 4. Agreed valuation methodology (the plan)

### Step 1: Denominator estimation (marginal roto points per stat unit)
From 5 years of historical standings (2022–2025 complete seasons only):
- For each category, compute the denominator = (max − min) / (N − 1) per year, where N = number of competing teams.
- **Saves:** exclude teams that punt saves (SV < 15) before computing the SV denominator.
- **SB:** weight post-2022 years more heavily (MLB stolen base rule change in 2023 created a regime shift).
- Assess stability across years. Use multi-year average for stable categories; for unstable ones, consider weighting recent years or using the auction regression to cross-check.

### Step 2: Rate stat conversion
- AVG/ERA/WHIP can't be divided by a denominator directly. Convert to counting-equivalent marginal impact using **league-average team PA/IP** per roster slot.
- Assume each hitter roster slot contributes `league_avg_PA / 14` and each pitcher slot contributes `league_avg_IP / 9`. Imperfect but good enough for v1.

### Step 3: Auction regression (dollars per roto point)
- Pair each drafted player's auction price with their actual season production (roto points computed via Step 1 denominators).
- Fit `roto_points ~ draft_$` — the slope = roto points per dollar. The inverse = dollars per roto point.
- **Key:** this naturally absorbs bust/IL waste. A $30 player who produces 0 pulls the slope down = the real, waste-adjusted exchange rate.
- Run multiple specifications:
  - Full sample (all drafted players incl. keepers) vs. auction-only (excluding keepers)
  - Bucketed by price tier ($1-5, $6-15, $16-30, $31+) and by fantasy value tier
  - With/without weighting by draft price
  - Log and semi-log transforms
- Assess whether $/point is constant across the price spectrum or if there's a scarcity premium for elite players.

### Step 4: 2027 player projections
- For each player, blend 50/50: (a) projected 2026 full-season (actuals-to-date + ROS ZiPS) and (b) ZiPS 2027 pre-season projection.
- Apply blending at the **rate × playing-time** level, not raw counting stats (to avoid double-counting PT suppression in ZiPS).
- Compute roto points using 2027-rescaled denominators (historical denominators adjusted proportionally to ZiPS 2027 league-wide stat levels).

### Step 5: Dollar value + keeper surplus
- Dollar value = projected roto points × ($/point from auction regression).
- Keeper cost = current salary for contract years 1–2; salary + $5 for extension candidates (year 3/F).
- F players who aren't extended = not keeper candidates.
- Surplus = dollar value − keeper cost. Rank keepers by surplus.

### Step 6: Sanity check
- Validate against **Pookie 2.0's roster** (leading the league in 2026) — model should explain their standings position.
- Hand-check ~10 known players spanning the value spectrum before presenting any numbers.

### Deferred (Phase 2)
- 3-year keeper horizon (aging curves, discount rate, contention weight for multi-year surplus).
- Waiver wire value decomposition (how much free production comes from mid-season pickups per team-year; how that affects replacement level and keeper strategy).
- Historical roster reconstruction from transaction logs.
- Draft order analysis (when teams spend, value by pick position).

---

## 5. Data & file guide

All paths are in **`/Users/JoshInwald/Documents/Fantasy Baseball/`**.

### Source data (from Josh / CBS / FanGraphs)
| File | What it is | Notes |
|---|---|---|
| `Legends Fantasy Baseball Constitution V2.docx` | League rules | Canonical rules source |
| `legends_league_v14.xlsx` | Josh's prior model | Projections, rosters (no salaries), FA pool; z-score $ values |
| `fg_2026_hitters.csv` / `_pitchers.csv` | 2026 actuals to date | Reduced export: AB/H derived for hitters; K/ER/BB/H derived for pitchers |
| `fg_ros_hitters.csv` / `_pitchers.csv` | ZiPS ROS 2026 | Rich format, full components. Updates in-season. |
| `fg_zips_dc_2027_*` / `_2028_*` | ZiPS multi-year | **Regressed + PT-suppressed** — use as aging signal, not raw value |
| `fg_hitters_2022_2026.csv` | **All FG hitter stats 2022–2026** | 7,249 player-seasons. AB/H approximated from PA×0.91 and AVG. |
| `fg_pitchers_2022_2026.csv` | **All FG pitcher stats 2022–2026** | 4,255 player-seasons. K/ER/BB/H derived from rate stats × IP. |
| `contracts_raw.txt` | **Authoritative** current salary + contract year | 1/2/3/F interpretation confirmed (see §2) |

### Standings data
| File | What it is | Notes |
|---|---|---|
| `standings_2022.csv` through `standings_2026.csv` | Wide-format per year | 2026 is in-progress (~70% season) |
| `standings_long_all.csv` | Tidy long format, all 5 years | Best file for denominator computation |

### Draft data
| File | What it is | Notes |
|---|---|---|
| `draft_2021.csv` | 2021 auction results (inaugural all-MLB draft) | 10 teams, with team pick order. **Not used in valuation model** — no standings/keeper data for 2021. Useful for team tendency analysis. |
| `draft_2022.csv` | 2022 auction results | 137 picks, 10 teams, with team pick order |
| `draft_2023.csv` | 2023 auction results | 136 picks, 10 teams, with team pick order |
| `draft_2024.csv` | 2024 auction results | 163 picks, 10 teams, with team pick order |
| `draft_2025.csv` | 2025 auction results | 129 picks, 10 teams, with team pick order |
| `draft_salaries_all.csv` | Combined 2024–2026 with FG IDs | From prior session; authoritative for ID matching |

### Derived files (from prior session — in `keeper-league-lab.zip`)
| File | Trust |
|---|---|
| `rosters_current.csv` | Good; ~9 leans + 2 Contreras flagged |
| `contracts_parsed.csv` | Good for current salaries |
| `rosters_valued.csv` | Salaries good; dollar values/surplus **not trustworthy** |
| `league_report.html` | **Numbers unreliable** — rebuild after valuation is fixed |

### Keeper data
| File | What it is | Notes |
|---|---|---|
| `keepers_2022.csv` | 2022 keepers | 25 keepers, 10 teams (McBlocks, NPB No Stars, Fighting Phils had 0). First year with keepers (league switched from NL-only to all-MLB in 2021, no keepers in 2021). |
| `keepers_2023.csv` | 2023 keepers | 28 keepers, 10 teams (NPB No Stars + Fighting Phils had 0) |
| `keepers_2024.csv` | 2024 keepers | 29 keepers |
| `keepers_2025.csv` | 2025 keepers | 29 keepers |
| `keepers_2026.csv` | 2026 keepers | 100 keepers |
| `franchise_map.csv` | Team name → franchise ID mapping | CBS retroactively applies current names to historical keeper pages |

**Note:** Keeper CSVs have player names only — no salary column. Must join with contracts/draft data to determine keeper costs. CBS uses current team names even on historical pages; franchise_map.csv resolves this.

### Data still needed (nice-to-have, not blocking MVP)
1. **Draft order** (true nomination/bidding sequence, not just by-team listing) — nice to have for draft strategy analysis but not blocking.
2. **Transaction logs** (2022–2026) — Phase 2, for roster reconstruction and waiver value attribution.
3. **Keeper salaries** will be derived by joining keeper lists with draft/contracts data programmatically — no additional raw data needed from CBS.

---

## 6. Error ledger — what the prior session got wrong

1. **Denominator = stdev of projected roster roll-ups.** Should be standings-gap slope. Result: counting denominators ~4.7× too large.
2. **Featured raw ZiPS 2027 as "keeper value."** PT-suppressed → Yordán Álvarez valued at $4 (he's a league leader). Use true-talent, not raw out-year projections.
3. **Asserted a diagnosis without verifying** (claimed league AVG baseline was .225; it was .245). Verify every constant before explaining it.
4. **Claimed 1 SB > 1 HR in value** using in-progress 2026 season; on full seasons HR ≈ 1.6× a SB. Never derive full-season denominators from a partial season.
5. **Salary reconstruction from draft history** missed pre-draft extensions (had Skubal at $23; real is $38/3yr). Superseded by `contracts_raw.txt`.
6. **Two-way Ohtani** shares one FG ID across hitter/pitcher files — dedup needed (handled, but watch for it).

**Meta-lesson:** Value a known set of players first, eyeball against domain knowledge, and decompose any surprise **before** presenting numbers.

---

## 7. Key observations from the data

- **Saves punt pattern:** NY Polar Bears at 0 SV in 2022, 2023, 2024, 2025. Phenoms at 0 SV in 2024. Always exclude SV < 15 teams from the SV denominator.
- **SB regime change:** 2022 leader had 141 SB; 2023+ leaders at 250–270. MLB stolen base rule change. Weight 2023+ for SB denominators.
- **Tank/rebuild teams create outliers:** Phenoms 2024 (178 HR, 651 R), Wax Kandels 2025 (232 HR), The Metropolis 2025 (846 K). These compress denominators — consider trimming or using median-based methods.
- **ERA/WHIP league-wide shift:** 2022–2023 had higher ERA (best team ~2.87–3.71) vs. 2024–2025 (~3.44–3.48). Tracks MLB run environment. Denominators for rate stats should be relatively stable in roto-point terms even with level shifts.
- **Team turnover:** Who's On First (2022) → Micks (2023) → gone by 2024. Milwaukee Beers → Wax Kandels. Phenoms → The Metropolis. Team identity changes don't affect the math.
- **Draft spending varies widely:** Teams spend $106–$235 in the draft, with the rest on keepers ($25–$154). This is the keeper vs. auction split needed for the regression.

---

## 8. Code structure (in `keeper-league-lab.zip`)

```
klab/config.py      league constants (14H/9P, $260, keeper economics) — all knobs
klab/ingest.py      load FG CSVs (rich + reduced) → normalized stats
klab/valuation.py   SGP engine (denominators, replacement, $ conversion) ← needs rebuild per §4
klab/league.py      standings, roto points, trade deltas
klab/contracts.py   parse contracts_raw.txt → authoritative salary+contract
klab/db.py          DuckDB connect/schema
db/schema.sql       tables (stats keep raw components)
db/build.py         orchestrator → db/keeper.duckdb
db/build_report.py  static HTML report
app/streamlit_app.py  UI
```
Run: `pip install -r requirements.txt` → `python db/build.py` → `streamlit run app/streamlit_app.py`.

---

## 9. Next steps (agreed, in order)

1. **~~Collect remaining data~~** ✅ Complete. Keepers 2022–2026, drafts 2021–2025, standings 2022–2026, FG stats 2022–2026. 2021 was inaugural all-MLB draft (no keepers, no standings data). 2021 draft saved for team tendency analysis but excluded from valuation model.
2. **Denominator analysis:** compute per-category denominators across 5 years, assess stability, settle on averaging/weighting method. Trim saves punters, weight post-rule-change for SB.
3. **Auction regression:** pair draft prices with player production, compute roto points, run the regression battery (full sample, auction-only, bucketed, weighted, log-transformed). Extract empirical $/roto-point conversion rate.
4. **2027 player projections:** 50/50 blend of (2026 actuals+ROS) and ZiPS 2027 at rate×PT level → roto points via 2027-rescaled denominators → dollar value.
5. **Keeper board:** surplus = dollar value − keeper cost. Rank keepers.
6. **Sanity check:** validate against Pookie 2.0's roster + hand-check 10 known players.
7. **Rebuild app/report** with trustworthy numbers.

---

## 10. How to start the next session

Paste this at the top of a new chat (on the stronger model):

> Read HANDOFF.md in `/Users/JoshInwald/Documents/Fantasy Baseball/`. All data collection is done — proceed directly to Step 2 (denominator analysis). Compute denominators, then move through Steps 3–6 of §4, sanity-checking at each stage before moving on. Show me the denominator table and auction regression results before computing player values.
