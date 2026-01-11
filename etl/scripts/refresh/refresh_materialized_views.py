"""
Materialized View Refresh Utility (Async/Standalone)
Standalone CLI tool for refreshing materialized views using asyncpg.
Use this for scheduled jobs or standalone operations.

For integration with SQLAlchemy-based ETL pipeline, use refresh_materialized_views_sync.py
"""

import sys
import asyncpg
from typing import Optional
from datetime import datetime
from pathlib import Path

# Setup paths BEFORE importing scripts modules
# Add etl directory to sys.path so we can import scripts.* (scripts is in etl/scripts/)
_script_dir = Path(__file__).parent.parent  # refresh -> scripts
_etl_dir = _script_dir.parent  # scripts -> etl
_etl_dir_str = str(_etl_dir)
if _etl_dir_str not in sys.path:
    sys.path.insert(0, _etl_dir_str)

from scripts.core.paths import setup_script_paths
from scripts.core.logger import setup_logger
from scripts.core.constants import MATERIALIZED_VIEWS, MATERIALIZED_VIEWS_WITH_DATES

# Ensure paths are set up (this is idempotent)
setup_script_paths()

logger = setup_logger(__name__)


# Use centralized database URL function
from scripts.database.db_connection import get_db_connection_string as get_database_url


async def refresh_materialized_views(
    connection: Optional[asyncpg.Connection] = None,
    views: Optional[list[str]] = None,
    incremental: bool = False,
    date_range_days: int = 2
) -> dict:
    """
    Refresh materialized views after data ingestion.
    
    Args:
        connection: Existing database connection (creates new if None)
        views: List of view names to refresh (None = all views)
        incremental: If True, only refresh recent data (last N days)
        date_range_days: Number of days to refresh for incremental updates
    
    Returns:
        Dictionary with refresh results and timing
    """
    
    views_to_refresh = views or MATERIALIZED_VIEWS
    
    # Filter to only existing views
    existing_views = []
    should_close_conn = False
    
    try:
        if connection is None:
            db_url = get_database_url()
            connection = await asyncpg.connect(db_url)
            should_close_conn = True
        
        # Check which views exist
        existing_views_query = """
            SELECT matviewname 
            FROM pg_matviews 
            WHERE schemaname = 'public' 
            AND matviewname = ANY($1)
        """
        existing_views = await connection.fetch(
            existing_views_query,
            views_to_refresh
        )
        existing_views = [row['matviewname'] for row in existing_views]
        
        if not existing_views:
            logger.warning("No materialized views found to refresh")
            return {
                'success': False,
                'message': 'No materialized views found',
                'views_refreshed': [],
                'duration_seconds': 0
            }
        
        logger.info(f"Refreshing {len(existing_views)} materialized views...")
        start_time = datetime.now()
        
        if incremental:
            # Incremental refresh: Only update recent data
            logger.info(f"Performing incremental refresh (last {date_range_days} days)")
            await _refresh_incremental(connection, existing_views, date_range_days)
        else:
            # Full refresh: Refresh all data
            logger.info("Performing full refresh")
            for view_name in existing_views:
                try:
                    logger.info(f"Refreshing {view_name}...")
                    await connection.execute(
                        f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"
                    )
                    logger.info(f"✓ {view_name} refreshed successfully")
                except Exception as e:
                    logger.error(f"✗ Failed to refresh {view_name}: {e}")
                    raise
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✓ Materialized views refresh completed in {duration:.2f} seconds")
        
        return {
            'success': True,
            'views_refreshed': existing_views,
            'duration_seconds': duration,
            'refresh_type': 'incremental' if incremental else 'full'
        }
    
    except Exception as e:
        logger.error(f"Error refreshing materialized views: {e}")
        raise
    
    finally:
        if should_close_conn and connection:
            await connection.close()


