"""
LangGraph Agent Workflow
Orchestrates the NL-to-SQL agent pipeline
"""

import logging
import time
from typing import Literal

from langgraph.graph import END, StateGraph

from .agents import (
    intent_and_schema_agent,
    result_validator_agent,
    sql_generator_agent,
    sql_validator_agent,
)
from .models.state import AgentState, create_initial_state

logger = logging.getLogger(__name__)


def should_clarify(state: AgentState) -> Literal["clarify", "schema"]:
    """
    Router after intent and schema analysis.
    Returns "clarify" if clarification needed, otherwise "schema" (proceed to SQL generation).
    """
    if state.get("needs_clarification", False):
        return "clarify"
    return "schema"


def should_retry(state: AgentState) -> Literal["retry", "execute", "error"]:
    """
    Router after SQL validation.
    Returns:
    - "retry" if validation failed and retries available
    - "execute" if validation passed (proceed to result validator)
    - "error" if max retries exceeded
    """
    if state.get("sql_validation_passed", False):
        return "execute"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)

    if retry_count < max_retries:
        return "retry"

    return "error"


def should_retry_sql(state: AgentState) -> Literal["retry", "viz"]:
    """
    Router after result validation.
    Returns:
    - "retry" if results don't answer question and corrected SQL available (goes back to validate_sql)
    - "viz" if results are valid or if we've already tried correcting
    """
    results_valid = state.get("results_valid", True)
    sql_corrected = state.get("sql_corrected", False)

    if results_valid:
        return "viz"

    # If SQL was corrected, retry once by going back to validate SQL (which will then execute)
    if sql_corrected:
        result_retry_count = state.get("result_retry_count", 0)
        if result_retry_count < 1:  # Allow one retry for corrected SQL
            state["result_retry_count"] = result_retry_count + 1
            # Clear validation flag so SQL validator runs again on corrected SQL
            state["sql_validation_passed"] = False
            return "retry"

    # Even if invalid, proceed to visualization (don't block)
    return "viz"


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph workflow for NL-to-SQL processing.

    Workflow:
    1. Intent & Schema Agent → Extract intent, entities, time range AND determine tables, columns, joins (merged for latency)
    2. (Optional) Clarification → If query is ambiguous
    3. SQL Generator → Generate PostgreSQL query
    4. SQL Validator → Validate safety and correctness
    5. (Retry loop if validation fails)
    6. Result Validator → Execute SQL and check if results answer question
    7. (Retry SQL generation if results invalid)
    
    Note: Visualization Planner runs in main.py after SQL execution with actual results

    Returns:
        Compiled LangGraph workflow
    """

    # Create the graph with AgentState
    workflow = StateGraph(AgentState)

    # Add all nodes (viz planner removed - runs in main.py after SQL execution with actual results)
    workflow.add_node("intent_and_schema", intent_and_schema_agent)
    workflow.add_node("generate_sql", sql_generator_agent)
    workflow.add_node("validate_sql", sql_validator_agent)
    workflow.add_node("validate_results", result_validator_agent)

    # Set entry point
    workflow.set_entry_point("intent_and_schema")

    # Add conditional edge from intent & schema agent
    workflow.add_conditional_edges(
        "intent_and_schema",
        should_clarify,
        {"clarify": END, "schema": "generate_sql"},  # End early for clarification, otherwise go to SQL generation
    )

    # Linear flow: sql → validate
    workflow.add_edge("generate_sql", "validate_sql")

    # Conditional edge from SQL validator (retry logic)
    workflow.add_conditional_edges(
        "validate_sql",
        should_retry,
        {
            "retry": "generate_sql",  # Loop back to regenerate
            "execute": "validate_results",  # Success, execute and validate results
            "error": END,  # Max retries exceeded
        },
    )

    # Conditional edge from result validator (retry SQL if results invalid)
    # Viz planner removed - runs in main.py after SQL execution with actual results
    workflow.add_conditional_edges(
        "validate_results",
        should_retry_sql,
        {
            "retry": "validate_sql",  # Loop back to validate corrected SQL
            "viz": END,  # Results valid, workflow complete (viz planning happens in main.py)
        },
    )

    logger.info("Agent workflow graph created")

    return workflow.compile()


class AgentRunner:
    """
    High-level runner for the agent workflow.
    Handles initialization, execution, and error handling.
    """

    def __init__(self):
        self.graph = create_agent_graph()
        logger.info("AgentRunner initialized")

    def process_query(
        self,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AgentState:
        """
        Process a natural language query through the agent workflow.

        Args:
            query: The user's natural language query
            conversation_history: Optional list of previous messages

        Returns:
            Final AgentState with results or clarification request
        """
        start_time = time.perf_counter()

        # Create initial state
        state = create_initial_state(user_query=query, conversation_history=conversation_history)
        state["processing_start_time"] = start_time

        logger.info(f"Processing query: {query[:100]}...")

        try:
            # Run the workflow
            result = self.graph.invoke(state)

            # Calculate total processing time
            end_time = time.perf_counter()
            result["total_processing_time_ms"] = (end_time - start_time) * 1000

            logger.info(
                f"Query processed in {result['total_processing_time_ms']:.2f}ms. "
                f"Agents: {result.get('agent_trace', [])}"
            )

            return result

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")

            end_time = time.perf_counter()
            state["total_processing_time_ms"] = (end_time - start_time) * 1000
            state["execution_error"] = str(e)
            state["sql_validation_passed"] = False

            return state

    async def process_query_async(
        self,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AgentState:
        """
        Async version of process_query.
        Note: The underlying LangGraph is synchronous, so this wraps it.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self.process_query, query, conversation_history
        )


# Singleton instance
_agent_runner: AgentRunner | None = None


def get_agent_runner() -> AgentRunner:
    """
    Get or create the singleton agent runner.

    Returns:
        AgentRunner instance (singleton)
    """
    global _agent_runner
    if _agent_runner is None:
        _agent_runner = AgentRunner()
    return _agent_runner
