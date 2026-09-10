"""Sanity checks that must pass before any number is presented.

1. Does the roto-point scorer reproduce the 2026 standings from rosters?
2. Do the ten hand-checked players land where domain knowledge says?
3. Does the auction sample reconcile with the league's actual cap?
5. Is the pool that sets the dollar scale one the league could actually field?
"""
import numpy as np
import pandas as pd

import klab.config as C
from klab.board import build_board
from klab.io import load_hitters_history, load_pitchers_history, load_standings_long
from klab.trade import standings_points

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 50)


def check_2026_standings(board):
    """Roll each team's CURRENT roster forward over its actual 2026 stats and
    compare the implied standings to the real ones.

    Caveat: rosters are as of mid-August, so anyone acquired in-season carries
    production they banked for a different team. This is a directional check,
    not an identity.
    """
    hit = load_hitters_history()
    pit = load_pitchers_history()
    h26 = hit[hit["season"] == 2026]
    p26 = pit[pit["season"] == 2026]

    # drop_duplicates: a split player has two board rows per fg_id and was
    # otherwise counted twice for his team (FINDINGS #80).
    r = board[["team", "fg_id"]].drop_duplicates()
    H = r.merge(h26, on="fg_id", how="inner")
    P = r.merge(p26, on="fg_id", how="inner")

    gh = H.groupby("team")[["AB", "H", "HR", "R", "RBI", "SB"]].sum()
    gp = P.groupby("team")[["IP", "W", "SV", "K", "ER", "BB", "H"]].sum()
    gp = gp.rename(columns={"H": "H_allowed"})
    t = gh.join(gp, how="outer").fillna(0.0)
    t["AVG"] = t["H"] / t["AB"]
    t["ERA"] = t["ER"] * 9 / t["IP"]
    t["WHIP"] = (t["BB"] + t["H_allowed"]) / t["IP"]

    pred = standings_points(t[C.CATS])
    st = load_standings_long()
    actual_wide = st[st["season"] == 2026].pivot(index="team", columns="category",
                                                 values="total")
    act = standings_points(actual_wide[C.CATS])

    cmp = pd.DataFrame({
        "predicted_pts": pred["TOTAL"], "actual_pts": act["TOTAL"],
    }).dropna()
    cmp["pred_rank"] = cmp["predicted_pts"].rank(ascending=False)
    cmp["act_rank"] = cmp["actual_pts"].rank(ascending=False)
    from scipy.stats import spearmanr, pearsonr
    rho = spearmanr(cmp["predicted_pts"], cmp["actual_pts"]).statistic
    r_p = pearsonr(cmp["predicted_pts"], cmp["actual_pts"]).statistic
    print("=== CHECK 1: current rosters -> 2026 standings ===")
    print(cmp.sort_values("actual_pts", ascending=False).round(1).to_string())
    print(f"\nSpearman(predicted, actual) = {rho:.3f}   Pearson = {r_p:.3f}")
    print("(rosters are mid-August, so in-season adds carry other teams' production)")
    return cmp


HAND_CHECK = [
    "Shohei Ohtani", "Aaron Judge", "Tarik Skubal", "Bobby Witt Jr.",
    "Paul Skenes", "Yordan Alvarez", "Elly De La Cruz", "Mason Miller",
    "Pete Alonso", "Spencer Strider",
]


def check_players(board):
    print("\n=== CHECK 2: hand-check across the value spectrum ===")
    cols = ["team", "name", "role", "contract", "salary", "keeper_cost",
            "PA", "HR", "R", "RBI", "SB", "AVG", "IP", "W", "SV", "K",
            "ERA", "WHIP", "roto_points", "redraft_value", "surplus_redraft"]
    rows = []
    for n in HAND_CHECK:
        m = board[board["name"].str.contains(n.split()[-1], case=False, na=False)]
        m = m[m["name"].str.lower().str[0] == n[0].lower()]
        if len(m):
            rows.append(m.iloc[0])
    print(pd.DataFrame(rows)[cols].round(2).to_string(index=False))


