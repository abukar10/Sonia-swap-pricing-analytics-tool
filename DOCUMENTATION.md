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

---

## Recalibration with New Market Data

### Daily Recalibration Process

The tool supports recalibration through the **Market Data Upload** feature in the Streamlit dashboard.

### Step-by-Step Process

1. **Prepare Updated Curves**:
   - Export current market quotes to CSV format
   - Ensure CSV has columns: `instrument_type`, `tenor_years`, `rate`
   - Update rates with latest market data

2. **Upload via Dashboard**:
   - Navigate to "Market Data Upload" section in the sidebar
   - Upload updated OIS curve CSV file
   - Upload updated Forward curve CSV file
   - Enable "Use Uploaded Curves" checkbox

3. **Automatic Recalibration**:
   - The tool automatically:
     - Validates the uploaded data
     - Bootstraps new discount and forward curves
     - Reprices the swap with new curves
     - Updates all risk metrics

4. **Verification**:
   - Check that curves look reasonable (visual inspection)
   - Verify MTM and risk metrics are updated
   - Compare with previous day's values to identify significant changes

### CSV Format Requirements

**Required Columns**:
- `instrument_type`: "OIS_MARKET" for discount curve, "SONIA_SWAP" for forward curve
- `tenor_years`: Tenor in years (numeric)
- `rate`: Rate as decimal (e.g., 0.035 for 3.5%)

**Validation Rules**:
- No missing values (NaN)
- All tenors must be positive
- Rates must be between -50% and 200% (reasonable range)
- At least one data point required

### What Gets Recalibrated

1. **Discount Curve**: 
   - New zero rates bootstrapped from OIS quotes
   - New discount factors recalculated
   - Affects all cashflow discounting

2. **Forward Curve**:
   - New zero rates bootstrapped from swap quotes
   - New forward rates recalculated
   - Affects all floating leg cashflows

3. **Swap Pricing**:
   - All cashflows recalculated with new curves
   - MTM updated
   - PV01/DV01 recalculated
   - Key Rate DV01 recalculated

4. **Stress Tests**:
   - All stress scenarios use new base curves
   - Stressed metrics updated

### Best Practices

1. **Data Quality**:
   - Source data from reliable providers (Bloomberg, Reuters, interdealer brokers)
   - Verify data timestamps
   - Check for outliers or data errors

2. **Frequency**:
   - Recalibrate daily for active trading
   - Recalibrate intraday for large market moves
   - Document recalibration dates and sources

3. **Version Control**:
   - Save historical curve files
   - Track changes in MTM over time
   - Maintain audit trail

4. **Validation**:
   - Compare new curves with previous curves
   - Check for sudden jumps (may indicate data errors)
   - Verify MTM changes are reasonable given market movements

### Limitations

- **Manual Process**: Currently requires manual CSV upload (not automated data feeds)
- **No Historical Tracking**: Tool does not store historical curves or track changes over time
- **Single Snapshot**: Each recalibration replaces previous curves (no versioning)

---

## End-to-End Deployment Guide

This section provides a comprehensive guide to deploying the GBP SONIA Interest Rate Swap Pricing Analytics Tool from development to production, covering the complete workflow from code development in VS Code to cloud deployment on Streamlit Cloud.

### Overview of Deployment Architecture

```
VS Code (Development) → Git (Version Control) → GitHub (Repository) → Streamlit Cloud (Web Hosting)
```

### Step 1: Development in VS Code

#### 1.1 Project Setup

**Initial Setup:**
1. **Open VS Code**: Launch Visual Studio Code
2. **Open Workspace**: Open the project folder (`C:\Users\user\PRicing_IR_Swaps`)
3. **Python Extension**: Ensure Python extension is installed in VS Code
4. **Virtual Environment**: Create and activate virtual environment:
   ```bash
   python -m venv swaps
   # Windows
   swaps\Scripts\activate
   # Linux/Mac
   source swaps/bin/activate
   ```

#### 1.2 Development Workflow

**File Structure in VS Code:**
```
PRicing_IR_Swaps/
├── app.py                    # Main Streamlit application
├── src/                      # Source code modules
│   ├── __init__.py
│   ├── curves.py            # Curve construction
│   ├── swap_pricing.py      # Swap pricing logic
│   ├── pricing_engine.py   # Risk calculations
│   ├── market_data.py      # Data loading
│   ├── schedule.py         # Cashflow scheduling
│   └── daycount.py         # Day count conventions
├── data/                     # Market data CSV files
│   ├── sonia_ois_quotes.csv
│   └── sonia_forward_quotes.csv
├── notebooks/               # Jupyter notebooks
│   └── gbp_sonia_swap_pricing.ipynb
├── .streamlit/              # Streamlit configuration
│   └── config.toml
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md               # Project documentation
```

