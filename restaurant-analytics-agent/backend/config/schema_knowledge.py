"""
Schema Knowledge Base
Comprehensive metadata about the restaurant database schema
Used by agents to understand table structures and generate correct SQL
"""

SCHEMA_KNOWLEDGE = {
    "tables": {
        "unified_orders": {
            "type": "table",
            "description": "Canonical order-level fact table. Main orders from Toast POS, DoorDash, and Square. Contains all order-level information including financials and status.",
            "grain": "One row per order",
            "key_columns": {
                "order_id": "Primary key - unique order identifier",
                "unified_location_id": "Foreign key to unified_locations",
                "source_system": "Origin system: 'toast', 'doordash', or 'square'",
                "order_date": "Date of order (DATE type) - use for date filtering",
                "order_timestamp": "Full timestamp with time - use for time-of-day analysis",
                "order_type": "Order type: 'DINE_IN', 'TAKE_OUT', 'DELIVERY', 'PICKUP'",
                "source_type": "Channel: 'POS', 'ONLINE', 'THIRD_PARTY'",
                "subtotal_cents": "Subtotal in cents (divide by 100.0 for dollars)",
                "tax_cents": "Tax in cents",
                "tip_cents": "Tips in cents",
                "service_fee_cents": "Service fees in cents",
                "delivery_fee_cents": "Delivery fees in cents",
                "discount_cents": "Discounts in cents",
                "total_cents": "Total amount in cents",
                "commission_cents": "Platform commission (DoorDash) in cents",
                "merchant_payout_cents": "Net merchant payout in cents",
                "status": "Order status: 'COMPLETED', 'CANCELLED', 'REFUNDED'",
                "voided": "Boolean - TRUE if order was voided (ALWAYS filter voided = FALSE)",
                "server_name": "Name of server/employee",
                "customer_name": "Customer name if available",
            },
            "use_for": [
                "revenue analysis",
                "order counts",
                "time-based analysis",
                "order type analysis",
                "channel comparison",
                "server performance",
                "customer orders",
            ],
            "do_not_use_for": [
                "Product-level analytics (use unified_order_items or mv_product_sales_summary)",
                "Payment details (use unified_payments)",
                "Daily aggregations (use mv_daily_sales_summary materialized view)",
            ],
            "required_filters": ["voided = FALSE"],
            "money_columns": [
                "subtotal_cents",
                "tax_cents",
                "tip_cents",
                "service_fee_cents",
                "delivery_fee_cents",
                "discount_cents",
                "total_cents",
                "commission_cents",
                "merchant_payout_cents",
            ],
            "notes": "CRITICAL: All monetary columns are in CENTS - divide by 100.0 for dollars. Always filter voided = FALSE.",
        },
        "unified_order_items": {
            "type": "table",
            "description": "Line-item details for orders. One row per product per order. Links to products and contains item-level pricing.",
            "grain": "One row per product per order",
            "key_columns": {
                "order_item_id": "Primary key",
                "order_id": "Foreign key to unified_orders - JOIN ON THIS",
                "unified_product_id": "Foreign key to unified_products (can be NULL)",
                "product_name": "Original product name from source - USE FOR PRODUCT FILTERING",
                "normalized_product_name": "Cleaned, standardized product name",
                "category_name": "Product category STRING - USE EXACT NAMES: Burgers, Sides, Beverages, Sandwiches, Breakfast, Salads, Entrees, Appetizers, Cocktails, Steaks, Alcohol, Wraps, Seafood, Pasta, Desserts, Coffee",
                "quantity": "Number of items ordered",
                "unit_price_cents": "Price per unit in cents",
                "total_price_cents": "Total line item price in cents",
                "tax_cents": "Item tax in cents",
                "source_system": "Origin system",
            },
            "use_for": [
                "product performance",
                "category analytics",
                "item-level reporting",
                "product sales analysis",
                "item quantity tracking",
                "category analysis",
            ],
            "do_not_use_for": [
                "Order-level totals (use unified_orders)",
                "Product rankings (use mv_product_sales_summary materialized view)",
            ],
            "money_columns": ["unit_price_cents", "total_price_cents", "tax_cents"],
            "columns_NOT_available": ["voided", "order_date", "location_code"],
            "notes": "CRITICAL: This table has NO 'voided' column! To filter voided orders, JOIN with unified_orders and filter uo.voided = FALSE. category_name is a STRING column (not an ID).",
        },
        "unified_products": {
            "type": "table",
            "description": "Canonical menu product definitions. Master product/menu item catalog with normalized names.",
            "grain": "One row per unique product",
            "key_columns": {
                "product_id": "Primary key",
                "product_code": "Standardized product code",
                "product_name": "Product name",
                "normalized_name": "Cleaned, standardized name",
                "category_id": "Foreign key to unified_categories",
                "is_alcohol": "Boolean - TRUE for alcoholic beverages",
            },
            "use_for": ["product lookups", "menu analysis", "alcohol sales tracking"],
            "notes": "Use normalized_name for consistent product matching",
        },
        "unified_categories": {
            "type": "table",
            "description": "Normalized, emoji-free product categories. Product categories with hierarchy support.",
            "grain": "One row per category",
            "key_columns": {
                "category_id": "Primary key",
                "category_name": "Category name (exact values: Burgers, Sides, Beverages, Sandwiches, Breakfast, Salads, Entrees, Appetizers, Cocktails, Steaks, Alcohol, Wraps, Seafood, Pasta, Desserts, Coffee)",
                "display_name": "Original name with emojis if applicable",
                "parent_category_id": "Self-referencing for category hierarchy",
            },
            "use_for": ["category grouping", "menu organization"],
            "notes": "Available categories: Burgers, Sides, Beverages, Sandwiches, Breakfast, Salads, Entrees, Appetizers, Cocktails, Steaks, Alcohol, Wraps, Seafood, Pasta, Desserts, Coffee",
        },
        "unified_locations": {
            "type": "table",
            "description": "Canonical list of physical restaurant locations. Restaurant locations/stores.",
            "grain": "One row per physical restaurant location",
            "key_columns": {
                "location_id": "Primary key",
                "location_code": "Short code: 'DOWNTOWN', 'AIRPORT', 'MALL', 'UNIVERSITY'",
                "location_name": "Full location name",
                "city": "City name",
                "state": "State abbreviation",
                "zip_code": "ZIP code",
                "timezone": "Location timezone",
            },
            "use_for": [
                "location-based grouping",
                "display names",
                "timezone-aware reporting",
                "location filtering",
                "regional analysis",
            ],
            "do_not_use_for": [
                "Revenue or order analytics directly (join with unified_orders or use views)"
            ],
            "notes": "Use location_code for filtering and display. JOIN: unified_orders.unified_location_id → unified_locations.location_id",
        },
        "unified_payments": {
            "type": "table",
            "description": "Payment transaction records. Payment transactions linked to orders.",
            "grain": "One row per payment transaction",
            "key_columns": {
                "payment_id": "Primary key",
                "order_id": "Foreign key to unified_orders",
                "payment_date": "Date of payment",
                "payment_timestamp": "Full payment timestamp",
                "payment_type": "Type: 'CREDIT', 'DEBIT', 'CASH', 'WALLET', 'OTHER'",
                "card_brand": "Card brand: 'VISA', 'MASTERCARD', 'AMEX', 'DISCOVER'",
                "card_last_4": "Last 4 digits of card",
                "wallet_type": "Digital wallet: 'APPLE_PAY', 'GOOGLE_PAY'",
                "amount_cents": "Payment amount in cents",
                "tip_cents": "Tip amount in cents",
                "processing_fee_cents": "Processing fee in cents",
                "status": "Payment status",
                "refund_status": "Refund status: 'NONE', 'PARTIAL', 'FULL'",
            },
            "use_for": [
                "payment method analysis",
                "tip reporting",
                "fee reconciliation",
                "tip analysis",
                "processing fee tracking",
                "card brand breakdown",
            ],
            "money_columns": ["amount_cents", "tip_cents", "processing_fee_cents"],
            "notes": "All monetary columns in cents. JOIN: unified_payments.order_id → unified_orders.order_id",
        },
        # ============ MATERIALIZED VIEWS (HIGHEST PERFORMANCE - USE THESE FIRST) ============
        # NOTE: This project uses ONLY materialized views (mv_*) for analytics.
        # Regular views (v_*) have been removed from the schema - do not use them.
        "mv_daily_sales_summary": {
            "type": "materialized_view",
            "description": "MATERIALIZED VIEW: Daily sales aggregations by location, order type, and source. 10-50x faster than regular views. Pre-aggregated and indexed.",
            "grain": "One row per: order_date, location_code, order_type, source_system",
            "key_columns": {
                "order_date": "Date (DATE type)",
                "location_id": "Location ID (INTEGER)",
                "location_code": "Location code: DOWNTOWN, AIRPORT, MALL, UNIVERSITY",
                "location_name": "Full location name",
                "order_type": "Order type: DINE_IN, TAKE_OUT, DELIVERY, PICKUP",
                "source_system": "Source: toast, doordash, square",
                "order_count": "Number of orders",
                "item_count": "Number of items",
                "total_subtotal": "Subtotal in DOLLARS",
                "total_tax": "Tax in DOLLARS",
                "total_tips": "Tips in DOLLARS",
                "total_revenue": "Total revenue in DOLLARS",
                "total_service_fees": "Service fees in DOLLARS",
                "total_delivery_fees": "Delivery fees in DOLLARS",
                "total_commissions": "Commissions in DOLLARS",
                "net_revenue": "Net revenue after commissions in DOLLARS",
                "avg_order_value": "Average order value in DOLLARS",
            },
            "use_for": [
                "daily sales by location",
                "revenue by location",
                "compare locations",
                "daily revenue trends",
                "order type comparisons",
                "source system comparisons",
                "How much from DoorDash/Toast/Square",
                "source system revenue",
                "platform comparison",
            ],
            "performance": "10-50x faster than querying base tables - USE THIS FIRST",
            "notes": "MATERIALIZED VIEW: Values in DOLLARS. Already filters voided orders. Has indexes on order_date, location_code, source_system, order_type.",
        },
        "mv_product_sales_summary": {
            "type": "materialized_view",
            "description": "MATERIALIZED VIEW: Product-level sales aggregations. 15-30x faster than regular views. Pre-aggregated and indexed.",
            "grain": "One row per product",
            "key_columns": {
                "product_id": "Product ID",
                "product_code": "Product code",
                "product": "Normalized product name (use this for filtering)",
                "original_product_name": "Original product name",
                "category_id": "Category ID",
                "category_name": "Category name",
                "order_count": "Number of orders",
                "location_count": "Number of locations",
                "total_quantity_sold": "Total quantity sold",
                "total_revenue": "Total revenue in DOLLARS",
                "avg_unit_price": "Average unit price in DOLLARS",
                "min_unit_price": "Minimum unit price in DOLLARS",
                "max_unit_price": "Maximum unit price in DOLLARS",
            },
            "use_for": [
                "top products",
                "best sellers",
                "product rankings",
                "product revenue analysis",
                "category revenue",
            ],
            "performance": "15-30x faster than v_product_sales_summary - USE THIS FIRST",
            "notes": "MATERIALIZED VIEW: Values in DOLLARS. Use 'product' column (normalized_name) for filtering. Has indexes on total_revenue, total_quantity_sold, category_name.",
        },
        "mv_product_location_sales": {
            "type": "materialized_view",
            "description": "MATERIALIZED VIEW: Product sales by location. Optimized for location-specific product queries.",
            "grain": "One row per: location_code, product",
            "key_columns": {
                "location_id": "Location ID",
                "location_code": "Location code",
                "location_name": "Location name",
                "product_id": "Product ID",
                "product": "Normalized product name",
                "category_name": "Category name",
                "order_count": "Number of orders",
                "total_quantity_sold": "Total quantity sold",
                "total_revenue": "Total revenue in DOLLARS",
            },
            "use_for": [
                "top products at specific location",
                "product performance by location",
                "location-specific product analysis",
            ],
            "performance": "15-30x faster than querying base tables - USE THIS FIRST",
            "notes": "MATERIALIZED VIEW: Values in DOLLARS. Has indexes on location_code, product, category_name.",
        },
        "mv_hourly_sales_pattern": {
            "type": "materialized_view",
            "description": "MATERIALIZED VIEW: Hourly sales patterns with location and order type. 25-50x faster than regular views.",
            "grain": "One row per: order_date, order_hour, location_code, order_type, source_system",
            "key_columns": {
                "order_date": "Date (DATE type)",
                "order_hour": "Hour of day (0-23)",
                "day_of_week": "Day of week (0=Sunday, 6=Saturday)",
                "location_id": "Location ID",
                "location_code": "Location code",
                "location_name": "Location name",
                "order_type": "Order type",
                "source_system": "Source system",
                "order_count": "Number of orders",
                "total_revenue": "Total revenue in DOLLARS",
                "avg_order_value": "Average order value in DOLLARS",
            },
            "use_for": [
                "hourly sales patterns",
                "peak hours by location",
                "time-of-day analysis",
                "busiest hours",
            ],
            "performance": "25-50x faster than querying base tables - USE THIS FIRST",
            "notes": "MATERIALIZED VIEW: Values in DOLLARS. Has indexes on order_date, order_hour, location_code.",
        },
        "mv_payment_methods_by_source": {
            "type": "materialized_view",
            "description": "MATERIALIZED VIEW: Payment method aggregations by source. 20-40x faster than regular views.",
            "grain": "One row per: source_system, payment_type, card_brand",
            "key_columns": {
                "source_system": "Source: toast, doordash, square",
                "payment_type": "Payment type: CREDIT, DEBIT, CASH, WALLET, OTHER",
                "card_brand": "Card brand: VISA, MASTERCARD, AMEX, DISCOVER",
                "transaction_count": "Number of transactions",
                "total_amount": "Total amount in DOLLARS",
                "avg_transaction_amount": "Average transaction amount in DOLLARS",
                "min_amount": "Minimum amount in DOLLARS",
                "max_amount": "Maximum amount in DOLLARS",
            },
            "use_for": [
                "payment method analysis",
                "most used payment methods",
                "payment breakdown",
                "card brand usage",
            ],
            "performance": "20-40x faster than querying base tables - USE THIS FIRST",
            "notes": "MATERIALIZED VIEW: Values in DOLLARS. NO order_date column. Has indexes on payment_type, source_system, transaction_count.",
        },
        "mv_order_type_performance": {
            "type": "materialized_view",
            "description": "MATERIALIZED VIEW: Order type performance comparisons. 20-30x faster than regular views.",
            "grain": "One row per: order_type, source_system, location_code",
            "key_columns": {
                "order_type": "Order type: DINE_IN, TAKE_OUT, DELIVERY, PICKUP",
                "source_system": "Source: toast, doordash, square",
                "location_code": "Location code",
                "order_count": "Number of orders",
                "gross_revenue": "Gross revenue in DOLLARS",
                "commissions": "Commissions in DOLLARS",
                "net_revenue": "Net revenue in DOLLARS",
                "avg_order_value": "Average order value in DOLLARS",
                "total_tips": "Total tips in DOLLARS",
                "avg_tip": "Average tip in DOLLARS",
            },
            "use_for": [
                "order type comparisons",
                "delivery vs dine-in",
                "channel analysis",
                "order type by location",
            ],
            "performance": "20-30x faster than querying base tables - USE THIS FIRST",
            "notes": "MATERIALIZED VIEW: Values in DOLLARS. Has indexes on order_type, source_system, location_code, net_revenue.",
        },
        "mv_category_sales_summary": {
            "type": "materialized_view",
            "description": "MATERIALIZED VIEW: Category-level sales aggregations. 15-30x faster than querying base tables.",
            "grain": "One row per category",
            "key_columns": {
                "category_id": "Category ID",
                "category_name": "Category name",
                "product_count": "Number of products",
                "order_count": "Number of orders",
                "location_count": "Number of locations",
                "total_quantity_sold": "Total quantity sold",
                "total_revenue": "Total revenue in DOLLARS",
                "avg_product_price": "Average product price in DOLLARS",
            },
            "use_for": [
                "category revenue analysis",
                "which category generates most revenue",
                "category performance",
            ],
            "performance": "15-30x faster than querying base tables - USE THIS FIRST",
            "notes": "MATERIALIZED VIEW: Values in DOLLARS. Has indexes on total_revenue, category_name.",
        },
        "mv_location_performance": {
            "type": "materialized_view",
            "description": "MATERIALIZED VIEW: Location performance metrics. 20-30x faster than querying base tables.",
            "grain": "One row per location",
            "key_columns": {
                "location_id": "Location ID",
                "location_code": "Location code",
                "location_name": "Location name",
                "order_count": "Number of orders",
                "total_revenue": "Total revenue in DOLLARS",
                "total_subtotal": "Subtotal in DOLLARS",
                "total_tax": "Tax in DOLLARS",
                "total_tips": "Tips in DOLLARS",
                "avg_order_value": "Average order value in DOLLARS",
                "doordash_orders": "DoorDash order count",
                "pos_orders": "POS order count",
                "doordash_revenue": "DoorDash revenue in DOLLARS",
                "pos_revenue": "POS revenue in DOLLARS",
            },
            "use_for": [
                "location comparisons",
                "which location had highest sales",
                "location performance ranking",
            ],
            "performance": "20-30x faster than querying base tables - USE THIS FIRST",
            "notes": "MATERIALIZED VIEW: Values in DOLLARS. Has indexes on location_code, total_revenue.",
        },
    },
    "joins": {
        "orders_to_locations": {
            "from_table": "unified_orders",
            "to_table": "unified_locations",
            "join_condition": "unified_orders.unified_location_id = unified_locations.location_id",
            "join_type": "INNER JOIN",
        },
        "orders_to_items": {
            "from_table": "unified_orders",
            "to_table": "unified_order_items",
            "join_condition": "unified_orders.order_id = unified_order_items.order_id",
            "join_type": "LEFT JOIN",
        },
        "items_to_products": {
            "from_table": "unified_order_items",
            "to_table": "unified_products",
            "join_condition": "unified_order_items.unified_product_id = unified_products.product_id",
            "join_type": "LEFT JOIN",
        },
        "products_to_categories": {
            "from_table": "unified_products",
            "to_table": "unified_categories",
            "join_condition": "unified_products.category_id = unified_categories.category_id",
            "join_type": "LEFT JOIN",
        },
        "orders_to_payments": {
            "from_table": "unified_orders",
            "to_table": "unified_payments",
            "join_condition": "unified_orders.order_id = unified_payments.order_id",
            "join_type": "LEFT JOIN",
        },
    },
    "important_rules": [
        "CRITICAL: Database only contains data from January 1-4, 2025. Use dates in this range.",
        "All *_cents columns in base tables must be divided by 100.0 for dollars",
        "Views (mv_*) already have values in dollars - do NOT divide",
        "Always filter voided = FALSE on unified_orders (views already do this)",
        "DO NOT JOIN views with base tables - views already contain denormalized data",
        "When filtering locations, use location_code (DOWNTOWN, AIRPORT, MALL, UNIVERSITY) not location_name",
        "JOIN via unified_location_id for locations and unified_product_id for products (only for base tables)",
        "Use order_date (DATE) for date filtering, order_timestamp (TIMESTAMP) for time-of-day",
        "location_code values: DOWNTOWN, AIRPORT, MALL, UNIVERSITY",
        "order_type values: DINE_IN, TAKE_OUT, DELIVERY, PICKUP",
        "source_system values: toast, doordash, square",
        "payment_type values: CREDIT, DEBIT, CASH, WALLET, OTHER",
    ],
    "table_selection_guide": {
        "use_views_when": [
            "Query asks for aggregated totals (SUM, COUNT, AVG) over dates",
            "Query asks for daily/weekly/monthly summaries",
            "Query compares locations or order types at aggregate level",
            "Query asks for product rankings or top sellers",
            "Query focuses on revenue trends over time",
        ],
        "use_base_tables_when": [
            "Query asks for individual order details",
            "Query asks for specific order items or line items",
            "Query needs payment-level details (card brand, tip per payment)",
            "Query asks for customer or server information",
            "Query needs order timestamps (hour, minute level)",
            "Query asks about modifiers or special instructions",
            "Query needs to filter by fields not in views",
            "Query asks 'show me orders' or 'list orders'",
        ],
        "examples": {
            "mv_daily_sales_summary": "Total sales today, Revenue by location, Daily trends, Daily revenue reporting",
            "mv_product_sales_summary": "Top 10 products, Best sellers overall, Menu optimization, Product pricing",
            "mv_hourly_sales_pattern": "Busiest hours, Peak times, Day of week patterns, Staffing optimization",
            "mv_product_location_sales": "Top products at specific location, Product performance by location",
            "mv_location_performance": "Location comparisons, Which location had highest sales",
            "mv_category_sales_summary": "Which category generates most revenue, Category performance",
            "mv_payment_methods_by_source": "Payment methods, Card brands, Payment breakdown",
            "mv_order_type_performance": "Delivery vs dine-in, Order type comparisons",
            # Base tables (use only for non-aggregated queries):
            "unified_orders": "Individual orders, Order details, Server performance, Customer orders",
            "unified_order_items": "What items in an order, Item-level analysis, Product performance",
            "unified_payments": "Payment details, Individual transactions, Payment method analysis",
            "unified_products": "Product catalog, Menu items, Product lookups",
            "unified_locations": "Location details, Addresses, Timezone-aware reporting",
        },
    },
    "common_query_patterns": {
        "total_sales_date_range": """
            SELECT SUM(total_revenue) as total_sales
            FROM mv_daily_sales_summary
            WHERE order_date BETWEEN '2025-01-01' AND '2025-01-04'
        """,
        "top_products": """
            SELECT product, total_quantity_sold, total_revenue
            FROM mv_product_sales_summary
            ORDER BY total_revenue DESC
            LIMIT 10
        """,
        "sales_by_location": """
            SELECT location_code, SUM(total_revenue) as revenue
            FROM mv_daily_sales_summary
            WHERE order_date BETWEEN '2025-01-01' AND '2025-01-04'
            GROUP BY location_code
            ORDER BY revenue DESC
        """,
        "compare_specific_locations": """
            SELECT location_code, SUM(total_revenue) as total_sales
            FROM mv_daily_sales_summary
            WHERE location_code IN ('DOWNTOWN', 'AIRPORT')
            AND order_date BETWEEN '2025-01-01' AND '2025-01-04'
            GROUP BY location_code
            ORDER BY total_sales DESC
        """,
        "hourly_pattern": """
            SELECT order_hour, SUM(order_count) as orders, SUM(total_revenue) as revenue
            FROM mv_hourly_sales_pattern
            GROUP BY order_hour
            ORDER BY order_hour
        """,
        "payment_breakdown": """
            SELECT payment_type, COUNT(*) as count, SUM(amount_cents)/100.0 as total
            FROM unified_payments up
            JOIN unified_orders uo ON up.order_id = uo.order_id
            WHERE uo.voided = FALSE
            GROUP BY payment_type
        """,
        "category_revenue": """
            SELECT uoi.category_name,
                   SUM(uoi.quantity) as total_items,
                   SUM(uoi.total_price_cents)/100.0 as total_revenue
            FROM unified_order_items uoi
            JOIN unified_orders uo ON uoi.order_id = uo.order_id
            WHERE uo.voided = FALSE
            GROUP BY uoi.category_name
            ORDER BY total_revenue DESC
        """,
        "product_by_location": """
            SELECT uoi.product_name,
                   SUM(uoi.quantity) as total_qty,
                   SUM(uoi.total_price_cents)/100.0 as revenue
            FROM unified_order_items uoi
            JOIN unified_orders uo ON uoi.order_id = uo.order_id
            JOIN unified_locations ul ON uo.unified_location_id = ul.location_id
            WHERE uo.voided = FALSE
            AND ul.location_code = 'MALL'
            GROUP BY uoi.product_name
            ORDER BY revenue DESC
            LIMIT 10
        """,
        "daily_trend": """
            SELECT order_date, SUM(total_revenue) as revenue, SUM(order_count) as orders
            FROM mv_daily_sales_summary
            WHERE order_date BETWEEN '2025-01-01' AND '2025-01-04'
            GROUP BY order_date
            ORDER BY order_date
        """,
        "source_comparison": """
            SELECT source_system, SUM(order_count) as total_orders, SUM(gross_revenue) as gross_revenue, SUM(net_revenue) as net_revenue, AVG(avg_order_value) as avg_order_value
            FROM mv_daily_sales_summary
            GROUP BY source_system
            ORDER BY net_revenue DESC
        """,
        "toast_vs_doordash": """
            SELECT source_system, SUM(order_count) as total_orders, SUM(total_revenue) as gross_revenue, SUM(net_revenue) as net_revenue
            FROM mv_daily_sales_summary
            WHERE source_system IN ('toast', 'doordash')
            GROUP BY source_system
        """,
        "category_revenue_ranking": """
            SELECT category_name, total_revenue
            FROM mv_category_sales_summary
            ORDER BY total_revenue DESC
        """,
        "order_type_comparison": """
            SELECT order_type, SUM(order_count) as orders, SUM(net_revenue) as revenue
            FROM mv_order_type_performance
            GROUP BY order_type
            ORDER BY revenue DESC
        """,
        "dine_in_vs_delivery": """
            SELECT order_type, SUM(net_revenue) as revenue
            FROM mv_order_type_performance
            WHERE order_type IN ('DINE_IN', 'DELIVERY')
            GROUP BY order_type
        """,
        "payment_method_breakdown": """
            SELECT payment_type, SUM(transaction_count) as count, SUM(total_amount) as total
            FROM mv_payment_methods_by_source
            GROUP BY payment_type
            ORDER BY total DESC
        """,
        "doordash_revenue": """
            SELECT source_system, SUM(total_revenue) as gross_revenue, SUM(net_revenue) as net_revenue, SUM(total_commissions) as total_commissions
            FROM mv_daily_sales_summary
            WHERE source_system = 'doordash'
            GROUP BY source_system
        """,
        "top_products_doordash": """
            SELECT 
                uoi.normalized_product_name as product,
                SUM(uoi.total_price_cents) / 100.0 as total_revenue,
                ROW_NUMBER() OVER (ORDER BY SUM(uoi.total_price_cents) DESC) as revenue_rank
            FROM unified_order_items uoi
            JOIN unified_orders uo ON uoi.order_id = uo.order_id
            WHERE uo.source_system = 'doordash' AND uo.voided = FALSE
            GROUP BY uoi.normalized_product_name
            ORDER BY revenue_rank
            LIMIT 10
        """,
        "market_share": """
            SELECT 
                source_system,
                SUM(total_revenue) as revenue,
                (SUM(total_revenue) * 100.0 / SUM(SUM(total_revenue)) OVER ()) as revenue_percentage
            FROM mv_daily_sales_summary
            GROUP BY source_system
            ORDER BY revenue DESC
        """,
    },
    "entity_mappings": {
        "locations": {
            "downtown": "DOWNTOWN",
            "airport": "AIRPORT",
            "mall": "MALL",
            "university": "UNIVERSITY",
            "uni": "UNIVERSITY",
        },
        "categories": {
            "burgers": "Burgers",
            "burger": "Burgers",
            "sides": "Sides",
            "side": "Sides",
            "beverages": "Beverages",
            "beverage": "Beverages",
            "drinks": "Beverages",
            "drink": "Beverages",
            "sandwiches": "Sandwiches",
            "sandwich": "Sandwiches",
            "breakfast": "Breakfast",
            "salads": "Salads",
            "salad": "Salads",
            "entrees": "Entrees",
            "entree": "Entrees",
            "appetizers": "Appetizers",
            "appetizer": "Appetizers",
            "cocktails": "Cocktails",
            "cocktail": "Cocktails",
            "steaks": "Steaks",
            "steak": "Steaks",
            "alcohol": "Alcohol",
            "wraps": "Wraps",
            "wrap": "Wraps",
            "seafood": "Seafood",
            "pasta": "Pasta",
            "desserts": "Desserts",
            "dessert": "Desserts",
            "coffee": "Coffee",
        },
        "order_types": {
            "dine in": "DINE_IN",
            "dine-in": "DINE_IN",
            "takeout": "TAKE_OUT",
            "take out": "TAKE_OUT",
            "take-out": "TAKE_OUT",
            "delivery": "DELIVERY",
            "pickup": "PICKUP",
            "pick up": "PICKUP",
            "pick-up": "PICKUP",
        },
        "sources": {
            "toast": "toast",
            "doordash": "doordash",
            "door dash": "doordash",
            "square": "square",
        },
        "payment_types": {
            "credit": "CREDIT",
            "credit card": "CREDIT",
            "debit": "DEBIT",
            "debit card": "DEBIT",
            "cash": "CASH",
            "apple pay": "WALLET",
            "google pay": "WALLET",
            "wallet": "WALLET",
        },
    },
    "time_expressions": {
        "today": "CURRENT_DATE",
        "yesterday": "CURRENT_DATE - INTERVAL '1 day'",
        "this week": "date_trunc('week', CURRENT_DATE)",
        "last week": "date_trunc('week', CURRENT_DATE - INTERVAL '1 week')",
        "this month": "date_trunc('month', CURRENT_DATE)",
        "last month": "date_trunc('month', CURRENT_DATE - INTERVAL '1 month')",
        "last 7 days": "CURRENT_DATE - INTERVAL '7 days'",
        "last 30 days": "CURRENT_DATE - INTERVAL '30 days'",
        "last 90 days": "CURRENT_DATE - INTERVAL '90 days'",
        "this year": "date_trunc('year', CURRENT_DATE)",
        "last year": "date_trunc('year', CURRENT_DATE - INTERVAL '1 year'",
    },
    "data_date_range": {
        "description": "IMPORTANT: The database currently only contains data from January 1-4, 2025",
        "start_date": "2025-01-01",
        "end_date": "2025-01-04",
        "note": "When generating queries, use dates within this range. Relative terms like 'yesterday' or 'last week' may return no data if current date is outside this range.",
    },
}


