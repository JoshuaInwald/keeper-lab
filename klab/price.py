"""Auction PRICE: what this league will pay, as distinct from what a player is
worth to a roster.

`board.py` prices production (`production_value`, the top-230-sums-to-$2,600
scale). This module prices the auction, fit on 677 revealed purchases with only
the information a bidder had on auction day. The two are deliberately never
blended (CONSTRAINTS.md); the gap between them is the buy/sell signal.

Specification, chosen by leave-one-season-out inside 2023-2025 and validated by
holding out 2026 (docs/FINDINGS.md #56): OLS on log(salary) with season fixed
effects, a role interaction on the production terms, Duan smearing back to
dollars, P20/P80 quantile fits widened by two-sided split-conformal
calibration, and a hard cap at the realised maximum for the role. Held-out MAE
5.76 against 6.84 for prior-salary-plus-trend and 7.20 for the comp estimator.

Rejected on LOSO and kept out: an upside/spread feature (ROADMAP Step 5) and a
monotone gradient-boosted model (ROADMAP Step 2's fallback).

Step 3 lives here too: `market_prices_2027()` rescales the raw predictions so
the lots that will actually be sold sum to the money that will actually be in
the room, $2,600 minus committed keeper salaries. Without it the predictions
are individually reasonable and collectively meaningless.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import config as C
from .io import cached

# Fit window. 2022 is excluded, not held out: the FanGraphs exports start in
# 2022, so its purchases have no prior-season line and are indistinguishable
# from genuine rookies (docs/FINDINGS.md #56.3).
FIT_SEASONS = (2023, 2024, 2025, 2026)
VALIDATION_TRAIN = (2023, 2024, 2025)   # what the acceptance test fits on
TRANSFORM = "linear"
AGE_FILL = "segment"

TRANSFORMS = {
    "linear": lambda x: x,
    "sqrt": lambda x: np.sqrt(x.clip(lower=0)),
    "log1p": lambda x: np.log1p(x.clip(lower=0)),
}


def age_fills(train: pd.DataFrame) -> dict:
    """Fill values for missing age, estimated on TRAINING rows only, so no
    number here is hand-entered and none of it comes from the held-out season
    (CONSTRAINTS.md forbids inventing a figure; leakage would invalidate the
    acceptance test)."""
    have = train[train["age"].notna()]
    rook = have[have["no_prior_line"] == 1]["age"]
    return {"mean": float(have["age"].mean()),
            "rookie": float(rook.mean()) if len(rook) else float(have["age"].mean()),
            "veteran": float(have[have["no_prior_line"] == 0]["age"].mean()),
            "upside": float(train["comp_upside"].mean())}


def impute_age(d: pd.DataFrame, how: str, fills: dict) -> tuple[pd.Series, pd.Series | None]:
    """Age, and optionally a missingness flag.

    `mean+flag` is the obvious design and it is a trap here. Age comes from the
    Chadwick register, which misses a player only when his FanGraphs id is
    newer than the register: in 2023-2025 that was five unmatched $1
    placeholders, in 2026 it is eight prospects and NPB imports sold for $1-$20.
    The flag therefore learns "missing age means $1" from training and applies
    it to the most expensive rookie class in the sample. `segment` drops the
    flag and fills age from players with the same prior-line status instead,
    which is what the missingness actually tracks.
    """
    age = d["age"]
    if how == "mean+flag":
        return age.fillna(fills["mean"]), age.isna().astype(float)
    fill = pd.Series(np.where(d["no_prior_line"] == 1, fills["rookie"],
                              fills["veteran"]), index=d.index)
    return age.fillna(fill), None


def design(d: pd.DataFrame, seasons: tuple[int, ...], transform: str,
           age_fill: str, fills: dict, upside: bool = False) -> pd.DataFrame:
    """Model matrix. Season dummies are built against `seasons`; a row whose
    season is not among them gets the most recent training season's dummy, so
    a future season inherits the latest observed price level instead of the
    omitted base year's."""
    f = TRANSFORMS[transform]
    pit = (d["role"] == "PIT").astype(float)
    rp1, rp2 = f(d["rp_prior1"]), f(d["rp_prior2"])
    X = pd.DataFrame({
        "const": 1.0,
        "rp_prior1": rp1,
        "rp_prior2": rp2,
        # Role interaction: hitters and pitchers are paid on different slopes
        # (1.10 vs 0.48 $/pt in the ROADMAP diagnosis), so one slope fits neither.
        "rp_prior1_pit": rp1 * pit,
        "is_pit": pit,
        "no_prior_line": d["no_prior_line"].astype(float),
        "log_PA_prior1": np.log1p(d["PA_prior1"]),
        "log_IP_prior1": np.log1p(d["IP_prior1"]),
        "SV_prior1": d["SV_prior1"],
        "auction_tenure": d["auction_tenure"].astype(float),
        "ever_bought_before": d["ever_bought_before"].astype(float),
        # log1p, not raw: $40 -> $45 is a smaller signal than $1 -> $6.
        "log_last_salary": np.log1p(d["last_salary"].fillna(0.0)),
        "years_since_last": d["years_since_last"].fillna(0.0),
    }, index=d.index)
    age, flag = impute_age(d, age_fill, fills)
    X["age"] = age
    if flag is not None:
        X["age_missing"] = flag
    if upside:
        # ROADMAP item 1 Step 5. Interaction as well as level: the hypothesis on
        # record is that the market pays for spread among hitters and not among
        # pitchers, so the two are separated rather than pooled.
        u = d["comp_upside"].fillna(fills["upside"])
        X["comp_upside"] = u
        X["comp_upside_pit"] = u * pit

    latest = max(seasons)
    for s in seasons[1:]:
        on = (d["season"] == s)
        if s == latest:
            on = on | ~d["season"].isin(seasons)   # unseen season carries the latest level
        X[f"season_{s}"] = on.astype(float)
    return X


