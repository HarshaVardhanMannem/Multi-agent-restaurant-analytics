-- =====================================================
-- MATERIALIZED VIEWS & INDEX OPTIMIZATION
-- =====================================================
-- This script creates materialized views and strategic indexes
-- optimized for the expected query patterns from EXAMPLE_QUERIES.md
--
-- Run this AFTER unified_schema.sql
-- =====================================================

-- =====================================================
-- 1. MATERIALIZED VIEWS (High Priority)
-- =====================================================

-- 1.1 Daily Sales Summary (Most Common Query Pattern)
-- Optimizes: "Show me total sales by location", "What was revenue yesterday?", 
--           "Compare sales between locations", "Daily revenue for the first week"
DROP MATERIALIZED VIEW IF EXISTS mv_daily_sales_summary CASCADE;
CREATE MATERIALIZED VIEW mv_daily_sales_summary AS
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
GROUP BY uo.order_date, ul.location_id, ul.location_code, ul.location_name, uo.order_type, uo.source_system;

-- Indexes for mv_daily_sales_summary
CREATE INDEX idx_mv_daily_date ON mv_daily_sales_summary(order_date);
CREATE INDEX idx_mv_daily_location ON mv_daily_sales_summary(location_code);
CREATE INDEX idx_mv_daily_location_date ON mv_daily_sales_summary(location_code, order_date);
CREATE INDEX idx_mv_daily_source ON mv_daily_sales_summary(source_system);
CREATE INDEX idx_mv_daily_type ON mv_daily_sales_summary(order_type);
CREATE INDEX idx_mv_daily_date_source ON mv_daily_sales_summary(order_date, source_system);
CREATE INDEX idx_mv_daily_date_type ON mv_daily_sales_summary(order_date, order_type);

-- 1.2 Product Sales Summary (Top Selling Items)
-- Optimizes: "List the top 10 selling items", "Top selling items at the Mall",
--           "Which category generates the most revenue?"
DROP MATERIALIZED VIEW IF EXISTS mv_product_sales_summary CASCADE;
CREATE MATERIALIZED VIEW mv_product_sales_summary AS
SELECT 
    up.product_id,
    up.product_code,
    up.normalized_name as product,
    up.product_name as original_product_name,
    uc.category_id,
    uc.category_name,
    COUNT(DISTINCT uoi.order_id) as order_count,
    COUNT(DISTINCT uo.unified_location_id) as location_count,
    SUM(uoi.quantity) as total_quantity_sold,
    SUM(uoi.total_price_cents) / 100.0 as total_revenue,
    AVG(uoi.unit_price_cents) / 100.0 as avg_unit_price,
    MIN(uoi.unit_price_cents) / 100.0 as min_unit_price,
    MAX(uoi.unit_price_cents) / 100.0 as max_unit_price
FROM unified_order_items uoi
JOIN unified_products up ON uoi.unified_product_id = up.product_id
LEFT JOIN unified_categories uc ON up.category_id = uc.category_id
JOIN unified_orders uo ON uoi.order_id = uo.order_id
WHERE uo.voided = FALSE
GROUP BY up.product_id, up.product_code, up.normalized_name, up.product_name, uc.category_id, uc.category_name;

-- Indexes for mv_product_sales_summary
CREATE INDEX idx_mv_product_revenue ON mv_product_sales_summary(total_revenue DESC);
CREATE INDEX idx_mv_product_quantity ON mv_product_sales_summary(total_quantity_sold DESC);
CREATE INDEX idx_mv_product_category ON mv_product_sales_summary(category_name);
CREATE INDEX idx_mv_product_name ON mv_product_sales_summary(product);

-- 1.3 Product Sales by Location (Location-Specific Product Queries)
-- Optimizes: "Top selling items at the Mall", "Beverage sales across all locations"
DROP MATERIALIZED VIEW IF EXISTS mv_product_location_sales CASCADE;

CREATE MATERIALIZED VIEW mv_product_location_sales AS
SELECT 
    ul.location_id,
    ul.location_code,
    UPPER(TRIM(ul.location_name)) AS location_name,
    up.product_id,
    up.normalized_name AS product,
    uc.category_name,
    COUNT(DISTINCT uoi.order_id) AS order_count,
    SUM(uoi.quantity) AS total_quantity_sold,
    SUM(uoi.total_price_cents) / 100.0 AS total_revenue
FROM unified_order_items uoi
JOIN unified_products up 
  ON uoi.unified_product_id = up.product_id
