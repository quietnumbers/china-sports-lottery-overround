#!/usr/bin/env python3
"""Reproduce the headline numbers of this report from data/overround_897.csv.

Pure standard library, no dependencies.

    python3 overround.py            # print the report
    python3 overround.py --check    # exit non-zero if the numbers moved

Source of data/overround_897.csv: 897 Chinese Sports Lottery (竞彩) matches,
2026-05-17 .. 2026-09-25, each with the three-way fixed odds and, for the same
match, the "99 bookmakers average" closing odds (欧赔 99家平均终指).
"""
import argparse, csv, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, 'data', 'overround_897.csv')

# What the report claims. `--check` verifies these from the shipped CSV.
EXPECT = {'n_pair': 897, 'jc': 1.1292, 'eu': 1.0685, 'jch': 1.1291, 'diff_pp': 6.07}
TOL = 5e-5


def overround(triple):
    """Three odds -> overround, or None if the book is malformed."""
    try:
        h, d, a = (float(x) for x in triple)
    except (TypeError, ValueError):
        return None
    if min(h, d, a) <= 1.0:
        return None
    return 1 / h + 1 / d + 1 / a


def stats_of(vals):
    if not vals:
        return None
    m = st.mean(vals)
    return {'n': len(vals), 'mean': m, 'median': st.median(vals),
            'sd': st.pstdev(vals) if len(vals) > 1 else 0.0,
            'lo': min(vals), 'hi': max(vals),
            'edge': (m - 1) * 100, 'payout': 100.0 / m}


def load(path=CSV):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def collect(rows):
    def tri(r, p):
        return [r.get(p + 'h', ''), r.get(p + 'd', ''), r.get(p + 'a', '')]
    jc = [overround(tri(r, 'jc_')) for r in rows]
    jch = [overround(tri(r, 'jch_')) for r in rows]
    eu = [overround(tri(r, 'eu_')) for r in rows]
    pairs = [(a, b) for a, b in zip(jc, eu) if a and b]
    return ([x for x in jc if x], [x for x in jch if x], [x for x in eu if x], pairs)


def line(name, s):
    if not s:
        return "%-22s  (no data)" % name
    return ("%-22s %5d   %.4f   %6.2f%%   %5.1f%%   %.4f   [%.4f, %.4f]"
            % (name, s['n'], s['mean'], s['edge'], s['payout'], s['sd'], s['lo'], s['hi']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default=CSV)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    rows = load(a.csv)
    jc, jch, eu, pairs = collect(rows)
    s_jc, s_jch, s_eu = stats_of(jc), stats_of(jch), stats_of(eu)
    diffs = [x - y for x, y in pairs]

    print("matches in file: %d   |   jc odds: %d   |   eu odds: %d   |   paired: %d"
          % (len(rows), len(jc), len(eu), len(pairs)))
    print()
    print("%-22s %5s   %6s   %7s   %6s   %6s   %s" %
          ("market", "n", "overround", "vig", "payout", "sigma", "range"))
    print("-" * 96)
    print(line("JC 1X2 (fixed odds)", s_jc))
    print(line("JC handicap", s_jch))
    print(line("EU avg (99 books)", s_eu))
    print()
    print("paired, per match: mean %.2f pp, median %.2f pp, JC more expensive in %d/%d"
          % (st.mean(diffs) * 100, st.median(diffs) * 100, sum(1 for x in diffs if x > 0), len(diffs)))
    print()
    print("multi-leg (vig compounds): each 100 staked ->")
    p = 1.0 / st.mean(jc)          # per-leg payout rate, e.g. 0.8856
    for k in (1, 2, 3, 4, 5, 6, 7, 8):
        ret = 100 * p ** k
        print("   %d-leg   return %6.1f   taken %6.1f" % (k, ret, 100 - ret))

    if a.check:
        got = {'n_pair': len(pairs), 'jc': s_jc['mean'], 'eu': s_eu['mean'],
               'jch': s_jch['mean'], 'diff_pp': round(st.mean(diffs) * 100, 2)}
        bad = []
        for k, v in EXPECT.items():
            if k == 'diff_pp':
                ok = abs(got[k] - v) <= 0.005
            elif k == 'n_pair':
                ok = got[k] == v
            else:
                ok = abs(got[k] - v) <= TOL
            if not ok:
                bad.append("%s: got %s, expected %s" % (k, got[k], v))
        if bad:
            print("\nCHECK FAILED")
            for b in bad:
                print("   " + b)
            raise SystemExit(1)
        print("\nCHECK OK - all headline numbers reproduce from data/overround_897.csv")


if __name__ == '__main__':
    main()
