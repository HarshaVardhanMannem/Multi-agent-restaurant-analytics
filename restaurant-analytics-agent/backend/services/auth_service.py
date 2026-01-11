"""
Authentication Service
Handles user registration, login, and token management
"""

import json
import logging
from typing import Any
from uuid import UUID

from ..database import SupabasePool
from ..models.database_models import (
    QueryHistoryCreate,
    QueryHistoryDetailResponse,
    QueryHistoryResponse,
    UserCreate,
    UserInDB,
    UserResponse,
    UserRole,
)
from ..utils.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service for user authentication operations"""
    
    @staticmethod
    async def create_user(user_data: UserCreate) -> UserResponse | None:
        """
        Create a new user in the database.
        Automatically initializes auth tables if they don't exist.
        
        Args:
            user_data: User registration data
            
        Returns:
            Created user or None if email already exists
        """
        try:
            # Try to check if user already exists (this will fail if table doesn't exist)
            try:
                existing, _ = await SupabasePool.execute_query(
                    "SELECT id FROM app_users WHERE email = $1",
                    user_data.email
                )
                if existing:
                    logger.warning(f"User with email {user_data.email} already exists")
                    return None
            except Exception as table_error:
                # Table doesn't exist, create it
                error_msg = str(table_error).lower()
                if "does not exist" in error_msg or "relation" in error_msg:
                    logger.info("Auth tables not found, initializing...")
                    from ..models.database_models import INIT_AUTH_TABLES_SQL
                    await SupabasePool.execute_query(INIT_AUTH_TABLES_SQL)
                    logger.info("Auth tables initialized successfully")
                else:
                    raise
            
            # Hash password
            hashed_password = get_password_hash(user_data.password)
            
            # Insert user
            result, _ = await SupabasePool.execute_query(
                """
                INSERT INTO app_users (email, full_name, hashed_password, role, is_active)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, email, full_name, role, is_active, created_at
                """,
                user_data.email,
                user_data.full_name,
                hashed_password,
                UserRole.USER.value,
                True
            )
            
            if result:
                user = result[0]
                return UserResponse(
                    id=user["id"],
                    email=user["email"],
                    full_name=user["full_name"],
                    role=UserRole(user["role"]),
                    is_active=user["is_active"],
                    created_at=user["created_at"]
                )
            return None
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    @staticmethod
    async def authenticate_user(email: str, password: str) -> UserInDB | None:
        """
        Authenticate a user by email and password.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User data if authenticated, None otherwise
        """
        try:
            result, _ = await SupabasePool.execute_query(
                """
                SELECT id, email, full_name, hashed_password, role, is_active, created_at, updated_at
                FROM app_users
                WHERE email = $1 AND is_active = true
                """,
                email
            )
            
            if not result:
                return None
            
            user_data = result[0]
            
            # Verify password
            if not verify_password(password, user_data["hashed_password"]):
                return None
            
            return UserInDB(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=user_data["hashed_password"],
                role=UserRole(user_data["role"]),
                is_active=user_data["is_active"],
                created_at=user_data["created_at"],
                updated_at=user_data["updated_at"]
            )
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    @staticmethod
    async def get_user_by_id(user_id: UUID) -> UserResponse | None:
        """
        Get user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            User data or None if not found
        """
        try:
            result, _ = await SupabasePool.execute_query(
                """
                SELECT id, email, full_name, role, is_active, created_at
                FROM app_users
                WHERE id = $1 AND is_active = true
                """,
                str(user_id)
            )
            
            if not result:
                return None
            
            user_data = result[0]
            return UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                role=UserRole(user_data["role"]),
                is_active=user_data["is_active"],
                created_at=user_data["created_at"]
            )
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None


class QueryHistoryService:
    """Service for query history operations"""
    
    @staticmethod
    async def save_query(query_data: QueryHistoryCreate) -> str | None:
        """
        Save a query to history.
        
        Args:
            query_data: Query history data
            
        Returns:
            Query ID if saved successfully
        """
        try:
            # Limit results sample to first 10 rows
            results_sample = query_data.results_sample[:10] if query_data.results_sample else []
            
            result, _ = await SupabasePool.execute_query(
                """
                INSERT INTO query_history (
                    query_id, user_id, natural_query, generated_sql, intent,
                    execution_time_ms, result_count, results_sample, columns,
                    visualization_type, visualization_config, answer, success, error_message
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11::jsonb, $12, $13, $14)
                RETURNING query_id
                """,
                query_data.query_id,
                str(query_data.user_id) if query_data.user_id else None,
                query_data.natural_query,
                query_data.generated_sql,
                query_data.intent,
                query_data.execution_time_ms,
                query_data.result_count,
                json.dumps(results_sample),
                json.dumps(query_data.columns),
                query_data.visualization_type,
                json.dumps(query_data.visualization_config),
                query_data.answer,
                query_data.success,
                query_data.error_message
            )
            
            if result:
                logger.info(f"Query saved to history: {query_data.query_id}")
                return result[0]["query_id"]
            return None
            
        except Exception as e:
            # Log error but don't fail the main request
            logger.error(f"Error saving query to history: {e}")
            return None
    
    @staticmethod
    async def get_user_queries(
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> list[QueryHistoryResponse]:
        """
        Get query history for a user.
        
        Args:
            user_id: User UUID
            limit: Maximum number of queries to return
            offset: Number of queries to skip
            
        Returns:
            List of query history entries
        """
        try:
            result, _ = await SupabasePool.execute_query(
                """
                SELECT id, query_id, user_id, natural_query, generated_sql, intent,
                       execution_time_ms, result_count, visualization_type, answer,
                       success, created_at
                FROM query_history
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                str(user_id),
                limit,
                offset
            )
            
            return [
                QueryHistoryResponse(
                    id=row["id"],
                    query_id=row["query_id"],
                    user_id=row["user_id"],
                    natural_query=row["natural_query"],
                    generated_sql=row["generated_sql"],
                    intent=row["intent"],
                    execution_time_ms=row["execution_time_ms"],
                    result_count=row["result_count"],
                    visualization_type=row["visualization_type"],
                    answer=row["answer"],
                    success=row["success"],
                    created_at=row["created_at"]
                )
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Error getting user queries: {e}")
            return []
    
    @staticmethod
    async def get_user_queries_with_results(
        user_id: UUID,
        limit: int = 20
    ) -> list[QueryHistoryDetailResponse]:
        """
        Get query history with full results for restoring widgets.
        
        Args:
            user_id: User UUID
            limit: Maximum number of queries to return
            
        Returns:
            List of detailed query history entries with results
        """
        try:
            result, _ = await SupabasePool.execute_query(
                """
                SELECT id, query_id, user_id, natural_query, generated_sql, intent,
                       execution_time_ms, result_count, results_sample, columns,
                       visualization_type, visualization_config, answer, success, created_at
                FROM query_history
                WHERE user_id = $1 AND success = true
                ORDER BY created_at DESC
                LIMIT $2
                """,
                str(user_id),
                limit
            )
            
            responses = []
            for row in result:
                # Parse JSONB fields that may come back as strings
                results_sample = row["results_sample"]
                if isinstance(results_sample, str):
                    results_sample = json.loads(results_sample) if results_sample else []
                
                columns = row["columns"]
                if isinstance(columns, str):
                    columns = json.loads(columns) if columns else []
                
                visualization_config = row["visualization_config"]
                if isinstance(visualization_config, str):
                    visualization_config = json.loads(visualization_config) if visualization_config else {}
                
                responses.append(QueryHistoryDetailResponse(
                    id=row["id"],
                    query_id=row["query_id"],
                    user_id=row["user_id"],
                    natural_query=row["natural_query"],
                    generated_sql=row["generated_sql"],
                    intent=row["intent"],
                    execution_time_ms=row["execution_time_ms"],
                    result_count=row["result_count"],
                    results_sample=results_sample or [],
                    columns=columns or [],
                    visualization_type=row["visualization_type"],
                    visualization_config=visualization_config or {},
                    answer=row["answer"],
                    success=row["success"],
                    created_at=row["created_at"]
                ))
            
            return responses
            
        except Exception as e:
            logger.error(f"Error getting user queries with results: {e}")
            return []

    @staticmethod
    async def get_query_by_id(query_id: str) -> QueryHistoryDetailResponse | None:
        """
        Get a specific query by ID.
        
        Args:
            query_id: Query UUID string
            
        Returns:
            Query history detail or None if not found
        """
        try:
            result, _ = await SupabasePool.execute_query(
                """
                SELECT id, query_id, user_id, natural_query, generated_sql, intent,
                       execution_time_ms, result_count, results_sample, columns,
                       visualization_type, visualization_config, answer, success, created_at
                FROM query_history
                WHERE query_id = $1
                """,
                query_id
            )
            
            if not result:
                return None
            
            row = result[0]
            
            # Parse JSONB fields that may come back as strings
            results_sample = row["results_sample"]
            if isinstance(results_sample, str):
                results_sample = json.loads(results_sample) if results_sample else []
            
            columns = row["columns"]
            if isinstance(columns, str):
                columns = json.loads(columns) if columns else []
            
            visualization_config = row["visualization_config"]
            if isinstance(visualization_config, str):
                visualization_config = json.loads(visualization_config) if visualization_config else {}
            
            return QueryHistoryDetailResponse(
                id=row["id"],
                query_id=row["query_id"],
                user_id=row["user_id"],
                natural_query=row["natural_query"],
                generated_sql=row["generated_sql"],
                intent=row["intent"],
                execution_time_ms=row["execution_time_ms"],
                result_count=row["result_count"],
                results_sample=results_sample or [],
                columns=columns or [],
                visualization_type=row["visualization_type"],
                visualization_config=visualization_config or {},
                answer=row["answer"],
                success=row["success"],
                created_at=row["created_at"]
            )
            
        except Exception as e:
            logger.error(f"Error getting query by ID: {e}")
            return None
    
    @staticmethod
    async def get_recent_queries(limit: int = 20) -> list[QueryHistoryResponse]:
        """
        Get recent queries (for admin or public view).
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of recent query history entries
        """
        try:
            result, _ = await SupabasePool.execute_query(
                """
                SELECT id, query_id, user_id, natural_query, generated_sql, intent,
                       execution_time_ms, result_count, visualization_type, answer,
                       success, created_at
                FROM query_history
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit
            )
            
            return [
                QueryHistoryResponse(
                    id=row["id"],
                    query_id=row["query_id"],
                    user_id=row["user_id"],
                    natural_query=row["natural_query"],
                    generated_sql=row["generated_sql"],
                    intent=row["intent"],
                    execution_time_ms=row["execution_time_ms"],
                    result_count=row["result_count"],
                    visualization_type=row["visualization_type"],
                    answer=row["answer"],
                    success=row["success"],
                    created_at=row["created_at"]
                )
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent queries: {e}")
            return []
    
    @staticmethod
    async def delete_query(query_id: str, user_id: UUID) -> bool:
        """
        Delete a query from history.
        
        Args:
            query_id: Query UUID string
            user_id: User UUID to verify ownership
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # First verify the query exists and belongs to the user
            result, _ = await SupabasePool.execute_query(
                """
                SELECT user_id FROM query_history
                WHERE query_id = $1
                """,
                query_id
            )
            
            if not result:
                logger.warning(f"Query not found: {query_id}")
                return False
            
            query_user_id = result[0]["user_id"]
            
            # Check ownership (user_id can be None for unauthenticated queries)
            # Normalize both to strings for comparison (database might return UUID object or string)
            if query_user_id:
                query_user_id_str = str(query_user_id)
                user_id_str = str(user_id)
                if query_user_id_str != user_id_str:
                    logger.warning(f"User {user_id} attempted to delete query {query_id} owned by {query_user_id}")
                    return False
            
            # Delete the query
            _, _ = await SupabasePool.execute_query(
                """
                DELETE FROM query_history
                WHERE query_id = $1
                """,
                query_id
            )
            
            logger.info(f"Query deleted from history: {query_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting query: {e}")
            return False