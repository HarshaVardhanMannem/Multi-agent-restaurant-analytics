#!/usr/bin/env python3
"""
Script to create the unified database schema.
Reads unified_schema.sql and executes it.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Setup paths BEFORE importing scripts modules
# Add etl directory to sys.path so we can import scripts.* (scripts is in etl/scripts/)
_script_dir = Path(__file__).parent.parent  # database -> scripts
_etl_dir = _script_dir.parent  # scripts -> etl
_etl_dir_str = str(_etl_dir)
if _etl_dir_str not in sys.path:
    sys.path.insert(0, _etl_dir_str)

from scripts.core.paths import setup_script_paths, get_schema_file
from scripts.core.sql_executor import execute_sql_file
from scripts.database.db_connection import get_db_connection_string, test_connection

# Ensure paths are set up (this is idempotent)
setup_script_paths()

def create_schema(connection_string: str = None):
    """
    Create the unified schema by executing unified_schema.sql
    
    Args:
        connection_string: Optional specific connection string to use
    """
    
    # Test connection first
    print("Testing database connection...")
    if not test_connection(connection_string):
        print("Failed to connect to database. Please check your DATABASE_URL in .env")
        return False
    
    # Get schema file path
    schema_file = get_schema_file('unified_schema.sql')
    print(f"\nReading schema from: {schema_file}")
    
    # Execute SQL file
    if connection_string:
        engine = create_engine(connection_string)
    else:
        engine = create_engine(get_db_connection_string())
    print("\nCreating database schema...")
    print("(This may take a moment...)")
    
    try:
        with engine.connect() as conn:
            # Execute as single block for better performance
            executed, errors = execute_sql_file(
                conn,
                schema_file,
                parse_statements=False,
                verbose=True
            )
        
        # Check if errors are just "already exists" warnings (non-fatal)
        has_non_fatal_errors = False
        if errors:
            has_non_fatal_errors = all("already exists" in err.lower() or "duplicate" in err.lower() for err in errors)
        
        if executed > 0 or has_non_fatal_errors:
            if has_non_fatal_errors:
                print("\n[OK] Database schema check complete!")
                print("Note: Some tables already exist. This is safe to ignore.")
            else:
                print("\n[OK] Database schema created successfully!")
            
            print("\nYou can now run data ingestion:")
            print("  python etl/scripts/pipeline/ingest_unified_data.py --all")
            return True
        else:
            print(f"\n[ERROR] Failed to create schema")
            if errors:
                for err in errors:
                    print(f"  - {err}")
            return False
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] Schema file not found: {e}")
        return False
    except Exception as e:
        error_msg = str(e)
        print(f"\n[ERROR] Failed to create schema: {error_msg}")
        
        # Check if tables already exist
        if "already exists" in error_msg.lower():
            print("\nNote: Some tables may already exist. This is usually safe to ignore.")
            print("You can proceed with data ingestion.")
            return True
        
        return False

if __name__ == "__main__":
    create_schema()

