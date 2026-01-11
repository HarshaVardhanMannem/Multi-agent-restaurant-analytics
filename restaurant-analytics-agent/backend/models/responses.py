"""
API Response Models
Pydantic models for API responses
"""

from typing import Any

from pydantic import BaseModel, Field

from .state import QueryIntent, VisualizationType


class VisualizationResponse(BaseModel):
    """Visualization configuration in response"""

    type: VisualizationType = Field(..., description="Type of visualization recommended")

    config: dict[str, Any] = Field(
        default={}, description="Visualization configuration (x_axis, y_axis, title, etc.)"
    )

    chart_js_config: dict[str, Any] | None = Field(
        default=None, description="Complete Chart.js compatible configuration"
    )


class QueryResponse(BaseModel):
    """Successful query response"""

    success: bool = Field(default=True, description="Whether the query was successful")

    query_id: str = Field(..., description="Unique identifier for this query")

    intent: QueryIntent = Field(..., description="Detected query intent")

    sql: str = Field(..., description="Generated SQL query")

    explanation: str = Field(..., description="Human-readable explanation of the query")

    results: list[dict[str, Any]] = Field(..., description="Query result rows")

    result_count: int = Field(..., description="Total number of result rows")

    columns: list[str] = Field(..., description="Column names in the result")

    visualization: VisualizationResponse = Field(..., description="Visualization configuration")

    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")

    total_processing_time_ms: float = Field(
        ..., description="Total processing time including all agents"
    )

    answer: str | None = Field(
        default=None,
        description="Natural language answer to the user's question based on the results",
    )


class ClarificationResponse(BaseModel):
    """Response when clarification is needed"""

    success: bool = Field(default=True, description="Request was processed but needs clarification")

    clarification_needed: bool = Field(
        default=True, description="Indicates clarification is required"
    )

    question: str = Field(..., description="Clarification question to ask the user")

    suggestions: list[str] = Field(default=[], description="Suggested clarification options")

    original_query: str = Field(..., description="The original user query")

    detected_intent: QueryIntent | None = Field(
        default=None, description="Partial intent detected, if any"
    )


class ErrorResponse(BaseModel):
    """Error response"""

    success: bool = Field(default=False, description="Indicates the request failed")

    error_code: str = Field(..., description="Error code for programmatic handling")

    error_message: str = Field(..., description="Human-readable error message")

    details: dict[str, Any] | None = Field(
        default=None, description="Additional error details"
    )

    suggestions: list[str] = Field(default=[], description="Suggestions for fixing the error")


class SchemaResponse(BaseModel):
    """Schema information response"""

    tables: dict[str, Any] = Field(..., description="Table information")

    views: dict[str, Any] = Field(..., description="View information")

    important_rules: list[str] = Field(..., description="Important rules for querying")


class ExampleQuery(BaseModel):
    """Example query structure"""

    query: str = Field(..., description="Example natural language query")

    intent: QueryIntent = Field(..., description="Expected intent")

    description: str = Field(..., description="Description of what the query does")


class ExamplesResponse(BaseModel):
    """Example queries response"""

    examples: list[ExampleQuery] = Field(..., description="List of example queries")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status")

    database_connected: bool = Field(..., description="Whether database connection is healthy")

    version: str = Field(..., description="API version")
