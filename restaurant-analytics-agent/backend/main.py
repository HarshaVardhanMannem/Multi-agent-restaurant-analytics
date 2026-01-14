"""
FastAPI Application - Refactored
Main entry point for the Restaurant Analytics Agent API
Uses service layer architecture for clean separation of concerns
"""

import asyncio
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
from .services.query_service import QueryService
from .services.streaming_service import StreamingService
from .services.visualization_service import VisualizationService
from .utils.formatters import format_results, get_result_columns

from .models.requests import QueryRequest
from .models.responses import (
    VisualizationResponse,
    SchemaResponse,
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

# Global shutdown flag
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
        
        # Initialize agent runner (preloads LLM config)
        get_agent_runner()
        logger.info("Agent runner initialized")
        
    except (KeyboardInterrupt, asyncio.CancelledError):
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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost",
        "http://127.0.0.1",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
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
    
    try:
        # Run agent workflow
        runner = get_agent_runner()
        result = runner.process_query(
            query=request.query,
            conversation_history=request.context
        )
        
        # Handle clarification requests
        if result.get("needs_clarification", False):
            logger.info(f"[{query_id}] Clarification needed")
            return QueryService.create_clarification_response(result, request.query)
        
        # Check SQL validation
        if not result.get("sql_validation_passed", False):
            logger.warning(f"[{query_id}] SQL validation failed")
            return QueryService.create_error_response("SQL_GENERATION_FAILED")
        
        # Get generated SQL
        sql = result.get("generated_sql", "")
        if not sql:
            logger.error(f"[{query_id}] No SQL generated")
            return QueryService.create_error_response("NO_SQL_GENERATED")
        
        # Check shutdown state
        if _shutdown_in_progress:
            logger.warning(f"[{query_id}] Shutdown in progress")
            return QueryService.create_error_response("SHUTDOWN_IN_PROGRESS")
        
        # Execute SQL with retry logic
        try:
            query_results, exec_time, sql = await QueryService.execute_sql_with_retry(
                query_id, sql, result
            )
        except asyncio.CancelledError:
            logger.warning(f"[{query_id}] Query execution cancelled")
            return QueryService.create_error_response("QUERY_CANCELLED")
        except Exception as e:
            logger.error(f"[{query_id}] SQL execution failed: {e}")
            return QueryService.create_error_response(
                "SQL_EXECUTION_FAILED",
                error=e,
                details={"query_id": query_id}
            )
        
        # Apply max results limit
        if request.max_results and len(query_results) > request.max_results:
            query_results = query_results[:request.max_results]
        
        # Format results
        formatted_results = format_results(query_results)
        columns = get_result_columns(query_results)
        
        # Update state
        result["query_results"] = formatted_results
        result["result_count"] = len(formatted_results)
        result["expected_columns"] = columns
        result["execution_time_ms"] = exec_time
        
        # Check if streaming requested
        stream_answer = getattr(request, 'stream_answer', False)
        if isinstance(stream_answer, str):
            stream_answer = stream_answer.lower() in ('true', '1', 'yes')
        
        # Return streaming response if requested
        if stream_answer:
            logger.info(f"[{query_id}] Returning streaming response")
            return StreamingResponse(
                StreamingService.generate_stream(
                    query_id, result, request, sql,
                    formatted_results, columns, exec_time, user_id
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # Non-streaming response
        logger.info(f"[{query_id}] Returning non-streaming response")
        return await QueryService.process_non_streaming_query(
            query_id, result, request, sql,
            formatted_results, columns, exec_time, user_id
        )
        
    except TimeoutError as e:
        logger.error(f"[{query_id}] Query timeout: {e}")
        return QueryService.create_error_response("QUERY_TIMEOUT", error=e)
        
    except Exception as e:
        logger.exception(f"[{query_id}] Unexpected error: {e}")
        return QueryService.create_error_response(
            "INTERNAL_ERROR", error=e, details={"error": str(e)}
        )


# ==================== Visualization Endpoint ====================

@app.get("/api/visualization/{query_id}", response_model=VisualizationResponse)
async def get_visualization(query_id: str):
    """
    Fetch precomputed visualization for a query.
    Returns visualization data if available.
    Falls back to database if cache is empty (e.g., after restart).
    """
    logger.info(f"Fetching visualization for query_id: {query_id}")
    
    # Get visualization from cache or database
    viz_response = await VisualizationService.get_visualization_from_cache_or_db(query_id)
    
    if viz_response:
        return viz_response
    
    # If not found, return 404
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error_code": "VISUALIZATION_NOT_FOUND",
            "error_message": "Visualization not found or expired"
        }
    )


# ==================== Schema & Examples Endpoints ====================

@app.get("/api/schema", response_model=SchemaResponse)
async def get_schema():
    """Get schema information for the restaurant database."""
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
        "agent": {"status": "ready"}
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
