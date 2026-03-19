#!/usr/bin/env python3
"""Compute day intervals between diagnosis and treatment start with partial-date bounds.

Usage:
  python compute_interval.py --dx 2021-03-04 --tx 2021-03-20
  python compute_interval.py --dx 2021-03 --tx 2021-04-15
  python compute_interval.py --dx 2021 --tx 2021-04

Inputs:
  --dx / --tx accept: YYYY-MM-DD, YYYY-MM, YYYY

Output: JSON with days (if exact), and days_min/days_max bounds.
"""

from __future__ import annotations

import argparse
import calendar
import json
from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple


@dataclass(frozen=True)
class PartialDate:
    raw: str
    precision: str  # day|month|year
    start: date
    end: date


def parse_partial_date(s: str) -> PartialDate:
    s = s.strip()
    parts = s.split("-")

    if len(parts) == 3:
        y, m, d = map(int, parts)
        dt = date(y, m, d)
        return PartialDate(raw=s, precision="day", start=dt, end=dt)

    if len(parts) == 2:
        y, m = map(int, parts)
        last = calendar.monthrange(y, m)[1]
        return PartialDate(raw=s, precision="month", start=date(y, m, 1), end=date(y, m, last))

    if len(parts) == 1:
        y = int(parts[0])
        return PartialDate(raw=s, precision="year", start=date(y, 1, 1), end=date(y, 12, 31))

    raise ValueError(f"Unrecognized date format: {s}")


def interval_bounds(dx: PartialDate, tx: PartialDate) -> Tuple[Optional[int], int, int]:
    # If both exact days, interval is exact.
    exact = None
    if dx.precision == "day" and tx.precision == "day":
        exact = (tx.start - dx.start).days

    # Bounds:
    # minimum days occurs when tx is as early as possible and dx as late as possible
    days_min = (tx.start - dx.end).days
    # maximum days occurs when tx is as late as possible and dx as early as possible
    days_max = (tx.end - dx.start).days
    return exact, days_min, days_max


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dx", required=True, help="Diagnosis date: YYYY-MM-DD|YYYY-MM|YYYY")
    ap.add_argument("--tx", required=True, help="Treatment start date: YYYY-MM-DD|YYYY-MM|YYYY")
    args = ap.parse_args()

    dx = parse_partial_date(args.dx)
    tx = parse_partial_date(args.tx)

    exact, dmin, dmax = interval_bounds(dx, tx)

    out = {
        "dx": {"raw": dx.raw, "precision": dx.precision, "start": dx.start.isoformat(), "end": dx.end.isoformat()},
        "tx": {"raw": tx.raw, "precision": tx.precision, "start": tx.start.isoformat(), "end": tx.end.isoformat()},
        "days": exact,
        "days_min": dmin,
        "days_max": dmax,
        "negative_flag": (exact is not None and exact < 0) or (dmax < 0),
    }

    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
