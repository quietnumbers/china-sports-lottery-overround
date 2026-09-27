#!/usr/bin/env python3
"""Recompute the backtest table of this report from the per-bet files.

Pure standard library. Reads data/trades/*.csv (one row per bet: odds, won/lost,
P/L) and recomputes stake count, hit rate, ROI and the 95% CI from scratch, so
the shipped summary can be checked line by line.

    python3 backtest.py
"""
import csv, glob, math, os, re, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
TRADES = os.path.join(HERE, 'data', 'trades')

# The project's go/no-go rule, fixed in code before looking at results:
#   trade it only if  n >= 300  AND  the 95% CI lower bound of ROI is > 0
MIN_N = 300


def load(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def metrics(rows, unit=1.0):
    pl = [float(r['盈亏']) / unit for r in rows]
    n = len(pl)
    if not n:
        return None
    wins = sum(1 for r in rows if str(r.get('是否中', '')).strip() in ('1', '1.0'))
    roi = st.mean(pl)
    sd = math.sqrt(sum((x - roi) ** 2 for x in pl) / max(n - 1, 1))
    ci = 1.96 * sd / math.sqrt(n)
    odds = [float(r['赔率']) for r in rows if r.get('赔率')]
    return {'n': n, 'wins': wins, 'hit': wins / n, 'roi': roi, 'ci': ci,
            'odds': st.mean(odds) if odds else float('nan'),
            'total': sum(pl)}


def main():
    files = sorted(glob.glob(os.path.join(TRADES, 'trades_*.csv')))
    if not files:
        raise SystemExit("no data/trades/trades_*.csv found")
    out = []
    for f in files:
        name = re.sub(r'^trades_', '', os.path.splitext(os.path.basename(f))[0])
        m = metrics(load(f))
        if m:
            out.append((name, m))
    out.sort(key=lambda t: -t[1]['roi'])

    print("%-4s %6s %8s %9s %10s %10s  %s" %
          ("id", "n", "hit", "ROI", "95%CI", "avg odds", "verdict"))
    print("-" * 88)
    n_pos = n_sig_neg = 0
    for name, m in out:
        lo, hi = m['roi'] - m['ci'], m['roi'] + m['ci']
        if m['roi'] > 0:
            n_pos += 1
        if hi < 0:
            n_sig_neg += 1
        if m['n'] >= MIN_N and lo > 0:
            verdict = "PASSES the rule (n>=300 & CI lo>0)"
        elif m['roi'] > 0:
            verdict = "positive but CI crosses 0 - noise"
        else:
            verdict = "negative"
        print("%-4s %6d %7.1f%% %+8.2f%%   +/-%7.2f%%   %8.2f  %s" %
              (name, m['n'], m['hit'] * 100, m['roi'] * 100, m['ci'] * 100,
               m['odds'], verdict))
    print()
    print("%d strategies total: %d negative, %d positive; "
          "significantly negative (95%% CI upper bound < 0): %d"
          % (len(out), len(out) - n_pos, n_pos, n_sig_neg))
    print("Strategies passing the pre-registered rule (n>=%d and CI lower bound > 0): %d"
          % (MIN_N, sum(1 for _, m in out if m['n'] >= MIN_N and m['roi'] - m['ci'] > 0)))


if __name__ == '__main__':
    main()
