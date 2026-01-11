"""
Agent State Definition
TypedDict for managing state across the LangGraph workflow
"""

from enum import Enum
from typing import Any, TypedDict


class QueryIntent(str, Enum):
    """Types of queries the system can handle"""

    SALES_ANALYSIS = "sales_analysis"
    PRODUCT_ANALYSIS = "product_analysis"
    LOCATION_COMPARISON = "location_comparison"
    TIME_SERIES = "time_series"
    PAYMENT_ANALYSIS = "payment_analysis"
    ORDER_TYPE_ANALYSIS = "order_type_analysis"
    SOURCE_COMPARISON = "source_comparison"
    PERFORMANCE_METRICS = "performance_metrics"
    CATEGORY_ANALYSIS = "category_analysis"
    CUSTOMER_ANALYSIS = "customer_analysis"
    UNKNOWN = "unknown"


class VisualizationType(str, Enum):
    """Types of visualizations available"""

    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    MULTI_SERIES = "multi_series"
    HEATMAP = "heatmap"
    STACKED_BAR = "stacked_bar"
    AREA_CHART = "area_chart"
    NONE = "none"


class TimeRange(TypedDict, total=False):
    """Time range specification"""

    start_date: str | None
    end_date: str | None
    relative: str | None  # e.g., "last_week", "yesterday"


class ExtractedEntities(TypedDict, total=False):
    """Entities extracted from user query"""

    locations: list[str]
    products: list[str]
    categories: list[str]
    order_types: list[str]
    payment_types: list[str]
    sources: list[str]  # toast, doordash, square
    metrics: list[str]  # revenue, count, average, etc.
    limit: int | None  # For top-N queries


class JoinInfo(TypedDict):
    """Information about required joins"""

    from_table: str
    to_table: str
    join_condition: str
    join_type: str  # INNER JOIN, LEFT JOIN, etc.


class VisualizationConfig(TypedDict, total=False):
    """Configuration for chart visualization"""

    x_axis: str
    y_axis: str
    y_axes: list[str]  # For multi-series
    title: str
    subtitle: str | None
    colors: list[str]
    legend_position: str
    show_values: bool
    format_type: str  # currency, number, percentage


class AgentState(TypedDict, total=False):
    """
    Complete state passed through the LangGraph workflow
    Each agent reads and updates relevant fields
    """

    # Input
    user_query: str
    conversation_history: list[dict[str, str]]

    # Intent Classification
    query_intent: QueryIntent
    intent_confidence: float
    entities_extracted: ExtractedEntities
    time_range: TimeRange

    # Schema Analysis
    relevant_tables: list[str]
    relevant_columns: dict[str, list[str]]  # table_name -> columns
    required_joins: list[JoinInfo]
    schema_considerations: list[str]  # Special notes like "divide by 100"
    use_views: bool  # Whether to use pre-aggregated views

    # SQL Generation
    generated_sql: str
    sql_explanation: str
    expected_columns: list[str]  # Expected result columns

    # SQL Validation
    sql_validation_passed: bool
    sql_errors: list[str]
    sql_warnings: list[str]

    # Execution
    query_results: list[dict[str, Any]]
    result_count: int
    execution_time_ms: float
    execution_error: str | None

    # Result Validation
    results_valid: bool  # Whether results correctly answer the question
    result_validation_issue: str  # Description of issue if results invalid
    sql_corrected: bool  # Whether SQL was corrected by result validator

    # Visualization
    visualization_type: VisualizationType
    visualization_config: VisualizationConfig
    chart_config: dict[str, Any]  # Complete Chart.js config

    # Answer Generation
    generated_answer: str  # Natural language answer to user's question
    key_insights: list[str]  # Key insights extracted from results

    # Control Flow
    needs_clarification: bool
    clarification_question: str
    retry_count: int
    max_retries: int
    result_retry_count: int  # Retry count for result validation

    # Metadata
    processing_start_time: float
    total_processing_time_ms: float
    agent_trace: list[str]  # Track which agents processed the state


def create_initial_state(
    user_query: str, conversation_history: list[dict[str, str]] | None = None
) -> AgentState:
    """Create a fresh AgentState with default values"""
    return AgentState(
        user_query=user_query,
        conversation_history=conversation_history or [],
        query_intent=QueryIntent.UNKNOWN,
        intent_confidence=0.0,
        entities_extracted=ExtractedEntities(
            locations=[],
            products=[],
            categories=[],
            order_types=[],
            payment_types=[],
            sources=[],
            metrics=[],
            limit=None,
        ),
        time_range=TimeRange(),
        relevant_tables=[],
        relevant_columns={},
        required_joins=[],
        schema_considerations=[],
        use_views=False,
        generated_sql="",
        sql_explanation="",
        expected_columns=[],
        sql_validation_passed=False,
        sql_errors=[],
        sql_warnings=[],
        query_results=[],
        result_count=0,
        execution_time_ms=0.0,
        execution_error=None,
        visualization_type=VisualizationType.TABLE,
        visualization_config=VisualizationConfig(),
        chart_config={},
        needs_clarification=False,
        clarification_question="",
        retry_count=0,
        max_retries=1,
        result_retry_count=0,
        results_valid=True,
        result_validation_issue="",
        sql_corrected=False,
        processing_start_time=0.0,
        total_processing_time_ms=0.0,
        agent_trace=[],
    )
