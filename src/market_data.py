from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_ois_quotes(filename: str = "sonia_ois_quotes.csv") -> pd.DataFrame:
    path = DATA_DIR / filename
    df = pd.read_csv(path)
    df.sort_values("tenor_years", inplace=True)
    return df.reset_index(drop=True)


def load_forward_quotes(filename: str = "sonia_forward_quotes.csv") -> pd.DataFrame:
    path = DATA_DIR / filename
    df = pd.read_csv(path)
    df.sort_values("tenor_years", inplace=True)
    return df.reset_index(drop=True)


def validate_curve_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate that uploaded curve data has the correct format.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        required_cols = {"tenor_years", "rate"}
        if not required_cols.issubset(df.columns):
            return False, f"Missing required columns. Need: {required_cols}, Got: {set(df.columns)}"
        
        if df.empty:
            return False, "Dataframe is empty"
        
        if df["tenor_years"].isna().any():
            return False, "tenor_years column contains NaN values"
        
        if df["rate"].isna().any():
            return False, "rate column contains NaN values"
        
        if (df["tenor_years"] <= 0).any():
            return False, "All tenor_years must be positive"
        
        # More lenient rate validation - allow negative rates and rates > 1 (for high inflation scenarios)
        if (df["rate"] < -0.5).any() or (df["rate"] > 2.0).any():
            return False, "Rates should be between -50% and 200% (reasonable range)"
        
        return True, ""
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def load_curve_from_upload(uploaded_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Load and validate curve data from uploaded file.
    
    Returns:
        (dataframe, error_message) - If successful, returns (df, None). If error, returns (None, error_msg).
    """
    try:
        df = pd.read_csv(uploaded_file)
        is_valid, error_msg = validate_curve_dataframe(df)
        if not is_valid:
            return None, error_msg
        df.sort_values("tenor_years", inplace=True)
        return df.reset_index(drop=True), None
    except Exception as e:
        return None, f"Error reading CSV file: {str(e)}"

