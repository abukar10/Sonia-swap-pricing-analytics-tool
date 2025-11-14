import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from datetime import date

from src.pricing_engine import (
    build_curves,
    bump_curve,
    calculate_key_rate_dv01,
    combined_cashflows_table,
    format_cashflows,
    price_with_non_parallel_shift,
    price_with_risk,
    stress_curves,
    swap_summary_dataframe,
)
from src.market_data import load_curve_from_upload, validate_curve_dataframe
from src.swap_pricing import SwapDefinition


st.set_page_config(page_title="GBP SONIA Interest Rate Swap Analytics", layout="wide")

# Theme selector in sidebar
with st.sidebar:
    st.markdown("### 🎨 Theme Settings")
    theme_mode = st.selectbox(
        "Background Theme",
        options=["Dark", "Light", "Custom"],
        index=0,
        help="Choose your preferred background theme"
    )
    
    if theme_mode == "Custom":
        bg_color = st.color_picker("Background Color", value="#0d1117")
        text_color = st.color_picker("Text Color", value="#e6edf3")
        card_color = st.color_picker("Card Background", value="#161b22")
        accent_color = st.color_picker("Accent Color", value="#58a6ff")
    elif theme_mode == "Light":
        bg_color = "#ffffff"
        text_color = "#1f2328"
        card_color = "#f6f8fa"
        accent_color = "#0969da"
    else:  # Dark
        bg_color = "#0d1117"
        text_color = "#e6edf3"
        card_color = "#161b22"
        accent_color = "#58a6ff"

# Dynamic CSS based on theme
CUSTOM_STYLE = f"""
<style>
    .main {{background-color: {bg_color}; padding-top: 3rem !important;}}
    .block-container {{background-color: {bg_color}; padding-top: 2rem !important; max-width: 100%;}}
    .stApp {{background-color: {bg_color}; color: {text_color};}}
    h1 {{color: {text_color} !important; margin-top: 0.5rem !important; margin-bottom: 0.25rem !important; padding-top: 0 !important;}}
    h2, h3, h4, h5, h6 {{color: {text_color} !important;}}
    p, div, span, label {{color: {text_color} !important;}}
    .streamlit-expanderHeader {{background: {card_color} !important; color: {text_color} !important;}}
    .stDataFrame {{background-color: {bg_color};}}
    .metric-container {{background:{card_color};border-radius:8px;padding:12px;margin-bottom:12px;}}
    .metric-value {{font-size:1.3rem;font-weight:600;color: {accent_color};}}
    .metric-label {{color:{text_color};opacity:0.8;font-size:0.85rem;}}
    div[data-testid="stMetricValue"] {{color: {accent_color};}}
    div[data-testid="stMetricLabel"] {{color: {text_color};opacity:0.8;}}
    .frame-card {{background:{card_color};padding:18px;border-radius:12px;border:1px solid rgba(255,255,255,0.1);}}
    .frame-card h4 {{margin-top:0;color: {text_color};}}
    .left-panel ul {{padding-left: 1.1rem;}}
    .left-panel li {{margin-bottom: 0.35rem;}}
    .analysis-card {{background:{card_color};padding:15px;border-radius:8px;margin-top:10px;border:1px solid rgba(255,255,255,0.1);}}
    .analysis-title {{color: {accent_color};font-size:0.95rem;font-weight:600;margin-bottom:8px;}}
    .analysis-value {{color: {text_color};font-size:1.1rem;font-weight:500;}}
    .analysis-label {{color: {text_color};opacity:0.7;font-size:0.8rem;}}
    /* Larger, button-like tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 48px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 8px;
        background-color: {card_color};
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {accent_color};
        color: {bg_color};
        border: 2px solid {accent_color};
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }}
    .stTabs [aria-selected="false"] {{
        background-color: {card_color};
        color: {text_color};
        border: 2px solid {card_color};
        cursor: pointer;
    }}
    .stTabs [aria-selected="false"]:hover {{
        background-color: {card_color};
        border: 2px solid {accent_color};
        opacity: 0.8;
    }}
</style>
"""
st.markdown(CUSTOM_STYLE, unsafe_allow_html=True)

# Curve Upload Section in Sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📊 Market Data Upload")
    st.markdown("Upload updated curve data to override default curves")
    
    # Initialize checkbox state in session state
    if 'use_uploaded_curves' not in st.session_state:
        st.session_state['use_uploaded_curves'] = False
    
    use_uploaded_curves = st.checkbox(
        "Use Uploaded Curves", 
        value=st.session_state['use_uploaded_curves'],
        help="Enable to use uploaded curve data instead of default",
        key='use_uploaded_curves_checkbox'
    )
    st.session_state['use_uploaded_curves'] = use_uploaded_curves
    
    uploaded_ois = st.file_uploader(
        "Upload OIS Discount Curve (CSV)",
        type=["csv"],
        help="CSV format: instrument_type,tenor_years,rate"
    )
    
    uploaded_forward = st.file_uploader(
        "Upload Forward Curve (CSV)",
        type=["csv"],
        help="CSV format: instrument_type,tenor_years,rate"
    )
    
    # Show current curve status
    if use_uploaded_curves:
        if 'uploaded_ois_df' in st.session_state and 'uploaded_forward_df' in st.session_state:
            st.info("✓ Using uploaded curves")
        else:
            st.warning("⚠ Upload both curves to use uploaded data")
    else:
        st.info("Using default curves")
    
    # Download template button
    if st.button("📥 Download CSV Template"):
        template_df = pd.DataFrame({
            "instrument_type": ["OIS_MARKET"] * 15,
            "tenor_years": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30],
            "rate": [0.03] * 15  # Placeholder rates
        })
        csv = template_df.to_csv(index=False)
        st.download_button(
            label="Download OIS Template CSV",
            data=csv,
            file_name="ois_curve_template.csv",
            mime="text/csv"
        )
        csv2 = template_df.to_csv(index=False)
        st.download_button(
            label="Download Forward Template CSV",
            data=csv2,
            file_name="forward_curve_template.csv",
            mime="text/csv"
        )
    
    if st.button("Reset to Default Curves"):
        if 'uploaded_ois_df' in st.session_state:
            del st.session_state['uploaded_ois_df']
        if 'uploaded_forward_df' in st.session_state:
            del st.session_state['uploaded_forward_df']
        st.session_state['use_uploaded_curves'] = False
        st.rerun()

