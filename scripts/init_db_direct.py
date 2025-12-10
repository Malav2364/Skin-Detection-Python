#!/usr/bin/env python3
"""
Direct database initialization using SQLAlchemy
Bypasses Alembic for initial setup
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine
from db.models import Base
from app.config import get_settings

def init_database():
    """Initialize database tables directly using SQLAlchemy"""
    
    print("🔧 Initializing database with SQLAlchemy...")
    
    # Get database URL from settings
    settings = get_settings()
    database_url = settings.DATABASE_URL
    
    print(f"📊 Connecting to: {database_url.split('@')[1] if '@' in database_url else 'database'}")
    
    # Create engine
    engine = create_engine(database_url)
    
    # Create all tables
    print("📦 Creating all tables...")
    Base.metadata.create_all(engine)
    
    print("✅ Database initialization complete!")
    print("\n📋 Created tables:")
    
    # List all tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        print(f"  - {table_name}")
    
    engine.dispose()

if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
