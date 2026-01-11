"""
FastAPI Application
Main entry point for the Restaurant Analytics Agent API
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Annotated

from .config.settings import get_settings
from .config.schema_knowledge import SCHEMA_KNOWLEDGE
from .database import SupabasePool, init_database, close_database
from .agent_framework import get_agent_runner
from .agents.answer_agent import answer_agent
from .agents.visualization_agent import visualization_agent, is_visualization_applicable
from .visualization import generate_chart_config
from .utils.formatters import format_results, get_result_columns
from .utils.viz_cache import VisualizationCache
from .utils.error_parser import parse_sql_error
from .services.auth_service import QueryHistoryService
from .models.database_models import QueryHistoryCreate

from .models.requests import QueryRequest
from .models.responses import (
    QueryResponse,
    ClarificationResponse,
    ErrorResponse,
    VisualizationResponse,
    SchemaResponse,
    ExamplesResponse,
    ExampleQuery,
    HealthResponse
)
from .models.state import QueryIntent, VisualizationType
from .routes.auth import get_current_user_optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global flag to track shutdown state
_shutdown_in_progress = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown"""
    global _shutdown_in_progress
    
    # Startup
    logger.info("Starting Restaurant Analytics Agent API...")
    _shutdown_in_progress = False
    
    try:
        # Initialize database connection pool
        try:
            await init_database()
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.warning(f"Database connection failed during startup: {e}")
            logger.warning("Application will start, but database operations will fail until connection is established")
            # Don't raise - allow app to start, connection will be retried on first use
        
        # Initialize agent runner (preloads LLM config)
        get_agent_runner()
        logger.info("Agent runner initialized")
        
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Gracefully handle cancellation during startup
        logger.info("Startup cancelled")
        raise
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    _shutdown_in_progress = True
    logger.info("Shutting down...")
    try:
        await close_database()
    except Exception as e:
        logger.error(f"Error during database shutdown: {e}")
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Restaurant Analytics Agent API",
    description="Natural Language to SQL agent for restaurant analytics",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from .routes.auth import router as auth_router
app.include_router(auth_router)


# ==================== Main Query Endpoint ====================

