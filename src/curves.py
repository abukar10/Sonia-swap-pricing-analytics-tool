from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CurvePoint:
    tenor: float  # in years
    rate: float   # annualised continuously compounded rate


class ZeroCurve:
    """Simple continuously-compounded zero curve with linear interpolation in rates."""

    def __init__(
        self,
        points: Iterable[CurvePoint],
        name: str,
        discount_factors: Optional[Iterable[float]] = None,
    ):
        pts = sorted(points, key=lambda p: p.tenor)
        if pts[0].tenor <= 0:
            raise ValueError("Tenors must be positive")
        self._tenors = np.array([p.tenor for p in pts], dtype=float)
        self._rates = np.array([p.rate for p in pts], dtype=float)
        self.name = name
        if discount_factors is not None:
            dfs = np.array(list(discount_factors), dtype=float)
            if dfs.shape != self._tenors.shape:
                raise ValueError("Discount factors must align with tenor points")
            self._discount_factors = dfs
        else:
            self._discount_factors = None

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, name: str) -> "ZeroCurve":
        required_cols = {"tenor_years", "rate"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"Zero curve dataframe must contain columns {required_cols}")
        points = [CurvePoint(row.tenor_years, row.rate) for row in df.itertuples()]
        discount_factors = np.exp(-df["rate"].to_numpy(dtype=float) * df["tenor_years"].to_numpy(dtype=float))
        return cls(points, name=name, discount_factors=discount_factors)

    @classmethod
    def from_par_swap_dataframe(
        cls,
        df: pd.DataFrame,
        name: str,
        payment_frequency: int = 4,
    ) -> "ZeroCurve":
        """Bootstrap zero curve from par swap rates using standard coupon-stripping."""
        required_cols = {"tenor_years", "rate"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"Par swap dataframe must contain columns {required_cols}")

        if payment_frequency <= 0:
            raise ValueError("Payment frequency must be positive")

        sorted_df = df.sort_values("tenor_years").reset_index(drop=True)
        par_tenors = sorted_df["tenor_years"].to_numpy(dtype=float)
        par_rates = sorted_df["rate"].to_numpy(dtype=float)

        max_tenor = par_tenors[-1]
        steps = int(np.round(max_tenor * payment_frequency))
        if steps <= 0:
            raise ValueError("Insufficient tenor coverage for bootstrapping")

        tenors = np.arange(1, steps + 1, dtype=float) / payment_frequency
        accruals = np.diff(np.concatenate(([0.0], tenors)))

        discount_factors = np.empty_like(tenors)

        for idx, (tenor, accrual) in enumerate(zip(tenors, accruals)):
            par_rate = float(np.interp(tenor, par_tenors, par_rates))
            if idx == 0:
                discount_factors[idx] = 1.0 / (1.0 + par_rate * accrual)
                continue

            pv_previous_coupons = par_rate * np.sum(accruals[:idx] * discount_factors[:idx])
            numerator = 1.0 - pv_previous_coupons
            denominator = 1.0 + par_rate * accrual
            discount_factors[idx] = numerator / denominator

        zero_rates = -np.log(discount_factors) / tenors
        points = [CurvePoint(t, r) for t, r in zip(tenors, zero_rates)]
        return cls(points, name=name, discount_factors=discount_factors)

    @property
    def tenors(self) -> np.ndarray:
        return self._tenors.copy()

    @property
    def zero_rates(self) -> np.ndarray:
        return self._rates.copy()

    def zero_rate(self, tenor: float) -> float:
        if tenor <= 0:
            return self._rates[0]
        if tenor >= self._tenors[-1]:
            return self._rates[-1]
        return float(np.interp(tenor, self._tenors, self._rates))

    def discount_factor(self, tenor: float) -> float:
        if tenor <= 0:
            return 1.0
        if self._discount_factors is not None:
            if tenor <= self._tenors[0]:
                rate = self._rates[0]
                return float(np.exp(-rate * tenor))
            if tenor >= self._tenors[-1]:
                last_df = self._discount_factors[-1]
                last_tenor = self._tenors[-1]
                rate = self._rates[-1]
                extension = tenor - last_tenor
                return float(last_df * np.exp(-rate * extension))
            log_dfs = np.log(self._discount_factors)
            log_df = float(np.interp(tenor, self._tenors, log_dfs))
            return float(np.exp(log_df))
        rate = self.zero_rate(tenor)
        return float(np.exp(-rate * tenor))

    def forward_rate(self, start: float, end: float) -> float:
        if end <= start:
            raise ValueError("End tenor must be greater than start tenor")
        df_start = self.discount_factor(start)
        df_end = self.discount_factor(end)
        return float(np.log(df_start / df_end) / (end - start))

    def as_dataframe(self) -> pd.DataFrame:
        discounts = np.array([self.discount_factor(t) for t in self._tenors])
        return pd.DataFrame(
            {
                "tenor_years": self._tenors,
                "zero_rate": self._rates,
                "discount_factor": discounts,
            }
        )
