"""League constants for the Legends Fantasy Baseball keeper league.

Every knob that drives the valuation lives here. Nothing downstream should
hard-code a league rule.
"""

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

HIT_CATS = ["R", "HR", "RBI", "SB", "AVG"]
PIT_CATS = ["W", "SV", "K", "ERA", "WHIP"]
CATS = HIT_CATS + PIT_CATS
NEG_CATS = {"ERA", "WHIP"}          # lower is better
RATE_CATS = {"AVG", "ERA", "WHIP"}
COUNT_CATS = [c for c in CATS if c not in RATE_CATS]

# --- Keeper economics -------------------------------------------------------
EXTENSION_COST = 5        # +$5/yr to extend a player in his final year
MIN_KEEPERS = 6
MAX_KEEPERS = 13
FA_SALARY_PRE_ASB = 10
FA_SALARY_POST_ASB = 20

# Contract year semantics. CORRECTED 2026-08-13 -- the previous handoff had
# this backwards, which understated every multi-year contract by a full season.
#
# The code is the number of seasons remaining AFTER the current one:
#   "3" -> 2027, 2028, 2029 at current salary (only reachable via extension)
#   "2" -> 2027, 2028 at current salary
#   "1" -> 2027 only, at current salary
#   "F" -> 2026 was the final year; keep only by extending at salary + $5
#
# Evidence in contracts_parsed.csv:
#   * $10 and $20 salaries -- the pre- and post-All-Star-break FA acquisition
#     prices -- cluster almost entirely in code "2". Those are 2026 in-season
#     pickups, and a 3-year deal signed in 2026 leaves exactly 2027 and 2028.
#   * Code "F" holds the big 2024 auction prices (Judge $39, Witt $39,
#     Tucker $33, Tatis $34, Devers $30): 2024 + 3 years = final year 2026.
#   * Only Skubal ($38) and Cal Raleigh ($16) carry "3", consistent with the
#     +$5/yr extension being exercised rather than "3" meaning a final year.
YEARS_REMAINING = {"1": 1, "2": 2, "3": 3}
EXTENSION_REQUIRED = {"F"}
KEEPABLE_AT_SALARY = set(YEARS_REMAINING)
# Extension rules, verified against the constitution (Keeper Eligibility):
#   "owners must extend the player's contract by adding $5 for each additional
#    year... extend the player for one more season at $15 or two more seasons
#    at $20"  -> +$5 PER YEAR, and the owner chooses 1 or 2 years.
#   "Players can only be extended once per contract"  -> one bite, ever.
EXTENSION_MAX_YEARS = 2
# A player whose current salary exceeds his last auction price has already
# used his extension and cannot extend again.
EXTENSION_ALREADY_USED_IF_SALARY_ABOVE_DRAFT = True
# Extra-constitutional rulings. The league agreed Ohtani is not extendable --
# a one-off to deal with a two-way player the contract rules never anticipated.
# This is not derivable from any file we hold, so it lives here as an explicit
# override rather than as a silent special case somewhere downstream.
NON_EXTENDABLE_NAMES = {"Shohei Ohtani"}

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
# Nobody keeps a part-time player. Real keeper candidates project for a full
# workload, so keeper value is computed at full-season playing time: rates are
# held fixed and playing time is scaled up to the floor. Guards against ZiPS
# durability haircuts and rookie-ramp projections burying a breakout.
KEEPER_PA_FLOOR = 600
KEEPER_IP_FLOOR = 150
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
# Seasons used to fit denominators. 2026 is in progress (~70%) so it is
# excluded from denominator fitting but used for projections.
DENOM_SEASONS = [2024, 2025, 2026]   # regime changed in 2024; 2026 added below
# 2026 is in progress. Each team's counting totals are ~75% of a full season,
# but `pooled_relative_dispersion` divides every team by its own season mean
# before pooling, so a uniform scale factor cancels exactly -- "scale 2026 up
# to full-season volume" and "use 2026 raw" are the same computation.
#
# What does NOT cancel is sampling noise. Relative variance of a team total is
# roughly  sigma_talent^2 + sigma_noise^2 / f, so a partial season is
# over-dispersed by the noise term. CORRECTED 2026-08-13 -- the original
# version of this comment checked five categories (ERA, WHIP, R, HR, SB),
# generalized "rate cats bad, counting cats fine," and shipped that as
# DENOM_EXCLUDE_PARTIAL_FOR_RATES. All ten, measured per-season CV:
#
#            2024    2025    2026(f=.75)
#   R       0.142   0.063   0.054
#   HR      0.190   0.104   0.103
#   RBI     0.150   0.053   0.064
#   SB      0.341   0.301   0.127
#   AVG     0.036   0.014   0.026   <-- NOT inflated, despite being a rate cat
#   W       0.114   0.144   0.121
#   SV      0.254   0.177   0.328   <-- inflated, despite being a counting cat
#   K       0.090   0.164   0.085
#   ERA     0.037   0.035   0.073   <-- 2x the full-season figure
#   WHIP    0.028   0.028   0.042
#
# The rate-vs-counting split was a proxy, and it fails on both ends: AVG
# denominates over at-bats, which accumulate at a stable known rate all
# season (every hitter plays ~daily), so a partial season is not meaningfully
# noisier there. SV denominates over save opportunities, which depend on a
# specific role (closer) that is unstable and gets reassigned mid-season --
# the actual mechanism is "denominator accumulates unevenly / is subject to
# role churn," not "is this a rate stat." Pooling AVG's 2026 data tightens its
# standard error by ~21% for a ~2% shift in the point estimate (clear win);
# excluding SV's 2026 data drops the pooled estimate by 16% (0.250 -> 0.209,
# about 1.2 current-scheme standard errors, so directionally supported by the
# closer-role-churn mechanism but not overwhelming on its own). See
# out/FINDINGS.md #26 for the full experiment, and out/LAB_NOTEBOOK.md for why
# the original five-category check wasn't wrong, just incomplete.
PARTIAL_SEASONS = {2026: 0.75}
# Categories whose 2026 data is excluded from denominator pooling because a
# partial season measurably inflates their dispersion. Not RATE_CATS -- see
# comment above. Set DENOM_EXCLUDE_PARTIAL_SEASON = False to pool all thirty
# team-seasons everywhere and accept the ERA/WHIP/SV inflation.
PARTIAL_EXCLUDE_CATS = {"ERA", "WHIP", "SV"}
DENOM_EXCLUDE_PARTIAL_SEASON = True
# Teams below this SV total are punting saves and are dropped before
# computing the SV denominator (HANDOFF §7).
SV_PUNT_THRESHOLD = 15
# MLB stolen-base rule change landed in 2023; weight the new regime.
SB_REGIME_START = 2023
SB_PRE_REGIME_WEIGHT = 0.0

