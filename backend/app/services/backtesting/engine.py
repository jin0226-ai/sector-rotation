"""
Backtesting Engine
Walk-forward backtesting for sector rotation strategy
"""
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.sector_data import SectorData
from app.models.scores import SectorScore
from app.services.data_collection.yahoo_collector import YahooCollector
from app.services.ml.scorer import SectorScorer
from app.core.constants import SECTOR_ETFS, BENCHMARK_ETF

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    start_date: str = "2005-01-01"
    end_date: Optional[str] = None
    initial_capital: float = 100000
    rebalance_frequency: str = "monthly"  # daily, weekly, monthly
    top_n_sectors: int = 3
    benchmark: str = "SPY"


class BacktestEngine:
    """
    Walk-forward backtesting engine for sector rotation strategy
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.yahoo_collector = YahooCollector()

    def _get_rebalance_dates(
        self,
        start_date: date,
        end_date: date,
        frequency: str,
    ) -> List[date]:
        """Get list of rebalance dates"""
        dates = []
        current = start_date

        if frequency == "daily":
            delta = timedelta(days=1)
        elif frequency == "weekly":
            delta = timedelta(days=7)
        elif frequency == "monthly":
            delta = timedelta(days=30)
        else:
            delta = timedelta(days=30)

        while current <= end_date:
            dates.append(current)
            current += delta

        return dates

    def _get_sector_prices(
        self,
        target_date: date,
        db: Session,
    ) -> Dict[str, float]:
        """Get sector prices for a specific date"""
        prices = {}

        for symbol in list(SECTOR_ETFS.keys()) + [self.config.benchmark]:
            # Get price on or before target date
            result = db.query(SectorData).filter(
                SectorData.symbol == symbol,
                SectorData.date <= target_date,
            ).order_by(SectorData.date.desc()).first()

            if result:
                prices[symbol] = result.adj_close

        return prices

    def _get_sector_scores(
        self,
        target_date: date,
        db: Session,
    ) -> Dict[str, float]:
        """Get sector scores for a specific date"""
        scores = {}

        # First try to get from database
        db_scores = db.query(SectorScore).filter(
            SectorScore.date <= target_date,
        ).order_by(SectorScore.date.desc()).limit(len(SECTOR_ETFS)).all()

        if db_scores:
            # Get the latest date's scores
            latest_date = db_scores[0].date
            for s in db_scores:
                if s.date == latest_date:
                    scores[s.symbol] = s.composite_score

        if not scores:
            # Calculate scores if not in database
            scorer = SectorScorer()
            calculated = scorer.calculate_composite_scores(target_date, db)
            scores = {
                symbol: data["composite_score"]
                for symbol, data in calculated.items()
            }

        return scores

    def run(self, db: Optional[Session] = None) -> Dict:
        """
        Run backtest

        Returns:
            Dict with performance metrics and equity curve
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            start = datetime.strptime(self.config.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(self.config.end_date, "%Y-%m-%d").date() if self.config.end_date else date.today()

            # Get rebalance dates
            rebalance_dates = self._get_rebalance_dates(
                start, end, self.config.rebalance_frequency
            )

            logger.info(f"Running backtest from {start} to {end}")
            logger.info(f"Rebalance dates: {len(rebalance_dates)}")

            # Initialize portfolio
            portfolio_value = self.config.initial_capital
            benchmark_value = self.config.initial_capital

            equity_curve = []
            monthly_returns = []
            allocations_history = []
            all_trades = []

            prev_portfolio_value = portfolio_value
            prev_benchmark_value = benchmark_value
            prev_month = None

            # Get initial benchmark price
            initial_prices = self._get_sector_prices(start, db)
            if self.config.benchmark not in initial_prices:
                raise ValueError(f"No data for benchmark {self.config.benchmark}")

            initial_benchmark_price = initial_prices[self.config.benchmark]

            for i, rebal_date in enumerate(rebalance_dates[:-1]):
                next_date = rebalance_dates[i + 1]

                # Get prices
                prices_start = self._get_sector_prices(rebal_date, db)
                prices_end = self._get_sector_prices(next_date, db)

                if not prices_start or not prices_end:
                    continue

                # Get scores and select top sectors
                scores = self._get_sector_scores(rebal_date, db)

                if not scores:
                    continue

                # Select top N sectors
                sorted_sectors = sorted(
                    scores.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:self.config.top_n_sectors]

                selected = [s[0] for s in sorted_sectors]

                # Equal weight allocation
                weight = 1.0 / len(selected)
                allocations = {s: weight for s in selected}

                # Calculate portfolio return
                portfolio_return = 0
                for symbol, w in allocations.items():
                    if symbol in prices_start and symbol in prices_end:
                        ret = (prices_end[symbol] / prices_start[symbol] - 1)
                        portfolio_return += w * ret

                # Calculate benchmark return
                if self.config.benchmark in prices_start and self.config.benchmark in prices_end:
                    benchmark_return = (
                        prices_end[self.config.benchmark] /
                        prices_start[self.config.benchmark] - 1
                    )
                else:
                    benchmark_return = 0

                # Update values
                portfolio_value *= (1 + portfolio_return)
                benchmark_value *= (1 + benchmark_return)

                # Record equity curve
                equity_curve.append({
                    "date": next_date.isoformat(),
                    "portfolio_value": round(portfolio_value, 2),
                    "benchmark_value": round(benchmark_value, 2),
                    "portfolio_return": round(portfolio_return * 100, 2),
                    "benchmark_return": round(benchmark_return * 100, 2),
                })

                # Record allocations
                allocations_history.append({
                    "date": rebal_date.isoformat(),
                    "allocations": allocations,
                    "scores": {s: scores.get(s) for s in selected},
                })

                # Monthly returns
                current_month = next_date.strftime("%Y-%m")
                if prev_month and current_month != prev_month:
                    monthly_portfolio_return = (portfolio_value / prev_portfolio_value - 1) * 100
                    monthly_benchmark_return = (benchmark_value / prev_benchmark_value - 1) * 100

                    monthly_returns.append({
                        "month": prev_month,
                        "portfolio_return": round(monthly_portfolio_return, 2),
                        "benchmark_return": round(monthly_benchmark_return, 2),
                        "excess_return": round(monthly_portfolio_return - monthly_benchmark_return, 2),
                    })

                    prev_portfolio_value = portfolio_value
                    prev_benchmark_value = benchmark_value

                prev_month = current_month

            # Calculate performance metrics
            metrics = self._calculate_metrics(
                equity_curve,
                self.config.initial_capital,
            )

            return {
                "config": {
                    "start_date": self.config.start_date,
                    "end_date": self.config.end_date or date.today().isoformat(),
                    "initial_capital": self.config.initial_capital,
                    "rebalance_frequency": self.config.rebalance_frequency,
                    "top_n_sectors": self.config.top_n_sectors,
                },
                "performance": metrics,
                "equity_curve": equity_curve,
                "monthly_returns": monthly_returns,
                "allocations_history": allocations_history[-20:],  # Last 20 rebalances
            }

        finally:
            if close_session:
                db.close()

    def _calculate_metrics(
        self,
        equity_curve: List[Dict],
        initial_capital: float,
    ) -> Dict:
        """Calculate performance metrics"""
        if not equity_curve:
            return {}

        # Convert to arrays
        portfolio_values = [initial_capital] + [e["portfolio_value"] for e in equity_curve]
        benchmark_values = [initial_capital] + [e["benchmark_value"] for e in equity_curve]

        portfolio_returns = np.diff(portfolio_values) / portfolio_values[:-1]
        benchmark_returns = np.diff(benchmark_values) / benchmark_values[:-1]

        # Total Return
        total_return = (portfolio_values[-1] / initial_capital - 1) * 100
        benchmark_total_return = (benchmark_values[-1] / initial_capital - 1) * 100

        # Annualized Return (approximate)
        years = len(equity_curve) / 252 if len(equity_curve) > 0 else 1
        annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
        benchmark_annualized = ((1 + benchmark_total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Volatility
        volatility = np.std(portfolio_returns) * np.sqrt(252) * 100 if len(portfolio_returns) > 0 else 0
        benchmark_volatility = np.std(benchmark_returns) * np.sqrt(252) * 100 if len(benchmark_returns) > 0 else 0

        # Sharpe Ratio (assuming 2% risk-free rate)
        risk_free = 0.02
        sharpe = (annualized_return / 100 - risk_free) / (volatility / 100) if volatility > 0 else 0

        # Maximum Drawdown
        cumulative = np.array(portfolio_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown) * 100

        # Win Rate (monthly)
        excess_returns = portfolio_returns - benchmark_returns
        win_rate = (excess_returns > 0).sum() / len(excess_returns) * 100 if len(excess_returns) > 0 else 0

        # Alpha and Beta
        if len(portfolio_returns) > 0 and len(benchmark_returns) > 0:
            covariance = np.cov(portfolio_returns, benchmark_returns)
            beta = covariance[0, 1] / covariance[1, 1] if covariance[1, 1] != 0 else 1
            alpha = (annualized_return - beta * benchmark_annualized)
        else:
            beta = 1
            alpha = 0

        # Information Ratio
        tracking_error = np.std(excess_returns) * np.sqrt(252) * 100 if len(excess_returns) > 0 else 0
        information_ratio = (annualized_return - benchmark_annualized) / tracking_error if tracking_error > 0 else 0

        return {
            "total_return": round(total_return, 2),
            "benchmark_return": round(benchmark_total_return, 2),
            "excess_return": round(total_return - benchmark_total_return, 2),
            "annualized_return": round(annualized_return, 2),
            "benchmark_annualized": round(benchmark_annualized, 2),
            "volatility": round(volatility, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_drawdown, 2),
            "win_rate": round(win_rate, 2),
            "alpha": round(alpha, 2),
            "beta": round(beta, 2),
            "information_ratio": round(information_ratio, 2),
            "final_portfolio_value": round(portfolio_values[-1], 2),
            "final_benchmark_value": round(benchmark_values[-1], 2),
        }

    def calculate_correlation(self, db: Optional[Session] = None) -> Dict:
        """
        Calculate correlation between predicted scores and actual returns
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Get all scores and returns
            scores_query = db.query(SectorScore).order_by(SectorScore.date).all()

            if not scores_query:
                return {"error": "No scores available"}

            # Build DataFrame
            data = []
            for score in scores_query:
                # Get forward return (21 days)
                forward_date = score.date + timedelta(days=30)

                current_price = db.query(SectorData).filter(
                    SectorData.symbol == score.symbol,
                    SectorData.date == score.date,
                ).first()

                future_price = db.query(SectorData).filter(
                    SectorData.symbol == score.symbol,
                    SectorData.date <= forward_date,
                    SectorData.date > score.date,
                ).order_by(SectorData.date.desc()).first()

                if current_price and future_price:
                    actual_return = (future_price.adj_close / current_price.adj_close - 1) * 100

                    data.append({
                        "date": score.date,
                        "symbol": score.symbol,
                        "predicted_score": score.composite_score,
                        "actual_return": actual_return,
                    })

            if not data:
                return {"error": "Insufficient data for correlation"}

            df = pd.DataFrame(data)

            # Overall correlation
            overall_corr = df["predicted_score"].corr(df["actual_return"])

            # By sector
            by_sector = {}
            for symbol in df["symbol"].unique():
                sector_df = df[df["symbol"] == symbol]
                if len(sector_df) > 10:
                    by_sector[symbol] = round(
                        sector_df["predicted_score"].corr(sector_df["actual_return"]), 3
                    )

            return {
                "overall_correlation": round(overall_corr, 3) if not np.isnan(overall_corr) else 0,
                "by_sector": by_sector,
                "sample_size": len(df),
                "scatter_data": [
                    {
                        "predicted": round(row["predicted_score"], 2),
                        "actual": round(row["actual_return"], 2),
                    }
                    for _, row in df.sample(min(100, len(df))).iterrows()
                ],
            }

        finally:
            if close_session:
                db.close()
