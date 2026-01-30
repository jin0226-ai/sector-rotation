"""
SQLAlchemy models for backtest results and model metadata
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base


class BacktestResult(Base):
    """Store backtest results"""

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(String(50), unique=True, nullable=False, index=True)
    config = Column(JSON, nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<BacktestResult(id={self.backtest_id})>"


class ModelMetadata(Base):
    """Store ML model metadata"""

    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    trained_at = Column(DateTime, nullable=False)
    training_end_date = Column(Date, nullable=False)
    metrics = Column(JSON)
    file_path = Column(String(500))
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<ModelMetadata(name={self.model_name}, version={self.version})>"
