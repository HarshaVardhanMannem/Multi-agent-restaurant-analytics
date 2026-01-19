-- Add performance indexes for dashboard queries
-- This migration optimizes dashboard and widget queries

-- Index for dashboard widgets by dashboard_id (used in JOINs)
CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_dashboard_id 
ON dashboard_widgets(dashboard_id);

-- Index for dashboard widgets by query_id (used in JOINs with query_history)
CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_query_id 
ON dashboard_widgets(query_id);

-- Composite index for user dashboards ordered by update time
CREATE INDEX IF NOT EXISTS idx_dashboards_user_updated 
ON dashboards(user_id, updated_at DESC);

-- Index for query history lookups by user
CREATE INDEX IF NOT EXISTS idx_query_history_user_id 
ON query_history(user_id, created_at DESC);

-- Composite index for dashboard-query JOINs (most common operation)
CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_dashboard_query 
ON dashboard_widgets(dashboard_id, query_id);

COMMENT ON INDEX idx_dashboard_widgets_dashboard_id IS 'Optimizes widget queries by dashboard';
COMMENT ON INDEX idx_dashboard_widgets_query_id IS 'Optimizes widget-query JOINs';
COMMENT ON INDEX idx_dashboards_user_updated IS 'Optimizes user dashboard list with sorting';
COMMENT ON INDEX idx_query_history_user_id IS 'Optimizes query history lookups';
COMMENT ON INDEX idx_dashboard_widgets_dashboard_query IS 'Optimizes dashboard widget detail queries';
