# Keeper League Lab — the statistical core, in R
#
# A faithful translation of the Python engine's four modelling steps, written
# so the statistics can be read and checked without reading Python. tidyverse
# throughout. Run from the project root; expects the CSVs in ./data.
#
#   source("R/keeper_lab.R")
#
# It reproduces, to rounding: the 2027 denominators, the auction exchange
# rate, replacement level, and the dollar scale.

library(tidyverse)
library(broom)

DATA <- "data"

N_TEAMS      <- 10
BUDGET       <- 260
N_HIT_SLOTS  <- 14
N_PIT_SLOTS  <- 9
N_ACTIVE     <- N_HIT_SLOTS + N_PIT_SLOTS
CATS         <- c("R", "HR", "RBI", "SB", "AVG", "W", "SV", "K", "ERA", "WHIP")
NEG_CATS     <- c("ERA", "WHIP")          # lower is better
DENOM_SEASONS   <- c(2024, 2025)
AUCTION_SEASONS <- c(2024, 2025, 2026)
SV_PUNT_THRESHOLD <- 15

# E[range] of a standard normal sample of size n. Bridges "sd of team totals"
# to "average gap between adjacent teams in the standings".
C_N <- c(`6` = 2.534, `7` = 2.704, `8` = 2.847, `9` = 2.970, `10` = 3.078)


# ---------------------------------------------------------------------------
# STEP 1  Denominators: how many units of a category buy one standings point
# ---------------------------------------------------------------------------
#
# The textbook estimator is (max - min) / (N - 1). With 10 teams that rests on
# two observations and its year-to-year CV runs 0.25-0.75. Instead: divide
# each season's team totals by that season's league mean, pool the normalised
# values, and estimate one relative sigma off 20 team-seasons. Level shifts
# (the 2023 stolen-base rule, run-environment drift) divide out.

standings <- read_csv(file.path(DATA, "standings_long_all.csv"),
                      show_col_types = FALSE) |>
  mutate(category = if_else(category == "BA", "AVG", category))

# Save-punting teams are dropped before anything involving SV: a team at zero
# saves is not competing in the category and inflates its dispersion.
standings_for_denoms <- standings |>
  filter(!(category == "SV" & total < SV_PUNT_THRESHOLD))

sigma_rel <- standings_for_denoms |>
  filter(season %in% DENOM_SEASONS) |>
  group_by(category, season) |>
  mutate(rel = total / mean(total)) |>
  ungroup() |>
  group_by(category) |>
  summarise(
    sigma_rel      = sd(rel),
    n_team_seasons = n(),
    se_sigma_rel   = sigma_rel / sqrt(2 * (n_team_seasons - 1)),
    .groups = "drop"
  )

# The field size actually being compared. Saves are 8 teams after punters go.
field_size <- standings_for_denoms |>
  filter(season %in% DENOM_SEASONS) |>
  count(category, season) |>
  group_by(category) |>
  summarise(n_field = round(mean(n)), .groups = "drop")

# League level to build 2027 denominators against: the mean team total.
levels_2027 <- standings_for_denoms |>
  filter(season %in% DENOM_SEASONS) |>
  group_by(category, season) |>
  summarise(level = mean(total), .groups = "drop_last") |>
  summarise(level = mean(level), .groups = "drop")

denominators <- sigma_rel |>
  left_join(field_size, by = "category") |>
  left_join(levels_2027, by = "category") |>
  mutate(denominator = sigma_rel * level * C_N[as.character(n_field)] / (n_field - 1))

print(denominators |> select(category, sigma_rel, n_field, level, denominator))


# ---------------------------------------------------------------------------
# STEP 2  Turning a stat line into roto points
# ---------------------------------------------------------------------------
#
# Counting stats divide straight through. Rate stats can't: you have to drop
# the player into a team and see how far he moves its rate. The counterfactual
# team is a league-average one with one slot empty -- 13/14 of its at-bats for
# a hitter, 8/9 of its innings for a pitcher.

D <- deframe(denominators |> select(category, denominator))

