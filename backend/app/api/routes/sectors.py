"""
Sector Data API Routes
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sector_data import SectorData
from app.services.data_collection.yahoo_collector import YahooCollector
from app.services.data_processing.indicators import TechnicalIndicators
from app.core.constants import SECTOR_ETFS, BENCHMARK_ETF, ALL_ETFS

router = APIRouter(prefix="/api/sectors", tags=["Sector Data"])


@router.get("/")
async def get_all_sectors(db: Session = Depends(get_db)):
    """
    Get all sector ETFs with current data
    """
    collector = YahooCollector()
    prices = collector.get_all_etf_prices(db=db)

    sectors = []
    for symbol in SECTOR_ETFS.keys():
        if symbol in prices:
            data = prices[symbol]

            # Get returns
            returns = collector.calculate_returns(symbol, db=db)

            sectors.append({
                "symbol": symbol,
                "name": data["name"],
                "price": data["close"],
                "date": data["date"].isoformat(),
                "change_1d": data["change_1d"],
                "change_1w": returns.get("1w"),
                "change_1m": returns.get("1m"),
                "change_3m": returns.get("3m"),
                "change_ytd": returns.get("1y"),  # Approximate
            })

    return sectors


@router.get("/benchmark")
async def get_benchmark(db: Session = Depends(get_db)):
    """
    Get benchmark (S&P 500) data
    """
    collector = YahooCollector()
    prices = collector.get_all_etf_prices(db=db)

    if BENCHMARK_ETF not in prices:
        raise HTTPException(status_code=404, detail="Benchmark data not found")

    data = prices[BENCHMARK_ETF]
    returns = collector.calculate_returns(BENCHMARK_ETF, db=db)

    return {
        "symbol": BENCHMARK_ETF,
        "name": "S&P 500",
        "price": data["close"],
        "date": data["date"].isoformat(),
        "change_1d": data["change_1d"],
        "returns": returns,
    }


@router.get("/{symbol}")
async def get_sector(symbol: str, db: Session = Depends(get_db)):
    """
    Get single sector ETF details
    """
    symbol = symbol.upper()

    if symbol not in ALL_ETFS:
        raise HTTPException(status_code=404, detail=f"Sector {symbol} not found")

    collector = YahooCollector()

    # Get latest price
    df = collector.get_etf_data(symbol, db=db)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    # Calculate indicators
    df_with_indicators = TechnicalIndicators.calculate_all_indicators(df)
    latest = df_with_indicators.iloc[-1]

    # Get returns
    returns = collector.calculate_returns(symbol, db=db)

    name = SECTOR_ETFS.get(symbol, {}).get("name", symbol)

    return {
        "symbol": symbol,
        "name": name,
        "price": latest["close"],
        "adj_close": latest["adj_close"],
        "volume": latest["volume"],
        "date": df["date"].iloc[-1].isoformat(),
        "returns": returns,
        "technicals": {
            "rsi_14": round(latest["rsi_14"], 2) if "rsi_14" in latest else None,
            "sma_20": round(latest["sma_20"], 2) if "sma_20" in latest else None,
            "sma_50": round(latest["sma_50"], 2) if "sma_50" in latest else None,
            "sma_200": round(latest["sma_200"], 2) if "sma_200" in latest else None,
            "macd": round(latest["macd"], 4) if "macd" in latest else None,
            "macd_signal": round(latest["macd_signal"], 4) if "macd_signal" in latest else None,
            "trend": int(latest["trend"]) if "trend" in latest else None,
        },
    }


@router.get("/{symbol}/history")
async def get_sector_history(
    symbol: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=252, le=2520),
    db: Session = Depends(get_db),
):
    """
    Get historical price data for sector ETF
    """
    symbol = symbol.upper()

    if symbol not in ALL_ETFS:
        raise HTTPException(status_code=404, detail=f"Sector {symbol} not found")

    collector = YahooCollector()
    df = collector.get_etf_data(symbol, start_date=start_date, end_date=end_date, db=db)

    if df.empty:
        return []

    # Apply limit
    df = df.tail(limit)

    return [
        {
            "date": row["date"].isoformat(),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "adj_close": row["adj_close"],
            "volume": row["volume"],
        }
        for _, row in df.iterrows()
    ]


@router.get("/{symbol}/relative-performance")
async def get_relative_performance(
    symbol: str,
    db: Session = Depends(get_db),
):
    """
    Get sector performance relative to S&P 500
    """
    symbol = symbol.upper()

    if symbol not in SECTOR_ETFS:
        raise HTTPException(status_code=404, detail=f"Sector {symbol} not found")

    collector = YahooCollector()

    # Get sector and benchmark data
    sector_df = collector.get_etf_data(symbol, db=db)
    benchmark_df = collector.get_etf_data(BENCHMARK_ETF, db=db)

    if sector_df.empty or benchmark_df.empty:
        raise HTTPException(status_code=404, detail="Insufficient data")

    # Calculate relative returns
    sector_returns = collector.calculate_returns(symbol, db=db)
    benchmark_returns = collector.calculate_returns(BENCHMARK_ETF, db=db)

    relative = {}
    for period in ["1w", "1m", "3m", "6m", "1y"]:
        if period in sector_returns and period in benchmark_returns:
            relative[period] = round(
                sector_returns[period] - benchmark_returns[period], 2
            )

    # Calculate rolling relative performance
    sector_df = sector_df.set_index("date")
    benchmark_df = benchmark_df.set_index("date")

    merged = sector_df[["adj_close"]].join(
        benchmark_df[["adj_close"]],
        rsuffix="_bench",
    ).dropna()

    if len(merged) > 20:
        # 20-day rolling relative return
        sector_ret = merged["adj_close"].pct_change(20)
        bench_ret = merged["adj_close_bench"].pct_change(20)
        relative_series = (sector_ret - bench_ret) * 100

        history = [
            {
                "date": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                "relative_return": round(val, 2),
            }
            for idx, val in relative_series.dropna().tail(252).items()
        ]
    else:
        history = []

    return {
        "symbol": symbol,
        "name": SECTOR_ETFS[symbol]["name"],
        "relative_returns": relative,
        "history": history,
    }


@router.post("/refresh")
async def refresh_sector_data(
    start_date: Optional[str] = "2004-01-01",
    db: Session = Depends(get_db),
):
    """
    Refresh sector ETF data from Yahoo Finance
    """
    collector = YahooCollector()
    results = collector.update_all_etfs(start_date=start_date)

    return {
        "status": "success",
        "updated_etfs": results,
        "total_records": sum(results.values()),
    }
