"""Player value as z-scores: distribution, team totals, and difference-makers.

An independent cross-check on the roto-point engine. Roto points come from
standings dispersion; z-scores come from the *player* distribution. If both
say the same thing about who matters and which teams are good, the engine is
measuring something real rather than an artefact of its own construction.
"""
import numpy as np
import pandas as pd

import klab.config as C
from klab.board import build_2027_scorer
from klab.io import load_standings_long
from klab.trade import standings_points
from scripts.leaderboard_2026 import full_2026

pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 60)


def build():
    scorer, D, base, _ = build_2027_scorer()
    H, P = full_2026()
    Hs = H.join(scorer.hitters(H))
    Ps = P.join(scorer.pitchers(P))

    # z-scores are computed within the ROSTERED pool, not all of MLB: the
    # relevant comparison for a fantasy manager is other players he could
    # actually have, not the 900th-best arm in the majors.
    board = pd.read_csv(C.OUT / "keeper_board_2027.csv")
    rostered = set(board["fg_id"])

    frames = []
    for df, cats in ((Hs, ["R", "HR", "RBI", "SB", "AVG"]),
                     (Ps, ["W", "SV", "K", "ERA", "WHIP"])):
        d = df[df["fg_id"].isin(rostered)].copy()
        for c in cats:
            col = f"rp_{c}"
            d[f"z_{c}"] = (d[col] - d[col].mean()) / d[col].std()
        d["z_total"] = (d["roto_points"] - d["roto_points"].mean()) / d["roto_points"].std()
        frames.append(d)
    return frames, board


def main():
    (Hs, Ps), board = build()
    allp = pd.concat([Hs, Ps], ignore_index=True)

    print("=" * 96)
    print("1. DISTRIBUTION OF 2026 ROTO VALUE ACROSS ROSTERED PLAYERS")
    print("=" * 96)
    rp = allp["roto_points"]
    print(f"  n={len(allp)}  mean={rp.mean():.2f}  sd={rp.std():.2f}  "
          f"skew={rp.skew():.2f}")
    print(f"  quantiles: " + "  ".join(
        f"p{int(q*100)}={rp.quantile(q):.2f}" for q in [.1, .25, .5, .75, .9, .99]))
    print()
    for z in [3, 2, 1.5, 1, 0]:
        n = (allp["z_total"] >= z).sum()
        print(f"  players at z >= {z:+.1f}: {n:3d}  ({100*n/len(allp):4.1f}%)  "
              f"= {n/C.N_TEAMS:.1f} per team")
    print()
    print("  DIFFERENCE-MAKERS (z >= 2):")
    dm = allp.nlargest(18, "z_total")[["name", "roto_points", "z_total"]]
    print("   " + ", ".join(f"{r['name']} ({r.z_total:.1f})" for _, r in dm.iterrows()))

    print("\n" + "=" * 96)
    print("2. DOES SUMMED PLAYER Z PREDICT THE STANDINGS?  (engine cross-check)")
    print("=" * 96)
    m = allp.merge(board[["fg_id", "team"]], on="fg_id", how="inner")
    g = m.groupby("team").agg(
        sum_z=("z_total", "sum"), mean_z=("z_total", "mean"),
        n=("z_total", "size"),
        n_above1=("z_total", lambda s: (s >= 1).sum()),
        n_above2=("z_total", lambda s: (s >= 2).sum()),
        n_below0=("z_total", lambda s: (s < 0).sum()))
    st = load_standings_long()
    wide = st[st["season"] == 2026].pivot(index="team", columns="category", values="total")
    g["standings_pts"] = standings_points(wide[C.CATS])["TOTAL"]
    g = g.sort_values("standings_pts", ascending=False)
    print(g.round(2).to_string())
    from scipy.stats import spearmanr
    for c in ["sum_z", "mean_z", "n_above1", "n_above2", "n_below0"]:
        print(f"  spearman(standings, {c:9s}) = "
              f"{spearmanr(g['standings_pts'], g[c]).statistic:+.3f}")

    print("\n" + "=" * 96)
    print("3. WHERE EACH TEAM'S EDGE COMES FROM (mean z by category)")
    print("=" * 96)
    zc = [f"z_{c}" for c in C.CATS]
    for c in zc:
        if c not in m:
            m[c] = np.nan
    cat = m.groupby("team")[zc].sum().reindex(g.index)
    cat.columns = C.CATS
    print(cat.round(1).to_string())

    print("\n" + "=" * 96)
    print("4. WHAT A DIFFERENCE-MAKER COSTS")
    print("=" * 96)
    lb = pd.read_csv(C.OUT / "leaderboard_2026.csv")
    j = allp.merge(lb[["fg_id", "hindsight_$", "drafted_$", "current_$"]],
                   on="fg_id", how="left")
    j["band"] = pd.cut(j["z_total"], [-9, 0, 1, 2, 9],
                       labels=["below avg", "z 0-1", "z 1-2", "z 2+"])
    b = j.groupby("band", observed=True).agg(
        n=("name", "size"), roto=("roto_points", "mean"),
        hindsight=("hindsight_$", "mean"), paid_at_auction=("drafted_$", "mean"),
        current_salary=("current_$", "mean"))
    print(b.round(2).to_string())
    allp.to_csv(C.OUT / "zscores_2026.csv", index=False)
    print(f"\nwrote {C.OUT/'zscores_2026.csv'}")


if __name__ == "__main__":
    main()
