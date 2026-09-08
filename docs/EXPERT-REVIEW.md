# Expert review sheet: what to ask, and why those questions

Built 2026-09-08 for a sit-down with Pookie 2.0's owner. Numbers from the
committed build; regenerate with `scripts/run_all.py` if the roster has moved.

## The two rules that make this worth doing

**1. Ask blind, then reveal.** For every question below, get his answer BEFORE
showing him the model's. An expert shown a number reviews that number; an expert
asked cold produces an independent estimate. Only the second is comparable, and
only the second can be scored later. This is the whole difference between a chat
and a measurement.

**2. Write the answers down here.** `docs/FINDINGS.md` #69 established that this
model does NOT beat the league's owners out of sample on 289 past decisions. A
strong owner is therefore a better benchmark than the model, and his recorded
calls become a scoreable human baseline for 2027 the way `out/decision_audit.csv`
is for the past. An unrecorded opinion is worth a fraction of a recorded one.

Do NOT ask him things the data already answers: what the denominators are, who
the best player is, whether the standings math is right. Ask only where he has
information the model structurally cannot have.

---

## Q1. Playing time. The highest-value question, because the model genuinely does not know.

ZiPS projects the playing time it EXPECTS, not the playing time a job change
would produce. It has no idea who wins a rotation spot or a closer's job in
March. **44 keeper decisions flip on this assumption alone.**

Ask, for each: **does he get a full workload in 2027, yes or no?** Nothing else.

| player | cost | 2027 PA/IP projected | surplus if projected | surplus if full-time | his call |
|---|---|---|---|---|---|
| Devin Williams | $13 | 55 IP | -$3.9 | **+$44.9** | |
| Grant Taylor | $10 | 69 IP | -$6.5 | +$36.5 | |
| Mason Montgomery | $10 | 80 IP | -$8.2 | +$33.6 | |
| Brandon Woodruff | $1 | 94 IP | -$1.0 | +$18.9 | |
| Chase DeLauter | $5 | 312 PA | -$5.0 | +$18.3 | |
| José Caballero | $14 | 402 PA | -$6.9 | +$16.4 | |
| Jake Bauers | $10 | 404 PA | -$2.6 | +$20.4 | |
| Blake Snell | $7 | 91 IP | -$7.0 | +$14.8 | |
| Edwin Díaz | $16 | 51 IP | -$16.0 | +$12.8 | |
| Luis Robert Jr. | $18 | 404 PA | -$11.6 | +$10.9 | |
| Curtis Mead | $10 | 407 PA | -$8.9 | +$10.4 | |
| Kaelen Culpepper | $20 | 419 PA | -$15.1 | +$4.2 | |

The app now has a `playing time: as projected / full season` selector, so his
answers can be applied directly. A player he says is a full-timer should be read
on the full-season basis and nowhere else.

---

## Q2. The model's biggest and most falsifiable claim: pitchers are underpriced.

**Of the 25 largest gaps between what the model says a player is worth and what
it expects him to cost, 20 are pitchers**, mean gap $14.2. The model is saying
this league systematically underpays for pitching.

| player | keeper cost | model says worth | model says will cost | gap |
|---|---|---|---|---|
| Cade Smith | $10 | $39.9 | $14.6 | **$25.3** |
| Jhoan Duran | $4 | $35.8 | $10.8 | $25.0 |
| Paul Skenes | $15 | $48.3 | $24.0 | $24.3 |
| Tarik Skubal | $38 | $57.8 | $34.0 | $23.8 |
| Mason Miller | $15 | $38.6 | $18.1 | $20.6 |
| Garrett Crochet | $15 | $28.3 | $10.4 | $17.9 |
| Logan Webb | $27 | $31.2 | $14.2 | $17.0 |

**Ask: what do these actually go for in your auction?** Then: **is the room
wrong, or are we?**

