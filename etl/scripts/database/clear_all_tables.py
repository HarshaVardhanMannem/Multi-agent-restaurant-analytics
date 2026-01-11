#!/usr/bin/env python3
"""
Script to clear all data from unified schema tables.
Respects foreign key constraints by deleting in correct order.
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

from scripts.core.paths import setup_script_paths
from scripts.database.db_connection import get_db_connection, test_connection

# Ensure paths are set up (this is idempotent)
setup_script_paths()

# Tables in order of deletion (respecting foreign keys)
# Tables with foreign keys must be deleted before their referenced tables
TABLES_DELETE_ORDER = [
    # Order matters - delete child tables first
    'unified_order_item_modifiers',      # References unified_order_items
    'unified_payments',                   # References unified_orders
    'unified_order_items',                # References unified_orders, unified_products
    'unified_orders',                     # References unified_locations
    'product_name_mapping',               # References unified_products
    'unified_products',                   # References unified_categories
    'location_id_mapping',                # References unified_locations
    'unified_categories',                 # May self-reference (parent_category_id)
    'unified_locations',                  # No dependencies
]

# Sequences to reset (for SERIAL columns)
SEQUENCES = [
    'unified_locations_location_id_seq',
    'location_id_mapping_mapping_id_seq',
    'unified_categories_category_id_seq',
    'unified_products_product_id_seq',
    'product_name_mapping_mapping_id_seq',
    'unified_orders_order_id_seq',
    'unified_order_items_order_item_id_seq',
    'unified_order_item_modifiers_modifier_id_seq',
    'unified_payments_payment_id_seq',
]


def clear_all_tables(confirm: bool = False):
    """
    Clear all data from unified schema tables.
    
    Args:
        confirm: If False, will ask for confirmation before proceeding
    """
    # Test connection
    print("Testing database connection...")
    if not test_connection():
        print("Failed to connect to database. Please check your DATABASE_URL in .env")
        return False
    
    # Confirmation prompt
    if not confirm:
        print("\n" + "=" * 80)
        print("WARNING: This will DELETE ALL DATA from the following tables:")
        print("=" * 80)
        for table in TABLES_DELETE_ORDER:
            print(f"  - {table}")
        print("\nThis action CANNOT be undone!")
        print("=" * 80)
        
        response = input("\nType 'DELETE ALL' to confirm: ").strip()
        if response != 'DELETE ALL':
            print("\nCancelled. No data was deleted.")
            return False
    
    print("\nConnecting to database...")
    conn = get_db_connection()
    
    try:
        # Disable foreign key checks temporarily (PostgreSQL doesn't support this,
        # but we're deleting in correct order anyway)
        print("\nDeleting data from tables...")
        
        deleted_counts = {}
        
        for table in TABLES_DELETE_ORDER:
            try:
                # Get count before deletion
                count_query = text(f"SELECT COUNT(*) FROM {table}")
                result = conn.execute(count_query)
                count_before = result.fetchone()[0]
                
                # Delete all rows
                delete_query = text(f"DELETE FROM {table}")
                conn.execute(delete_query)
                
                deleted_counts[table] = count_before
                print(f"  ✓ Deleted {count_before:,} rows from {table}")
                
            except Exception as e:
                print(f"  ✗ Error deleting from {table}: {e}")
                # Continue with other tables
        
        # Reset sequences
        print("\nResetting sequences...")
        for sequence in SEQUENCES:
            try:
                reset_query = text(f"ALTER SEQUENCE {sequence} RESTART WITH 1")
                conn.execute(reset_query)
                print(f"  ✓ Reset {sequence}")
            except Exception as e:
                # Sequence might not exist or already be reset
                print(f"  ! Could not reset {sequence}: {e}")
        
        # Commit all changes
        conn.commit()
        print("\n✓ All changes committed successfully!")
        
        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        total_deleted = sum(deleted_counts.values())
        print(f"Total rows deleted: {total_deleted:,}")
        print("\nBreakdown by table:")
        for table, count in deleted_counts.items():
            print(f"  {table}: {count:,} rows")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error during deletion: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def clear_specific_table(table_name: str, confirm: bool = False):
    """
    Clear data from a specific table.
    
    Args:
        table_name: Name of table to clear
        confirm: If False, will ask for confirmation
    """
    if not confirm:
        print(f"\nWARNING: This will DELETE ALL DATA from table '{table_name}'")
        response = input("Type 'DELETE' to confirm: ").strip()
        if response != 'DELETE':
            print("Cancelled.")
            return False
    
    print(f"\nConnecting to database...")
    conn = get_db_connection()
    
    try:
        # Get count
        count_query = text(f"SELECT COUNT(*) FROM {table_name}")
        result = conn.execute(count_query)
        count_before = result.fetchone()[0]
        
        # Delete all rows
        delete_query = text(f"DELETE FROM {table_name}")
        conn.execute(delete_query)
        conn.commit()
        
        print(f"✓ Deleted {count_before:,} rows from {table_name}")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error: {e}")
        return False
    finally:
        conn.close()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear all data from unified schema tables')
    parser.add_argument('--table', help='Clear specific table only')
    parser.add_argument('--yes', '-y', action='store_true', 
                       help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    if args.table:
        clear_specific_table(args.table, confirm=args.yes)
    else:
        clear_all_tables(confirm=args.yes)


if __name__ == "__main__":
    main()

