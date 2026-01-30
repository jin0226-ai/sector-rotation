"""
Core constants for the Sector Rotation System
Contains FRED series IDs, sector ETF symbols, and configuration
"""

# =============================================================================
# FRED MACRO ECONOMIC SERIES
# =============================================================================

FRED_SERIES = {
    # Growth Indicators
    "GDPC1": {"name": "Real GDP", "frequency": "quarterly", "category": "growth"},
    "INDPRO": {"name": "Industrial Production", "frequency": "monthly", "category": "growth"},
    "TCU": {"name": "Capacity Utilization", "frequency": "monthly", "category": "growth"},
    "RSXFS": {"name": "Retail Sales Ex Food Services", "frequency": "monthly", "category": "growth"},
    "DGORDER": {"name": "Durable Goods Orders", "frequency": "monthly", "category": "growth"},
    "USSLIND": {"name": "Leading Index", "frequency": "monthly", "category": "growth"},

    # Labor Market
    "UNRATE": {"name": "Unemployment Rate", "frequency": "monthly", "category": "labor"},
    "PAYEMS": {"name": "Total Nonfarm Payrolls", "frequency": "monthly", "category": "labor"},
    "ICSA": {"name": "Initial Jobless Claims", "frequency": "weekly", "category": "labor"},
    "CIVPART": {"name": "Labor Force Participation", "frequency": "monthly", "category": "labor"},
    "JTSJOL": {"name": "Job Openings", "frequency": "monthly", "category": "labor"},

    # Inflation
    "CPIAUCSL": {"name": "CPI All Items", "frequency": "monthly", "category": "inflation"},
    "CPILFESL": {"name": "Core CPI", "frequency": "monthly", "category": "inflation"},
    "PCEPI": {"name": "PCE Price Index", "frequency": "monthly", "category": "inflation"},
    "PPIACO": {"name": "Producer Price Index", "frequency": "monthly", "category": "inflation"},
    "DCOILWTICO": {"name": "WTI Crude Oil", "frequency": "daily", "category": "inflation"},

    # Interest Rates & Yield Curve
    "FEDFUNDS": {"name": "Federal Funds Rate", "frequency": "monthly", "category": "rates"},
    "DGS10": {"name": "10-Year Treasury", "frequency": "daily", "category": "rates"},
    "DGS2": {"name": "2-Year Treasury", "frequency": "daily", "category": "rates"},
    "T10Y2Y": {"name": "10Y-2Y Spread", "frequency": "daily", "category": "rates"},
    "T10Y3M": {"name": "10Y-3M Spread", "frequency": "daily", "category": "rates"},
    "BAA10Y": {"name": "Corporate Bond Spread", "frequency": "daily", "category": "rates"},

    # Sentiment & Surveys
    "UMCSENT": {"name": "Consumer Sentiment", "frequency": "monthly", "category": "sentiment"},
    "MANEMP": {"name": "Manufacturing Employment", "frequency": "monthly", "category": "sentiment"},

    # Housing & Credit
    "HOUST": {"name": "Housing Starts", "frequency": "monthly", "category": "housing"},
    "PERMIT": {"name": "Building Permits", "frequency": "monthly", "category": "housing"},
    "CSUSHPISA": {"name": "Case-Shiller Home Price", "frequency": "monthly", "category": "housing"},
    "TOTALSL": {"name": "Consumer Credit", "frequency": "monthly", "category": "credit"},

    # Money & Financial Conditions
    "M2SL": {"name": "M2 Money Supply", "frequency": "monthly", "category": "money"},
    "NFCI": {"name": "Financial Conditions Index", "frequency": "weekly", "category": "financial"},
    "STLFSI4": {"name": "Financial Stress Index", "frequency": "weekly", "category": "financial"},
}

# ISM PMI (from ISM website or alternative sources)
ISM_INDICATORS = {
    "ISM_PMI": {"name": "ISM Manufacturing PMI", "frequency": "monthly"},
    "ISM_NEW_ORDERS": {"name": "ISM New Orders", "frequency": "monthly"},
    "ISM_SERVICES": {"name": "ISM Services PMI", "frequency": "monthly"},
}

