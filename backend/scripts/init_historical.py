"""
Initial historical data loading script
Loads 20 years of data for backtesting

Usage:
    python scripts/init_historical.py
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Load initial historical data"""
    logger.info("=" * 60)
    logger.info("Starting initial historical data load...")
    logger.info("This may take several minutes...")
    logger.info("=" * 60)

    # Initialize database
    logger.info("\nInitializing database...")
    from app.database import init_db
    init_db()

    start_date = "2004-01-01"

    # Load FRED data
    logger.info(f"\n[1/2] Loading FRED macro data from {start_date}...")
    from app.services.data_collection.fred_collector import FREDCollector

    fred = FREDCollector()
    if fred.fred:
        fred_results = fred.update_all_series(start_date=start_date)
        total_fred = sum(fred_results.values())
        logger.info(f"FRED data loaded: {total_fred} records across {len(fred_results)} series")

        for series_id, count in fred_results.items():
            logger.info(f"  - {series_id}: {count} records")
    else:
        logger.warning("FRED API not configured!")
        logger.warning("Set FRED_API_KEY in .env file to load macro data")
        logger.warning("You can get a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html")

    # Load Yahoo Finance data
    logger.info(f"\n[2/2] Loading sector ETF data from {start_date}...")
    from app.services.data_collection.yahoo_collector import YahooCollector

    yahoo = YahooCollector()
    yahoo_results = yahoo.update_all_etfs(start_date=start_date)
    total_yahoo = sum(yahoo_results.values())
    logger.info(f"Yahoo Finance data loaded: {total_yahoo} records across {len(yahoo_results)} ETFs")

    for symbol, count in yahoo_results.items():
        logger.info(f"  - {symbol}: {count} records")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Historical data load complete!")
    logger.info(f"Total macro data points: {total_fred if fred.fred else 0}")
    logger.info(f"Total ETF data points: {total_yahoo}")
    logger.info("=" * 60)

    logger.info("\nNext steps:")
    logger.info("1. Run 'python scripts/daily_update.py' to calculate initial scores")
    logger.info("2. Start the API server with 'uvicorn app.main:app --reload'")
    logger.info("3. Start the frontend with 'cd frontend && npm run dev'")


if __name__ == "__main__":
    main()