# Load curves - use uploaded if available and enabled
ois_df = None
forward_df = None

if use_uploaded_curves:
    # Process uploaded OIS curve
    if uploaded_ois is not None:
        # Validate file type
        if not uploaded_ois.name.endswith('.csv'):
            st.sidebar.warning("⚠ OIS file must be a CSV file. Upload ignored.")
        else:
            ois_df, error_msg = load_curve_from_upload(uploaded_ois)
            if ois_df is not None:
                st.session_state['uploaded_ois_df'] = ois_df
                st.sidebar.success("✓ OIS curve uploaded successfully")
            else:
                st.sidebar.warning(f"⚠ Invalid OIS curve format: {error_msg or 'Check CSV structure. Expected columns: instrument_type,tenor_years,rate'}")
                # Don't break - continue with default or previously uploaded curve
                if 'uploaded_ois_df' in st.session_state:
                    ois_df = st.session_state['uploaded_ois_df']
    elif 'uploaded_ois_df' in st.session_state:
        ois_df = st.session_state['uploaded_ois_df']
    
    # Process uploaded Forward curve
    if uploaded_forward is not None:
        # Validate file type
        if not uploaded_forward.name.endswith('.csv'):
            st.sidebar.warning("⚠ Forward file must be a CSV file. Upload ignored.")
        else:
            forward_df, error_msg = load_curve_from_upload(uploaded_forward)
            if forward_df is not None:
                st.session_state['uploaded_forward_df'] = forward_df
                st.sidebar.success("✓ Forward curve uploaded successfully")
            else:
                st.sidebar.warning(f"⚠ Invalid Forward curve format: {error_msg or 'Check CSV structure. Expected columns: instrument_type,tenor_years,rate'}")
                # Don't break - continue with default or previously uploaded curve
                if 'uploaded_forward_df' in st.session_state:
                    forward_df = st.session_state['uploaded_forward_df']
    elif 'uploaded_forward_df' in st.session_state:
        forward_df = st.session_state['uploaded_forward_df']
    
    # If both curves are available, use them
    if ois_df is not None and forward_df is not None:
        discount_curve, forward_curve, discount_curve_df, forward_curve_df = build_curves(ois_df, forward_df)
        st.success(f"✓ Using uploaded curves: OIS ({len(ois_df)} points), Forward ({len(forward_df)} points)")
    elif ois_df is not None or forward_df is not None:
        st.warning("Both OIS and Forward curves required. Using defaults for missing curves.")
        discount_curve, forward_curve, discount_curve_df, forward_curve_df = build_curves(ois_df, forward_df)
    else:
        st.info("No uploaded curves found. Using default curves.")
        discount_curve, forward_curve, discount_curve_df, forward_curve_df = build_curves()
else:
    # Use default curves
    discount_curve, forward_curve, discount_curve_df, forward_curve_df = build_curves()

# Store forward_df for display in Forward Rate Analysis
if forward_df is not None:
    st.session_state['forward_quotes_df'] = forward_df
else:
    # Load default if not uploaded
    from src.market_data import load_forward_quotes
    st.session_state['forward_quotes_df'] = load_forward_quotes()

# Title and caption at the top
col_title, col_readme, col_note = st.columns([4, 1, 1])
with col_title:
    st.title("GBP SONIA Interest Rate Swap Analytics")
    st.caption("Abukar - Pricing, Risk & Model Validation Tool")
with col_readme:
    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
    if st.button("📖 ReadMe", use_container_width=True):
        st.session_state['show_readme'] = not st.session_state.get('show_readme', False)
with col_note:
    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
    if st.button("📝 Note", use_container_width=True):
        st.session_state['show_note'] = not st.session_state.get('show_note', False)

st.success("Loaded SONIA discount & forward curves and pricing engine.")

# ReadMe section (collapsible)
if st.session_state.get('show_readme', False):
    with st.expander("📖 ReadMe - Tool Information", expanded=True):
        st.markdown("### About this tool")
        st.markdown(
            """
            This interactive studio bootstraps SONIA discount and forward curves from market quotes,
            projects fixed and floating legs, and marks the swap to market with base and stressed views.
            """
        )
        st.markdown("### Quick guide")
        st.markdown(
            """
            1. Adjust swap inputs in the middle panel.\n
            2. Review mark-to-market, PV01, DV01, and stressed metrics on the right.\n
            3. Explore cashflows, combined legs, and curve visuals below.
            """
        )
        st.markdown("### Factors included")
        st.markdown(
            """
            - SONIA OIS discount curve (quarterly bootstrap)\n
            - SONIA par swap forward curve\n
            - Fixed leg 30/360, floating leg ACT/365\n
            - Parallel bump PV01/DV01 and configurable stress shift
            """,
        )