def fit_price_model(train: pd.DataFrame, seasons: tuple[int, ...], transform: str,
                    age_fill: str = "mean+flag", upside: bool = False) -> dict:
    fills = age_fills(train)
    X, y = design(train, seasons, transform, age_fill, fills, upside), train["log_salary"]
    ols = sm.OLS(y, X).fit()
    # Duan smearing: E[price] = exp(Xb) * mean(exp(residual)), from training only.
    smear = float(np.mean(np.exp(ols.resid)))
    q20 = sm.QuantReg(y, X).fit(q=0.20, max_iter=5000)
    q80 = sm.QuantReg(y, X).fit(q=0.80, max_iter=5000)
    return {"ols": ols, "smear": smear, "q20": q20, "q80": q80,
            "seasons": seasons, "transform": transform, "age_fill": age_fill,
            "fills": fills, "upside": upside, "conformal": (0.0, 0.0),
            # The league has never paid more than this for the role; a price
            # model that predicts past it is extrapolating, not forecasting.
            "role_cap": train.groupby("role")["salary"].max().to_dict()}


def conformal_width(train: pd.DataFrame, seasons: tuple[int, ...], transform: str,
                    age_fill: str, upside: bool, miss: float = 0.20) -> tuple[float, float]:
    """How much each END of the P20-P80 band has to move to actually cover.

    In-sample the quantile fits cover 57.5%, out of sample 38.4%: the band is
    fit where the residuals are already minimised and does not transfer. This is
    split-conformal quantile regression with the training SEASONS as the folds,
    which is the right split here because the thing that fails to transfer is a
    season, not a random row. Each fold refits q20/q80 on the other seasons and
    scores the held-out one.

    The two ends are calibrated separately. Pooling them left the misses
    lopsided (19.6% below P20 against 27.7% above P80) because the upper tail is
    what the model underprices; one shared widening cannot fix an asymmetric
    miss. Each end targets `miss` of the mass outside it.

    Calibrated on training seasons only, so the held-out season stays held out.
    """
    lo_scores, hi_scores = [], []
    for hold in seasons:
        fit_seasons = tuple(s for s in seasons if s != hold)
        tr = train[train["season"].isin(fit_seasons)]
        te = train[train["season"] == hold]
        f = age_fills(tr)
        Xtr = design(tr, fit_seasons, transform, age_fill, f, upside)
        lo = sm.QuantReg(tr["log_salary"], Xtr).fit(q=0.20, max_iter=5000)
        hi = sm.QuantReg(tr["log_salary"], Xtr).fit(q=0.80, max_iter=5000)
        Xte = design(te, fit_seasons, transform, age_fill, f, upside)
        y = te["log_salary"]
        lo_scores.append(lo.predict(Xte) - y)      # > 0 when the truth fell below P20
        hi_scores.append(y - hi.predict(Xte))      # > 0 when it fell above P80
    q = 1.0 - miss
    return (max(0.0, float(np.quantile(np.concatenate([s.to_numpy() for s in lo_scores]), q))),
            max(0.0, float(np.quantile(np.concatenate([s.to_numpy() for s in hi_scores]), q))))


