"""Score the exchange-rate estimator family by decisions, not correlations.

Three tests, in the order they bind (HANDOFF "Next session", items 1-2):

  1. BOARD FLIPS. Rebuild the 2027 board under each estimator and count
     keep/cut flips against the shipped board. This is what a different fit
     would change in the room.
  2. REWOUND BACKTEST. Refit each estimator on data that existed before each
     past season and re-score the keep/cut calls it would have produced on
     the 289 decisions of `scripts/backtest_keepers.py`, dollars against
     keep-everything, truth held at the shipped definition.
  3. LOSO SHAPE TEST. Hold out each auction season, fit on the rest, and
     score predicted points-for-salary RMSE: does any non-linear or
     keeper-count term actually transfer across seasons? (#62.5 is the
     cautionary tale: LOSO on three seasons is itself noisy; the decision
     tests above are the acceptance criteria.)

Plus the replacement-anchor section (HANDOFF item 4): the three anchors
rebuilt via `sensitivity.knob`, reported the same way. Keep flips are
expected to be zero there by construction (`KEEP_BASIS = "replacement"`
prices keeps off the exchange rate, which never sees the anchor); what moves
is every redraft price, and the table says by how much.

    PYTHONPATH=.:scripts python3 scripts/exchange_lab.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import klab.config as C
from klab.board import build_board, keep_cost
from klab.exchange import fit_variant

pd.set_option("display.width", 260)

# The full menu. Order is the report order: shipped first, then the linear
# family, then the two curves.
MENU = ["keeper_adjusted", "pick_level", "pick_level_2426", "pooled_2426",
        "pooled_2226", "recent_2026", "window_2425", "partial_pool",
        "median_two_stage", "median_pooled", "projected", "projected_pooled",
        "spline", "tiered_two_stage"]

# Estimators that can honestly be refitted on pre-season data. The two-stage
# trend needs >= 3 prior auctions; projected fits need the Marcel archive
# (2024-26), which kills the keeper-count term (no k variation among priors),
# so the pooled projected form is the testable member of that family.
BACKTEST_MENU = {
    "pooled_prior (shipped backtest)": lambda s: None,   # rewound_exchange itself
    "two_stage_rewound": lambda s: fit_variant("two_stage_rewound",
                                               before_season=s,
                                               k=C.KEEPERS_REMOVED[s]),
    "pick_level": lambda s: fit_variant("pick_level", before_season=s,
                                        k=C.KEEPERS_REMOVED[s]),
    "median_pooled": lambda s: fit_variant("median_pooled", before_season=s),
    "projected_pooled": lambda s: fit_variant("projected_pooled",
                                              before_season=s),
    "spline": lambda s: fit_variant("spline", before_season=s,
                                    k=C.KEEPERS_REMOVED[s]),
    "tiered_two_stage": lambda s: fit_variant("tiered_two_stage",
                                              before_season=s,
                                              k=C.KEEPERS_REMOVED[s]),
}


def section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def board_key(b: pd.DataFrame) -> pd.Index:
    return pd.Index(list(zip(b["fg_id"], b["role"].astype(str))))


def board_flips() -> pd.DataFrame:
    base, base_exch, _ = build_board()
    base = base.set_index(board_key(base))
    sk = base[base["name"] == "Tarik Skubal"]
    rows, flip_names = [], {}
    for name in MENU:
        try:
            v = fit_variant(name)
        except ValueError as e:
            rows.append({"variant": name, "note": f"DEGENERATE: {e}"})
            continue
        b, _, _ = build_board(exch=v)
        b = b.set_index(board_key(b))
        j = base[["name", "keep_2027", "surplus_multiyear"]].join(
            b[["keep_2027", "surplus_multiyear", "keep_value"]], rsuffix="_v",
            how="inner")
        flips = j["keep_2027"] != j["keep_2027_v"]
        flip_names[name] = j.loc[flips, "name"].tolist()
        seg = v.get("segment_usd")
        rows.append({
            "variant": name,
            "usd_per_pt": round(v["usd_per_point"], 2),
            "intercept": round(v["intercept"], 2),
            "n": v["n"],
            "usd_se": round(v["usd_se"], 2) if "usd_se" in v else np.nan,
            "segments": str(seg) if seg else "",
            "keeps": int(b["keep_2027"].sum()),
            "flips": int(flips.sum()),
            "skubal_keep_value": round(
                float(b.loc[b["name"] == "Tarik Skubal", "keep_value"].max()), 2)
            if (b["name"] == "Tarik Skubal").any() else np.nan,
        })
    out = pd.DataFrame(rows)
    section("1. THE 2027 BOARD UNDER EACH ESTIMATOR  (flips vs the shipped board)")
    print(f"shipped: {base_exch['basis']}, ${base_exch['usd_per_point']:.2f}/pt, "
          f"{int(base['keep_2027'].sum())} keeps; Skubal keep_value "
          f"${float(sk['keep_value'].max()):.2f}")
    print(out.to_string(index=False))
    print("\nflipped players (variant: names):")
    for name, names in flip_names.items():
        if names:
            print(f"  {name} ({len(names)}): {', '.join(sorted(names))}")
    return out


def rewound_backtest() -> pd.DataFrame:
    from backtest_keepers import build
    from klab.rewind import rewound_points

    d = build("slot_role")
    # Attach the ex-ante projected roto points each decision was priced on,
    # so a variant's replace-cost can be recomputed from the same projection.
    frames = []
    for s in sorted(d["decision_season"].unique()):
        pts = rewound_points(s)[["fg_id", "roto_points"]]
        sub = d[d["decision_season"] == s].merge(pts, on="fg_id", how="left")
        sub["roto_points"] = sub["roto_points"].fillna(0.0)
        frames.append(sub)
    d = pd.concat(frames, ignore_index=True)

    rows = []
    for label, fitter in BACKTEST_MENU.items():
        for s in sorted(d["decision_season"].unique()):
            sub = d[d["decision_season"] == s]
            if label.startswith("pooled_prior"):
                call = sub["model_replace"]
            else:
                try:
                    v = fitter(s)
                except Exception as e:
                    rows.append({"variant": label, "season": s,
                                 "note": f"n/a: {e}"})
                    continue
                cost = keep_cost(v, sub["roto_points"])
                call = (cost > sub["keeper_salary"]).astype(int)
            keep_all = sub["surplus_true"].sum()
            captured = float((call * sub["surplus_true"]).sum())
            rows.append({
                "variant": label, "season": s, "n": len(sub),
                "kept_%": round(100 * call.mean(), 1),
                "accuracy_%": round(100 * (call == sub["truth"]).mean(), 1),
                "dollars": round(captured, 1),
                "vs_keep_all": round(captured - keep_all, 1),
            })
    out = pd.DataFrame(rows)
    section("2. REWOUND BACKTEST  (each estimator refit on pre-season data only)")
    print("truth fixed at the shipped definition; dollars read against keep-everything.")
    print("2024 has too few prior auctions for trend estimators; blanks are honest.")
    print(out.to_string(index=False))
    return out


def loso_shape() -> pd.DataFrame:
    """Held-out points-for-salary RMSE, one season out at a time."""
    import statsmodels.api as sm
    from klab.exchange import _pwl_design, _sample

    s = _sample(tuple(sorted(C.KEEPERS_REMOVED)))
    specs = {
        "linear": lambda d: sm.add_constant(d[["salary"]]),
        "linear+k": lambda d: pd.DataFrame(
            {"const": 1.0, "k": d["k"], "salary": d["salary"],
             "salary_k": d["salary"] * d["k"]}, index=d.index),
        "spline+k": lambda d: _pwl_design(d, with_k=True),
    }
    rows = []
    for hold in sorted(s["season"].unique()):
        tr, te = s[s["season"] != hold], s[s["season"] == hold]
        row = {"held_out": hold, "n": len(te)}
        for label, X in specs.items():
            r = sm.OLS(tr["roto_points"], X(tr)).fit()
            pred = r.predict(X(te))
            row[f"rmse_{label}"] = round(
                float(np.sqrt(((te["roto_points"] - pred) ** 2).mean())), 3)
        rows.append(row)
    out = pd.DataFrame(rows)
    section("3. LOSO SHAPE TEST  (predict a held-out season's points from price)")
    print("If curvature or the keeper-count term were real signal, their columns")
    print("would win. 2026 is the regime test: k-models extrapolate 29 -> 100.")
    print(out.to_string(index=False))
    means = out[[c for c in out.columns if c.startswith("rmse")]].mean().round(3)
    print("\nmean held-out RMSE:", means.to_dict())
    return out


def anchor_section() -> pd.DataFrame:
    from sensitivity import knob

    base, _, base_meta = build_board()
    base = base.set_index(board_key(base))
    rows = []
    for anchor in ("low", "medium", "high"):
        if anchor == "low":
            b, meta = base, base_meta
        else:
            with knob(WAIVER_VALUE=anchor):
                b, _, meta = build_board()
            b = b.set_index(board_key(b))
        j = base[["keep_2027", "redraft_value"]].join(
            b[["keep_2027", "redraft_value"]], rsuffix="_v", how="inner")
        sk = b[b["name"] == "Tarik Skubal"]
        rows.append({
            "anchor": anchor,
            "replacement": str({k: round(v, 3) for k, v in
                                (meta.get("replacement_by_role") or {}).items()})
            or round(meta["replacement_rp"], 3),
            "usd_per_rp_redraft": round(meta["usd_per_rp_redraft"], 3),
            "keeps": int(b["keep_2027"].sum()),
            "keep_flips": int((j["keep_2027"] != j["keep_2027_v"]).sum()),
            "median_|d_redraft|": round(float(
                (j["redraft_value_v"] - j["redraft_value"]).abs().median()), 2),
            "max_|d_redraft|": round(float(
                (j["redraft_value_v"] - j["redraft_value"]).abs().max()), 2),
            "skubal_redraft": round(float(sk["redraft_value"].max()), 2),
        })
    out = pd.DataFrame(rows)
    section("4. REPLACEMENT ANCHOR  (prices move, keep calls do not: #69/#70 asymmetry)")
    print("keep_2027 runs on keep_value, which never sees the anchor, so zero")
    print("flips is the expected result, and the anchor toggle is a PRICING toggle.")
    print(out.to_string(index=False))
    return out


def main() -> None:
    flips = board_flips()
    bt = rewound_backtest()
    loso = loso_shape()
    anchors = anchor_section()
    flips.to_csv(C.OUT / "exchange_variants.csv", index=False)
    bt.to_csv(C.OUT / "exchange_backtest.csv", index=False)
    loso.to_csv(C.OUT / "exchange_loso.csv", index=False)
    anchors.to_csv(C.OUT / "anchor_variants.csv", index=False)
    print(f"\nwrote exchange_variants/backtest/loso and anchor_variants to {C.OUT}")


if __name__ == "__main__":
    main()
