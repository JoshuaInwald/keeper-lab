"""Full-time playing-time scaling and multi-year keeper surplus.

Two corrections that materially change the board:

1. **Keeper value is a full-season question.** ZiPS applies a player-specific
   durability haircut (Alvarez 474 PA, Witt 656) and gives rookies a partial
   ramp. Valuing a keeper on that line asks "what does he produce if he plays
   the amount ZiPS expects", when the actual decision is "he holds a roster
   spot for a season -- what is that worth". Rates are held fixed and playing
   time is scaled to the floor, capped at MAX_PT_SCALE.

2. **Contracts run multiple years.** A code-"2" contract is two more seasons
   at the same salary, not one. Surplus is summed across the remaining years
   with a per-year discount, using ZiPS 2028 for the out year.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .io import _read_fg_projection, cached
from .config import DATA


def load_zips28_hitters():
    return _read_fg_projection(DATA / C.PROJ_2028_HITTERS)


def load_zips28_pitchers():
    return _read_fg_projection(DATA / C.PROJ_2028_PITCHERS)


def project_2028(saves_2027: pd.Series | None = None) -> pd.DataFrame:
    """2028 lines straight from ZiPS. Two years out there is no in-season
    evidence to blend, so ZiPS is the only source. Saves carry forward from
    the 2027 projection through the same persistence model."""
    from .project import fit_save_model, project_saves

    zh = load_zips28_hitters()
    H = zh[["fg_id", "name", "PA", "AB", "H", "HR", "R", "RBI", "SB"]].groupby(
        "fg_id", as_index=False).agg({"name": "first", **{c: "sum" for c in
        ["PA", "AB", "H", "HR", "R", "RBI", "SB"]}})
    H["AVG"] = H["H"] / H["AB"].replace(0, np.nan)
    H["role"] = "HIT"

    zp = load_zips28_pitchers().rename(columns={"SO": "K"})
    P = zp[["fg_id", "name", "IP", "W", "K", "ER", "BB", "H"]].groupby(
        "fg_id", as_index=False).agg({"name": "first", **{c: "sum" for c in
        ["IP", "W", "K", "ER", "BB", "H"]}})
    P["role"] = "PIT"
    P["ERA"] = P["ER"] * 9.0 / P["IP"].replace(0, np.nan)
    P["WHIP"] = (P["BB"] + P["H"]) / P["IP"].replace(0, np.nan)

    P["reliever"] = P["IP"] < 80
    if saves_2027 is not None:
        m = fit_save_model()
        sv = P["fg_id"].map(saves_2027).fillna(0.0)
        # real reliever flag: True-for-all handed every starter the SV intercept
        P["SV"] = project_saves(sv, m, P["reliever"])
    else:
        P["SV"] = 0.0
    return H, P


# --- playing-time scaling ---------------------------------------------------

def pt_scale(df: pd.DataFrame) -> pd.Series:
    """Multiplier that lifts each player to a full-time workload."""
    pa = df.get("PA", pd.Series(0.0, index=df.index)).fillna(0.0)
    ip = df.get("IP", pd.Series(0.0, index=df.index)).fillna(0.0)
    sv = df.get("SV", pd.Series(0.0, index=df.index)).fillna(0.0)
    rel = df.get("reliever", pd.Series(False, index=df.index)).fillna(False).astype(bool)

    s = pd.Series(1.0, index=df.index)

    is_hit = pa > 0
    s = s.where(~is_hit, np.where(pa > 0, C.KEEPER_PA_FLOOR / pa.replace(0, np.nan), 1.0))

    is_sp = (ip > 0) & (~rel)
    s_sp = np.where(ip > 0, C.KEEPER_IP_FLOOR / ip.replace(0, np.nan), 1.0)
    s = s.where(~is_sp, s_sp)

    # A closer's full season is a save total, not an innings total.
    is_rp = (ip > 0) & rel
    base_rp = np.where(sv >= 5,
                       C.KEEPER_SV_FLOOR / sv.replace(0, np.nan),
                       C.KEEPER_RP_IP_FLOOR / ip.replace(0, np.nan))
    s = s.where(~is_rp, base_rp)

    # Two-way players are scaled on their bat.
    both = is_hit & (ip > 0)
    s = s.where(~both, np.where(pa > 0, C.KEEPER_PA_FLOOR / pa.replace(0, np.nan), 1.0))

    return s.astype(float).fillna(1.0).clip(lower=1.0, upper=C.MAX_PT_SCALE)


def pt_scale_kind(df: pd.DataFrame) -> pd.Series:
    """Which floor `pt_scale()` applied, using the SAME masks in the SAME
    order (docs/FINDINGS.md #53): "health" = scaled to a full healthy workload
    at the existing role; "role" = a 5+ save reliever scaled to KEEPER_SV_FLOOR,
    i.e. a bet on being handed the closer job, a less grounded upside."""
    pa = df.get("PA", pd.Series(0.0, index=df.index)).fillna(0.0)
    ip = df.get("IP", pd.Series(0.0, index=df.index)).fillna(0.0)
    sv = df.get("SV", pd.Series(0.0, index=df.index)).fillna(0.0)
    rel = df.get("reliever", pd.Series(False, index=df.index)).fillna(False).astype(bool)

    is_rp = (ip > 0) & rel & (pa <= 0)   # `both` (two-way) is excluded below regardless
    is_role = is_rp & (sv >= 5)

    both = (pa > 0) & (ip > 0)
    kind = pd.Series(np.where(is_role, "role", "health"), index=df.index)
    return kind.where(~both, "health")


COUNTING = ["PA", "AB", "H", "HR", "R", "RBI", "SB",
            "IP", "W", "SV", "K", "ER", "BB"]


def to_full_time(df: pd.DataFrame, exclude_ids: set | None = None) -> pd.DataFrame:
    """Scale counting stats to a full workload, leaving every rate untouched.

    `exclude_ids` pins the scale at 1.0 for specific players -- used to stop a
    two-way player from collecting both the hitter and the pitcher floor.
    """
    out = df.copy()
    s = pt_scale(df)
    kind = pt_scale_kind(df)
    if exclude_ids:
        excluded = out["fg_id"].isin(exclude_ids)
        s = s.where(~excluded, 1.0)
        kind = kind.where(~excluded, "health")
    out["pt_scale"] = s
    out["pt_extrapolated"] = s > 1.05
    out["pt_scale_kind"] = kind
    for c in COUNTING:
        if c in out:
            out[c] = out[c].fillna(0.0) * s
    return out


# --- multi-year surplus -----------------------------------------------------

def years_controlled(contract) -> int:
    """Seasons of control at the current salary, from 2027 onward.

    An `F` player has none: 2026 was his final year and holding him requires
    an extension, which is priced separately.
    """
    c = str(contract).strip().upper()
    if c in C.YEARS_REMAINING:
        return C.YEARS_REMAINING[c]
    return 1          # F, or unknown -> one extension year


@cached
def already_extended() -> set:
    """Players who have used their one extension, so cannot extend again.

    The constitution allows one extension per contract. A salary above the
    price last paid at auction is the fingerprint of an extension having been
    exercised -- Bryce Harper went for $11 in 2023 and carries $16 today.
    """
    from .auction import match_drafts
    from .io import load_contracts
    d = match_drafts(verbose=False).dropna(subset=["fg_id"]).copy()
    d["fg_id"] = d["fg_id"].astype(int)
    last = d.sort_values("season").groupby("fg_id")["salary"].last()
    c = load_contracts()
    c["draft_salary"] = c["fg_id"].map(last)
    raised = c["draft_salary"].notna() & (c["salary"] > c["draft_salary"])
    # A salary exactly on a FA price ($10/$20) is a re-add, not an extension.
    # KNOWN GAP (FINDINGS #32.3): draft+$5/+$10 can also land there; no
    # current player does, and no transaction date exists to resolve it.
    fa_price = c["salary"].isin([C.FA_SALARY_PRE_ASB, C.FA_SALARY_POST_ASB])
    # A legal extension adds exactly $5 or $10 (one or two years).
    legal = (c["salary"] - c["draft_salary"]).isin(
        [C.EXTENSION_COST * n for n in range(1, C.EXTENSION_MAX_YEARS + 1)])
    used = c[raised & ~fa_price & legal]
    return set(used["fg_id"])


def keeper_cost(salary, contract) -> float:
    """Annual cost of holding the player from 2027 on."""
    c = str(contract).strip().upper()
    if c in C.YEARS_REMAINING:
        return float(salary)
    return float(salary) + C.EXTENSION_COST


def multiyear_surplus(value_2027: pd.Series, value_2028: pd.Series,
                      cost: pd.Series, years: pd.Series,
                      salary: pd.Series | None = None) -> pd.DataFrame:
    """Discounted surplus over the remaining contract, plus the extension.

    Year 1 is the 2027 valuation; later years use the ZiPS 2028 valuation,
    discounted. The extension is a call option (salary + $5/yr, 1 or 2
    years) exercised only when worth it; ignoring it once cost cheap young
    stars ~$34 of surplus. Returns `extension_years` (0/1/2) as the decision.
    """
    # A contract is an OPTION to retain, not an obligation: year one carries
    # its sign, later years clip at zero (an obligation penalised every
    # multi-year deal for its own length, e.g. -$9.35 for an unkept 2028).
    y1 = value_2027 - cost
    y2 = ((value_2028 - cost) * C.FUTURE_YEAR_DISCOUNT).clip(lower=0.0)
    y3 = ((value_2028 - cost) * C.FUTURE_YEAR_DISCOUNT ** 2).clip(lower=0.0)
    total = y1 + y2.where(years >= 2, 0.0) + y3.where(years >= 3, 0.0)

    if salary is None:
        ext = pd.Series(0.0, index=total.index)
        ext_yrs = pd.Series(0, index=total.index)
    else:
        # +$5 PER YEAR for one or two years, chosen once. (a) live contract:
        # a call option on seasons after expiry. (b) final year `F`: the
        # 2-year alternative at +$10 must be priced too, not just the 1-year
        # already inside keeper_cost (zeroing it forced every F star to 1 yr).
        is_final = cost.eq(salary + C.EXTENSION_COST)

        def _best(cands):
            """Elementwise max over (value, n_years) candidates."""
            val = cands[0][0].copy()
            yrs = pd.Series(cands[0][1], index=total.index, dtype=int)
            for v, n in cands[1:]:
                take = v > val
                val = val.where(~take, v)
                yrs = yrs.where(~take, n)
            return val, yrs

        live = [(pd.Series(0.0, index=total.index), 0)]
        for n_yrs in range(1, C.EXTENSION_MAX_YEARS + 1):
            cost_n = salary + C.EXTENSION_COST * n_yrs
            v = pd.Series(0.0, index=total.index)
            for k in range(n_yrs):
                disc = C.FUTURE_YEAR_DISCOUNT ** (years.clip(lower=0) + k)
                v = v + (value_2028 - cost_n) * disc
            live.append((v.clip(lower=0.0), n_yrs))
        live_val, live_yrs = _best(live)

        # `F` choice expressed as an increment over y1 so surplus_multiyear =
        # total + ext holds. Informational only (FINDINGS #39): every `F`
        # player is unkeepable in build_board, which zeroes this downstream.
        final = [(pd.Series(0.0, index=total.index), 1)]
        for n_yrs in range(2, C.EXTENSION_MAX_YEARS + 1):
            cost_n = salary + C.EXTENSION_COST * n_yrs
            v = value_2027 - cost_n
            for k in range(1, n_yrs):
                v = v + ((value_2028 - cost_n)
                         * C.FUTURE_YEAR_DISCOUNT ** k).clip(lower=0.0)
            final.append((v - y1, n_yrs))
        final_val, final_yrs = _best(final)

        # Only code "1" (about to enter his final year) may extend; applying
        # live_val to codes 2/3 handed them a phantom option (FINDINGS #33).
        extend_eligible = (~is_final) & years.eq(1)
        ext = pd.Series(0.0, index=total.index).mask(is_final, final_val).mask(extend_eligible, live_val)
        ext_yrs = pd.Series(0, index=total.index).mask(is_final, final_yrs).mask(extend_eligible, live_yrs)

    return pd.DataFrame({
        "surplus_y2027": y1,
        "surplus_y2028": y2.where(years >= 2, 0.0),
        "surplus_y2029": y3.where(years >= 3, 0.0),
        "extension_option": ext,
        "extension_years": ext_yrs,
        "surplus_multiyear": total + ext,
    })


# --- positional replacement -------------------------------------------------

def position_map() -> pd.Series:
    """fg_id -> position.

    `data/positions_2026.csv` first, then the auction files. The auction files
    alone left 134 of 277 rostered players (48%) with no position at all --
    anyone acquired through free agency rather than bought at auction -- and
    `auction_estimator.find_comps()` silently falls back to the full role for
    those, so half the roster was comped against every hitter or every pitcher
    instead of its own position group (docs/FINDINGS.md #61).

    Hitters in the positions file are the primary position off the league's own
    contracts page. Pitchers are classified SP or RP by career starts share
    (GS/G >= 0.5), which is derived, not hand-entered.
    """
    from .auction import match_drafts
    d = match_drafts(verbose=False).dropna(subset=["fg_id"])
    d["fg_id"] = d["fg_id"].astype(int)
    out = d[d["pos"].notna()].sort_values("season").groupby("fg_id")["pos"].last()

    path = C.DATA / "positions_2026.csv"
    if path.exists():
        cur = pd.read_csv(path)
        cur = cur.dropna(subset=["fg_id", "pos"]).astype({"fg_id": int})
        out = pd.concat([out, cur.set_index("fg_id")["pos"]])
        out = out[~out.index.duplicated(keep="last")]
    return out


def two_position_replacement(players: pd.DataFrame, elig: dict) -> dict:
    """Replacement level for catcher and shortstop only, from real
    eligibility data (`klab.io.load_position_eligibility()`, docs/FINDINGS.md
    #52): Nth-best-at-the-position by roto_points, N = slots x N_TEAMS.
    Every other position stays on the pooled replacement level.
    """
    out = {}
    for g in C.TWO_POS_ADJUST:
        ids = elig.get(g, set())
        sub = players[players["fg_id"].isin(ids)].nlargest(
            C.TWO_POS_SLOTS[g] * C.N_TEAMS, "roto_points")
        if len(sub):
            out[g] = float(sub["roto_points"].min())
    return out
