"""Integrity check on the Marcel archive in `data/`.

The archive was transcribed rather than downloaded (Baseball-Reference returns
403 to automated fetches), so it gets a stronger check than a row count.
Baseball-Reference publishes derived columns alongside the counting stats, and
those are algebraically determined:

    pitchers   WHIP = (BB + H) / IP        ERA  = 9 * ER / IP
               H9   = 9 * H / IP           BB9  = 9 * BB / IP
               SO9  = 9 * SO / IP          SO/W = SO / BB
    hitters    BA   = H / AB               SLG  = TB / AB
               TB   = H + 2B + 2*3B + 3*HR OPS  = OBP + SLG

A transcription error in almost any numeric field breaks at least one identity,
so this catches what a row count cannot. Tolerances match the published rounding
(3 decimals on rates, 2 on ERA/WHIP, 1 on the per-9 rates).

    PYTHONPATH=.:scripts python3 scripts/validate_marcel.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from klab.marcel import SEASONS, load_marcel, marcel_fg_ids


def _check(df, name, lhs, rhs, tol, mask=None):
    """One identity. Returns (n_checked, n_bad, worst_abs_error)."""
    ok = lhs.notna() & rhs.notna() & np.isfinite(lhs) & np.isfinite(rhs)
    if mask is not None:
        ok &= mask
    if not ok.any():
        return 0, 0, 0.0
    err = (lhs[ok] - rhs[ok]).abs()
    bad = err > tol
    return int(ok.sum()), int(bad.sum()), float(err.max())


def check_pitchers(df: pd.DataFrame, season: int) -> int:
    ip, bb, h, er, so = df["IP"], df["BB"], df["H"], df["ER"], df["K"]
    live = ip > 0
    rows = [
        ("WHIP", df["WHIP"], (bb + h) / ip, 0.0015, live),
        ("ERA", df["ERA"], 9 * er / ip, 0.015, live),
        ("H9", df["H9"], 9 * h / ip, 0.06, live),
        ("BB9", df["BB9"], 9 * bb / ip, 0.06, live),
        ("SO9", df["SO9"], 9 * so / ip, 0.06, live),
        ("SO/W", df["SO/W"], so / bb.replace(0, np.nan), 0.006, live & (bb > 0)),
    ]
    return _report(rows, f"marcel_{season}_pitchers", len(df))


def check_hitters(df: pd.DataFrame, season: int) -> int:
    ab, h = df["AB"], df["AB"].where(df["AB"] > 0)
    tb_calc = df["H"] + df["2B"] + 2 * df["3B"] + 3 * df["HR"]
    rows = [
        ("BA", df["AVG"], df["H"] / h, 0.0015, ab > 0),
        ("TB", df["TB"].astype(float), tb_calc.astype(float), 0.5, None),
        ("SLG", df["SLG"], df["TB"] / h, 0.0015, ab > 0),
        ("OPS", df["OPS"], df["OBP"] + df["SLG"], 0.0015, None),
    ]
    return _report(rows, f"marcel_{season}_hitters", len(df))


def _report(rows, label, n_rows) -> int:
    print(f"\n{label}  ({n_rows} rows)")
    failures = 0
    for name, lhs, rhs, tol, mask in rows:
        n, bad, worst = _check(None, name, lhs, rhs, tol, mask)
        flag = "ok  " if bad == 0 else "FAIL"
        print(f"  {flag} {name:<5} checked {n:>5}  violations {bad:>4}  "
              f"worst |err| {worst:.4f}  (tol {tol})")
        failures += bad
    return failures


def main() -> int:
    total = 0
    for season in SEASONS:
        for role, fn in (("HIT", check_hitters), ("PIT", check_pitchers)):
            try:
                df = load_marcel(season, role)
            except FileNotFoundError as e:
                print(f"\nmarcel {season} {role}: MISSING\n  {e}")
                total += 1
                continue
            total += fn(df, season)

    print("\n=== fg_id JOIN COVERAGE ===")
    for season in SEASONS:
        for role in ("HIT", "PIT"):
            try:
                d = marcel_fg_ids(season, role)
            except Exception as e:
                print(f"  {season} {role}: could not join ({e})")
                continue
            n, un = d.attrs["n_total"], d.attrs["n_unmatched"]
            print(f"  {season} {role}: {n - un}/{n} matched to an fg_id "
                  f"({100 * (n - un) / max(n, 1):.1f}%)")

    print("\n=== RELIABILITY (Marcel `Rel`: share carried by the player's own "
          "record) ===")
    for season in SEASONS:
        for role in ("HIT", "PIT"):
            try:
                d = load_marcel(season, role)
            except FileNotFoundError:
                continue
            r = d["rel"].dropna()
            if not len(r):
                continue
            print(f"  {season} {role}: median {r.median():.2f}  "
                  f"p10 {r.quantile(.10):.2f}  p90 {r.quantile(.90):.2f}  "
                  f"| rel<0.30: {int((r < 0.30).sum())} rows "
                  f"({100 * (r < 0.30).mean():.0f}%)")

    print("\n" + ("ALL IDENTITIES HOLD" if total == 0
                  else f"{total} PROBLEMS -- do not use this archive yet"))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
