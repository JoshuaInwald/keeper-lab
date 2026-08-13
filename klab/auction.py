"""Step 3: what a draft dollar actually buys, in roto points.

Pair every auction purchase 2022-2026 with the production that player actually
delivered that season, then regress. Because busts, injuries and outright
releases are all in the sample at the price that was paid, the fitted slope is
the waste-adjusted exchange rate -- not a theoretical SGP ideal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .io import cached
from .denoms import (RotoScorer, denominators_for_level,
                     pooled_relative_dispersion, season_levels, team_baselines,
                     teams_per_category)
from .io import (NameResolver, load_draft_ids, load_drafts,
                 load_hitters_history, load_pitchers_history)


def build_player_pool(hit: pd.DataFrame, pit: pd.DataFrame) -> pd.DataFrame:
    """Name-matching pool: one row per (season, fg_id, role) with a size weight."""
    h = hit[["season", "fg_id", "name"]].copy()
    h["role"] = "HIT"
    h["weight"] = hit["PA"].fillna(0)
    p = pit[["season", "fg_id", "name"]].copy()
    p["role"] = "PIT"
    p["weight"] = pit["IP"].fillna(0) * 4.3      # put IP on a PA-ish scale
    return pd.concat([h, p], ignore_index=True)


@cached
def match_drafts(verbose: bool = True) -> pd.DataFrame:
    """Attach fg_id to every auction purchase, preferring the curated map."""
    drafts = load_drafts()
    hit, pit = load_hitters_history(), load_pitchers_history()
    pool = build_player_pool(hit, pit)
    resolver = NameResolver(pool)

    known = load_draft_ids()[["season", "player", "fg_id"]].dropna()
    known["k"] = known["player"].map(lambda s: s.strip().lower())
    kmap = {(r.season, r.k): int(r.fg_id) for r in known.itertuples()}

    ids, how, conf = [], [], []
    for r in drafts.itertuples():
        pre = kmap.get((r.season, str(r.player).strip().lower()))
        if pre is not None:
            ids.append(pre); how.append("curated"); conf.append(1.0); continue
        if not pd.isna(getattr(r, "fg_id", np.nan)):
            ids.append(int(r.fg_id)); how.append("file"); conf.append(1.0); continue
        role = None
        if isinstance(r.pos, str):
            role = "PIT" if r.pos.strip().upper() in {"SP", "RP", "P"} else "HIT"
        fid, tag, c = resolver.resolve(r.player, r.season, role)
        ids.append(fid); how.append(tag); conf.append(c)

    drafts = drafts.assign(fg_id=ids, match=how, match_conf=conf)
    if verbose:
        print("draft name matching:", drafts["match"].value_counts().to_dict())
        bad = drafts[drafts["fg_id"].isna()]
        if len(bad):
            print(f"  UNMATCHED ({len(bad)}):",
                  bad[["season", "player"]].to_dict("records")[:40])
    return drafts


def score_season(season: int, sigma_rel: pd.DataFrame, levels: pd.DataFrame,
                 hit: pd.DataFrame, pit: pd.DataFrame,
                 baselines: pd.DataFrame) -> pd.DataFrame:
    """Roto points for every player in one season, on that season's scale."""
    L = levels[levels["season"] == season].set_index("category")["level"].to_dict()
    D = denominators_for_level(sigma_rel, L, n_by_cat=teams_per_category())
    b = baselines.set_index("season").loc[season].to_dict()
    sc = RotoScorer(D, b)

    # The FanGraphs hitter export carries a zero-PA row for every pitcher (and
    # vice versa). They contribute nothing to roto points but do decide the
    # role label, so drop them before scoring or every pitcher reads as a
    # hitter.
    h = hit[(hit["season"] == season) & (hit["PA"].fillna(0) > 0)].copy()
    p = pit[(pit["season"] == season) & (pit["IP"].fillna(0) > 0)].copy()
    H = h[["season", "fg_id", "name"]].join(sc.hitters(h))
    H["is_hit"] = 1
    P = p[["season", "fg_id", "name"]].join(sc.pitchers(p))
    P["is_hit"] = 0
    out = pd.concat([H, P], ignore_index=True)
    # Ohtani carries the same fg_id in both files: sum his two lines. The role
    # label rides on a numeric flag rather than a lambda -- a Python-level
    # groupby aggregation over thousands of groups was costing more than the
    # scoring itself.
    agg = {c: "sum" for c in out.columns if c.startswith("rp_")}
    agg["roto_points"] = "sum"
    agg["name"] = "first"
    agg["is_hit"] = "max"
    g = out.groupby(["season", "fg_id"], as_index=False).agg(agg)
    g["role"] = np.where(g["is_hit"] > 0, "HIT", "PIT")
    return g.drop(columns=["is_hit"])