# Note section (collapsible)
if st.session_state.get('show_note', False):
    with st.expander("📝 Note - Key Rate DV01 Explanation", expanded=True):
        st.markdown(
            """
            **Key Rate DV01:** Absolute sensitivity to 1bp triangular shift at each key rate node. 
            Values shown are on current curves (base or shifted). Sum should approximately equal total parallel DV01.
            
            **Key Rate DV01 Decomposition:** The sum of individual key rate DV01s should approximately equal 
            the total parallel DV01. Small differences are expected due to triangular shift patterns used 
            in key rate calculations versus uniform parallel shifts.
            
            **Impact of Applied Shifts:** Shows the approximate impact of tenor-specific shifts calculated 
            as Key Rate DV01 × Shift Amount. This is an approximation; actual impact may differ due to 
            curve shape changes and non-linear effects.
            """
        )

info_col, input_col, metrics_col = st.columns([1.6, 1.3, 1.1], gap="large")

# Default values (defined outside column for scope)
default_notional = 10_000_000
default_valuation_date = date(2025, 11, 13)
default_effective_date = date(2025, 11, 17)
default_maturity = 5.0
default_fixed_rate = 3.5766
default_spread_bp = 0.0

# Left column - All pricing inputs
with info_col:
    st.markdown("### Swap Inputs")
    c1, c2 = st.columns(2)
    
    with c1:
        notional = st.number_input(
            "Notional (GBP)", 
            value=default_notional, 
            min_value=1_000_000, 
            max_value=10_000_000_000,
            step=1_000_000, 
            format="%d",
            help="Notional amount between £1M and £10B"
        )
        
        valuation_date_input = st.date_input(
            "Valuation Date", 
            value=default_valuation_date,
            min_value=date(2000, 1, 1),
            max_value=date(2100, 12, 31),
            help="Valuation date for pricing"
        )
        # Ensure date is not None - Streamlit can return None if cleared
        if valuation_date_input is None:
            valuation_date = default_valuation_date
            st.warning("⚠ Valuation date cleared. Using default.")
        else:
            valuation_date = valuation_date_input
        
        effective_date_input = st.date_input(
            "Effective Date", 
            value=default_effective_date,
            min_value=date(2000, 1, 1),
            max_value=date(2100, 12, 31),
            help="Swap effective/start date"
        )
        # Ensure date is not None and after valuation date
        if effective_date_input is None:
            effective_date = default_effective_date
            st.warning("⚠ Effective date cleared. Using default.")
        elif effective_date_input < valuation_date:
            st.warning("⚠ Effective date must be >= Valuation date. Using default.")
            effective_date = default_effective_date
        else:
            effective_date = effective_date_input
        
        maturity_years = st.number_input(
            "Tenor (years)", 
            value=default_maturity, 
            min_value=0.25,
            max_value=50.0,
            step=0.5, 
            format="%.1f",
            help="Swap maturity in years (0.25 to 50)"
        )
        
        # Validate maturity doesn't create unreasonable end date
        from datetime import timedelta
        max_maturity_date = effective_date + timedelta(days=int(maturity_years * 365.25))
        if max_maturity_date > date(2100, 12, 31):
            st.warning(f"⚠ Maturity date ({max_maturity_date.strftime('%Y-%m-%d')}) exceeds maximum. Please reduce tenor.")
            # Cap maturity to reasonable value
            max_allowed_years = (date(2100, 12, 31) - effective_date).days / 365.25
            maturity_years = min(maturity_years, max_allowed_years)
    
    with c2:
        fixed_rate_pct = st.number_input(
            "Fixed Rate (%)", 
            value=default_fixed_rate, 
            min_value=-10.0,
            max_value=20.0,
            step=0.01, 
            format="%.4f",
            help="Fixed rate between -10% and 20%"
        )
        fixed_rate = fixed_rate_pct / 100.0
        
        spread_bp = st.number_input(
            "Floating Spread (bp)", 
            value=default_spread_bp, 
            min_value=-1000.0,
            max_value=1000.0,
            step=0.5, 
            format="%.2f",
            help="Floating spread in basis points (-1000 to 1000 bp)"
        )
        
        fixed_freq = st.selectbox("Fixed Payments/Year", options=[1, 2, 4], index=1)
        float_freq = st.selectbox("Floating Payments/Year", options=[4, 12], index=0)
    
    stress_shift_bp = st.slider(
        "Stress shift (+/- bp)", 
        min_value=-200.0, 
        max_value=200.0, 
        value=50.0, 
        step=5.0
    )


