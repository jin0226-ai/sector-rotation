"""
Technical Indicators Module
Calculate moving averages, momentum, RSI, and other technical indicators
"""
import numpy as np
import pandas as pd
from typing import Optional, List, Dict


class TechnicalIndicators:
    """Calculate technical indicators for time series data"""

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """
        Simple Moving Average

        Args:
            series: Price series
            period: Number of periods

        Returns:
            SMA series
        """
        return series.rolling(window=period, min_periods=1).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """
        Exponential Moving Average

        Args:
            series: Price series
            period: Number of periods

        Returns:
            EMA series
        """
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index

        Args:
            series: Price series
            period: RSI period (default 14)

        Returns:
            RSI series (0-100)
        """
        delta = series.diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        return rsi.fillna(50)

    @staticmethod
    def momentum(series: pd.Series, period: int = 12) -> pd.Series:
        """
        Momentum (Price change over period)

        Args:
            series: Price series
            period: Lookback period

        Returns:
            Momentum series
        """
        return series.diff(period)

    @staticmethod
    def rate_of_change(series: pd.Series, period: int) -> pd.Series:
        """
        Rate of Change (Percentage change over period)

        Args:
            series: Price/value series
            period: Lookback period

        Returns:
            ROC series (percentage)
        """
        return series.pct_change(periods=period) * 100

    @staticmethod
    def macd(
        series: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, pd.Series]:
        """
        Moving Average Convergence Divergence

        Args:
            series: Price series
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period

        Returns:
            Dict with 'macd', 'signal', 'histogram' series
        """
        fast_ema = TechnicalIndicators.ema(series, fast_period)
        slow_ema = TechnicalIndicators.ema(series, slow_period)

        macd_line = fast_ema - slow_ema
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        }

    @staticmethod
    def bollinger_bands(
        series: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Dict[str, pd.Series]:
        """
        Bollinger Bands

        Args:
            series: Price series
            period: Moving average period
            std_dev: Number of standard deviations

        Returns:
            Dict with 'middle', 'upper', 'lower' bands
        """
        middle = TechnicalIndicators.sma(series, period)
        rolling_std = series.rolling(window=period, min_periods=1).std()

        upper = middle + (rolling_std * std_dev)
        lower = middle - (rolling_std * std_dev)

        return {
            "middle": middle,
            "upper": upper,
            "lower": lower,
        }

    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """
        Average True Range

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period

        Returns:
            ATR series
        """
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        return true_range.rolling(window=period, min_periods=1).mean()

    @staticmethod
    def historical_percentile(series: pd.Series, lookback: int = 2520) -> pd.Series:
        """
        Calculate historical percentile of current value

        Args:
            series: Value series
            lookback: Number of periods for percentile calculation

        Returns:
            Percentile series (0-100)
        """
        def calc_percentile(window):
            if len(window) < 2:
                return 50
            return (window.iloc[-1] > window.iloc[:-1]).sum() / (len(window) - 1) * 100

        return series.rolling(window=lookback, min_periods=20).apply(
            calc_percentile, raw=False
        )

    @staticmethod
    def zscore(series: pd.Series, lookback: int = 252) -> pd.Series:
        """
        Calculate Z-score (standard deviations from mean)

        Args:
            series: Value series
            lookback: Number of periods for calculation

        Returns:
            Z-score series
        """
        rolling_mean = series.rolling(window=lookback, min_periods=20).mean()
        rolling_std = series.rolling(window=lookback, min_periods=20).std()

        return (series - rolling_mean) / rolling_std.replace(0, np.nan)

    @staticmethod
    def trend_direction(series: pd.Series, short_period: int = 20, long_period: int = 50) -> pd.Series:
        """
        Determine trend direction based on moving average crossover

        Args:
            series: Price series
            short_period: Short MA period
            long_period: Long MA period

        Returns:
            Series with values: 1 (uptrend), -1 (downtrend), 0 (neutral)
        """
        short_ma = TechnicalIndicators.sma(series, short_period)
        long_ma = TechnicalIndicators.sma(series, long_period)

        trend = pd.Series(index=series.index, data=0)
        trend[short_ma > long_ma] = 1
        trend[short_ma < long_ma] = -1

        return trend

    @staticmethod
    def calculate_all_indicators(
        df: pd.DataFrame,
        price_col: str = "adj_close",
    ) -> pd.DataFrame:
        """
        Calculate all technical indicators for a price DataFrame

        Args:
            df: DataFrame with OHLCV data
            price_col: Column to use for calculations

        Returns:
            DataFrame with added indicator columns
        """
        result = df.copy()
        price = df[price_col]

        # Moving Averages
        for period in [20, 50, 200]:
            result[f"sma_{period}"] = TechnicalIndicators.sma(price, period)
            result[f"ema_{period}"] = TechnicalIndicators.ema(price, period)

        # Price vs MAs
        for period in [20, 50, 200]:
            result[f"price_vs_sma_{period}"] = price / result[f"sma_{period}"] - 1

        # RSI
        result["rsi_14"] = TechnicalIndicators.rsi(price, 14)

        # Momentum
        for period in [5, 10, 20]:
            result[f"momentum_{period}"] = TechnicalIndicators.momentum(price, period)

        # Rate of Change
        for period in [5, 20, 60]:
            result[f"roc_{period}"] = TechnicalIndicators.rate_of_change(price, period)

        # MACD
        macd = TechnicalIndicators.macd(price)
        result["macd"] = macd["macd"]
        result["macd_signal"] = macd["signal"]
        result["macd_histogram"] = macd["histogram"]

        # Bollinger Bands
        bb = TechnicalIndicators.bollinger_bands(price)
        result["bb_upper"] = bb["upper"]
        result["bb_middle"] = bb["middle"]
        result["bb_lower"] = bb["lower"]
        result["bb_width"] = (bb["upper"] - bb["lower"]) / bb["middle"]
        result["bb_position"] = (price - bb["lower"]) / (bb["upper"] - bb["lower"])

        # ATR (if OHLC data available)
        if all(col in df.columns for col in ["high", "low", "close"]):
            result["atr_14"] = TechnicalIndicators.atr(
                df["high"], df["low"], df["close"], 14
            )

        # Historical Percentile
        result["percentile_1y"] = TechnicalIndicators.historical_percentile(price, 252)
        result["percentile_5y"] = TechnicalIndicators.historical_percentile(price, 252 * 5)

        # Z-Score
        result["zscore_1y"] = TechnicalIndicators.zscore(price, 252)

        # Trend Direction
        result["trend"] = TechnicalIndicators.trend_direction(price)

        return result
