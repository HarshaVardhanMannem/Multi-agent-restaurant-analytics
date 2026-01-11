"""
Synchronous Materialized View Refresh Utility
For integration with SQLAlchemy-based ETL pipeline
"""

import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from sqlalchemy import text

# Setup paths BEFORE importing scripts modules
# Add etl directory to sys.path so we can import scripts.* (scripts is in etl/scripts/)
_script_dir = Path(__file__).parent.parent  # refresh -> scripts
_etl_dir = _script_dir.parent  # scripts -> etl
_etl_dir_str = str(_etl_dir)
if _etl_dir_str not in sys.path:
    sys.path.insert(0, _etl_dir_str)

from scripts.core.logger import setup_logger
from scripts.core.constants import MATERIALIZED_VIEWS, MATERIALIZED_VIEWS_WITH_DATES

logger = setup_logger(__name__)


def refresh_materialized_views(
    db_conn,
    views: Optional[List[str]] = None,
    incremental: bool = False,
    date_range_days: int = 2
) -> dict:
    """
    Refresh materialized views after data ingestion.
    
    Args:
        db_conn: SQLAlchemy database connection
        views: List of view names to refresh (None = all views)
        incremental: If True, only refresh recent data (last N days)
        date_range_days: Number of days to refresh for incremental updates
    
    Returns:
        Dictionary with refresh results and timing
    """
    
    # Ensure connection is in a clean state before refresh
    # This is important when using the same connection from ingestion
    try:
        db_conn.commit()
    except Exception:
        # If commit fails, rollback to clean state
        try:
            db_conn.rollback()
        except Exception:
            pass  # Connection might already be clean
    
    views_to_refresh = views or MATERIALIZED_VIEWS
    
    try:
        # Check which views exist
        check_query = text("""
            SELECT matviewname 
            FROM pg_matviews 
            WHERE schemaname = 'public' 
            AND matviewname = ANY(:views)
        """)
        result = db_conn.execute(check_query, {'views': views_to_refresh})
        existing_views = [row[0] for row in result]
        
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
            _refresh_incremental(db_conn, existing_views, date_range_days)
        else:
            # Full refresh: Refresh all data
            logger.info("Performing full refresh")
            for view_name in existing_views:
                try:
                    logger.info(f"Refreshing {view_name}...")
                    # Try concurrent refresh first (requires unique index)
                    try:
                        refresh_query = text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                        db_conn.execute(refresh_query)
                        db_conn.commit()
                        logger.info(f"✓ {view_name} refreshed successfully (concurrent)")
                    except Exception as concurrent_error:
                        # Rollback the failed transaction first
                        db_conn.rollback()
                        
                        # Fallback to non-concurrent refresh if concurrent fails
                        error_str = str(concurrent_error).lower()
                        if "concurrently" in error_str or "unique index" in error_str or "prerequisite" in error_str:
                            logger.warning(f"  Concurrent refresh failed for {view_name}, using non-concurrent refresh")
                            try:
                                refresh_query = text(f"REFRESH MATERIALIZED VIEW {view_name}")
                                db_conn.execute(refresh_query)
                                db_conn.commit()
                                logger.info(f"✓ {view_name} refreshed successfully (non-concurrent)")
                            except Exception as non_concurrent_error:
                                logger.error(f"✗ Failed to refresh {view_name} (non-concurrent): {non_concurrent_error}")
                                db_conn.rollback()
                                raise
                        else:
                            raise
                except Exception as e:
                    logger.error(f"✗ Failed to refresh {view_name}: {e}")
                    db_conn.rollback()
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
        db_conn.rollback()
        raise


