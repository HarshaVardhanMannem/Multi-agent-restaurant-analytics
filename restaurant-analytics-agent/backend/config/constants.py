"""
Application Constants
Centralized configuration values and magic numbers
"""

# ==================== Query Execution ====================

# Maximum time allowed for SQL query execution (seconds)
MAX_QUERY_TIMEOUT = 30

# Number of times to retry failed SQL execution
MAX_EXECUTION_RETRIES = 1

# Default maximum number of results to return
MAX_RESULTS_DEFAULT = 1000

# SQL execution retry delay (seconds)
SQL_RETRY_DELAY_SECONDS = 0.5

# SQL regeneration retry delay (seconds)
SQL_REGENERATION_DELAY_SECONDS = 0.3


# ==================== Visualization ====================

# Maximum attempts to wait for visualization to be ready
VIZ_MAX_WAIT_ATTEMPTS = 20

# Interval between visualization status checks (seconds)
VIZ_WAIT_INTERVAL_SEC = 0.5

# Maximum total wait time for visualization (VIZ_MAX_WAIT_ATTEMPTS * VIZ_WAIT_INTERVAL_SEC)
# = 20 * 0.5 = 10 seconds

# Cache status check interval (seconds)
VIZ_CACHE_STATUS_POLL_INTERVAL = 0.5


# ==================== Streaming ====================

# Minimum answer length to trigger chunk streaming (characters)
ANSWER_STREAM_THRESHOLD = 100

# Size of each answer chunk when streaming (characters)
ANSWER_CHUNK_SIZE = 50


# ==================== Query History ====================

# Number of result rows to save as sample in query history
HISTORY_RESULTS_SAMPLE_SIZE = 10


# ==================== Agent Workflow ====================

# Maximum agent retry attempts
MAX_AGENT_RETRIES = 1

# Maximum result validation retry attempts  
MAX_RESULT_VALIDATION_RETRIES = 1


# ==================== Error Messages ====================

# Default user-friendly error messages
ERROR_MESSAGES = {
    "SQL_GENERATION_FAILED": "I couldn't understand your question. Could you try rephrasing it?",
    "NO_SQL_GENERATED": "I couldn't understand your question. Could you try rephrasing it?",
    "SHUTDOWN_IN_PROGRESS": "The system is temporarily unavailable. Please wait a moment and try again.",
    "QUERY_CANCELLED": "Your request was interrupted. Please try again in a moment.",
    "SQL_EXECUTION_FAILED": "There was an error processing your query. Please try again.",
    "INTERNAL_ERROR": "An unexpected error occurred",
}

# Default error suggestions
ERROR_SUGGESTIONS = {
    "GENERIC": [
        "Try asking your question more clearly",
        "Be more specific about what data you want to see",
        "Check example queries for guidance",
        "Ask about sales, revenue, products, locations, or orders"
    ],
    "SHUTDOWN": ["Wait a few seconds and try again"],
    "CANCELLED": ["Please wait a moment and try again"],
}


# ==================== Default Titles ====================

# Titles to replace with user query
DEFAULT_VISUALIZATION_TITLES = [
    "No Results",
    "No Results Found", 
    "Result",
    "Query Results"
]


# ==================== Response Limits ====================

# Maximum query title length in visualization
MAX_QUERY_TITLE_LENGTH = 60
