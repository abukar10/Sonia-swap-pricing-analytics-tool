from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .curves import CurvePoint, ZeroCurve
from .market_data import load_forward_quotes, load_ois_quotes
from .swap_pricing import SwapDefinition, SwapPricer


BUMP_SIZE_BP = 1.0


def build_curves(
    ois_df: Optional[pd.DataFrame] = None,
    forward_df: Optional[pd.DataFrame] = None,
) -> Tuple[ZeroCurve, ZeroCurve, pd.DataFrame, pd.DataFrame]:
    """Load market quotes and bootstrap SONIA discount and forward curves.
    
    Args:
        ois_df: Optional OIS quotes dataframe. If None, loads from default file.
        forward_df: Optional forward quotes dataframe. If None, loads from default file.
    """
    if ois_df is None:
        ois_df = load_ois_quotes()
    if forward_df is None:
        forward_df = load_forward_quotes()

    discount_curve = ZeroCurve.from_par_swap_dataframe(
        ois_df, name="SONIA OIS Discount", payment_frequency=4
    )
    forward_curve = ZeroCurve.from_par_swap_dataframe(
        forward_df, name="SONIA Forward", payment_frequency=4
    )

    discount_curve_df = discount_curve.as_dataframe()
    forward_curve_df = forward_curve.as_dataframe().rename(
        columns={
            "zero_rate": "forward_zero_rate",
            "discount_factor": "forward_discount_factor",
        }
    )
    return discount_curve, forward_curve, discount_curve_df, forward_curve_df


def bump_curve(curve: ZeroCurve, bump_bp: float) -> ZeroCurve:
    """Apply a parallel bump in basis points to a zero curve."""
    bump = bump_bp / 10_000.0
    tenors = curve.tenors
    base_dfs = np.array([curve.discount_factor(t) for t in tenors])
    bumped_dfs = base_dfs * np.exp(-bump * tenors)
    bumped_rates = -np.log(bumped_dfs) / tenors
    points = [CurvePoint(t, r) for t, r in zip(tenors, bumped_rates)]
    return ZeroCurve(points, name=f"{curve.name} +{bump_bp:.0f}bp", discount_factors=bumped_dfs)


def stress_curves(
    discount_curve: ZeroCurve, forward_curve: ZeroCurve, shift_bp: float
) -> Tuple[ZeroCurve, ZeroCurve]:
    """Produce stressed discount and forward curves via parallel shift."""
    stressed_discount = bump_curve(discount_curve, shift_bp)
    stressed_forward = bump_curve(forward_curve, shift_bp)
    return stressed_discount, stressed_forward


def apply_non_parallel_shift(
    curve: ZeroCurve, tenor_shifts: Dict[float, float]
) -> ZeroCurve:
    """Apply non-parallel shift to curve based on tenor-specific shifts in bp.
    
    Args:
        curve: Base zero curve
        tenor_shifts: Dictionary mapping tenor (years) to shift in basis points
        
    Returns:
        Shifted zero curve with linear interpolation between specified tenors
    """
    tenors = curve.tenors
    base_rates = curve.zero_rates
    
    # Create shift array by interpolating the tenor_shifts
    shifts = np.zeros_like(tenors)
    for i, tenor in enumerate(tenors):
        # Find the shift for this tenor by interpolating
        if tenor in tenor_shifts:
            shifts[i] = tenor_shifts[tenor] / 10_000.0
        else:
            # Interpolate between known shifts
            sorted_tenors = sorted(tenor_shifts.keys())
            if tenor < sorted_tenors[0]:
                shifts[i] = tenor_shifts[sorted_tenors[0]] / 10_000.0
            elif tenor > sorted_tenors[-1]:
                shifts[i] = tenor_shifts[sorted_tenors[-1]] / 10_000.0
            else:
                # Linear interpolation
                for j in range(len(sorted_tenors) - 1):
                    t1, t2 = sorted_tenors[j], sorted_tenors[j + 1]
                    if t1 <= tenor <= t2:
                        shift1 = tenor_shifts[t1] / 10_000.0
                        shift2 = tenor_shifts[t2] / 10_000.0
                        alpha = (tenor - t1) / (t2 - t1) if t2 != t1 else 0
                        shifts[i] = shift1 + alpha * (shift2 - shift1)
                        break
    
    # Apply shifts to rates
    bumped_rates = base_rates + shifts
    
    # Recalculate discount factors
    bumped_dfs = np.exp(-bumped_rates * tenors)
    points = [CurvePoint(t, r) for t, r in zip(tenors, bumped_rates)]
    return ZeroCurve(points, name=f"{curve.name} non-parallel shift", discount_factors=bumped_dfs)