# Validate inputs before creating swap definition
try:
    swap_definition = SwapDefinition(
        valuation_date=valuation_date,
        effective_date=effective_date,
        maturity_years=maturity_years,
        notional=notional,
        fixed_rate=fixed_rate,
        payer="fixed",
        fixed_leg_frequency=fixed_freq,
        floating_leg_frequency=float_freq,
        fixed_leg_daycount="30/360",
        floating_leg_daycount="ACT/365",
        spread=spread_bp / 10_000.0,
    )
    
    # Price swap with error handling
    try:
        base_metrics = price_with_risk(swap_definition, discount_curve, forward_curve)
        stressed_discount_curve, stressed_forward_curve = stress_curves(discount_curve, forward_curve, stress_shift_bp)
        stressed_metrics = price_with_risk(swap_definition, stressed_discount_curve, stressed_forward_curve)
    except Exception as e:
        st.error(f"❌ Pricing error: {str(e)}. Please check your inputs.")
        # Use dummy metrics to prevent further errors
        base_metrics = {"npv": 0.0, "pv01": 0.0, "dv01": 0.0, "cashflows": pd.DataFrame()}
        stressed_metrics = {"npv": 0.0, "pv01": 0.0, "dv01": 0.0}
        stressed_discount_curve = discount_curve
        stressed_forward_curve = forward_curve
except Exception as e:
    st.error(f"❌ Invalid swap definition: {str(e)}. Please check your inputs.")
    # Create a minimal valid swap definition to prevent crashes
    swap_definition = SwapDefinition(
        valuation_date=default_valuation_date,
        effective_date=default_effective_date,
        maturity_years=5.0,
        notional=10_000_000,
        fixed_rate=0.035,
        payer="fixed",
        fixed_leg_frequency=2,
        floating_leg_frequency=4,
        fixed_leg_daycount="30/360",
        floating_leg_daycount="ACT/365",
        spread=0.0,
    )
    base_metrics = {"npv": 0.0, "pv01": 0.0, "dv01": 0.0, "cashflows": pd.DataFrame()}
    stressed_metrics = {"npv": 0.0, "pv01": 0.0, "dv01": 0.0}
    stressed_discount_curve = discount_curve
    stressed_forward_curve = forward_curve

# Default tenor shifts (defined outside column context for reuse)
default_tenors = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0]
default_shifts = {0.25: 5.0, 0.5: 10.0, 1.0: 10.0, 2.0: 5.0, 3.0: 0.0, 5.0: -5.0, 7.0: -10.0, 10.0: -10.0, 15.0: -5.0, 20.0: 0.0, 30.0: 5.0}

