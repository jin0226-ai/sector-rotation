"""
Data Normalizer Module
Normalize and standardize macro economic data
"""
import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import pickle
from pathlib import Path


class DataNormalizer:
    """Normalize and standardize data for analysis and ML"""

    def __init__(self, method: str = "zscore"):
        """
        Initialize normalizer

        Args:
            method: Normalization method ('zscore', 'minmax', 'percentile')
        """
        self.method = method
        self.scalers: Dict[str, StandardScaler | MinMaxScaler] = {}

    def fit_transform(
        self,
        series: pd.Series,
        name: str,
        lookback: Optional[int] = None,
    ) -> pd.Series:
        """
        Fit normalizer and transform data

        Args:
            series: Input series
            name: Name for storing scaler
            lookback: Rolling window for normalization (None = full history)

        Returns:
            Normalized series
        """
        if lookback:
            return self._rolling_normalize(series, lookback)
        else:
            return self._full_normalize(series, name)

    def _full_normalize(self, series: pd.Series, name: str) -> pd.Series:
        """Normalize using full series statistics"""
        values = series.values.reshape(-1, 1)
        valid_mask = ~np.isnan(values.flatten())

        if self.method == "zscore":
            scaler = StandardScaler()
        elif self.method == "minmax":
            scaler = MinMaxScaler()
        else:
            raise ValueError(f"Unknown method: {self.method}")

        scaler.fit(values[valid_mask].reshape(-1, 1))
        self.scalers[name] = scaler

        result = np.full(len(series), np.nan)
        result[valid_mask] = scaler.transform(values[valid_mask].reshape(-1, 1)).flatten()

        return pd.Series(result, index=series.index)

    def _rolling_normalize(self, series: pd.Series, lookback: int) -> pd.Series:
        """Normalize using rolling window statistics"""
        if self.method == "zscore":
            rolling_mean = series.rolling(window=lookback, min_periods=20).mean()
            rolling_std = series.rolling(window=lookback, min_periods=20).std()
            return (series - rolling_mean) / rolling_std.replace(0, np.nan)

        elif self.method == "minmax":
            rolling_min = series.rolling(window=lookback, min_periods=20).min()
            rolling_max = series.rolling(window=lookback, min_periods=20).max()
            range_val = rolling_max - rolling_min
            return (series - rolling_min) / range_val.replace(0, np.nan)

        elif self.method == "percentile":
            def calc_percentile(window):
                if len(window) < 2:
                    return 50
                return (window.iloc[-1] > window.iloc[:-1]).sum() / (len(window) - 1) * 100

            return series.rolling(window=lookback, min_periods=20).apply(
                calc_percentile, raw=False
            )

        else:
            raise ValueError(f"Unknown method: {self.method}")

    def transform(self, series: pd.Series, name: str) -> pd.Series:
        """
        Transform data using previously fitted scaler

        Args:
            series: Input series
            name: Name of previously fitted scaler

        Returns:
            Normalized series
        """
        if name not in self.scalers:
            raise ValueError(f"Scaler '{name}' not found. Call fit_transform first.")

        scaler = self.scalers[name]
        values = series.values.reshape(-1, 1)
        valid_mask = ~np.isnan(values.flatten())

        result = np.full(len(series), np.nan)
        result[valid_mask] = scaler.transform(values[valid_mask].reshape(-1, 1)).flatten()

        return pd.Series(result, index=series.index)

    def inverse_transform(self, series: pd.Series, name: str) -> pd.Series:
        """
        Inverse transform normalized data

        Args:
            series: Normalized series
            name: Name of scaler

        Returns:
            Original scale series
        """
        if name not in self.scalers:
            raise ValueError(f"Scaler '{name}' not found.")

        scaler = self.scalers[name]
        values = series.values.reshape(-1, 1)
        valid_mask = ~np.isnan(values.flatten())

        result = np.full(len(series), np.nan)
        result[valid_mask] = scaler.inverse_transform(values[valid_mask].reshape(-1, 1)).flatten()

        return pd.Series(result, index=series.index)

    def save(self, filepath: str | Path):
        """Save scalers to file"""
        with open(filepath, "wb") as f:
            pickle.dump(self.scalers, f)

    def load(self, filepath: str | Path):
        """Load scalers from file"""
        with open(filepath, "rb") as f:
            self.scalers = pickle.load(f)

    @staticmethod
    def calculate_percentile(
        value: float,
        series: pd.Series,
    ) -> float:
        """
        Calculate percentile of a value within a series

        Args:
            value: Value to calculate percentile for
            series: Historical series

        Returns:
            Percentile (0-100)
        """
        clean_series = series.dropna()
        if len(clean_series) == 0:
            return 50.0

        return (clean_series < value).sum() / len(clean_series) * 100

    @staticmethod
    def calculate_trend(
        series: pd.Series,
        periods: int = 3,
    ) -> str:
        """
        Calculate trend direction

        Args:
            series: Value series
            periods: Number of recent periods to consider

        Returns:
            'rising', 'falling', or 'stable'
        """
        if len(series) < periods + 1:
            return "stable"

        recent = series.iloc[-periods:]
        slope = np.polyfit(range(len(recent)), recent, 1)[0]

        threshold = series.std() * 0.1
        if slope > threshold:
            return "rising"
        elif slope < -threshold:
            return "falling"
        else:
            return "stable"


