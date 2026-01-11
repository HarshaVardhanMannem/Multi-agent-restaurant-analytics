"""
SQL Generator Agent
Generates PostgreSQL queries based on schema analysis
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from ..config.schema_knowledge import SCHEMA_KNOWLEDGE
from ..config.settings import get_settings
from ..models.state import AgentState, QueryIntent
from ..utils.llm_factory import create_llm

logger = logging.getLogger(__name__)


SQL_GENERATOR_PROMPT = """Generate PostgreSQL query for restaurant analytics.

Query: {user_query} | Intent: {intent} | Entities: {entities} | Time: {time_range}
Tables: {tables} | Columns: {columns} | Joins: {joins} | Notes: {considerations}

### Schema Rules:
- Tables (*_cents)/100.0; Materialized Views=no divide (values already in DOLLARS)
- unified_orders: voided=FALSE
- **ONLY USE MATERIALIZED VIEWS**: Always use materialized views (mv_*). They are pre-aggregated and 10-50x faster than base tables.
- Column names: Use exact column names from schema. For revenue: use total_revenue/net_revenue/gross_revenue (NOT just "revenue"). Materialized views have: total_revenue, net_revenue, gross_revenue. Tables have: total_cents (divide by 100.0)
- Order type comparisons: Use mv_order_type_performance with net_revenue or gross_revenue
- Product comparisons: Use mv_product_sales_summary with 'product' column. For multiple products use: WHERE product ILIKE '%term1%' OR product ILIKE '%term2%'. Example: "Compare French Fries and Burgers" → WHERE product ILIKE '%fries%' OR product ILIKE '%burger%'
- Product filtering: ALWAYS use ILIKE with wildcards for flexible matching: product ILIKE '%burger%' (not = 'Burger')
- Payment method queries: Use mv_payment_methods_by_source for payment analysis. This view has: payment_type, source_system, transaction_count, total_amount (in DOLLARS). NO order_date column in this view.
- Date columns: Only use order_date/order_timestamp when querying time-based materialized views (mv_daily_sales_summary, mv_hourly_sales_pattern). Payment views (mv_payment_methods_by_source) do NOT have date columns.
- Location queries: Use mv_location_performance for location comparisons, or mv_daily_sales_summary grouped by location_code
- Category queries: Use mv_category_sales_summary for category analysis
- Product by location: Use mv_product_location_sales for location-specific product queries
- Source system queries: Use mv_daily_sales_summary grouped by source_system (e.g., "How much from DoorDash?" → SELECT source_system, SUM(total_revenue) FROM mv_daily_sales_summary WHERE source_system = 'doordash' GROUP BY source_system). DO NOT use mv_source_performance_summary (it doesn't exist).

### Time Rules (CRITICAL):
- **IMPORTANT: Database ONLY contains data from January 1-4, 2025 (2025-01-01 to 2025-01-04)**
- **Relative date mapping**: When user asks for "yesterday", "today", "last week", etc., map to the available date range:
  * "yesterday" → Use the most recent date in range: '2025-01-04' (or '2025-01-03' if context suggests)
  * "today" → Use '2025-01-04' (most recent date)
  * "last week" → Use date range '2025-01-01' to '2025-01-04'
  * "this week" → Use date range '2025-01-01' to '2025-01-04'
- Time expressions: {time_expressions}
- Dates: Use order_date (DATE type) or order_timestamp (TIMESTAMP type). Date literals: '2025-01-01' (quotes, DATE) or '2025-01-01 00:00:00' (TIMESTAMP). NEVER use dates without quotes or in numeric context.
- Always filter dates within the range: WHERE order_date BETWEEN '2025-01-01' AND '2025-01-04'

### Aggregation Rules (CRITICAL):
- "total"/"sum" → SUM() returning single row
- "breakdown"/"by" → GROUP BY with breakdown columns
- "top N"/"best"/"worst" → ORDER BY + LIMIT N
- "compare"/"comparison"/"vs"/"versus" → GROUP BY with the comparison dimension(s)
- **MANDATORY GROUP BY**: When selecting a categorical field (order_type, location_name, product, category, payment_type, source_system) along with ANY aggregate function (SUM, COUNT, AVG, MIN, MAX), you MUST use GROUP BY
- **MANDATORY GROUP BY**: When filtering by multiple values of a categorical field (e.g., WHERE order_type IN ('A','B')) AND selecting that field, ALWAYS use GROUP BY
- **Materialized views with pre-aggregated data**: When using materialized views, if you select a categorical field with an aggregate metric, use GROUP BY to aggregate by that dimension
- Examples (using materialized views - REQUIRED):
  * "Compare delivery vs dine revenue" → SELECT order_type, SUM(total_revenue) FROM mv_daily_sales_summary WHERE order_type IN ('DELIVERY','DINE_IN') GROUP BY order_type
  * "Revenue by location" → SELECT location_name, SUM(total_revenue) FROM mv_daily_sales_summary GROUP BY location_name
  * "Top products" → SELECT product, SUM(total_revenue) FROM mv_product_sales_summary GROUP BY product ORDER BY SUM(total_revenue) DESC LIMIT 10
  * "Most used payment methods" → SELECT payment_type, SUM(transaction_count) as count, SUM(total_amount) as total FROM mv_payment_methods_by_source GROUP BY payment_type ORDER BY count DESC
  * "Compare payment methods" → SELECT payment_type, SUM(transaction_count) as count, SUM(total_amount) as total FROM mv_payment_methods_by_source GROUP BY payment_type ORDER BY total DESC
  * "Top selling items at the Mall" → SELECT product, total_revenue FROM mv_product_location_sales WHERE location_code = 'MALL' ORDER BY total_revenue DESC LIMIT 10
  * "Which category generates the most revenue?" → SELECT category_name, total_revenue FROM mv_category_sales_summary ORDER BY total_revenue DESC LIMIT 1

### SQL Bias Corrections (IMPORTANT):
- COUNT(*) should ONLY appear in SELECT when user explicitly asks for counts. For "top N" or "most popular" queries, use COUNT(*) in ORDER BY but NOT in SELECT unless count is requested.
- Avoid IN with subqueries when INTERSECT/EXCEPT can be used for set operations
- Prefer INNER JOIN over LEFT JOIN unless NULL results are acceptable
- Always use DISTINCT when comparing data across multiple sources to avoid duplicates
- Use LIMIT 100 as default. ROUND currency values to 2 decimal places.

### Output Format:
Return JSON only:
{{
    "sql": "SELECT ... FROM ... WHERE ...",
    "explanation": "brief description",
    "expected_columns": ["col1", "col2"]
}}
No comments in SQL. No markdown formatting.
"""


def sql_generator_agent(state: AgentState) -> AgentState:
    """
    Generate the SQL query based on schema analysis.

    Uses the tables, columns, and joins identified by the schema analyzer
    to construct an accurate PostgreSQL query.
    """
    logger.info("SQL generator processing...")

    # Track this agent
    agent_trace = state.get("agent_trace", [])
    agent_trace.append("sql_generator")

    # Check if this is a retry
    retry_count = state.get("retry_count", 0)
    sql_errors = state.get("sql_errors", [])

    try:
        settings = get_settings()

        # NOTE: Reasoning can be enabled if SQL quality issues occur
        # Disabled by default for performance (30-50% faster)
        llm = create_llm(
            temperature=0.2,  # Slightly higher for creativity, but still deterministic
            top_p=1,
            max_tokens=1024,
            reasoning_budget=None,  # Disabled for performance - enable if SQL quality degrades
            enable_thinking=False,  # Disabled for performance
        )

        # Build prompt with retry context if needed
        prompt_template = SQL_GENERATOR_PROMPT

        # Check for both validation errors and execution errors
        execution_error = state.get("execution_error")
        has_errors = retry_count > 0 and (sql_errors or execution_error)
        
        if has_errors:
            error_list = list(sql_errors) if sql_errors else []
            if execution_error:
                error_list.append(f"SQL Execution Error: {execution_error}")
            
            failed_sql = state.get("generated_sql", "N/A")
            prompt_template += f"\n\nRETRY: Fix the following errors: {chr(10).join(f'- {err}' for err in error_list)}\nFailed SQL: {failed_sql}\n\nGenerate corrected SQL that addresses these specific errors."

        prompt = ChatPromptTemplate.from_template(prompt_template)

        # Prepare inputs
        intent = state.get("query_intent", QueryIntent.UNKNOWN)
        entities = state.get("entities_extracted", {})
        time_range = state.get("time_range", {})

        # Format joins
        joins = state.get("required_joins", [])
        joins_str = json.dumps([dict(j) for j in joins], indent=2) if joins else "None"

        # Get time expressions and data date range
        time_expressions = json.dumps(SCHEMA_KNOWLEDGE.get("time_expressions", {}), indent=2)
        data_date_range = SCHEMA_KNOWLEDGE.get("data_date_range", {})
        date_range_note = f"**CRITICAL**: {data_date_range.get('description', '')} Available dates: {data_date_range.get('start_date', '2025-01-01')} to {data_date_range.get('end_date', '2025-01-04')}. {data_date_range.get('note', '')}"

        chain = prompt | llm

        response = chain.invoke(
            {
                "user_query": state.get("user_query", ""),
                "intent": intent.value if isinstance(intent, QueryIntent) else str(intent),
                "entities": json.dumps(entities, default=str),
                "time_range": json.dumps(time_range, default=str),
                "tables": json.dumps(state.get("relevant_tables", [])),
                "columns": json.dumps(state.get("relevant_columns", {})),
                "joins": joins_str,
                "considerations": json.dumps(state.get("schema_considerations", [])),
                "time_expressions": f"{time_expressions}\n\n{date_range_note}",
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

        # Update state
        generated_sql = result.get("sql", "")
        state["generated_sql"] = generated_sql
        state["sql_explanation"] = result.get("explanation", "")
        state["expected_columns"] = result.get("expected_columns", [])
        state["agent_trace"] = agent_trace
        
        # Log generated SQL for debugging
        logger.info(f"SQL generated: {len(generated_sql)} chars")
        logger.debug(f"Generated SQL: {generated_sql}")

        # Clear previous errors (they'll be re-validated)
        state["sql_errors"] = []
        state["sql_validation_passed"] = False

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse SQL generation response: {e}")
        state["generated_sql"] = ""
        state["sql_explanation"] = "Failed to generate SQL query"
        state["sql_errors"] = ["Failed to parse LLM response"]
        state["agent_trace"] = agent_trace

    except Exception as e:
        logger.error(f"SQL generator error: {e}")
        state["generated_sql"] = ""
        state["sql_explanation"] = f"Error generating SQL: {str(e)}"
        state["sql_errors"] = [str(e)]
        state["agent_trace"] = agent_trace

    return state
