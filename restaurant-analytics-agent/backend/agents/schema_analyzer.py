"""
Schema Analyzer Agent
Determines which tables, columns, and joins are needed for the query
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA

from ..config.schema_knowledge import get_schema_summary
from ..config.settings import get_settings
from ..models.state import AgentState, JoinInfo, QueryIntent

logger = logging.getLogger(__name__)


SCHEMA_ANALYZER_PROMPT = """Select tables/views for restaurant analytics query.

Schema: {schema_summary}
Query: {user_query}
Intent: {intent}
Entities: {entities}
Time Range: {time_range}

USE MATERIALIZED VIEWS for: aggregates, summaries, rankings, comparisons, trends (e.g., "total sales", "top products", "compare locations")
USE BASE TABLES for: individual orders/items, payment details, timestamps, modifiers, fields not in views (e.g., "list orders", "order details")

Materialized Views (values already in DOLLARS, no divide needed): 
- mv_daily_sales_summary (daily sales by location, order_type, source_system)
- mv_product_sales_summary (product sales with categories)
- mv_product_location_sales (product sales by location)
- mv_hourly_sales_pattern (hourly sales patterns)
- mv_payment_methods_by_source (payment method analysis)
- mv_order_type_performance (order type comparisons: delivery vs dine-in)
- mv_category_sales_summary (category revenue analysis)
- mv_location_performance (location comparisons)

Tables (cents/100): unified_orders (voided=FALSE), unified_order_items, unified_payments, unified_products, unified_locations

Rules: Materialized Views=no divide (already in dollars), no joins needed. Tables=divide by 100, join via unified_location_id/unified_product_id/order_id