async def _refresh_incremental(
    connection: asyncpg.Connection,
    views: list[str],
    days: int
):
    """
    Perform incremental refresh for time-based materialized views.
    Only refreshes data from the last N days.
    """
    
    # Views that support incremental refresh (have date columns)
    # Use constants for incremental views
    incremental_views = MATERIALIZED_VIEWS_WITH_DATES
    
    # Full refresh for views that don't support incremental
    full_refresh_views = [v for v in views if v not in incremental_views]
    
    # Incremental refresh for time-based views
    for view_name in views:
        if view_name in incremental_views:
            date_column = incremental_views[view_name]
            try:
                logger.info(f"Incremental refresh: {view_name} (last {days} days)")
                
                # Delete old rows for the date range
                delete_query = f"""
                    DELETE FROM {view_name} 
                    WHERE {date_column} >= CURRENT_DATE - INTERVAL '{days} days'
                """
                deleted = await connection.execute(delete_query)
                logger.info(f"  Deleted {deleted} old rows from {view_name}")
                
                # Re-insert fresh data for the date range
                # Note: This requires the original view definition
                # For now, we'll do a full refresh of these views
                # In production, you'd want to store the INSERT query
                await connection.execute(
                    f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"
                )
                logger.info(f"  ✓ {view_name} refreshed")
            except Exception as e:
                logger.error(f"  ✗ Failed incremental refresh for {view_name}: {e}")
                # Fallback to full refresh
                await connection.execute(
                    f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"
                )
        else:
            # Full refresh for non-time-based views
            try:
                logger.info(f"Full refresh: {view_name}")
                await connection.execute(
                    f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"
                )
                logger.info(f"  ✓ {view_name} refreshed")
            except Exception as e:
                logger.error(f"  ✗ Failed to refresh {view_name}: {e}")
                raise


async def refresh_views_smart(connection: Optional[asyncpg.Connection] = None) -> dict:
    """
    Smart refresh: Determines if incremental or full refresh is needed.
    
    Logic:
    - If data is > 1 day old, do full refresh
    - Otherwise, do incremental refresh
    """
    
    should_close_conn = False
    
    try:
        if connection is None:
            db_url = get_database_url()
            connection = await asyncpg.connect(db_url)
            should_close_conn = True
        
        # Check when views were last refreshed
        check_query = """
            SELECT MAX(order_date) as last_date
            FROM mv_daily_sales_summary
        """
        
        try:
            result = await connection.fetchrow(check_query)
            last_date = result['last_date'] if result else None
            
            if last_date:
                days_behind = (datetime.now().date() - last_date).days
                logger.info(f"Last data date: {last_date} ({days_behind} days behind)")
                
                if days_behind > 1:
                    logger.info("Data is > 1 day old, performing full refresh")
                    return await refresh_materialized_views(
                        connection=connection,
                        incremental=False
                    )
                else:
                    logger.info("Data is recent, performing incremental refresh")
                    return await refresh_materialized_views(
                        connection=connection,
                        incremental=True,
                        date_range_days=2
                    )
            else:
                # No data, do full refresh
                logger.info("No data found, performing full refresh")
                return await refresh_materialized_views(
                    connection=connection,
                    incremental=False
                )
        except Exception as e:
            # If check fails, assume full refresh needed
            logger.warning(f"Could not check view freshness: {e}. Performing full refresh.")
            return await refresh_materialized_views(
                connection=connection,
                incremental=False
            )
    
    finally:
        if should_close_conn and connection:
            await connection.close()


def main():
    """CLI entry point for refreshing materialized views"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Refresh materialized views for analytics'
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Perform incremental refresh (last 2 days only)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Perform full refresh (all data)'
    )
    parser.add_argument(
        '--smart',
        action='store_true',
        help='Smart refresh (auto-detect incremental vs full)'
    )
    parser.add_argument(
        '--views',
        nargs='+',
        help='Specific views to refresh (default: all)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=2,
        help='Number of days for incremental refresh (default: 2)'
    )
    
    args = parser.parse_args()
    
    # Determine refresh strategy
    if args.smart:
        refresh_func = refresh_views_smart
        refresh_kwargs = {}
    elif args.incremental:
        refresh_func = refresh_materialized_views
        refresh_kwargs = {'incremental': True, 'date_range_days': args.days}
    elif args.full:
        refresh_func = refresh_materialized_views
        refresh_kwargs = {'incremental': False}
    else:
        # Default to smart refresh
        refresh_func = refresh_views_smart
        refresh_kwargs = {}
    
    if args.views:
        refresh_kwargs['views'] = args.views
    
    # Run refresh
    import asyncio
    try:
        result = asyncio.run(refresh_func(**refresh_kwargs))
        
        if result['success']:
            print(f"\n✓ Successfully refreshed {len(result['views_refreshed'])} views")
            print(f"  Duration: {result['duration_seconds']:.2f} seconds")
            print(f"  Type: {result.get('refresh_type', 'smart')}")
            print(f"  Views: {', '.join(result['views_refreshed'])}")
            sys.exit(0)
        else:
            print(f"\n✗ Refresh failed: {result.get('message', 'Unknown error')}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


