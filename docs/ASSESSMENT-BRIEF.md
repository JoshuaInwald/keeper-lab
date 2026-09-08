# Assessment phase: closed 2026-09-08

This brief asked how much of the model we actually believed. It was written at
the end of a build phase, ran in two parts on 2026-09-08, and is now **complete**.
The 381-line original is in git history; it is not reproduced here because every
question it raised has since been answered, and in two cases answered the
opposite way from what it expected.

**Where the answers live.** All in `docs/FINDINGS.md`.

| the brief asked | answer |
|---|---|
| Should the budget be split between hitters and pitchers? | **No, refuted.** This league pays $2.092 per realised roto point for hitters and $2.114 for pitchers, a ratio of 0.99 on 668 purchases. #64 |
| Is the calibration pool sound? | **No.** It priced 183 hitters against 47 pitchers where the league fields 140/90. Diagnosed #65, explained #68, fixed #70 |
| Were the owners' past keeper calls good? | Scored, 336 decisions. Their throw-backs beat their keeps. #66 |
| Would the MODEL have beaten them? | **The brief could not ask this; it needed a projection archive.** Archive obtained #67, test run #69: it does not. |

**Two of its conclusions were wrong and are recorded as such**, which is the
reason this file is kept rather than deleted: the budget split it called its
strongest lead is refuted (#64), and the pool repair it queued was rejected on a
benchmark that #68 later withdrew (#70 shipped that repair).

Nothing here is live work. For what to do next read `HANDOFF.md`.