@app.post("/api/query", response_model=None)
async def process_query(
    request: QueryRequest,
    authorization: Annotated[str | None, Header()] = None
):
    """
    Process a natural language query about restaurant data.
    
    The agent will:
    1. Classify the intent and extract entities
    2. Analyze the schema to determine tables needed
    3. Generate a PostgreSQL query
    4. Validate the query for safety
    5. Execute on Supabase
    6. Plan appropriate visualization
    
    Returns either:
    - Query results with SQL and visualization config
    - Clarification request if query is ambiguous
    - Error response if query cannot be processed
    """
    query_id = str(uuid.uuid4())
    logger.info(f"[{query_id}] Processing query: {request.query[:100]}...")
    
    # Get current user if authenticated
    current_user = await get_current_user_optional(authorization)
    user_id = current_user.id if current_user else None
    
    # Debug: Log request fields
    request_dict = request.model_dump() if hasattr(request, 'model_dump') else {}
    logger.info(f"[{query_id}] Request fields: {list(request_dict.keys())}, stream_answer: {request_dict.get('stream_answer', 'NOT_FOUND')}")
    
    try:
        # Get agent runner and process query
        runner = get_agent_runner()
        result = runner.process_query(
            query=request.query,
            conversation_history=request.context
        )
        
        # Check if clarification is needed
        if result.get("needs_clarification", False):
            logger.info(f"[{query_id}] Clarification needed")
            return ClarificationResponse(
                success=True,
                clarification_needed=True,
                question=result.get("clarification_question", "Could you please clarify your query?"),
                suggestions=_get_clarification_suggestions(result),
                original_query=request.query,
                detected_intent=result.get("query_intent")
            )
        
        # Check if SQL generation failed
        if not result.get("sql_validation_passed", False):
            logger.warning(f"[{query_id}] SQL validation failed")
            return ErrorResponse(
                success=False,
                error_code="SQL_GENERATION_FAILED",
                error_message="I couldn't understand your question. Could you try rephrasing it?",
                details={},  # Don't expose technical details to restaurant managers
                suggestions=[
                    "Try asking your question more clearly",
                    "Be more specific about what data you want to see",
                    "Check example queries for guidance",
                    "Ask about sales, revenue, products, locations, or orders"
                ]
            )
        
        # Execute the SQL query
        sql = result.get("generated_sql", "")
        
        if not sql:
            logger.error(f"[{query_id}] No SQL generated")
            return ErrorResponse(
                success=False,
                error_code="NO_SQL_GENERATED",
                error_message="I couldn't understand your question. Could you try rephrasing it?",
                details={},  # Don't expose technical details
                suggestions=[
                    "Try asking your question more clearly",
                    "Be more specific about what data you want to see",
                    "Check example queries for guidance",
                    "Ask about sales, revenue, products, locations, or orders"
                ]
            )
        
        # Check if shutdown is in progress (e.g., during uvicorn reload)
        if _shutdown_in_progress:
            logger.warning(f"[{query_id}] Shutdown in progress, aborting query execution")
            return ErrorResponse(
                success=False,
                error_code="SHUTDOWN_IN_PROGRESS",
                error_message="The system is temporarily unavailable. Please wait a moment and try again.",
                details={},  # Don't expose technical details
                suggestions=["Wait a few seconds and try again"]
            )
        
        logger.debug(f"[{query_id}] Executing SQL: {sql[:200]}...")
        
        settings = get_settings()
        max_execution_retries = 1  # Retry once if execution fails
        execution_retry_count = 0
        query_results = None
        exec_time = 0.0
        
        while execution_retry_count <= max_execution_retries:
            try:
                query_results, exec_time = await SupabasePool.execute_query(
                    sql,
                    timeout=settings.max_query_timeout
                )
                # Success - break out of retry loop
                break
            except asyncio.CancelledError:
                logger.warning(f"[{query_id}] Query execution cancelled (likely due to shutdown/reload)")
                return ErrorResponse(
                    success=False,
                    error_code="QUERY_CANCELLED",
                    error_message="Your request was interrupted. Please try again in a moment.",
                    details={},  # Don't expose technical details
                    suggestions=["Please wait a moment and try again"]
                )
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
                        
                        # Regenerate SQL with error context
                        runner = get_agent_runner()
                        retry_state = dict(result)
                        retry_state["agent_trace"] = list(result.get("agent_trace", []))
                        
                        # Import here to avoid circular dependency
                        from .agents.sql_generator import sql_generator_agent
                        from .agents.sql_validator import sql_validator_agent
                        
                        # Regenerate SQL
                        retry_state = sql_generator_agent(retry_state)
                        retry_state = sql_validator_agent(retry_state)
                        
                        # If new SQL is valid and different, try executing it
                        if retry_state.get("sql_validation_passed", False):
                            new_sql = retry_state.get("generated_sql", "")
                            if new_sql and new_sql != sql:
                                logger.info(f"[{query_id}] Retrying with corrected SQL")
                                sql = new_sql
                                result = retry_state
                                execution_retry_count = 0  # Reset counter for new SQL
                                await asyncio.sleep(0.3)  # Small delay before retry
                                continue  # Retry with new SQL
                    except Exception as retry_error:
                        logger.error(f"[{query_id}] Error during SQL regeneration: {retry_error}")
                
                # If we've exhausted retries, return error
                if execution_retry_count > max_execution_retries:
                    logger.error(f"[{query_id}] SQL execution failed after {execution_retry_count} attempts: {e}")
                    
                    # Parse error for user-friendly message
                    user_message, suggestions = parse_sql_error(e)
                    
                    # Return user-friendly error (hide technical details from restaurant managers)
                    return ErrorResponse(
                        success=False,
                        error_code="SQL_EXECUTION_FAILED",
                        error_message=user_message,
                        details={
                            # Only include technical details in development/debug mode
                            # For production, these should be logged server-side only
                            "retry_attempts": execution_retry_count - 1
                        },
                        suggestions=suggestions
                    )
                else:
                    # Log retry attempt and wait before retrying same SQL
                    logger.info(f"[{query_id}] Retrying SQL execution ({execution_retry_count}/{max_execution_retries})")
                    await asyncio.sleep(0.5)
        
        # Apply max results limit
        if request.max_results and len(query_results) > request.max_results:
            query_results = query_results[:request.max_results]
        
        # Format results
        formatted_results = format_results(query_results)
        columns = get_result_columns(query_results)
        
        # Update state with results for visualization and answer generation
        result["query_results"] = formatted_results
        result["result_count"] = len(formatted_results)
        result["expected_columns"] = columns
        result["execution_time_ms"] = exec_time
        
        # If streaming is requested, send results immediately
        # Use getattr as fallback in case model hasn't reloaded yet
        stream_answer = getattr(request, 'stream_answer', False)
        # Ensure it's a boolean (handle string "true"/"True")
        if isinstance(stream_answer, str):
            stream_answer = stream_answer.lower() in ('true', '1', 'yes')
        logger.info(f"[{query_id}] Stream answer requested: {stream_answer} (type: {type(stream_answer).__name__}), request fields: {list(request.model_fields.keys()) if hasattr(request, 'model_fields') else 'N/A'}")
        if stream_answer:
            logger.info(f"[{query_id}] ✅ Entering streaming path - will return StreamingResponse")
            import json
            
            async def generate_stream():
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
                    if len(generated_answer) > 100:
                        chunk_size = 50
                        for i in range(0, len(generated_answer), chunk_size):
                            chunk = generated_answer[i:i + chunk_size]
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
                    # Check if visualization is applicable
                    viz_applicable = is_visualization_applicable(answer_state) if request.include_chart else False
                    logger.info(f"[{query_id}] Visualization applicable: {viz_applicable}, include_chart: {request.include_chart}")
                    
                    if viz_applicable:
                        # Mark visualization as pending
                        await VisualizationCache.set_status(query_id, "pending")
                        
                        # Trigger async visualization generation
                        async def generate_visualization_async():
                            try:
                                logger.info(f"[{query_id}] Starting async visualization generation")
                                viz_state = dict(answer_state)
                                viz_state["agent_trace"] = list(answer_state.get("agent_trace", []))
                                
                                # Generate visualization
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
                                
                                # Update config with better defaults based on actual results
                                if viz_config:
                                    default_titles = ["No Results", "No Results Found", "Result", "Query Results"]
                                    if not viz_config.get("title") or viz_config.get("title") in default_titles:
                                        viz_config["title"] = (
                                            request.query[:60] + "..." if len(request.query) > 60 else request.query
                                        )
                                    
                                    if columns and not viz_config.get("x_axis"):
                                        viz_config["x_axis"] = columns[0]
                                    if len(columns) > 1 and not viz_config.get("y_axis"):
                                        viz_config["y_axis"] = columns[1]
                                
                                try:
                                    chart_config = generate_chart_config(formatted_results, viz_type, viz_config)
                                    logger.info(
                                        f"[{query_id}] Chart config generated: type={viz_type.value if hasattr(viz_type, 'value') else viz_type}, has_config={'data' in chart_config if chart_config else False}"
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
                        
                        # Start async task (fire and forget) AFTER sending the event
                        asyncio.create_task(generate_visualization_async())
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
                    # Note: visualization is not included here - it will be fetched separately when ready
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
                    
                    # Save query to history asynchronously (don't block response)
                    # Wait a bit for visualization to complete before saving
                    if user_id:
                        async def save_with_visualization():
                            try:
                                # Wait up to 10 seconds for visualization to be ready
                                viz_type = VisualizationType.TABLE
                                viz_config = {}
                                if viz_applicable:
                                    for _ in range(20):  # 20 * 0.5s = 10s max wait
                                        status = await VisualizationCache.get_status(query_id)
                                        if status in ("ready", "error", "not_applicable"):
                                            break
                                        await asyncio.sleep(0.5)
                                    
                                    cached_viz = await VisualizationCache.get(query_id)
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
                        
                        # Save asynchronously without blocking
                        asyncio.create_task(save_with_visualization())
                except Exception as e:
                    logger.error(f"[{query_id}] Error in streaming generator: {e}", exc_info=True)
                    error_data = {
                        "type": "error",
                        "error": str(e)
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            logger.info(f"[{query_id}] ✅ Returning StreamingResponse with text/event-stream")
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # Non-streaming path (original behavior)
        logger.info(f"[{query_id}] ⚠️ Using non-streaming path (stream_answer was False or not set)")
        # Generate answer first, then visualization
        answer_state = dict(result)
        answer_state["agent_trace"] = list(result.get("agent_trace", []))
        
        # Generate answer
        answer_state = answer_agent(answer_state)
        
        # Generate visualization if requested
        if request.include_chart:
            viz_state = dict(answer_state)
            viz_state["agent_trace"] = list(answer_state.get("agent_trace", []))
            viz_state = visualization_agent(viz_state)
            answer_state = viz_state
        
        # Get generated answer
        generated_answer = answer_state.get(
            "generated_answer",
            f"Query executed successfully. Found {len(formatted_results)} result(s)."
        )
        
        # Process visualization results
        viz_response = None
        if request.include_chart:
            viz_type = answer_state.get("visualization_type", VisualizationType.TABLE)
            viz_config = answer_state.get("visualization_config", {})
            
            # Skip if visualization type is NONE
            if viz_type == VisualizationType.NONE:
                logger.info(f"[{query_id}] Visualization not applicable, using table")
                viz_response = VisualizationResponse(type=VisualizationType.TABLE, config={})
            else:
                logger.info(
                    f"[{query_id}] Visualization type selected: {viz_type.value if hasattr(viz_type, 'value') else viz_type}"
                )
                
                # Update config with better defaults based on actual results
                if viz_config:
                    # Set title from query if not set or if it's a default
                    default_titles = ["No Results", "No Results Found", "Result", "Query Results"]
                    if not viz_config.get("title") or viz_config.get("title") in default_titles:
                        viz_config["title"] = (
                            request.query[:60] + "..." if len(request.query) > 60 else request.query
                        )
                    
                    # Auto-detect axes from columns if not set
                    if columns and not viz_config.get("x_axis"):
                        viz_config["x_axis"] = columns[0]
                    if len(columns) > 1 and not viz_config.get("y_axis"):
                        viz_config["y_axis"] = columns[1]
                
                try:
                    chart_config = generate_chart_config(formatted_results, viz_type, viz_config)
                    logger.info(
                        f"[{query_id}] Chart config generated: type={viz_type.value if hasattr(viz_type, 'value') else viz_type}, has_config={'data' in chart_config if chart_config else False}"
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
                
                viz_response = VisualizationResponse(
                    type=viz_type,
                    config=dict(viz_config) if viz_config else {},
                    chart_js_config=chart_config,
                )
        else:
            viz_response = VisualizationResponse(type=VisualizationType.TABLE, config={})
        
        logger.info(
            f"[{query_id}] Query successful: {len(formatted_results)} rows "
            f"in {exec_time:.2f}ms"
        )
        
        # Save query to history asynchronously (don't block response)
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
                    results_sample=formatted_results[:10],
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
        
    except TimeoutError as e:
        logger.error(f"[{query_id}] Query timeout: {e}")
        user_message, suggestions = parse_sql_error(e)
        return ErrorResponse(
            success=False,
            error_code="QUERY_TIMEOUT",
            error_message=user_message,
            details={},  # Don't expose technical details
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.exception(f"[{query_id}] Unexpected error: {e}")
        return ErrorResponse(
            success=False,
            error_code="INTERNAL_ERROR",
            error_message="An unexpected error occurred",
            details={"error": str(e)},
            suggestions=["Please try again", "Contact support if the issue persists"]
        )


def _get_clarification_suggestions(result: dict) -> list:
    """Generate clarification suggestions based on detected context"""
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
    
    return suggestions[:3]


# ==================== Visualization Endpoint ====================

@app.get("/api/visualization/{query_id}", response_model=VisualizationResponse)
async def get_visualization(query_id: str):
    """
    Fetch precomputed visualization for a query.
    Returns visualization data if available, or error if not ready/not applicable.
    Falls back to database if cache is empty (e.g., after restart).
    """
    logger.info(f"Fetching visualization for query_id: {query_id}")
    
    # First check cache
    status = await VisualizationCache.get_status(query_id)
    viz_data = await VisualizationCache.get(query_id)
    
    # If cache is empty but status exists, check database as fallback
    if not viz_data and status != "not_applicable":
        logger.info(f"[{query_id}] Cache miss, checking database for visualization")
        try:
            # Query database for saved visualization
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
                else:
                    # Visualization config exists but chart_js_config not stored (old records)
                    logger.info(f"[{query_id}] Found visualization config in database but no chart_js_config")
                    # Could regenerate here if needed, but for now return not found
        except Exception as e:
            logger.error(f"[{query_id}] Error checking database for visualization: {e}", exc_info=True)
    
    # Handle cache status responses
    if status == "not_applicable":
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error_code": "VISUALIZATION_NOT_APPLICABLE",
                "error_message": "A chart isn't available for this type of data"
            }
        )
    
    if status == "pending":
        return JSONResponse(
            status_code=202,
            content={
                "success": False,
                "error_code": "VISUALIZATION_PENDING",
                "error_message": "Visualization is still being generated",
                "status": "pending"
            }
        )
    
    if status == "error":
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "VISUALIZATION_ERROR",
                "error_message": "Error generating visualization"
            }
        )
    
    # If still no viz_data, return not found
    if not viz_data:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error_code": "VISUALIZATION_NOT_FOUND",
                "error_message": "Visualization not found or expired"
            }
        )
    
    # Convert to VisualizationResponse
    try:
        viz_type = VisualizationType(viz_data["type"])
    except ValueError:
        viz_type = VisualizationType.TABLE
    
    return VisualizationResponse(
        type=viz_type,
        config=viz_data.get("config", {}),
        chart_js_config=viz_data.get("chart_js_config")
    )


