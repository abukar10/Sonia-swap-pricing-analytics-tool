from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import numpy as np
import pandas as pd

from .curves import ZeroCurve
from .daycount import year_fraction
from .schedule import generate_schedule


@dataclass(frozen=True)
class SwapDefinition:
    valuation_date: date
    effective_date: date
    maturity_years: float
    notional: float
    fixed_rate: float
    payer: Literal["fixed", "float"]
    fixed_leg_frequency: int = 2
    floating_leg_frequency: int = 4
    fixed_leg_daycount: str = "30/360"
    floating_leg_daycount: str = "ACT/365"
    spread: float = 0.0


class SwapPricer:
    def __init__(self, discount_curve: ZeroCurve, forward_curve: ZeroCurve):
        self.discount_curve = discount_curve
        self.forward_curve = forward_curve

    def _build_fixed_cashflows(self, swap: SwapDefinition) -> pd.DataFrame:
        schedule = generate_schedule(
            start=swap.effective_date,
            tenor_years=swap.maturity_years,
            payments_per_year=swap.fixed_leg_frequency,
            day_count=swap.fixed_leg_daycount,
        )
        rows = []
        for period in schedule:
            t_pay = year_fraction(swap.valuation_date, period.end, "ACT/365")
            discount = self.discount_curve.discount_factor(t_pay)
            cashflow = swap.notional * swap.fixed_rate * period.accrual_factor
            direction = -1.0 if swap.payer == "fixed" else 1.0
            rows.append(
                {
                    "period_start": period.start,
                    "period_end": period.end,
                    "accrual_factor": period.accrual_factor,
                    "coupon_rate": swap.fixed_rate,
                    "forward_rate": np.nan,
                    "cashflow": direction * cashflow,
                    "discount_factor": discount,
                    "present_value": direction * cashflow * discount,
                    "time_to_payment": t_pay,
                    "leg": "fixed",
                    "projection_rate": swap.fixed_rate,
                }
            )
        return pd.DataFrame(rows)

    def _build_floating_cashflows(self, swap: SwapDefinition) -> pd.DataFrame:
        schedule = generate_schedule(
            start=swap.effective_date,
            tenor_years=swap.maturity_years,
            payments_per_year=swap.floating_leg_frequency,
            day_count=swap.floating_leg_daycount,
        )
        rows = []
        for period in schedule:
            t_start = year_fraction(swap.valuation_date, period.start, "ACT/365")
            t_end = year_fraction(swap.valuation_date, period.end, "ACT/365")
            forward = self.forward_curve.forward_rate(t_start, t_end)
            effective_rate = forward + swap.spread
            cashflow = swap.notional * effective_rate * period.accrual_factor
            discount = self.discount_curve.discount_factor(t_end)
            direction = 1.0 if swap.payer == "fixed" else -1.0
            rows.append(
                {
                    "period_start": period.start,
                    "period_end": period.end,
                    "accrual_factor": period.accrual_factor,
                    "coupon_rate": effective_rate,
                    "forward_rate": forward,
                    "projection_rate": forward,
                    "cashflow": direction * cashflow,
                    "discount_factor": discount,
                    "present_value": direction * cashflow * discount,
                    "time_to_payment": t_end,
                    "leg": "floating",
                }
            )
        return pd.DataFrame(rows)

    def build_cashflows(self, swap: SwapDefinition) -> pd.DataFrame:
        fixed_leg = self._build_fixed_cashflows(swap)
        float_leg = self._build_floating_cashflows(swap)
        return pd.concat([fixed_leg, float_leg], ignore_index=True)

    def price(self, swap: SwapDefinition) -> dict:
        cashflows = self.build_cashflows(swap)
        fixed_pv = cashflows.loc[cashflows["leg"] == "fixed", "present_value"].sum()
        float_pv = cashflows.loc[cashflows["leg"] == "floating", "present_value"].sum()
        npv = fixed_pv + float_pv
        return {
            "cashflows": cashflows.sort_values("period_end").reset_index(drop=True),
            "fixed_leg_pv": fixed_pv,
            "floating_leg_pv": float_pv,
            "npv": npv,
        }

