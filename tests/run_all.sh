#!/usr/bin/env bash
# Runs every browser check. Needs Python Playwright with Chromium.
set -eo pipefail
cd "$(dirname "$0")"
for t in test_phone.py test_tablet.py test_update.py test_posters.py; do
  echo "== $t"
  python3 "$t" | tail -1
done
