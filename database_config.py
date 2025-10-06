"""
Database Configuration Module
Handles PostgreSQL/Supabase database connections only.
"""

import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus

Base = declarative_base()

class DatabaseConfig:
    """Database configuration manager for PostgreSQL/Supabase only."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.is_postgres = True  # Always PostgreSQL now
        
        # Always setup PostgreSQL/Supabase
        self._setup_postgresql()
    
    def _setup_postgresql(self):
        """Setup PostgreSQL connection for Supabase."""
        # Get database connection details from environment variables
        db_host = os.environ.get('DB_HOST', 'db.xxxxxxxxxxxx.supabase.co')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'postgres')
        db_user = os.environ.get('DB_USER', 'postgres')
        db_password = os.environ.get('DB_PASSWORD', 'your_password_here')
        
        # Create connection string
        connection_string = f"postgresql://{quote_plus(db_user)}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"
        
        try:
            self.engine = create_engine(connection_string, echo=False)
            self.session_factory = sessionmaker(bind=self.engine)
            self.is_postgres = True
            print(f"✅ Connected to Supabase PostgreSQL database: {db_host}")
        except Exception as e:
            print(f"❌ Failed to connect to Supabase PostgreSQL: {e}")
            raise Exception(f"Database connection failed: {e}")
    
    def get_session(self):
        """Get a database session."""
        return self.session_factory()
    
    def execute_raw_sql(self, sql, params=None):
        """Execute raw SQL query."""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return result.fetchall()
    
    def execute_raw_sql_single(self, sql, params=None):
        """Execute raw SQL query and return single result."""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return result.fetchone()
    
    def get_connection(self):
        """Get raw database connection."""
        return self.engine.connect()

# Global database configuration
db_config = DatabaseConfig()