# ==================== Schema & Examples Endpoints ====================

@app.get("/api/schema", response_model=SchemaResponse)
async def get_schema():
    """
    Get schema information for the restaurant database.
    Useful for understanding available tables and columns.
    """
    tables = {}
    views = {}
    
    for name, info in SCHEMA_KNOWLEDGE["tables"].items():
        if info.get("type") == "view":
            views[name] = info
        else:
            tables[name] = info
    
    return SchemaResponse(
        tables=tables,
        views=views,
        important_rules=SCHEMA_KNOWLEDGE.get("important_rules", [])
    )


@app.get("/api/examples", response_model=ExamplesResponse)
async def get_examples():
    """
    Get example natural language queries.
    Useful for understanding what kinds of questions can be asked.
    """
    # Note: Database contains data from Jan 1-4, 2025 only
    examples = [
        ExampleQuery(
            query="What were total sales on January 2nd?",
            intent=QueryIntent.SALES_ANALYSIS,
            description="Get aggregate sales for a specific day"
        ),
        ExampleQuery(
            query="Show me the top 10 selling products",
            intent=QueryIntent.PRODUCT_ANALYSIS,
            description="Product ranking by sales volume"
        ),
        ExampleQuery(
            query="Compare revenue across all locations",
            intent=QueryIntent.LOCATION_COMPARISON,
            description="Location-wise revenue comparison"
        ),
        ExampleQuery(
            query="What are our busiest hours?",
            intent=QueryIntent.TIME_SERIES,
            description="Time-of-day analysis for staffing"
        ),
        ExampleQuery(
            query="Payment method breakdown",
            intent=QueryIntent.PAYMENT_ANALYSIS,
            description="Analyze payment type distribution"
        ),
        ExampleQuery(
            query="Daily revenue trend from Jan 1-4, 2025",
            intent=QueryIntent.TIME_SERIES,
            description="Revenue trend over available dates"
        ),
        ExampleQuery(
            query="Compare dine-in vs delivery vs takeout sales",
            intent=QueryIntent.ORDER_TYPE_ANALYSIS,
            description="Order type comparison"
        ),
        ExampleQuery(
            query="Which categories generate the most revenue?",
            intent=QueryIntent.CATEGORY_ANALYSIS,
            description="Category-level revenue analysis"
        ),
        ExampleQuery(
            query="Average order value by location",
            intent=QueryIntent.PERFORMANCE_METRICS,
            description="Calculate KPIs by location"
        ),
        ExampleQuery(
            query="Toast vs DoorDash revenue comparison",
            intent=QueryIntent.SOURCE_COMPARISON,
            description="Compare data sources"
        )
    ]
    
    return ExamplesResponse(examples=examples)


