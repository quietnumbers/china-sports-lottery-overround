# China's sports lottery is not a betting market — it's a formula

*I measured the margin on 897 matches. The surprising part is not the size of the fee, but that
the fee barely moves — and what that implies.*

---

The Chinese Sports Lottery (竞彩) publishes fixed odds on football matches. I wanted to know what
they actually cost, so I wrote down the three-way odds for **897 matches** between 2026-05-17 and
2026-09-25, and paired each of them with the same fixture's **"99 bookmakers average"** closing
odds from the European market.

The measure is the **overround**: the sum of the implied probabilities.

```
overround = 1/home + 1/draw + 1/away
payout    = 1 / overround
```

If the odds were fair, overround would be exactly 1.0. Real books are always above 1.0, and the
excess is the margin — the fee you pay *before* your opinion about the match is even relevant.

Here is what 897 matches gave me:

| market | n | overround | margin | σ | range |
|---|---|---|---|---|---|
| Chinese lottery, 1X2 | 897 | 1.1292 | **12.92%** | **0.0006** | 1.1251 – 1.1299 |
| Chinese lottery, handicap | 897 | 1.1291 | 12.91% | 0.0006 | 1.1251 – 1.1299 |
| European average (99 books) | 897 | 1.0685 | 6.85% | 0.0109 | 1.0403 – 1.1085 |

The lottery is more expensive in **897 of 897 matches.** No exceptions. The mean gap is
**6.07 percentage points**.

## The σ is the actual finding

Everyone can guess that a state lottery is expensive. The interesting column is the fourth one.

Across 897 matches — different leagues, different days, different kick-off times — the lottery's
overround stays inside a band **0.0048 wide**. In percentage terms, the margin never leaves
12.51%–12.99%. The European average swings **19× more**, because it is set by people: it follows
league, liquidity, and how close the match is to kick-off.

That difference is not a curiosity. It tells you what kind of object you are looking at:

- **A market price** is produced by the interaction of many participants. It moves, because it
  aggregates disagreement. *A price that moves can be wrong* — and that is exactly what
  professional syndicates spend millions looking for.
- **A formula price** is produced by a fixed payout parameter. It does not move. **A price that
  does not move cannot be wrong.**

The confirmation is inside the same lottery: two *different* play types — 1X2 and handicap — land
on **12.92%** and **12.91%**. The same parameter applied to everything. That is what a formula
looks like.

The practical upshot: there is no mispricing to find here. Not "hard to find" — *nothing to find*.
You are not looking for a bad price in an efficient market; you are looking at a posted fee.

## What the fee does to multi-leg bets

The margin compounds per leg. Per 100 staked, long-run expected return:

| legs | returned | taken |
|---|---|---|
| 1 | 88.6 | 11.4 |
| 2 | 78.4 | 21.6 |
| 4 | 61.5 | 38.5 |
| 6 | 48.2 | **51.8** |
| 8 | 37.8 | **62.2** |

A 6-leg accumulator gives up **more than half**. For scale: American roulette with double zero
takes 5.26%. A 6-leg ticket here takes roughly **10×** that.

This is also why the usual advice — "find value, bet singles, avoid parlays" — is right about
parlays and hopeless about value. You would need a 12.92% edge to break even. Professional
betting teams build models to find **2–4%**. The bar here is 3–6× higher than the edge that
professionals consider a good year.

## I also tested this on myself

To be fair to the other side, I ran **15 betting rules over a 1,617-bet sample** — favourite
backing, home/draw/away, handicap variants, odds-band filters, a model-value filter, and a
daily 2-leg combination. Stated precisely:

- **12 of 15** rules are negative; **9** are significantly negative (95% CI upper bound below 0).
  Worst: −58%.
- **3 of 15** are positive: +23.78% (n=37), +5.79% (n=127), +3.94% (n=52) — and **all three have
  95% confidence intervals that cross zero** (±116%, ±15%, ±86%). The largest makes +143% and
  +43% in its first two months and −100% in each of the last three.
- **0 of 15** pass the rule I fixed *before* looking at the data: n ≥ 300 **and** CI lower
  bound > 0.

So the honest summary is not "every strategy loses." It is: **nothing survives the sample-size
bar, and the positive results are indistinguishable from noise.**

One more result worth keeping, because it is the one thing that *is* real: hit rate rises
monotonically with confidence tier, from 46.6% to 82.2%. The information is there. But the average
odds fall to 1.23, so breaking even needs 81.3% — and the best tier hits 82.2%. It lands exactly
on the margin line. That is what a 12.92% fee looks like from the inside: you can be right, and
still be paying tolls.

## Limitations

- One market, one period: a four-month season fragment, not a full year.
- The benchmark is the 99-bookmaker average **close**, not a single book's live price.
- Overround measures the **price of entry**, not any individual's loss rate — that depends on what
  and how much you actually stake.
- The σ comparison is well supported (overround is a per-match constant). The finer breakdowns —
  by league, by month — are not, and are not claimed here.

## Reproduce it

Everything ships as raw data plus scripts, standard library only, no API keys:

```
git clone https://github.com/quietnumbers/china-sports-lottery-overround
cd china-sports-lottery-overround
./reproduce.sh
```

`overround.py --check` recomputes the headline numbers from the raw odds CSV and **exits
non-zero if any of them moved**. `backtest.py` recomputes the 15-rule table from the per-bet
files. The dataset is also on Kaggle if you would rather poke at it in a notebook.

## Disclaimer

This is data analysis, not betting advice. I do not recommend matches, sell selections, or
promise any return. I measured this number precisely to make the opposite point: **in this market
every strategy must first clear a 12.92% wall.** If it cannot, you are paying someone else's toll.
