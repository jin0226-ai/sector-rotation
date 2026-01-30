"""
Database setup and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Ensure data directory exists
data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{data_dir}/sector_rotation.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite specific
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from app.models import macro_data, sector_data, scores, backtest_results
    Base.metadata.create_all(bind=engine)
