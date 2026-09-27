#!/usr/bin/env bash
# Reproduce every number in this report. Standard library only, no network.
set -e
cd "$(dirname "$0")"
echo "== overround ($(python3 -c 'print("python")') $(python3 -V 2>&1 | cut -d' ' -f2)) =="
python3 overround.py --check
echo
echo "== backtest =="
python3 backtest.py
echo
echo "== single-file offline HTML =="
python3 make_html.py --check