# Non-Parallel Shift Analysis Section (continue in left column)
with info_col:
    st.markdown("---")
    st.markdown("#### 📈 Non-Parallel Shift Impact")
    
    # User inputs for tenor-specific shifts
    st.markdown("**Tenor-Specific Shifts (bp):**")
    
    # Create a cleaner two-column layout with proper headers
    left_col, right_col = st.columns(2)
    tenor_shifts = {}
    
    with left_col:
        # Header row
        h1, h2 = st.columns([1, 2])
        with h1:
            st.markdown("**Tenor**")
        with h2:
            st.markdown("**Shift (bp)**")
        
        for t in default_tenors[:6]:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"<div style='padding-top: 8px;'>{t:.2f}Y</div>", unsafe_allow_html=True)
            with col2:
                shift_val = st.number_input(
                    f"shift_{t}",
                    value=default_shifts.get(t, 0.0),
                    min_value=-500.0,
                    max_value=500.0,
                    step=1.0,
                    format="%.1f",
                    key=f"shift_left_{t}",
                    label_visibility="collapsed",
                    help=f"Shift for {t}Y tenor (-500 to 500 bp)"
                )
                tenor_shifts[t] = shift_val
    
    with right_col:
        # Header row
        h1, h2 = st.columns([1, 2])
        with h1:
            st.markdown("**Tenor**")
        with h2:
            st.markdown("**Shift (bp)**")
        
        for t in default_tenors[6:]:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"<div style='padding-top: 8px;'>{t:.2f}Y</div>", unsafe_allow_html=True)
            with col2:
                shift_val = st.number_input(
                    f"shift_{t}",
                    value=default_shifts.get(t, 0.0),
                    min_value=-500.0,
                    max_value=500.0,
                    step=1.0,
                    format="%.1f",
                    key=f"shift_right_{t}",
                    label_visibility="collapsed",
                    help=f"Shift for {t}Y tenor (-500 to 500 bp)"
                )
                tenor_shifts[t] = shift_val
    
    # Use same shifts for both curves (can be made separate if needed)
    discount_shifts = tenor_shifts.copy()
    forward_shifts = tenor_shifts.copy()
    
    # Store shifts in session state for access in other columns
    st.session_state['tenor_shifts'] = tenor_shifts
    st.session_state['discount_shifts'] = discount_shifts
    st.session_state['forward_shifts'] = forward_shifts
    
    # Always calculate base key rate DV01 first (for comparison)
    base_key_rate_dv01 = calculate_key_rate_dv01(
        swap_definition, discount_curve, forward_curve, default_tenors
    )
    
    # Calculate bucketed DV01 based on current shifts
    # Always recalculate to ensure it updates with shift changes
    has_shifts = any(abs(s) > 1e-6 for s in tenor_shifts.values())  # Check for non-zero with tolerance
    
    if has_shifts:
        # Apply shifts to get the shifted curves
        from src.pricing_engine import apply_non_parallel_shift
        shifted_discount = apply_non_parallel_shift(discount_curve, discount_shifts)
        shifted_forward = apply_non_parallel_shift(forward_curve, forward_shifts)
        # Calculate bucketed DV01 on shifted curves (absolute values)
        shifted_key_rate_dv01 = calculate_key_rate_dv01(
            swap_definition, shifted_discount, shifted_forward, default_tenors
        )
        # Show absolute key rate DV01 values on shifted curves
        # These should sum to approximately the total DV01 on shifted curves
        key_rate_dv01_dict = {
            tenor: shifted_key_rate_dv01.get(tenor, 0.0)
            for tenor in default_tenors
        }
    else:
        # No shifts applied, show absolute key rate DV01 on base curves
        # These should sum to approximately the total DV01 on base curves
        key_rate_dv01_dict = {
            tenor: base_key_rate_dv01.get(tenor, 0.0)
            for tenor in default_tenors
        }
    
    # Store bucketed DV01 in session state
    st.session_state['key_rate_dv01_dict'] = key_rate_dv01_dict
    st.session_state['has_shifts'] = has_shifts
    st.session_state['base_key_rate_dv01'] = base_key_rate_dv01  # Store for absolute comparison
    
    # Calculate non-parallel shift impact
    if discount_shifts and forward_shifts:
        non_parallel_metrics = price_with_non_parallel_shift(
            swap_definition, discount_curve, forward_curve, discount_shifts, forward_shifts
        )
        # Store in session state for access in other columns
        st.session_state['non_parallel_metrics'] = non_parallel_metrics
        
        # Display metrics
        np_metrics_cols = st.columns(4)
        with np_metrics_cols[0]:
            st.markdown(
                f'<div class="analysis-card">'
                f'<div class="analysis-label">Shifted MTM</div>'
                f'<div class="analysis-value">£{non_parallel_metrics["npv"]:,.2f}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with np_metrics_cols[1]:
            st.markdown(
                f'<div class="analysis-card">'
                f'<div class="analysis-label">MTM Change</div>'
                f'<div class="analysis-value">£{non_parallel_metrics["npv_change"]:,.2f}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with np_metrics_cols[2]:
            st.markdown(
                f'<div class="analysis-card">'
                f'<div class="analysis-label">PV01</div>'
                f'<div class="analysis-value">£{non_parallel_metrics["pv01"]:,.2f}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with np_metrics_cols[3]:
            st.markdown(
                f'<div class="analysis-card">'
                f'<div class="analysis-label">DV01</div>'
                f'<div class="analysis-value">£{non_parallel_metrics["dv01"]:,.2f}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

# Middle column - Curve visualizations
with input_col:
    plot_template = "plotly_dark" if theme_mode == "Dark" else "plotly_white"
    
    # Chart 1: Implied vs Quoted Forward Curves
    forward_comparison_fig = go.Figure()
    
    # Get quoted forward rates (market par swap rates)
    forward_quotes_df = st.session_state.get('forward_quotes_df', None)
    if forward_quotes_df is None:
        from src.market_data import load_forward_quotes
        forward_quotes_df = load_forward_quotes()
    
    # Add quoted SONIA forward curve (market par swap rates)
    if forward_quotes_df is not None and 'rate' in forward_quotes_df.columns:
        forward_comparison_fig.add_trace(
            go.Scatter(
                x=forward_quotes_df["tenor_years"],
                y=forward_quotes_df["rate"],
                mode="lines+markers",
                name="Quoted SONIA Forward (Par Swap Rates)",
                line=dict(color="#ff6b6b", width=2),
                marker=dict(size=6, symbol="diamond"),
            )
        )
    
    # Add implied SONIA forward zero curve (bootstrapped)
    forward_comparison_fig.add_trace(
        go.Scatter(
            x=forward_curve.tenors,
            y=forward_curve.zero_rates,
            mode="lines+markers",
            name="Implied SONIA Forward Zero Curve",
            line=dict(color=accent_color, width=2),
            marker=dict(size=6),
        )
    )
    
    forward_comparison_fig.update_layout(
        title="Quoted vs Implied Forward Curves",
        xaxis_title="Tenor (years)",
        yaxis_title="Rate",
        template=plot_template,
        height=500,
        plot_bgcolor=card_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, size=12),
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor=accent_color,
            borderwidth=1,
            font=dict(size=11)
        ),
        margin=dict(l=50, r=30, t=60, b=50),
    )
    
    st.plotly_chart(
        forward_comparison_fig, 
        use_container_width=True,
        config={"displayModeBar": False, "displaylogo": False}
    )
    
    # Chart 2: Stressed Curves (Before and After)
    stressed_curves_fig = go.Figure()
    
    # Base discount curve
    stressed_curves_fig.add_trace(
        go.Scatter(
            x=discount_curve_df["tenor_years"],
            y=discount_curve_df["zero_rate"],
            mode="lines+markers",
            name="Discount Zero Rates (Base)",
            line=dict(color=accent_color, width=2),
            marker=dict(size=5),
        )
    )
    
    # Base forward curve
    stressed_curves_fig.add_trace(
        go.Scatter(
            x=forward_curve.tenors,
            y=forward_curve.zero_rates,
            mode="lines+markers",
            name="Forward Zero Rates (Base)",
            line=dict(color="#58a6ff" if theme_mode == "Dark" else "#0969da", width=2),
            marker=dict(size=5),
        )
    )
    
    # Stressed discount curve
    stressed_curves_fig.add_trace(
        go.Scatter(
            x=stressed_discount_curve.tenors,
            y=stressed_discount_curve.zero_rates,
            mode="lines",
            name=f"Stressed Discount (+{stress_shift_bp:.0f}bp)",
            line=dict(dash="dash", color=accent_color, width=2),
        )
    )
    
    # Stressed forward curve
    stressed_curves_fig.add_trace(
        go.Scatter(
            x=stressed_forward_curve.tenors,
            y=stressed_forward_curve.zero_rates,
            mode="lines",
            name=f"Stressed Forward (+{stress_shift_bp:.0f}bp)",
            line=dict(dash="dash", color="#58a6ff" if theme_mode == "Dark" else "#0969da", width=2),
        )
    )
    
    stressed_curves_fig.update_layout(
        title="Curves Before and After Stress",
        xaxis_title="Tenor (years)",
        yaxis_title="Zero Rate",
        template=plot_template,
        height=500,
        plot_bgcolor=card_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, size=12),
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor=accent_color,
            borderwidth=1,
            font=dict(size=11)
        ),
        margin=dict(l=50, r=30, t=60, b=50),
    )
    
    st.plotly_chart(
        stressed_curves_fig, 
        use_container_width=True,
        config={"displayModeBar": False, "displaylogo": False}
    )
    
    # Chart 3: Forward SONIA Rates by Period
    forward_path_fig = go.Figure()
    
    # Get forward rates from floating leg cashflows
    floating_cashflows = base_metrics["cashflows"].loc[
        base_metrics["cashflows"]["leg"] == "floating"
    ].copy()
    
    if len(floating_cashflows) > 0:
        # Sort by period end date
        floating_cashflows = floating_cashflows.sort_values("period_end").reset_index(drop=True)
        
        # Calculate time in years from valuation date
        time_years = floating_cashflows["time_to_payment"].values
        forward_rates = floating_cashflows["forward_rate"].values
        
        # Create line chart with annotations
        forward_path_fig.add_trace(
            go.Scatter(
                x=time_years,
                y=forward_rates,
                mode="lines+markers+text",
                name="Forward SONIA Rate",
                line=dict(color=accent_color, width=2.5),
                marker=dict(size=8, color=accent_color),
                text=[f"{rate*100:.3f}%" for rate in forward_rates],
                textposition="top center",
                textfont=dict(size=9, color=text_color),
                hovertemplate="Time: %{x:.2f} years<br>Forward Rate: %{y:.4%}<extra></extra>",
            )
        )
        
        forward_path_fig.update_layout(
            title="Forward SONIA Rates by Period",
            xaxis_title="Time (years)",
            yaxis_title="Forward Rate",
            template=plot_template,
            height=400,
            plot_bgcolor=card_color,
            paper_bgcolor=bg_color,
            font=dict(color=text_color, size=12),
            legend=dict(
                x=0.02,
                y=0.98,
                bgcolor="rgba(0,0,0,0.5)",
                bordercolor=accent_color,
                borderwidth=1,
                font=dict(size=11)
            ),
            margin=dict(l=50, r=30, t=60, b=50),
            yaxis=dict(tickformat=".2%"),
        )
    else:
        # Empty chart if no data
        forward_path_fig.update_layout(
            title="Forward SONIA Rates by Period",
            xaxis_title="Time (years)",
            yaxis_title="Forward Rate",
            template=plot_template,
            height=400,
            plot_bgcolor=card_color,
            paper_bgcolor=bg_color,
            font=dict(color=text_color, size=12),
        )
    
    st.plotly_chart(
        forward_path_fig, 
        use_container_width=True,
        config={"displayModeBar": False, "displaylogo": False}
    )

