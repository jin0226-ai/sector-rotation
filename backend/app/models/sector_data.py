"""
SQLAlchemy model for sector ETF data
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, BigInteger, Index
from sqlalchemy.sql import func
from app.database import Base


class SectorData(Base):
    """Store sector ETF price data from Yahoo Finance"""

    __tablename__ = "sector_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adj_close = Column(Float)
    volume = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_sector_symbol_date", "symbol", "date", unique=True),
    )

    def __repr__(self):
        return f"<SectorData(symbol={self.symbol}, date={self.date}, close={self.close})>"