def predict(m: dict, d: pd.DataFrame, cap: bool = True) -> pd.DataFrame:
    X = design(d, m["seasons"], m["transform"], m["age_fill"], m["fills"], m["upside"])
    w_lo, w_hi = m.get("conformal", (0.0, 0.0))
    out = pd.DataFrame({
        "pred": np.exp(m["ols"].predict(X)) * m["smear"],
        "p20": np.exp(m["q20"].predict(X) - w_lo),
        "p80": np.exp(m["q80"].predict(X) + w_hi),
    }, index=d.index).clip(lower=1.0)
    if cap:
        ceiling = d["role"].map(m["role_cap"]).astype(float)
        ceiling = ceiling.fillna(float(max(m["role_cap"].values())))
        for c in ("pred", "p20", "p80"):
            out[c] = np.minimum(out[c], ceiling)
    return out


# ---------------------------------------------------------------- baselines


# ---------------------------------------------------------------- 2027 pool

@cached
def _feature_table() -> pd.DataFrame:
    """The fitted-on purchase table (`scripts/price_features.py`'s output)."""
    d = pd.read_csv(C.OUT / "price_features.csv")
    return d[d["has_prior_window"] == 1].copy()


def features_2027(players: pd.DataFrame) -> pd.DataFrame:
    """Ex-ante features for the 2027 auction, for any frame with fg_id + role.

    Same columns `scripts/price_features.py` builds for a historical purchase,
    computed as of the 2027 auction: 2026 and 2025 are the prior two seasons,
    tenure and last salary come from the 2022-2026 auction history, age from the
    Chadwick register.

    Caveat carried forward: the 2026 export is a partial season (~75% at the
    2026-08-15 pull), so `PA_prior1`/`IP_prior1` are short for everyone. Its
    coefficient is small and the shortfall is near-uniform, so it lands as a
    level shift, which `calibrate_to_budget()` divides straight back out.
    """
    from .auction import score_season, match_drafts
    from .auction_estimator import position_group
    from .denoms import pooled_relative_dispersion, season_levels, team_baselines
    from .io import load_hitters_history, load_pitchers_history
    from .keeper import position_map

    seasons = (2022, 2023, 2024, 2025, 2026)
    sig, lev = pooled_relative_dispersion(), season_levels()
    hit, pit = load_hitters_history(), load_pitchers_history()
    bl = team_baselines(list(seasons))
    scored = pd.concat([score_season(s, sig, lev, hit, pit, bl) for s in seasons],
                       ignore_index=True)
    rp_cats = [f"rp_{c}" for c in C.CATS]

    h = load_hitters_history()[["season", "fg_id", "PA"]].assign(IP=0.0, SV=0.0)
    p_ = load_pitchers_history()[["season", "fg_id", "IP", "SV"]].assign(PA=0.0)
    pt = pd.concat([h, p_[["season", "fg_id", "PA", "IP", "SV"]]], ignore_index=True)
    pt = pt.groupby(["season", "fg_id"], as_index=False).sum()

    d = players[["fg_id", "role"]].copy()
    d["fg_id"] = d["fg_id"].astype("Int64").astype("float").astype("Int64")
    d["season"] = 2027

    for lag, tag in ((1, "prior1"), (2, "prior2")):
        src = scored[scored["season"] == 2027 - lag]
        cols = ["fg_id", "roto_points"] + (rp_cats if lag == 1 else [])
        ren = {"roto_points": f"rp_{tag}"}
        if lag == 1:
            ren.update({c: f"{c}_prior1" for c in rp_cats})
        d = d.merge(src[cols].rename(columns=ren), on="fg_id", how="left")
        d[f"played_{tag}"] = d[f"rp_{tag}"].notna().astype(int)
        v = pt[pt["season"] == 2027 - lag][["fg_id", "PA", "IP", "SV"]]
        d = d.merge(v.rename(columns={c: f"{c}_{tag}" for c in ("PA", "IP", "SV")}),
                    on="fg_id", how="left")

    d["has_prior_window"] = 1
    d["no_prior_line"] = ((d["played_prior1"] == 0) & (d["played_prior2"] == 0)).astype(int)

    # Auction history: every purchase 2022-2026 predates the 2027 auction.
    a = match_drafts(verbose=False).dropna(subset=["fg_id"]).copy()
    a["fg_id"] = a["fg_id"].astype(int)
    a = a[a["fg_id"] > 0]
    ten = a.groupby("fg_id").size().rename("auction_tenure")
    last = a.sort_values("season").groupby("fg_id").last()[["season", "salary"]]
    last.columns = ["last_salary_season", "last_salary"]
    d = d.merge(ten, on="fg_id", how="left").merge(last, on="fg_id", how="left")
    d["auction_tenure"] = d["auction_tenure"].fillna(0).astype(int)
    d["ever_bought_before"] = d["last_salary"].notna().astype(int)
    d["years_since_last"] = d["season"] - d["last_salary_season"]

    reg = pd.read_csv(C.DATA / "chadwick_register.csv")
    reg = reg[reg["birth_year"].notna()][["key_fangraphs", "birth_year"]]
    reg = reg.rename(columns={"key_fangraphs": "fg_id"}).astype({"fg_id": int})
    d = d.merge(reg, on="fg_id", how="left")
    d["age"] = d["season"] - d["birth_year"]

    pmap = position_map()
    d["pos"] = d["fg_id"].map(pmap)
    d["pos_group"] = d["pos"].map(position_group)

    for lag in ("prior1", "prior2"):
        d[f"rp_{lag}"] = d[f"rp_{lag}"].fillna(0.0)
        for c in ("PA", "IP", "SV"):
            d[f"{c}_{lag}"] = d[f"{c}_{lag}"].fillna(0.0)
    for c in rp_cats:
        d[f"{c}_prior1"] = d[f"{c}_prior1"].fillna(0.0)
    d["comp_upside"] = np.nan          # unused (rejected on LOSO), kept for shape
    return d


