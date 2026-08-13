"""Where in the auction price chain does surplus actually live?

Pairs every purchase 2022-2026 with the value its realized production was
worth on the redraft scale, then asks how that value compares to the price
paid at each point on the chain.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from klab.auction import auction_sample
from klab.board import fit_exchange_rate, value_players

pd.set_option("display.width", 300)


def build():
    exch, _ = fit_exchange_rate()
    _, _, meta = value_players(exch)
    usd, repl = meta["usd_per_rp_redraft"], meta["replacement_rp"]
    s = auction_sample()
    s["value"] = ((s["roto_points"] - repl) * usd + 1).clip(lower=0)
    s["surplus"] = s["value"] - s["salary"]
    return s, meta


def price_ceiling(s):
    print("=== PRICE CEILING: top prices paid, by season ===")
    for y in sorted(s["season"].unique()):
        d = s[s["season"] == y]
        top = np.sort(d["salary"].values)[::-1][:6]
        print(f"  {y}: {[int(x) for x in top]}   n={len(d)}  total ${d['salary'].sum()}")


def chain(s):
    print("\n=== SURPLUS ALONG THE PRICE CHAIN ===")
    s = s.copy()
    s["bucket"] = pd.cut(s["salary"], [0, 1, 3, 5, 10, 15, 20, 30, 45],
                         labels=["$1", "$2-3", "$4-5", "$6-10", "$11-15",
                                 "$16-20", "$21-30", "$31+"])
    g = s.groupby("bucket", observed=True).agg(
        n=("salary", "size"), paid=("salary", "mean"),
        rp=("roto_points", "mean"), value=("value", "mean"),
        surplus=("surplus", "mean"), sd=("surplus", "std"))
    g["se"] = g["sd"] / np.sqrt(g["n"])
    g["t"] = g["surplus"] / g["se"]
    g["value_per_$"] = g["value"] / g["paid"]
    g["total_surplus"] = g["surplus"] * g["n"]
    print(g.drop(columns=["sd"]).round(2).to_string())
    print(f"\ntotal spent ${s['salary'].sum():,.0f} | value delivered "
          f"${s['value'].sum():,.0f} | aggregate surplus ${s['surplus'].sum():,.0f}")


def shape(s):
    """Is the market's price convex in production, or linear?"""
    print("\n=== FUNCTIONAL FORM OF price -> production ===")
    s = s.copy()
    s["logsal"] = np.log(s["salary"])
    s["sal2"] = s["salary"] ** 2
    r1 = sm.OLS(s["roto_points"], sm.add_constant(s[["salary"]])).fit(cov_type="HC1")
    r2 = sm.OLS(s["roto_points"], sm.add_constant(s[["logsal"]])).fit(cov_type="HC1")
    r3 = sm.OLS(s["roto_points"], sm.add_constant(s[["salary", "sal2"]])).fit(cov_type="HC1")
    print(f"  linear    rp = {r1.params['const']:.2f} + {r1.params['salary']:.4f}*$"
          f"        R2={r1.rsquared:.3f}")
    print(f"  log       rp = {r2.params['const']:.2f} + {r2.params['logsal']:.3f}*ln($)"
          f"    R2={r2.rsquared:.3f}")
    print(f"  quadratic $^2 coef = {r3.params['sal2']:.6f} "
          f"(t={r3.tvalues['sal2']:.2f})   R2={r3.rsquared:.3f}")
    print("  -> a null quadratic term means price buys production at a constant")
    print("     rate. There is no scarcity premium to correct for at the top.")


def deciles(s):
    print("\n=== VALUE vs PRICE, by price decile ===")
    s = s.copy()
    s["dec"] = pd.qcut(s["salary"], 10, duplicates="drop")
    g = s.groupby("dec", observed=True).agg(
        n=("salary", "size"), paid=("salary", "mean"), value=("value", "mean"))
    g["surplus"] = g["value"] - g["paid"]
    g["value_per_$"] = g["value"] / g["paid"]
    print(g.round(2).to_string())


if __name__ == "__main__":
    s, meta = build()
    price_ceiling(s)
    chain(s)
    shape(s)
    deciles(s)
    s.to_csv("out/draft_surplus_sample.csv", index=False)
