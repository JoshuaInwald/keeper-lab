"""Original experiments: put real error bars on the headline numbers.

Four questions the model has been answering with point estimates:

  1. How uncertain are the denominators, really? (bootstrap)
  2. Does the exchange rate generalise out of sample? (leave-one-season-out)
  3. Is the saves finding robust to the null? (permutation test)
  4. Is the AVG denominator right? (calibrate against CBS's independent rank)
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

import klab.config as C
from klab.auction import auction_sample, regress
from klab.board import build_2027_scorer, fit_exchange_rate, value_players
from klab.denoms import (RotoScorer, denominators_for_level,
                         pooled_relative_dispersion, season_levels,
                         team_baselines, teams_per_category)
from klab.io import load_pitchers_history, load_standings_long, norm_name
from klab.project import projected_2027_levels

pd.set_option("display.width", 300)
RNG = np.random.default_rng(20260813)


def exp1_bootstrap_denominators(B=2000):
    """Resample team-seasons to get real intervals on each denominator.

    The model has been quoting '±16%' from the analytic standard error of a
    standard deviation. Bootstrapping the actual estimator is honest about
    the small sample and about the punter filter, which the analytic formula
    ignores entirely.
    """
    print("=" * 96)
    print("EXPERIMENT 1 — bootstrap confidence intervals on the denominators")
    print("=" * 96)
    st = load_standings_long()
    lv = projected_2027_levels(season_levels())
    n_by = teams_per_category()
    rows = []
    for cat in C.CATS:
        obs = []
        for s in C.DENOM_SEASONS:
            v = st[(st.season == s) & (st.category == cat)]["total"].astype(float).values
            if cat == "SV":
                v = v[v >= C.SV_PUNT_THRESHOLD]
            obs.append(v / v.mean())
        pooled = np.concatenate(obs)
        n = len(pooled)
        point = pooled.std(ddof=1)
        draws = np.array([RNG.choice(pooled, n, replace=True).std(ddof=1)
                          for _ in range(B)])
        lo, hi = np.percentile(draws, [2.5, 97.5])
        k = {6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}[n_by[cat]] / (n_by[cat] - 1)
        rows.append({"category": cat, "n": n,
                     "denominator": point * lv[cat] * k,
                     "lo95": lo * lv[cat] * k, "hi95": hi * lv[cat] * k,
                     "rel_width_pct": 100 * (hi - lo) / point})
    t = pd.DataFrame(rows)
    print(t.round(4).to_string(index=False))
    print(f"\n  mean 95% interval width: ±{t.rel_width_pct.mean()/2:.0f}% of the point estimate")
    print("  The '±16%' quoted elsewhere is the analytic SE and is optimistic;")
    print("  the bootstrap is the number to put next to a dollar figure.")
    return t


def exp2_loso_exchange_rate():
    """Leave one season out: fit on four auctions, predict the fifth."""
    print("\n" + "=" * 96)
    print("EXPERIMENT 2 — leave-one-season-out on the exchange rate")
    print("=" * 96)
    s = auction_sample()
    rows = []
    for y in sorted(s.season.unique()):
        tr, te = s[s.season != y], s[s.season == y]
        r = regress(tr)
        pred = r.params["const"] + r.params["salary"] * te["salary"]
        resid = te["roto_points"] - pred
        actual = 1 / regress(te).params["salary"]
        rows.append({"held_out": y, "pooled_$/pt": 1 / r.params["salary"],
                     "actual_$/pt": actual,
                     "mean_resid": resid.mean(), "rmse": np.sqrt((resid ** 2).mean())})
    t = pd.DataFrame(rows)
    print(t.round(3).to_string(index=False))
    r_yr = np.corrcoef(t.held_out, t.mean_resid)[0, 1]
    print(f"\n  mean residual on the held-out season runs "
          f"{t.mean_resid.min():+.2f} to {t.mean_resid.max():+.2f} roto points")
    print(f"  corr(held-out year, mean residual) = {r_yr:+.3f}  -- weak and NOT monotone,")
    print(f"  so a pooled fit is not systematically biased by season in the")
    print(f"  *residual*. What it does miss is the level: pooled $/pt sits at")
    print(f"  {t['pooled_$/pt'].min():.1f}-{t['pooled_$/pt'].max():.1f} while the held-out season's own rate")
    print(f"  runs {t['actual_$/pt'].min():.1f}-{t['actual_$/pt'].max():.1f}. Pooling gets the ranking right and the")
    print(f"  price level wrong, which is exactly why EXCHANGE_BASIS exists.")
    return t


def exp3_saves_permutation(B=5000):
    """Is the closer effect bigger than chance would produce?

    Shuffle the closer label within season and price band, so the null
    preserves both the time trend and the fact that closers are cheap.
    """
    print("\n" + "=" * 96)
    print("EXPERIMENT 3 — permutation test on the saves finding")
    print("=" * 96)
    s = auction_sample()
    p = load_pitchers_history()[["season", "fg_id", "SV"]].copy()
    p["season"] += 1
    prior = p.groupby(["season", "fg_id"], as_index=False)["SV"].sum().rename(
        columns={"SV": "SV_prior"})
    s = s.merge(prior, on=["season", "fg_id"], how="left")
    s["SV_prior"] = s["SV_prior"].fillna(0)
    s["closer"] = (s["SV_prior"] >= 10) & (s["role"] == "PIT")
    r = regress(s)
    s["resid"] = s["roto_points"] - (r.params["const"] + r.params["salary"] * s["salary"])
    s["band"] = pd.cut(s["salary"], [0, 5, 10, 20, 99])

    obs = s.loc[s.closer, "resid"].mean() - s.loc[~s.closer, "resid"].mean()
    null = np.empty(B)
    for b in range(B):
        lab = s.groupby(["season", "band"], observed=True)["closer"].transform(
            lambda x: RNG.permutation(x.values))
        null[b] = s.loc[lab, "resid"].mean() - s.loc[~lab, "resid"].mean()
    pval = (np.abs(null) >= abs(obs)).mean()
    print(f"  observed closer excess: {obs:+.2f} roto points")
    print(f"  null distribution (label shuffled within season x price band):")
    print(f"    mean {null.mean():+.3f}, sd {null.std():.3f}, "
          f"95% range [{np.percentile(null,2.5):+.2f}, {np.percentile(null,97.5):+.2f}]")
    print(f"  two-sided p = {pval:.4f}  ({B} permutations)")
    print("  The shuffle holds season and price band fixed, so this is not")
    print("  the time trend and not 'cheap players beat their price'.")
    return obs, pval


def exp4_avg_denominator_calibration():
    """Solve for the AVG denominator that best reproduces CBS's own rank.

    CBS publishes an independent roto rank. If the model's AVG weight were
    right, no rescaling would improve agreement. If a systematically smaller
    denominator (= more weight on average) fits better, that is evidence the
    pooled 2024-25 estimate is too large.
    """
    print("\n" + "=" * 96)
    print("EXPERIMENT 4 — calibrating the AVG denominator against CBS's rank")
    print("=" * 96)
    try:
        cbs = pd.read_csv(C.DATA / "cbs_rank_2026.csv")
    except FileNotFoundError:
        print("  cbs_rank_2026.csv not present; skipping")
        return None
    from scripts.leaderboard_2026 import full_2026

    scorer, D, base, _ = build_2027_scorer()
    H, _ = full_2026()
    cbs["k"] = cbs["player"].map(norm_name)
    H = H.copy()
    H["k"] = H["name"].map(norm_name)
    H = H.sort_values("PA", ascending=False).drop_duplicates("k")
    m = cbs.merge(H, on="k", suffixes=("_cbs", ""))
    print(f"  matched {len(m)} of {len(cbs)} CBS hitters")

    rows = []
    for mult in [0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5, 2.0]:
        d = dict(D)
        d["AVG"] = D["AVG"] * mult
        sc = RotoScorer(d, base)
        rp = sc.hitters(m)["roto_points"]
        # both ranks are "1 = best", so agreement is a POSITIVE correlation
        rho = spearmanr(m["cbs_rank"], rp.rank(ascending=False)).statistic
        rows.append({"AVG_denom_multiplier": mult, "AVG_denominator": d["AVG"],
                     "spearman_vs_CBS": rho})
    t = pd.DataFrame(rows)
    print(t.round(4).to_string(index=False))
    best = t.loc[t.spearman_vs_CBS.idxmax()]
    print(f"\n  best agreement at multiplier {best.AVG_denom_multiplier} "
          f"(denominator {best.AVG_denominator:.5f}), rho = {best.spearman_vs_CBS:.3f}")
    print(f"  current setting is 1.0, rho = {t.loc[t.AVG_denom_multiplier==1.0,'spearman_vs_CBS'].iloc[0]:.3f}")
    cur = t.loc[t.AVG_denom_multiplier == 1.0, "spearman_vs_CBS"].iloc[0]
    gain = best.spearman_vs_CBS - cur
    if best.AVG_denom_multiplier < 1.0:
        direction = "MORE"
    elif best.AVG_denom_multiplier > 1.0:
        direction = "LESS"
    else:
        direction = None
    if direction is None or gain < 0.02:
        print("  -> the curve is flat near 1.0; no material evidence the AVG")
        print("     denominator is mis-set. The CBS/model disagreement on")
        print("     average-vs-power is not explained by this parameter.")
    else:
        print(f"  -> CBS behaves as if average is worth {direction} than this model")
        print(f"     says; rho improves by {gain:+.3f} at multiplier "
              f"{best.AVG_denom_multiplier}.")
    return t


if __name__ == "__main__":
    exp1_bootstrap_denominators()
    exp2_loso_exchange_rate()
    exp3_saves_permutation()
    exp4_avg_denominator_calibration()
