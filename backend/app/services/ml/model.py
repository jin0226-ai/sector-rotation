"""
Machine Learning Model for Sector Rotation
Predicts relative sector performance based on macro factors
"""
import numpy as np
import pandas as pd
from datetime import date, datetime
from typing import Optional, Dict, List, Tuple, Any
import pickle
import logging
from pathlib import Path

from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import warnings

warnings.filterwarnings("ignore")

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

from app.core.constants import SECTOR_ETFS

logger = logging.getLogger(__name__)


class SectorRotationModel:
    """
    Machine Learning model for predicting sector relative performance

    Uses an ensemble of:
    - XGBoost/Gradient Boosting (primary)
    - Ridge Regression (baseline)
    """

    def __init__(self, models_dir: Optional[Path] = None):
        """
        Initialize the sector rotation model

        Args:
            models_dir: Directory to save/load models
        """
        self.models_dir = models_dir or Path("data/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.scaler = StandardScaler()
        self.models: Dict[str, Any] = {}
        self.feature_names: List[str] = []
        self.feature_importance: Dict[str, Dict[str, float]] = {}
        self.is_trained = False

        # Model parameters
        self.ensemble_weights = {"gradient_boosting": 0.7, "ridge": 0.3}

    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get feature columns from DataFrame"""
        exclude_cols = ["date", "symbol", "sector_return", "benchmark_return", "relative_return"]
        return [c for c in df.columns if c not in exclude_cols]

    def _prepare_features(
        self,
        features_df: pd.DataFrame,
        fit_scaler: bool = False,
    ) -> np.ndarray:
        """
        Prepare features for model

        Args:
            features_df: DataFrame with features
            fit_scaler: Whether to fit the scaler

        Returns:
            Scaled feature array
        """
        feature_cols = self._get_feature_columns(features_df)
        self.feature_names = feature_cols

        X = features_df[feature_cols].copy()

        # Handle missing values
        X = X.fillna(X.median())
        X = X.replace([np.inf, -np.inf], 0)

        if fit_scaler:
            return self.scaler.fit_transform(X)
        else:
            return self.scaler.transform(X)

    def train(
        self,
        features_df: pd.DataFrame,
        targets_df: pd.DataFrame,
        validation_split: float = 0.2,
    ) -> Dict[str, float]:
        """
        Train the sector rotation model

        Args:
            features_df: DataFrame with features
            targets_df: DataFrame with target relative returns
            validation_split: Fraction of data to use for validation

        Returns:
            Dict with training metrics
        """
        logger.info("Starting model training...")

        # Merge features and targets
        df = features_df.merge(
            targets_df[["date", "symbol", "relative_return"]],
            on=["date", "symbol"],
        )

        # Sort by date for time series split
        df = df.sort_values("date")

        # Prepare features and target
        X = self._prepare_features(df, fit_scaler=True)
        y = df["relative_return"].values

        # Time series split
        split_idx = int(len(df) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        logger.info(f"Training samples: {len(X_train)}, Validation samples: {len(X_val)}")

        metrics = {}

        # Train Gradient Boosting / XGBoost
        if XGBOOST_AVAILABLE:
            logger.info("Training XGBoost model...")
            gb_model = XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                verbosity=0,
            )
        else:
            logger.info("Training Gradient Boosting model...")
            gb_model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )

        gb_model.fit(X_train, y_train)
        self.models["gradient_boosting"] = gb_model

        # Gradient Boosting metrics
        gb_train_pred = gb_model.predict(X_train)
        gb_val_pred = gb_model.predict(X_val)

        metrics["gb_train_rmse"] = np.sqrt(mean_squared_error(y_train, gb_train_pred))
        metrics["gb_val_rmse"] = np.sqrt(mean_squared_error(y_val, gb_val_pred))
        metrics["gb_val_r2"] = r2_score(y_val, gb_val_pred)

        logger.info(f"GB Train RMSE: {metrics['gb_train_rmse']:.4f}")
        logger.info(f"GB Val RMSE: {metrics['gb_val_rmse']:.4f}")
        logger.info(f"GB Val R²: {metrics['gb_val_r2']:.4f}")

        # Store feature importance
        if hasattr(gb_model, "feature_importances_"):
            importance = dict(zip(self.feature_names, gb_model.feature_importances_))
            self.feature_importance["gradient_boosting"] = dict(
                sorted(importance.items(), key=lambda x: x[1], reverse=True)[:20]
            )

        # Train Ridge Regression
        logger.info("Training Ridge Regression model...")
        ridge_model = Ridge(alpha=1.0)
        ridge_model.fit(X_train, y_train)
        self.models["ridge"] = ridge_model

        # Ridge metrics
        ridge_train_pred = ridge_model.predict(X_train)
        ridge_val_pred = ridge_model.predict(X_val)

        metrics["ridge_train_rmse"] = np.sqrt(mean_squared_error(y_train, ridge_train_pred))
        metrics["ridge_val_rmse"] = np.sqrt(mean_squared_error(y_val, ridge_val_pred))
        metrics["ridge_val_r2"] = r2_score(y_val, ridge_val_pred)

        logger.info(f"Ridge Train RMSE: {metrics['ridge_train_rmse']:.4f}")
        logger.info(f"Ridge Val RMSE: {metrics['ridge_val_rmse']:.4f}")
        logger.info(f"Ridge Val R²: {metrics['ridge_val_r2']:.4f}")

        # Ensemble validation
        ensemble_pred = (
            self.ensemble_weights["gradient_boosting"] * gb_val_pred +
            self.ensemble_weights["ridge"] * ridge_val_pred
        )

        metrics["ensemble_val_rmse"] = np.sqrt(mean_squared_error(y_val, ensemble_pred))
        metrics["ensemble_val_r2"] = r2_score(y_val, ensemble_pred)
        metrics["ensemble_val_mae"] = mean_absolute_error(y_val, ensemble_pred)

        # Calculate correlation
        correlation = np.corrcoef(y_val, ensemble_pred)[0, 1]
        metrics["ensemble_correlation"] = correlation

        logger.info(f"Ensemble Val RMSE: {metrics['ensemble_val_rmse']:.4f}")
        logger.info(f"Ensemble Val R²: {metrics['ensemble_val_r2']:.4f}")
        logger.info(f"Ensemble Correlation: {metrics['ensemble_correlation']:.4f}")

        self.is_trained = True
        return metrics

    def predict(
        self,
        features_df: pd.DataFrame,
    ) -> np.ndarray:
        """
        Predict relative returns for sectors

        Args:
            features_df: DataFrame with features

        Returns:
            Array of predicted relative returns
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        X = self._prepare_features(features_df, fit_scaler=False)

        # Get predictions from each model
        predictions = {}
        for name, model in self.models.items():
            predictions[name] = model.predict(X)

        # Ensemble prediction
        ensemble_pred = np.zeros(len(X))
        for name, weight in self.ensemble_weights.items():
            if name in predictions:
                ensemble_pred += weight * predictions[name]

        return ensemble_pred

    def predict_sector_scores(
        self,
        features_dict: Dict[str, float],
        sector_features: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        """
        Predict scores for all sectors given features

        Args:
            features_dict: Common macro features
            sector_features: Sector-specific features by symbol

        Returns:
            Dict mapping sector symbol to predicted score
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        scores = {}

        for symbol in SECTOR_ETFS.keys():
            # Combine features
            combined_features = {**features_dict, **sector_features.get(symbol, {})}

            # Create single-row DataFrame
            row_df = pd.DataFrame([combined_features])

            # Ensure all expected columns exist
            for col in self.feature_names:
                if col not in row_df.columns:
                    row_df[col] = 0

            # Select only expected columns in correct order
            row_df = row_df[self.feature_names]

            try:
                X = self.scaler.transform(row_df.fillna(0).replace([np.inf, -np.inf], 0))

                # Ensemble prediction
                pred = 0
                for name, model in self.models.items():
                    weight = self.ensemble_weights.get(name, 0)
                    pred += weight * model.predict(X)[0]

                scores[symbol] = float(pred)

            except Exception as e:
                logger.warning(f"Error predicting for {symbol}: {str(e)}")
                scores[symbol] = 0.0

        return scores

    def save(self, filename: str = "sector_model"):
        """
        Save model to file

        Args:
            filename: Base filename for model files
        """
        filepath = self.models_dir / f"{filename}.pkl"

        model_data = {
            "models": self.models,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "feature_importance": self.feature_importance,
            "ensemble_weights": self.ensemble_weights,
            "is_trained": self.is_trained,
            "saved_at": datetime.now().isoformat(),
        }

        with open(filepath, "wb") as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {filepath}")

    def load(self, filename: str = "sector_model"):
        """
        Load model from file

        Args:
            filename: Base filename for model files
        """
        filepath = self.models_dir / f"{filename}.pkl"

        if not filepath.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")

        with open(filepath, "rb") as f:
            model_data = pickle.load(f)

        self.models = model_data["models"]
        self.scaler = model_data["scaler"]
        self.feature_names = model_data["feature_names"]
        self.feature_importance = model_data.get("feature_importance", {})
        self.ensemble_weights = model_data.get("ensemble_weights", self.ensemble_weights)
        self.is_trained = model_data["is_trained"]

        logger.info(f"Model loaded from {filepath}")

    def get_feature_importance(self, top_n: int = 20) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get feature importance from trained models

        Args:
            top_n: Number of top features to return

        Returns:
            Dict mapping model name to list of (feature, importance) tuples
        """
        result = {}

        for model_name, model in self.models.items():
            if hasattr(model, "feature_importances_"):
                importance = list(zip(self.feature_names, model.feature_importances_))
                importance.sort(key=lambda x: x[1], reverse=True)
                result[model_name] = importance[:top_n]
            elif hasattr(model, "coef_"):
                importance = list(zip(self.feature_names, np.abs(model.coef_)))
                importance.sort(key=lambda x: x[1], reverse=True)
                result[model_name] = importance[:top_n]

        return result


# Training script function
def train_model_from_data(
    features_path: str,
    targets_path: str,
    output_dir: str = "data/models",
) -> Dict[str, float]:
    """
    Train model from saved CSV files

    Args:
        features_path: Path to features CSV
        targets_path: Path to targets CSV
        output_dir: Directory to save model

    Returns:
        Training metrics
    """
    features_df = pd.read_csv(features_path)
    targets_df = pd.read_csv(targets_path)

    model = SectorRotationModel(models_dir=Path(output_dir))
    metrics = model.train(features_df, targets_df)
    model.save()

    return metrics
