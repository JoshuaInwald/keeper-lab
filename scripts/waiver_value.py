"""ROADMAP item 4: what a team actually gets off the waiver wire.

Replacement level anchors every dollar figure in the project, and it is not a
stable number: it moved 4.811 to 4.599 to 4.733 across two data refreshes in one
day. METHODS section 2.5 lists three routes to it and picks the 230th-best
projection, noting none of the three is fitted to agree with the others.

This adds a fourth, and it is the only one built on what owners DID rather than
on where a ranked list happens to fall. Two roster snapshots 3.5 weeks apart
(2026-08-13 and 2026-09-07) give 38 adds and 39 drops of observed waiver
activity. The margin between what teams reach for and what they discard is the
replacement level they actually face.

Needs the pre-refresh roster snapshot; pass its path as the first argument.

    PYTHONPATH=.:scripts python3 scripts/waiver_value.py OLD_ROSTERS.csv
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from klab import config as C
from klab.board import build_board, value_players
from klab.freeagents import free_agent_board
from price_features import playing_time, scored_history


def main(old_path: str) -> int:
    old = pd.read_csv(old_path)
    new = pd.read_csv(C.DATA / "rosters_valued.csv")
    # The older snapshot stores player_id as text; comparing the raw columns
    # made every one of 276 players look both added and dropped.
    for f in (old, new):
        f["player_id"] = pd.to_numeric(f["player_id"], errors="coerce")
    old = old.dropna(subset=["player_id"]).astype({"player_id": int})
    new = new.dropna(subset=["player_id"]).astype({"player_id": int})
    o, n = set(old["player_id"]), set(new["player_id"])
    added, dropped = sorted(n - o), sorted(o - n)

    board, exch, meta = build_board()
    repl = meta["replacement_rp"]
    players, _, _ = value_players()
    proj = players.groupby("fg_id")[["roto_points", "redraft_value"]].max()

    sc = scored_history()
    a26 = sc[sc["season"] == 2026].groupby("fg_id")["roto_points"].sum()
    pt = playing_time()
    v26 = pt[pt["season"] == 2026].set_index("fg_id")[["PA", "IP"]]

    def describe(ids, label):
        d = pd.DataFrame({"fg_id": ids})
        d["rp_2026"] = d["fg_id"].map(a26)
        d["rp_2027"] = d["fg_id"].map(proj["roto_points"])
        d["value_2027"] = d["fg_id"].map(proj["redraft_value"])
        d["PA"] = d["fg_id"].map(v26["PA"])
        d["IP"] = d["fg_id"].map(v26["IP"])
        nm = dict(zip(new["player_id"], new["name"])) | dict(zip(old["player_id"], old["name"]))
        d["name"] = d["fg_id"].map(nm)
        print(f"\n{label}: n={len(d)}")
        print(f"  2026 roto points   mean {d['rp_2026'].mean():.2f}  "
              f"median {d['rp_2026'].median():.2f}  (replacement {repl:.3f})")
        print(f"  2027 projection    mean {d['rp_2027'].mean():.2f}  "
              f"median {d['rp_2027'].median():.2f}")
        print(f"  2027 value         mean ${d['value_2027'].mean():.2f}  "
              f"median ${d['value_2027'].median():.2f}")
        print(f"  above replacement on 2026: "
              f"{100 * (d['rp_2026'] > repl).mean():.0f}% | on 2027: "
              f"{100 * (d['rp_2027'] > repl).mean():.0f}%")
        return d

    print("=" * 72)
    print("OBSERVED WAIVER ACTIVITY, 2026-08-13 to 2026-09-07 (3.5 weeks)")
    print("=" * 72)
    add = describe(added, "ADDED off the wire")
    drp = describe(dropped, "DROPPED to the wire")

    print("\n" + "=" * 72)
    print("THE MARGIN: what teams reach for vs what they discard")
    print("=" * 72)
    for col, lab in (("rp_2026", "2026 actual"), ("rp_2027", "2027 projected")):
        a, b = add[col].dropna(), drp[col].dropna()
        mid = (a.median() + b.median()) / 2
        print(f"  {lab:16s} added median {a.median():5.2f} | dropped median "
              f"{b.median():5.2f} | midpoint {mid:5.2f}")
    print(f"\n  engine replacement level (230th projection): {repl:.3f}")

    print("\n" + "=" * 72)
    print("HOW MUCH PRODUCTION THE UNROSTERED POOL HOLDS")
    print("=" * 72)
    fa = free_agent_board()
    ros_ids = set(new["player_id"])
    tot_ros = float(board["roto_points"].clip(lower=0).sum())
    # The pool that would fill the league's active slots if every roster
    # emptied: 230 slots, not "230 minus the current roster", which went
    # negative because rosters carry reserves beyond the 23 active spots.
    top_fa = fa.nlargest(C.N_TEAMS * C.N_ACTIVE, "roto_points")
    print(f"  rostered roto points (277 players):        {tot_ros:8.1f}")
    print(f"  best {len(top_fa)} free agents (a full league of them):  "
          f"{float(top_fa['roto_points'].clip(lower=0).sum()):8.1f}")
    print(f"  free agents projecting above replacement:  "
          f"{int((fa['roto_points'] > repl).sum())} of {len(fa)}")

    print("\n  best available, by 2027 projection:")
    print(fa.nlargest(10, "roto_points")[
        ["name", "role", "roto_points", "redraft_value"]].round(2).to_string(index=False))

    out = pd.concat([add.assign(move="added"), drp.assign(move="dropped")])
    out.to_csv(C.OUT / "waiver_moves.csv", index=False)
    print(f"\nwrote {C.OUT / 'waiver_moves.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
