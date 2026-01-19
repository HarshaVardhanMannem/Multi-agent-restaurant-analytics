"""
Dashboard Service
Handles dashboard and widget CRUD operations
"""

import json
import logging
from typing import Any
from uuid import UUID

from ..database import SupabasePool
from ..models.database_models import (
    DashboardResponse,
    DashboardDetailResponse,
    WidgetResponse,
    QueryHistoryDetailResponse,
)

logger = logging.getLogger(__name__)

# Constants
MAX_WIDGETS_PER_DASHBOARD = 12


class DashboardService:
    """Service for dashboard and widget management"""
    
    @staticmethod
    async def create_dashboard(
        user_id: UUID,
        name: str,
        description: str | None = None
    ) -> DashboardResponse:
        """
        Create a new dashboard for a user.
        
        Args:
            user_id: User ID
            name: Dashboard name
            description: Optional dashboard description
            
        Returns:
            Created dashboard
        """
        try:
            sql = """
            INSERT INTO dashboards (user_id, name, description)
            VALUES ($1, $2, $3)
            RETURNING id, user_id, name, description, is_public, created_at, updated_at
            """
            
            results, _ = await SupabasePool.execute_query(
                sql,
                str(user_id),
                name,
                description
            )
            
            if not results:
                raise Exception("Failed to create dashboard")
            
            dashboard = results[0]
            return DashboardResponse(
                id=dashboard["id"],
                user_id=dashboard["user_id"],
                name=dashboard["name"],
                description=dashboard["description"],
                is_public=dashboard["is_public"],
                widget_count=0,
                created_at=dashboard["created_at"],
                updated_at=dashboard["updated_at"]
            )
        except Exception as e:
            logger.error(f"Error creating dashboard: {str(e)}")
            raise
    
    @staticmethod
    async def get_user_dashboards(
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> list[DashboardResponse]:
        """
        Get all dashboards for a user with widget counts.
        
        Args:
            user_id: User ID
            limit: Maximum number of dashboards to return
            offset: Number of dashboards to skip
            
        Returns:
            List of user's dashboards with widget counts
        """
        try:
            sql = """
            SELECT 
                d.id,
                d.user_id,
                d.name,
                d.description,
                d.is_public,
                d.created_at,
                d.updated_at,
                COUNT(dw.id) as widget_count
            FROM dashboards d
            LEFT JOIN dashboard_widgets dw ON d.id = dw.dashboard_id
            WHERE d.user_id = $1
            GROUP BY d.id, d.user_id, d.name, d.description, d.is_public, d.created_at, d.updated_at
            ORDER BY d.updated_at DESC
            LIMIT $2 OFFSET $3
            """
            
            results, _ = await SupabasePool.execute_query(
                sql,
                str(user_id),
                limit,
                offset
            )
            
            return [
                DashboardResponse(
                    id=row["id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    description=row["description"],
                    is_public=row["is_public"],
                    widget_count=row["widget_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error fetching user dashboards: {str(e)}")
            raise
    
    @staticmethod
    async def get_dashboard_detail(
        dashboard_id: UUID,
        user_id: UUID
    ) -> DashboardDetailResponse | None:
        """
        Get dashboard details with all widgets and their query data.
        
        Args:
            dashboard_id: Dashboard ID
            user_id: User ID (for authorization)
            
        Returns:
            Dashboard with widgets or None if not found/unauthorized
        """
        try:
            # Get dashboard
            dashboard_sql = """
            SELECT id, user_id, name, description, is_public, created_at, updated_at
            FROM dashboards
            WHERE id = $1 AND user_id = $2
            """
            
            dashboard_results, _ = await SupabasePool.execute_query(
                dashboard_sql,
                str(dashboard_id),
                str(user_id)
            )
            
            if not dashboard_results:
                return None
            
            dashboard = dashboard_results[0]
            
            # Get widgets with query data
            widgets_sql = """
            SELECT 
                dw.id,
                dw.dashboard_id,
                dw.query_id,
                dw.position,
                dw.size,
                dw.created_at,
                qh.id as query_history_id,
                qh.user_id as query_user_id,
                qh.natural_query,
                qh.generated_sql,
                qh.intent,
                qh.execution_time_ms,
                qh.result_count,
                qh.results_sample,
                qh.columns,
                qh.visualization_type,
                qh.visualization_config,
                qh.answer,
                qh.success,
                qh.created_at as query_created_at
            FROM dashboard_widgets dw
            JOIN query_history qh ON dw.query_id = qh.query_id
            WHERE dw.dashboard_id = $1
            ORDER BY dw.position ASC
            """
            
            widgets_results, _ = await SupabasePool.execute_query(
                widgets_sql,
                str(dashboard_id)
            )
            
            widgets = []
            for row in widgets_results:
                # Parse JSON fields if they are strings
                results_sample = row["results_sample"]
                if isinstance(results_sample, str):
                    results_sample = json.loads(results_sample) if results_sample else []
                
                columns = row["columns"]
                if isinstance(columns, str):
                    columns = json.loads(columns) if columns else []
                
                visualization_config = row["visualization_config"]
                if isinstance(visualization_config, str):
                    visualization_config = json.loads(visualization_config) if visualization_config else None
                
                query_data = QueryHistoryDetailResponse(
                    id=row["query_history_id"],
                    query_id=row["query_id"],
                    user_id=row["query_user_id"],
                    natural_query=row["natural_query"],
                    generated_sql=row["generated_sql"],
                    intent=row["intent"],
                    execution_time_ms=row["execution_time_ms"],
                    result_count=row["result_count"],
                    results_sample=results_sample,
                    columns=columns,
                    visualization_type=row["visualization_type"],
                    visualization_config=visualization_config,
                    answer=row["answer"],
                    success=row["success"],
                    created_at=row["query_created_at"]
                )
                
                widgets.append(WidgetResponse(
                    id=row["id"],
                    dashboard_id=row["dashboard_id"],
                    query_id=row["query_id"],
                    position=row["position"],
                    size=row["size"],
                    created_at=row["created_at"],
                    query_data=query_data
                ))
            
            return DashboardDetailResponse(
                id=dashboard["id"],
                user_id=dashboard["user_id"],
                name=dashboard["name"],
                description=dashboard["description"],
                is_public=dashboard["is_public"],
                widget_count=len(widgets),
                created_at=dashboard["created_at"],
                updated_at=dashboard["updated_at"],
                widgets=widgets
            )
        except Exception as e:
            logger.error(f"Error fetching dashboard detail: {str(e)}")
            raise
    
    @staticmethod
    async def update_dashboard(
        dashboard_id: UUID,
        user_id: UUID,
        name: str | None = None,
        description: str | None = None
    ) -> DashboardResponse | None:
        """
        Update dashboard metadata.
        
        Args:
            dashboard_id: Dashboard ID
            user_id: User ID (for authorization)
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            Updated dashboard or None if not found/unauthorized
        """
        try:
            # Build dynamic update query
            updates = []
            params = []
            param_idx = 1
            
            if name is not None:
                updates.append(f"name = ${param_idx}")
                params.append(name)
                param_idx += 1
            
            if description is not None:
                updates.append(f"description = ${param_idx}")
                params.append(description)
                param_idx += 1
            
            if not updates:
                # No updates provided, just fetch current
                dashboards = await DashboardService.get_user_dashboards(user_id, limit=1000)
                for d in dashboards:
                    if d.id == dashboard_id:
                        return d
                return None
            
            updates.append("updated_at = NOW()")
            updates_str = ", ".join(updates)
            
            params.extend([str(dashboard_id), str(user_id)])
            
            sql = f"""
            UPDATE dashboards
            SET {updates_str}
            WHERE id = ${param_idx} AND user_id = ${param_idx + 1}
            RETURNING id, user_id, name, description, is_public, created_at, updated_at
            """
            
            results, _ = await SupabasePool.execute_query(sql, *params)
            
            if not results:
                return None
            
            dashboard = results[0]
            
            # Get widget count
            count_sql = "SELECT COUNT(*) as count FROM dashboard_widgets WHERE dashboard_id = $1"
            count_results, _ = await SupabasePool.execute_query(count_sql, str(dashboard_id))
            widget_count = count_results[0]["count"] if count_results else 0
            
            return DashboardResponse(
                id=dashboard["id"],
                user_id=dashboard["user_id"],
                name=dashboard["name"],
                description=dashboard["description"],
                is_public=dashboard["is_public"],
                widget_count=widget_count,
                created_at=dashboard["created_at"],
                updated_at=dashboard["updated_at"]
            )
        except Exception as e:
            logger.error(f"Error updating dashboard: {str(e)}")
            raise
    
    @staticmethod
    async def delete_dashboard(
        dashboard_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete a dashboard (cascades to widgets).
        
        Args:
            dashboard_id: Dashboard ID
            user_id: User ID (for authorization)
            
        Returns:
            True if deleted, False if not found/unauthorized
        """
        try:
            sql = """
            DELETE FROM dashboards
            WHERE id = $1 AND user_id = $2
            """
            
            results, _ = await SupabasePool.execute_query(
                sql,
                str(dashboard_id),
                str(user_id)
            )
            
            # asyncpg doesn't return affected rows in results, so we check if dashboard existed
            check_sql = "SELECT COUNT(*) as count FROM dashboards WHERE id = $1"
            check_results, _ = await SupabasePool.execute_query(check_sql, str(dashboard_id))
            
            return check_results[0]["count"] == 0  # True if dashboard is gone
        except Exception as e:
            logger.error(f"Error deleting dashboard: {str(e)}")
            raise
    
    @staticmethod
    async def _get_widget_with_query_data(widget_id: UUID) -> WidgetResponse | None:
        """
        Helper method to fetch a single widget with its query data.
        
        Args:
            widget_id: Widget ID
            
        Returns:
            Widget with query data or None if not found
        """
        try:
            sql = """
            SELECT 
                dw.id,
                dw.dashboard_id,
                dw.query_id,
                dw.position,
                dw.size,
                dw.created_at,
                qh.id as query_history_id,
                qh.user_id as query_user_id,
                qh.natural_query,
                qh.generated_sql,
                qh.intent,
                qh.execution_time_ms,
                qh.result_count,
                qh.results_sample,
                qh.columns,
                qh.visualization_type,
                qh.visualization_config,
                qh.answer,
                qh.success,
                qh.created_at as query_created_at
            FROM dashboard_widgets dw
            JOIN query_history qh ON dw.query_id = qh.query_id
            WHERE dw.id = $1
            """
            
            results, _ = await SupabasePool.execute_query(sql, str(widget_id))
            
            if not results:
                return None
            
            row = results[0]
            
            # Parse JSON fields if they are strings
            results_sample = row["results_sample"]
            if isinstance(results_sample, str):
                results_sample = json.loads(results_sample) if results_sample else []
            
            columns = row["columns"]
            if isinstance(columns, str):
                columns = json.loads(columns) if columns else []
            
            visualization_config = row["visualization_config"]
            if isinstance(visualization_config, str):
                visualization_config = json.loads(visualization_config) if visualization_config else None
            
            query_data = QueryHistoryDetailResponse(
                id=row["query_history_id"],
                query_id=row["query_id"],
                user_id=row["query_user_id"],
                natural_query=row["natural_query"],
                generated_sql=row["generated_sql"],
                intent=row["intent"],
                execution_time_ms=row["execution_time_ms"],
                result_count=row["result_count"],
                results_sample=results_sample,
                columns=columns,
                visualization_type=row["visualization_type"],
                visualization_config=visualization_config,
                answer=row["answer"],
                success=row["success"],
                created_at=row["query_created_at"]
            )
            
            return WidgetResponse(
                id=row["id"],
                dashboard_id=row["dashboard_id"],
                query_id=row["query_id"],
                position=row["position"],
                size=row["size"],
                created_at=row["created_at"],
                query_data=query_data
            )
        except Exception as e:
            logger.error(f"Error fetching widget with query data: {str(e)}")
            return None
    
    @staticmethod
    async def add_widget(
        dashboard_id: UUID,
        user_id: UUID,
        query_id: str,
        position: int = 0,
        size: str = "medium"
    ) -> WidgetResponse | None:
        """
        Add a widget to a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            user_id: User ID (for authorization)
            query_id: Query ID from query history
            position: Widget position
            size: Widget size (small, medium, large, full)
            
        Returns:
            Created widget with query data or None if failed
        """
        try:
            # Lightweight ownership check - just verify dashboard exists and belongs to user
            ownership_sql = """
            SELECT id, 
                   (SELECT COUNT(*) FROM dashboard_widgets WHERE dashboard_id = $1) as widget_count
            FROM dashboards
            WHERE id = $1 AND user_id = $2
            """
            ownership_results, _ = await SupabasePool.execute_query(
                ownership_sql,
                str(dashboard_id),
                str(user_id)
            )
            
            if not ownership_results:
                raise ValueError("Dashboard not found or unauthorized")
            
            # Check widget limit
            widget_count = ownership_results[0]["widget_count"]
            if widget_count >= MAX_WIDGETS_PER_DASHBOARD:
                raise ValueError(f"Maximum {MAX_WIDGETS_PER_DASHBOARD} widgets per dashboard")
            
            # Verify query exists and belongs to user
            query_sql = """
            SELECT query_id FROM query_history
            WHERE query_id = $1 AND user_id = $2
            """
            query_results, _ = await SupabasePool.execute_query(query_sql, query_id, str(user_id))
            
            if not query_results:
                raise ValueError("Query not found or unauthorized")
            
            # Insert widget
            widget_sql = """
            INSERT INTO dashboard_widgets (dashboard_id, query_id, position, size)
            VALUES ($1, $2, $3, $4)
            RETURNING id, dashboard_id, query_id, position, size, created_at
            """
            
            widget_results, _ = await SupabasePool.execute_query(
                widget_sql,
                str(dashboard_id),
                query_id,
                position,
                size
            )
            
            if not widget_results:
                return None
            
            widget = widget_results[0]
            widget_id = widget["id"]
            
            # Update dashboard timestamp
            await SupabasePool.execute_query(
                "UPDATE dashboards SET updated_at = NOW() WHERE id = $1",
                str(dashboard_id)
            )
            
            # Fetch the widget with query data using optimized single query
            return await DashboardService._get_widget_with_query_data(widget_id)
        except Exception as e:
            logger.error(f"Error adding widget: {str(e)}")
            raise
    
    @staticmethod
    async def update_widget(
        widget_id: UUID,
        dashboard_id: UUID,
        user_id: UUID,
        position: int | None = None,
        size: str | None = None
    ) -> WidgetResponse | None:
        """
        Update widget position or size.
        
        Args:
            widget_id: Widget ID
            dashboard_id: Dashboard ID
            user_id: User ID (for authorization)
            position: New position (optional)
            size: New size (optional)
            
        Returns:
            Updated widget or None if not found/unauthorized
        """
        try:
            # Verify dashboard ownership
            dashboard = await DashboardService.get_dashboard_detail(dashboard_id, user_id)
            if not dashboard:
                return None
            
            # Build dynamic update query
            updates = []
            params = []
            param_idx = 1
            
            if position is not None:
                updates.append(f"position = ${param_idx}")
                params.append(position)
                param_idx += 1
            
            if size is not None:
                updates.append(f"size = ${param_idx}")
                params.append(size)
                param_idx += 1
            
            if not updates:
                # No updates, just return current widget
                for w in dashboard.widgets:
                    if w.id == widget_id:
                        return w
                return None
            
            updates_str = ", ".join(updates)
            params.extend([str(widget_id), str(dashboard_id)])
            
            sql = f"""
            UPDATE dashboard_widgets
            SET {updates_str}
            WHERE id = ${param_idx} AND dashboard_id = ${param_idx + 1}
            RETURNING id
            """
            
            results, _ = await SupabasePool.execute_query(sql, *params)
            
            if not results:
                return None
            
            # Update dashboard timestamp
            await SupabasePool.execute_query(
                "UPDATE dashboards SET updated_at = NOW() WHERE id = $1",
                str(dashboard_id)
            )
            
            # Get updated widget with query data
            updated_dashboard = await DashboardService.get_dashboard_detail(dashboard_id, user_id)
            if updated_dashboard:
                for w in updated_dashboard.widgets:
                    if w.id == widget_id:
                        return w
            
            return None
        except Exception as e:
            logger.error(f"Error updating widget: {str(e)}")
            raise
    
    @staticmethod
    async def delete_widget(
        widget_id: UUID,
        dashboard_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete a widget from a dashboard.
        
        Args:
            widget_id: Widget ID
            dashboard_id: Dashboard ID
            user_id: User ID (for authorization)
            
        Returns:
            True if deleted, False if not found/unauthorized
        """
        try:
            # Verify dashboard ownership
            dashboard = await DashboardService.get_dashboard_detail(dashboard_id, user_id)
            if not dashboard:
                return False
            
            sql = """
            DELETE FROM dashboard_widgets
            WHERE id = $1 AND dashboard_id = $2
            """
            
            results, _ = await SupabasePool.execute_query(
                sql,
                str(widget_id),
                str(dashboard_id)
            )
            
            # Update dashboard timestamp
            await SupabasePool.execute_query(
                "UPDATE dashboards SET updated_at = NOW() WHERE id = $1",
                str(dashboard_id)
            )
            
            return True
        except Exception as e:
            logger.error(f"Error deleting widget: {str(e)}")
            raise