def check_budget(board, exch, meta):
    print("\n=== CHECK 3: budget reconciliation ===")
    tot_sal = board["salary"].sum()
    print(f"salary committed across all 275 rostered players: ${tot_sal:,.0f}")
    print(f"league cap (10 x $260):                           ${C.N_TEAMS*C.BUDGET:,.0f}")
    print(f"BUDGET IDENTITY over the calibration pool:        "
          f"${meta['budget_check_top230']:,.0f}  (must equal $2,600)")
    # Under "slot_role" replacement is a pair (140th hitter, 90th pitcher) and
    # this scalar is the lower of the two, so the comparison to the auction
    # intercept below is against the pitcher bar (FINDINGS #68, #69).
    if meta.get("replacement_by_role"):
        rr = meta["replacement_by_role"]
        print(f"replacement roto points, per role:                "
              f"HIT {rr['HIT']:.2f} / PIT {rr['PIT']:.2f}")
    print(f"replacement roto points (scalar used downstream):  {meta['replacement_rp']:.2f}")
    print(f"auction regression intercept (free production):   {exch['intercept']:.2f}")
    print("  -> these two estimate the same quantity from independent data;")
    print("     agreement within ~0.8 roto points is the key validation.")
    print(f"$/roto point, auction opportunity cost:           ${meta['usd_per_rp_keep']:.2f}")
    print(f"$/roto point, redraft budget normalisation:       ${meta['usd_per_rp_redraft']:.2f}")

    k = board[board["keep_2027"]]
    by_team = k.groupby("team").agg(
        n_keep=("name", "size"), keeper_salary=("keeper_cost", "sum"),
        value=("redraft_value", "sum"), surplus=("surplus_redraft", "sum"))
    by_team["auction_budget_left"] = C.BUDGET - by_team["keeper_salary"]
    print("\n=== CHECK 4: optimal 2027 keeper set by team ===")
    print(by_team.sort_values("surplus", ascending=False).round(0).to_string())


LEAGUE_HITTER_SHARE = 0.634      # 4 independent measures span 0.629-0.641 (#64)


def check_role_split():
    """CHECK 5: is the pool that sets `usd_per_rp` one the league could field?

    Under the old "blind" rule the pool was the top 230 by roto points
    regardless of role, which on a projection is 183 hitters and 47 pitchers, a
    set no ten teams could roster, allocating 73.7% of the $2,600 to hitters
    (FINDINGS #64, #65). `POOL_RULE = "slot_role"` now calibrates on the
    fieldable 140/90 with replacement read per role (#68, #69).

    This reads the pool off the SHIPPED board rather than recomputing it. The
    earlier version reimplemented the selection inline and therefore kept
    reporting 183/47 after the rule changed: a check that cannot see the thing
    it checks is worse than no check.
    """
    from klab.board import value_players

    print("\n=== CHECK 5: role split of the calibration pool (#64, #65, #68, #69) ===")
    players, _, meta = value_players()
    n_rost = meta["n_rostered"]
    role = np.where(players["role"] == "PIT", "PIT", "HIT")
    if meta.get("replacement_by_role"):
        pool_idx = pd.concat([
            players[role == "HIT"].nlargest(C.N_TEAMS * C.N_HIT_SLOTS, "roto_points"),
            players[role == "PIT"].nlargest(C.N_TEAMS * C.N_PIT_SLOTS, "roto_points"),
        ]).index
    else:
        pool_idx = players.nlargest(n_rost, "roto_points").index
    pool = players.loc[pool_idx]
    is_hit = np.where(pool["role"] == "PIT", "PIT", "HIT") == "HIT"
    n_h = int(is_hit.sum())
    share = float(pool.loc[is_hit, "redraft_value"].sum()
                  / pool["redraft_value"].sum())

    print(f"pool rule:             {meta.get('pool_rule')}")
    print(f"pool composition:      {n_h} hitters / {len(pool) - n_h} pitchers")
    print(f"league fields:         {C.N_TEAMS*C.N_HIT_SLOTS} hitters / "
          f"{C.N_TEAMS*C.N_PIT_SLOTS} pitchers (by rule)")
    print(f"budget identity:       ${pool['redraft_value'].sum():,.2f} "
          f"(must be ${C.N_TEAMS * C.BUDGET:,})")
    print(f"hitter share of $2,600: {share:6.1%}")
    print(f"league's revealed share: {LEAGUE_HITTER_SHARE:6.1%}  "
          f"(auction spend, roster salary, and roto points delivered all agree)")
    print(f"gap:                    {share - LEAGUE_HITTER_SHARE:+6.1%}")
    # The league's 63-64% is its share of AUCTION SPEND over the players it
    # rosters. The pool's share is model dollars over the calibration pool, a
    # different population: #68 item 5 measured the two and they are not the
    # same quantity. Perfect foresight on completed seasons puts this rule at
    # 52.0-55.1%, so that band, not 63-64%, is where it should sit.
    if not 0.50 <= share <= 0.58:
        print("  OFF THE PERFECT-FORESIGHT BAND (52.0-55.1%, #68). Find out what")
        print("  changed before shipping. Do not 'fix' by splitting the budget: #64.")
    return {"n_hitters": n_h, "hitter_dollar_share": share}


if __name__ == "__main__":
    board, exch, meta = build_board()
    check_2026_standings(board)
    check_players(board)
    check_budget(board, exch, meta)
    check_role_split()
