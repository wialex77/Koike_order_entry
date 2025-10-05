"""
Database Configuration Module
Handles both SQLite (development) and PostgreSQL (production) databases.
"""

import os
import sqlite3
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus

Base = declarative_base()

class DatabaseConfig:
    """Database configuration manager for SQLite and PostgreSQL."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.is_postgres = False
        
        # Check if we're in production (App Runner)
        if os.environ.get('FLASK_ENV') == 'production':
            self._setup_postgresql()
        else:
            self._setup_sqlite()
    
    def _setup_postgresql(self):
        """Setup PostgreSQL connection for production (Supabase)."""
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
            print("Falling back to SQLite for development...")
            self._setup_sqlite()
    
    def _get_db_password(self):
        """Get database password from environment variable."""
        return os.environ.get('DB_PASSWORD', 'your_password_here')
    
    def _setup_sqlite(self):
        """Setup SQLite connection for development."""
        db_path = "data/metrics.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        connection_string = f"sqlite:///{db_path}"
        self.engine = create_engine(connection_string, echo=False)
        self.session_factory = sessionmaker(bind=self.engine)
        self.is_postgres = False
        print(f"✅ Connected to SQLite database: {db_path}")
    
    def get_session(self):
        """Get a database session."""
        return self.session_factory()
    
    def execute_raw_sql(self, sql, params=None):
        """Execute raw SQL query."""
        with self.engine.connect() as conn:
            if self.is_postgres:
                result = conn.execute(text(sql), params or {})
            else:
                result = conn.execute(sql, params or {})
            
            # Check if this is a SELECT query that returns rows
            sql_upper = sql.strip().upper()
            if sql_upper.startswith('SELECT'):
                return result.fetchall()
            else:
                # For non-SELECT queries (CREATE, INSERT, UPDATE, DELETE), commit and return empty list
                conn.commit()
                return []
    
    def execute_raw_sql_single(self, sql, params=None):
        """Execute raw SQL query and return single result."""
        with self.engine.connect() as conn:
            if self.is_postgres:
                result = conn.execute(text(sql), params or {})
            else:
                result = conn.execute(sql, params or {})
            
            # Check if this is a SELECT query that returns rows
            sql_upper = sql.strip().upper()
            if sql_upper.startswith('SELECT'):
                return result.fetchone()
            else:
                # For non-SELECT queries, commit and return None
                conn.commit()
                return None
    
    def get_connection(self):
        """Get raw database connection."""
        if self.is_postgres:
            # For PostgreSQL, return SQLAlchemy connection
            return self.engine.connect()
        else:
            # For SQLite, return sqlite3 connection for compatibility
            return sqlite3.connect(self.engine.url.database)

# Global database configuration
db_config = DatabaseConfig()
