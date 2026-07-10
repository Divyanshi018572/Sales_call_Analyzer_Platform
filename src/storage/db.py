"""
Database connection and session management for SQLAlchemy.

Why this approach:
We establish the SQLAlchemy connection engine, configure session-maker factories, and 
declare the ORM base mapping class. We expose a thread-safe get_db session generator 
to be used as a FastAPI dependency for request-scoped database operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import settings

# Create engine using connection string from settings
engine = create_engine(settings.DATABASE_URL)

# Configure session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative ORM models
Base = declarative_base()

def get_db():
    """
    FastAPI dependency yielding a database session and closing it after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