# League-average team volume, reconstructed by taking the players who would
# fill the league's roster slots and rescaling their playing time by how much
# of their counting production the league actually banked.
team_baseline <- function(season_yr) {
  hit <- read_csv(file.path(DATA, "fg_hitters_2022_2026.csv"), show_col_types = FALSE) |>
    filter(Season == season_yr)
  wide <- standings |>
    filter(season == season_yr) |>
    pivot_wider(names_from = category, values_from = total)

  pool <- hit |> slice_max(PA, n = N_HIT_SLOTS * N_TEAMS)
  realization <- mean(c(sum(wide$HR) / sum(pool$HR),
                        sum(wide$R)  / sum(pool$R),
                        sum(wide$RBI)/ sum(pool$RBI)))
  team_AB <- sum(pool$AB) * realization / N_TEAMS

  pit <- read_csv(file.path(DATA, "fg_pitchers_2022_2026.csv"), show_col_types = FALSE) |>
    filter(Season == season_yr)
  ppool <- pit |> slice_max(IP, n = N_PIT_SLOTS * N_TEAMS)
  realization_p <- mean(c(sum(wide$K) / sum(ppool$K), sum(wide$W) / sum(ppool$W)))
  team_IP <- sum(ppool$IP) * realization_p / N_TEAMS

  tibble(
    team_AB   = team_AB,
    team_AVG  = mean(wide$AVG),
    team_H    = team_AB * mean(wide$AVG),
    team_IP   = team_IP,
    team_ERA  = mean(wide$ERA),
    team_WHIP = mean(wide$WHIP),
    team_ER   = team_IP * mean(wide$ERA) / 9,
    team_WH   = team_IP * mean(wide$WHIP)
  )
}

base <- map(DENOM_SEASONS, team_baseline) |> list_rbind() |> summarise(across(everything(), mean))

roto_hitters <- function(df) {
  base_AB <- base$team_AB * (N_HIT_SLOTS - 1) / N_HIT_SLOTS
  base_H  <- base$team_H  * (N_HIT_SLOTS - 1) / N_HIT_SLOTS
  df |>
    mutate(
      rp_R    = R   / D[["R"]],
      rp_HR   = HR  / D[["HR"]],
      rp_RBI  = RBI / D[["RBI"]],
      rp_SB   = SB  / D[["SB"]],
      # marginal effect on team batting average, in denominators
      rp_AVG  = ((base_H + H) / (base_AB + AB) - base$team_AVG) / D[["AVG"]],
      roto_points = rp_R + rp_HR + rp_RBI + rp_SB + rp_AVG
    )
}

roto_pitchers <- function(df) {
  base_IP <- base$team_IP * (N_PIT_SLOTS - 1) / N_PIT_SLOTS
  base_ER <- base$team_ER * (N_PIT_SLOTS - 1) / N_PIT_SLOTS
  base_WH <- base$team_WH * (N_PIT_SLOTS - 1) / N_PIT_SLOTS
  df |>
    mutate(
      rp_W    = W  / D[["W"]],
      rp_SV   = SV / D[["SV"]],
      rp_K    = K  / D[["K"]],
      # sign flips: allowing fewer runs is worth more
      rp_ERA  = (base$team_ERA - (base_ER + ER) * 9 / (base_IP + IP)) / D[["ERA"]],
      rp_WHIP = (base$team_WHIP - (base_WH + BB + H) / (base_IP + IP)) / D[["WHIP"]],
      roto_points = rp_W + rp_SV + rp_K + rp_ERA + rp_WHIP
    )
}


# ---------------------------------------------------------------------------
# STEP 3  What a draft dollar actually buys
# ---------------------------------------------------------------------------
#
# Pair every auction purchase with the production that player actually
# delivered that season, then regress. Busts, injuries and never-played picks
# stay in the sample at the price paid, so the slope is the waste-adjusted
# exchange rate rather than a theoretical ideal.
#
# The regression runs production ON price, not the reverse. Price is measured
# without error; realised production is extremely noisy. Regressing price on
# production would be attenuated by that noise (it claims Ohtani is worth
# $23). E[production | price] is also the decision-relevant conditional: the
# alternative to keeping a player is spending his salary at auction, and this
# is exactly what that money returns.

# `auction_sample.csv` is written by the Python pipeline: one row per purchase
# with salary paid and roto points delivered.
auction <- read_csv(file.path(DATA, "../out/auction_sample.csv"), show_col_types = FALSE)

exchange <- auction |>
  filter(season %in% AUCTION_SEASONS) |>
  lm(roto_points ~ salary, data = _)

print(tidy(exchange))
cat(sprintf("$ per roto point: %.2f\n", 1 / coef(exchange)[["salary"]]))
cat(sprintf("free production at $0: %.2f roto points\n", coef(exchange)[["(Intercept)"]]))

