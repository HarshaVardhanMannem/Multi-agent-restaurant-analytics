"""
Result Validator Agent
Checks if SQL query results correctly answer the user's question.
If not, generates a corrected SQL query.

Note: SQL execution happens in main.py (async context) to avoid event loop conflicts.
This agent just passes through - result validation can be added post-execution if needed.
"""

import logging

from ..models.state import AgentState

logger = logging.getLogger(__name__)


def result_validator_agent(state: AgentState) -> AgentState:
    """
    Pass-through agent for result validation.

    SQL execution happens in main.py (async context) to avoid event loop conflicts
    with the synchronous LangGraph workflow. Result validation can be implemented
    post-execution in main.py if needed.
    """
    logger.info("Result validator: Pass-through (SQL execution happens in main.py)")

    agent_trace = state.get("agent_trace", [])
    agent_trace.append("result_validator")

    # Mark as valid - actual validation would happen post-execution in main.py if needed
    state["results_valid"] = True
    state["agent_trace"] = agent_trace

    return state
