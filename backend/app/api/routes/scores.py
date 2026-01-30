"""
Scoring API Routes
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scores import SectorScore, BusinessCycle
from app.services.ml.scorer import SectorScorer
from app.services.data_collection.yahoo_collector import YahooCollector
from app.core.constants import SECTOR_ETFS, SECTOR_MACRO_SENSITIVITY, FRED_SERIES

router = APIRouter(prefix="/api/scores", tags=["Scoring"])


def get_recommendation(score: float) -> str:
    """Get recommendation based on score"""
    if score >= 70:
        return "Overweight"
    elif score >= 40:
        return "Neutral"
    else:
        return "Underweight"


@router.get("/rankings")
async def get_sector_rankings(db: Session = Depends(get_db)):
    """
    Get current sector rankings by composite score
    """
    scorer = SectorScorer()
    rankings = scorer.get_current_rankings(db=db)

    if not rankings:
        # Calculate new scores if none exist
        scores = scorer.calculate_composite_scores(db=db)
        scorer.save_scores(scores, db=db)
        rankings = scorer.get_current_rankings(db=db)

    # Add recommendations and price data
    collector = YahooCollector()
    prices = collector.get_all_etf_prices(db=db)

    for r in rankings:
        r["recommendation"] = get_recommendation(r["composite_score"])

        if r["symbol"] in prices:
            r["price"] = prices[r["symbol"]]["close"]
            r["change_1d"] = prices[r["symbol"]]["change_1d"]

    return rankings


@router.get("/rankings/history")
async def get_ranking_history(
    days: int = Query(default=90, le=365),
    db: Session = Depends(get_db),
):
    """
    Get historical sector rankings
    """
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Query historical scores
    scores = db.query(SectorScore).filter(
        SectorScore.date >= start_date,
        SectorScore.date <= end_date,
    ).order_by(SectorScore.date, SectorScore.rank).all()

    # Group by date
    from collections import defaultdict
    by_date = defaultdict(list)

    for s in scores:
        by_date[s.date].append({
            "symbol": s.symbol,
            "score": s.composite_score,
            "rank": s.rank,
        })

    return [
        {
            "date": d.isoformat(),
            "rankings": by_date[d],
        }
        for d in sorted(by_date.keys())
    ]


@router.get("/heatmap")
async def get_influence_heatmap(db: Session = Depends(get_db)):
    """
    Get macro variable x sector influence matrix
    """
    # Define key macro variables for display
    key_variables = [
        ("interest_rates", "Interest Rates"),
        ("yield_curve", "Yield Curve"),
        ("gdp_growth", "GDP Growth"),
        ("inflation", "Inflation"),
        ("unemployment", "Unemployment"),
        ("consumer_confidence", "Consumer Confidence"),
        ("oil_prices", "Oil Prices"),
        ("credit_spreads", "Credit Spreads"),
        ("financial_stress", "Financial Stress"),
        ("industrial_production", "Industrial Production"),
    ]

    sectors = list(SECTOR_ETFS.keys())
    sector_names = [SECTOR_ETFS[s]["name"] for s in sectors]

    # Build matrix
    matrix = []
    for var_id, var_name in key_variables:
        row = []
        for symbol in sectors:
            sensitivity = SECTOR_MACRO_SENSITIVITY.get(symbol, {}).get(var_id, 0)
            row.append(round(sensitivity, 2))
        matrix.append(row)

    return {
        "variables": [v[1] for v in key_variables],
        "variable_ids": [v[0] for v in key_variables],
        "sectors": sectors,
        "sector_names": sector_names,
        "matrix": matrix,
    }


@router.get("/{symbol}/breakdown")
async def get_score_breakdown(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed score breakdown for a sector
    """
    symbol = symbol.upper()

    if symbol not in SECTOR_ETFS:
        raise HTTPException(status_code=404, detail=f"Sector {symbol} not found")

    # Get latest score
    latest = db.query(SectorScore).filter(
        SectorScore.symbol == symbol
    ).order_by(SectorScore.date.desc()).first()

    if not latest:
        raise HTTPException(status_code=404, detail=f"No scores for {symbol}")

    # Get score history
    history = db.query(SectorScore).filter(
        SectorScore.symbol == symbol
    ).order_by(SectorScore.date.desc()).limit(90).all()

    # Get macro sensitivity
    sensitivity = SECTOR_MACRO_SENSITIVITY.get(symbol, {})

    return {
        "symbol": symbol,
        "name": SECTOR_ETFS[symbol]["name"],
        "date": latest.date.isoformat(),
        "composite_score": latest.composite_score,
        "recommendation": get_recommendation(latest.composite_score),
        "components": {
            "ml_score": {
                "value": latest.ml_score,
                "weight": 0.40,
                "description": "Machine learning predicted relative return",
            },
            "cycle_score": {
                "value": latest.cycle_score,
                "weight": 0.25,
                "description": "Historical performance in current business cycle phase",
            },
            "momentum_score": {
                "value": latest.momentum_score,
                "weight": 0.20,
                "description": "Technical momentum indicators (RSI, MA, returns)",
            },
            "macro_sensitivity_score": {
                "value": latest.macro_sensitivity_score,
                "weight": 0.15,
                "description": "Current macro conditions impact on sector",
            },
        },
        "macro_sensitivity": sensitivity,
        "trend": [
            {
                "date": h.date.isoformat(),
                "score": h.composite_score,
            }
            for h in reversed(history)
        ],
    }


@router.get("/trends")
async def get_score_trends(
    days: int = Query(default=180, le=365),
    db: Session = Depends(get_db),
):
    """
    Get time series of sector scores
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    scores = db.query(SectorScore).filter(
        SectorScore.date >= start_date,
        SectorScore.date <= end_date,
    ).order_by(SectorScore.date).all()

    # Organize by date and sector
    from collections import defaultdict
    dates = set()
    by_sector = defaultdict(dict)

    for s in scores:
        dates.add(s.date)
        by_sector[s.symbol][s.date] = s.composite_score

    sorted_dates = sorted(dates)

    return {
        "dates": [d.isoformat() for d in sorted_dates],
        "sectors": {
            symbol: {
                "name": SECTOR_ETFS[symbol]["name"],
                "scores": [
                    by_sector[symbol].get(d)
                    for d in sorted_dates
                ],
            }
            for symbol in SECTOR_ETFS.keys()
        },
    }


@router.post("/update")
async def update_scores(
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """
    Update sector scores for a specific date
    """
    scorer = SectorScorer()
    scores = scorer.update_daily_scores(target_date)

    return {
        "status": "success",
        "date": (target_date or date.today()).isoformat(),
        "scores": scores,
    }
