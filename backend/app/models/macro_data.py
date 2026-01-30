"""
SQLAlchemy model for macro economic data
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class MacroData(Base):
    """Store macro economic data from FRED and other sources"""

    __tablename__ = "macro_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    value = Column(Float)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_macro_series_date", "series_id", "date", unique=True),
    )

    def __repr__(self):
        return f"<MacroData(series_id={self.series_id}, date={self.date}, value={self.value})>"
