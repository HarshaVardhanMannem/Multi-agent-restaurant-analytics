"""
SQL Validator Agent
Validates generated SQL for safety and correctness
"""

import logging

from ..models.state import AgentState
from ..utils.validators import SQLValidator, ValidationResult

logger = logging.getLogger(__name__)


def sql_validator_agent(state: AgentState) -> AgentState:
    """
    Validate the generated SQL query.

    Checks for:
    - Only SELECT statements allowed
    - Proper cents to dollars conversion
    - Voided orders filter
    - SQL injection patterns
    - Common mistakes

    If validation fails and retries available, increments retry_count.
    """
    logger.info("SQL validator processing...")

    # Track this agent
    agent_trace = state.get("agent_trace", [])
    agent_trace.append("sql_validator")

    sql = state.get("generated_sql", "")

    # Handle empty SQL
    if not sql or not sql.strip():
        state["sql_validation_passed"] = False
        state["sql_errors"] = ["No SQL query generated"]
        state["sql_warnings"] = []
        state["agent_trace"] = agent_trace
        logger.warning("Validation failed: No SQL generated")
        return state

    # Run validation
    result: ValidationResult = SQLValidator.validate(sql)

    # Apply additional context-aware validation
    context_errors, context_warnings = _context_validation(sql, state)

    # Combine results
    all_errors = result.errors + context_errors
    all_warnings = result.warnings + context_warnings

    # Update state
    state["sql_validation_passed"] = len(all_errors) == 0
    state["sql_errors"] = all_errors
    state["sql_warnings"] = all_warnings
    state["agent_trace"] = agent_trace

    if not state["sql_validation_passed"]:
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 1)

        if retry_count < max_retries:
            state["retry_count"] = retry_count + 1
            logger.warning(
                f"Validation failed with {len(all_errors)} errors. "
                f"Retry {retry_count + 1}/{max_retries}"
            )
        else:
            logger.error(f"Validation failed after {max_retries} retries. " f"Errors: {all_errors}")
    else:
        if all_warnings:
            logger.info(f"Validation passed with {len(all_warnings)} warnings: {all_warnings}")
        else:
            logger.info("Validation passed")

    return state


def _context_validation(sql: str, state: AgentState) -> tuple[list[str], list[str]]:
    """
    Additional validation based on query context.

    Checks that the SQL matches the expected intent and uses
    the right tables/columns.
    """
    errors = []
    warnings = []

    sql_lower = sql.lower()

    # Check tables match what schema analyzer recommended
    expected_tables = state.get("relevant_tables", [])
    if expected_tables:
        tables_in_sql = []
        for table in expected_tables:
            if table.lower() in sql_lower:
                tables_in_sql.append(table)

        if not tables_in_sql:
            warnings.append(f"SQL doesn't use recommended tables: {expected_tables}")

    # Check for missing GROUP BY with aggregates
    aggregates = ["sum(", "count(", "avg(", "min(", "max("]
    has_aggregate = any(agg in sql_lower for agg in aggregates)
    has_group_by = "group by" in sql_lower

    # Check if there are non-aggregated columns in SELECT with aggregates
    if has_aggregate and not has_group_by:
        # Extract SELECT clause
        select_part = sql_lower.split("from")[0] if "from" in sql_lower else sql_lower
        select_part = select_part.replace("select", "").strip()
        
        # Common categorical fields that require GROUP BY when used with aggregates
        categorical_fields = [
            "order_type", "location_name", "location_code", "product", "category",
            "payment_type", "source_system", "order_date", "day_of_week"
        ]
        
        # Check if any categorical fields are in SELECT
        has_categorical = any(field in select_part for field in categorical_fields)
        comma_count = select_part.count(",")
        
        # If there are multiple columns OR categorical fields with aggregates, GROUP BY is required
        if comma_count > 0 or has_categorical:
            errors.append(
                "Query has aggregate functions with non-aggregated columns but no GROUP BY. "
                "When comparing categories (e.g., order_type, location) or selecting categorical fields with aggregates, "
                "you must use GROUP BY. Example: SELECT order_type, SUM(total_revenue) FROM ... GROUP BY order_type"
            )

    # Check for potentially large result sets
    if "limit" not in sql_lower and has_group_by:
        # Grouped query without limit
        group_by_part = sql_lower.split("group by")[1] if "group by" in sql_lower else ""
        if "order by" not in group_by_part:
            warnings.append(
                "Query has GROUP BY but no ORDER BY. Results may be in arbitrary order."
            )

    # Check for date filter when time range was specified
    time_range = state.get("time_range", {})
    if time_range.get("relative") or time_range.get("start_date"):
        date_patterns = ["order_date", "payment_date", "created_at"]
        has_date_filter = any(pattern in sql_lower for pattern in date_patterns)
        if not has_date_filter:
            warnings.append(
                "Time range was specified but no date filter found in SQL. "
                "The query might not be time-filtered correctly."
            )

    # Check view usage for aggregations
    use_views = state.get("use_views", False)
    materialized_views = ["mv_daily_sales_summary", "mv_product_sales_summary", "mv_hourly_sales_pattern", 
                          "mv_payment_methods_by_source", "mv_order_type_performance", "mv_category_sales_summary",
                          "mv_location_performance", "mv_product_location_sales"]

    if use_views:
        uses_view = any(view in sql_lower for view in materialized_views)
        if not uses_view:
            warnings.append(
                "Views were recommended for performance but base tables were used instead."
            )

    return errors, warnings
