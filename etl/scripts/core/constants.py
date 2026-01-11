"""
Shared constants for ETL pipeline scripts.
"""

# Materialized views used in the pipeline
MATERIALIZED_VIEWS = [
    'mv_daily_sales_summary',
    'mv_product_sales_summary',
    'mv_product_location_sales',
    'mv_hourly_sales_pattern',
    'mv_payment_methods_by_source',
    'mv_order_type_performance',
    'mv_category_sales_summary',
    'mv_location_performance',
]

# Materialized views with date columns for incremental refresh
MATERIALIZED_VIEWS_WITH_DATES = {
    'mv_daily_sales_summary': 'order_date',
    'mv_hourly_sales_pattern': 'order_date',
    'mv_product_location_sales': 'order_date',  # If it has a date column
}

