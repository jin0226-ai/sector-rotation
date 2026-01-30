"""
Macro Data API Routes
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.macro_data import MacroData
from app.models.scores import BusinessCycle
from app.services.data_collection.fred_collector import FREDCollector
from app.services.data_processing.normalizer import MacroDataNormalizer
from app.services.ml.scorer import BusinessCycleDetector
from app.core.constants import FRED_SERIES

router = APIRouter(prefix="/api/macro", tags=["Macro Data"])


@router.get("/variables")
async def get_macro_variables():
    """
    Get list of all tracked macro variables with metadata
    """
    return [
        {
            "id": series_id,
            "name": info["name"],
            "frequency": info["frequency"],
            "category": info["category"],
        }
        for series_id, info in FRED_SERIES.items()
    ]


@router.get("/variables/{variable_id}")
async def get_macro_variable(
    variable_id: str,
    db: Session = Depends(get_db),
):
    """
    Get single macro variable details and current status
    """
    if variable_id not in FRED_SERIES:
        raise HTTPException(status_code=404, detail=f"Variable {variable_id} not found")

    info = FRED_SERIES[variable_id]

    # Get data from database
    collector = FREDCollector()
    data = collector.get_series_data(variable_id, db=db)

    if data.empty:
        raise HTTPException(status_code=404, detail=f"No data for {variable_id}")

    # Calculate status
    normalizer = MacroDataNormalizer()
    status = normalizer.get_current_status(data["value"], variable_id)

    return {
        "id": variable_id,
        "name": info["name"],
        "category": info["category"],
        "frequency": info["frequency"],
        "current_value": status["value"],
        "percentile": status["percentile"],
        "trend": status["trend"],
        "zscore": status["zscore"],
        "roc_1m": status["roc_1m"],
        "latest_date": data["date"].iloc[-1].isoformat() if not data.empty else None,
    }


@router.get("/variables/{variable_id}/history")
async def get_macro_history(
    variable_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """
    Get historical data for a macro variable
    """
    if variable_id not in FRED_SERIES:
        raise HTTPException(status_code=404, detail=f"Variable {variable_id} not found")

    collector = FREDCollector()
    data = collector.get_series_data(
        variable_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )

    if data.empty:
        return []

    return [
        {
            "date": row["date"].isoformat(),
            "value": row["value"],
        }
        for _, row in data.iterrows()
    ]


@router.get("/dashboard")
async def get_macro_dashboard(db: Session = Depends(get_db)):
    """
    Get aggregated macro dashboard data
    """
    collector = FREDCollector()
    normalizer = MacroDataNormalizer()

    # Get all latest values
    latest_values = collector.get_all_latest_values(db=db)

    # Get business cycle
    detector = BusinessCycleDetector()
    phase, confidence = detector.detect_phase(db=db)

    variables = []
    for series_id, data in latest_values.items():
        # Get full series for status calculation
        series_data = collector.get_series_data(series_id, db=db)

        if not series_data.empty:
            status = normalizer.get_current_status(series_data["value"], series_id)

            # Determine status indicator
            if status["percentile"] >= 80:
                indicator = "high"
            elif status["percentile"] <= 20:
                indicator = "low"
            else:
                indicator = "normal"

            variables.append({
                "id": series_id,
                "name": data["name"],
                "category": data["category"],
                "value": data["value"],
                "date": data["date"].isoformat(),
                "percentile": status["percentile"],
                "trend": status["trend"],
                "zscore": status["zscore"],
                "status": indicator,
            })

    # Get last updated time
    latest_entry = db.query(MacroData.created_at).order_by(
        MacroData.created_at.desc()
    ).first()

    return {
        "variables": variables,
        "business_cycle_phase": phase,
        "phase_confidence": round(confidence, 2),
        "last_updated": latest_entry[0].isoformat() if latest_entry else None,
    }


@router.get("/business-cycle")
async def get_business_cycle(db: Session = Depends(get_db)):
    """
    Get current business cycle phase and history
    """
    detector = BusinessCycleDetector()
    phase, confidence = detector.detect_phase(db=db)

    # Get history
    history = db.query(BusinessCycle).order_by(
        BusinessCycle.date.desc()
    ).limit(365).all()

    return {
        "current_phase": phase,
        "confidence": round(confidence, 2),
        "phase_history": [
            {
                "date": h.date.isoformat(),
                "phase": h.phase,
                "confidence": h.confidence,
            }
            for h in history
        ],
    }


@router.post("/refresh")
async def refresh_macro_data(
    start_date: Optional[str] = "2004-01-01",
    db: Session = Depends(get_db),
):
    """
    Refresh macro data from FRED API
    """
    collector = FREDCollector()

    if not collector.fred:
        raise HTTPException(
            status_code=500,
            detail="FRED API not configured. Set FRED_API_KEY environment variable.",
        )

    results = collector.update_all_series(start_date=start_date)

    return {
        "status": "success",
        "updated_series": results,
        "total_records": sum(results.values()),
    }
