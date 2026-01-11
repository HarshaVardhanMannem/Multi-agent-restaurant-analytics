# Materialized View Refresh Integration

This guide provides detailed information about materialized view refresh strategies.

**For overall pipeline structure, see [ETL_PIPELINE_STRUCTURE.md](ETL_PIPELINE_STRUCTURE.md).**

This document focuses specifically on materialized view refresh options and integration.

## Overview

Materialized views need to be refreshed after data ingestion to ensure analytics queries return up-to-date results. This can be done:

1. **Automatically** - Integrated into the ETL pipeline (recommended)
2. **Manually** - Run refresh script separately
3. **Scheduled** - Via cron or scheduled jobs

## Integration with ETL Pipeline

### Automatic Refresh (Default)

The materialized views are automatically refreshed after successful data ingestion:

```bash
# Refresh happens automatically after ingestion
python etl/scripts/pipeline/ingest_unified_data.py --all
```

**Output:**
```
✓ Data ingestion completed and committed!

Refreshing materialized views...
Refreshing 8 materialized views...
Performing full refresh
Refreshing mv_daily_sales_summary...
✓ mv_daily_sales_summary refreshed successfully
...
✓ Materialized views refresh completed in 12.34 seconds
✓ Materialized views refreshed successfully
  Refreshed 8 views in 12.34s
```

### Skip Refresh

To skip automatic refresh (e.g., for testing):

```bash
python etl/scripts/pipeline/ingest_unified_data.py --all --skip-refresh
```

## Manual Refresh

### Standalone Script (Async)

For standalone use or scheduled jobs:

```bash
# Smart refresh (auto-detects incremental vs full)
python etl/scripts/refresh/refresh_materialized_views.py --smart

# Full refresh
python etl/scripts/refresh/refresh_materialized_views.py --full

# Incremental refresh (last 2 days)
python etl/scripts/refresh/refresh_materialized_views.py --incremental

# Incremental refresh (last 7 days)
python etl/scripts/refresh/refresh_materialized_views.py --incremental --days 7

# Refresh specific views
python etl/scripts/refresh/refresh_materialized_views.py --views mv_daily_sales_summary mv_hourly_sales_pattern
```

### From Python Code (Sync)

For integration with SQLAlchemy-based code:

```python
from scripts.refresh.refresh_materialized_views_sync import refresh_views_smart, refresh_materialized_views
from scripts.database.db_connection import get_db_connection

# Get database connection
conn = get_db_connection()

# Smart refresh (recommended)
result = refresh_views_smart(conn)

# Or explicit refresh
result = refresh_materialized_views(
    db_conn=conn,
    incremental=False,  # or True for incremental
    date_range_days=2
)

print(f"Refreshed {len(result['views_refreshed'])} views in {result['duration_seconds']:.2f}s")
```

## Refresh Strategies

### 1. Full Refresh

**When to use:**
- After bulk data loads
- When data integrity is critical
- Initial setup
- When data is > 1 day old

**Performance:**
- Slower (30-60 seconds for all views)
- Ensures complete consistency

**Usage:**
```python
refresh_materialized_views(db_conn, incremental=False)
```

### 2. Incremental Refresh

**When to use:**
- Regular scheduled updates (every 15 minutes)
- Real-time or near-real-time requirements
- High-traffic periods

**Performance:**
- Faster (5-15 seconds for recent data)
- Only updates last N days

**Usage:**
```python
refresh_materialized_views(
    db_conn,
    incremental=True,
    date_range_days=2  # Refresh last 2 days
)
```

### 3. Smart Refresh (Recommended)

**When to use:**
- Automated scheduling
- Default for ETL pipeline

**Logic:**
- Full refresh if data > 1 day old
- Incremental refresh if data is recent

**Usage:**
```python
refresh_views_smart(db_conn)
```

## Scheduled Refresh

### Option 1: PostgreSQL Cron (pg_cron)

If you have the `pg_cron` extension:

```sql
-- Refresh every 15 minutes
SELECT cron.schedule(
    'refresh-materialized-views',
    '*/15 * * * *',
    $$SELECT refresh_materialized_views_smart()$$
);
```

### Option 2: System Cron

Add to crontab:

