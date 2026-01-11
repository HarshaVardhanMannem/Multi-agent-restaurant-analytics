"""
Script to create materialized views and indexes for performance optimization
Run this after unified_schema.sql
"""

import sys
from pathlib import Path
from sqlalchemy import text

# Setup paths BEFORE importing scripts modules
# Add etl directory to sys.path so we can import scripts.* (scripts is in etl/scripts/)
_script_dir = Path(__file__).parent.parent  # database -> scripts
_etl_dir = _script_dir.parent  # scripts -> etl
_etl_dir_str = str(_etl_dir)
if _etl_dir_str not in sys.path:
    sys.path.insert(0, _etl_dir_str)

from scripts.core.paths import setup_script_paths, get_schema_file
from scripts.core.sql_executor import read_sql_file, parse_sql_statements, extract_object_name
from scripts.database.db_connection import get_db_connection, test_connection

# Ensure paths are set up (this is idempotent)
setup_script_paths()


def create_materialized_views(connection_string: str = None):
    """
    Create materialized views and indexes from SQL file
    
    Args:
        connection_string: Optional specific connection string to use
    """
    
    # Test connection
    if not test_connection(connection_string):
        print("❌ Database connection failed. Please check your DATABASE_URL.")
        sys.exit(1)
    
    # Get SQL file path
    sql_file = get_schema_file('optimization_materialized_views.sql')
    print(f"📄 Reading SQL file: {sql_file}")
    
    # Read and parse SQL file
    sql_content = read_sql_file(sql_file)
    statements = parse_sql_statements(sql_content, remove_comments=True)
    print(f"📊 Found {len(statements)} SQL statements to execute")
    
    # Connect to database
    conn = get_db_connection(connection_string)
    
    try:
        print("\n🚀 Creating materialized views and indexes...")
        print("=" * 60)
        
        executed = 0
        errors = []
        
        for i, statement in enumerate(statements, 1):
            try:
                # Skip empty statements
                if not statement.strip():
                    continue
                
                # Execute statement
                from sqlalchemy import text
                conn.execute(text(statement))
                conn.commit()
                
                # Extract object name for better logging
                view_name = extract_object_name(statement, "MATERIALIZED VIEW")
                if view_name:
                    print(f"✓ Created materialized view: {view_name}")
                else:
                    index_name = extract_object_name(statement, "INDEX")
                    if index_name:
                        print(f"✓ Created index: {index_name}")
                    else:
                        regular_view = extract_object_name(statement, "VIEW")
                        if regular_view:
                            print(f"✓ Created/updated view alias: {regular_view}")
                        else:
                            print(f"✓ Executed statement {i}")
                
                executed += 1
                
            except Exception as e:
                error_msg = f"Error in statement {i}: {str(e)}"
                errors.append(error_msg)
                print(f"⚠ {error_msg}")
                # Continue with next statement
                conn.rollback()
        
        print("=" * 60)
        print(f"\n✅ Successfully executed {executed}/{len(statements)} statements")
        
        if errors:
            print(f"\n⚠ {len(errors)} errors occurred:")
            for error in errors:
                print(f"  - {error}")
        
        # Verify materialized views were created
        print("\n🔍 Verifying materialized views...")
        from sqlalchemy import text
        verify_query = text("""
            SELECT matviewname 
            FROM pg_matviews 
            WHERE schemaname = 'public' 
            AND matviewname LIKE 'mv_%'
            ORDER BY matviewname
        """)
        result = conn.execute(verify_query)
        views = [row[0] for row in result]
        
        if views:
            print(f"✓ Found {len(views)} materialized views:")
            for view in views:
                print(f"  - {view}")
        else:
            print("⚠ No materialized views found (mv_*)")
        
        # Verify indexes
        print("\n🔍 Verifying indexes...")
        index_query = text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND (tablename LIKE 'mv_%' OR indexname LIKE 'idx_%')
            ORDER BY indexname
        """)
        result = conn.execute(index_query)
        indexes = [row[0] for row in result]
        
        if indexes:
            print(f"✓ Found {len(indexes)} indexes")
        else:
            print("⚠ No indexes found")
        
        print("\n✅ Materialized views setup complete!")
        print("\n💡 Next steps:")
        print("  1. Refresh views after data ingestion: python etl/scripts/refresh/refresh_materialized_views_sync.py")
        print("  2. Or let ETL pipeline refresh automatically: python etl/scripts/pipeline/ingest_unified_data.py --all")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error creating materialized views: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == "__main__":
    create_materialized_views()

