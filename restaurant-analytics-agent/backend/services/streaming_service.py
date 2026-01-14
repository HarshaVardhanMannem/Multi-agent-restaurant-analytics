"""
Streaming Service
Handles Server-Sent Events (SSE) streaming for query responses
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

from ..config.constants import (
    ANSWER_STREAM_THRESHOLD,
    ANSWER_CHUNK_SIZE,
)
from ..models.requests import QueryRequest
from ..models.responses import QueryResponse, VisualizationResponse
from ..models.state import AgentState, QueryIntent, VisualizationType
from ..services.visualization_service import VisualizationService
from ..utils.viz_cache import VisualizationCache
from ..agents.answer_agent import answer_agent

logger = logging.getLogger(__name__)


class StreamingService:
    """Service for handling streaming query responses"""

    @staticmethod
    async def generate_stream(
        query_id: str,
        result: AgentState,
        request: QueryRequest,
        sql: str,
        formatted_results: list,
        columns: list[str],
        exec_time: float,
        user_id: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate Server-Sent Events stream for query response.
        
        Args:
            query_id: Unique query identifier
            result: Agent state with processing results
            request: Original query request
            sql: Generated SQL query
            formatted_results: Query results
            columns: Result column names
            exec_time: SQL execution time in ms
            user_id: Optional user ID for history saving
            
        Yields:
            SSE formatted strings
        """
        try:
            logger.info(f"[{query_id}] Streaming: Sending results immediately")
            
            # Step 1: Send SQL results immediately after validation and execution
            results_data = {
                "type": "results",
                "data": {
                    "query_id": query_id,
                    "intent": result.get("query_intent", QueryIntent.UNKNOWN).value,
                    "sql": sql,
                    "explanation": result.get("sql_explanation", ""),
                    "results": formatted_results,
                    "result_count": len(formatted_results),
                    "columns": columns,
                    "execution_time_ms": exec_time,
                }
            }
            results_json = json.dumps(results_data)
            logger.info(f"[{query_id}] Streaming: Yielding results event ({len(results_json)} bytes)")
            yield f"data: {results_json}\n\n"
            
            # Step 2: Generate answer and stream chunks immediately
            answer_state = dict(result)
            answer_state["agent_trace"] = list(result.get("agent_trace", []))
            
            # Generate answer only (decoupled from visualization)
            answer_state = answer_agent(answer_state)
            
            generated_answer = answer_state.get(
                "generated_answer",
                f"Query executed successfully. Found {len(formatted_results)} result(s)."
            )
            
            # Stream answer chunks if it's a long answer
            logger.info(f"[{query_id}] Streaming: Sending answer ({len(generated_answer)} chars)")
            if len(generated_answer) > ANSWER_STREAM_THRESHOLD:
                for i in range(0, len(generated_answer), ANSWER_CHUNK_SIZE):
                    chunk = generated_answer[i:i + ANSWER_CHUNK_SIZE]
                    chunk_data = {
                        "type": "answer_chunk",
                        "chunk": chunk
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
            else:
                # Send full answer if short
                chunk_data = {
                    "type": "answer_chunk",
                    "chunk": generated_answer
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
            
            # Step 3: Trigger visualization generation asynchronously
            viz_applicable = VisualizationService.should_generate_visualization(
                answer_state, request.include_chart
            )
            logger.info(f"[{query_id}] Visualization applicable: {viz_applicable}, include_chart: {request.include_chart}")
            
            if viz_applicable:
                # Mark visualization as pending
                await VisualizationCache.set_status(query_id, "pending")
                
                # Send visualization availability signal BEFORE starting async task
                viz_available_data = {
                    "type": "visualization_available",
                    "data": {
                        "query_id": query_id,
                        "status": "pending"
                    }
                }
                logger.info(f"[{query_id}] Streaming: Sending visualization_available event (pending)")
                yield f"data: {json.dumps(viz_available_data)}\n\n"
                
                # Start async task (fire and forget)
                asyncio.create_task(
                    VisualizationService.generate_and_cache_visualization(
                        query_id,
                        answer_state,
                        formatted_results,
                        columns,
                        request.query
                    )
                )
            else:
                # Visualization not applicable - send event to notify frontend
                await VisualizationCache.set_status(query_id, "not_applicable")
                viz_not_applicable_data = {
                    "type": "visualization_available",
                    "data": {
                        "query_id": query_id,
                        "status": "not_applicable"
                    }
                }
                logger.info(f"[{query_id}] Streaming: Sending visualization_available event (not_applicable)")
                yield f"data: {json.dumps(viz_not_applicable_data)}\n\n"
            
            # Step 4: Send complete response with all data
            complete_response = QueryResponse(
                success=True,
                query_id=query_id,
                intent=result.get("query_intent", QueryIntent.UNKNOWN),
                sql=sql,
                explanation=result.get("sql_explanation", ""),
                results=formatted_results,
                result_count=len(formatted_results),
                columns=columns,
                visualization=VisualizationResponse(type=VisualizationType.TABLE, config={}),  # Placeholder
                execution_time_ms=exec_time,
                total_processing_time_ms=result.get("total_processing_time_ms", 0),
                answer=generated_answer
            )
            
            logger.info(f"[{query_id}] Streaming: Sending complete event")
            complete_data = {
                "type": "complete",
                "response": complete_response.model_dump()
            }
            yield f"data: {json.dumps(complete_data)}\n\n"
            logger.info(f"[{query_id}] Streaming: Stream complete")
            
            # Step 5: Save query to history asynchronously
            if user_id:
                asyncio.create_task(
                    StreamingService._save_query_with_visualization(
                        query_id,
                        user_id,
                        request,
                        result,
                        sql,
                        formatted_results,
                        columns,
                        exec_time,
                        generated_answer,
                        viz_applicable
                    )
                )
                
        except Exception as e:
            logger.error(f"[{query_id}] Error in streaming generator: {e}", exc_info=True)
            error_data = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    @staticmethod
    async def _save_query_with_visualization(
        query_id: str,
        user_id: str,
        request: QueryRequest,
        result: AgentState,
        sql: str,
        formatted_results: list,
        columns: list[str],
        exec_time: float,
        generated_answer: str,
        viz_applicable: bool
    ) -> None:
        """
        Save query to history after waiting for visualization to complete.
        
        Args:
            query_id: Unique query identifier
            user_id: User ID
            request: Original request
            result: Agent state
            sql: Generated SQL
            formatted_results: Query results
            columns: Column names
            exec_time: Execution time
            generated_answer: Generated answer
            viz_applicable: Whether visualization was generated
        """
        try:
            from ..services.auth_service import QueryHistoryService
            from ..models.database_models import QueryHistoryCreate
            
            # Wait up to 10 seconds for visualization to be ready
            viz_type = VisualizationType.TABLE
            viz_config = {}
            
            if viz_applicable:
                cached_viz = await VisualizationService.wait_for_visualization(query_id)
                if cached_viz:
                    viz_type = VisualizationType(cached_viz.get("type", "table"))
                    viz_config = cached_viz.get("config", {})
                    # Include chart_js_config in visualization_config for persistence
                    if cached_viz.get("chart_js_config"):
                        viz_config["chart_js_config"] = cached_viz["chart_js_config"]
            
            query_history_data = QueryHistoryCreate(
                query_id=query_id,
                user_id=user_id,
                natural_query=request.query,
                generated_sql=sql,
                intent=result.get("query_intent", QueryIntent.UNKNOWN).value,
                execution_time_ms=exec_time,
                result_count=len(formatted_results),
                results_sample=formatted_results[:10],
                columns=columns,
                visualization_type=viz_type.value,
                visualization_config=viz_config,
                answer=generated_answer,
                success=True,
                error_message=None
            )
            await QueryHistoryService.save_query(query_history_data)
        except Exception as e:
            logger.error(f"[{query_id}] Error saving query to history: {e}", exc_info=True)