# =============================================================================
# SECTOR ETFs (S&P 500 GICS Sectors)
# =============================================================================

SECTOR_ETFS = {
    "XLK": {"name": "Technology", "full_name": "Technology Select Sector SPDR"},
    "XLV": {"name": "Healthcare", "full_name": "Health Care Select Sector SPDR"},
    "XLF": {"name": "Financials", "full_name": "Financial Select Sector SPDR"},
    "XLY": {"name": "Consumer Discretionary", "full_name": "Consumer Discretionary Select Sector SPDR"},
    "XLP": {"name": "Consumer Staples", "full_name": "Consumer Staples Select Sector SPDR"},
    "XLE": {"name": "Energy", "full_name": "Energy Select Sector SPDR"},
    "XLI": {"name": "Industrials", "full_name": "Industrial Select Sector SPDR"},
    "XLB": {"name": "Materials", "full_name": "Materials Select Sector SPDR"},
    "XLU": {"name": "Utilities", "full_name": "Utilities Select Sector SPDR"},
    "XLRE": {"name": "Real Estate", "full_name": "Real Estate Select Sector SPDR"},
    "XLC": {"name": "Communication Services", "full_name": "Communication Services Select Sector SPDR"},
}

BENCHMARK_ETF = "SPY"  # S&P 500 ETF

ALL_ETFS = list(SECTOR_ETFS.keys()) + [BENCHMARK_ETF]

# =============================================================================
# BUSINESS CYCLE PHASES (Fidelity Model)
# =============================================================================

BUSINESS_CYCLE_PHASES = ["early_cycle", "mid_cycle", "late_cycle", "recession"]

# Historical sector performance by business cycle phase
# Based on Fidelity's research
PHASE_SECTOR_SCORES = {
    "early_cycle": {
        "XLF": 0.9,   # Financials - Strong
        "XLY": 0.85,  # Consumer Discretionary - Strong
        "XLI": 0.8,   # Industrials - Strong
        "XLRE": 0.75, # Real Estate - Strong
        "XLB": 0.7,   # Materials - Moderate
        "XLK": 0.6,   # Technology - Moderate
        "XLC": 0.55,  # Communication - Moderate
        "XLE": 0.5,   # Energy - Neutral
        "XLV": 0.4,   # Healthcare - Underweight
        "XLP": 0.35,  # Consumer Staples - Underweight
        "XLU": 0.3,   # Utilities - Underweight
    },
    "mid_cycle": {
        "XLK": 0.9,   # Technology - Strong
        "XLC": 0.85,  # Communication - Strong
        "XLI": 0.75,  # Industrials - Moderate
        "XLF": 0.7,   # Financials - Moderate
        "XLY": 0.65,  # Consumer Discretionary - Moderate
        "XLB": 0.6,   # Materials - Moderate
        "XLE": 0.55,  # Energy - Neutral
        "XLRE": 0.5,  # Real Estate - Neutral
        "XLV": 0.45,  # Healthcare - Neutral
        "XLP": 0.4,   # Consumer Staples - Underweight
        "XLU": 0.35,  # Utilities - Underweight
    },
    "late_cycle": {
        "XLE": 0.9,   # Energy - Strong
        "XLB": 0.85,  # Materials - Strong
        "XLV": 0.7,   # Healthcare - Moderate
        "XLI": 0.65,  # Industrials - Moderate
        "XLK": 0.6,   # Technology - Moderate
        "XLP": 0.55,  # Consumer Staples - Neutral
        "XLU": 0.5,   # Utilities - Neutral
        "XLC": 0.45,  # Communication - Neutral
        "XLF": 0.4,   # Financials - Underweight
        "XLY": 0.35,  # Consumer Discretionary - Underweight
        "XLRE": 0.3,  # Real Estate - Underweight
    },
    "recession": {
        "XLV": 0.9,   # Healthcare - Strong (Defensive)
        "XLP": 0.85,  # Consumer Staples - Strong (Defensive)
        "XLU": 0.8,   # Utilities - Strong (Defensive)
        "XLC": 0.55,  # Communication - Neutral
        "XLK": 0.5,   # Technology - Neutral
        "XLRE": 0.45, # Real Estate - Neutral
        "XLI": 0.4,   # Industrials - Underweight
        "XLB": 0.35,  # Materials - Underweight
        "XLE": 0.3,   # Energy - Underweight
        "XLF": 0.25,  # Financials - Underweight
        "XLY": 0.2,   # Consumer Discretionary - Underweight
    },
}