LEFT JOIN unified_categories uc 
  ON up.category_id = uc.category_id
JOIN unified_orders uo 
  ON uoi.order_id = uo.order_id
JOIN unified_locations ul 
  ON uo.unified_location_id = ul.location_id
WHERE uo.voided = FALSE
GROUP BY 
    ul.location_id,
    ul.location_code,
    UPPER(TRIM(ul.location_name)),
    up.product_id,
    up.normalized_name,
    uc.category_name;

-- Indexes for mv_product_location_sales
CREATE INDEX idx_mv_prod_loc_location ON mv_product_location_sales(location_code);
CREATE INDEX idx_mv_prod_loc_product ON mv_product_location_sales(product);
CREATE INDEX idx_mv_prod_loc_category ON mv_product_location_sales(category_name);
CREATE INDEX idx_mv_prod_loc_location_revenue ON mv_product_location_sales(location_code, total_revenue DESC);

-- 1.4 Hourly Sales Pattern (Time-Based Queries)
-- Optimizes: "What were hourly sales on the 3rd?", "Show me peak hours for each location"
DROP MATERIALIZED VIEW IF EXISTS mv_hourly_sales_pattern CASCADE;
CREATE MATERIALIZED VIEW mv_hourly_sales_pattern AS
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
GROUP BY uo.order_date, EXTRACT(HOUR FROM uo.order_timestamp), EXTRACT(DOW FROM uo.order_timestamp), 
         ul.location_id, ul.location_code, ul.location_name, uo.order_type, uo.source_system;

-- Indexes for mv_hourly_sales_pattern
CREATE INDEX idx_mv_hourly_date ON mv_hourly_sales_pattern(order_date);
CREATE INDEX idx_mv_hourly_hour ON mv_hourly_sales_pattern(order_hour);
CREATE INDEX idx_mv_hourly_location ON mv_hourly_sales_pattern(location_code);
CREATE INDEX idx_mv_hourly_date_hour ON mv_hourly_sales_pattern(order_date, order_hour);
CREATE INDEX idx_mv_hourly_location_hour ON mv_hourly_sales_pattern(location_code, order_hour);

-- 1.5 Payment Methods Summary (Payment Analysis)
-- Optimizes: "Which payment methods are most popular?"
DROP MATERIALIZED VIEW IF EXISTS mv_payment_methods_by_source CASCADE;
CREATE MATERIALIZED VIEW mv_payment_methods_by_source AS
SELECT 
    up.source_system,
    up.payment_type,
    up.card_brand,
    COUNT(*) as transaction_count,
    SUM(up.amount_cents) / 100.0 as total_amount,
    AVG(up.amount_cents) / 100.0 as avg_transaction_amount,
    MIN(up.amount_cents) / 100.0 as min_amount,
    MAX(up.amount_cents) / 100.0 as max_amount
FROM unified_payments up
WHERE up.payment_type IS NOT NULL
GROUP BY up.source_system, up.payment_type, up.card_brand;

-- Indexes for mv_payment_methods_by_source
CREATE INDEX idx_mv_payment_type ON mv_payment_methods_by_source(payment_type);
CREATE INDEX idx_mv_payment_source ON mv_payment_methods_by_source(source_system);
CREATE INDEX idx_mv_payment_count ON mv_payment_methods_by_source(transaction_count DESC);

-- 1.6 Order Type Performance (Channel Analysis)
-- Optimizes: "Compare delivery vs dine-in revenue", "Average order value by channel"
DROP MATERIALIZED VIEW IF EXISTS mv_order_type_performance CASCADE;
CREATE MATERIALIZED VIEW mv_order_type_performance AS
SELECT 
    uo.order_type,
    uo.source_system,
    ul.location_code,
    COUNT(DISTINCT uo.order_id) as order_count,
    SUM(uo.total_cents) / 100.0 as gross_revenue,
    SUM(uo.commission_cents) / 100.0 as commissions,
    SUM(COALESCE(uo.merchant_payout_cents, uo.total_cents - COALESCE(uo.commission_cents, 0))) / 100.0 as net_revenue,
    AVG(uo.total_cents) / 100.0 as avg_order_value,
    SUM(uo.tip_cents) / 100.0 as total_tips,
    AVG(uo.tip_cents) / 100.0 as avg_tip
