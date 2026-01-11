"""
Database Connection Utility
Handles Supabase database connections for data ingestion
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)  # This will also load from current directory if project root doesn't have it
load_dotenv()  # Also try loading from current directory


def get_db_connection_string() -> Optional[str]:
    """
    Get database connection string from environment variable.
    
    Checks DATABASE_URL first, then SUPABASE_DB_URL as fallback.
    Returns None if ENABLE_SUPABASE is explicitly set to False.
    
    Returns:
        Database connection string or None
    
    Raises:
        ValueError: If no valid database URL is found AND ENABLE_SUPABASE is True (default)
    """
    if os.getenv('ENABLE_SUPABASE', 'True').lower() == 'false':
        return None

    database_url = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')
    
    if not database_url:
        raise ValueError(
            "DATABASE_URL or SUPABASE_DB_URL environment variable must be set"
        )
    
    if not database_url.startswith('postgresql://') and not database_url.startswith('postgres://'):
        raise ValueError("Invalid DATABASE_URL format. Must start with postgresql:// or postgres://")
    
    return database_url


def get_local_db_connection_string() -> str:
    """
    Get local PostgreSQL connection string from environment variable.
    
    Returns:
        Database connection string
    
    Raises:
        ValueError: If ENABLE_LOCAL_POSTGRES is True but URL is missing
    """
    if os.getenv('ENABLE_LOCAL_POSTGRES', 'False').lower() == 'true':
        url = os.getenv('LOCAL_POSTGRES_URL')
        if not url:
            raise ValueError("LOCAL_POSTGRES_URL must be set when ENABLE_LOCAL_POSTGRES is True")
        return url
    return None


def create_db_engine(connection_string: Optional[str] = None) -> Engine:
    """
    Create SQLAlchemy database engine.
    
    Args:
        connection_string: Optional specific connection string to use.
                         If None, gets from get_db_connection_string()
    
    Returns:
        SQLAlchemy Engine instance
    """
    if connection_string is None:
        connection_string = get_db_connection_string()
        
    engine = create_engine(
        connection_string,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,  # Set to True for SQL debugging
    )
    return engine


def create_local_db_engine() -> Optional[Engine]:
    """
    Create SQLAlchemy engine for local database if enabled.
    
    Returns:
        Engine or None if not enabled
    """
    try:
        conn_str = get_local_db_connection_string()
        if conn_str:
            return create_db_engine(conn_str)
    except ValueError as e:
        print(f"Warning: {e}")
    return None


def get_db_connection(connection_string: Optional[str] = None):
    """
    Get database connection (for pandas/sqlalchemy use).
    
    Args:
        connection_string: Optional specific connection string
        
    Returns:
        Database connection object
    """
    engine = create_db_engine(connection_string)
    return engine.connect()


def get_local_db_connection():
    """Get local database connection if enabled."""
    conn_str = get_local_db_connection_string()
    if conn_str:
        return get_db_connection(conn_str)
    return None


def test_connection(connection_string: Optional[str] = None) -> bool:
    """
    Test database connection.
    
    Args:
        connection_string: Optional specific connection string to test
        
    Returns:
        True if connection successful, False otherwise.
        Returns False (safely) if connection_string is None (e.g. disabled Supabase).
    """
    try:
        if connection_string is None:
            connection_string = get_db_connection_string()
            
        if not connection_string:
            # Could be disabled
            if os.getenv('ENABLE_SUPABASE', 'True').lower() == 'false':
                 print("Supabase connection disabled.")
                 return False
            print("No connection string found.")
            return False
            
        print(f"Testing database connection to {connection_string.split('@')[-1]}...")
        
        engine = create_db_engine(connection_string)
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            conn.commit()
        print("Database connection successful!")
        return True
    except ValueError as e:
        print(f"Configuration error: {e}")
        return False
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def test_local_connection() -> bool:
    """Test local database connection if enabled."""
    try:
        conn_str = get_local_db_connection_string()
        if conn_str:
            return test_connection(conn_str)
        return False
    except ValueError:
        return False


if __name__ == "__main__":
    print("Testing Primary Connection:")
    test_connection()
    
    if os.getenv('ENABLE_LOCAL_POSTGRES', 'False').lower() == 'true':
        print("\nTesting Local Connection:")
        test_local_connection()

