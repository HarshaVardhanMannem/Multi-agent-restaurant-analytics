"""
Custom exceptions for the ingestion pipeline.
"""


class IngestionError(Exception):
    """Base exception for ingestion errors."""
    pass


class DatabaseConnectionError(IngestionError):
    """Raised when database connection fails."""
    pass


class SchemaError(IngestionError):
    """Raised when schema operations fail."""
    pass


class DataValidationError(IngestionError):
    """Raised when data validation fails."""
    pass


class ConfigurationError(IngestionError):
    """Raised when configuration is invalid."""
    pass


