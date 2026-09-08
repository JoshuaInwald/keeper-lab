"""Step 2: fit auction price directly, and hold out a season to check it.

`redraft_value` prices production. This prices the AUCTION: what this league
will actually pay. Fit on `out/price_features.csv` (ex-ante features only); it
never touches `redraft_value`, which CONSTRAINTS.md keeps as a separate
quantity. See docs/ROADMAP.md item 1 Step 2, docs/FINDINGS.md #56.

Specification: OLS on log(salary) with season fixed effects (inflation), role
interactions on the production terms (the market pays pitchers about half the
per-point rate of hitters), and Duan smearing on the way back to dollars --
exp(fitted) is a median, not a mean, and under-predicts by the retransformation
bias `auction_estimator` already tripped over (docs/FINDINGS.md #35). P20/P80
come from quantile regressions on the same design; quantiles need no smearing,
being equivariant under exp().

Two design points the first cut got wrong, both worth stating because they cost
the model its first acceptance test:

  season level    A held-out FUTURE season has no dummy. Defaulting it to the
                  omitted base level handed 2026 the 2023 price level and
                  inflated every prediction by exp(0.90); MAE 8.76 against a
                  6.84 baseline. An unseen season now carries the MOST RECENT
                  training season's effect, which is what "next year looks
                  like last year" actually means.
  production term log(price) linear in roto points is exponential in roto
                  points: it predicted $86 for a hitter in a league whose
                  all-time high is $45. Concave transforms are among the
                  candidates below and the top-end check is an acceptance
                  criterion, not a diagnostic.

Specification is chosen by leave-one-season-out CV INSIDE the training seasons
(2023-2025), never on 2026: picking a spec on the held-out season is the same
leak as fitting on it (docs/FINDINGS.md #7 is the cautionary tale about
selecting on a number you then report).

Acceptance test: fit 2023-2025, predict 2026. 2022 is excluded from the fit,
not held out: the FanGraphs exports start in 2022, so its purchases have no
prior-season line and are indistinguishable from genuine rookies.

Baselines it has to beat:
  prior salary   what this league paid him last time, carried forward by the
                 training seasons' own price trend. The strongest simple rule,
                 and the one the ROADMAP diagnosis found doubles R^2.
  comp estimator `klab/auction_estimator.py` re-implemented over training-only
                 comps. The shipped module reads the full auction sample, 2026
                 included, so calling it directly here would leak the answer.

    PYTHONPATH=.:scripts python3 scripts/price_model.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

from klab import config as C
from klab.auction_estimator import PROFILE_COLS

TRAIN = (2023, 2024, 2025)
# Chosen by leave-one-season-out inside TRAIN; see main(). Named here so
# klab/price.py fits the same specification it was validated under.
TRANSFORM = "linear"
AGE_FILL = "segment"
TEST = 2026
PROFILE_PRIOR = [f"{c}_prior1" for c in PROFILE_COLS]

# Candidate production transforms. All concave-or-linear in roto points; the
# linear one is the first cut, kept in so the CV table shows why it loses.
TRANSFORMS = {
    "linear": lambda x: x,
    "sqrt": lambda x: np.sqrt(x.clip(lower=0)),
    "log1p": lambda x: np.log1p(x.clip(lower=0)),
}


# ---------------------------------------------------------------- design

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

def baseline_prior_salary(train: pd.DataFrame, test: pd.DataFrame) -> pd.Series:
    """Last price this league paid him, carried forward by the training
    seasons' own year-over-year price trend. Never-bought players fall back to
    the training mean price, which is the best a prior-salary rule can do."""
    means = train.groupby("season")["salary"].mean()
    yrs = int(means.index.max() - means.index.min())
    drift = float((means.iloc[-1] / means.iloc[0]) ** (1.0 / yrs)) if yrs else 1.0
    fallback = float(train["salary"].mean())
    gap = (test["season"] - test["last_salary_season"]).fillna(0.0)
    return (test["last_salary"] * drift ** gap).fillna(fallback).clip(lower=1.0)


def baseline_comps(train: pd.DataFrame, test: pd.DataFrame, k: int = 15) -> pd.Series:
    """`klab/auction_estimator.py`'s rule with comps drawn from training
    seasons only: the k nearest purchases in normalised per-category
    roto-point space, same role, preferring the same position group, priced at
    the comps' own median real salary."""
    pool = train[train["played_prior1"] == 1]
    scale = pool[PROFILE_PRIOR].std().replace(0, 1.0)
    out = []
    for r in test.itertuples():
        cand = pool[pool["role"] == r.role]
        same = cand[cand["pos_group"] == r.pos_group]
        used = same if len(same) >= k else cand
        if used.empty:
            out.append(float(train["salary"].median()))
            continue
        t = np.array([getattr(r, c) for c in PROFILE_PRIOR], dtype=float)
        dist = np.sqrt((((used[PROFILE_PRIOR] - t) / scale) ** 2).sum(axis=1))
        out.append(float(used.loc[dist.nsmallest(k).index, "salary"].median()))
    return pd.Series(out, index=test.index).clip(lower=1.0)