def _refresh_incremental(
    db_conn,
    views: List[str],
    days: int
):
    """
    Perform incremental refresh for time-based materialized views.
    Only refreshes data from the last N days.
    """
    
    # Full refresh for views that don't support incremental
    for view_name in views:
        if view_name in MATERIALIZED_VIEWS_WITH_DATES:
            date_column = MATERIALIZED_VIEWS_WITH_DATES[view_name]
            try:
                logger.info(f"Incremental refresh: {view_name} (last {days} days)")
                
                # Delete old rows for the date range
                delete_query = text(f"""
                    DELETE FROM {view_name} 
                    WHERE {date_column} >= CURRENT_DATE - INTERVAL '{days} days'
                """)
                result = db_conn.execute(delete_query)
                deleted = result.rowcount
                logger.info(f"  Deleted {deleted} old rows from {view_name}")
                db_conn.commit()
                
                # Re-insert fresh data for the date range
                # For now, we'll do a full refresh of these views
                # In production, you'd want to store the INSERT query
                try:
                    refresh_query = text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                    db_conn.execute(refresh_query)
                    db_conn.commit()
                    logger.info(f"  ✓ {view_name} refreshed (concurrent)")
                except Exception as concurrent_error:
                    # Rollback the failed transaction first
                    db_conn.rollback()
                    
                    error_str = str(concurrent_error).lower()
                    if "concurrently" in error_str or "unique index" in error_str or "prerequisite" in error_str:
                        logger.warning(f"  Concurrent refresh failed, using non-concurrent refresh")
                        try:
                            refresh_query = text(f"REFRESH MATERIALIZED VIEW {view_name}")
                            db_conn.execute(refresh_query)
                            db_conn.commit()
                            logger.info(f"  ✓ {view_name} refreshed (non-concurrent)")
                        except Exception as non_concurrent_error:
                            logger.error(f"  ✗ Failed non-concurrent refresh: {non_concurrent_error}")
                            db_conn.rollback()
                            raise
                    else:
                        raise
            except Exception as e:
                logger.error(f"  ✗ Failed incremental refresh for {view_name}: {e}")
                db_conn.rollback()
                # Fallback to full refresh
                try:
                    refresh_query = text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                    db_conn.execute(refresh_query)
                    db_conn.commit()
                except Exception as concurrent_error:
                    # Rollback the failed transaction first
                    db_conn.rollback()
                    
                    error_str = str(concurrent_error).lower()
                    if "concurrently" in error_str or "unique index" in error_str or "prerequisite" in error_str:
                        try:
                            refresh_query = text(f"REFRESH MATERIALIZED VIEW {view_name}")
                            db_conn.execute(refresh_query)
                            db_conn.commit()
                        except Exception as non_concurrent_error:
                            db_conn.rollback()
                            raise
                    else:
                        raise
        else:
            # Full refresh for non-time-based views
            try:
                logger.info(f"Full refresh: {view_name}")
                try:
                    refresh_query = text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                    db_conn.execute(refresh_query)
                    db_conn.commit()
                    logger.info(f"  ✓ {view_name} refreshed (concurrent)")
                except Exception as concurrent_error:
                    # Rollback the failed transaction first
                    db_conn.rollback()
                    
                    error_str = str(concurrent_error).lower()
                    if "concurrently" in error_str or "unique index" in error_str or "prerequisite" in error_str:
                        logger.warning(f"  Concurrent refresh failed, using non-concurrent refresh")
                        try:
                            refresh_query = text(f"REFRESH MATERIALIZED VIEW {view_name}")
                            db_conn.execute(refresh_query)
                            db_conn.commit()
                            logger.info(f"  ✓ {view_name} refreshed (non-concurrent)")
                        except Exception as non_concurrent_error:
                            logger.error(f"  ✗ Failed non-concurrent refresh: {non_concurrent_error}")
                            db_conn.rollback()
                            raise
                    else:
                        raise
            except Exception as e:
                logger.error(f"  ✗ Failed to refresh {view_name}: {e}")
                db_conn.rollback()
                raise


def refresh_views_smart(db_conn) -> dict:
    """
    Smart refresh: Determines if incremental or full refresh is needed.
    
    Logic:
    - If data is > 1 day old, do full refresh
    - Otherwise, do incremental refresh
    """
    
    try:
        # Check when views were last refreshed
        check_query = text("""
            SELECT MAX(order_date) as last_date
            FROM mv_daily_sales_summary
        """)
        
        try:
            result = db_conn.execute(check_query).fetchone()
            last_date = result[0] if result else None
            
            if last_date:
                days_behind = (datetime.now().date() - last_date).days
                logger.info(f"Last data date: {last_date} ({days_behind} days behind)")
                
                if days_behind > 1:
                    logger.info("Data is > 1 day old, performing full refresh")
                    return refresh_materialized_views(
                        db_conn=db_conn,
                        incremental=False
                    )
                else:
                    logger.info("Data is recent, performing incremental refresh")
                    return refresh_materialized_views(
                        db_conn=db_conn,
                        incremental=True,
                        date_range_days=2
                    )
            else:
                # No data, do full refresh
                logger.info("No data found, performing full refresh")
                return refresh_materialized_views(
                    db_conn=db_conn,
                    incremental=False
                )
        except Exception as e:
            # If check fails, assume full refresh needed
            logger.warning(f"Could not check view freshness: {e}. Performing full refresh.")
            return refresh_materialized_views(
                db_conn=db_conn,
                incremental=False
            )
    except Exception as e:
        logger.error(f"Error in smart refresh: {e}")
        raise