class MacroDataNormalizer:
    """Specialized normalizer for macro economic data"""

    def __init__(self):
        self.normalizer = DataNormalizer(method="percentile")

    def normalize_macro_variable(
        self,
        series: pd.Series,
        variable_name: str,
        lookback_years: int = 10,
    ) -> Dict[str, pd.Series]:
        """
        Normalize a macro variable and calculate derived metrics

        Args:
            series: Raw macro data series
            variable_name: Name of the variable
            lookback_years: Years for rolling calculations

        Returns:
            Dict with normalized values, percentiles, z-scores, etc.
        """
        lookback = lookback_years * 252  # Approximate trading days

        result = {}

        # Current value (raw)
        result[f"{variable_name}_value"] = series

        # Z-score (rolling)
        rolling_mean = series.rolling(window=lookback, min_periods=20).mean()
        rolling_std = series.rolling(window=lookback, min_periods=20).std()
        result[f"{variable_name}_zscore"] = (series - rolling_mean) / rolling_std

        # Historical percentile (rolling)
        def calc_pct(window):
            if len(window) < 2:
                return 50
            return (window.iloc[-1] > window.iloc[:-1]).sum() / (len(window) - 1) * 100

        result[f"{variable_name}_percentile"] = series.rolling(
            window=lookback, min_periods=20
        ).apply(calc_pct, raw=False)

        # Rate of change (various periods)
        for months in [1, 3, 6, 12]:
            periods = months * 21  # Approximate trading days per month
            result[f"{variable_name}_roc_{months}m"] = series.pct_change(periods) * 100

        # Momentum (acceleration)
        roc_3m = result[f"{variable_name}_roc_3m"]
        result[f"{variable_name}_acceleration"] = roc_3m.diff(21)

        # Trend vs moving averages
        for months in [3, 6, 12]:
            ma_periods = months * 21
            ma = series.rolling(window=ma_periods, min_periods=10).mean()
            result[f"{variable_name}_vs_ma_{months}m"] = (series / ma - 1) * 100

        return result

    def get_current_status(
        self,
        series: pd.Series,
        variable_name: str,
    ) -> Dict:
        """
        Get current status of a macro variable

        Args:
            series: Raw macro data series
            variable_name: Name of the variable

        Returns:
            Dict with current value, percentile, trend, etc.
        """
        if series.empty:
            return {
                "value": None,
                "percentile": None,
                "trend": "unknown",
                "zscore": None,
                "roc_1m": None,
            }

        current_value = series.iloc[-1]

        # Calculate percentile
        percentile = DataNormalizer.calculate_percentile(current_value, series)

        # Calculate trend
        trend = DataNormalizer.calculate_trend(series, periods=3)

        # Calculate z-score
        mean = series.mean()
        std = series.std()
        zscore = (current_value - mean) / std if std > 0 else 0

        # Calculate 1-month rate of change
        if len(series) > 21:
            roc_1m = (current_value / series.iloc[-22] - 1) * 100
        else:
            roc_1m = None

        return {
            "value": round(current_value, 4),
            "percentile": round(percentile, 1),
            "trend": trend,
            "zscore": round(zscore, 2),
            "roc_1m": round(roc_1m, 2) if roc_1m else None,
        }