def price_with_non_parallel_shift(
    swap: SwapDefinition,
    discount_curve: ZeroCurve,
    forward_curve: ZeroCurve,
    discount_shifts: Dict[float, float],
    forward_shifts: Dict[float, float],
) -> Dict[str, object]:
    """Price swap with non-parallel shifts and compute impact metrics."""
    # Base pricing
    base_pricer = SwapPricer(discount_curve=discount_curve, forward_curve=forward_curve)
    base_pricing = base_pricer.price(swap)
    base_npv = base_pricing["npv"]
    
    # Apply non-parallel shifts
    shifted_discount = apply_non_parallel_shift(discount_curve, discount_shifts)
    shifted_forward = apply_non_parallel_shift(forward_curve, forward_shifts)
    
    # Price with shifted curves
    shifted_pricer = SwapPricer(discount_curve=shifted_discount, forward_curve=shifted_forward)
    shifted_pricing = shifted_pricer.price(swap)
    shifted_npv = shifted_pricing["npv"]
    
    # Calculate 1bp bump for PV01/DV01 on shifted curves
    bumped_discount = bump_curve(shifted_discount, 1.0)
    bumped_forward = bump_curve(shifted_forward, 1.0)
    bumped_pricer = SwapPricer(discount_curve=bumped_discount, forward_curve=bumped_forward)
    bumped_pricing = bumped_pricer.price(swap)
    shifted_pv01 = bumped_pricing["npv"] - shifted_npv
    shifted_dv01 = shifted_pv01
    
    return {
        "npv": shifted_npv,
        "npv_change": shifted_npv - base_npv,
        "pv01": shifted_pv01,
        "dv01": shifted_dv01,
        "cashflows": shifted_pricing["cashflows"],
    }


def apply_key_rate_shift(
    curve: ZeroCurve, key_tenor: float, shift_bp: float, width: float = None
) -> ZeroCurve:
    """Apply a key rate shift (triangular/tent pattern) to a curve.
    
    The shift follows a triangular pattern centered at key_tenor:
    - Full shift at key_tenor
    - Linearly tapers to zero at key_tenor ± width
    - Zero shift beyond that range
    
    Args:
        curve: Base zero curve
        key_tenor: The tenor node to shift (years)
        shift_bp: Shift amount in basis points
        width: Half-width of the triangular shift pattern (years). 
               If None, uses adaptive width: min(2.0, key_tenor/2, next_key_tenor/2)
        
    Returns:
        Shifted zero curve
    """
    tenors = curve.tenors
    base_rates = curve.zero_rates
    shift_decimal = shift_bp / 10_000.0
    
    # Adaptive width: use wider width for better coverage
    if width is None:
        # Use wider width based on key tenor:
        # - Short tenors (< 1Y): 1.0 year width
        # - Medium tenors (1-5Y): 2.0 years width  
        # - Long tenors (> 5Y): 3.0 years width
        if key_tenor < 1.0:
            width = 1.0
        elif key_tenor <= 5.0:
            width = 2.0
        else:
            width = 3.0
    
    # Calculate triangular shift pattern
    shifts = np.zeros_like(tenors)
    for i, tenor in enumerate(tenors):
        distance = abs(tenor - key_tenor)
        if distance <= width:
            # Triangular pattern: 1.0 at center, 0.0 at edges
            shift_factor = 1.0 - (distance / width)
            shifts[i] = shift_decimal * shift_factor
        else:
            shifts[i] = 0.0
    
    # Apply shifts to rates
    bumped_rates = base_rates + shifts
    
    # Recalculate discount factors
    bumped_dfs = np.exp(-bumped_rates * tenors)
    points = [CurvePoint(t, r) for t, r in zip(tenors, bumped_rates)]
    return ZeroCurve(points, name=f"{curve.name} KR {key_tenor}Y", discount_factors=bumped_dfs)


def calculate_key_rate_dv01(
    swap: SwapDefinition,
    discount_curve: ZeroCurve,
    forward_curve: ZeroCurve,
    key_tenors: list,
    bump_bp: float = 1.0,
) -> Dict[float, float]:
    """Calculate Key Rate DV01 for specified tenor nodes.
    
    Args:
        swap: Swap definition
        discount_curve: Base discount curve
        forward_curve: Base forward curve
        key_tenors: List of key tenor nodes (e.g., [1.0, 2.0, 5.0, 10.0])
        bump_bp: Size of bump in basis points (default 1bp)
        
    Returns:
        Dictionary mapping tenor to DV01 value
    """
    # Base pricing
    base_pricer = SwapPricer(discount_curve=discount_curve, forward_curve=forward_curve)
    base_pricing = base_pricer.price(swap)
    base_npv = base_pricing["npv"]
    
    key_rate_dv01 = {}
    
    for key_tenor in key_tenors:
        # Apply key rate shift to both curves
        shifted_discount = apply_key_rate_shift(discount_curve, key_tenor, bump_bp)
        shifted_forward = apply_key_rate_shift(forward_curve, key_tenor, bump_bp)
        
        # Price with shifted curves
        shifted_pricer = SwapPricer(discount_curve=shifted_discount, forward_curve=shifted_forward)
        shifted_pricing = shifted_pricer.price(swap)
        shifted_npv = shifted_pricing["npv"]
        
        # DV01 is the change in NPV for 1bp shift
        key_rate_dv01[key_tenor] = shifted_npv - base_npv
    
    return key_rate_dv01


