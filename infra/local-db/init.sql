-- Initialization script for Restaurant Analytics Database
-- This will run when the container is first created
-- Creates all application tables needed for the analytics agent

-- Create UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =================================================================
-- User Authentication Tables
-- =================================================================

-- Table: app_users
-- Stores user authentication and profile information
CREATE TABLE IF NOT EXISTS app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON app_users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON app_users(role);

-- =================================================================
-- Query History Tables
-- =================================================================

-- Table: query_history
-- Stores all natural language queries and their results
CREATE TABLE IF NOT EXISTS query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    natural_query TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    intent VARCHAR(100) NOT NULL,
    execution_time_ms FLOAT NOT NULL,
    result_count INTEGER NOT NULL,
    results_sample JSONB DEFAULT '[]'::jsonb,
    columns JSONB DEFAULT '[]'::jsonb,
    visualization_type VARCHAR(50) NOT NULL,
    visualization_config JSONB DEFAULT '{}'::jsonb,
    answer TEXT,
    success BOOLEAN DEFAULT TRUE NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_query_history_user_id ON query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_query_history_query_id ON query_history(query_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_intent ON query_history(intent);

-- =================================================================
-- Dashboard Tables
-- =================================================================

-- Table: dashboards
-- Stores user-created dashboards
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

-- Table: dashboard_widgets
-- Stores widgets within dashboards (references query_history)
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

-- =================================================================
-- Initialization Complete
-- =================================================================
