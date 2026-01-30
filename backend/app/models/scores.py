"""
SQLAlchemy models for sector scores and business cycle
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class SectorScore(Base):
    """Store calculated sector scores"""

    __tablename__ = "sector_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    composite_score = Column(Float)
    ml_score = Column(Float)
    cycle_score = Column(Float)
    momentum_score = Column(Float)
    macro_sensitivity_score = Column(Float)
    rank = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_scores_date_symbol", "date", "symbol", unique=True),
    )

    def __repr__(self):
        return f"<SectorScore(date={self.date}, symbol={self.symbol}, score={self.composite_score})>"


class BusinessCycle(Base):
    """Store business cycle phase history"""

    __tablename__ = "business_cycle"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    phase = Column(String(20), nullable=False)
    confidence = Column(Float)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<BusinessCycle(date={self.date}, phase={self.phase})>"


class Features(Base):
    """Store processed features for ML model"""

    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    feature_name = Column(String(100), nullable=False)
    value = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_features_date_name", "date", "feature_name", unique=True),
    )

    def __repr__(self):
        return f"<Features(date={self.date}, feature={self.feature_name}, value={self.value})>"