def price_with_risk(
    swap: SwapDefinition, discount_curve: ZeroCurve, forward_curve: ZeroCurve, bump_bp: float = BUMP_SIZE_BP
) -> Dict[str, object]:
    """Price swap and compute PV01/DV01 via parallel bump of both curves."""
    pricer = SwapPricer(discount_curve=discount_curve, forward_curve=forward_curve)
    pricing = pricer.price(swap)
    npv = pricing["npv"]

    # Bump both discount and forward curves in parallel for proper PV01 calculation
    # PV01/DV01: Change in present value for a 1bp parallel increase in rates
    bumped_discount = bump_curve(discount_curve, bump_bp)
    bumped_forward = bump_curve(forward_curve, bump_bp)
    bumped_pricing = SwapPricer(discount_curve=bumped_discount, forward_curve=bumped_forward).price(swap)
    pv01 = bumped_pricing["npv"] - npv
    # PV01 and DV01 are the same - both measure dollar value change per 1bp rate move
    dv01 = pv01

    return {
        "pricing": pricing,
        "npv": npv,
        "pv01": pv01,
        "dv01": dv01,
        "cashflows": pricing["cashflows"],
    }


def swap_summary_dataframe(
    swap: SwapDefinition,
    base_metrics: Dict[str, float],
    stressed_metrics: Dict[str, float],
) -> pd.DataFrame:
    """Create summary table with swap terms and pricing metrics."""
    rows = [
        ("Notional", f"£{swap.notional:,.0f}"),
        ("Currency", "GBP"),
        ("Fixed Rate", f"{swap.fixed_rate * 100:.4f} %"),
        ("Swap Type", "Fixed Payer" if swap.payer == "fixed" else "Fixed Receiver"),
        ("Valuation Date", swap.valuation_date.isoformat()),
        ("Effective Date", swap.effective_date.isoformat()),
        ("Maturity", f"{swap.maturity_years:.1f} years"),
        ("Fixed Leg Frequency", f"{swap.fixed_leg_frequency} per year"),
        ("Floating Leg Frequency", f"{swap.floating_leg_frequency} per year"),
        ("Fixed Leg Day Count", swap.fixed_leg_daycount),
        ("Floating Leg Day Count", swap.floating_leg_daycount),
        ("Spread", f"{swap.spread * 100:.2f} bp"),
        ("Mark-to-Market", f"£{base_metrics['npv']:,.2f}"),
        ("PV01", f"£{base_metrics['pv01']:,.2f}"),
        ("DV01", f"£{base_metrics['dv01']:,.2f}"),
        ("Stressed MTM (+50bp)", f"£{stressed_metrics['npv']:,.2f}"),
        ("Stressed PV01 (+50bp)", f"£{stressed_metrics['pv01']:,.2f}"),
        ("Stressed DV01 (+50bp)", f"£{stressed_metrics['dv01']:,.2f}"),
    ]
    return pd.DataFrame(rows, columns=["Attribute", "Value"])


def format_cashflows(cashflows: pd.DataFrame) -> pd.DataFrame:
    """Return nicely formatted cashflow table."""
    df = cashflows.copy()
    money_cols = ["cashflow", "present_value"]
    for col in money_cols:
        df[col] = df[col].apply(lambda x: f"£{x:,.2f}")
    df["coupon_rate"] = df["coupon_rate"].apply(lambda x: f"{x * 100:.4f} %")
    if "forward_rate" in df.columns:
        df["forward_rate"] = df["forward_rate"].apply(lambda x: f"{x * 100:.4f} %" if pd.notnull(x) else "")
    return df


def combined_cashflows_table(cashflows: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fixed and floating legs by payment date."""
    rows = []
    for period_end, group in cashflows.groupby("period_end"):
        discount_factor = group["discount_factor"].mean()
        forward_rate = group.loc[group["leg"] == "floating", "forward_rate"].mean()
        fixed_rate = group.loc[group["leg"] == "fixed", "coupon_rate"].mean()
        floating_rate = group.loc[group["leg"] == "floating", "coupon_rate"].mean()
        rows.append(
            {
                "period_end": period_end,
                "discount_factor": discount_factor,
                "forward_rate": forward_rate,
                "fixed_rate": fixed_rate,
                "floating_rate": floating_rate,
                "fixed_cashflow": group.loc[group["leg"] == "fixed", "cashflow"].sum(),
                "floating_cashflow": group.loc[group["leg"] == "floating", "cashflow"].sum(),
                "net_cashflow": group["cashflow"].sum(),
                "net_present_value": group["present_value"].sum(),
            }
        )
    df = pd.DataFrame(rows).sort_values("period_end").reset_index(drop=True)
    money_cols = ["fixed_cashflow", "floating_cashflow", "net_cashflow", "net_present_value"]
    for col in money_cols:
        df[col] = df[col].apply(lambda x: f"£{x:,.2f}")
    df["forward_rate"] = df["forward_rate"].apply(lambda x: f"{x * 100:.4f} %")
    df["fixed_rate"] = df["fixed_rate"].apply(lambda x: f"{x * 100:.4f} %")
    df["floating_rate"] = df["floating_rate"].apply(lambda x: f"{x * 100:.4f} %")
    return df

