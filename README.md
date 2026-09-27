# China's Sports Lottery is not a betting market — it's a formula

*中文版：[README.zh-CN.md](README.zh-CN.md)*

*Also published as a long-form article on [dev.to](https://dev.to/quietnumbers/chinas-sports-lottery-is-not-a-betting-market-its-a-formula-26g).*

**Measured margin on 897 Chinese Sports Lottery (竞彩) football matches: 12.92%.**
The same 897 matches, priced at the European "99 bookmakers average" close: **6.85%.**
The lottery is more expensive in **897 of 897 matches** — no exceptions.

The interesting finding is not that it is expensive. It is *how* it is expensive.

| market | n | overround | margin | payout | σ | range |
|---|---|---|---|---|---|---|
| JC 1X2 (fixed odds) | 897 | 1.1292 | **12.92%** | 88.6% | **0.0006** | 1.1251 – 1.1299 |
| JC handicap | 897 | 1.1291 | 12.91% | 88.6% | 0.0006 | 1.1251 – 1.1299 |
| EU avg (99 books) | 897 | 1.0685 | 6.85% | 93.6% | 0.0109 | 1.0403 – 1.1085 |

σ is 19× tighter in the lottery than in the market. A price that does not move
cannot be wrong — so there is nothing to find here.

Reproduce every number above in one command:

```bash
python3 overround.py --check
```

---

## 1. The measure

Given three-way odds (home / draw / away), the *overround* is the sum of the
implied probabilities:

```
overround = 1/home + 1/draw + 1/away
payout    = 1 / overround
```

If the odds were fair, overround would be exactly 1.0. Real books are always
above 1.0, and the excess is the margin — the fee you pay before your opinion
about the match is even relevant.

## 2. Data and method

- **Sample**: 897 matches, 2026-05-17 → 2026-09-25 (one season fragment).
- **Odds under test**: Chinese Sports Lottery 竞彩 1X2 *fixed* odds, and the
  handicap market on the same matches.
- **Benchmark**: 欧赔 "99 bookmakers average" closing odds — the market
  consensus for the same fixture, from the same page.
- **Method**: compute overround per match for each market; compare pairs.
- Shipped as `data/overround_897.csv` — one row per match, raw odds only;
  all statistics are computed by `overround.py` from that file.
- The numbers here are frozen at the 2026-09-25 cut. The collection pipeline
  that produced them is still running; this repository is a snapshot, not a feed.

## 3. Results

### 3.1 It is a formula, not a market

Look at σ. Across 897 matches the lottery's overround stays inside
1.1251 – 1.1299 — a swing of under half a percentage point. The European
average swings 19× more, following league, liquidity and kick-off time.

- **Market pricing** (EU): produced by the interaction of many participants, so
  it moves. *A moving price can be wrong.*
- **Formula pricing** (JC): produced by a fixed payout parameter. It does not
  move, and therefore **there is no mispricing to find.**

Two independent play types in the lottery (1X2 and handicap) land on 12.92% and
12.91% — the same parameter applied to everything, which is what formula pricing
looks like.

### 3.2 It is more expensive in every single match

897 of 897, mean gap **6.07 percentage points** (median 5.97).

Consequence: a model that is profitable at European margins is *necessarily*
unprofitable here. You need ~6.85% edge to break even against the average book;
you need 12.92% here. Professional syndicates spend millions building models to
find 2–4%. The bar here is 3–6× that.

### 3.3 Multi-leg bets compound the margin

The margin multiplies per leg. Per 100 staked (long-run expected):

| legs | returned | taken |
|---|---|---|
| 1 | 88.6 | 11.4 |
| 2 | 78.4 | 21.6 |
| 4 | 61.5 | 38.5 |
| 6 | 48.2 | **51.8** |
| 8 | 37.8 | **62.2** |

A 6-leg accumulator gives up more than half. For scale: American roulette
(double zero) takes 5.26%. A 6-leg ticket here takes ~10× that.

## 4. I also tested this on myself

I ran 15 betting rules over an extended 1,617-bet sample. Reproduce the table:

```bash
python3 backtest.py
```

Result, stated precisely:

- **12** of 15 rules have a negative point estimate; **9** are significantly
  negative (95% CI upper bound below 0). Worst: −58%, best of the negatives:
  −7.8%.
- **3** rules are positive: +23.78% (n=37), +5.79% (n=127), +3.94% (n=52) —
  and **all three have 95% CIs that cross zero** (±116%, ±15%, ±86%). The
  largest of them makes +143% and +43% in its first two months and −100% in each
  of the last three.
- **0** rules pass the rule I fixed *before* looking at the data: n ≥ 300 **and**
  CI lower bound > 0.
- (Re-running `backtest.py` can differ from `data/backtest_1617_summary.csv` in
  the second decimal: the per-bet files round P/L to 2 decimals. The rule
  verdicts are unaffected.)

So the honest summary is not "every strategy loses" — it is "nothing survives the
sample size bar, and the positive results are indistinguishable from noise."

This is the part that connects to §1–3: the best-looking rule has to clear a
12.92% entry fee, which is 3–6× the edge professional teams are looking for.

> Note on an earlier claim: an earlier write-up of this work also reported a
> "top-confidence tier: 90 bets, 82.2% hit rate, −0.06% ROI". That figure comes
> from a different filter and is **not** reproduced by the code shipped here;
> at n=90 it is below this project's own 100-bet credibility floor. It is
> therefore excluded from the conclusions above.

## 5. Limitations

- One market, one period: a season fragment, not a full year.
- The benchmark is the 99-bookmaker average close, not one book's live price.
- Overround measures the *price of entry*, not any individual's loss rate —
  that depends on what and how much you actually stake.
- The σ comparison is well supported (overround is a per-match constant); the
  finer breakdowns (by league, by month) are not, and are not claimed.
- The 3 positive rules above are reported as noise, not findings.

## 6. Files

| file | what |
|---|---|
| `overround.py` | recomputes §3 from the shipped CSV; `--check` fails loudly if numbers move |
| `backtest.py` | recomputes §4 from the per-bet files |
| `data/overround_897.csv` | 897 matches, raw odds (JC + handicap + EU average) |
| `data/trades/trades_*.csv` | one row per bet for each of the 15 rules |
| `data/backtest_1617_summary.csv` | the summary table as originally produced |
| `CITATION.cff` | machine-readable citation (GitHub shows a "Cite this repository" button) |
| `ARTICLE.en.md` | the same material written as a blog post |
| `make_html.py` | builds `index.html`, the single-file offline version (bilingual, → also `report.pdf` / `report.en.pdf`) |
| `reproduce.sh` | runs everything (including `make_html.py`) |

Standard library only — no dependencies, no API keys, no network.

## 7. Disclaimer

This is data analysis, not betting advice. I do not recommend matches, sell
selections, or promise any return. I measured this number precisely to make the
opposite point: in this market every strategy must first clear a 12.92% wall.
If it doesn't, you are paying someone else's toll.

Corrections welcome — if you can show the numbers are wrong, open an issue.

MIT licensed.

## 8. Offline single file

`python3 make_html.py` builds `index.html` — the whole report as **one self-contained
file** (bilingual, charts are inline SVG, no network, no fonts, no images).
It opens by double-click and can be sent as a single attachment.
`report.pdf` is the same thing printed to PDF (5 pages) - easier to forward in chat apps.