FROM unified_orders uo
JOIN unified_locations ul ON uo.unified_location_id = ul.location_id
WHERE uo.voided = FALSE
GROUP BY uo.order_type, uo.source_system, ul.location_code;

-- Indexes for mv_order_type_performance
CREATE INDEX idx_mv_order_type_type ON mv_order_type_performance(order_type);
CREATE INDEX idx_mv_order_type_source ON mv_order_type_performance(source_system);
CREATE INDEX idx_mv_order_type_location ON mv_order_type_performance(location_code);
CREATE INDEX idx_mv_order_type_revenue ON mv_order_type_performance(net_revenue DESC);

-- 1.7 Category Sales Summary (Category Analysis)
-- Optimizes: "Which category generates the most revenue?", "Beverage sales across all locations"
DROP MATERIALIZED VIEW IF EXISTS mv_category_sales_summary CASCADE;
CREATE MATERIALIZED VIEW mv_category_sales_summary AS
SELECT 
    uc.category_id,
    uc.category_name,
    COUNT(DISTINCT up.product_id) as product_count,
    COUNT(DISTINCT uoi.order_id) as order_count,
    COUNT(DISTINCT uo.unified_location_id) as location_count,
    SUM(uoi.quantity) as total_quantity_sold,
    SUM(uoi.total_price_cents) / 100.0 as total_revenue,
    AVG(uoi.unit_price_cents) / 100.0 as avg_product_price
FROM unified_order_items uoi
JOIN unified_products up ON uoi.unified_product_id = up.product_id
JOIN unified_categories uc ON up.category_id = uc.category_id
JOIN unified_orders uo ON uoi.order_id = uo.order_id
WHERE uo.voided = FALSE
GROUP BY uc.category_id, uc.category_name;

-- Indexes for mv_category_sales_summary
CREATE INDEX idx_mv_category_revenue ON mv_category_sales_summary(total_revenue DESC);
CREATE INDEX idx_mv_category_name ON mv_category_sales_summary(category_name);

-- 1.8 Location Performance Summary (Location Comparisons)
-- Optimizes: "Which location had the highest sales?", "Compare sales between Downtown and Airport"
DROP MATERIALIZED VIEW IF EXISTS mv_location_performance CASCADE;

CREATE MATERIALIZED VIEW mv_location_performance AS
SELECT 
    ul.location_id,
    ul.location_code,
    UPPER(TRIM(ul.location_name)) AS location_name,
    COUNT(DISTINCT uo.order_id) AS order_count,
    SUM(uo.total_cents) / 100.0 AS total_revenue,
    SUM(uo.subtotal_cents) / 100.0 AS total_subtotal,
    SUM(uo.tax_cents) / 100.0 AS total_tax,
    SUM(uo.tip_cents) / 100.0 AS total_tips,
    AVG(uo.total_cents) / 100.0 AS avg_order_value,
    COUNT(DISTINCT uo.order_id) FILTER (WHERE uo.source_system = 'doordash') AS doordash_orders,
    COUNT(DISTINCT uo.order_id) FILTER (WHERE uo.source_system != 'doordash') AS pos_orders,
    SUM(uo.total_cents) FILTER (WHERE uo.source_system = 'doordash') / 100.0 AS doordash_revenue,
    SUM(uo.total_cents) FILTER (WHERE uo.source_system != 'doordash') / 100.0 AS pos_revenue
FROM unified_orders uo
JOIN unified_locations ul 
  ON uo.unified_location_id = ul.location_id
WHERE uo.voided = FALSE
GROUP BY 
    ul.location_id,
    ul.location_code,
    UPPER(TRIM(ul.location_name));

-- Indexes for mv_location_performance
CREATE INDEX idx_mv_location_code ON mv_location_performance(location_code);
CREATE INDEX idx_mv_location_revenue ON mv_location_performance(total_revenue DESC);

-- =====================================================
-- 2. STRATEGIC COMPOSITE INDEXES (High Priority)
-- =====================================================

-- 2.1 Orders Table - Date + Location + Source (Most Common Pattern)
CREATE INDEX IF NOT EXISTS idx_orders_date_location_source_voided 
ON unified_orders(order_date, unified_location_id, source_system) 
WHERE voided = FALSE;

-- 2.2 Orders Table - Order Type + Date (Channel Comparisons)
CREATE INDEX IF NOT EXISTS idx_orders_type_date_voided 
ON unified_orders(order_type, order_date) 
WHERE voided = FALSE;

