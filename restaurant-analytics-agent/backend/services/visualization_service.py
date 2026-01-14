"""
Visualization Service
Handles visualization generation and caching logic
"""

import logging
from typing import Optional

from ..config.constants import (
    DEFAULT_VISUALIZATION_TITLES,
    MAX_QUERY_TITLE_LENGTH,
    VIZ_MAX_WAIT_ATTEMPTS,
    VIZ_WAIT_INTERVAL_SEC,
)
from ..database import SupabasePool
from ..models.responses import VisualizationResponse
from ..models.state import AgentState, VisualizationType
from ..utils.viz_cache import VisualizationCache
from ..visualization import generate_chart_config
from ..agents.visualization_agent import visualization_agent, is_visualization_applicable

logger = logging.getLogger(__name__)


class VisualizationService:
    """Service for visualization generation and management"""

    @staticmethod
    def should_generate_visualization(state: AgentState, include_chart: bool) -> bool:
        """
        Check if visualization should be generated for this query.
        
        Args:
            state: Current agent state with query results
            include_chart: Whether chart was requested by client
            
        Returns:
            True if visualization is applicable and requested
        """
        if not include_chart:
            return False
        
        return is_visualization_applicable(state)

    @staticmethod
    def update_viz_config_defaults(
        viz_config: dict,
        columns: list[str],
        user_query: str
    ) -> dict:
        """
        Update visualization config with better defaults based on actual results.
        
        Args:
            viz_config: Current visualization configuration
            columns: Result column names
            user_query: Original user query
            
        Returns:
            Updated viz config with defaults
        """
        if not viz_config:
            viz_config = {}
        
        # Set title from query if not set or if it's a default
        current_title = viz_config.get("title", "")
        if not current_title or current_title in DEFAULT_VISUALIZATION_TITLES:
            viz_config["title"] = (
                user_query[:MAX_QUERY_TITLE_LENGTH] + "..."
                if len(user_query) > MAX_QUERY_TITLE_LENGTH
                else user_query
            )
        
        # Auto-detect axes from columns if not set
        if columns and not viz_config.get("x_axis"):
            viz_config["x_axis"] = columns[0]
        if len(columns) > 1 and not viz_config.get("y_axis"):
            viz_config["y_axis"] = columns[1]
        
        return viz_config

    @staticmethod
    def generate_visualization(
        query_id: str,
        state: AgentState,
        formatted_results: list,
        columns: list[str],
        user_query: str
    ) -> VisualizationResponse:
        """
        Generate visualization response synchronously.
        
        Args:
            query_id: Unique query identifier
            state: Agent state with visualization config
            formatted_results: Query results
            columns: Result column names
            user_query: Original user query
            
        Returns:
            VisualizationResponse with type, config, and chart_js_config
        """
        # Run visualization agent
        viz_state = dict(state)
        viz_state["agent_trace"] = list(state.get("agent_trace", []))
        viz_state = visualization_agent(viz_state)
        
        viz_type = viz_state.get("visualization_type", VisualizationType.TABLE)
        viz_config = viz_state.get("visualization_config", {})
        
        # Skip if visualization type is NONE
        if viz_type == VisualizationType.NONE:
            logger.info(f"[{query_id}] Visualization not applicable, using table")
            return VisualizationResponse(type=VisualizationType.TABLE, config={})
        
        logger.info(
            f"[{query_id}] Visualization type selected: {viz_type.value if hasattr(viz_type, 'value') else viz_type}"
        )
        
        # Update config with defaults
        viz_config = VisualizationService.update_viz_config_defaults(
            viz_config, columns, user_query
        )
        
        # Generate chart config
        try:
            chart_config = generate_chart_config(formatted_results, viz_type, viz_config)
            logger.info(
                f"[{query_id}] Chart config generated: type={viz_type.value if hasattr(viz_type, 'value') else viz_type}, "
                f"has_config={'data' in chart_config if chart_config else False}"
            )
        except Exception as e:
            logger.error(f"[{query_id}] Error generating chart config: {e}", exc_info=True)
            # Fallback to table visualization on error
            chart_config = {
                "type": "table",
                "data": {"columns": columns, "rows": formatted_results},
                "options": {"title": viz_config.get("title", "Query Results")},
            }
            viz_type = VisualizationType.TABLE
        
        return VisualizationResponse(
            type=viz_type,
            config=dict(viz_config) if viz_config else {},
            chart_js_config=chart_config,
        )

    @staticmethod
    async def generate_and_cache_visualization(
        query_id: str,
        state: AgentState,
        formatted_results: list,
        columns: list[str],
        user_query: str
    ) -> None:
        """
        Generate visualization and store in cache (async workflow).
        
        Used in streaming mode where visualization is generated in background.
        
        Args:
            query_id: Unique query identifier
            state: Agent state
            formatted_results: Query results
            columns: Result column names
            user_query: Original user query
        """
        try:
            logger.info(f"[{query_id}] Starting async visualization generation")
            
            # Run visualization agent
            viz_state = dict(state)
            viz_state["agent_trace"] = list(state.get("agent_trace", []))
            viz_state = visualization_agent(viz_state)
            
            viz_type = viz_state.get("visualization_type", VisualizationType.TABLE)
            viz_config = viz_state.get("visualization_config", {})
            
            # Skip if visualization type is NONE
            if viz_type == VisualizationType.NONE:
                logger.info(f"[{query_id}] Visualization not applicable, skipping")
                await VisualizationCache.set_status(query_id, "not_applicable")
                return
            
            logger.info(
                f"[{query_id}] Visualization type selected: {viz_type.value if hasattr(viz_type, 'value') else viz_type}"
            )
            
            # Update config with defaults
            viz_config = VisualizationService.update_viz_config_defaults(
                viz_config, columns, user_query
            )
            
            # Generate chart config
            try:
                chart_config = generate_chart_config(formatted_results, viz_type, viz_config)
                logger.info(
                    f"[{query_id}] Chart config generated: type={viz_type.value if hasattr(viz_type, 'value') else viz_type}, "
                    f"has_config={'data' in chart_config if chart_config else False}"
                )
                
                # Store in cache
                await VisualizationCache.store(
                    query_id,
                    viz_type,
                    viz_config,
                    chart_config
                )
                await VisualizationCache.set_status(query_id, "ready")
                logger.info(f"[{query_id}] Visualization stored in cache and ready")
            except Exception as e:
                logger.error(f"[{query_id}] Error generating chart config: {e}", exc_info=True)
                await VisualizationCache.set_status(query_id, "error")
        except Exception as e:
            logger.error(f"[{query_id}] Error in async visualization generation: {e}", exc_info=True)
            await VisualizationCache.set_status(query_id, "error")

    @staticmethod
    async def get_visualization_from_cache_or_db(query_id: str) -> Optional[VisualizationResponse]:
        """
        Get visualization from cache or database as fallback.
        
        Args:
            query_id: Unique query identifier
            
        Returns:
            VisualizationResponse if found, None otherwise
        """
        # First check cache
        status = await VisualizationCache.get_status(query_id)
        viz_data = await VisualizationCache.get(query_id)
        
        # If found in cache, return it
        if viz_data:
            try:
                viz_type = VisualizationType(viz_data.get("type", "table"))
            except (ValueError, KeyError):
                viz_type = VisualizationType.TABLE
            
            return VisualizationResponse(
                type=viz_type,
                config=viz_data.get("config", {}),
                chart_js_config=viz_data.get("chart_js_config")
            )
        
        # If cache is empty but status exists, check database as fallback
        if status != "not_applicable":
            logger.info(f"[{query_id}] Cache miss, checking database for visualization")
            try:
                # Query database for saved visualization
                import json
                
                result, _ = await SupabasePool.execute_query(
                    """
                    SELECT visualization_type, visualization_config, results_sample, columns
                    FROM query_history
                    WHERE query_id = $1
                    LIMIT 1
                    """,
                    query_id
                )
                
                if result and result[0]:
                    row = result[0]
                    viz_config = row.get("visualization_config") or {}
                    
                    # Parse JSON string if needed (database may return string)
                    if isinstance(viz_config, str):
                        try:
                            viz_config = json.loads(viz_config) if viz_config else {}
                        except json.JSONDecodeError:
                            viz_config = {}
                    
                    # Check if chart_js_config is stored in visualization_config
                    chart_js_config = viz_config.get("chart_js_config")
                    
                    # If chart_js_config exists, restore to cache and return
                    if chart_js_config:
                        logger.info(f"[{query_id}] Found visualization in database, restoring to cache")
                        try:
                            viz_type = VisualizationType(row["visualization_type"])
                        except (ValueError, KeyError):
                            viz_type = VisualizationType.TABLE
                        
                        # Restore to cache for future requests
                        await VisualizationCache.store(
                            query_id,
                            viz_type,
                            {k: v for k, v in viz_config.items() if k != "chart_js_config"},
                            chart_js_config
                        )
                        await VisualizationCache.set_status(query_id, "ready")
                        
                        return VisualizationResponse(
                            type=viz_type,
                            config={k: v for k, v in viz_config.items() if k != "chart_js_config"},
                            chart_js_config=chart_js_config
                        )
            except Exception as e:
                logger.error(f"[{query_id}] Error fetching visualization from database: {e}")
        
        return None

    @staticmethod
    async def wait_for_visualization(query_id: str) -> Optional[dict]:
        """
        Wait for visualization to be ready (used in query history saving).
        
        Args:
            query_id: Unique query identifier
            
        Returns:
            Cached visualization data if ready, None if timeout or not applicable
        """
        for _ in range(VIZ_MAX_WAIT_ATTEMPTS):
            status = await VisualizationCache.get_status(query_id)
            if status in ("ready", "error", "not_applicable"):
                break
            
            import asyncio
            await asyncio.sleep(VIZ_WAIT_INTERVAL_SEC)
        
        return await VisualizationCache.get(query_id)