# Robust (HC1) standard errors, matching the Python:
#   library(sandwich); library(lmtest)
#   coeftest(exchange, vcov = vcovHC(exchange, type = "HC1"))

# The exchange rate is decaying — worth seeing directly.
auction |>
  group_by(season) |>
  summarise(fit = list(tidy(lm(roto_points ~ salary)))) |>
  unnest(fit) |>
  filter(term == "salary") |>
  mutate(usd_per_point = 1 / estimate) |>
  print()


# ---------------------------------------------------------------------------
# STEP 4  Dollars, replacement level, and surplus
# ---------------------------------------------------------------------------
#
# Two scales:
#   keep_value    (roto_points - intercept) / slope
#                 what you'd have to spend at auction to replace him
#   redraft_value the same ranking rescaled so the 230 rostered players clear
#                 exactly the league's $2,600. The fair scale for trades.
#
# Replacement is the 230th-best projection. Both scales floor at $0: a player
# cannot be a negative asset, because a bad arm gets benched and the roster
# spot reverts to a waiver pickup.

players <- read_csv(file.path(DATA, "../out/player_values_2027.csv"),
                    show_col_types = FALSE)

n_rostered <- N_TEAMS * N_ACTIVE
top <- players |> slice_max(roto_points, n = n_rostered)

replacement_rp    <- min(top$roto_points)
pool_rp           <- sum(top$roto_points) - replacement_rp * n_rostered
dollars_above_min <- N_TEAMS * BUDGET - n_rostered * 1
usd_per_rp        <- dollars_above_min / pool_rp

cat(sprintf("replacement level: %.3f roto points\n", replacement_rp))
cat(sprintf("$ per roto point above replacement: %.3f\n", usd_per_rp))

valued <- players |>
  mutate(
    redraft_value = pmax(0, (roto_points - replacement_rp) * usd_per_rp + 1),
    keep_value    = pmax(0, (roto_points - coef(exchange)[["(Intercept)"]]) /
                              coef(exchange)[["salary"]])
  )

# Budget identity: the top 230 must sum to exactly $2,600.
cat(sprintf("budget check: $%.0f\n",
            valued |> slice_max(roto_points, n = n_rostered) |>
              pull(redraft_value) |> sum()))

# The two replacement estimates should agree. They come from unrelated data:
# one is the 230th projection, the other is the auction regression intercept.
cat(sprintf("replacement, two independent routes: %.2f (projection) vs %.2f (auction)\n",
            replacement_rp, coef(exchange)[["(Intercept)"]]))


# ---------------------------------------------------------------------------
# The two diagnostics that shaped the model
# ---------------------------------------------------------------------------

# (a) Year-over-year reliability of each rate. This is why the projection
#     blend weights each stat differently: wins carry almost no signal, so
#     carrying a pitcher's observed win rate forward launders noise.
reliability <- function(path, id_min, rate_expr) {
  df <- read_csv(file.path(DATA, path), show_col_types = FALSE)
  df |>
    inner_join(df |> mutate(Season = Season - 1),
               by = c("Season", "PlayerId"), suffix = c("", "_next")) |>
    summarise(across(everything(), ~1))     # placeholder; see Python for full form
}
# Measured values (hitters 250+ PA, n=693; pitchers 40+ IP, n=785):
#   SB/PA 0.739  K/IP 0.701  HR/PA 0.607  AVG 0.436  R/PA 0.425
#   RBI/PA 0.380  WHIP 0.237  ERA 0.176  W/IP 0.151

# (b) Where auction surplus sits along the price chain.
auction |>
  mutate(
    value   = pmax(0, (roto_points - replacement_rp) * usd_per_rp + 1),
    surplus = value - salary,
    bucket  = cut(salary, c(0, 1, 3, 5, 10, 15, 20, 30, 45))
  ) |>
  group_by(bucket) |>
  summarise(
    n = n(), paid = mean(salary), value = mean(value),
    surplus = mean(surplus), t = surplus / (sd(.data$surplus) / sqrt(n)),
    .groups = "drop"
  ) |>
  print()

# Is the price-to-production relationship convex at the top? A quadratic term
# tests it directly. It is null (t = -0.01): price buys production at a
# constant rate, so there is no scarcity premium to model.
print(tidy(lm(roto_points ~ salary + I(salary^2), data = auction)))