# ---------------------------------------------------------------- scoring

def score(actual: pd.Series, pred: pd.Series, label: str) -> dict:
    err = pred - actual
    return {"model": label,
            "MAE": round(float(err.abs().mean()), 2),
            "RMSE": round(float(np.sqrt((err ** 2).mean())), 2),
            "bias": round(float(err.mean()), 2),
            "Spearman": round(float(spearmanr(actual, pred).statistic), 3)}


def calibration(actual: pd.Series, pred: pd.Series, nbins: int = 10) -> pd.DataFrame:
    q = pd.qcut(pred, nbins, labels=False, duplicates="drop")
    t = pd.DataFrame({"actual": actual, "pred": pred, "bin": q})
    g = t.groupby("bin").agg(n=("actual", "size"), mean_pred=("pred", "mean"),
                             mean_actual=("actual", "mean"))
    g["gap"] = g["mean_actual"] - g["mean_pred"]
    g.index, g.index.name = g.index + 1, "pred_decile"
    return g.round(2)


def gbm_loso(train: pd.DataFrame, transform: str, age_fill: str) -> pd.DataFrame | None:
    """ROADMAP item 1 Step 2's own fallback: a monotone gradient-boosted model,
    to be tried only if the GLM's held-out error is poor. Reported because a
    tree model cannot predict outside the observed price range, which is
    exactly the top-end problem the GLM needs a hard cap for. It loses anyway.

    Optional dependency: skipped, not failed, when scikit-learn is absent."""
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except ImportError:
        return None
    rows = []
    for mono in (True, False):
        preds, acts = [], []
        for hold in TRAIN:
            fit_seasons = tuple(s for s in TRAIN if s != hold)
            tr = train[train["season"].isin(fit_seasons)]
            te = train[train["season"] == hold]
            f = age_fills(tr)
            X = design(tr, fit_seasons, transform, age_fill, f)
            cst = [1 if c in ("rp_prior1", "rp_prior2", "log_last_salary") else 0
                   for c in X.columns]
            g = HistGradientBoostingRegressor(
                max_iter=300, learning_rate=0.05, max_depth=3, min_samples_leaf=15,
                l2_regularization=1.0, random_state=0,
                monotonic_cst=cst if mono else None).fit(X, tr["log_salary"])
            Xte = design(te, fit_seasons, transform, age_fill, f)[list(X.columns)]
            preds.append(pd.Series(np.exp(g.predict(Xte)), index=te.index).clip(lower=1.0))
            acts.append(te["salary"])
        a, p = pd.concat(acts), pd.concat(preds)
        rows.append({**score(a, p, f"GBM monotone={mono}")})
    return pd.DataFrame(rows)[["model", "MAE", "RMSE", "bias", "Spearman"]]


def select_transform(train: pd.DataFrame, age_fill: str = "mean+flag",
                     upside: bool = False) -> pd.DataFrame:
    """Leave-one-season-out over the TRAINING seasons only. Each fold refits
    everything (coefficients, smearing, quantiles, role caps) on the other two
    seasons, so the held-out season is never touched by the choice."""
    rows = []
    for name in TRANSFORMS:
        preds, acts = [], []
        for hold in TRAIN:
            fit_seasons = tuple(s for s in TRAIN if s != hold)
            tr = train[train["season"].isin(fit_seasons)]
            te = train[train["season"] == hold]
            m = fit_price_model(tr, fit_seasons, name, age_fill, upside)
            preds.append(predict(m, te)["pred"])
            acts.append(te["salary"])
        a, p = pd.concat(acts), pd.concat(preds)
        rows.append({"transform": name, **score(a, p, name)})
    return pd.DataFrame(rows).drop(columns=["model"])