-- 2.3 Orders Table - Source + Date (Source System Queries)
CREATE INDEX IF NOT EXISTS idx_orders_source_date_voided 
ON unified_orders(source_system, order_date) 
WHERE voided = FALSE;

-- 2.4 Orders Table - Timestamp + Location (Hourly Patterns)
CREATE INDEX IF NOT EXISTS idx_orders_timestamp_location_voided 
ON unified_orders(order_timestamp, unified_location_id) 
WHERE voided = FALSE;

-- 2.5 Order Items - Product + Order (Product Analysis)
CREATE INDEX IF NOT EXISTS idx_order_items_product_order 
ON unified_order_items(unified_product_id, order_id) 
INCLUDE (quantity, total_price_cents, category_name);

-- 2.6 Order Items - Category + Source (Category by Source)
CREATE INDEX IF NOT EXISTS idx_order_items_category_source 
ON unified_order_items(category_name, source_system) 
INCLUDE (quantity, total_price_cents);

-- 2.7 Payments - Date + Type (Payment Analysis)
CREATE INDEX IF NOT EXISTS idx_payments_date_type 
ON unified_payments(payment_date, payment_type, source_system);

-- 2.8 Payments - Type + Source + Amount (Payment Methods)
CREATE INDEX IF NOT EXISTS idx_payments_type_source_amount 
ON unified_payments(payment_type, source_system, amount_cents);

-- =====================================================
-- 3. COVERING INDEXES (For Common SELECT Patterns)
-- =====================================================

-- 3.1 Orders - Covering Index for Daily Sales Queries
CREATE INDEX IF NOT EXISTS idx_orders_covering_daily 
ON unified_orders(order_date, unified_location_id, order_type, source_system) 
INCLUDE (total_cents, subtotal_cents, tax_cents, tip_cents, commission_cents, merchant_payout_cents)
WHERE voided = FALSE;

-- 3.2 Order Items - Covering Index for Product Queries
CREATE INDEX IF NOT EXISTS idx_order_items_covering_product 
ON unified_order_items(unified_product_id, order_id) 
INCLUDE (quantity, total_price_cents, unit_price_cents, category_name, product_name);

-- =====================================================
-- 4. PARTIAL INDEXES (For Filtered Queries)
-- =====================================================

-- 4.1 Active Orders Only (Most queries filter voided = FALSE)
CREATE INDEX IF NOT EXISTS idx_orders_active_date_location 
ON unified_orders(order_date, unified_location_id) 
WHERE voided = FALSE;

-- 4.2 DoorDash Orders Only (Common source system filter)
CREATE INDEX IF NOT EXISTS idx_orders_doordash_date 
ON unified_orders(order_date, unified_location_id) 
WHERE voided = FALSE AND source_system = 'doordash';

-- 4.3 Delivery Orders Only (Common order type filter)
CREATE INDEX IF NOT EXISTS idx_orders_delivery_date 
ON unified_orders(order_date, unified_location_id) 
WHERE voided = FALSE AND order_type = 'DELIVERY';

-- =====================================================
-- 5. STATISTICS UPDATE (For Query Planner)
-- =====================================================

-- Update table statistics for better query planning
ANALYZE unified_orders;
ANALYZE unified_order_items;
ANALYZE unified_payments;
ANALYZE unified_products;
ANALYZE unified_locations;
ANALYZE unified_categories;

-- =====================================================
-- 6. VIEW ALIASES (Backward Compatibility)
-- =====================================================
-- NOTE: Regular views (v_*) have been removed
-- =====================================================
-- This project uses ONLY materialized views (mv_*) for analytics.
-- Regular views were removed to simplify the architecture.
-- Query materialized views directly: mv_daily_sales_summary, mv_product_sales_summary, etc.

-- =====================================================
-- NOTES:
-- =====================================================
-- 1. Materialized views need to be refreshed periodically
--    Run: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales_summary;
--
-- 2. Refresh Strategy:
--    - Incremental: Only refresh last 24-48 hours
--    - Full: Refresh all data (slower but ensures consistency)
--    - Scheduled: Every 15 minutes during business hours
--
-- 3. Index Maintenance:
--    - REINDEX periodically for heavily updated tables
--    - Monitor index usage with pg_stat_user_indexes
--
-- 4. Query Performance:
--    - Materialized views: 10-50x faster than base views
--    - Composite indexes: 3-10x faster for filtered queries
--    - Covering indexes: Eliminate table lookups entirely
--
-- =====================================================

