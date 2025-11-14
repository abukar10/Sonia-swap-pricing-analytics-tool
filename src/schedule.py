from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List

import pandas as pd

from .daycount import year_fraction


@dataclass(frozen=True)
class CashflowPeriod:
    start: date
    end: date
    accrual_factor: float


def generate_schedule(start: date, tenor_years: float, payments_per_year: int, day_count: str) -> List[CashflowPeriod]:
    if payments_per_year <= 0:
        raise ValueError("Payments per year must be positive")

    total_periods = int(round(tenor_years * payments_per_year))
    if not total_periods:
        raise ValueError("Tenor coupled with frequency yields zero periods")

    step_months = int(round(12 / payments_per_year))
    periods: List[CashflowPeriod] = []
    period_start = pd.Timestamp(start)

    for _ in range(total_periods):
        period_end = period_start + pd.DateOffset(months=step_months)
        accrual = year_fraction(period_start.date(), period_end.date(), day_count)
        periods.append(
            CashflowPeriod(
                start=period_start.date(),
                end=period_end.date(),
                accrual_factor=accrual,
            )
        )
        period_start = period_end

    return periods

