"""
Database connection and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import os

from .models import Base


class Database:
    def __init__(self, database_url: str, pool_size: int = 20, max_overflow: int = 10):
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            echo=os.getenv("DEBUG", "false").lower() == "true"
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_db(self) -> Generator[Session, None, None]:
        """Dependency for FastAPI to get database session"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()


# Global database instance (initialized in main.py)
db: Database = None


def init_db(database_url: str, pool_size: int = 20, max_overflow: int = 10):
    """Initialize the global database instance"""
    global db
    db = Database(database_url, pool_size, max_overflow)
    return db


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to get database session"""
    if db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    yield from db.get_db()
