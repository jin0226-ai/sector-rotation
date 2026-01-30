"""
FRED API Data Collector
Fetches macro economic data from Federal Reserve Economic Data
"""
import os
import logging
from datetime import datetime, date
from typing import Optional, Dict, List
import pandas as pd

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models.macro_data import MacroData
from app.core.constants import FRED_SERIES

logger = logging.getLogger(__name__)


class FREDCollector:
    """Collect macro economic data from FRED API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FRED collector

        Args:
            api_key: FRED API key. If not provided, reads from FRED_API_KEY env variable
        """
        self.api_key = api_key or os.getenv("FRED_API_KEY", "")

        if FRED_AVAILABLE and self.api_key:
            self.fred = Fred(api_key=self.api_key)
        else:
            self.fred = None
            if not FRED_AVAILABLE:
                logger.warning("fredapi not installed. Install with: pip install fredapi")
            if not self.api_key:
                logger.warning("FRED_API_KEY not set. Set it in .env file or environment")

    def fetch_series(
        self,
        series_id: str,
        start_date: Optional[str] = "2004-01-01",
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch a single FRED series

        Args:
            series_id: FRED series ID (e.g., 'GDPC1')
            start_date: Start date for data fetch
            end_date: End date (defaults to today)

        Returns:
            DataFrame with date and value columns
        """
        if not self.fred:
            logger.error("FRED API not available")
            return None

        try:
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")

            data = self.fred.get_series(
                series_id,
                observation_start=start_date,
                observation_end=end_date,
            )

            if data is not None and len(data) > 0:
                df = pd.DataFrame({"date": data.index, "value": data.values})
                df["date"] = pd.to_datetime(df["date"]).dt.date
                df["series_id"] = series_id
                return df

            logger.warning(f"No data returned for series {series_id}")
            return None

        except Exception as e:
            logger.error(f"Error fetching FRED series {series_id}: {str(e)}")
            return None

    def save_to_db(self, df: pd.DataFrame, db: Optional[Session] = None) -> int:
        """
        Save DataFrame to database

        Args:
            df: DataFrame with series_id, date, value columns
            db: Database session (creates new one if not provided)

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
                # Use INSERT OR REPLACE for SQLite
                stmt = text("""
                    INSERT OR REPLACE INTO macro_data (series_id, date, value, created_at)
                    VALUES (:series_id, :date, :value, CURRENT_TIMESTAMP)
                """)
                db.execute(
                    stmt,
                    {
                        "series_id": row["series_id"],
                        "date": row["date"],
                        "value": float(row["value"]) if pd.notna(row["value"]) else None,
                    },
                )
                count += 1

            db.commit()
            logger.info(f"Saved {count} records for series {df['series_id'].iloc[0]}")
            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving to database: {str(e)}")
            return 0

        finally:
            if close_session:
                db.close()

    def update_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> int:
        """
        Update a single series in database

        Args:
            series_id: FRED series ID
            start_date: Start date (if None, gets all available data)
            db: Database session

        Returns:
            Number of records updated
        """
        if start_date is None:
            start_date = "2004-01-01"

        df = self.fetch_series(series_id, start_date=start_date)

        if df is not None:
            return self.save_to_db(df, db)
        return 0

    def update_all_series(
        self,
        start_date: Optional[str] = "2004-01-01",
    ) -> Dict[str, int]:
        """
        Update all configured FRED series

        Args:
            start_date: Start date for all series

        Returns:
            Dict mapping series_id to number of records updated
        """
        results = {}
        db = SessionLocal()

        try:
            for series_id, info in FRED_SERIES.items():
                logger.info(f"Updating {series_id} ({info['name']})...")
                count = self.update_series(series_id, start_date=start_date, db=db)
                results[series_id] = count

        finally:
            db.close()

        total = sum(results.values())
        logger.info(f"Total records updated: {total}")
        return results

    def get_latest_date(self, series_id: str, db: Optional[Session] = None) -> Optional[date]:
        """Get the latest date for a series in the database"""
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            result = db.query(MacroData.date).filter(
                MacroData.series_id == series_id
            ).order_by(MacroData.date.desc()).first()

            return result[0] if result else None

        finally:
            if close_session:
                db.close()

    def get_series_data(
        self,
        series_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> pd.DataFrame:
        """
        Get series data from database

        Args:
            series_id: FRED series ID
            start_date: Filter start date
            end_date: Filter end date
            db: Database session

        Returns:
            DataFrame with date and value columns
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            query = db.query(MacroData).filter(MacroData.series_id == series_id)

            if start_date:
                query = query.filter(MacroData.date >= start_date)
            if end_date:
                query = query.filter(MacroData.date <= end_date)

            query = query.order_by(MacroData.date)
            results = query.all()

            if results:
                df = pd.DataFrame([
                    {"date": r.date, "value": r.value}
                    for r in results
                ])
                return df

            return pd.DataFrame(columns=["date", "value"])

        finally:
            if close_session:
                db.close()

    def get_all_latest_values(self, db: Optional[Session] = None) -> Dict[str, Dict]:
        """
        Get latest values for all tracked series

        Returns:
            Dict mapping series_id to {value, date, name, category}
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            results = {}

            for series_id, info in FRED_SERIES.items():
                # Get latest value
                latest = db.query(MacroData).filter(
                    MacroData.series_id == series_id
                ).order_by(MacroData.date.desc()).first()

                if latest:
                    results[series_id] = {
                        "value": latest.value,
                        "date": latest.date,
                        "name": info["name"],
                        "category": info["category"],
                        "frequency": info["frequency"],
                    }

            return results

        finally:
            if close_session:
                db.close()


# Demo/test function
def demo_fetch():
    """Demo function to test FRED data fetching"""
    collector = FREDCollector()

    # Test fetching GDP data
    print("Fetching GDP data...")
    df = collector.fetch_series("GDPC1", start_date="2020-01-01")

    if df is not None:
        print(f"Fetched {len(df)} records")
        print(df.head())
    else:
        print("No data fetched. Check your FRED_API_KEY")


if __name__ == "__main__":
    demo_fetch()
