"""
Sector Scorer Module
Combines ML predictions with business cycle and macro sensitivity scores
"""
import numpy as np
import pandas as pd
from datetime import date, datetime
from typing import Optional, Dict, List, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.models.scores import SectorScore, BusinessCycle
from app.services.ml.model import SectorRotationModel
from app.services.data_processing.feature_processor import FeatureProcessor
from app.services.data_processing.indicators import TechnicalIndicators
from app.services.data_collection.yahoo_collector import YahooCollector
from app.services.data_collection.fred_collector import FREDCollector
from app.core.constants import (
    SECTOR_ETFS,
    PHASE_SECTOR_SCORES,
    SECTOR_MACRO_SENSITIVITY,
    SCORE_WEIGHTS,
    BUSINESS_CYCLE_PHASES,
)

logger = logging.getLogger(__name__)


class BusinessCycleDetector:
    """
    Detect current business cycle phase based on macro indicators

    Phases:
    - early_cycle: Recovery from recession
    - mid_cycle: Expansion, growth momentum
    - late_cycle: Overheating, inflation rising
    - recession: Contraction
    """

    def __init__(self):
        self.fred_collector = FREDCollector()

    def detect_phase(
        self,
        db: Optional[Session] = None,
    ) -> Tuple[str, float]:
        """
        Detect current business cycle phase

        Returns:
            Tuple of (phase_name, confidence_score)
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            indicators = {}

            # Get key indicators
            key_series = {
                "yield_curve": "T10Y2Y",
                "unemployment": "UNRATE",
                "leading_index": "USSLIND",
                "industrial_production": "INDPRO",
                "credit_spread": "BAA10Y",
                "consumer_sentiment": "UMCSENT",
            }

            for name, series_id in key_series.items():
                data = self.fred_collector.get_series_data(series_id, db=db)
                if not data.empty:
                    indicators[name] = data

            # Score each phase
            phase_scores = {phase: 0 for phase in BUSINESS_CYCLE_PHASES}

            # Yield Curve analysis
            if "yield_curve" in indicators and len(indicators["yield_curve"]) > 0:
                yc_value = indicators["yield_curve"]["value"].iloc[-1]
                yc_trend = self._calculate_trend(indicators["yield_curve"]["value"])

                if yc_value < 0:  # Inverted
                    phase_scores["recession"] += 2
                    phase_scores["late_cycle"] += 1
                elif yc_value < 0.5:  # Flat
                    phase_scores["late_cycle"] += 2
                elif yc_value > 1.5:  # Steep
                    phase_scores["early_cycle"] += 2
                else:  # Normal
                    phase_scores["mid_cycle"] += 1.5

            # Unemployment analysis
            if "unemployment" in indicators and len(indicators["unemployment"]) > 0:
                unemp_value = indicators["unemployment"]["value"].iloc[-1]
                unemp_trend = self._calculate_trend(indicators["unemployment"]["value"])

                if unemp_trend == "rising":
                    phase_scores["recession"] += 2
                    phase_scores["late_cycle"] += 1
                elif unemp_trend == "falling":
                    phase_scores["early_cycle"] += 2
                    phase_scores["mid_cycle"] += 1
                else:  # Stable
                    phase_scores["mid_cycle"] += 1.5

            # Leading Index analysis
            if "leading_index" in indicators and len(indicators["leading_index"]) > 0:
                lead_trend = self._calculate_trend(indicators["leading_index"]["value"])

                if lead_trend == "rising":
                    phase_scores["early_cycle"] += 1.5
                    phase_scores["mid_cycle"] += 1
                elif lead_trend == "falling":
                    phase_scores["late_cycle"] += 1
                    phase_scores["recession"] += 1.5

            # Industrial Production analysis
            if "industrial_production" in indicators and len(indicators["industrial_production"]) > 0:
                ip_trend = self._calculate_trend(indicators["industrial_production"]["value"])

                if ip_trend == "rising":
                    phase_scores["mid_cycle"] += 1.5
                    phase_scores["early_cycle"] += 1
                elif ip_trend == "falling":
                    phase_scores["recession"] += 1.5
                    phase_scores["late_cycle"] += 1

            # Credit Spread analysis
            if "credit_spread" in indicators and len(indicators["credit_spread"]) > 0:
                spread_value = indicators["credit_spread"]["value"].iloc[-1]
                spread_trend = self._calculate_trend(indicators["credit_spread"]["value"])

                if spread_value > 3:  # High spreads
                    phase_scores["recession"] += 2
                elif spread_value > 2:
                    phase_scores["late_cycle"] += 1.5
                elif spread_value < 1.5:  # Low spreads
                    phase_scores["mid_cycle"] += 1.5

            # Determine phase with highest score
            max_score = max(phase_scores.values())
            detected_phase = max(phase_scores.items(), key=lambda x: x[1])[0]

            # Calculate confidence
            total_score = sum(phase_scores.values())
            confidence = max_score / total_score if total_score > 0 else 0.25

            logger.info(f"Detected phase: {detected_phase} (confidence: {confidence:.2%})")
            logger.debug(f"Phase scores: {phase_scores}")

            return detected_phase, confidence

        finally:
            if close_session:
                db.close()

    def _calculate_trend(self, series: pd.Series, periods: int = 3) -> str:
        """Calculate trend direction from series"""
        if len(series) < periods + 1:
            return "stable"

        recent = series.iloc[-periods:]
        slope = np.polyfit(range(len(recent)), recent, 1)[0]

        threshold = series.std() * 0.05
        if slope > threshold:
            return "rising"
        elif slope < -threshold:
            return "falling"
        else:
            return "stable"

    def save_phase(
        self,
        phase: str,
        confidence: float,
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ):
        """Save detected phase to database"""
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        if target_date is None:
            target_date = date.today()

        try:
            stmt = text("""
                INSERT OR REPLACE INTO business_cycle (date, phase, confidence, created_at)
                VALUES (:date, :phase, :confidence, CURRENT_TIMESTAMP)
            """)
            db.execute(stmt, {
                "date": target_date,
                "phase": phase,
                "confidence": confidence,
            })
            db.commit()

        finally:
            if close_session:
                db.close()


class SectorScorer:
    """
    Calculate composite scores for sectors

    Combines:
    - ML Model predictions (40%)
    - Business Cycle scores (25%)
    - Momentum scores (20%)
    - Macro Sensitivity scores (15%)
    """

    def __init__(self, model_path: Optional[str] = None):
        self.feature_processor = FeatureProcessor()
        self.cycle_detector = BusinessCycleDetector()
        self.yahoo_collector = YahooCollector()

        self.ml_model = SectorRotationModel()
        if model_path:
            try:
                self.ml_model.load(model_path)
            except FileNotFoundError:
                logger.warning("ML model not found. ML scores will be 0.")

    def calculate_ml_scores(
        self,
        macro_features: Dict[str, float],
        sector_features: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        """
        Calculate ML-based predicted scores

        Returns:
            Dict mapping sector symbol to ML score (0-100)
        """
        if not self.ml_model.is_trained:
            return {symbol: 50.0 for symbol in SECTOR_ETFS.keys()}

        try:
            raw_scores = self.ml_model.predict_sector_scores(
                macro_features, sector_features
            )

            # Normalize to 0-100 scale
            values = list(raw_scores.values())
            min_val, max_val = min(values), max(values)
            range_val = max_val - min_val if max_val != min_val else 1

            normalized = {
                symbol: ((score - min_val) / range_val * 80 + 10)  # 10-90 range
                for symbol, score in raw_scores.items()
            }

            return normalized

        except Exception as e:
            logger.error(f"Error calculating ML scores: {str(e)}")
            return {symbol: 50.0 for symbol in SECTOR_ETFS.keys()}

    def calculate_cycle_scores(
        self,
        phase: str,
    ) -> Dict[str, float]:
        """
        Calculate business cycle based scores

        Args:
            phase: Current business cycle phase

        Returns:
            Dict mapping sector symbol to cycle score (0-100)
        """
        if phase not in PHASE_SECTOR_SCORES:
            phase = "mid_cycle"  # Default

        phase_scores = PHASE_SECTOR_SCORES[phase]

        return {
            symbol: phase_scores.get(symbol, 0.5) * 100
            for symbol in SECTOR_ETFS.keys()
        }

    def calculate_momentum_scores(
        self,
        db: Optional[Session] = None,
    ) -> Dict[str, float]:
        """
        Calculate momentum-based scores

        Returns:
            Dict mapping sector symbol to momentum score (0-100)
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            scores = {}

            for symbol in SECTOR_ETFS.keys():
                df = self.yahoo_collector.get_etf_data(symbol, db=db)

                if df.empty or len(df) < 50:
                    scores[symbol] = 50.0
                    continue

                # Calculate momentum indicators
                price = df["adj_close"]

                # RSI
                rsi = TechnicalIndicators.rsi(price).iloc[-1]

                # Price vs 50-day MA
                sma_50 = TechnicalIndicators.sma(price, 50).iloc[-1]
                price_vs_ma = (price.iloc[-1] / sma_50 - 1) * 100 if sma_50 else 0

                # 3-month return
                if len(price) > 63:
                    return_3m = (price.iloc[-1] / price.iloc[-63] - 1) * 100
                else:
                    return_3m = 0

                # Combine into score
                # RSI: 30-70 is neutral, outside is overbought/oversold
                rsi_score = 50 + (rsi - 50) * 0.5  # Dampen RSI impact

                # Price vs MA: Positive is bullish
                ma_score = 50 + min(max(price_vs_ma * 5, -30), 30)

                # Return momentum
                return_score = 50 + min(max(return_3m * 2, -40), 40)

                # Weighted average
                momentum_score = (
                    rsi_score * 0.3 +
                    ma_score * 0.35 +
                    return_score * 0.35
                )

                scores[symbol] = min(max(momentum_score, 0), 100)

            return scores

        finally:
            if close_session:
                db.close()

    def calculate_macro_sensitivity_scores(
        self,
        macro_features: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Calculate macro sensitivity based scores

        Returns:
            Dict mapping sector symbol to macro sensitivity score (0-100)
        """
        scores = {}

        # Map macro features to sensitivity categories
        macro_conditions = {}

        # Interest rates
        if "DGS10_value" in macro_features:
            rate_percentile = macro_features.get("DGS10_percentile", 50)
            macro_conditions["interest_rates"] = (rate_percentile - 50) / 50  # -1 to 1

        # GDP growth proxy (use leading index or industrial production)
        if "USSLIND_roc_3m" in macro_features:
            lead_change = macro_features.get("USSLIND_roc_3m", 0) or 0
            macro_conditions["gdp_growth"] = min(max(lead_change / 2, -1), 1)

        # Yield curve
        if "T10Y2Y_value" in macro_features:
            yc_value = macro_features.get("T10Y2Y_value", 1) or 1
            macro_conditions["yield_curve"] = min(max(yc_value / 2, -1), 1)

        # Credit spreads
        if "BAA10Y_value" in macro_features:
            spread = macro_features.get("BAA10Y_value", 2) or 2
            macro_conditions["credit_spreads"] = max(min((2 - spread) / 2, 1), -1)

        # Consumer confidence
        if "UMCSENT_percentile" in macro_features:
            sent_percentile = macro_features.get("UMCSENT_percentile", 50) or 50
            macro_conditions["consumer_confidence"] = (sent_percentile - 50) / 50

        # Oil prices
        if "DCOILWTICO_roc_3m" in macro_features:
            oil_change = macro_features.get("DCOILWTICO_roc_3m", 0) or 0
            macro_conditions["oil_prices"] = min(max(oil_change / 20, -1), 1)

        # Financial stress
        if "STLFSI4_value" in macro_features:
            stress = macro_features.get("STLFSI4_value", 0) or 0
            macro_conditions["financial_stress"] = -min(max(stress, -2), 2) / 2  # Invert

        # Industrial production
        if "INDPRO_roc_3m" in macro_features:
            ip_change = macro_features.get("INDPRO_roc_3m", 0) or 0
            macro_conditions["industrial_production"] = min(max(ip_change / 3, -1), 1)

        # Calculate score for each sector
        for symbol, sensitivities in SECTOR_MACRO_SENSITIVITY.items():
            score = 50  # Base score

            for factor, sensitivity in sensitivities.items():
                if factor in macro_conditions:
                    # Positive sensitivity + positive condition = positive impact
                    impact = sensitivity * macro_conditions[factor] * 25
                    score += impact

            scores[symbol] = min(max(score, 0), 100)

        return scores

    def calculate_composite_scores(
        self,
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate composite scores for all sectors

        Returns:
            Dict mapping sector symbol to score breakdown
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Get features
            macro_features, sector_features = self.feature_processor.get_all_features_for_date(
                target_date, db
            )

            # Detect business cycle
            phase, confidence = self.cycle_detector.detect_phase(db)

            # Calculate component scores
            ml_scores = self.calculate_ml_scores(macro_features, sector_features)
            cycle_scores = self.calculate_cycle_scores(phase)
            momentum_scores = self.calculate_momentum_scores(db)
            macro_sens_scores = self.calculate_macro_sensitivity_scores(macro_features)

            # Combine scores
            results = {}

            for symbol in SECTOR_ETFS.keys():
                ml = ml_scores.get(symbol, 50)
                cycle = cycle_scores.get(symbol, 50)
                momentum = momentum_scores.get(symbol, 50)
                macro_sens = macro_sens_scores.get(symbol, 50)

                composite = (
                    SCORE_WEIGHTS["ml_score"] * ml +
                    SCORE_WEIGHTS["cycle_score"] * cycle +
                    SCORE_WEIGHTS["momentum_score"] * momentum +
                    SCORE_WEIGHTS["macro_sensitivity_score"] * macro_sens
                )

                results[symbol] = {
                    "composite_score": round(composite, 2),
                    "ml_score": round(ml, 2),
                    "cycle_score": round(cycle, 2),
                    "momentum_score": round(momentum, 2),
                    "macro_sensitivity_score": round(macro_sens, 2),
                }

            # Add ranks
            sorted_sectors = sorted(
                results.items(),
                key=lambda x: x[1]["composite_score"],
                reverse=True,
            )

            for rank, (symbol, _) in enumerate(sorted_sectors, 1):
                results[symbol]["rank"] = rank

            return results

        finally:
            if close_session:
                db.close()

    def save_scores(
        self,
        scores: Dict[str, Dict[str, float]],
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ):
        """Save calculated scores to database"""
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        if target_date is None:
            target_date = date.today()

        try:
            for symbol, score_data in scores.items():
                stmt = text("""
                    INSERT OR REPLACE INTO sector_scores
                    (date, symbol, composite_score, ml_score, cycle_score,
                     momentum_score, macro_sensitivity_score, rank, created_at)
                    VALUES (:date, :symbol, :composite_score, :ml_score, :cycle_score,
                            :momentum_score, :macro_sensitivity_score, :rank, CURRENT_TIMESTAMP)
                """)
                db.execute(stmt, {
                    "date": target_date,
                    "symbol": symbol,
                    "composite_score": score_data["composite_score"],
                    "ml_score": score_data["ml_score"],
                    "cycle_score": score_data["cycle_score"],
                    "momentum_score": score_data["momentum_score"],
                    "macro_sensitivity_score": score_data["macro_sensitivity_score"],
                    "rank": score_data["rank"],
                })

            db.commit()
            logger.info(f"Saved scores for {len(scores)} sectors on {target_date}")

        finally:
            if close_session:
                db.close()

    def update_daily_scores(self, target_date: Optional[date] = None):
        """
        Update scores for a specific date (or today)

        Args:
            target_date: Date to update scores for
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Updating scores for {target_date}...")

        db = SessionLocal()

        try:
            # Detect and save business cycle
            phase, confidence = self.cycle_detector.detect_phase(db)
            self.cycle_detector.save_phase(phase, confidence, target_date, db)

            # Calculate and save scores
            scores = self.calculate_composite_scores(target_date, db)
            self.save_scores(scores, target_date, db)

            logger.info(f"Score update complete for {target_date}")

            return scores

        finally:
            db.close()

    def get_current_rankings(
        self,
        db: Optional[Session] = None,
    ) -> List[Dict]:
        """
        Get current sector rankings

        Returns:
            List of sector rankings with all score components
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Get latest scores
            latest_date = db.query(SectorScore.date).order_by(
                SectorScore.date.desc()
            ).first()

            if not latest_date:
                return []

            scores = db.query(SectorScore).filter(
                SectorScore.date == latest_date[0]
            ).order_by(SectorScore.rank).all()

            return [
                {
                    "rank": s.rank,
                    "symbol": s.symbol,
                    "name": SECTOR_ETFS.get(s.symbol, {}).get("name", s.symbol),
                    "composite_score": s.composite_score,
                    "ml_score": s.ml_score,
                    "cycle_score": s.cycle_score,
                    "momentum_score": s.momentum_score,
                    "macro_sensitivity_score": s.macro_sensitivity_score,
                    "date": s.date,
                }
                for s in scores
            ]

        finally:
            if close_session:
                db.close()
