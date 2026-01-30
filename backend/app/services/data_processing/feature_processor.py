"""
Feature Processor Module
Process and prepare features for ML model
"""
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.models.macro_data import MacroData
from app.models.sector_data import SectorData
from app.models.scores import Features
from app.services.data_collection.fred_collector import FREDCollector
from app.services.data_collection.yahoo_collector import YahooCollector
from app.services.data_processing.indicators import TechnicalIndicators
from app.services.data_processing.normalizer import MacroDataNormalizer
from app.core.constants import FRED_SERIES, SECTOR_ETFS, BENCHMARK_ETF, ALL_ETFS

logger = logging.getLogger(__name__)


class FeatureProcessor:
    """Process and prepare features for ML model"""

    def __init__(self):
        self.fred_collector = FREDCollector()
        self.yahoo_collector = YahooCollector()
        self.normalizer = MacroDataNormalizer()

    def get_macro_features(
        self,
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, float]:
        """
        Get all macro features for a specific date

        Args:
            target_date: Date to get features for (defaults to latest)
            db: Database session

        Returns:
            Dict of feature name to value
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            features = {}

            for series_id, info in FRED_SERIES.items():
                # Get series data
                query = db.query(MacroData).filter(MacroData.series_id == series_id)

                if target_date:
                    query = query.filter(MacroData.date <= target_date)

                query = query.order_by(MacroData.date)
                results = query.all()

                if not results:
                    continue

                # Convert to pandas Series
                series = pd.Series(
                    [r.value for r in results],
                    index=[r.date for r in results]
                )

                # Get current status
                status = self.normalizer.get_current_status(series, series_id)

                # Add features
                features[f"{series_id}_value"] = status["value"]
                features[f"{series_id}_percentile"] = status["percentile"]
                features[f"{series_id}_zscore"] = status["zscore"]
                features[f"{series_id}_roc_1m"] = status["roc_1m"]

                # Add more detailed features
                normalized = self.normalizer.normalize_macro_variable(
                    series, series_id, lookback_years=10
                )

                for key, val_series in normalized.items():
                    if not val_series.empty:
                        features[key] = val_series.iloc[-1] if pd.notna(val_series.iloc[-1]) else None

            return features

        finally:
            if close_session:
                db.close()

    def get_sector_features(
        self,
        symbol: str,
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, float]:
        """
        Get technical features for a sector ETF

        Args:
            symbol: ETF ticker symbol
            target_date: Date to get features for
            db: Database session

        Returns:
            Dict of feature name to value
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Get sector data
            query = db.query(SectorData).filter(SectorData.symbol == symbol)

            if target_date:
                query = query.filter(SectorData.date <= target_date)

            query = query.order_by(SectorData.date)
            results = query.all()

            if not results:
                return {}

            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    "date": r.date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "adj_close": r.adj_close,
                    "volume": r.volume,
                }
                for r in results
            ])

            # Calculate technical indicators
            df_with_indicators = TechnicalIndicators.calculate_all_indicators(df)

            # Get latest values
            latest = df_with_indicators.iloc[-1]

            features = {}
            indicator_cols = [c for c in df_with_indicators.columns
                           if c not in ["date", "open", "high", "low", "close", "adj_close", "volume"]]

            for col in indicator_cols:
                value = latest[col]
                features[f"{symbol}_{col}"] = value if pd.notna(value) else None

            # Add returns
            returns = self.yahoo_collector.calculate_returns(symbol, db=db)
            for period, ret in returns.items():
                features[f"{symbol}_return_{period}"] = ret

            return features

        finally:
            if close_session:
                db.close()

    def get_relative_performance(
        self,
        symbol: str,
        target_date: Optional[date] = None,
        forward_periods: List[int] = [21, 63],
        db: Optional[Session] = None,
    ) -> Dict[str, float]:
        """
        Calculate relative performance vs benchmark (SPY)

        Args:
            symbol: Sector ETF symbol
            target_date: Date for calculation
            forward_periods: Forward looking periods in days
            db: Database session

        Returns:
            Dict with relative returns
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            results = {}

            # Get sector and benchmark data
            sector_df = self.yahoo_collector.get_etf_data(symbol, db=db)
            benchmark_df = self.yahoo_collector.get_etf_data(BENCHMARK_ETF, db=db)

            if sector_df.empty or benchmark_df.empty:
                return results

            # Merge on date
            sector_df = sector_df.set_index("date")
            benchmark_df = benchmark_df.set_index("date")

            # Calculate returns
            sector_returns = sector_df["adj_close"].pct_change()
            benchmark_returns = benchmark_df["adj_close"].pct_change()

            # Filter to target date
            if target_date:
                sector_returns = sector_returns[sector_returns.index <= target_date]
                benchmark_returns = benchmark_returns[benchmark_returns.index <= target_date]

            # Historical relative performance
            for period in [21, 63, 126, 252]:
                if len(sector_returns) > period:
                    sector_ret = (1 + sector_returns.iloc[-period:]).prod() - 1
                    bench_ret = (1 + benchmark_returns.iloc[-period:]).prod() - 1
                    results[f"relative_{period}d"] = (sector_ret - bench_ret) * 100

            return results

        finally:
            if close_session:
                db.close()

    def get_all_features_for_date(
        self,
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
        """
        Get all features for all sectors on a specific date

        Args:
            target_date: Date to get features for
            db: Database session

        Returns:
            Tuple of (macro_features, sector_features_by_symbol)
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Get macro features (same for all sectors)
            macro_features = self.get_macro_features(target_date, db)

            # Get sector-specific features
            sector_features = {}
            for symbol in SECTOR_ETFS.keys():
                features = self.get_sector_features(symbol, target_date, db)
                relative = self.get_relative_performance(symbol, target_date, db=db)
                features.update(relative)
                sector_features[symbol] = features

            return macro_features, sector_features

        finally:
            if close_session:
                db.close()

    def prepare_training_data(
        self,
        start_date: str = "2005-01-01",
        end_date: Optional[str] = None,
        target_period: int = 21,  # 1 month forward
        db: Optional[Session] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare training data for ML model

        Args:
            start_date: Start date for training data
            end_date: End date for training data
            target_period: Forward period for target calculation (days)
            db: Database session

        Returns:
            Tuple of (features_df, targets_df)
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()

            # Get all dates with data
            dates_query = db.query(SectorData.date).filter(
                SectorData.symbol == BENCHMARK_ETF,
                SectorData.date >= start,
                SectorData.date <= end,
            ).distinct().order_by(SectorData.date)

            dates = [r[0] for r in dates_query.all()]

            # Sample dates (e.g., weekly) to reduce computation
            sample_dates = dates[::5]  # Every 5 trading days

            all_features = []
            all_targets = []

            logger.info(f"Processing {len(sample_dates)} sample dates...")

            for i, target_date in enumerate(sample_dates):
                if i % 50 == 0:
                    logger.info(f"Processing date {i+1}/{len(sample_dates)}: {target_date}")

                # Get features
                macro_features, sector_features = self.get_all_features_for_date(
                    target_date, db
                )

                # Get forward returns for targets
                forward_date = target_date + timedelta(days=target_period + 10)  # Buffer

                for symbol in SECTOR_ETFS.keys():
                    # Combine features
                    row_features = {
                        "date": target_date,
                        "symbol": symbol,
                        **macro_features,
                        **sector_features.get(symbol, {}),
                    }

                    # Calculate forward return
                    sector_query = db.query(SectorData).filter(
                        SectorData.symbol == symbol,
                        SectorData.date > target_date,
                        SectorData.date <= forward_date,
                    ).order_by(SectorData.date).limit(target_period + 5)

                    sector_prices = [r.adj_close for r in sector_query.all()]

                    bench_query = db.query(SectorData).filter(
                        SectorData.symbol == BENCHMARK_ETF,
                        SectorData.date > target_date,
                        SectorData.date <= forward_date,
                    ).order_by(SectorData.date).limit(target_period + 5)

                    bench_prices = [r.adj_close for r in bench_query.all()]

                    if len(sector_prices) >= target_period and len(bench_prices) >= target_period:
                        # Get current prices
                        current_sector = db.query(SectorData).filter(
                            SectorData.symbol == symbol,
                            SectorData.date == target_date,
                        ).first()

                        current_bench = db.query(SectorData).filter(
                            SectorData.symbol == BENCHMARK_ETF,
                            SectorData.date == target_date,
                        ).first()

                        if current_sector and current_bench:
                            sector_ret = (sector_prices[target_period - 1] / current_sector.adj_close - 1) * 100
                            bench_ret = (bench_prices[target_period - 1] / current_bench.adj_close - 1) * 100
                            relative_ret = sector_ret - bench_ret

                            row_target = {
                                "date": target_date,
                                "symbol": symbol,
                                "sector_return": sector_ret,
                                "benchmark_return": bench_ret,
                                "relative_return": relative_ret,
                            }

                            all_features.append(row_features)
                            all_targets.append(row_target)

            features_df = pd.DataFrame(all_features)
            targets_df = pd.DataFrame(all_targets)

            logger.info(f"Prepared {len(features_df)} training samples")

            return features_df, targets_df

        finally:
            if close_session:
                db.close()

    def save_features_to_db(
        self,
        features: Dict[str, float],
        target_date: date,
        db: Optional[Session] = None,
    ):
        """
        Save calculated features to database

        Args:
            features: Dict of feature name to value
            target_date: Date for the features
            db: Database session
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            for name, value in features.items():
                if value is not None and not np.isnan(value):
                    stmt = text("""
                        INSERT OR REPLACE INTO features (date, feature_name, value, created_at)
                        VALUES (:date, :feature_name, :value, CURRENT_TIMESTAMP)
                    """)
                    db.execute(stmt, {
                        "date": target_date,
                        "feature_name": name,
                        "value": float(value),
                    })

            db.commit()
            logger.info(f"Saved {len(features)} features for {target_date}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving features: {str(e)}")

        finally:
            if close_session:
                db.close()

    def process_daily_features(self, target_date: Optional[date] = None):
        """
        Process and save features for a specific date (or today)

        Args:
            target_date: Date to process (defaults to today)
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Processing features for {target_date}...")

        db = SessionLocal()

        try:
            # Get all features
            macro_features, sector_features = self.get_all_features_for_date(
                target_date, db
            )

            # Save macro features
            self.save_features_to_db(macro_features, target_date, db)

            # Save sector features
            for symbol, features in sector_features.items():
                self.save_features_to_db(features, target_date, db)

            logger.info(f"Feature processing complete for {target_date}")

        finally:
            db.close()