Return JSON only:
{{
    "tables": ["table1", "table2"],
    "columns": {{"table": ["col1", "col2"]}},
    "joins": [{{"from_table": "t1", "to_table": "t2", "join_condition": "t1.id=t2.id", "join_type": "LEFT JOIN"}}],
    "considerations": ["notes"],
    "use_views": true/false,
    "reasoning": "why"
}}
"""


def schema_analyzer_agent(state: AgentState) -> AgentState:
    """
    Analyze schema requirements for the query.

    Determines which tables, columns, and joins are needed based on
    the detected intent and extracted entities.
    """
    logger.info(f"Schema analyzer processing query with intent: {state.get('query_intent')}")

    # Track this agent
    agent_trace = state.get("agent_trace", [])
    agent_trace.append("schema_analyzer")

    try:
        settings = get_settings()

        llm = ChatNVIDIA(
            model=settings.nvidia_model,
            nvidia_api_key=settings.nvidia_api_key,
            temperature=0.1,
            top_p=1,
            max_tokens=1024,
            reasoning_budget=1024,
            chat_template_kwargs={"enable_thinking": True},
        )

        prompt = ChatPromptTemplate.from_template(SCHEMA_ANALYZER_PROMPT)

        # Get schema summary
        schema_summary = get_schema_summary()

        # Prepare inputs
        intent = state.get("query_intent", QueryIntent.UNKNOWN)
        entities = state.get("entities_extracted", {})
        time_range = state.get("time_range", {})

        chain = prompt | llm

        response = chain.invoke(
            {
                "user_query": state.get("user_query", ""),
                "schema_summary": schema_summary,
                "intent": intent.value if isinstance(intent, QueryIntent) else str(intent),
                "entities": json.dumps(entities, default=str),
                "time_range": json.dumps(time_range, default=str),
            }
        )

        # Parse response
        response_text = response.content.strip()

        # Extract JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text)

        # Update state with schema analysis
        state["relevant_tables"] = result.get("tables", [])
        state["relevant_columns"] = result.get("columns", {})

        # Parse joins
        joins = []
        for join_data in result.get("joins", []):
            joins.append(
                JoinInfo(
                    from_table=join_data.get("from_table", ""),
                    to_table=join_data.get("to_table", ""),
                    join_condition=join_data.get("join_condition", ""),
                    join_type=join_data.get("join_type", "LEFT JOIN"),
                )
            )
        state["required_joins"] = joins

        state["schema_considerations"] = result.get("considerations", [])
        state["use_views"] = result.get("use_views", False)
        state["agent_trace"] = agent_trace

        logger.info(
            f"Schema analysis complete: {len(state['relevant_tables'])} tables, "
            f"{len(joins)} joins, use_views={state['use_views']}"
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse schema analysis response: {e}")
        # Fall back to basic analysis based on intent
        state = _fallback_schema_analysis(state)
        state["agent_trace"] = agent_trace

    except Exception as e:
        logger.error(f"Schema analyzer error: {e}")
        state = _fallback_schema_analysis(state)
        state["agent_trace"] = agent_trace

    return state


def _fallback_schema_analysis(state: AgentState) -> AgentState:
    """
    Fallback schema analysis when LLM fails.
    Uses heuristics based on query intent AND query text.
    """
    intent = state.get("query_intent", QueryIntent.UNKNOWN)
    query = state.get("user_query", "").lower()

    # Check for keywords that indicate base table usage
    needs_base_tables = any(
        keyword in query
        for keyword in [
            "order details",
            "individual order",
            "list orders",
            "show orders",
            "specific order",
            "order #",
            "order number",
            "items in",
            "line items",
            "payment details",
            "card brand",
            "card type",
            "tip per",
            "server",
            "employee",
            "customer name",
            "refund",
            "modifier",
            "special instruction",
            "notes",
        ]
    )

    # Check for keywords that indicate view usage (aggregations)
    # Note: This check is informational - actual view selection is done by LLM
    _ = any(
        keyword in query
        for keyword in [
            "total",
            "sum",
            "average",
            "count",
            "top",
            "best",
            "worst",
            "compare",
            "trend",
            "by day",
            "by week",
            "by month",
            "daily",
            "busiest",
            "peak",
            "ranking",
            "breakdown",
        ]
    )

    # Default mappings based on intent
    intent_to_tables = {
        QueryIntent.SALES_ANALYSIS: {
            "tables": (
                ["mv_daily_sales_summary"]
                if not needs_base_tables
                else ["unified_orders", "unified_locations"]
            ),
            "columns": (
                {
                    "mv_daily_sales_summary": [
                        "order_date",
                        "location_code",
                        "location_name",
                        "total_revenue",
                        "order_count",
                        "net_revenue",
                    ]
                }
                if not needs_base_tables
                else {"unified_orders": ["order_id", "order_date", "total_cents", "voided"]}
            ),
            "use_views": not needs_base_tables,
        },
        QueryIntent.PRODUCT_ANALYSIS: {
            "tables": (
                ["mv_product_sales_summary"]
                if not needs_base_tables
                else ["unified_order_items", "unified_products"]
            ),
            "columns": (
                {
                    "mv_product_sales_summary": [
                        "product",
                        "category_name",
                        "total_quantity_sold",
                        "total_revenue",
                        "order_count",
                    ]
                }
                if not needs_base_tables
                else {"unified_order_items": ["product_name", "quantity", "total_price_cents"]}
            ),
            "use_views": not needs_base_tables,
        },
        QueryIntent.LOCATION_COMPARISON: {
            "tables": ["mv_location_performance"],
            "columns": {
                "mv_location_performance": [
                    "location_code",
                    "location_name",
                    "total_revenue",
                    "order_count",
                    "avg_order_value",
                ]
            },
            "use_views": True,
        },
        QueryIntent.TIME_SERIES: {
            "tables": (
                ["mv_daily_sales_summary"] if "hour" not in query else ["mv_hourly_sales_pattern"]
            ),
            "columns": (
                {"mv_hourly_sales_pattern": ["order_date", "order_hour", "total_revenue", "order_count"]}
                if "hour" in query
                else {"mv_daily_sales_summary": ["order_date", "total_revenue", "order_count"]}
            ),
            "use_views": True,
        },
        QueryIntent.PAYMENT_ANALYSIS: {
            "tables": (
                ["mv_payment_methods_by_source"]
                if not needs_base_tables
                else ["unified_payments", "unified_orders"]
            ),
            "columns": (
                {
                    "mv_payment_methods_by_source": [
                        "payment_type",
                        "card_brand",
                        "source_system",
                        "transaction_count",
                        "total_amount",
                    ]
                }
                if not needs_base_tables
                else {
                    "unified_payments": ["payment_type", "card_brand", "amount_cents", "tip_cents"],
                    "unified_orders": ["order_id", "voided"],
                }
            ),
            "use_views": not needs_base_tables,
        },
        QueryIntent.ORDER_TYPE_ANALYSIS: {
            "tables": ["mv_order_type_performance"],
            "columns": {
                "mv_order_type_performance": [
                    "order_type",
                    "source_system",
                    "location_code",
                    "order_count",
                    "net_revenue",
                    "gross_revenue",
                    "avg_order_value",
                ]
            },
            "use_views": True,
        },
    }

    config = intent_to_tables.get(
        intent,
        {
            "tables": ["mv_daily_sales_summary"],
            "columns": {"mv_daily_sales_summary": ["order_date", "total_revenue", "order_count"]},
            "use_views": True,
        },
    )

    state["relevant_tables"] = config["tables"]
    state["relevant_columns"] = config["columns"]
    state["required_joins"] = []
    state["schema_considerations"] = [
        "Using fallback schema analysis",
        "Views already have values in dollars",
        "Filter voided = FALSE for base order tables",
    ]
    state["use_views"] = config["use_views"]

    return state