@cached
def auction_sample(seasons=(2022, 2023, 2024, 2025, 2026),
                   sigma_rel: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per auction purchase: price paid + roto points delivered."""
    sigma_rel = pooled_relative_dispersion() if sigma_rel is None else sigma_rel
    levels = season_levels()
    hit, pit = load_hitters_history(), load_pitchers_history()
    bl = team_baselines(list(seasons))

    scored = pd.concat([score_season(s, sigma_rel, levels, hit, pit, bl)
                        for s in seasons], ignore_index=True)
    drafts = match_drafts(verbose=False)
    drafts = drafts[drafts["season"].isin(seasons)].copy()
    # Unmatched names are players who never took an MLB plate appearance or
    # inning that year (Bauer 2022, Painter/Buehler on TJ, deep prospect
    # fliers). That is real money burned, so they stay in at zero.
    drafts["fg_id"] = drafts["fg_id"].fillna(-1).astype(int)

    m = drafts.merge(scored, on=["season", "fg_id"], how="left",
                     suffixes=("", "_fg"))
    # A drafted player with no stat line never appeared: that is a real $0
    # return, not missing data. Keep it at zero roto points.
    m["played"] = m["roto_points"].notna()
    for c in [c for c in m.columns if c.startswith("rp_")] + ["roto_points"]:
        m[c] = m[c].fillna(0.0)
    return m


def regress(df: pd.DataFrame, y="roto_points", x="salary", w=None):
    """Plain OLS with heteroskedasticity-robust errors."""
    import statsmodels.api as sm
    cols = [y, x] + ([w] if w and w not in (y, x) else [])
    d = df[cols].dropna()
    X = sm.add_constant(d[[x]])
    wt = df.loc[d.index, w].to_numpy(dtype=float) if w else None
    mod = sm.WLS(d[y], X, weights=wt) if w is not None else sm.OLS(d[y], X)
    return mod.fit(cov_type="HC1")


def spec_battery(sample: pd.DataFrame) -> pd.DataFrame:
    """The battery from HANDOFF §4 step 3."""
    rows = []

    def add(label, d, y="roto_points", x="salary", w=None, note=""):
        if len(d) < 12:
            return
        r = regress(d, y, x, w)
        rows.append({
            "spec": label, "n": int(r.nobs),
            "intercept": r.params["const"], "slope": r.params[x],
            "slope_se": r.bse[x], "r2": r.rsquared,
            "usd_per_point": (1.0 / r.params[x]) if r.params[x] else np.nan,
            "note": note,
        })

    add("full sample", sample)
    for s in sorted(sample["season"].unique()):
        add(f"season {s}", sample[sample["season"] == s])
    add("hitters", sample[sample["role"] == "HIT"])
    add("pitchers", sample[sample["role"] == "PIT"])
    add("weighted by $", sample, w="salary")
    bins = [(1, 5), (6, 15), (16, 30), (31, 999)]
    for lo, hi in bins:
        d = sample[(sample["salary"] >= lo) & (sample["salary"] <= hi)]
        add(f"price ${lo}-{hi if hi < 999 else '+'}", d)
    add("excl. never-played", sample[sample["played"]],
        note="drops the pure-waste picks; slope should rise")
    s2 = sample.copy()
    s2["log_salary"] = np.log(s2["salary"].clip(lower=1))
    add("log($) -> points", s2, x="log_salary", note="slope = pts per log-$")
    return pd.DataFrame(rows)
