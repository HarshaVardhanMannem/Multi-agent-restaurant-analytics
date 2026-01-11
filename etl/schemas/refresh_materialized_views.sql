-- =====================================================
-- MATERIALIZED VIEW REFRESH STRATEGY
-- =====================================================
-- This script provides refresh strategies for materialized views
-- Run this periodically (via cron or scheduled job)
-- =====================================================

-- =====================================================
-- OPTION 1: FULL REFRESH (Slower, but ensures consistency)
-- =====================================================
-- Use this for:
-- - Initial setup
-- - After bulk data loads
-- - When data integrity is critical
-- - During low-traffic periods

-- Full refresh all materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_sales_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_location_sales;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_sales_pattern;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_payment_methods_by_source;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_order_type_performance;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_category_sales_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_location_performance;

-- =====================================================
-- OPTION 2: INCREMENTAL REFRESH (Faster, for recent data)
-- =====================================================
-- Use this for:
-- - Regular scheduled updates (every 15 minutes)
-- - Real-time or near-real-time requirements
-- - High-traffic periods

-- Incremental refresh: Only update last 24-48 hours
-- This requires dropping and recreating affected rows

-- For mv_daily_sales_summary (refresh last 2 days)
DELETE FROM mv_daily_sales_summary 
WHERE order_date >= CURRENT_DATE - INTERVAL '2 days';

INSERT INTO mv_daily_sales_summary
SELECT 
    uo.order_date,
    ul.location_id,
    ul.location_code,
    ul.location_name,
    uo.order_type,
    uo.source_system,
    COUNT(DISTINCT uo.order_id) as order_count,
    COUNT(DISTINCT uoi.order_item_id) as item_count,
    SUM(uo.subtotal_cents) / 100.0 as total_subtotal,
    SUM(uo.tax_cents) / 100.0 as total_tax,
    SUM(uo.tip_cents) / 100.0 as total_tips,
    SUM(uo.total_cents) / 100.0 as total_revenue,
    SUM(uo.service_fee_cents) / 100.0 as total_service_fees,
    SUM(uo.delivery_fee_cents) / 100.0 as total_delivery_fees,
    SUM(uo.commission_cents) / 100.0 as total_commissions,
    SUM(COALESCE(uo.merchant_payout_cents, uo.total_cents - COALESCE(uo.commission_cents, 0))) / 100.0 as net_revenue,
    AVG(uo.total_cents) / 100.0 as avg_order_value
FROM unified_orders uo
JOIN unified_locations ul ON uo.unified_location_id = ul.location_id
LEFT JOIN unified_order_items uoi ON uo.order_id = uoi.order_id
WHERE uo.voided = FALSE
    AND uo.order_date >= CURRENT_DATE - INTERVAL '2 days'
GROUP BY uo.order_date, ul.location_id, ul.location_code, ul.location_name, uo.order_type, uo.source_system;

-- For mv_hourly_sales_pattern (refresh last 2 days)
DELETE FROM mv_hourly_sales_pattern 
WHERE order_date >= CURRENT_DATE - INTERVAL '2 days';

INSERT INTO mv_hourly_sales_pattern
SELECT 
    uo.order_date,
    EXTRACT(HOUR FROM uo.order_timestamp) as order_hour,
    EXTRACT(DOW FROM uo.order_timestamp) as day_of_week,
    ul.location_id,
    ul.location_code,
    ul.location_name,
    uo.order_type,
    uo.source_system,
    COUNT(DISTINCT uo.order_id) as order_count,
    SUM(uo.total_cents) / 100.0 as total_revenue,
    AVG(uo.total_cents) / 100.0 as avg_order_value
FROM unified_orders uo
JOIN unified_locations ul ON uo.unified_location_id = ul.location_id
WHERE uo.voided = FALSE
    AND uo.order_date >= CURRENT_DATE - INTERVAL '2 days'
GROUP BY uo.order_date, EXTRACT(HOUR FROM uo.order_timestamp), EXTRACT(DOW FROM uo.order_timestamp), 
         ul.location_id, ul.location_code, ul.location_name, uo.order_type, uo.source_system;

-- Note: Product and category views may need full refresh if products change
-- Payment and order type views can be refreshed less frequently

-- =====================================================
-- OPTION 3: SMART REFRESH FUNCTION (Recommended)
-- =====================================================
-- This function determines refresh strategy based on data age

CREATE OR REPLACE FUNCTION refresh_materialized_views_smart()
RETURNS void AS $$
DECLARE
    last_refresh_date DATE;
    days_since_refresh INTEGER;
BEGIN
    -- Check when views were last refreshed (using mv_daily_sales_summary as reference)
    SELECT MAX(order_date) INTO last_refresh_date
    FROM mv_daily_sales_summary;
    
    days_since_refresh := COALESCE(CURRENT_DATE - last_refresh_date, 999);
    
    -- If more than 1 day old, do full refresh
    IF days_since_refresh > 1 THEN
        RAISE NOTICE 'Performing full refresh (data is % days old)', days_since_refresh;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales_summary;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_sales_summary;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_location_sales;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_sales_pattern;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_payment_methods_by_source;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_order_type_performance;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_category_sales_summary;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_location_performance;
    ELSE
        -- Otherwise, incremental refresh for time-based views
        RAISE NOTICE 'Performing incremental refresh (data is % days old)', days_since_refresh;
        
        -- Incremental refresh for daily and hourly views
        -- (Use DELETE + INSERT pattern from OPTION 2 above)
        -- For brevity, showing full refresh here - implement incremental logic as needed
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales_summary;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_sales_pattern;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SCHEDULING RECOMMENDATIONS
-- =====================================================

-- PostgreSQL cron extension (pg_cron) - if available:
-- SELECT cron.schedule('refresh-materialized-views', '*/15 * * * *', 
--     'SELECT refresh_materialized_views_smart();');

-- Or use external cron job:
-- */15 * * * * psql $DATABASE_URL -c "SELECT refresh_materialized_views_smart();"

-- =====================================================
-- MONITORING QUERIES
-- =====================================================

-- Check materialized view sizes
SELECT 
    schemaname,
    matviewname,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
FROM pg_matviews
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||matviewname) DESC;

-- Check last refresh time (approximate - based on max date in view)
SELECT 
    'mv_daily_sales_summary' as view_name,
    MAX(order_date) as last_data_date,
    CURRENT_DATE - MAX(order_date) as days_behind
FROM mv_daily_sales_summary
UNION ALL
SELECT 
    'mv_hourly_sales_pattern',
    MAX(order_date),
    CURRENT_DATE - MAX(order_date)
FROM mv_hourly_sales_pattern;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND tablename LIKE 'mv_%'
ORDER BY idx_scan DESC;