# ==================== Health & Status Endpoints ====================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_healthy = await SupabasePool.check_health()
    
    return HealthResponse(
        status="healthy" if db_healthy else "degraded",
        database_connected=db_healthy,
        version="1.0.0"
    )


@app.get("/api/stats")
async def get_stats():
    """Get API statistics"""
    pool_stats = await SupabasePool.get_pool_stats()
    
    return {
        "database": pool_stats,
        "agent": {
            "status": "ready"
        }
    }


# ==================== Utility Endpoints ====================

@app.post("/api/validate-sql")
async def validate_sql(sql: str = Query(..., description="SQL to validate")):
    """
    Validate a SQL query without executing it.
    Useful for testing queries before running them.
    """
    from .utils.validators import SQLValidator
    
    result = SQLValidator.validate(sql)
    
    return {
        "valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings
    }


@app.post("/api/explain")
async def explain_query(request: QueryRequest):
    """
    Get an explanation of what SQL would be generated for a query,
    without actually executing it.
    """
    runner = get_agent_runner()
    result = runner.process_query(
        query=request.query,
        conversation_history=request.context
    )
    
    return {
        "intent": result.get("query_intent", QueryIntent.UNKNOWN).value,
        "entities": result.get("entities_extracted", {}),
        "time_range": result.get("time_range", {}),
        "tables": result.get("relevant_tables", []),
        "sql": result.get("generated_sql", ""),
        "explanation": result.get("sql_explanation", ""),
        "visualization_type": result.get("visualization_type", VisualizationType.TABLE).value,
        "validation_passed": result.get("sql_validation_passed", False),
        "errors": result.get("sql_errors", []),
        "warnings": result.get("sql_warnings", [])
    }


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "error_message": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": "An unexpected error occurred"
        }
    )


# ==================== Run Configuration ====================

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