@cached
def fitted_model() -> dict:
    """The production price model: same specification the acceptance test
    validated, refit on every season with a prior window (2023-2026)."""
    train = _feature_table()
    m = fit_price_model(train, FIT_SEASONS, TRANSFORM, AGE_FILL, upside=False)
    m["conformal"] = conformal_width(train, FIT_SEASONS, TRANSFORM, AGE_FILL, False)
    return m


def raw_prices_2027(players: pd.DataFrame) -> pd.DataFrame:
    """Uncalibrated model price per player, BEFORE the role cap.

    The level is not meaningful until `calibrate_to_budget()` has run: the raw
    predictions carry 2026's season effect and a partial-season playing-time
    shortfall, and sum to about $3,545 across the 276 rostered players against a
    $2,600 league cap. Capping here instead of after calibration would pin seven
    players at $45 and distort the rescaling, so the cap is applied last.
    """
    f = features_2027(players)
    out = predict(fitted_model(), f, cap=False)
    out.index = players.index
    return out


# ---------------------------------------------------------------- Step 3

def role_ceiling(roles: pd.Series) -> pd.Series:
    """The most this league has ever paid for the role, per row."""
    caps = fitted_model()["role_cap"]
    return roles.map(caps).astype(float).fillna(float(max(caps.values())))


def apply_scale(raw: pd.DataFrame, ceiling: pd.Series, k: float) -> pd.DataFrame:
    """Put raw model prices on the calibrated scale: rescale the amount above
    the $1 minimum bid, then cap at the role's realised maximum."""
    out = {}
    for c in ("pred", "p20", "p80"):
        v = (1.0 + (raw[c].astype(float) - 1.0) * k).clip(lower=1.0)
        out[c] = np.minimum(v, ceiling)
    out = pd.DataFrame(out, index=raw.index)
    # Two independently fitted quantile regressions can cross, and the cap can
    # push them together: Crow-Armstrong came out P20 $41.53 against P80 $39.73.
    # Sort the band ends and hold the point estimate inside them, so the
    # displayed range is always a range.
    lo = out[["p20", "p80"]].min(axis=1)
    hi = out[["p20", "p80"]].max(axis=1)
    out["p20"], out["p80"] = lo, hi
    out["pred"] = out["pred"].clip(lower=lo, upper=hi)
    return out


