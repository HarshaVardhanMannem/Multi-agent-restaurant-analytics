"""
API Request Models
Pydantic models for incoming API requests
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for natural language query"""

    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language query about restaurant data",
        examples=[
            "What were total sales yesterday?",
            "Show top 10 products last month",
            "Compare revenue across all locations",
        ],
    )

    context: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Previous conversation context for follow-up queries"
    )

    include_chart: bool = Field(
        default=True, description="Whether to include chart configuration in response"
    )

    max_results: Optional[int] = Field(
        default=100, ge=1, le=1000, description="Maximum number of result rows to return"
    )

    stream_answer: bool = Field(
        default=False, description="Whether to stream the response progressively (results first, then answer, then visualization)"
    )


class ClarificationResponse(BaseModel):
    """Response model when user provides clarification"""

    original_query: str = Field(..., description="The original query that needed clarification")

    clarification: str = Field(..., description="User's clarification response")