summary_df = swap_summary_dataframe(
    swap_definition,
    {"npv": base_metrics["npv"], "pv01": base_metrics["pv01"], "dv01": base_metrics["dv01"]},
    {"npv": stressed_metrics["npv"], "pv01": stressed_metrics["pv01"], "dv01": stressed_metrics["dv01"]},
)

with metrics_col:
    st.markdown("### Pricing Snapshot")
    base_npv = f"£{base_metrics['npv']:,.2f}"
    base_pv01 = f"£{base_metrics['pv01']:,.2f}"
    base_dv01 = f"£{base_metrics['dv01']:,.2f}"
    stressed_npv = f"£{stressed_metrics['npv']:,.2f}"
    stressed_pv01 = f"£{stressed_metrics['pv01']:,.2f}"
    stressed_dv01 = f"£{stressed_metrics['dv01']:,.2f}"

    st.markdown(f'<div class="metric-container"><div class="metric-label">Mark-to-Market</div><div class="metric-value">{base_npv}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-container"><div class="metric-label">PV01</div><div class="metric-value">{base_pv01}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-container"><div class="metric-label">DV01</div><div class="metric-value">{base_dv01}</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f'<div class="metric-container"><div class="metric-label">Stress MTM (+{stress_shift_bp:.0f} bp)</div><div class="metric-value">{stressed_npv}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-container"><div class="metric-label">Stress PV01</div><div class="metric-value">{stressed_pv01}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-container"><div class="metric-label">Stress DV01</div><div class="metric-value">{stressed_dv01}</div></div>', unsafe_allow_html=True)
    
    # Add Bucketed DV01 section here
    st.markdown("---")
    st.markdown("### 🔑 Bucketed DV01 / Key Rate DV01")
    st.markdown("**All tenor node exposures**")
    
    # Get bucketed DV01 from session state (calculated in input_col with current shifts)
    # This ensures it's always up-to-date with the latest shift values
    if 'key_rate_dv01_dict' in st.session_state:
        key_rate_dv01_dict = st.session_state['key_rate_dv01_dict']
    else:
        # Fallback: calculate on base curves if not in session state (first run)
        key_rate_dv01_dict = calculate_key_rate_dv01(
            swap_definition, discount_curve, forward_curve, default_tenors
        )
    
    # Display in 2-column grid with cards
    num_tenors = len(default_tenors)
    rows = (num_tenors + 1) // 2  # Number of rows needed for 2 columns
    
    for row_idx in range(rows):
        cols = st.columns(2)
        for col_idx in range(2):
            tenor_idx = row_idx * 2 + col_idx
            if tenor_idx < num_tenors:
                tenor = default_tenors[tenor_idx]
                dv01_val = key_rate_dv01_dict.get(tenor, 0.0)
                with cols[col_idx]:
                    st.markdown(
                        f'<div class="analysis-card">'
                        f'<div class="analysis-label">{tenor:.2f}Y</div>'
                        f'<div class="analysis-value">£{dv01_val:,.2f}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
    
    # Calculate and display sum (for reference, but don't show decomposition sections)
    total_bucketed_dv01 = sum(key_rate_dv01_dict.values())

# Divider and tables moved up to fill gap - placed right after three-column layout ends
st.markdown("---")
st.markdown("### Swap Pricing Template")
terms_col, pricing_col, table_col = st.columns([1.2, 1.2, 2.6], gap="large")

with terms_col:
    st.markdown('<div class="frame-card"><h4>Terms & Conditions</h4>', unsafe_allow_html=True)
    st.dataframe(summary_df.iloc[:11].set_index("Attribute"), use_container_width=True, height=300)
    st.markdown("</div>", unsafe_allow_html=True)

with pricing_col:
    st.markdown('<div class="frame-card"><h4>Pricing & Risk Metrics</h4>', unsafe_allow_html=True)
    st.dataframe(summary_df.iloc[11:].set_index("Attribute"), use_container_width=True, height=300)
    st.markdown("</div>", unsafe_allow_html=True)

with table_col:
    st.markdown('<div class="frame-card"><h4>Leg Cashflows (Base)</h4>', unsafe_allow_html=True)
    base_cashflows = format_cashflows(base_metrics["cashflows"])
    st.dataframe(base_cashflows, use_container_width=True, height=300)
    st.markdown("</div>", unsafe_allow_html=True)

tabs = st.tabs(["Combined Cashflows", "Curve Visualisation", "Stress Summary", "Forward Rate Analysis"])

with tabs[0]:
    st.markdown("#### Combined Fixed & Floating Cashflows")
    combined_table = combined_cashflows_table(base_metrics["cashflows"])
    st.dataframe(combined_table, use_container_width=True, height=320)

with tabs[1]:
    st.markdown("#### SONIA Curves Before and After Stress")
    curve_fig = go.Figure()
    curve_fig.add_trace(
        go.Scatter(
            x=discount_curve_df["tenor_years"],
            y=discount_curve_df["zero_rate"],
            mode="lines+markers",
            name="Discount Zero Rates",
            line=dict(color=accent_color),
        )
    )
    curve_fig.add_trace(
        go.Scatter(
            x=forward_curve.tenors,
            y=forward_curve.zero_rates,
            mode="lines+markers",
            name="Forward Zero Rates",
            line=dict(color="#58a6ff" if theme_mode == "Dark" else "#0969da"),
        )
    )
    curve_fig.add_trace(
        go.Scatter(
            x=stressed_discount_curve.tenors,
            y=stressed_discount_curve.zero_rates,
            mode="lines",
            name=f"Stressed Discount (+{stress_shift_bp:.0f}bp)",
            line=dict(dash="dash", color=accent_color, width=2),
        )
    )
    curve_fig.add_trace(
        go.Scatter(
            x=stressed_forward_curve.tenors,
            y=stressed_forward_curve.zero_rates,
            mode="lines",
            name=f"Stressed Forward (+{stress_shift_bp:.0f}bp)",
            line=dict(dash="dash", color="#58a6ff" if theme_mode == "Dark" else "#0969da", width=2),
        )
    )
    plot_template = "plotly_dark" if theme_mode == "Dark" else "plotly_white"
    curve_fig.update_layout(
        xaxis_title="Tenor (years)",
        yaxis_title="Zero Rate",
        template=plot_template,
        height=420,
        plot_bgcolor=card_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color),
    )
    st.plotly_chart(
        curve_fig, 
        use_container_width=True,
        config={"displayModeBar": True, "displaylogo": False}
    )

with tabs[2]:
    st.markdown("#### Base vs Stressed Metrics")
    stress_table = pd.DataFrame(
        {
            "Metric": [
                "Base NPV",
                "Base PV01",
                "Base DV01",
                f"Stressed NPV (+{stress_shift_bp:.0f}bp)",
                "Stressed PV01",
                "Stressed DV01",
            ],
            "Value": [
                f"£{base_metrics['npv']:,.2f}",
                f"£{base_metrics['pv01']:,.2f}",
                f"£{base_metrics['dv01']:,.2f}",
                f"£{stressed_metrics['npv']:,.2f}",
                f"£{stressed_metrics['pv01']:,.2f}",
                f"£{stressed_metrics['dv01']:,.2f}",
            ],
        }
    )
    st.dataframe(stress_table.set_index("Metric"), use_container_width=True, height=260)
    st.markdown(
        """
        _The stress applies a parallel shift to discount and forward SONIA zero curves,
        re-projecting floating coupons and discounting both legs consistently._
        """
    )

with tabs[3]:
    st.markdown("#### 📊 Forward Rate Analysis")
    
    # Get quoted forward rates (market par swap rates)
    forward_quotes_df = st.session_state.get('forward_quotes_df', None)
    if forward_quotes_df is None:
        from src.market_data import load_forward_quotes
        forward_quotes_df = load_forward_quotes()
    
    # Create chart with both quoted and implied curves
    forward_analysis_fig = go.Figure()
    
    # Add quoted SONIA forward curve (market par swap rates)
    if forward_quotes_df is not None and 'rate' in forward_quotes_df.columns:
        forward_analysis_fig.add_trace(
            go.Scatter(
                x=forward_quotes_df["tenor_years"],
                y=forward_quotes_df["rate"],
                mode="lines+markers",
                name="Quoted SONIA Forward (Par Swap Rates)",
                line=dict(color="#ff6b6b", width=3),
                marker=dict(size=8, symbol="diamond"),
            )
        )
    
    # Add implied SONIA forward zero curve (bootstrapped)
    forward_analysis_fig.add_trace(
        go.Scatter(
            x=forward_curve.tenors,
            y=forward_curve.zero_rates,
            mode="lines+markers",
            name="Implied SONIA Forward Zero Curve",
            line=dict(color=accent_color, width=3),
            marker=dict(size=8),
        )
    )
    
    plot_template = "plotly_dark" if theme_mode == "Dark" else "plotly_white"
    forward_analysis_fig.update_layout(
        title="Quoted vs Implied SONIA Forward Curves",
        xaxis_title="Tenor (years)",
        yaxis_title="Rate",
        template=plot_template,
        height=450,
        plot_bgcolor=card_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color),
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor=accent_color,
            borderwidth=1
        ),
    )
    
    st.plotly_chart(
        forward_analysis_fig, 
        use_container_width=True, 
        config={"displayModeBar": True, "displaylogo": False}
    )
    
    st.markdown("---")
    
    # Calculate forward rates for key tenors
    def get_forward_rate_analysis(forward_curve, discount_curve):
        """Calculate forward rate statistics and key metrics."""
        tenors = forward_curve.tenors
        zero_rates = forward_curve.zero_rates
        
        # Calculate 1Y forward rates
        forward_1y_1y = forward_curve.forward_rate(1.0, 2.0)
        forward_2y_1y = forward_curve.forward_rate(2.0, 3.0)
        forward_5y_1y = forward_curve.forward_rate(5.0, 6.0)
        
        # Curve statistics
        min_rate = np.min(zero_rates)
        max_rate = np.max(zero_rates)
        avg_rate = np.mean(zero_rates)
        curve_slope = (zero_rates[-1] - zero_rates[0]) / (tenors[-1] - tenors[0])
        
        # Calculate convexity (second derivative approximation)
        if len(tenors) >= 3:
            mid_idx = len(tenors) // 2
            convexity = (zero_rates[mid_idx+1] - 2*zero_rates[mid_idx] + zero_rates[mid_idx-1]) / ((tenors[mid_idx+1] - tenors[mid_idx])**2) if mid_idx > 0 and mid_idx < len(tenors)-1 else 0
        else:
            convexity = 0
        
        return {
            "1Y1Y Forward": forward_1y_1y * 100,
            "2Y1Y Forward": forward_2y_1y * 100,
            "5Y1Y Forward": forward_5y_1y * 100,
            "Min Rate": min_rate * 100,
            "Max Rate": max_rate * 100,
            "Avg Rate": avg_rate * 100,
            "Curve Slope (bp/yr)": curve_slope * 10000,
            "Convexity": convexity * 10000,
        }
    
    # Get analysis for base curves
    forward_analysis = get_forward_rate_analysis(forward_curve, discount_curve)
    
    # Display in a grid
    analysis_cols = st.columns(4)
    metrics_to_show = [
        ("1Y1Y Forward", f"{forward_analysis['1Y1Y Forward']:.2f}%"),
        ("2Y1Y Forward", f"{forward_analysis['2Y1Y Forward']:.2f}%"),
        ("5Y1Y Forward", f"{forward_analysis['5Y1Y Forward']:.2f}%"),
        ("Avg Rate", f"{forward_analysis['Avg Rate']:.2f}%"),
    ]
    
    for idx, (label, value) in enumerate(metrics_to_show):
        with analysis_cols[idx]:
            st.markdown(
                f'<div class="analysis-card">'
                f'<div class="analysis-label">{label}</div>'
                f'<div class="analysis-value">{value}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    
    # Additional metrics
    st.markdown("---")
    analysis_cols2 = st.columns(4)
    metrics_to_show2 = [
        ("Min Rate", f"{forward_analysis['Min Rate']:.2f}%"),
        ("Max Rate", f"{forward_analysis['Max Rate']:.2f}%"),
        ("Curve Slope", f"{forward_analysis['Curve Slope (bp/yr)']:.1f} bp/yr"),
        ("Convexity", f"{forward_analysis['Convexity']:.2f}"),
    ]
    
    for idx, (label, value) in enumerate(metrics_to_show2):
        with analysis_cols2[idx]:
            st.markdown(
                f'<div class="analysis-card">'
                f'<div class="analysis-label">{label}</div>'
                f'<div class="analysis-value">{value}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


st.caption("Adjust the inputs above to explore scenarios. Outputs refresh instantly.")

