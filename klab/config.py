"""League constants for the Legends Fantasy Baseball keeper league.

Every knob that drives the valuation lives here. Nothing downstream should
hard-code a league rule.
"""

import os
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(exist_ok=True)

# --- League structure -------------------------------------------------------
N_TEAMS = 10
BUDGET = 260
N_HIT_SLOTS = 14          # C,1B,2B,3B,SS,CI,MI,5xOF,2xUTIL
N_PIT_SLOTS = 9
N_ACTIVE = N_HIT_SLOTS + N_PIT_SLOTS

# Standings payout: 50/25/15% of the pot for 1st-3rd, buy-in back for 4th
# (shipped as flat top-2 once, docs/FINDINGS.md #55). PAYOUT_SPOTS is the
# count of places that pay at all; the weighting is not modeled yet (ROADMAP Phase 5).
PAYOUT_SPOTS = 4
PAYOUT_SHARE = {1: 0.50, 2: 0.25, 3: 0.15, 4: 0.0}   # 4th = buy-in back, not a pot share

HIT_CATS = ["R", "HR", "RBI", "SB", "AVG"]
PIT_CATS = ["W", "SV", "K", "ERA", "WHIP"]
CATS = HIT_CATS + PIT_CATS
NEG_CATS = {"ERA", "WHIP"}          # lower is better

# --- Keeper economics -------------------------------------------------------
EXTENSION_COST = 5        # +$5/yr to extend a player in his final year
MIN_KEEPERS = 6
MAX_KEEPERS = 13
FA_SALARY_PRE_ASB = 10
FA_SALARY_POST_ASB = 20

# Contract code = seasons remaining AFTER the current one (the old handoff
# had this backwards, understating every multi-year deal by a season):
#   "3" -> 2027, 2028, 2029 at current salary (only reachable via extension)
#   "2" -> 2027, 2028;  "1" -> 2027 only
#   "F" -> confirmed unrestricted free agent after 2026. NOT extendable.
# "F" = gone, never "pay $5 to keep him" (docs/FINDINGS.md #39): the extension
# window closes before a player's own walk-year draft, so an F in this
# mid-2026 snapshot already missed it. The only live extension decision is
# for a code-"1" player (klab/keeper.py::multiyear_surplus's `live` branch).
YEARS_REMAINING = {"1": 1, "2": 2, "3": 3}
EXTENSION_REQUIRED = {"F"}
# Constitution (Keeper Eligibility): +$5 PER YEAR, owner chooses 1 or 2 years;
# "Players can only be extended once per contract".
EXTENSION_MAX_YEARS = 2
# Extra-constitutional ruling: the league agreed Ohtani is not extendable.
# Not derivable from any file, so it lives here as an explicit override.
NON_EXTENDABLE_NAMES = {"Shohei Ohtani"}

# A true two-way player is auctioned as two separate assets from the 2027
# auction on (Josh, 2026-08-15). Affects only the forward valuation path
# (klab.board.project_all_players / value_2028); klab.auction.score_season
# still sums his two lines into one realized past purchase.
TWO_WAY_SPLIT_NAMES = {"Shohei Ohtani"}

# Contracts the CBS export left unreadable, resolved by the commissioner.
# name -> (contract_code, salary). These are the only hand-entered contracts in
# the project; everything else is read from the export.
CONTRACT_OVERRIDES = {
    "Cam Smith": ("2", 1),          # waiver pickup, 2 years at $1
    "William Contreras": ("2", 11),
    "Jarren Duran": ("F", 1),       # kept 2026, not 2025 -- re-added at his
                                    # draft-year salary, extendable for 2027
}

# --- Keeper playing-time floor ---------------------------------------------
# Upside (_ft) value holds rates fixed and scales playing time to the floor,
# so ZiPS durability haircuts and rookie ramps don't bury a breakout.
KEEPER_PA_FLOOR = 600
KEEPER_IP_FLOOR = 150

# --- Rest-of-2026 projection basis (klab/trade.py) --------------------------
# ZiPS ROS is the default (docs/FINDINGS.md #45); these two only affect
# prorated_to_date_lines(), the "current pace" alternative. Team games
# played is estimated as the GAMES_PLAYED_PCTILE of G among PA > 300 hitters.
SEASON_GAMES = 162
GAMES_PLAYED_PCTILE = 0.95
KEEPER_SV_FLOOR = 25
KEEPER_RP_IP_FLOOR = 65
# Never extrapolate a player's playing time by more than this. Beyond it the
# projection is not evidence of a full-time role, it is a different player.
MAX_PT_SCALE = 2.0

# --- Multi-year horizon -----------------------------------------------------
# Surplus in year t+1 is worth less than surplus now: roster churn, injury,
# and drift in league conditions. Applied per season beyond 2027.
FUTURE_YEAR_DISCOUNT = 0.85

# --- Denominator estimation knobs ------------------------------------------
DENOM_SEASONS = [2024, 2025, 2026]   # regime changed in 2024
# 2026 is ~75% complete. Mean-normalising cancels the scale, not the sampling
# noise; the over-dispersed categories are measured per category (ERA, WHIP,
# SV), NOT "rate cats" -- AVG is fine and SV is not (docs/FINDINGS.md #26).
PARTIAL_SEASONS = {2026: 0.75}
PARTIAL_EXCLUDE_CATS = {"ERA", "WHIP", "SV"}
DENOM_EXCLUDE_PARTIAL_SEASON = True
# Teams below this SV total are punting saves and are dropped before
# computing the SV denominator (HANDOFF §7).
SV_PUNT_THRESHOLD = 15
# MLB stolen-base rule change landed in 2023; pre-regime SB seasons are skipped.
SB_REGIME_START = 2023

