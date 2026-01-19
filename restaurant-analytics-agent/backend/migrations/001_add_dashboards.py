"""
Database Migration: Add Dashboard Tables
Creates dashboards and dashboard_widgets tables for dashboard builder feature
"""

import logging
from ..database import SupabasePool

logger = logging.getLogger(__name__)

# SQL for creating dashboards table
CREATE_DASHBOARDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dashboards_user_id ON dashboards(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_created_at ON dashboards(created_at DESC);
"""

# SQL for creating dashboard_widgets table
CREATE_DASHBOARD_WIDGETS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dashboard_widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    query_id VARCHAR(255) NOT NULL REFERENCES query_history(query_id) ON DELETE CASCADE,
    position INTEGER DEFAULT 0 NOT NULL,
    size VARCHAR(20) DEFAULT 'medium' NOT NULL CHECK (size IN ('small', 'medium', 'large', 'full')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_dashboard_id ON dashboard_widgets(dashboard_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_query_id ON dashboard_widgets(query_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_position ON dashboard_widgets(dashboard_id, position);
"""

# Combined migration SQL
MIGRATION_SQL = CREATE_DASHBOARDS_TABLE_SQL + "\n" + CREATE_DASHBOARD_WIDGETS_TABLE_SQL


async def run_migration():
    """
    Run the dashboard tables migration.
    Creates dashboards and dashboard_widgets tables if they don't exist.
    """
    try:
        logger.info("Running migration: 001_add_dashboards")
        
        await SupabasePool._ensure_connected()
        execution_time = await SupabasePool.execute_script(MIGRATION_SQL)
        
        logger.info(f"Migration 001_add_dashboards completed successfully in {execution_time}ms")
        return True
    except Exception as e:
        logger.error(f"Migration 001_add_dashboards failed: {str(e)}")
        raise


async def rollback_migration():
    """
    Rollback the dashboard tables migration.
    WARNING: This will delete all dashboards and widgets data.
    """
    try:
        logger.info("Rolling back migration: 001_add_dashboards")
        
        rollback_sql = """
        DROP TABLE IF EXISTS dashboard_widgets CASCADE;
        DROP TABLE IF EXISTS dashboards CASCADE;
        """
        
        await SupabasePool._ensure_connected()
        execution_time = await SupabasePool.execute_script(rollback_sql)
        
        logger.info(f"Migration 001_add_dashboards rolled back successfully in {execution_time}ms")
        return True
    except Exception as e:
        logger.error(f"Rollback of 001_add_dashboards failed: {str(e)}")
        raise


if __name__ == "__main__":
    import asyncio
    
    async def main():
        await run_migration()
    
    asyncio.run(main())
