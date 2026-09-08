# Expert review: what the survey collects, and the two conversations it cannot

`out/keeper_survey.html` now does most of this. It walks a reviewer through all
243 keepable players blind, highest information first, and collects a keep/cut
call plus an auction price. Build and score it per `docs/WORKFLOWS.md` 6b. This
file holds only what a survey cannot ask.

## The two rules that make any of it worth doing

**Ask blind, then reveal.** The survey enforces this by showing no model output
at all: no dollar value, no surplus, no keep flag, no roto points. An expert
shown a number reviews that number; asked cold he produces an independent
estimate, and only the second is comparable to anything. Preserve the same rule
in conversation.

**Record it.** `docs/FINDINGS.md` #69 established that this model does not beat
the league's owners out of sample on 289 past decisions. A strong owner is
therefore a better benchmark than the model, and his recorded calls become a
scoreable human baseline for 2027 the way `out/decision_audit.csv` is for the
past. Do not ask him things the data already answers.

## What the survey covers

| | how it is handled |
|---|---|
| the 44 keeper calls that flip on playing time | ranked first; the one input a human has and a projection does not |
| close calls weighted by dollars at stake | next in the ordering, each card saying why it was ranked there |
| the model's confident calls | included, since a confident model can be confidently wrong |
| auction prices | asked on every cut, plus 18 price-check players either way |

## Conversation 1: the model's most falsifiable claim

**Of the 25 largest gaps between what the model says a player is worth and what
it expects him to cost, 20 are pitchers**, mean gap $14.20. Cade Smith worth
$39.90 and expected to cost $14.60; Skubal $57.80 against $34.00.

The survey's price-check players collect the numbers; `scripts/ingest_survey.py`
reports the role split. But ask him the question directly too: **is the room
wrong, or are we?**

The project has evidence pointing both ways. The revealed market pays pitchers
about half the per-point rate of hitters and has never paid more than $34 for
one. But #68 showed every projection system *compresses* pitchers, which would
mean they are understated rather than overvalued. **The claim also got stronger
when #70 shipped**, since the pool fix raised pitcher values, so it deserves an
outside check before anyone drafts on it. If it holds it is a repeatable edge;
if it does not, acting on it walks into a trap every March.

## Conversation 2: two structural questions worth more than any player

**How many keepers will the league actually withhold in 2027?** The model now
advises 123 across the league, 12.3 per team, against an observed 100 in 2026
and 29 in the years before. The exchange rate is fitted assuming 100. Fewer and
the model is over-keeping; more and auction inflation is understated and every
price on the board is low. **This single number moves more dollars than any
individual call.**

**Does keeping 12-13 per team leave a workable auction?** The model has the
average team spending $139 of its $260 on keepers and entering the auction with
$121 for 10-11 slots. Ask whether that is how good teams here actually operate,
or whether owners deliberately keep fewer to preserve flexibility the model
cannot see.

## What to do with the answers

1. Save each reviewer's file to `data/` and run `scripts/ingest_survey.py`.
2. Read the role-split price calibration first: it settles conversation 1.
3. Playing-time answers apply immediately through the app's `playing time`
   selector.
4. Where he and the model disagree confidently, that pair goes on a list to
   score after 2027 is played. #69 is the precedent and the method exists.