# Seasons whose auction results set the $/roto-point exchange rate. These
# auctions happened in different worlds: keepers removed ran 25/28/29/29 then
# 100 in 2026, and $/point tracks that count (r = 0.80), so pooling understates
# what a 2027 dollar will cost.
AUCTION_SEASONS = [2024, 2025, 2026]
KEEPERS_REMOVED = {2022: 25, 2023: 28, 2024: 29, 2025: 29, 2026: 100}
KEEPERS_EXPECTED_2027 = 100
# "pooled": straight fit on AUCTION_SEASONS. "keeper_adjusted" (default): fit
# $/pt on keeper count, predict at KEEPERS_EXPECTED_2027. "recent": 2026 alone.
EXCHANGE_BASIS = "keeper_adjusted"
# League level (mean team total) to build 2027 denominators against.
LEVEL_SEASONS = [2024, 2025]

# --- Waiver-wire value ------------------------------------------------------
# Replacement level = "the best player you can get for free". "low": the
# 230th-best projection (one per active slot). "medium": the 300th. "high":
# median 2026 production of actual FA pickups (5.04 rp) -- an ex-post upper
# bound, for sensitivity only. Higher replacement = every rostered player worth less.
WAIVER_VALUE = "low"
WAIVER_RANK = {"low": 230, "medium": 300}
WAIVER_HIGH_RP = 5.04

# Which pool the $2,600 identity is calibrated on, and how replacement is read
# off it. "blind": the top 230 by roto points regardless of role, which on a
# projection is 183 hitters and 47 pitchers, a set no ten teams could field
# (FINDINGS #65). "slot_role": the top 140 hitters and top 90 pitchers the
# league actually rosters, with replacement taken per role.
# Two independent lines chose slot_role: it reproduces perfect foresight on
# completed seasons where "blind" misses by 20 points (#68), and it makes
# better keep/cut calls out of sample (#69). It moves redraft_value, so it is
# a PRICING change; keep/cut runs off keep_value and does not see it (#69).
POOL_RULE = "slot_role"

# Which dollar scale the keep-or-cut decision compares against the keeper cost.
# "redraft": redraft_value, what he would fetch in a full redraft with no
# keepers withheld. "replacement": keep_value, what replacing him would cost at
# this league's auction, which is the market a keeper is actually traded
# against. Keeping at $S forgoes $S of budget, and $S buys intercept + S*slope
# roto points, so "replacement" is the identified comparison. Backtested at
# +$6.1 / +$124.6 / +$89.4 of captured surplus across 2024-2026 (FINDINGS #69).
KEEP_BASIS = "replacement"

# --- Positional adjustment --------------------------------------------------
# Full-spectrum positional adjustment is OFF and unimplemented (FanGraphs'
# 13-system test: largest adjustments finished last). Reported in settings only.
POSITIONAL_ADJUSTMENT = False

# Catcher/shortstop-only adjustment, the one wired into the app as a toggle
# (both variants ship every build; docs/FINDINGS.md #52). Needs
# data/fg_catchers_2026.csv and data/fg_shortstops_2026.csv.
TWO_POS_ADJUST = {"C", "SS"}
TWO_POS_SLOTS = {"C": 1, "SS": 1}   # dedicated roster slots per team

# --- Projection source ------------------------------------------------------
# Which files supply the out-year projection. Any export with FanGraphs' column
# names works -- Steamer, THE BAT, ATC, Depth Charts -- so switching systems is
# a filename change, not a code change.
PROJ_2027_HITTERS  = "fg_zips_dc_2027_hitters_projections.csv"
PROJ_2027_PITCHERS = "fg_zips_dc_2027_pitchers_projections.csv"
PROJ_2028_HITTERS  = "fg_zips_dc_2028_hitters_projections.csv"
PROJ_2028_PITCHERS = "fg_zips_dc_2028_pitchers_projections.csv"

# How the two views of 2027 are combined:
#   "blend"         reliability-weighted mix of 2026 form and the projection
#   "projection"    the projection system alone
#   "actuals"       2026 actuals + rest-of-season alone
PROJECTION_BASIS = os.environ.get("KLAB_PROJECTION_BASIS", "blend")
# ^ env override so build_app.py can rebuild per basis in fresh subprocesses:
# klab.io.cached() keys on args, not this global (docs/FINDINGS.md #42).

# --- Projection knobs -------------------------------------------------------
# Max weight on the 2026 leg for RATE stats (talent); playing time uses the
# separate, lower PT_BLEND_CAP_* caps below.
BLEND_W_2026 = 0.50

# Max weight on 2026 PLAYING TIME (docs/FINDINGS.md #51): a short 2026 is weak
# evidence about a healthy 2027 role, and injury-shortened pitcher seasons
# especially must not dock next year's IP. Josh's judgment calls, tunable.
PT_BLEND_CAP_HITTER = 0.30
PT_BLEND_CAP_PITCHER = 0.15
# Higher cap when a pitcher's 2026 IP already EXCEEDED ZiPS's 2027 IP -- he
# proved the workload (docs/FINDINGS.md #53). Applied only when IP_a > IP_b.
PT_BLEND_CAP_PITCHER_EXCEEDED = 0.40

# --- Decision weights -------------------------------------------------------
# Rebuilder default: 2027 surplus dominates, 2026 stretch-run production is
# worth ~25% as much per roto point.
CONTENTION_WEIGHT = 0.25
