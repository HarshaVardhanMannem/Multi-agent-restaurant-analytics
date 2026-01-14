"""
Query Service
Handles core query processing business logic
"""

import asyncio
import logging
from typing import Optional, Tuple

from ..config.constants import (
    MAX_EXECUTION_RETRIES,
    SQL_RETRY_DELAY_SECONDS,
    SQL_REGENERATION_DELAY_SECONDS,
    ERROR_MESSAGES,
    ERROR_SUGGESTIONS,
    HISTORY_RESULTS_SAMPLE_SIZE,
)
from ..config.settings import get_settings
from ..database import SupabasePool
from ..models.requests import QueryRequest
from ..models.responses import (
    QueryResponse,
    ClarificationResponse,
    ErrorResponse,
    VisualizationResponse,
)
from ..models.state import AgentState, QueryIntent, VisualizationType
from ..models.database_models import QueryHistoryCreate
from ..utils.formatters import format_results, get_result_columns
from ..utils.error_parser import parse_sql_error
from ..agents.answer_agent import answer_agent
from ..services.visualization_service import VisualizationService
from ..services.auth_service import QueryHistoryService

logger = logging.getLogger(__name__)


class QueryService:
    """Service for query processing business logic"""

    @staticmethod
    async def execute_sql_with_retry(
        query_id: str,
        sql: str,
        result: AgentState,
        max_retries: int = MAX_EXECUTION_RETRIES
    ) -> Tuple[Optional[list], float, Optional[str]]:
        """
        Execute SQL with automatic retry and regeneration on failure.
        
        Args:
            query_id: Unique query identifier
            sql: SQL query to execute
            result: Current agent state
            max_retries: Maximum number of retries
            
        Returns:
            Tuple of (query_results, execution_time_ms, updated_sql)
            Returns (None, 0, None) if all retries fail
        """
        settings = get_settings()
        execution_retry_count = 0
        query_results = None
        exec_time = 0.0
        current_sql = sql
        
        while execution_retry_count <= max_retries:
            try:
                query_results, exec_time = await SupabasePool.execute_query(
                    current_sql,
                    timeout=settings.max_query_timeout
                )
                # Success - break out of retry loop
                break
            except asyncio.CancelledError:
                logger.warning(f"[{query_id}] Query execution cancelled (likely due to shutdown/reload)")
                raise
            except Exception as e:
                execution_retry_count += 1
                logger.warning(f"[{query_id}] SQL execution failed (attempt {execution_retry_count}): {e}")
                
                # Try to regenerate SQL on first failure
                if execution_retry_count == 1:
                    logger.info(f"[{query_id}] Attempting to regenerate SQL after execution failure")
                    try:
                        # Update state with execution error for retry
                        result["execution_error"] = str(e)
                        result["retry_count"] = result.get("retry_count", 0)
                        
                        # Import here to avoid circular dependency
                        from ..agents.sql_generator import sql_generator_agent
                        from ..agents.sql_validator import sql_validator_agent
                        
                        # Regenerate SQL
                        retry_state = dict(result)
                        retry_state["agent_trace"] = list(result.get("agent_trace", []))
                        retry_state = sql_generator_agent(retry_state)
                        retry_state = sql_validator_agent(retry_state)
                        
                        # If new SQL is valid and different, try executing it
                        if retry_state.get("sql_validation_passed", False):
                            new_sql = retry_state.get("generated_sql", "")
                            if new_sql and new_sql != current_sql:
                                logger.info(f"[{query_id}] Retrying with corrected SQL")
                                current_sql = new_sql
                                result.update(retry_state)
                                execution_retry_count = 0  # Reset counter for new SQL
                                await asyncio.sleep(SQL_REGENERATION_DELAY_SECONDS)
                                continue  # Retry with new SQL
                    except Exception as retry_error:
                        logger.error(f"[{query_id}] Error during SQL regeneration: {retry_error}")
                
                # If we've exhausted retries, raise the error
                if execution_retry_count > max_retries:
                    raise
                else:
                    # Log retry attempt and wait before retrying same SQL
                    logger.info(f"[{query_id}] Retrying SQL execution ({execution_retry_count}/{max_retries})")
                    await asyncio.sleep(SQL_RETRY_DELAY_SECONDS)
        
        return query_results, exec_time, current_sql

    @staticmethod
    def create_clarification_response(
        result: AgentState,
        original_query: str
    ) -> ClarificationResponse:
        """
        Create a clarification response when query is ambiguous.
        
        Args:
            result: Agent state with clarification info
            original_query: Original user query
            
        Returns:
            ClarificationResponse
        """
        suggestions = []
        intent = result.get("query_intent")
        
        if intent == QueryIntent.SALES_ANALYSIS:
            suggestions.extend([
                "What time period are you interested in?",
                "Which location do you want to analyze?",
                "Do you want total sales or a breakdown?"
            ])
        elif intent == QueryIntent.PRODUCT_ANALYSIS:
            suggestions.extend([
                "Top selling by quantity or revenue?",
                "For a specific time period?",
                "For a specific category?"
            ])
        
        return ClarificationResponse(
            success=True,
            clarification_needed=True,
            question=result.get("clarification_question", "Could you please clarify your query?"),
            suggestions=suggestions[:3],
            original_query=original_query,
            detected_intent=result.get("query_intent")
        )

    @staticmethod
    def create_error_response(
        error_code: str,
        error: Optional[Exception] = None,
        details: Optional[dict] = None
    ) -> ErrorResponse:
        """
        Create an error response with user-friendly message.
        
        Args:
            error_code: Error code identifier
            error: Optional exception
            details: Optional additional details
            
        Returns:
            ErrorResponse
        """
        error_message = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["INTERNAL_ERROR"])
        
        # Parse SQL error for better messages
        if error and error_code == "SQL_EXECUTION_FAILED":
            user_message, suggestions = parse_sql_error(error)
            return ErrorResponse(
                success=False,
                error_code=error_code,
                error_message=user_message,
                details=details or {},
                suggestions=suggestions
            )
        
        # Get suggestions based on error code
        if error_code in ["SQL_GENERATION_FAILED", "NO_SQL_GENERATED"]:
            suggestions = ERROR_SUGGESTIONS["GENERIC"]
        elif error_code == "SHUTDOWN_IN_PROGRESS":
            suggestions = ERROR_SUGGESTIONS["SHUTDOWN"]
        elif error_code == "QUERY_CANCELLED":
            suggestions = ERROR_SUGGESTIONS["CANCELLED"]
        else:
            suggestions = ["Please try again", "Contact support if the issue persists"]
        
        return ErrorResponse(
            success=False,
            error_code=error_code,
            error_message=error_message,
            details=details or {},
            suggestions=suggestions
        )

    @staticmethod
    async def process_non_streaming_query(
        query_id: str,
        result: AgentState,
        request: QueryRequest,
        sql: str,
        formatted_results: list,
        columns: list[str],
        exec_time: float,
        user_id: Optional[str] = None
    ) -> QueryResponse:
        """
        Process query in non-streaming mode (traditional response).
        
        Args:
            query_id: Unique query identifier
            result: Agent state
            request: Original request
            sql: Generated SQL
            formatted_results: Query results
            columns: Column names
            exec_time: Execution time
            user_id: Optional user ID
            
        Returns:
            QueryResponse
        """
        # Generate answer first
        answer_state = dict(result)
        answer_state["agent_trace"] = list(result.get("agent_trace", []))
        answer_state = answer_agent(answer_state)
        
        generated_answer = answer_state.get(
            "generated_answer",
            f"Query executed successfully. Found {len(formatted_results)} result(s)."
        )
        
        # Generate visualization if requested
        viz_response = None
        if request.include_chart:
            viz_response = VisualizationService.generate_visualization(
                query_id,
                answer_state,
                formatted_results,
                columns,
                request.query
            )
        else:
            viz_response = VisualizationResponse(type=VisualizationType.TABLE, config={})
        
        logger.info(
            f"[{query_id}] Query successful: {len(formatted_results)} rows in {exec_time:.2f}ms"
        )
        
        # Save query to history asynchronously
        if user_id:
            try:
                query_history_data = QueryHistoryCreate(
                    query_id=query_id,
                    user_id=user_id,
                    natural_query=request.query,
                    generated_sql=sql,
                    intent=result.get("query_intent", QueryIntent.UNKNOWN).value,
                    execution_time_ms=exec_time,
                    result_count=len(formatted_results),
                    results_sample=formatted_results[:HISTORY_RESULTS_SAMPLE_SIZE],
                    columns=columns,
                    visualization_type=viz_response.type.value if viz_response else VisualizationType.TABLE.value,
                    visualization_config=viz_response.config if viz_response else {},
                    answer=generated_answer,
                    success=True,
                    error_message=None
                )
                # Save asynchronously without blocking
                asyncio.create_task(QueryHistoryService.save_query(query_history_data))
            except Exception as e:
                logger.error(f"[{query_id}] Error saving query to history: {e}", exc_info=True)
        
        return QueryResponse(
            success=True,
            query_id=query_id,
            intent=result.get("query_intent", QueryIntent.UNKNOWN),
            sql=sql,
            explanation=result.get("sql_explanation", ""),
            results=formatted_results,
            result_count=len(formatted_results),
            columns=columns,
            visualization=viz_response,
            execution_time_ms=exec_time,
            total_processing_time_ms=result.get("total_processing_time_ms", 0),
            answer=generated_answer
        )
