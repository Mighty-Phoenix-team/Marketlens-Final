"""Capture one report through local Team 1, without fetching daily/foreign-flow data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol", nargs="?", default="BBCA")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    symbol = args.symbol.strip().upper().removesuffix(".JK")
    if not re.fullmatch(r"[A-Z]{4}", symbol):
        parser.error("Use an IDX symbol with four letters, e.g. BBCA")
    url = f"{args.base_url.rstrip('/')}/api/assets/{symbol}/company-report"
    try:
        with urlopen(url, timeout=30) as response:
            report = json.load(response)
    except HTTPError as error:
        raise SystemExit(f"Team 1 returned HTTP {error.code}. Check the API response in /docs; no retries were made.")
    except URLError:
        raise SystemExit("Cannot reach Team 1. Start the backend on port 8000 first.")
    target = Path(f"live_company_report_{symbol}.json")
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"Saved {target}. This is the report endpoint only; no daily/foreign-flow request was made.")
    for section in ["overview", "financials", "valuation"]:
        print(f"{section}: {'present' if isinstance(report.get(section), dict) else 'missing/null'}")


if __name__ == "__main__":
    main()