```bash
# Refresh every 15 minutes
*/15 * * * * cd /path/to/project && python etl/scripts/refresh/refresh_materialized_views.py --smart

# Full refresh daily at 2 AM
0 2 * * * cd /path/to/project && python etl/scripts/refresh/refresh_materialized_views.py --full
```

### Option 3: Python Scheduler

Using `schedule` library:

```python
import schedule
import time
from scripts.refresh_materialized_views_sync import refresh_views_smart
from scripts.db_connection import get_db_connection

def refresh_views():
    conn = get_db_connection()
    try:
        refresh_views_smart(conn)
    finally:
        conn.close()

# Schedule every 15 minutes
schedule.every(15).minutes.do(refresh_views)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Refresh Timing

### Recommended Schedule

| Scenario | Refresh Frequency | Type |
|----------|------------------|------|
| **After ETL ingestion** | Immediately | Smart |
| **Regular updates** | Every 15 minutes | Incremental |
| **Daily maintenance** | Once per day (2 AM) | Full |
| **Bulk loads** | After each load | Full |

### Performance Considerations

- **Full refresh**: 30-60 seconds (all views)
- **Incremental refresh**: 5-15 seconds (recent data only)
- **Concurrent refresh**: Uses `CONCURRENTLY` to avoid blocking queries
- **Peak hours**: Use incremental refresh to minimize impact

## Monitoring

### Check View Freshness

```python
from sqlalchemy import text

check_query = text("""
    SELECT 
        'mv_daily_sales_summary' as view_name,
        MAX(order_date) as last_data_date,
        CURRENT_DATE - MAX(order_date) as days_behind
    FROM mv_daily_sales_summary
""")

result = conn.execute(check_query).fetchone()
print(f"Last data: {result[1]}, Days behind: {result[2]}")
```

### Check Refresh Status

```python
# After refresh
result = refresh_views_smart(conn)
print(f"Success: {result['success']}")
print(f"Views: {result['views_refreshed']}")
print(f"Duration: {result['duration_seconds']:.2f}s")
```

## Troubleshooting

### Views Not Refreshing

**Problem**: Views are stale after ingestion

**Solution**:
1. Check if views exist: `SELECT * FROM pg_matviews WHERE schemaname = 'public';`
2. Verify refresh is not being skipped: Remove `--skip-refresh` flag
3. Check logs for errors during refresh

### Refresh Takes Too Long

**Problem**: Full refresh takes > 60 seconds

**Solutions**:
1. Use incremental refresh for regular updates
2. Refresh during low-traffic periods
3. Consider refreshing only frequently-used views
4. Check database performance (indexes, connections)

### Concurrent Refresh Errors

**Problem**: `ERROR: cannot refresh materialized view concurrently`

**Solutions**:
1. Ensure unique indexes exist on materialized views
2. Check for locks: `SELECT * FROM pg_locks WHERE relation = 'mv_daily_sales_summary'::regclass;`
3. Wait for current queries to complete
4. Use non-concurrent refresh if needed (blocks queries)

## Best Practices

1. **Always refresh after data ingestion** - Ensures analytics are up-to-date
2. **Use smart refresh by default** - Automatically chooses best strategy
3. **Monitor refresh duration** - Alert if refresh takes > 60 seconds
4. **Schedule regular refreshes** - Every 15 minutes during business hours
5. **Use incremental for frequent updates** - Faster and less resource-intensive
6. **Full refresh for bulk loads** - Ensures complete consistency

## Example Integration

```python
from scripts.pipeline.ingest_unified_data import UnifiedDataIngester
from scripts.refresh.refresh_materialized_views_sync import refresh_views_smart
from scripts.database.db_connection import get_db_connection

# Ingest data
conn = get_db_connection()
try:
    ingester = UnifiedDataIngester(conn)
    ingester.setup_reference_data()
    ingester.ingest_toast_data('data/toast_pos_export.json')
    ingester.ingest_doordash_data('data/doordash_orders.json')
    ingester.ingest_square_data('data/square')
    
    # Commit data
    conn.commit()
    
    # Refresh materialized views
    refresh_result = refresh_views_smart(conn)
    if refresh_result['success']:
        print(f"✓ Views refreshed: {refresh_result['views_refreshed']}")
    else:
        print(f"⚠ Refresh failed: {refresh_result.get('message')}")
        
finally:
    conn.close()
```


