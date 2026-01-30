"""
Yahoo Finance Data Collector
Fetches sector ETF price data
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
import pandas as pd

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.models.sector_data import SectorData
from app.core.constants import SECTOR_ETFS, BENCHMARK_ETF, ALL_ETFS

logger = logging.getLogger(__name__)


class YahooCollector:
    """Collect sector ETF data from Yahoo Finance"""

    def __init__(self):
        """Initialize Yahoo Finance collector"""
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not installed. Install with: pip install yfinance")

    def fetch_etf_data(
        self,
        symbol: str,
        start_date: Optional[str] = "2004-01-01",
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch ETF price data from Yahoo Finance

        Args:
            symbol: ETF ticker symbol (e.g., 'XLK')
            start_date: Start date for data fetch
            end_date: End date (defaults to today)

        Returns:
            DataFrame with OHLCV data
        """
        if not YFINANCE_AVAILABLE:
            logger.error("yfinance not available")
            return None

        try:
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, auto_adjust=False)

            if df is not None and len(df) > 0:
                df = df.reset_index()
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]

                # Standardize column names
                df = df.rename(columns={
                    "adj_close": "adj_close",
                    "stock_splits": "splits",
                })

                # Keep only needed columns
                columns_to_keep = ["date", "open", "high", "low", "close", "volume"]
                if "adj_close" in df.columns:
                    columns_to_keep.append("adj_close")

                df = df[[c for c in columns_to_keep if c in df.columns]]

                # Convert date
                df["date"] = pd.to_datetime(df["date"]).dt.date
                df["symbol"] = symbol

                return df

            logger.warning(f"No data returned for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Error fetching Yahoo data for {symbol}: {str(e)}")
            return None

    def save_to_db(self, df: pd.DataFrame, db: Optional[Session] = None) -> int:
        """
        Save DataFrame to database

        Args:
            df: DataFrame with ETF price data
            db: Database session

        Returns:
            Number of records saved/updated
        """
        if df is None or df.empty:
            return 0

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            count = 0
            for _, row in df.iterrows():
                adj_close = row.get("adj_close", row["close"])

                stmt = text("""
                    INSERT OR REPLACE INTO sector_data
                    (symbol, date, open, high, low, close, adj_close, volume, created_at)
                    VALUES (:symbol, :date, :open, :high, :low, :close, :adj_close, :volume, CURRENT_TIMESTAMP)
                """)
                db.execute(
                    stmt,
                    {
                        "symbol": row["symbol"],
                        "date": row["date"],
                        "open": float(row["open"]) if pd.notna(row["open"]) else None,
                        "high": float(row["high"]) if pd.notna(row["high"]) else None,
                        "low": float(row["low"]) if pd.notna(row["low"]) else None,
                        "close": float(row["close"]) if pd.notna(row["close"]) else None,
                        "adj_close": float(adj_close) if pd.notna(adj_close) else None,
                        "volume": int(row["volume"]) if pd.notna(row["volume"]) else None,
                    },
                )
                count += 1

            db.commit()
            logger.info(f"Saved {count} records for {df['symbol'].iloc[0]}")
            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving to database: {str(e)}")
            return 0

        finally:
            if close_session:
                db.close()

    def update_etf(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> int:
        """
        Update a single ETF in database

        Args:
            symbol: ETF ticker symbol
            start_date: Start date
            db: Database session

        Returns:
            Number of records updated
        """
        if start_date is None:
            start_date = "2004-01-01"

        df = self.fetch_etf_data(symbol, start_date=start_date)

        if df is not None:
            return self.save_to_db(df, db)
        return 0

    def update_all_etfs(
        self,
        start_date: Optional[str] = "2004-01-01",
    ) -> Dict[str, int]:
        """
        Update all sector ETFs and benchmark

        Args:
            start_date: Start date for all ETFs

        Returns:
            Dict mapping symbol to number of records updated
        """
        results = {}
        db = SessionLocal()

        try:
            for symbol in ALL_ETFS:
                name = SECTOR_ETFS.get(symbol, {}).get("name", symbol)
                logger.info(f"Updating {symbol} ({name})...")
                count = self.update_etf(symbol, start_date=start_date, db=db)
                results[symbol] = count

        finally:
            db.close()

        total = sum(results.values())
        logger.info(f"Total ETF records updated: {total}")
        return results

    def get_latest_date(self, symbol: str, db: Optional[Session] = None) -> Optional[date]:
        """Get the latest date for an ETF in the database"""
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            result = db.query(SectorData.date).filter(
                SectorData.symbol == symbol
            ).order_by(SectorData.date.desc()).first()

            return result[0] if result else None

        finally:
            if close_session:
                db.close()

    def get_etf_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> pd.DataFrame:
        """
        Get ETF data from database

        Args:
            symbol: ETF ticker symbol
            start_date: Filter start date
            end_date: Filter end date
            db: Database session

        Returns:
            DataFrame with OHLCV data
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            query = db.query(SectorData).filter(SectorData.symbol == symbol)

            if start_date:
                query = query.filter(SectorData.date >= start_date)
            if end_date:
                query = query.filter(SectorData.date <= end_date)

            query = query.order_by(SectorData.date)
            results = query.all()

            if results:
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
                return df

            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close", "volume"])

        finally:
            if close_session:
                db.close()

    def get_all_etf_prices(
        self,
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Dict]:
        """
        Get latest prices for all ETFs

        Args:
            target_date: Specific date (defaults to latest available)
            db: Database session

        Returns:
            Dict mapping symbol to price data
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            results = {}

            for symbol in ALL_ETFS:
                query = db.query(SectorData).filter(SectorData.symbol == symbol)

                if target_date:
                    query = query.filter(SectorData.date <= target_date)

                latest = query.order_by(SectorData.date.desc()).first()

                if latest:
                    # Calculate returns
                    prev_data = db.query(SectorData).filter(
                        SectorData.symbol == symbol,
                        SectorData.date < latest.date,
                    ).order_by(SectorData.date.desc()).first()

                    change_1d = 0
                    if prev_data and prev_data.adj_close:
                        change_1d = (latest.adj_close - prev_data.adj_close) / prev_data.adj_close * 100

                    results[symbol] = {
                        "date": latest.date,
                        "close": latest.close,
                        "adj_close": latest.adj_close,
                        "volume": latest.volume,
                        "change_1d": round(change_1d, 2),
                        "name": SECTOR_ETFS.get(symbol, {}).get("name", symbol),
                    }

            return results

        finally:
            if close_session:
                db.close()

    def calculate_returns(
        self,
        symbol: str,
        periods: List[int] = [1, 5, 21, 63, 126, 252],
        db: Optional[Session] = None,
    ) -> Dict[str, float]:
        """
        Calculate returns for various periods

        Args:
            symbol: ETF ticker symbol
            periods: List of lookback periods in trading days
            db: Database session

        Returns:
            Dict mapping period label to return percentage
        """
        df = self.get_etf_data(symbol, db=db)

        if df.empty:
            return {}

        df = df.sort_values("date")
        latest_price = df["adj_close"].iloc[-1]

        returns = {}
        period_labels = {
            1: "1d",
            5: "1w",
            21: "1m",
            63: "3m",
            126: "6m",
            252: "1y",
        }

        for period in periods:
            if len(df) > period:
                past_price = df["adj_close"].iloc[-period - 1]
                ret = (latest_price - past_price) / past_price * 100
                label = period_labels.get(period, f"{period}d")
                returns[label] = round(ret, 2)

        return returns


# Demo/test function
def demo_fetch():
    """Demo function to test Yahoo Finance data fetching"""
    collector = YahooCollector()

    # Test fetching XLK data
    print("Fetching XLK (Technology) data...")
    df = collector.fetch_etf_data("XLK", start_date="2024-01-01")

    if df is not None:
        print(f"Fetched {len(df)} records")
        print(df.head())
        print(df.tail())
    else:
        print("No data fetched")


if __name__ == "__main__":
    demo_fetch()
