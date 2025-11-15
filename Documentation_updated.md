<style>
/* Style for section headings - Blue color */
h2 {
    color: #0066cc;
    font-size: 1.5em;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    font-weight: 600;
}

h3 {
    color: #0066cc;
    font-size: 1.2em;
    margin-top: 1.2em;
    margin-bottom: 0.6em;
    font-weight: 600;
}

h4 {
    color: #0066cc;
    font-size: 1.1em;
    margin-top: 1em;
    margin-bottom: 0.5em;
    font-weight: 600;
}

/* Smaller text size for body */
body {
    font-size: 14px;
    line-height: 1.6;
}

p {
    font-size: 14px;
    line-height: 1.6;
}

li {
    font-size: 14px;
    line-height: 1.6;
}

/* Table of contents styling */
h1 {
    color: #003366;
    font-size: 1.8em;
    margin-bottom: 0.5em;
}

/* Code blocks */
code {
    font-size: 13px;
}

/* Strong text */
strong {
    color: #004080;
    font-weight: 600;
}
</style>

# GBP SONIA Interest Rate Swap Pricing Analytics Tool - Technical Documentation

## Table of Contents
1. [What It Is](#what-it-is)
2. [Pricing Methodology](#pricing-methodology)
3. [Input Curves](#input-curves)
4. [Curve Construction Methodology](#curve-construction-methodology)
5. [Model Assumptions](#model-assumptions)
6. [Stress Testing](#stress-testing)
7. [Non-Parallel Shift Impact](#non-parallel-shift-impact)
8. [Trade Risks](#trade-risks)
9. [Recalibration with New Market Data](#recalibration-with-new-market-data)
10. [End-to-End Deployment Guide](#end-to-end-deployment-guide)
11. [Limitations and Missing Features](#limitations-and-missing-features)

---

## What It Is

The **GBP SONIA Interest Rate Swap Pricing Analytics Tool** is a prototype model, valuation and risk validation tool for GBP (British Pound) Interest Rate Swaps (IRS) that reference SONIA (Sterling Overnight Index Average). 

### Key Capabilities:
- **Pricing Engine**: Real-time mark-to-market (MTM) valuation of interest rate swaps
- **Curve Construction**: Bootstrapping of discount and forward curves from market quotes
- **Risk Analytics**: Calculation of PV01, DV01, and Key Rate DV01 (bucketed risk)
- **Stress Testing**: Parallel and non-parallel curve shift scenarios
- **Interactive Dashboard**: Streamlit-based web interface for real-time analysis
- **Market Data Integration**: Upload and override market curves for daily recalibration

### Target Users:
- Model validation teams to adopt this prototype
- Testing teams. 
- junior developers new to swaps price analytics 
- anyone who is interested in end-to-end derivative pricing and deployment

---

## Pricing Methodology

### Overview
The tool implements a **multi-curve framework** consistent with post-LIBOR market standards, where:
- **Discounting** uses the SONIA OIS (Overnight Indexed Swap) curve
- **Forward rate projection** uses a separate SONIA swap curve

This separation is critical because SONIA OIS rates (used for discounting) and SONIA swap rates (used for projection) can differ due to credit and liquidity premiums.

### Pricing Formula

The net present value (NPV) of an interest rate swap is calculated as:

$$NPV = PV_{Fixed} + PV_{Floating}$$

Where:

**Fixed Leg Present Value:**
$$PV_{Fixed} = \sum_{i=1}^{n} N \times R_{fixed} \times \tau_i \times P(0, T_i) \times Direction$$

**Floating Leg Present Value:**
$$PV_{Floating} = \sum_{j=1}^{m} N \times F(T_{j-1}, T_j) \times \tau_j \times P(0, T_j) \times Direction$$

**Notation:**
- $N$ = Notional amount
- $R_{fixed}$ = Fixed coupon rate
- $F(T_{j-1}, T_j)$ = Forward rate from $T_{j-1}$ to $T_j$ (from forward curve)
- $\tau_i, \tau_j$ = Accrual factors (day count fractions)
- $P(0, T)$ = Discount factor from valuation date to time $T$ (from discount curve)
- $Direction$ = +1 for fixed receiver, -1 for fixed payer

## Stress Testing

### Parallel Stress Testing

**What It Does**: Applies a uniform shift (in basis points) to both the discount and forward curves simultaneously.

**Implementation**:
- Shifts all zero rates by the same amount: $r_{new}(T) = r_{old}(T) + \Delta r$
- Recalculates discount factors: $P_{new}(0, T) = P_{old}(0, T) \times e^{-\Delta r \times T}$
- Reprices the swap with shifted curves

**Default Stress**: +50 basis points (0.50%)

**Outputs**:
- **Stressed MTM**: New mark-to-market value after the shift
- **Stressed PV01/DV01**: Risk metrics calculated on the stressed curves
- **Curve Visualization**: Shows curves before and after the stress

**Use Cases**:
- Understanding swap sensitivity to overall rate movements
- Regulatory stress testing (e.g., Basel III)
- Portfolio-level risk assessment

**Example**: If a swap has an MTM of £100,000 and a +50bp stress results in an MTM of £150,000, the swap gains £50,000 in a rising rate environment (if receiving fixed).

### Non-Parallel Stress Testing

**What It Does**: Applies tenor-specific shifts to the curves, allowing different parts of the curve to shift by different amounts.

**Implementation**:
- User specifies shifts for specific tenors (e.g., 1Y: +5bp, 5Y: +10bp, 10Y: 0bp, 30Y: -5bp)
- Linear interpolation is used between specified tenors
- Both discount and forward curves are shifted independently (user can specify different shifts for each)

**Outputs**:
- **Shifted MTM**: New mark-to-market value
- **MTM Change**: Difference from base MTM
- **Shifted PV01/DV01**: Risk metrics on shifted curves
- **Impact Analysis**: Shows how the swap responds to curve shape changes

**Use Cases**:
- **Yield Curve Steepening/Flattening**: Understanding swap sensitivity to curve shape changes
- **Key Rate Risk**: Identifying which parts of the curve drive swap value
- **Scenario Analysis**: Modeling specific market scenarios (e.g., short rates rise while long rates fall)

**Example Scenarios**:
- **Steepening**: Short rates (+10bp) rise more than long rates (+2bp) → Typically benefits fixed receivers
- **Flattening**: Long rates (+10bp) rise more than short rates (+2bp) → Typically benefits fixed payers
- **Inversion**: Short rates rise while long rates fall → Complex impact depending on swap structure

---

## Non-Parallel Shift Impact

### What It Measures

The non-parallel shift impact analysis quantifies how a swap's value changes when different parts of the yield curve move by different amounts. This is critical for understanding **curve risk** (also called **yield curve risk** or **shape risk**).

### Key Rate DV01 (Bucketed DV01)

**Definition**: The change in swap value (in currency units) for a 1 basis point shift at a specific tenor node, with the shift tapering to zero at adjacent nodes.

**Calculation Method**:
1. Apply a **triangular (tent) shift** centered at the key tenor
2. The shift is full (1bp) at the key tenor
3. The shift tapers linearly to zero at key_tenor ± width
4. Width is adaptive:
   - Short tenors (< 1Y): 1.0 year width
   - Medium tenors (1-5Y): 2.0 years width
   - Long tenors (> 5Y): 3.0 years width

**Formula for Triangular Shift**:
$$Shift(T) = \begin{cases}
\Delta r \times \left(1 - \frac{|T - T_{key}|}{width}\right) & \text{if } |T - T_{key}| \leq width \\
0 & \text{otherwise}
\end{cases}$$

**Output**: A dictionary mapping each key tenor to its DV01 contribution

**Example**: If 5Y Key Rate DV01 = £500, then a 1bp rise in the 5Y rate (with tapering) causes the swap to gain/lose £500.

### Aggregation Property

**Important**: The sum of all Key Rate DV01s should approximately equal the total parallel DV01:

$$\sum_{i} KR\_DV01(T_i) \approx Parallel\_DV01$$

This property allows traders to:
- **Decompose risk**: Understand which tenors drive the swap's sensitivity
- **Hedge selectively**: Hedge specific curve segments rather than the entire curve
- **Portfolio optimization**: Match key rate exposures across a portfolio

### What to Expect

1. **Short-Dated Swaps (< 5 years)**:
   - Highest sensitivity to short-term rates (1Y, 2Y)
   - Lower sensitivity to long-term rates (10Y, 30Y)

2. **Long-Dated Swaps (> 10 years)**:
   - Significant sensitivity to long-term rates (10Y, 30Y)
   - Lower sensitivity to short-term rates

3. **At-the-Money Swaps**:
   - Key Rate DV01s are typically small (swap is near par)
   - Risk increases as swap moves in/out of the money

4. **In-the-Money Swaps**:
   - Higher absolute Key Rate DV01s
   - More sensitive to curve movements

5. **Fixed Receiver Swaps**:
   - Positive Key Rate DV01s (gain when rates rise)
   - Benefit from curve steepening

6. **Fixed Payer Swaps**:
   - Negative Key Rate DV01s (lose when rates rise)
   - Benefit from curve flattening

### Practical Applications

- **Risk Management**: Identify and hedge specific curve exposures
- **Trading**: Understand which curve movements benefit/harm the position
- **Portfolio Construction**: Build portfolios with desired curve risk profiles
- **Regulatory Reporting**: Some regulations require bucketed risk reporting

---

## Trade Risks

### 1. **Interest Rate Risk (Delta Risk)**

**Definition**: Sensitivity of swap value to changes in interest rates.

**Metrics**:
- **PV01 (Present Value of 01)**: Change in swap value for a 1 basis point parallel increase in rates
- **DV01 (Dollar Value of 01)**: Same as PV01 (used interchangeably)
- **Key Rate DV01**: Sensitivity to shifts at specific curve points

**Interpretation**:
- **Positive PV01**: Swap gains value when rates rise (typical for fixed receiver)
- **Negative PV01**: Swap loses value when rates rise (typical for fixed payer)
- **Magnitude**: Larger PV01 = higher interest rate risk

**Hedging**: Can be hedged with offsetting swaps or interest rate futures.

### 2. **Curve Risk (Shape Risk)**

**Definition**: Sensitivity to non-parallel changes in the yield curve (steepening, flattening, inversion).

**Metrics**:
- **Key Rate DV01**: Shows exposure to specific curve segments
- **Non-Parallel Shift Impact**: Quantifies impact of curve shape changes

**Interpretation**:
- **Steepening Risk**: Swap value changes when short and long rates diverge
- **Flattening Risk**: Swap value changes when curve becomes flatter
- **Hump Risk**: Sensitivity to mid-curve (5Y-10Y) movements

**Hedging**: Requires instruments with offsetting curve risk profiles.

### 3. **Basis Risk**

**Definition**: Risk that the spread between OIS (discount) and swap (forward) curves changes.

**Current Limitation**: The tool does not explicitly model basis risk, but it exists implicitly:
- If OIS-SONIA swap basis widens, discounting changes while forward rates may not
- This affects swap valuation, especially for longer-dated swaps

**Mitigation**: Monitor basis spreads and recalibrate curves regularly.

### 4. **Spread Risk**

**Definition**: If a spread is added to the floating leg, changes in that spread affect swap value.

**Current Feature**: The tool allows adding a spread to floating rates, but does not separately risk this spread.

### 5. **Time Decay (Theta)**

**Definition**: As time passes, the swap's remaining life decreases, affecting its value.

**Current Limitation**: The tool does not explicitly calculate theta, but it's implicitly captured when repricing with updated valuation dates.

### 6. **Convexity Risk (Gamma)**

**Definition**: The change in PV01 as rates change (second-order sensitivity).

**Current Limitation**: The tool does not calculate convexity/gamma. This is important for:
- Large rate movements
- Options embedded in swaps
- Portfolio-level risk management

**Formula** (not currently implemented):
$$\Gamma = \frac{\partial^2 PV}{\partial r^2}$$

### 7. **Liquidity Risk**

**Definition**: Risk that the swap cannot be unwound or hedged at fair value due to market illiquidity.

**Current Limitation**: Not explicitly modeled, but affects:
- Bid-ask spreads (not captured in pricing)
- Ability to exit positions
- Market data availability

### 8. **Model Risk**

**Definition**: Risk that the pricing model is incorrect or mis-specified.

**Sources**:
- Interpolation assumptions (linear vs. spline)
- Extrapolation assumptions (flat vs. forward-looking)
- Day count conventions
- Payment frequency assumptions

**Mitigation**: Regular model validation, back-testing, and comparison with market prices.

### 9. **Operational Risk**

**Definition**: Risk of errors in data input, curve construction, or calculation.

**Mitigation**: 
- Input validation (implemented in the tool)
- Automated testing
- Regular audits
- User training

## Limitations and Missing Features

### Current Limitations

#### 1. **No Stochastic Modeling**
- **Missing**: Interest rate volatility modeling
- **Impact**: Cannot price options, swaptions, or path-dependent structures
- **Workaround**: Use external option pricing tools

#### 2. **Simple Interpolation**
- **Current**: Linear interpolation in zero rates
- **Missing**: Spline interpolation, log-linear interpolation, or other advanced methods
- **Impact**: May not accurately capture curve shape between market quotes
- **Enhancement**: Implement cubic spline or Hermite interpolation

#### 3. **Flat Extrapolation**
- **Current**: Constant rates beyond last market quote
- **Missing**: Forward-looking extrapolation or market-implied long-term rates
- **Impact**: Long-dated cashflows may be mispriced
- **Enhancement**: Implement exponential or mean-reverting extrapolation

#### 4. **No Convexity/Gamma**
- **Missing**: Second-order sensitivity (convexity) calculation
- **Impact**: Risk metrics incomplete for large rate movements
- **Enhancement**: Add gamma calculation: $\Gamma = \frac{\partial^2 PV}{\partial r^2}$

#### 5. **No Theta (Time Decay)**
- **Missing**: Explicit time decay calculation
- **Impact**: Cannot quantify daily P&L from time passage
- **Enhancement**: Calculate $\Theta = \frac{\partial PV}{\partial t}$

#### 6. **No Basis Risk Modeling**
- **Missing**: Explicit modeling of OIS-swap basis risk
- **Impact**: Basis changes not captured in risk metrics
- **Enhancement**: Add basis risk as separate risk factor

#### 7. **No Credit Risk**
- **Missing**: CVA (Credit Valuation Adjustment), DVA, FVA
- **Impact**: Pricing assumes risk-free counterparties
- **Enhancement**: Integrate credit curves and CVA calculation

#### 8. **No Funding Costs**
- **Missing**: Separate funding spread modeling
- **Impact**: Funding costs assumed embedded in discount curve
- **Enhancement**: Add funding curve and FVA calculation

#### 9. **Single Currency**
- **Current**: GBP (SONIA) only
- **Missing**: Multi-currency support (USD/SOFR, EUR/ESTR, etc.)
- **Enhancement**: Extend to support multiple currencies and cross-currency swaps

#### 10. **No Historical Analysis**
- **Missing**: Historical curve storage, back-testing, P&L attribution
- **Impact**: Cannot analyze performance over time
- **Enhancement**: Add database for historical curves and pricing snapshots

#### 11. **No Portfolio-Level Features**
- **Missing**: Portfolio aggregation, netting, portfolio risk metrics
- **Impact**: Tool is swap-specific, not portfolio-wide
- **Enhancement**: Add portfolio module for multiple swaps

#### 12. **Manual Data Input**
- **Current**: CSV file upload
- **Missing**: Automated data feeds (Bloomberg, Reuters APIs)
- **Impact**: Requires manual data preparation
- **Enhancement**: Integrate with market data providers

#### 13. **No Advanced Day Counts**
- **Current**: ACT/365 and 30/360 only
- **Missing**: ACT/360, ACT/ACT, 30E/360, etc.
- **Impact**: May not match all market conventions
- **Enhancement**: Add more day count conventions

#### 14. **No Amortizing/Accreting Notionals**
- **Missing**: Support for notional schedules
- **Impact**: Cannot price amortizing or accreting swaps
- **Enhancement**: Add notional schedule support

#### 15. **No Compounding Conventions**
- **Missing**: Different compounding methods (simple, compound, continuous)
- **Impact**: May not match all market conventions
- **Enhancement**: Add compounding convention options

#### 16. **No Early Termination**
- **Missing**: Break clauses, cancellable swaps
- **Impact**: Cannot price swaps with optionality
- **Enhancement**: Add optionality modeling

#### 17. **No Inflation Swaps**
- **Missing**: Inflation-linked swap support
- **Impact**: Cannot price inflation swaps
- **Enhancement**: Add inflation curve and inflation swap pricing

#### 18. **Limited Visualization**
- **Current**: Basic curve plots
- **Missing**: Advanced charts (3D surfaces, heat maps, risk decomposition charts)
- **Enhancement**: Add more sophisticated visualizations

#### 19. **No Export Functionality**
- **Missing**: Export pricing results, curves, or reports to Excel/PDF
- **Impact**: Manual copy-paste required for reporting
- **Enhancement**: Add export features

#### 20. **No User Authentication**
- **Missing**: Login, user roles, audit logs
- **Impact**: No access control or audit trail
- **Enhancement**: Add authentication and authorization

### Recommended Enhancements (Priority Order)

1. **High Priority**:
   - Spline interpolation for curves
   - Convexity (gamma) calculation
   - Historical curve storage
   - Export functionality

2. **Medium Priority**:
   - Multi-currency support
   - Portfolio aggregation
   - Automated data feeds
   - Advanced day count conventions

3. **Low Priority**:
   - Stochastic modeling
   - Credit risk (CVA)
   - Inflation swaps
   - User authentication

---

## Conclusion

The GBP SONIA Interest Rate Swap Pricing Analytics Tool provides a a good prototype for pricing and risk analysis of vanilla interest rate swaps. 

The tool is designed to be extended and enhanced, with a modular architecture that allows for easy addition of new features. Regular recalibration with updated market data ensures pricing accuracy, while stress testing and risk metrics provide essential insights for risk management.

---

## References

- [OIS vs LIBOR for IRS Pricing](https://financetrainingcourse.com/education/2012/10/using-ois-overnight-indexed-swap-rates-versus-libor-for-irs-pricing/)
- SONIA Market Conventions (Bank of England)
- ISDA Documentation for Interest Rate Swaps

---

**Document Version**: 1.0  
**Last Updated**: 2025  
**Author**: Abukar - Pricing, Risk & Model Validation Tool