def calibrate_to_budget(pool: pd.DataFrame, raw: pd.DataFrame, n_keepers: int,
                        keeper_salary: float) -> dict:
    """ROADMAP item 1 Step 3: put the predictions on the money that will
    actually be in the room.

    The auction sells `L = 230 - n_keepers` lots for `B = $2,600 - keeper
    salaries`. Raw model prices carry no such constraint. Rescale the amount
    above the $1 minimum bid so the L lots that clear sum to exactly B:

        sum over the top L of [1 + (p - 1) * k] = B
        k = (B - L) / (sum of the top L p - L)

    This replaces the top-230-sums-to-$2,600 identity for `market_price`;
    `production_value` keeps its own. `k` is the market's own inflation factor
    and should agree with `api._inflation()`'s remaining-budget / remaining-worth
    figure, which is computed a completely different way.
    """
    cap_total = C.N_TEAMS * C.BUDGET
    lots = C.N_TEAMS * C.N_ACTIVE - n_keepers
    budget = cap_total - float(keeper_salary)

    caps = fitted_model()["role_cap"]
    ceiling = pool["role"].map(caps).astype(float)
    ceiling = ceiling.fillna(float(max(caps.values())))

    # Solve for k by iteration, not in closed form: the $1 floor, the role cap
    # and the band-crossing repair in apply_scale() are all non-linear, so a
    # single algebraic pass left the lots summing to $1,853 against a $1,964
    # budget. Each pass re-solves k on the money the capped and floored lots no
    # longer absorb. Scoring through apply_scale() rather than a private copy of
    # the arithmetic is what keeps the identity exact: an earlier version solved
    # on unclipped prices and shipped a $7 miss.
    p = raw["pred"].astype(float)
    k = 1.0
    for _ in range(50):
        scaled = apply_scale(raw, ceiling, k)["pred"]
        top_idx = scaled.nlargest(min(lots, len(scaled))).index
        total = float(scaled.loc[top_idx].sum())
        if abs(total - budget) < 0.01:
            break
        stuck = ((scaled.loc[top_idx] >= ceiling.loc[top_idx] - 1e-9)
                 | (scaled.loc[top_idx] <= 1.0 + 1e-9))
        denom = float((p.loc[top_idx][~stuck] - 1.0).sum())
        if denom <= 0:
            break
        k += (budget - total) / denom

    out = apply_scale(raw, ceiling, k)
    top_idx = out["pred"].nlargest(min(lots, len(out))).index

    # The market's own inflation: dollars the auction will pay per dollar of
    # production_value, over the lots that actually clear. Directly comparable
    # to api._inflation()'s remaining-budget / remaining-worth, which is built
    # from the production scale and never sees this model.
    worth = float(pool.loc[top_idx, "production_value"].sum())
    meta = {"lots": int(lots), "auction_budget": float(budget),
            "n_keepers": int(n_keepers), "keeper_salary": float(keeper_salary),
            "scale_k": float(k),
            "sum_top_lots_raw": float(raw["pred"].nlargest(len(top_idx)).sum()),
            "sum_top_lots_calibrated": float(out["pred"].loc[top_idx].sum()),
            "production_value_of_lots": worth,
            "market_inflation": float(budget / worth) if worth else float("nan"),
            "n_at_role_cap": int((out["pred"] >= ceiling - 1e-9).sum())}
    return {"prices": out, "meta": meta}


def features_2028(board: pd.DataFrame) -> pd.DataFrame:
    """Ex-ante features for the 2028 auction, for players under contract.

    The 2027 season has not happened, so its "prior season" line is the board's
    own 2027 projection (`roto_points`, with the projected PA/IP behind it) and
    2026 actuals slide back to lag 2. Everything else ages by one year: the
    player is a year older, has one more auction on his record, and his last
    price is the 2027 keeper cost he is being carried at.

    This is a projection of a price, one year further out than the projection it
    rests on, and it inherits every bit of that uncertainty. It exists because
    multi-year keeper surplus needs an out-year price; it is not a forecast to
    quote on its own.
    """
    f = features_2027(board).copy()
    f["season"] = 2028
    f["rp_prior2"] = f["rp_prior1"]
    for c in ("PA", "IP", "SV"):
        f[f"{c}_prior2"] = f[f"{c}_prior1"]
    f["rp_prior1"] = board["roto_points"].to_numpy(float)
    f["PA_prior1"] = board["PA"].fillna(0.0).to_numpy(float)
    f["IP_prior1"] = board["IP"].fillna(0.0).to_numpy(float)
    f["SV_prior1"] = board["SV"].fillna(0.0).to_numpy(float)
    f["played_prior1"] = 1
    f["no_prior_line"] = 0
    f["age"] = f["age"] + 1
    f["auction_tenure"] = f["auction_tenure"] + 1
    f["last_salary"] = board["keeper_cost"].to_numpy(float)
    f["last_salary_season"] = 2027
    f["years_since_last"] = 1
    f["ever_bought_before"] = 1
    return f


def market_price_2028(board: pd.DataFrame, k: float) -> pd.Series:
    """2028 auction price on the same calibrated scale as 2027. `k` comes from
    the 2027 budget calibration: the 2028 budget is not knowable, so the level
    is carried forward rather than re-solved."""
    raw = predict(fitted_model(), features_2028(board), cap=False)
    raw.index = board.index
    return apply_scale(raw, role_ceiling(board["role"]), k)["pred"]
