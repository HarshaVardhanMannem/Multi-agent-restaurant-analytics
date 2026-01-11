"""
Formatters
Utility functions for formatting data and results
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def serialize_value(value: Any) -> Any:
    """Serialize a value for JSON response"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def format_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Format query results for API response.
    Handles serialization of special types.

    Args:
        results: List of result dictionaries

    Returns:
        Formatted results with serialized values
    """
    formatted = []
    for row in results:
        formatted_row = {}
        for key, value in row.items():
            formatted_row[key] = serialize_value(value)
        formatted.append(formatted_row)
    return formatted


def get_result_columns(results: list[dict[str, Any]]) -> list[str]:
    """Extract column names from results"""
    if not results:
        return []
    return list(results[0].keys())