**VS Code Features Used:**
- **Integrated Terminal**: For running commands and testing
- **Python Debugger**: For debugging code
- **Git Integration**: Built-in Git support for version control
- **Extensions**: Python, Jupyter, GitLens (optional but helpful)

#### 1.3 Development Best Practices

1. **Code Organization**:
   - Modular design with separate modules for curves, pricing, and data
   - Clear function and class documentation
   - Type hints for better code clarity

2. **Testing**:
   - Test locally using: `streamlit run app.py`
   - Verify all features work before committing
   - Test with different input scenarios

3. **Code Quality**:
   - Follow PEP 8 style guidelines
   - Use meaningful variable and function names
   - Add comments for complex logic

### Step 2: Version Control with Git

#### 2.1 Git Initialization

**Initial Setup:**
```bash
# Navigate to project directory
cd C:\Users\user\PRicing_IR_Swaps

# Initialize Git repository
git init
```

#### 2.2 Creating .gitignore

**Purpose**: Exclude unnecessary files from version control (virtual environment, cache files, etc.)

**Content of .gitignore**:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual Environment
swaps/
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Jupyter Notebook
.ipynb_checkpoints

# OS
.DS_Store
Thumbs.db

# Streamlit
.streamlit/secrets.toml

# Logs
*.log
```

**Why Important**: Prevents committing large virtual environment folders and temporary files to Git, keeping the repository clean and manageable.

#### 2.3 Git Workflow

**Basic Git Commands:**
```bash
# Check status of files
git status

# Add files to staging area
git add .                    # Add all files
git add app.py              # Add specific file

# Commit changes with message
git commit -m "Initial commit: GBP SONIA Interest Rate Swap Pricing Analytics Tool"

# View commit history
git log --oneline

# Check differences
git diff
```

#### 2.4 Branch Management

**Best Practice**: Use branches for feature development
```bash
# Create a new branch
git branch feature-name

# Switch to branch
git checkout feature-name

# Merge branch back to main
git checkout main
git merge feature-name
```

### Step 3: Pushing to GitHub

#### 3.1 Creating GitHub Repository

1. **Sign in to GitHub**: Go to https://github.com and sign in
2. **Create New Repository**:
   - Click "New" or "+" → "New repository"
   - Repository name: `Sonia-swap-pricing-analytics-tool`
   - Description: "GBP SONIA Interest Rate Swap Pricing Analytics Tool"
   - Visibility: Public or Private (your choice)
   - **Do NOT** initialize with README, .gitignore, or license (we already have these)
   - Click "Create repository"

#### 3.2 Connecting Local Repository to GitHub

**Add Remote Repository:**
```bash
# Add GitHub repository as remote origin
git remote add origin https://github.com/abukar10/Sonia-swap-pricing-analytics-tool.git

# Verify remote was added
git remote -v
```

**Expected Output:**
```
origin  https://github.com/abukar10/Sonia-swap-pricing-analytics-tool.git (fetch)
origin  https://github.com/abukar10/Sonia-swap-pricing-analytics-tool.git (push)
```

#### 3.3 Pushing Code to GitHub

**First Push:**
```bash
# Rename branch to 'main' (GitHub standard)
git branch -M main