# =============================================================================
# SECTOR MACRO SENSITIVITY MATRIX
# =============================================================================

# How each sector responds to macro variables
# Values: -1 (negative correlation) to +1 (positive correlation)
SECTOR_MACRO_SENSITIVITY = {
    "XLK": {  # Technology
        "interest_rates": -0.6,
        "gdp_growth": 0.7,
        "consumer_confidence": 0.6,
        "yield_curve": 0.3,
        "financial_conditions": -0.5,
    },
    "XLV": {  # Healthcare - Defensive
        "gdp_growth": 0.1,
        "interest_rates": -0.2,
        "unemployment": 0.3,  # Outperforms in downturns
        "financial_stress": 0.4,
    },
    "XLF": {  # Financials
        "interest_rates": 0.8,
        "yield_curve": 0.9,
        "gdp_growth": 0.6,
        "credit_spreads": -0.7,
        "housing": 0.5,
    },
    "XLY": {  # Consumer Discretionary
        "consumer_confidence": 0.8,
        "unemployment": -0.7,
        "gdp_growth": 0.7,
        "retail_sales": 0.6,
    },
    "XLP": {  # Consumer Staples - Defensive
        "gdp_growth": 0.1,
        "unemployment": 0.4,
        "inflation": -0.3,
        "financial_stress": 0.5,
    },
    "XLE": {  # Energy
        "oil_prices": 0.9,
        "gdp_growth": 0.4,
        "inflation": 0.5,
        "industrial_production": 0.6,
    },
    "XLI": {  # Industrials
        "gdp_growth": 0.7,
        "industrial_production": 0.8,
        "durable_goods": 0.7,
        "capacity_utilization": 0.6,
    },
    "XLB": {  # Materials
        "gdp_growth": 0.6,
        "inflation": 0.5,
        "industrial_production": 0.7,
        "capacity_utilization": 0.6,
    },
    "XLU": {  # Utilities - Defensive
        "interest_rates": -0.8,
        "yield_curve": -0.5,
        "financial_stress": 0.6,
        "unemployment": 0.3,
    },
    "XLRE": {  # Real Estate
        "interest_rates": -0.8,
        "housing": 0.7,
        "gdp_growth": 0.4,
        "credit_spreads": -0.5,
    },
    "XLC": {  # Communication Services
        "gdp_growth": 0.5,
        "consumer_confidence": 0.5,
        "interest_rates": -0.4,
    },
}

# =============================================================================
# SCORING WEIGHTS
# =============================================================================

SCORE_WEIGHTS = {
    "ml_score": 0.40,
    "cycle_score": 0.25,
    "momentum_score": 0.20,
    "macro_sensitivity_score": 0.15,
}

# =============================================================================
# TECHNICAL INDICATOR PARAMETERS
# =============================================================================

INDICATOR_PARAMS = {
    "ma_periods": [20, 50, 200],  # Moving average periods
    "rsi_period": 14,
    "momentum_period": 12,
    "roc_periods": [1, 3, 6, 12],  # Rate of change periods (months)
    "percentile_lookback": 252 * 10,  # 10 years for percentile calculation
}

# =============================================================================
# API CONFIGURATION
# =============================================================================

API_CONFIG = {
    "fred_api_key_env": "FRED_API_KEY",
    "data_start_date": "2004-01-01",  # 20 years of data
    "default_backtest_start": "2005-01-01",
    "rebalance_frequencies": ["daily", "weekly", "monthly"],
}
