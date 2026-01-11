"""
Database Models for User Authentication and Query History
SQLAlchemy-style definitions for creating tables via raw SQL
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles for authorization"""
    USER = "user"
    ADMIN = "admin"


class UserBase(BaseModel):
    """Base user model"""
    email: str = Field(..., description="User email address")
    full_name: str | None = Field(None, description="User's full name")


class UserCreate(UserBase):
    """User creation request"""
    password: str = Field(..., min_length=8, description="User password (min 8 chars)")


class UserLogin(BaseModel):
    """User login request"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserInDB(UserBase):
    """User model as stored in database"""
    id: UUID
    hashed_password: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class UserResponse(UserBase):
    """User model for API responses (excludes sensitive data)"""
    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")


class QueryHistoryBase(BaseModel):
    """Base query history model"""
    natural_query: str = Field(..., description="Original natural language query")
    generated_sql: str = Field(..., description="Generated SQL query")
    intent: str = Field(..., description="Detected query intent")
    

class QueryHistoryCreate(QueryHistoryBase):
    """Query history creation model"""
    user_id: UUID | None = Field(None, description="User ID if authenticated")
    query_id: str = Field(..., description="Unique query identifier")
    execution_time_ms: float = Field(..., description="Query execution time in ms")
    result_count: int = Field(..., description="Number of results returned")
    results_sample: list[dict[str, Any]] = Field(default=[], description="Sample of results (first 10)")
    columns: list[str] = Field(default=[], description="Result column names")
    visualization_type: str = Field(..., description="Type of visualization used")
    visualization_config: dict[str, Any] = Field(default={}, description="Visualization configuration")
    answer: str | None = Field(None, description="Generated natural language answer")
    success: bool = Field(default=True, description="Whether query was successful")
    error_message: str | None = Field(None, description="Error message if failed")


class QueryHistoryResponse(QueryHistoryBase):
    """Query history response model"""
    id: UUID
    query_id: str
    user_id: UUID | None
    execution_time_ms: float
    result_count: int
    visualization_type: str
    answer: str | None
    success: bool
    created_at: datetime


class QueryHistoryDetailResponse(QueryHistoryResponse):
    """Detailed query history response including results sample"""
    results_sample: list[dict[str, Any]]
    columns: list[str]
    visualization_config: dict[str, Any]


# SQL for creating tables (to be executed on Supabase)
CREATE_USERS_TABLE_SQL = """
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
"""

CREATE_QUERY_HISTORY_TABLE_SQL = """
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
"""

# Combined SQL for initial setup
INIT_AUTH_TABLES_SQL = CREATE_USERS_TABLE_SQL + "\n" + CREATE_QUERY_HISTORY_TABLE_SQL
