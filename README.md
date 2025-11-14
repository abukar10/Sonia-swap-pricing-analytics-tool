# GBP SONIA Interest Rate Swap Pricing Analytics Tool

A comprehensive pricing and risk analytics tool for GBP SONIA Interest Rate Swaps.

## Features

- Forward curve creation and bootstrapping
- Discount curve construction from OIS quotes
- Cashflow projection for fixed and floating legs
- Mark-to-Market (MTM) valuation
- Risk metrics: PV01, DV01, Key Rate DV01
- Stress testing with parallel and non-parallel curve shifts
- Interactive Streamlit dashboard
- Market data upload and curve override capabilities

## Installation

1. Create a virtual environment:
```bash
python -m venv swaps
```

2. Activate the virtual environment:
```bash
# Windows
swaps\Scripts\activate

# Linux/Mac
source swaps/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Streamlit Application
```bash
streamlit run app.py
```

### Jupyter Notebook
Open `notebooks/gbp_sonia_swap_pricing.ipynb` in Jupyter Notebook or JupyterLab.

## Project Structure

```
├── app.py                    # Streamlit dashboard
├── src/                      # Core pricing engine
│   ├── curves.py            # Zero curve construction
│   ├── swap_pricing.py      # Swap pricing logic
│   ├── pricing_engine.py   # Risk calculations
│   └── ...
├── data/                     # Market data files
├── notebooks/               # Jupyter notebooks
└── requirements.txt         # Python dependencies
```

## Author

Abukar - Pricing, Risk & Model Validation Tool

