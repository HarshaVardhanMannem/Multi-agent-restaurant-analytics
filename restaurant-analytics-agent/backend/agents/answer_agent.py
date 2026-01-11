"""
Answer Generation Agent
Generates natural language answers from query results.
Decoupled from visualization generation for better performance.
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import get_settings
from ..models.state import AgentState, QueryIntent
from ..utils.llm_factory import create_llm

logger = logging.getLogger(__name__)

# Prompt for answer generation only
ANSWER_PROMPT = """Generate a natural language answer for the query results.

User Question: {user_query}
SQL Query: {sql}
Query Results (first 5 rows): {results_sample}
Total Results: {result_count}
Columns: {columns}

Generate a concise, natural language answer that:
- Directly answers the user's question
- Highlights key findings or numbers
- Uses the actual values from the results EXACTLY as they appear
- **CRITICAL: Currency values are in DOLLARS, not thousands. Use exact values from results (e.g., $54.07, not $54.07K). Do NOT add "K" or assume values are in thousands.**
- Format currency as $X.XX (e.g., $54.07, $1,234.56) - use exact decimal values from results
- Is conversational and clear
- **IMPORTANT: If user asked about "yesterday", "today", "last week", etc., mention that the database only contains data from January 1-4, 2025, and provide results for the closest available date(s)**
- If results are empty, explain why (e.g., "No data found for the specified criteria")

Return JSON only:
{{
    "answer": "Natural language answer to the user's question",
    "key_insights": ["insight1", "insight2"]
}}

Keep the answer brief (2-4 sentences) and focused on answering the user's question.
"""


def answer_agent(state: AgentState) -> AgentState:
    """
    Generate natural language answer from query results.
    This is decoupled from visualization generation for better performance.
    """
    logger.info("Answer agent processing...")

    agent_trace = state.get("agent_trace", [])
    agent_trace.append("answer")

    results = state.get("query_results", [])
    result_count = len(results)
    columns = list(results[0].keys()) if results else state.get("expected_columns", [])
    sql = state.get("generated_sql", "")
    user_query = state.get("user_query", "")

    # Sample results (first 5 rows for context)
    results_sample = results[:5] if results else []

    # Quick decision for empty results
    if result_count == 0:
        state["generated_answer"] = (
            "No results found for your query. Please try different criteria or check if the data exists for the specified conditions."
        )
        state["key_insights"] = []
        state["agent_trace"] = agent_trace
        return state

    try:
        settings = get_settings()

        # Initialize LLM for answer generation
        llm = create_llm(
            temperature=0.3,  # Higher for more natural language
            top_p=1,
            max_tokens=512,  # Reduced since we're only generating answer
            reasoning_budget=None,  # Disabled for performance
            enable_thinking=False,  # Disabled for performance
        )

        prompt = ChatPromptTemplate.from_template(ANSWER_PROMPT)

        chain = prompt | llm

        response = chain.invoke(
            {
                "user_query": user_query,
                "sql": sql,
                "results_sample": json.dumps(results_sample, default=str),
                "result_count": result_count,
                "columns": json.dumps(columns),
            }
        )

        # Parse response
        response_text = response.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text)

        # Process Answer
        answer = result.get("answer", "Query executed successfully.")
        state["generated_answer"] = answer
        state["key_insights"] = result.get("key_insights", [])
        state["agent_trace"] = agent_trace

        logger.info(f"Answer generated: {len(answer)} chars")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse answer response: {e}")
        # Fallback answer
        if result_count == 0:
            state["generated_answer"] = (
                "No results found for your query. Please try different criteria or check if the data exists for the specified conditions."
            )
        else:
            state["generated_answer"] = (
                f"Query executed successfully. Found {result_count} result(s)."
            )
        state["key_insights"] = []
        state["agent_trace"] = agent_trace

    except Exception as e:
        logger.error(f"Answer agent error: {e}")
        # Fallback answer
        if result_count == 0:
            state["generated_answer"] = "No results found for your query."
        else:
            state["generated_answer"] = (
                f"Query executed successfully. Found {result_count} result(s)."
            )
        state["key_insights"] = []
        state["agent_trace"] = agent_trace

    return state