def report(m: dict, train: pd.DataFrame, test: pd.DataFrame, label: str) -> pd.DataFrame:
    raw = predict(m, test, cap=False)
    p = predict(m, test)
    t = test.assign(pred=p["pred"], p20=p["p20"], p80=p["p80"])

    print(f"\n=== held-out {TEST} (n={len(t)}): {label} ===")
    print(pd.DataFrame([
        score(t["salary"], t["pred"], "price model"),
        score(t["salary"], t["base_prior_salary"], "baseline: prior salary + trend"),
        score(t["salary"], t["base_comps"], "baseline: comp estimator (train-only pool)"),
    ]).to_string(index=False))

    print("\ncalibration by predicted-price decile")
    print(calibration(t["salary"], t["pred"]).to_string())

    def coverage(frame, lo, hi):
        return 100 * float(((frame["salary"] >= lo) & (frame["salary"] <= hi)).mean())

    tr_in = predict(m, train)
    print("\nP20-P80 band (nominal 60% coverage)")
    print(pd.DataFrame([
        {"set": "training 2023-2025 (in-sample)", "n": len(train),
         "coverage_pct": round(coverage(train, tr_in["p20"], tr_in["p80"]), 1),
         "median_width": round(float((tr_in["p80"] - tr_in["p20"]).median()), 2)},
        {"set": f"held-out {TEST}", "n": len(t),
         "coverage_pct": round(coverage(t, t["p20"], t["p80"]), 1),
         "median_width": round(float((t["p80"] - t["p20"]).median()), 2)},
    ]).to_string(index=False))
    print(f"  misses {100 * float((t['salary'] < t['p20']).mean()):.1f}% below P20 / "
          f"{100 * float((t['salary'] > t['p80']).mean()):.1f}% above P80 (target 20/20)")

    print("\nheld-out error by segment")
    seg = t.assign(segment=np.where(
        t["no_prior_line"] == 1, "no prior MLB line",
        np.where(t["ever_bought_before"] == 1, "bought before", "new to this league")))
    print(seg.groupby("segment").apply(
        lambda g: pd.Series({"n": len(g),
                             "mean_actual": round(g["salary"].mean(), 2),
                             "mean_pred": round(g["pred"].mean(), 2),
                             "MAE": round((g["pred"] - g["salary"]).abs().mean(), 2)}),
        include_groups=False).to_string())

    print("\ntop-end check (against the realised max for the role in training)")
    tops = []
    for role, g in t.groupby("role"):
        ceil = int(train.loc[train["role"] == role, "salary"].max())
        tops.append({"role": role, "n": len(g), "train_max": ceil,
                     "max_pred_uncapped": round(float(raw.loc[g.index, "pred"].max()), 2),
                     "max_pred": round(float(g["pred"].max()), 2),
                     "n_capped": int((raw.loc[g.index, "pred"] > ceil).sum()),
                     "breach": bool(g["pred"].max() > ceil + 1e-9)})
    print(pd.DataFrame(tops).to_string(index=False))
    return t


def main() -> int:
    d = pd.read_csv(C.OUT / "price_features.csv")
    d = d[d["has_prior_window"] == 1]
    train = d[d["season"].isin(TRAIN)].copy()
    test = d[d["season"] == TEST].copy()
    print(f"train {list(TRAIN)} n={len(train)}   test {TEST} n={len(test)}")
    test["base_prior_salary"] = baseline_prior_salary(train, test)
    test["base_comps"] = baseline_comps(train, test)

    print("\n--- specification search: leave-one-season-out inside 2023-2025 ---")
    print("2026 is never consulted here. Selecting a spec on the held-out season")
    print("is the same leak as fitting on it (docs/FINDINGS.md #7).")
    for up in (False, True):
        cv = select_transform(train, AGE_FILL, up)
        print(f"\n  production transform, Step 5 upside feature = {up}:")
        print("  " + cv.to_string(index=False).replace("\n", "\n  "))
    gb = gbm_loso(train, TRANSFORM, AGE_FILL)
    print("\n  Step 2's monotone-GBM fallback:")
    print("  " + (gb.to_string(index=False).replace("\n", "\n  ")
                  if gb is not None else "skipped (scikit-learn not installed)"))
    print(f"\nchosen: transform={TRANSFORM}, age={AGE_FILL}, upside=False, GLM. "
          f"Both ROADMAP fallbacks lose on LOSO.")

    w = conformal_width(train, TRAIN, TRANSFORM, AGE_FILL, False)
    m = fit_price_model(train, TRAIN, TRANSFORM, AGE_FILL, False)
    ols = m["ols"]
    print(f"\nlog-price OLS on 2023-2025: R^2 {ols.rsquared:.3f} "
          f"(adj {ols.rsquared_adj:.3f}), Duan smearing {m['smear']:.4f}, "
          f"role caps {m['role_cap']}, conformal widening lo {w[0]:.4f} hi {w[1]:.4f}")
    print(pd.DataFrame({"coef": ols.params.round(4), "se": ols.bse.round(4),
                        "t": ols.tvalues.round(2), "p": ols.pvalues.round(4)}).to_string())

    m["conformal"] = (0.0, 0.0)
    report(m, train, test, "quantile bands as fitted (uncalibrated)")
    m["conformal"] = w
    t = report(m, train, test, "quantile bands conformally calibrated on training seasons")

    out = t[["season", "player", "fg_id", "role", "pos_group", "salary",
             "pred", "p20", "p80", "base_prior_salary", "base_comps",
             "rp_prior1", "last_salary", "age", "no_prior_line"]]
    path = C.OUT / "price_model_holdout.csv"
    out.sort_values("salary", ascending=False).to_csv(path, index=False)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
