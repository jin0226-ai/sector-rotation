"""
Daily data update script for Windows Task Scheduler
Run at 6:00 PM ET (after market close)

Usage:
    python scripts/daily_update.py
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f'daily_update_{datetime.now().strftime("%Y%m%d")}.log'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Main update function"""
    logger.info("=" * 60)
    logger.info("Starting daily update...")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        # Initialize database
        logger.info("Initializing database...")
        from app.database import init_db
        init_db()

        # 1. Collect FRED data
        logger.info("\n[1/5] Collecting FRED macro data...")
        from app.services.data_collection.fred_collector import FREDCollector

        fred = FREDCollector()
        if fred.fred:
            fred_results = fred.update_all_series()
            logger.info(f"FRED data updated: {sum(fred_results.values())} records")
        else:
            logger.warning("FRED API not configured. Skipping FRED data collection.")
            logger.warning("Set FRED_API_KEY environment variable to enable.")

        # 2. Collect Yahoo Finance data
        logger.info("\n[2/5] Collecting sector ETF data from Yahoo Finance...")
        from app.services.data_collection.yahoo_collector import YahooCollector

        yahoo = YahooCollector()
        yahoo_results = yahoo.update_all_etfs()
        logger.info(f"Yahoo Finance data updated: {sum(yahoo_results.values())} records")

        # 3. Process features
        logger.info("\n[3/5] Processing features...")
        from app.services.data_processing.feature_processor import FeatureProcessor

        processor = FeatureProcessor()
        processor.process_daily_features()
        logger.info("Features processed successfully")

        # 4. Update business cycle
        logger.info("\n[4/5] Detecting business cycle phase...")
        from app.services.ml.scorer import BusinessCycleDetector
        from app.database import SessionLocal

        detector = BusinessCycleDetector()
        db = SessionLocal()
        try:
            phase, confidence = detector.detect_phase(db)
            detector.save_phase(phase, confidence, db=db)
            logger.info(f"Business cycle: {phase} (confidence: {confidence:.1%})")
        finally:
            db.close()

        # 5. Update sector scores
        logger.info("\n[5/5] Calculating sector scores...")
        from app.services.ml.scorer import SectorScorer

        scorer = SectorScorer()
        scores = scorer.update_daily_scores()

        # Log top sectors
        sorted_scores = sorted(
            scores.items(),
            key=lambda x: x[1]["composite_score"],
            reverse=True,
        )

        logger.info("\nTop 5 Sectors Today:")
        for i, (symbol, data) in enumerate(sorted_scores[:5], 1):
            logger.info(
                f"  {i}. {symbol}: {data['composite_score']:.1f} "
                f"(ML: {data['ml_score']:.1f}, Cycle: {data['cycle_score']:.1f}, "
                f"Mom: {data['momentum_score']:.1f})"
            )

        logger.info("\n" + "=" * 60)
        logger.info("Daily update completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\nDaily update FAILED: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
