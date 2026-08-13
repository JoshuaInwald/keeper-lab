"""How much do the contested modelling choices actually matter?

Six places in this model required a judgment call with no clearly right
answer. Each is defensible; none had been stress-tested. This rebuilds the
whole board under each alternative and reports what actually changes -- not
how much the dollar figures move (they always move), but how many keep-or-cut
decisions flip, which is the only thing that reaches a decision.

    PYTHONPATH=. python3 scripts/sensitivity.py
"""
from contextlib import contextmanager

import numpy as np
import pandas as pd

import klab.auction
import klab.board
import klab.config as C
import klab.denoms
import klab.io
import klab.project
from klab.board import build_board

pd.set_option("display.width", 300)

_CACHED = [
    (klab.io, ["load_hitters_history", "load_pitchers_history", "load_ros_hitters",
               "load_ros_pitchers", "load_zips27_hitters", "load_zips27_pitchers",
               "load_standings_long", "load_drafts", "load_draft_ids",
               "load_contracts", "load_rosters"]),
    (klab.denoms, ["pooled_relative_dispersion", "season_levels", "team_baselines",
                   "teams_per_category"]),
    (klab.project, ["fit_save_model", "project_hitters", "project_pitchers"]),
    (klab.auction, ["match_drafts", "auction_sample"]),
    (klab.board, ["build_2027_scorer", "fit_exchange_rate", "project_all_players",
                  "value_players"]),
]


def _clear_caches():
    for mod, names in _CACHED:
        for n in names:
            fn = getattr(mod, n, None)
            if fn is not None and hasattr(fn, "cache_clear"):
                fn.cache_clear()


@contextmanager
def knob(**overrides):
    """Temporarily override config constants and rebuild from cold.

    Caches are keyed on arguments, not on config, so they must be dropped on
    the way in *and* on the way out -- otherwise a variant leaks into the
    baseline and every later comparison is quietly wrong.
    """
    targets = {}
    for k, v in overrides.items():
        mod = klab.project if k == "RELIABILITY" else C
        targets[k] = (mod, getattr(mod, k))
        setattr(mod, k, v)
    _clear_caches()
    try:
        yield
    finally:
        for k, (mod, old) in targets.items():
            setattr(mod, k, old)
        _clear_caches()


FLAT_RELIABILITY = {k: 1.0 for k in klab.project.RELIABILITY}


VARIANTS = [
    ("baseline", {}),
    ("SV punters included", {"SV_PUNT_THRESHOLD": -1}),
    ("denominators 2022-25", {"DENOM_SEASONS": [2022, 2023, 2024, 2025],
                              "LEVEL_SEASONS": [2022, 2023, 2024, 2025]}),
    ("auction window 2022-26", {"AUCTION_SEASONS": [2022, 2023, 2024, 2025, 2026]}),
    ("flat 50/50 blend", {"RELIABILITY": FLAT_RELIABILITY}),
    ("no playing-time floor", {"MAX_PT_SCALE": 1.0}),
    ("no future discount", {"FUTURE_YEAR_DISCOUNT": 1.0}),
    ("heavy future discount", {"FUTURE_YEAR_DISCOUNT": 0.6}),
]


def run():
    results = {}
    consts = {}
    for label, over in VARIANTS:
        with knob(**over):
            b, exch, meta = build_board()
        results[label] = b.set_index("fg_id")[
            ["name", "team", "keep_2027", "surplus_multiyear", "redraft_value"]]
        consts[label] = {
            "$/roto pt (auction)": exch["usd_per_point"],
            "$/roto pt (redraft)": meta["usd_per_rp_redraft"],
            "replacement rp": meta["replacement_rp"],
            "SV denominator": meta["denominators"]["SV"],
            "ERA denominator": meta["denominators"]["ERA"],
            "keepers flagged": int(b["keep_2027"].sum()),
        }

    print("=" * 100)
    print("MODEL CONSTANTS UNDER EACH VARIANT")
    print("=" * 100)
    print(pd.DataFrame(consts).T.round(3).to_string())

    base = results["baseline"]
    rows = []
    for label, df in results.items():
        if label == "baseline":
            continue
        j = base.join(df, rsuffix="_v", how="inner")
        flips = (j["keep_2027"] != j["keep_2027_v"])
        d = (j["surplus_multiyear_v"] - j["surplus_multiyear"])
        rows.append({
            "variant": label,
            "keep/cut flips": int(flips.sum()),
            "% of roster": 100 * flips.mean(),
            "spearman(surplus)": j["surplus_multiyear"].corr(
                j["surplus_multiyear_v"], method="spearman"),
            "median |Δ$|": float(d.abs().median()),
            "max |Δ$|": float(d.abs().max()),
            "biggest mover": j.loc[d.abs().idxmax(), "name"],
        })
    print()
    print("=" * 100)
    print("DECISION IMPACT  (does the choice change a keep-or-cut call?)")
    print("=" * 100)
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    print()
    print("=" * 100)
    print("PLAYERS WHOSE KEEP/CUT DECISION IS NOT ROBUST")
    print("=" * 100)
    keep = pd.DataFrame({l: d["keep_2027"] for l, d in results.items()})
    unstable = keep[keep.nunique(axis=1) > 1]
    if len(unstable):
        info = base.loc[unstable.index, ["name", "team", "surplus_multiyear"]]
        info["variants_keeping"] = unstable.sum(axis=1)
        info["of_variants"] = keep.shape[1]
        print(info.sort_values("surplus_multiyear", ascending=False).round(1).to_string(index=False))
        print(f"\n{len(unstable)} of {len(base)} rostered players ({100*len(unstable)/len(base):.0f}%) "
              f"flip on at least one modelling choice.")
        print("Everyone else is a keep (or a cut) under every variant -- trust those.")
    else:
        print("none; every decision is robust to all six knobs")

    out = keep.copy()
    out.insert(0, "name", base["name"])
    out.insert(1, "team", base["team"])
    out.to_csv(C.OUT / "sensitivity_keep_flags.csv")
    pd.DataFrame(consts).T.to_csv(C.OUT / "sensitivity_constants.csv")
    print(f"\nwrote {C.OUT/'sensitivity_keep_flags.csv'} and sensitivity_constants.csv")


if __name__ == "__main__":
    run()