# Seasons whose auction results set the $/roto-point exchange rate.
#
# CAREFUL: these auctions did not happen in the same world. Keepers removed
# from the pool before each auction ran 25, 28, 29, 29, then **100** in 2026,
# and $/roto-point tracks that count at r = 0.80. Pooling 2024-25 (29 keepers)
# with 2026 (100) averages two different regimes, and 2027 will look like 2026
# or more extreme -- so the pooled number understates what a dollar will cost.
AUCTION_SEASONS = [2024, 2025, 2026]

# Keepers removed from the pool before each auction. Drives the environment
# adjustment below.
KEEPERS_REMOVED = {2022: 25, 2023: 28, 2024: 29, 2025: 29, 2026: 100}
KEEPERS_EXPECTED_2027 = 100

# How to set the 2027 exchange rate:
#   "pooled"          straight fit on AUCTION_SEASONS. Most data, wrong world.
#   "keeper_adjusted" fit $/pt on keeper count across all five seasons, then
#                     predict at KEEPERS_EXPECTED_2027. Uses every auction but
#                     lands in the right environment. Default.
#   "recent"          2026 alone. Right world, but n=112 and its two halves
#                     disagree by a factor of three.
EXCHANGE_BASIS = "keeper_adjusted"
# League level (mean team total) to build 2027 denominators against.
LEVEL_SEASONS = [2024, 2025]

# --- Waiver-wire value ------------------------------------------------------
# Replacement level is "the best player you can get for free". How good that
# player is depends on how rich the waiver wire is, and this league's wire is
# rich: in-season free agents supplied 40% of all 2026 roto production.
#
# The three settings are anchored on real quantities, not taste:
#   "low"    the 230th-best projection -- one per active roster slot. The
#            textbook choice, and it assumes the wire adds nothing you could
#            not already have drafted. Replacement 4.14 roto points.
#   "medium" the (rostered + one round)th projection, reflecting that this
#            league carries 275 players and churns hard, so the marginal
#            player is deeper than the 230th. Replacement ~3.9.
#   "high"   the median production of players actually acquired from free
#            agency in 2026 (5.04 roto points). This is an upper bound and
#            deliberately biased: those pickups were selected *after* they
#            started producing, so it overstates what is available ex ante.
#            Use it to see how much the answer moves, not as a point estimate.
#
# Higher replacement means free talent is better, which makes every rostered
# player worth LESS. "low" is the most generous to your own roster.
WAIVER_VALUE = "low"
WAIVER_RANK = {"low": 230, "medium": 300}
WAIVER_HIGH_RP = 5.04

# --- Positional adjustment --------------------------------------------------
# OFF by default, and that is a considered choice rather than an omission.
# FanGraphs' 13-system test found the variants with the largest positional
# adjustments finished last, and Razzball -- who tested four stances -- found
# "very close to zero impact". Where it plausibly does matter in this format
# is catcher and middle infield, the two slots with genuinely thin pools.
#
# When enabled, replacement level is computed per position group rather than
# league-wide, so a catcher is measured against other catchers.
POSITIONAL_ADJUSTMENT = False
# Roster slots by position group, used to set each group's replacement rank.
POSITION_SLOTS = {"C": 1, "MI": 2, "CI": 2, "OF": 5, "UTIL": 2, "P": 9}

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
PROJECTION_BASIS = "blend"

# --- Projection knobs -------------------------------------------------------
# 50/50 blend of (2026 actuals + ROS ZiPS) and pre-season ZiPS 2027.
BLEND_W_2026 = 0.50
BLEND_W_ZIPS27 = 0.50

# --- Decision weights -------------------------------------------------------
# Rebuilder default: 2027 surplus dominates, 2026 stretch-run production is
# worth ~25% as much per roto point.
CONTENTION_WEIGHT = 0.25
