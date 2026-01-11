#!/usr/bin/env python3
"""
Simple script to refresh materialized views.
Convenience wrapper for refresh_materialized_views_sync.
"""

import sys
from pathlib import Path

# Setup paths BEFORE importing scripts modules
_script_dir = Path(__file__).parent  # This file is in scripts/
_etl_dir = _script_dir.parent  # scripts -> etl
_etl_dir_str = str(_etl_dir)
if _etl_dir_str not in sys.path:
    sys.path.insert(0, _etl_dir_str)

from scripts.refresh.refresh_materialized_views_sync import refresh_views_smart
from scripts.database.db_connection import get_db_connection

if __name__ == "__main__":
    print("Refreshing materialized views...")
    conn = get_db_connection()
    try:
        result = refresh_views_smart(conn)
        if result['success']:
            print(f"\n✓ Successfully refreshed {len(result['views_refreshed'])} views in {result['duration_seconds']:.2f} seconds")
            print(f"  Views: {', '.join(result['views_refreshed'])}")
        else:
            print(f"\n✗ Failed to refresh views: {result.get('message', 'Unknown error')}")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error refreshing views: {e}")
        sys.exit(1)
    finally:
        conn.close()


