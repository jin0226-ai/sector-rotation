"""
Backtesting API Routes
"""
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models.backtest_results import BacktestResult
from app.services.backtesting.engine import BacktestEngine, BacktestConfig

router = APIRouter(prefix="/api/backtest", tags=["Backtesting"])


class BacktestRequest(BaseModel):
    """Backtest configuration request"""
    start_date: str = "2005-01-01"
    end_date: Optional[str] = None
    initial_capital: float = 100000
    rebalance_frequency: str = "monthly"  # daily, weekly, monthly
    top_n_sectors: int = 3
    benchmark: str = "SPY"


@router.post("/run")
async def run_backtest(
    config: BacktestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Run backtest with specified configuration
    """
    backtest_id = str(uuid.uuid4())[:8]

    try:
        # Create config object
        bt_config = BacktestConfig(
            start_date=config.start_date,
            end_date=config.end_date,
            initial_capital=config.initial_capital,
            rebalance_frequency=config.rebalance_frequency,
            top_n_sectors=config.top_n_sectors,
            benchmark=config.benchmark,
        )

        # Run backtest
        engine = BacktestEngine(bt_config)
        results = engine.run(db=db)

        # Save results
        bt_result = BacktestResult(
            backtest_id=backtest_id,
            config=config.model_dump(),
            results=results,
        )
        db.add(bt_result)
        db.commit()

        return {
            "backtest_id": backtest_id,
            "status": "completed",
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{backtest_id}")
async def get_backtest_results(
    backtest_id: str,
    db: Session = Depends(get_db),
):
    """
    Get backtest results
    """
    result = db.query(BacktestResult).filter(
        BacktestResult.backtest_id == backtest_id
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")

    return {
        "backtest_id": result.backtest_id,
        "config": result.config,
        "results": result.results,
        "created_at": result.created_at.isoformat(),
    }


@router.get("/correlation")
async def get_score_correlation(db: Session = Depends(get_db)):
    """
    Get correlation between predicted scores and actual returns
    """
    engine = BacktestEngine(BacktestConfig())
    correlation = engine.calculate_correlation(db=db)

    return correlation


@router.get("/default")
async def get_default_backtest(db: Session = Depends(get_db)):
    """
    Get pre-computed default 20-year backtest results
    """
    # Try to get cached default backtest
    result = db.query(BacktestResult).filter(
        BacktestResult.backtest_id == "default"
    ).first()

    if result:
        return {
            "backtest_id": "default",
            "config": result.config,
            "results": result.results,
            "created_at": result.created_at.isoformat(),
        }

    # Run default backtest if not cached
    config = BacktestConfig(
        start_date="2005-01-01",
        initial_capital=100000,
        rebalance_frequency="monthly",
        top_n_sectors=3,
    )

    engine = BacktestEngine(config)
    results = engine.run(db=db)

    # Cache results
    bt_result = BacktestResult(
        backtest_id="default",
        config={
            "start_date": config.start_date,
            "initial_capital": config.initial_capital,
            "rebalance_frequency": config.rebalance_frequency,
            "top_n_sectors": config.top_n_sectors,
        },
        results=results,
    )
    db.add(bt_result)
    db.commit()

    return {
        "backtest_id": "default",
        "config": config.__dict__,
        "results": results,
    }


@router.get("/history")
async def get_backtest_history(
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
):
    """
    Get list of past backtests
    """
    backtests = db.query(BacktestResult).order_by(
        BacktestResult.created_at.desc()
    ).limit(limit).all()

    return [
        {
            "backtest_id": bt.backtest_id,
            "config": bt.config,
            "total_return": bt.results.get("performance", {}).get("total_return"),
            "sharpe_ratio": bt.results.get("performance", {}).get("sharpe_ratio"),
            "created_at": bt.created_at.isoformat(),
        }
        for bt in backtests
    ]
