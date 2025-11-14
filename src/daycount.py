from __future__ import annotations

from dataclasses import dataclass
from datetime import date


def actual_365(start: date, end: date) -> float:
    """Actual/365 Fixed day count fraction."""
    return (end - start).days / 365.0


def thirty_360(start: date, end: date) -> float:
    """30/360 day count fraction using US convention."""
    d1 = min(start.day, 30)
    d2 = min(end.day, 30 if start.day == 30 else end.day)
    return ((end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)) / 360.0


DAYCOUNT_FUNCTIONS = {
    "ACT/365": actual_365,
    "30/360": thirty_360,
}


def year_fraction(start: date, end: date, convention: str) -> float:
    try:
        func = DAYCOUNT_FUNCTIONS[convention.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported day count convention: {convention}") from exc
    return func(start, end)
