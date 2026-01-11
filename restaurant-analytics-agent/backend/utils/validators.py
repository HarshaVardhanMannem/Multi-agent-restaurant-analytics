"""
SQL Validators
Validate SQL queries for safety and correctness
"""

import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of SQL validation"""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


class SQLValidator:
    """Validates SQL queries for safety and correctness"""

    # Dangerous keywords that should never appear in generated SQL
    DANGEROUS_KEYWORDS = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
        "EXECUTE",
        "EXEC",
        "MERGE",
        "REPLACE",
    ]

    # Tables that use cents (need division by 100)
    CENTS_TABLES = ["unified_orders", "unified_order_items", "unified_payments"]

    # Columns that are in cents
    CENTS_COLUMNS = [
        "subtotal_cents",
        "tax_cents",
        "tip_cents",
        "service_fee_cents",
        "delivery_fee_cents",
        "discount_cents",
        "total_cents",
        "commission_cents",
        "merchant_payout_cents",
        "unit_price_cents",
        "total_price_cents",
        "amount_cents",
        "processing_fee_cents",
        "price_cents",
    ]

    # Views that already have dollar values
    DOLLAR_VIEWS = ["mv_daily_sales_summary", "mv_product_sales_summary", "mv_hourly_sales_pattern",
                    "mv_payment_methods_by_source", "mv_order_type_performance", "mv_category_sales_summary",
                    "mv_location_performance", "mv_product_location_sales"]

    @classmethod
    def validate(cls, sql: str) -> ValidationResult:
        """
        Validate a SQL query for safety and correctness.

        Args:
            sql: The SQL query to validate

        Returns:
            ValidationResult with is_valid, errors, and warnings
        """
        errors = []
        warnings = []

        sql_upper = sql.upper()
        sql_lower = sql.lower()

        # Check 1: Only SELECT allowed
        for keyword in cls.DANGEROUS_KEYWORDS:
            # Use word boundary check to avoid false positives
            pattern = rf"\b{keyword}\b"
            if re.search(pattern, sql_upper):
                errors.append(
                    f"Dangerous operation '{keyword}' not allowed. Only SELECT queries permitted."
                )

        # Check 2: Must start with SELECT or WITH
        sql_stripped = sql.strip().upper()
        if not (sql_stripped.startswith("SELECT") or sql_stripped.startswith("WITH")):
            errors.append("Query must start with SELECT or WITH")

        # Check 3: Check for cents columns without conversion
        uses_cents_column = any(col in sql_lower for col in cls.CENTS_COLUMNS)
        uses_base_table = any(table in sql_lower for table in cls.CENTS_TABLES)
        has_division = "/100" in sql or "/ 100" in sql

        if uses_cents_column and uses_base_table and not has_division:
            errors.append(
                "Using *_cents columns without dividing by 100.0. "
                "All cent values must be converted to dollars (column_cents / 100.0)."
            )

        # Check 4: Voided filter for unified_orders
        if "unified_orders" in sql_lower:
            if "voided" not in sql_lower:
                errors.append(
                    "Query uses unified_orders but doesn't filter voided orders. "
                    "Add 'WHERE voided = FALSE' to exclude voided orders."
                )
            elif "voided = true" in sql_lower or "voided=true" in sql_lower:
                warnings.append(
                    "Query explicitly selects voided orders. " "Ensure this is intentional."
                )

        # Check 5: Warn about dividing view values
        uses_view = any(view in sql_lower for view in cls.DOLLAR_VIEWS)
        if uses_view and has_division and "cents" not in sql_lower:
            warnings.append(
                "Query divides values in a pre-aggregated view. "
                "Views already have values in dollars - division may be incorrect."
            )

        # Check 6: SQL injection patterns
        injection_patterns = [
            r";\s*--",  # Comment injection
            r"'\s*OR\s*'1'\s*=\s*'1",  # Classic OR injection
            r"'\s*OR\s*1\s*=\s*1",  # Numeric OR injection
            r"UNION\s+SELECT",  # UNION injection
            r"INTO\s+OUTFILE",  # File write attempt
            r"LOAD_FILE",  # File read attempt
        ]

        for pattern in injection_patterns:
            if re.search(pattern, sql_upper):
                errors.append("Potential SQL injection pattern detected")
                break

        # Check 7: Limit clause for potentially large results
        if "LIMIT" not in sql_upper and "COUNT(" not in sql_upper:
            if "GROUP BY" not in sql_upper:
                warnings.append(
                    "Query has no LIMIT clause. Consider adding LIMIT "
                    "to prevent returning too many rows."
                )

        # Check 8: Check for common mistakes
        if "SELECT *" in sql_upper and "mv_" not in sql_lower and "unified_" in sql_lower:
            warnings.append("Using SELECT * on base tables. Consider selecting specific columns.")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    @classmethod
    def quick_check(cls, sql: str) -> tuple[bool, str]:
        """
        Quick validation check returning a simple boolean and first error.

        Returns:
            Tuple of (is_valid, error_message)
        """
        result = cls.validate(sql)
        if result.is_valid:
            return True, ""
        return False, result.errors[0] if result.errors else "Unknown validation error"

    @classmethod
    def sanitize_identifiers(cls, identifier: str) -> str:
        """
        Sanitize a SQL identifier (table name, column name).

        Args:
            identifier: The identifier to sanitize

        Returns:
            Sanitized identifier safe for SQL
        """
        # Only allow alphanumeric and underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "", identifier)
        return sanitized

    @classmethod
    def validate_table_name(cls, table_name: str) -> bool:
        """Check if a table name is valid"""
        valid_tables = [
            "unified_orders",
            "unified_order_items",
            "unified_products",
            "unified_categories",
            "unified_locations",
            "unified_payments",
            "mv_daily_sales_summary",
            "mv_product_sales_summary",
            "mv_hourly_sales_pattern",
            "mv_payment_methods_by_source",
            "mv_order_type_performance",
            "mv_category_sales_summary",
            "mv_location_performance",
            "mv_product_location_sales",
            "unified_order_item_modifiers",
            "location_id_mapping",
            "product_name_mapping",
        ]
        return table_name.lower() in valid_tables