def get_table_info(table_name: str) -> dict:
    """Get information about a specific table"""
    return SCHEMA_KNOWLEDGE["tables"].get(table_name, {})


def get_join_info(from_table: str, to_table: str) -> dict:
    """Get join information between two tables"""
    for _, join_info in SCHEMA_KNOWLEDGE["joins"].items():
        if join_info["from_table"] == from_table and join_info["to_table"] == to_table:
            return join_info
        if join_info["from_table"] == to_table and join_info["to_table"] == from_table:
            return join_info
    return {}


def get_schema_summary() -> str:
    """Get a compact summary of the schema for LLM context (optimized for performance)"""
    summary_parts = []

    for table_name, table_info in SCHEMA_KNOWLEDGE["tables"].items():
        table_type = table_info.get("type", "table")
        # Use abbreviated description (first sentence only)
        description = table_info.get("description", "").split('.')[0]
        columns = list(table_info.get("key_columns", {}).keys())[:8]  # Limit to 8 most important columns
        use_for = table_info.get("use_for", [])[:3]  # Limit to top 3 use cases

        # Compact format: table_name (type): description | columns: col1, col2, ... | use_for: use1, use2
        summary_parts.append(
            f"{table_name} ({table_type}): {description} | "
            f"Columns: {', '.join(columns)}{'...' if len(table_info.get('key_columns', {})) > 8 else ''} | "
            f"Use: {', '.join(use_for)}{'...' if len(table_info.get('use_for', [])) > 3 else ''}"
        )

    summary_parts.append("")
    summary_parts.append("RULES: " + "; ".join(SCHEMA_KNOWLEDGE["important_rules"][:5]))  # Top 5 rules only

    return "\n".join(summary_parts)
