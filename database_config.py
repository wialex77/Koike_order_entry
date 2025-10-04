"""
Database Configuration Module
Handles both SQLite (development) and PostgreSQL (production) databases.
"""

import os
import sqlite3
import json
import boto3
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
        """Setup PostgreSQL connection for production."""
        # Get database connection details from environment variables
        db_host = os.environ.get('DB_HOST', 'arzana-db.c8xmsq8gsx4s.us-east-1.rds.amazonaws.com')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'arzana_db')
        db_user = os.environ.get('DB_USER', 'arzana_admin')
        
        # Get password from Secrets Manager if available
        db_password = self._get_db_password()
        
        # Create connection string
        connection_string = f"postgresql://{quote_plus(db_user)}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"
        
        try:
            self.engine = create_engine(connection_string, echo=False)
            self.session_factory = sessionmaker(bind=self.engine)
            self.is_postgres = True
            print(f"✅ Connected to PostgreSQL database: {db_host}")
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            print("Falling back to SQLite for development...")
            self._setup_sqlite()
    
    def _get_db_password(self):
        """Get database password from Secrets Manager or environment variable."""
        try:
            # Check if we have a secret ARN
            secret_arn = os.environ.get('DB_SECRET_ARN')
            if secret_arn:
                # Get password from Secrets Manager
                client = boto3.client('secretsmanager', region_name='us-east-1')
                response = client.get_secret_value(SecretId=secret_arn)
                secret_data = json.loads(response['SecretString'])
                return secret_data['password']
            else:
                # Fall back to environment variable
                return os.environ.get('DB_PASSWORD', 'Arzana2025!')
        except Exception as e:
            print(f"⚠️ Could not get password from Secrets Manager: {e}")
            # Fall back to environment variable
            return os.environ.get('DB_PASSWORD', 'Arzana2025!')
    
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
            return result.fetchall()
    
    def execute_raw_sql_single(self, sql, params=None):
        """Execute raw SQL query and return single result."""
        with self.engine.connect() as conn:
            if self.is_postgres:
                result = conn.execute(text(sql), params or {})
            else:
                result = conn.execute(sql, params or {})
            return result.fetchone()
    
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
