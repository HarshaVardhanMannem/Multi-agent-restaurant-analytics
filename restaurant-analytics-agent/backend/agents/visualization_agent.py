"""
Visualization Planning Agent
Determines appropriate visualization type and configuration for query results.
Runs asynchronously after answer generation.
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import get_settings
from ..models.state import AgentState, QueryIntent, VisualizationConfig, VisualizationType
from ..utils.llm_factory import create_llm

logger = logging.getLogger(__name__)

# Prompt for visualization planning only
VIZ_PROMPT = """Select visualization type for the query results.

Query Intent: {intent}
Columns: {columns}
Rows: {result_count}
Query: {user_query}

Chart types:
- line_chart: Time series, trends over time, multiple series
- bar_chart: Categories/locations/products, rankings, <=20 items (horizontal if long labels)
- pie_chart: Part-to-whole, <=8 categories, percentages
- stacked_bar: Category breakdown within groups
- table: >50 rows or >5 columns, exact values, multi-dimensional
- multi_series: Multiple metrics over time, location comparisons
- heatmap: Two categorical dimensions, time patterns (hour x day)

Return JSON only:
{{
    "visualization_type": "bar_chart|line_chart|pie_chart|table|multi_series|heatmap|stacked_bar",
    "config": {{
        "x_axis": "column_name",
        "y_axis": "column_name",
        "title": "title",
        "format_type": "currency|number|percentage",
        "show_values": true
    }},
    "reasoning": "brief explanation for visualization choice"
}}
"""


def is_visualization_applicable(state: AgentState) -> bool:
    """
    Determine if visualization is applicable for the given result set.
    
    Returns False if:
    - No results
    - Single value result (better as metric card)
    - Results don't have appropriate structure for visualization
    """
    results = state.get("query_results", [])
    result_count = len(results)
    columns = list(results[0].keys()) if results else state.get("expected_columns", [])
    
    # No results - no visualization
    if result_count == 0:
        return False
    
    # Single value result - better as metric card
    if result_count == 1 and len(columns) <= 2:
        return False
    
    # Need at least one column to visualize
    if not columns:
        return False
    
    return True


def visualization_agent(state: AgentState) -> AgentState:
    """
    Plan visualization type and configuration for query results.
    This runs asynchronously after answer generation.
    """
    logger.info("Visualization agent processing...")

    agent_trace = state.get("agent_trace", [])
    agent_trace.append("visualization")

    results = state.get("query_results", [])
    result_count = len(results)
    columns = list(results[0].keys()) if results else state.get("expected_columns", [])
    user_query = state.get("user_query", "")

    # Check if visualization is applicable
    if not is_visualization_applicable(state):
        logger.info("Visualization not applicable for this result set")
        state["visualization_type"] = VisualizationType.NONE
        state["visualization_config"] = {}
        state["agent_trace"] = agent_trace
        return state

    # Quick decision for obvious cases
    if result_count == 1 and len(columns) <= 2:
        # Single value result - just show as table/card
        state["visualization_type"] = VisualizationType.TABLE
        state["visualization_config"] = {
            "title": user_query[:50] + "..." if len(user_query) > 50 else user_query,
            "show_values": True
        }
        state["agent_trace"] = agent_trace
        return state

    try:
        settings = get_settings()

        # Initialize LLM for visualization planning
        llm = create_llm(
            temperature=0.2,  # Lower for more consistent visualization choices
            top_p=1,
            max_tokens=256,  # Smaller since we're only planning visualization
            reasoning_budget=None,  # Disabled for performance
            enable_thinking=False,  # Disabled for performance
        )

        prompt = ChatPromptTemplate.from_template(VIZ_PROMPT)

        intent = state.get("query_intent", QueryIntent.UNKNOWN)

        chain = prompt | llm

        response = chain.invoke(
            {
                "intent": intent.value if isinstance(intent, QueryIntent) else str(intent),
                "columns": json.dumps(columns),
                "result_count": result_count,
                "user_query": user_query,
            }
        )

        # Parse response
        response_text = response.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text)

        # Process Visualization
        viz_type_str = result.get("visualization_type", "table")
        try:
            viz_type = VisualizationType(viz_type_str)
        except ValueError:
            viz_type = VisualizationType.TABLE

        # Parse config
        config_data = result.get("config", {})
        viz_config: VisualizationConfig = {
            "x_axis": config_data.get("x_axis", columns[0] if columns else ""),
            "y_axis": config_data.get("y_axis", columns[1] if len(columns) > 1 else ""),
            "title": config_data.get("title", "Query Results"),
            "format_type": config_data.get("format_type", "number"),
            "show_values": config_data.get("show_values", True),
            "colors": config_data.get("colors", ["#4f46e5", "#10b981", "#f59e0b", "#ef4444"]),
        }
        if config_data.get("subtitle"):
            viz_config["subtitle"] = config_data.get("subtitle")

        state["visualization_type"] = viz_type
        state["visualization_config"] = viz_config
        state["agent_trace"] = agent_trace

        logger.info(f"Visualization planned: {viz_type.value}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse visualization response: {e}")
        state = _fallback_visualization(state, columns, result_count)
        state["agent_trace"] = agent_trace

    except Exception as e:
        logger.error(f"Visualization agent error: {e}")
        state = _fallback_visualization(state, columns, result_count)
        state["agent_trace"] = agent_trace

    return state


def _fallback_visualization(state: AgentState, columns: list[str], result_count: int) -> AgentState:
    """
    Fallback visualization selection based on heuristics.
    """
    intent = state.get("query_intent", QueryIntent.UNKNOWN)

    # Determine based on intent and data shape
    if intent == QueryIntent.TIME_SERIES:
        viz_type = VisualizationType.LINE_CHART
    elif intent == QueryIntent.PRODUCT_ANALYSIS:
        viz_type = VisualizationType.BAR_CHART if result_count <= 20 else VisualizationType.TABLE
    elif intent == QueryIntent.LOCATION_COMPARISON:
        viz_type = VisualizationType.BAR_CHART
    elif intent == QueryIntent.PAYMENT_ANALYSIS:
        viz_type = VisualizationType.PIE_CHART if result_count <= 8 else VisualizationType.BAR_CHART
    elif result_count > 50 or len(columns) > 5:
        viz_type = VisualizationType.TABLE
    elif result_count <= 10:
        viz_type = VisualizationType.BAR_CHART
    else:
        viz_type = VisualizationType.TABLE

    # Infer x and y axes
    x_axis = ""
    y_axis = ""

    for col in columns:
        col_lower = col.lower()
        if any(d in col_lower for d in ["date", "day", "week", "month", "hour"]):
            x_axis = col
        elif any(m in col_lower for m in ["name", "type", "code", "category"]):
            x_axis = col
        elif any(v in col_lower for v in ["revenue", "sales", "total", "count", "sum", "avg"]):
            y_axis = col

    if not x_axis and columns:
        x_axis = columns[0]
    if not y_axis and len(columns) > 1:
        y_axis = columns[1]

    state["visualization_type"] = viz_type
    state["visualization_config"] = {
        "x_axis": x_axis,
        "y_axis": y_axis,
        "title": "Query Results",
        "format_type": "number",
        "show_values": True,
    }

    return state