# Push to GitHub
git push -u origin main
```

**Authentication:**
- You'll be prompted for GitHub username and password
- **Note**: If you have 2FA enabled, use a Personal Access Token instead of password
  - Generate token: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Select `repo` scope
  - Use token as password when prompted

**Subsequent Pushes:**
```bash
# After making changes
git add .
git commit -m "Description of changes"
git push
```

#### 3.4 Repository Structure on GitHub

**What Gets Pushed:**
- All source code files (`src/`, `app.py`)
- Configuration files (`.streamlit/config.toml`, `requirements.txt`)
- Data files (`data/*.csv`)
- Documentation (`README.md`, `DOCUMENTATION.md`)
- Jupyter notebooks (`notebooks/`)

**What Does NOT Get Pushed** (due to .gitignore):
- Virtual environment (`swaps/`)
- Python cache files (`__pycache__/`)
- IDE settings (`.vscode/`)
- Temporary files

#### 3.5 Benefits of GitHub Version Control

1. **Backup**: Code is safely stored in the cloud
2. **Version History**: Track all changes over time
3. **Collaboration**: Multiple developers can work together
4. **Rollback**: Revert to previous versions if needed
5. **Documentation**: README and code documentation in one place
6. **Integration**: Easy integration with deployment platforms (like Streamlit Cloud)

### Step 4: Deployment to Streamlit Cloud

#### 4.1 What is Streamlit Cloud?

**Streamlit Cloud** is a free, cloud-based hosting platform specifically designed for Streamlit applications. It provides:
- **Free Hosting**: No cost for public apps
- **Automatic Deployments**: Auto-deploys when you push to GitHub
- **HTTPS**: Secure connections by default
- **Public URLs**: Shareable web links
- **Easy Setup**: Minimal configuration required

**URL**: https://share.streamlit.io/

#### 4.2 Prerequisites for Streamlit Cloud

1. ✅ **GitHub Repository**: Code must be on GitHub (completed in Step 3)
2. ✅ **Streamlit App**: `app.py` file in repository root
3. ✅ **Requirements File**: `requirements.txt` with all dependencies
4. ✅ **GitHub Account**: Must have access to the repository

#### 4.3 Deployment Process

**Step 1: Sign Up for Streamlit Cloud**
1. Go to https://share.streamlit.io/
2. Click "Sign in"
3. Authorize Streamlit Cloud to access your GitHub account
4. Grant necessary permissions

**Step 2: Deploy Your App**
1. Click "New app" button
2. Fill in deployment details:
   - **Repository**: Select `abukar10/Sonia-swap-pricing-analytics-tool`
   - **Branch**: Select `main`
   - **Main file path**: Enter `app.py`
   - **App URL** (optional): Customize the URL (e.g., `sonia-swap-pricing`)
3. Click "Deploy!"

**Step 3: Wait for Deployment**
- Streamlit Cloud will:
  1. Clone your repository
  2. Install system dependencies (from `packages.txt` if exists)
  3. Install Python dependencies (from `requirements.txt`)
  4. Run your Streamlit app
  5. Provide a public URL

**Typical Deployment Time**: 1-3 minutes

#### 4.4 Deployment Configuration Files

**requirements.txt** (Required):
```
pandas
numpy
scipy
matplotlib
plotly
streamlit
```

**packages.txt** (Optional - for system packages):
```
# Leave empty if no system packages needed
# Or list packages like: gcc, libgomp1, etc.
```

**Important Note**: `packages.txt` must be empty or contain only package names (no comments), as Streamlit Cloud tries to install each line as a package.

#### 4.5 Deployment URL

**Default URL Format**:
```
https://[app-name]-[random-id].streamlit.app
```

**Example**:
```
https://sonia-swap-pricing-analytics-tool-app-jvh2vp.streamlit.app
```

**Custom URL** (if available):
- Can customize in Streamlit Cloud settings
- Format: `https://[custom-name].streamlit.app`

#### 4.6 Automatic Updates

**How It Works**:
- Streamlit Cloud monitors your GitHub repository
- When you push changes to the `main` branch, it automatically:
  1. Detects the new commit
  2. Redeploys the app with updated code
  3. Updates the live app (usually within 1-2 minutes)

**Workflow**:
```bash
# Make changes in VS Code
# Test locally: streamlit run app.py

# Commit and push
git add .
git commit -m "Updated feature X"
git push

# Streamlit Cloud automatically redeploys!
```

#### 4.7 Troubleshooting Deployment Issues

**Common Issues and Solutions:**

1. **"Error during processing dependencies"**
   - **Cause**: Invalid `packages.txt` file (contains comments)
   - **Solution**: Ensure `packages.txt` is empty or contains only package names

2. **"Module not found"**
   - **Cause**: Missing dependency in `requirements.txt`
   - **Solution**: Add missing package to `requirements.txt` and push update

3. **"File not found"**
   - **Cause**: Data files not committed to Git
   - **Solution**: Ensure all required files are in repository (check `.gitignore`)

4. **"App failed to start"**
   - **Cause**: Error in `app.py` code
   - **Solution**: Check Streamlit Cloud logs, fix error, push update

5. **"Import error"**
   - **Cause**: Incorrect import paths
   - **Solution**: Ensure relative imports work (e.g., `from src.curves import ZeroCurve`)

**Viewing Logs**:
- Click on your app in Streamlit Cloud dashboard
- Click "Manage app" → "Logs"
- Review error messages and stack traces

#### 4.8 Streamlit Cloud Features

**Available Features**:
- **Public Apps**: Free hosting for public repositories
- **Private Apps**: Available with Streamlit Cloud Pro (paid)
- **Custom Domains**: Can connect custom domain (Pro feature)
- **Secrets Management**: Store API keys securely (via `.streamlit/secrets.toml`)
- **App Analytics**: View usage statistics (Pro feature)
- **Multiple Apps**: Deploy multiple apps from same account

**Limitations (Free Tier)**:
- Apps must be from public GitHub repositories
- Limited to 1 app per repository
- No custom domains
- Apps may sleep after inactivity (wake up on first access)

### Step 5: Complete Deployment Workflow Summary

**End-to-End Process:**

```
1. Development (VS Code)
   ├── Write code in app.py and src/ modules
   ├── Test locally: streamlit run app.py
   └── Fix bugs and verify functionality

2. Version Control (Git)
   ├── git add .
   ├── git commit -m "Description"
   └── git status (verify changes)

3. Push to GitHub
   ├── git push origin main
   └── Verify on GitHub website

4. Streamlit Cloud Deployment
   ├── Automatic detection of new commit
   ├── Automatic deployment (1-3 minutes)
   └── App live at public URL

5. Updates
   ├── Make changes in VS Code
   ├── Commit and push to GitHub
   └── Streamlit Cloud auto-updates
```

### Step 6: Best Practices for Deployment

#### 6.1 Code Organization
- Keep `app.py` in repository root
- Organize source code in `src/` directory
- Store data files in `data/` directory
- Use relative imports: `from src.curves import ZeroCurve`

#### 6.2 Dependency Management
- **Pin Versions** (recommended for production):
  ```
  pandas==2.0.3
  numpy==1.24.3
  streamlit==1.28.0
  ```
- **Or Use Ranges** (for flexibility):
  ```
  pandas>=2.0.0
  streamlit>=1.25.0
  ```

#### 6.3 Testing Before Deployment
- Always test locally first: `streamlit run app.py`
- Test with different input scenarios
- Verify all features work correctly
- Check for errors in console

#### 6.4 Documentation
- Maintain up-to-date `README.md`
- Document all configuration options
- Include deployment instructions
- Document any environment-specific requirements

#### 6.5 Security Considerations
- **Never commit secrets**: Use Streamlit Cloud secrets management
- **Validate inputs**: Implement input validation in app
- **File uploads**: Validate uploaded files before processing
- **Rate limiting**: Consider rate limiting for public apps

### Step 7: Monitoring and Maintenance

#### 7.1 Monitoring Deployment
- **Streamlit Cloud Dashboard**: Monitor app status and logs
- **GitHub**: Track code changes and versions
- **User Feedback**: Monitor for user-reported issues

#### 7.2 Regular Updates
- **Market Data**: Update CSV files with latest market quotes
- **Dependencies**: Keep Python packages updated
- **Code Improvements**: Continuously improve based on feedback

#### 7.3 Backup Strategy
- **GitHub**: Primary backup (automatic with Git)
- **Local**: Keep local copy of repository
- **Data Files**: Backup market data files separately

### Deployment Checklist

**Pre-Deployment:**
- [ ] Code tested locally and working
- [ ] All dependencies in `requirements.txt`
- [ ] `.gitignore` properly configured
- [ ] No sensitive data in code
- [ ] Documentation updated

**GitHub Setup:**
- [ ] Repository created on GitHub
- [ ] Remote added: `git remote add origin [URL]`
- [ ] Code pushed: `git push -u origin main`
- [ ] Files visible on GitHub

**Streamlit Cloud:**
- [ ] Signed in to Streamlit Cloud
- [ ] Connected GitHub account
- [ ] App deployed successfully
- [ ] App accessible via URL
- [ ] All features working on cloud

**Post-Deployment:**
- [ ] Tested all app features
- [ ] Verified automatic updates work
- [ ] Monitored logs for errors
- [ ] Shared URL with users

### Conclusion

This deployment workflow provides a robust, professional approach to developing and deploying the GBP SONIA Interest Rate Swap Pricing Analytics Tool. By leveraging VS Code for development, Git for version control, GitHub for repository hosting, and Streamlit Cloud for web deployment, you have a complete CI/CD pipeline that enables:

- **Rapid Development**: Code, test, and iterate quickly
- **Version Control**: Track all changes and maintain history
- **Cloud Deployment**: Automatic deployment with every push
- **Easy Updates**: Push changes and see them live in minutes
- **Professional Workflow**: Industry-standard tools and practices

The entire process from code change to live deployment can be completed in under 5 minutes, making it ideal for iterative development and rapid prototyping.

---

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

The GBP SONIA Interest Rate Swap Pricing Analytics Tool provides a solid foundation for pricing and risk analysis of vanilla interest rate swaps. While it has limitations, it implements industry-standard methodologies and provides essential functionality for quantitative analysts, risk managers, and traders.

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

