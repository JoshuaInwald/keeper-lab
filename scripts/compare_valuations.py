"""Every dollar figure this project produces, on one row per rostered player.

Five valuations, three of them anchored to this league's own history and two of
them new in ROADMAP item 1 (docs/FINDINGS.md #56, #57):

  production_value  roto points above replacement on the $2,600 budget scale.
                    What he is worth TO A ROSTER. $6.56 per roto point.
  keep_value        the same production priced at the auction exchange rate:
                    what it would cost to buy this production back. $9.17/pt.
  market_price      NEW. Fitted on 677 revealed purchases from ex-ante
                    features, calibrated so the 2027 lots sum to the money
                    actually in the room. What he will COST.
  comp_price        the shipped comp estimator: median real salary of his 15
                    nearest historical comps.
  revealed_price    NEW. The salary at which owners' own P(kept) = 0.5, from
                    133 reconstructed 2026 keeper decisions. What the league
                    ACTS as though he is worth.

and the two keeper calls they imply: `keep_2027` (production surplus, shipped)
and `keep_2027_market` (market arbitrage, a second lens).

    PYTHONPATH=.:scripts python3 scripts/compare_valuations.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

from klab import config as C
from klab.auction_estimator import estimate_auction_price
from klab.board import build_board

from keeper_revealed import attach_features, decision_set, fit


def revealed_price_curve():
    """Owners' indifference price as a function of production, from the 2026
    keeper decisions (docs/FINDINGS.md #56.5).

    `years_control_left` is held at the fitted sample's mean rather than at each
    player's own value. Its coefficient is negative, which would say owners pay
    LESS for more years of control; docs/FINDINGS.md #56.5 already identified
    that as a selection artifact of the eligible set (the longer-controlled
    class is made of players who survived an earlier keep decision). Carrying an
    artifact into a headline comparison inverted Skubal against Skenes on the
    strength of a contract code, so the term is frozen and the curve is a
    function of production and role, which is what is being compared.
    """
    feats = pd.read_csv(C.OUT / "price_features.csv")
    d = attach_features(decision_set(feats), feats)
    clean = d[d["decision_season"] == 2026]
    m = fit(clean, "2026")
    p = m.params
    yrs_bar = float(clean["years_control_left"].mean())

    def price(rp, is_pit):
        lin = (p["const"] + p["rp_prior"] * rp + p["played_prior"] * 1.0
               + p["years_control_left"] * yrs_bar + p["is_pit"] * is_pit)
        return -lin / p["keeper_salary"]
    return price


def comp_prices(b: pd.DataFrame) -> pd.Series:
    """Shipped comp estimator, one call per player. Failures (no comp pool for
    the role/position) come back NaN rather than a guess."""
    out = {}
    for r in b.itertuples():
        try:
            out[r.Index] = estimate_auction_price(r.name, b, role=r.role)["comp_adjusted_mid"]
        except Exception:
            out[r.Index] = np.nan
    return pd.Series(out)


def main() -> int:
    b, exch, meta = build_board()
    price = revealed_price_curve()

    b = b.copy()
    b["comp_price"] = comp_prices(b)
    b["revealed_price"] = [max(0.0, price(rp, 1 if role == "PIT" else 0))
                           for rp, role in zip(b["roto_points"], b["role"])]

    b["gap_prod_minus_market"] = b["production_value"] - b["market_price"]
    cols = ["team", "name", "role", "salary", "contract", "keeper_cost",
            "roto_points", "production_value", "keep_value", "market_price",
            "market_price_lo", "market_price_hi", "comp_price", "revealed_price",
            "gap_prod_minus_market", "surplus_redraft", "surplus_market",
            "surplus_multiyear", "surplus_multiyear_market",
            "keep_2027", "keep_2027_market"]
    out = b[cols].sort_values("production_value", ascending=False)
    path = C.OUT / "valuation_comparison.csv"
    out.to_csv(path, index=False)

    SYS = ["production_value", "keep_value", "market_price", "comp_price",
           "revealed_price"]
    print("=" * 78)
    print("LEVEL: what each system says the 276 rostered players are worth")
    print("=" * 78)
    lvl = pd.DataFrame({
        s: {"total $": round(b[s].sum(), 0), "mean": round(b[s].mean(), 2),
            "median": round(b[s].median(), 2), "max": round(b[s].max(), 2),
            "n over $40": int((b[s] > 40).sum()), "n at $0": int((b[s] <= 0.01).sum())}
        for s in SYS}).T
    print(lvl.to_string())
    print(f"\nleague cap is ${C.N_TEAMS * C.BUDGET}. The auction will sell "
          f"{meta['market']['lots']} lots for ${meta['market']['auction_budget']:.0f}.")

    print("\n" + "=" * 78)
    print("AGREEMENT: Spearman rank correlation between systems")
    print("=" * 78)
    rho = pd.DataFrame({a: {c: round(spearmanr(b[a], b[c]).statistic, 3)
                            for c in SYS} for a in SYS})
    print(rho.to_string())

    print("\n" + "=" * 78)
    print("WHERE THEY DIVERGE: mean $ by production decile")
    print("=" * 78)
    q = pd.qcut(b["roto_points"], 10, labels=False, duplicates="drop")
    t = b.groupby(q).agg(n=("name", "size"), roto_pts=("roto_points", "mean"),
                         cost=("keeper_cost", "mean"),
                         **{s: (s, "mean") for s in SYS}).round(2)
    t.index = t.index + 1
    t.index.name = "decile"
    print(t.to_string())

    print("\n" + "=" * 78)
    print("KEEPER CALLS")
    print("=" * 78)
    print(f"production basis (shipped)  keeps {int(b['keep_2027'].sum())}")
    print(f"market arbitrage basis      keeps {int(b['keep_2027_market'].sum())}")
    f = b[b["keep_2027"] != b["keep_2027_market"]]
    print(f"disagreements               {len(f)} of {len(b)}")
    add, drop = f[f["keep_2027_market"]], f[~f["keep_2027_market"]]
    repl = meta["replacement_rp"]
    print(f"  market keeps but production cuts: {len(add)}, of which "
          f"{int((add['roto_points'] < repl).sum())} project below replacement "
          f"({repl:.2f} roto pts)")
    print(f"  production keeps but market cuts: {len(drop)}, mean production "
          f"${drop['production_value'].mean():.2f} vs market "
          f"${drop['market_price'].mean():.2f}")

    print("\nbiggest BUY signals (production far above market price)")
    print(b.nlargest(12, "gap_prod_minus_market")[
        ["name", "role", "keeper_cost", "roto_points", "production_value",
         "market_price", "revealed_price", "keep_2027"]].to_string(index=False))
    print("\nbiggest SELL signals (market price far above production)")
    print(b.nsmallest(12, "gap_prod_minus_market")[
        ["name", "role", "keeper_cost", "roto_points", "production_value",
         "market_price", "revealed_price", "keep_2027"]].to_string(index=False))

    print("\n" + "=" * 78)
    print("2027 KEEPER DECISIONS BY TEAM (production basis, the shipped call)")
    print("=" * 78)
    k = b[b["keep_2027"]]
    per = k.groupby("team").agg(
        keeps=("name", "size"), salary=("keeper_cost", "sum"),
        production=("production_value", "sum"), market=("market_price", "sum"),
        surplus=("surplus_multiyear", "sum")).round(0)
    per["budget_left"] = C.BUDGET - per["salary"]
    per["mkt_arb"] = (per["market"] - per["salary"]).round(0)
    print(per.sort_values("surplus", ascending=False).to_string())
    print(f"\nleague: {len(k)} keepers, ${k['keeper_cost'].sum():.0f} committed of "
          f"${C.N_TEAMS * C.BUDGET}, leaving ${meta['market']['auction_budget']:.0f} "
          f"for {meta['market']['lots']} lots")

    print("\n" + "=" * 78)
    print("WORKED EXAMPLE: Pookie 2.0, every rostered player, keep call and why")
    print("=" * 78)
    ex = b[b["team"] == "Pookie 2.0"].sort_values("surplus_multiyear", ascending=False)
    print(ex[["name", "role", "contract", "keeper_cost", "roto_points",
              "production_value", "market_price", "revealed_price",
              "surplus_multiyear", "keep_2027", "keep_2027_market"]].to_string(index=False))

    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
