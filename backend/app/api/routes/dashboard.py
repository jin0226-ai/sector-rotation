"""
Dashboard API Routes
Aggregated endpoints for frontend dashboard
"""
from fastapi import APIRouter, Depends
from typing import Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.macro_data import MacroData
from app.models.sector_data import SectorData
from app.models.scores import SectorScore, BusinessCycle
from app.services.data_collection.fred_collector import FREDCollector
from app.services.data_collection.yahoo_collector import YahooCollector
from app.services.data_processing.normalizer import MacroDataNormalizer
from app.services.ml.scorer import SectorScorer, BusinessCycleDetector
from app.core.constants import SECTOR_ETFS, FRED_SERIES

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def get_recommendation(score: float) -> str:
    """Get recommendation based on score"""
    if score >= 70:
        return "Overweight"
    elif score >= 40:
        return "Neutral"
    else:
        return "Underweight"


@router.get("/")
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Get all dashboard data in single request
    """
    # Initialize collectors
    fred_collector = FREDCollector()
    yahoo_collector = YahooCollector()
    normalizer = MacroDataNormalizer()

    # Get business cycle
    detector = BusinessCycleDetector()
    phase, confidence = detector.detect_phase(db=db)

    # Get key macro indicators
    key_indicators = ["T10Y2Y", "UNRATE", "CPIAUCSL", "INDPRO", "UMCSENT", "BAA10Y"]

    macro_summary = []
    alerts = []

    for series_id in key_indicators:
        if series_id not in FRED_SERIES:
            continue

        info = FRED_SERIES[series_id]
        data = fred_collector.get_series_data(series_id, db=db)

        if not data.empty:
            status = normalizer.get_current_status(data["value"], series_id)

            # Determine status indicator
            if status["percentile"] >= 80:
                indicator = "high"
            elif status["percentile"] <= 20:
                indicator = "low"
            else:
                indicator = "normal"

            macro_summary.append({
                "id": series_id,
                "name": info["name"],
                "value": status["value"],
                "trend": status["trend"],
                "percentile": status["percentile"],
                "status": indicator,
            })

            # Generate alerts for extreme values
            if status["percentile"] >= 90 or status["percentile"] <= 10:
                alerts.append({
                    "indicator": info["name"],
                    "message": f"{info['name']} at {'extremely high' if status['percentile'] >= 90 else 'extremely low'} levels ({status['percentile']:.0f}th percentile)",
                    "severity": "warning" if 80 <= status["percentile"] <= 95 or 5 <= status["percentile"] <= 20 else "critical",
                })

    # Get sector rankings
    scorer = SectorScorer()
    rankings_data = scorer.get_current_rankings(db=db)

    if not rankings_data:
        # Calculate new scores
        scores = scorer.calculate_composite_scores(db=db)
        scorer.save_scores(scores, db=db)
        rankings_data = scorer.get_current_rankings(db=db)

    # Get prices and add to rankings
    prices = yahoo_collector.get_all_etf_prices(db=db)

    rankings = []
    for r in rankings_data:
        r["recommendation"] = get_recommendation(r["composite_score"])
        if r["symbol"] in prices:
            r["price"] = prices[r["symbol"]]["close"]
            r["change_1d"] = prices[r["symbol"]]["change_1d"]
        rankings.append(r)

    # Get top movers
    all_changes = []
    for symbol in SECTOR_ETFS.keys():
        if symbol in prices:
            all_changes.append({
                "symbol": symbol,
                "name": SECTOR_ETFS[symbol]["name"],
                "change": prices[symbol]["change_1d"],
            })

    all_changes.sort(key=lambda x: x["change"], reverse=True)
    gainers = all_changes[:3]
    losers = all_changes[-3:][::-1]

    # Get 30-day score trends
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    scores = db.query(SectorScore).filter(
        SectorScore.date >= start_date,
        SectorScore.date <= end_date,
    ).order_by(SectorScore.date).all()

    from collections import defaultdict
    dates = set()
    score_by_sector = defaultdict(dict)

    for s in scores:
        dates.add(s.date)
        score_by_sector[s.symbol][s.date] = s.composite_score

    sorted_dates = sorted(dates)

    score_trends = {
        "dates": [d.isoformat() for d in sorted_dates],
        "sectors": {
            symbol: {
                "name": SECTOR_ETFS[symbol]["name"],
                "scores": [score_by_sector[symbol].get(d) for d in sorted_dates]
            }
            for symbol in SECTOR_ETFS.keys()
        },
    }

    # Get last updated timestamp
    latest_macro = db.query(MacroData.created_at).order_by(
        MacroData.created_at.desc()
    ).first()

    latest_sector = db.query(SectorData.created_at).order_by(
        SectorData.created_at.desc()
    ).first()

    last_updated = None
    if latest_macro and latest_sector:
        last_updated = max(latest_macro[0], latest_sector[0]).isoformat()
    elif latest_macro:
        last_updated = latest_macro[0].isoformat()
    elif latest_sector:
        last_updated = latest_sector[0].isoformat()

    return {
        "last_updated": last_updated,
        "business_cycle": {
            "phase": phase,
            "confidence": round(confidence, 2),
        },
        "macro_summary": {
            "key_indicators": macro_summary,
            "alerts": alerts,
        },
        "sector_rankings": rankings,
        "top_movers": {
            "gainers": gainers,
            "losers": losers,
        },
        "score_trends_30d": score_trends,
    }


@router.get("/summary")
async def get_summary(db: Session = Depends(get_db)):
    """
    Get quick summary stats
    """
    # Count records
    macro_count = db.query(MacroData).count()
    sector_count = db.query(SectorData).count()
    score_count = db.query(SectorScore).count()

    # Get date ranges
    macro_dates = db.query(
        MacroData.date
    ).order_by(MacroData.date).first(), db.query(
        MacroData.date
    ).order_by(MacroData.date.desc()).first()

    sector_dates = db.query(
        SectorData.date
    ).order_by(SectorData.date).first(), db.query(
        SectorData.date
    ).order_by(SectorData.date.desc()).first()

    return {
        "macro_data": {
            "count": macro_count,
            "start_date": macro_dates[0][0].isoformat() if macro_dates[0] else None,
            "end_date": macro_dates[1][0].isoformat() if macro_dates[1] else None,
        },
        "sector_data": {
            "count": sector_count,
            "start_date": sector_dates[0][0].isoformat() if sector_dates[0] else None,
            "end_date": sector_dates[1][0].isoformat() if sector_dates[1] else None,
        },
        "scores": {
            "count": score_count,
        },
    }
