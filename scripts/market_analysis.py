"""Open valuation questions: market biases, team characteristics, keep-vs-cash.

Sections:
  1. Is $/roto-point stably estimated, and does the market agree?
  2. Do bidders overpay for particular MLB teams (the "Mets fan" hypothesis)?
  3. What separates this season's successful teams?
  4. Keep-vs-cash: what is a dollar of auction budget actually worth?
  5. Best available Skubal returns.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

import klab.config as C
from klab.auction import auction_sample, regress
from klab.board import build_board, fit_exchange_rate, value_players
from klab.io import load_hitters_history, load_pitchers_history, load_standings_long
from klab.trade import standings_points

pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 60)


def stability():
    print("=" * 96)
    print("1. IS $/ROTO-POINT STABLY ESTIMATED?")
    print("=" * 96)
    s = auction_sample()
    rows = []
    for lab, d in [("all 2022-26", s)] + [(str(y), s[s.season == y]) for y in sorted(s.season.unique())]:
        r = regress(d)
        rows.append({"sample": lab, "n": int(r.nobs), "slope": r.params["salary"],
                     "se": r.bse["salary"], "usd_per_pt": 1 / r.params["salary"],
                     "lo95": 1 / (r.params["salary"] + 1.96 * r.bse["salary"]),
                     "hi95": 1 / (r.params["salary"] - 1.96 * r.bse["salary"]),
                     "intercept": r.params["const"], "r2": r.rsquared})
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print("\nsplit-half reliability within each season (odd vs even purchases):")
    for y in sorted(s.season.unique()):
        d = s[s.season == y].reset_index(drop=True)
        a, b = d[d.index % 2 == 0], d[d.index % 2 == 1]
        if len(a) > 20 and len(b) > 20:
            print(f"  {y}: ${1/regress(a).params['salary']:5.2f} vs ${1/regress(b).params['salary']:5.2f}")


def mlb_team_bias():
    print("\n" + "=" * 96)
    print("2. DO BIDDERS OVERPAY FOR PARTICULAR MLB TEAMS?")
    print("=" * 96)
    s = auction_sample()
    hit = load_hitters_history()[["season", "fg_id", "Team"]]
    pit = load_pitchers_history()[["season", "fg_id", "Team"]]
    teams = pd.concat([hit, pit]).dropna().drop_duplicates(["season", "fg_id"])
    s = s.merge(teams, on=["season", "fg_id"], how="left")
    s = s[s["Team"].notna() & (s["Team"] != "- - -")]

    # Residual from the pooled price->production fit. Negative means the
    # player returned less than his price predicted, i.e. he was overpaid for.
    r = regress(s)
    s["resid"] = s["roto_points"] - (r.params["const"] + r.params["salary"] * s["salary"])

    g = s.groupby("Team").agg(n=("salary", "size"), mean_paid=("salary", "mean"),
                              mean_rp=("roto_points", "mean"), resid=("resid", "mean"))
    g["se"] = s.groupby("Team")["resid"].std() / np.sqrt(g["n"])
    g["t"] = g["resid"] / g["se"]
    g = g[g["n"] >= 10].sort_values("resid")
    print("\nmost OVERPAID (most negative residual), teams with >=10 purchases:")
    print(g.head(8).round(2).to_string())
    print("\nmost UNDERPAID:")
    print(g.tail(8).round(2).to_string())

    print("\nNew York Mets specifically:")
    nym = s[s["Team"] == "NYM"]
    if len(nym):
        t = sm.OLS(s["resid"], sm.add_constant((s["Team"] == "NYM").astype(float).rename("NYM"))).fit(cov_type="HC1")
        print(f"  n={len(nym)} purchases, mean price ${nym.salary.mean():.1f}, "
              f"mean roto {nym.roto_points.mean():.2f}")
        print(f"  NYM effect on residual: {t.params['NYM']:+.2f} roto points "
              f"(t={t.tvalues['NYM']:.2f}, p={t.pvalues['NYM']:.3f})")
        print(f"  in dollars at $7.56/pt: {t.params['NYM']*7.56:+.1f}")
    print("\nF-test, do MLB team dummies explain anything at all?")
    X = pd.get_dummies(s["Team"], drop_first=True).astype(float)
    full = sm.OLS(s["resid"], sm.add_constant(X)).fit()
    print(f"  R2 = {full.rsquared:.4f}, F = {full.fvalue:.2f}, p = {full.f_pvalue:.3f}, "
          f"n = {int(full.nobs)}, k = {X.shape[1]}")


def successful_teams():
    print("\n" + "=" * 96)
    print("3. WHAT SEPARATES THE SUCCESSFUL TEAMS IN 2026?")
    print("=" * 96)
    st = load_standings_long()
    wide = st[st["season"] == 2026].pivot(index="team", columns="category", values="total")
    pts = standings_points(wide[C.CATS])
    ch = pd.read_csv(C.OUT / "acquisition_channels_2026.csv")
    share = ch.pivot_table(index="team", columns="channel", values="roto_points",
                           aggfunc="sum").fillna(0)
    share = share.div(share.sum(axis=1), axis=0) * 100
    eff = ch.groupby("team").apply(
        lambda d: d["roto_points"].sum() / d["salary"].sum(), include_groups=False)

    tab = pd.DataFrame({"standings_pts": pts["TOTAL"]}).join(share).join(
        eff.rename("roto_per_$"))
    tab = tab.sort_values("standings_pts", ascending=False)
    print(tab.round(2).to_string())
    print("\ncorrelation with standings points:")
    for c in [c for c in tab.columns if c != "standings_pts"]:
        print(f"  {c:15s} r = {tab['standings_pts'].corr(tab[c]):+.3f}")
    print("\ncategory points, best vs worst team:")
    print(pts[C.CATS].loc[[pts['TOTAL'].idxmax(), pts['TOTAL'].idxmin()]].round(1).to_string())


def keep_vs_cash(board, meta):
    print("\n" + "=" * 96)
    print("4. KEEP-VS-CASH: WHAT IS A DOLLAR OF AUCTION BUDGET WORTH?")
    print("=" * 96)
    k = board[board["keep_2027"]]
    keeper_sal, keeper_worth = k["keeper_cost"].sum(), k["redraft_value"].sum()
    rem_sal = C.N_TEAMS * C.BUDGET - keeper_sal
    rem_worth = C.N_TEAMS * C.BUDGET - keeper_worth
    infl = rem_sal / rem_worth
    print(f"  aggregate keeper surplus ${keeper_worth-keeper_sal:,.0f}  ->  inflation {infl:.3f}")
    print(f"  so $1 of auction budget buys ${1/infl:.2f} of value, not $1.00")
    print()
    print("  This changes the keep rule. Cutting a player does not give you his")
    print("  value back -- it gives you his SALARY, which buys salary/inflation")
    print("  of production. So the correct test is:")
    print()
    print("      keep if   value  >  keeper_cost / inflation")
    print()
    b = board.copy()
    b["cash_equiv"] = b["keeper_cost"] / infl
    b["surplus_vs_cash"] = b["redraft_value"] - b["cash_equiv"]
    b["keep_naive"] = b["surplus_redraft"] > 0
    b["keep_infl"] = b["surplus_vs_cash"] > 0
    flips = b[b["keep_naive"] != b["keep_infl"]]
    print(f"  {len(flips)} of {len(b)} rostered players flip from cut to keep "
          f"once inflation is priced in.")
    for team in ("Pookie 2.0", "NPB No Stars"):
        d = b[b["team"] == team].sort_values("surplus_vs_cash", ascending=False)
        print(f"\n  --- {team}: marginal decisions ---")
        cols = ["name", "keeper_cost", "redraft_value", "cash_equiv",
                "surplus_redraft", "surplus_vs_cash", "keep_naive", "keep_infl"]
        marg = d[(d["surplus_redraft"] < 15) & (d["surplus_vs_cash"] > -12)]
        print(marg[cols].round(1).to_string(index=False))
    return b, infl


def skubal_returns(board, infl):
    print("\n" + "=" * 96)
    print("5. BEST AVAILABLE RETURNS FOR SKUBAL")
    print("=" * 96)
    k = board[board["keep_2027"]]
    room = (C.BUDGET - k.groupby("team")["keeper_cost"].sum()).rename("budget_left")
    print("  cap room per team after optimal keepers (can they absorb $38?):")
    print(room.sort_values(ascending=False).round(0).to_string())

    print("\n  best cheap-contract surplus assets in the league ($1-5 salary):")
    cheap = board[(board["salary"] <= 5) & (board["team"] != "NPB No Stars")]
    cols = ["team", "name", "role", "contract", "years_controlled", "salary",
            "roto_points", "redraft_value", "surplus_multiyear"]
    print(cheap.nlargest(18, "surplus_multiyear")[cols].round(1).to_string(index=False))

    print("\n  Skubal's multi-year surplus to beat: "
          f"${board.loc[board['name']=='Tarik Skubal','surplus_multiyear'].iloc[0]:.1f}")
    print("  (a fair package needs to clear that, from one team, with the cap room)")


if __name__ == "__main__":
    board, exch, meta = build_board()
    stability()
    mlb_team_bias()
    successful_teams()
    b, infl = keep_vs_cash(board, meta)
    skubal_returns(board, infl)
    b.to_csv(C.OUT / "keep_vs_cash.csv", index=False)