This matters more than it looks. If the market really does cap pitchers around
$34 while they produce like $58, that is a repeatable edge worth thousands of
points over the years. If instead the model overvalues pitching, acting on it
walks into a trap every March. The project has evidence pointing both ways: the
revealed market pays pitchers about half the per-point rate of hitters and has
never paid more than $34 for one, while #68 showed every projection system
*compresses* pitchers and therefore understates them. **This claim also got
stronger today**, because the #70 pool fix raised pitcher values; it deserves an
outside check before anyone drafts on it.

---

## Q3. Where a confident model can be confidently wrong.

Coin flips are not interesting: the model already says it does not know. The
diagnostic disagreements are the ones where it is *sure*.

**Expensive players the model says CUT.** Ask him cold: keep or cut?

| player | keeper cost | model's value | model's verdict |
|---|---|---|---|
| Tyler Glasnow | $23 | $0.00 | cut |
| Framber Valdez | $22 | $0.91 | cut |
| Javier Báez | $20 | $0.00 | cut |
| Nick Pivetta | $18 | $0.00 | cut |
| Max Clark | $20 | $3.72 | cut |
| Edwin Díaz | $16 | $0.00 | cut |
| Gerrit Cole | $16 | $0.00 | cut |

**High-surplus keeps the model is certain about.** Ask whether any look wrong:
Skenes ($15 cost, +$134 multi-year), Skubal ($38, +$113), Caminero ($11, +$102),
Neto ($1, +$96), Crow-Armstrong ($17, +$90), Kurtz ($10, +$86), Duran ($4, +$79),
Cade Smith ($10, +$77).

**And the genuine coin flips**, worth asking only because the salaries are large
and he may know something the model cannot: Carroll ($36), Soto ($36), Yamamoto
($32), Schwarber ($20), Bichette ($17), Hader ($15).

---

## Q4. Where the projection disagrees with the season just played.

The `Move` column is 2027 projection minus 2026 production, in standings places.
Large negatives are the projection calling a season unsustainable. **He watched
these players; the projection did not.**

| falling | 2026 | 2027 | move | | rising | 2026 | 2027 | move |
|---|---|---|---|---|---|---|---|---|
| Misiorowski | 17.3 | 7.3 | **-9.9** | | Crochet | -0.1 | 7.9 | **+8.0** |
| Schlittler | 15.3 | 6.3 | -9.0 | | Greene | -0.6 | 4.9 | +5.5 |
| E. Rodriguez | 10.0 | 2.1 | -7.9 | | Senga | -2.3 | 2.0 | +4.3 |
| Sale | 14.4 | 6.8 | -7.6 | | Strider | 0.4 | 4.6 | +4.2 |
| Wacha | 7.6 | 2.5 | -5.1 | | Rooker | 1.7 | 6.0 | +4.3 |

Ask: **which of these does the projection have wrong, and in which direction?**
Caveat worth knowing before weighting his answer: the movers are dominated by
pitchers because pitching is the least projectable thing in the sport, so a
large negative is more often the projection being appropriately humble than the
projection being wrong.

---

## Q5. Two structural questions, which are worth more than any single player.

**How many keepers will the league actually withhold in 2027?** The model now
advises 123 across the league, 12.3 per team, against an observed 100 in 2026
and 29 in the years before. The exchange rate is fitted assuming 100. If he says
the room will keep far fewer, the model is over-keeping; if he says more, auction
inflation is understated and every price on the board is low. **This single
number moves more dollars than any individual call.**

**Does keeping 12-13 per team leave a workable auction?** The model says the
average team spends $139 of its $260 on keepers and enters the auction with $121
for 10-11 slots. Ask whether that is how good teams actually operate here, or
whether owners deliberately keep fewer to preserve auction flexibility that the
model cannot see.

---

## What to do with the answers

1. Record them in the blank columns above and commit.
2. Q1's answers apply immediately through the app's playing-time selector.
3. Q2 is the one to act on or discard before the auction, not during it.
4. Where he and the model disagree confidently, that pair goes on a list to
   score after 2027 is played, which is the only way either of you finds out who
   was right. #69 is the precedent and the method already exists.
