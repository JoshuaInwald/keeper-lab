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

from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .io import _read_fg_projection, cached
from .config import DATA


_UPLOADS = Path("/mnt/user-data/uploads/Fantasy Baseball")


def _find(fname: str) -> Path:
    """Look in the project data dir first, then the staged uploads dir."""
    for base in (DATA, _UPLOADS):
        p = Path(base) / fname
        if p.exists():
            return p
    raise FileNotFoundError(fname)


def load_zips28_hitters():
    return _read_fg_projection(_find(C.PROJ_2028_HITTERS))


def load_zips28_pitchers():
    return _read_fg_projection(_find(C.PROJ_2028_PITCHERS))


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
        # pass the real reliever flag: passing True for everyone handed each
        # starter the 0.51-save intercept
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


COUNTING = ["PA", "AB", "H", "HR", "R", "RBI", "SB",
            "IP", "W", "SV", "K", "ER", "BB"]


def to_full_time(df: pd.DataFrame, exclude_ids: set | None = None) -> pd.DataFrame:
    """Scale counting stats to a full workload, leaving every rate untouched.

    `exclude_ids` pins the scale at 1.0 for specific players -- used to stop a
    two-way player from collecting both the hitter and the pitcher floor.
    """
    out = df.copy()
    s = pt_scale(df)
    if exclude_ids:
        s = s.where(~out["fg_id"].isin(exclude_ids), 1.0)
    out["pt_scale"] = s
    out["pt_extrapolated"] = s > 1.05
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
    # A salary sitting exactly on a free-agent price is a re-add, not an
    # extension: a $3 draftee who was dropped and claimed back after the
    # break carries $20, which is "above his draft price" for a reason that
    # has nothing to do with extending him.
    #
    # KNOWN GAP (out/FINDINGS.md #32.3): this guard is not always correct.
    # A $5 draft price + a legal +$5 extension also lands on exactly $10; a
    # $15 draft price + $5 lands on $20; a $10 draft price + $10 lands on
    # $20. Those genuine extensions would be wrongly read as re-adds. No
    # current player hits this (checked directly), and there's no data-
    # driven fix without a transaction date, which this project does not
    # have. Left as a documented dormant edge case rather than guessed at.
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

    Year 1 is the 2027 valuation. Later years use the ZiPS 2028 valuation --
    projecting three years out adds noise, not information. Each year past the
    first is discounted.

    **The extension is an option, and it was previously ignored for everyone
    except `F` players.** Any contract reaching its final year can be extended
    at salary + $5, so a code-1 player is not a one-year rental: he is one year
    at salary plus a call option on a second at salary + $5. Leaving it out
    understated cheap young stars badly -- Jhoan Duran at $4 lost roughly $34
    of surplus. The option is only exercised when it is worth exercising, hence
    the clip at zero.

    Returns `extension_years` alongside the dollar figure: 0, 1 or 2, i.e. how
    many years to actually buy. That is the decision, and it is not always the
    maximum -- the second year costs $5 in 2027 money and only pays off if the
    2028 line clears it.
    """
    # A contract is an OPTION to retain, not an obligation. You decide again
    # every winter, so a year you would not exercise costs nothing. The
    # decision under evaluation is 2027, so year one carries its sign; later
    # years clip at zero.
    #
    # As an obligation this charged Kazuma Okamoto -$9.35 for a 2028 season
    # nobody would keep him for, turning a -$3.5 contract into a -$12.8 one.
    # Every multi-year deal was being penalised for its own length.
    y1 = value_2027 - cost
    y2 = ((value_2028 - cost) * C.FUTURE_YEAR_DISCOUNT).clip(lower=0.0)
    y3 = ((value_2028 - cost) * C.FUTURE_YEAR_DISCOUNT ** 2).clip(lower=0.0)
    total = y1 + y2.where(years >= 2, 0.0) + y3.where(years >= 3, 0.0)

    if salary is None:
        ext = pd.Series(0.0, index=total.index)
        ext_yrs = pd.Series(0, index=total.index)
    else:
        # The constitution allows +$5 PER YEAR for one or two years, chosen
        # once. Two cases, and they are not the same problem.
        #
        # (a) LIVE CONTRACT (codes 1-3). The extension is a call option on
        #     seasons *after* the deal expires, exercised at expiry.
        #
        # (b) FINAL YEAR (`F`). The extension IS the keep decision, and
        #     `keeper_cost` already carries the one-year price. But the owner
        #     may instead buy TWO years at +$10, and that alternative was never
        #     priced -- the old code zeroed the option for `F` players on the
        #     grounds that it was "already inside keeper_cost", which is true
        #     of one year and false of two. It forced every final-year star
        #     into a one-year deal. Ohtani: $51 surplus at 1 year, $77 at 2.
        #     The rule is simple once written down -- take the second year iff
        #     the discounted 2028 surplus at salary+$10 clears the extra $5.
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

        # For `F`, express the choice as an increment over the y1 baseline so
        # `surplus_multiyear = total + ext` stays the identity everywhere.
        final = [(pd.Series(0.0, index=total.index), 1)]
        for n_yrs in range(2, C.EXTENSION_MAX_YEARS + 1):
            cost_n = salary + C.EXTENSION_COST * n_yrs
            v = value_2027 - cost_n
            for k in range(1, n_yrs):
                v = v + ((value_2028 - cost_n)
                         * C.FUTURE_YEAR_DISCOUNT ** k).clip(lower=0.0)
            final.append((v - y1, n_yrs))
        final_val, final_yrs = _best(final)

        ext = final_val.where(is_final, live_val)
        ext_yrs = final_yrs.where(is_final, live_yrs)

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
    """fg_id -> position, from the auction files (the only source we have)."""
    from .auction import match_drafts
    d = match_drafts(verbose=False).dropna(subset=["fg_id"])
    d["fg_id"] = d["fg_id"].astype(int)
    return d[d["pos"].notna()].sort_values("season").groupby("fg_id")["pos"].last()


def positional_replacement(players: pd.DataFrame) -> pd.Series:
    """Replacement level computed within each position group.

    OFF by default (config.POSITIONAL_ADJUSTMENT). Two reasons, one empirical
    and one practical.

    Empirical: the published evidence is against it. FanGraphs' 13-system test
    found the variants with the largest positional adjustments finished last,
    and Razzball -- who tested four stances -- measured "very close to zero
    impact". The theoretical appeal is much stronger than the measured effect.

    Practical: **this league does not have the data.** Positions come only
    from the auction files, which cover 51% of rostered players and identify
    just 6 catchers where there must be at least 10. Computing a catcher
    replacement level off 6 observations, most of a roster unlabelled, would
    manufacture precision rather than find it.

    To turn this on for real, the roster export needs a position column (CBS
    publishes one) or a FanGraphs positional-eligibility file. Then this
    becomes a ~20-line change: group by position, take the
    (slots x N_TEAMS)th player in each group as that group's replacement.
    """
    pos = position_map()
    covered = players["fg_id"].map(pos).notna().mean()
    if covered < 0.9:
        raise RuntimeError(
            f"positional adjustment needs position data for ~all players; "
            f"have {covered:.0%}. See the docstring -- get a roster export "
            f"with positions before enabling POSITIONAL_ADJUSTMENT."
        )
    grp = players.assign(pos=players["fg_id"].map(pos))
    out = {}
    for g, slots in C.POSITION_SLOTS.items():
        sub = grp[grp["pos"] == g].nlargest(slots * C.N_TEAMS, "roto_points")
        if len(sub):
            out[g] = float(sub["roto_points"].min())
    return pd.Series(out)
