"""
Error Parser
Converts technical database errors into user-friendly messages
"""

import re
import logging

logger = logging.getLogger(__name__)


def parse_sql_error(error: Exception) -> tuple[str, list[str]]:
    """
    Parse a SQL execution error and return user-friendly message and suggestions.
    
    Args:
        error: The exception that occurred
        
    Returns:
        Tuple of (user_friendly_message, suggestions_list)
    """
    error_str = str(error).lower()
    
    # Column does not exist
    if "column" in error_str and ("does not exist" in error_str or "not found" in error_str):
        message = "I couldn't find the information you're looking for. The data might not be available in the format you requested."
        suggestions = [
            "Try rephrasing your question using different terms",
            "Be more specific about what you want to see (e.g., 'sales by location' instead of 'location data')",
            "Ask about sales, revenue, products, locations, or orders",
            "Check if you're asking about the right time period (data is from January 1-4, 2025)"
        ]
        return message, suggestions
    
    # Table does not exist
    if "relation" in error_str and ("does not exist" in error_str or "not found" in error_str):
        message = "I couldn't find the information you're looking for. Please try rephrasing your question."
        suggestions = [
            "Try asking about sales, revenue, products, locations, or orders",
            "Be more specific about what data you want to see",
            "Check example queries for guidance"
        ]
        return message, suggestions
    
    # Syntax error
    if "syntax error" in error_str or "parse error" in error_str:
        message = "I had trouble understanding your question. Could you try rephrasing it?"
        suggestions = [
            "Try asking your question more clearly",
            "Be more specific about what you want to see",
            "Break down complex questions into simpler parts",
            "Example: 'What were our top selling products last week?'"
        ]
        return message, suggestions
    
    # Timeout
    if "timeout" in error_str or "exceeded" in error_str:
        message = "Your request is taking longer than expected. Let's try a simpler question."
        suggestions = [
            "Try asking about a more specific time period or location",
            "Narrow down your question (e.g., 'sales at Downtown location' instead of 'all sales')",
            "Ask about a smaller subset of data"
        ]
        return message, suggestions
    
    # Permission/access denied
    if "permission" in error_str or "access denied" in error_str or "forbidden" in error_str:
        message = "I don't have access to that information right now."
        suggestions = [
            "Try asking about different data (sales, revenue, products, locations, or orders)",
            "Contact support if you believe you should have access to this information"
        ]
        return message, suggestions
    
    # Division by zero
    if "division by zero" in error_str:
        message = "I couldn't calculate that because there's no data for the time period you're asking about."
        suggestions = [
            "Try asking about a different time period",
            "Remember: data is available from January 1-4, 2025"
        ]
        return message, suggestions
    
    # Type mismatch
    if "type" in error_str and ("mismatch" in error_str or "cannot" in error_str):
        message = "I had trouble calculating what you're asking for. Could you rephrase your question?"
        suggestions = [
            "Try being more specific about what you want to calculate",
            "Example: 'What was the total revenue?' or 'How many orders did we have?'"
        ]
        return message, suggestions
    
    # Generic database error
    if "database" in error_str or "postgres" in error_str:
        message = "Something went wrong while processing your question. Please try again."
        suggestions = [
            "Try rephrasing your question",
            "Wait a moment and try again",
            "If the problem persists, contact support"
        ]
        return message, suggestions
    
    # Default fallback
    message = "I couldn't process your question. Let's try rephrasing it."
    suggestions = [
        "Try asking your question more clearly",
        "Be more specific about what data you want to see",
        "Check example queries for guidance",
        "Ask about sales, revenue, products, locations, or orders"
    ]
    
    return message, suggestions

