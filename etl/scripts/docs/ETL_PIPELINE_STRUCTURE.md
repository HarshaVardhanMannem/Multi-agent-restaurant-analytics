# ETL Pipeline Structure

This document describes the structure and execution flow of the ETL pipeline.

## Pipeline Overview

The ETL pipeline processes restaurant data from three sources (Toast POS, DoorDash, Square) into a unified PostgreSQL schema.

```
┌─────────────────────────────────────────────────────────────┐
│                    ETL PIPELINE FLOW                        │
└─────────────────────────────────────────────────────────────┘

1. SETUP
   ├── Database connection validation
   └── Configuration loading

2. SCHEMA CREATION
   ├── Create unified schema (tables only)
   └── Create materialized views (required for analytics)

3. DATA INGESTION
   ├── Setup reference data (locations, categories)
   ├── Process Toast POS data
   ├── Process DoorDash data
   ├── Process Square data
   ├── Product matching & normalization
   └── Commit transaction

4. POST-INGESTION
   ├── Refresh materialized views (if created)
   └── Generate statistics
```

## Execution Methods

### Method 1: Orchestrator Script (Recommended)

Use `run_etl_pipeline.py` for a single command to run the entire pipeline:

```bash
# Full pipeline (schema + materialized views + ingestion)
python etl/scripts/pipeline/run_etl_pipeline.py --full

# Only ingestion (schema must exist)
python etl/scripts/pipeline/run_etl_pipeline.py --ingest-only

# Dry run (test without committing)
python etl/scripts/pipeline/run_etl_pipeline.py --full --dry-run
```

**Advantages:**
- Single entry point
- Automatic error handling
- Progress tracking
- Validation at each step
- Clean output and logging

### Method 2: Individual Scripts

For more control or debugging, run scripts individually:

```bash
# Step 1: Create schema
python etl/scripts/database/create_schema.py

# Step 2: Create materialized views (required for analytics)
python etl/scripts/database/create_materialized_views.py

# Step 3: Ingest data
python etl/scripts/pipeline/ingest_unified_data.py --all

# Note: Materialized views are automatically refreshed after ingestion
```

## Script Components

### Core Scripts

| Script | Purpose | Required | Run Order |
|--------|---------|----------|-----------|
| `run_etl_pipeline.py` | Main orchestrator | ✅ Recommended | N/A (orchestrates) |
| `create_schema.py` | Create base schema | ✅ Yes | 1 |
| `create_materialized_views.py` | Create materialized views | ✅ Yes | 2 |
| `ingest_unified_data.py` | Ingest all sources | ✅ Yes | 3 |
| `db_connection.py` | Database utilities | ✅ Yes | (imported) |

### Utility Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `refresh_materialized_views*.py` | Refresh materialized views | After data updates (auto-refreshes after ingestion) |
| `clear_all_tables.py` | Clear all data | For dev/testing only |

## Directory Structure

```
scripts/
├── run_etl_pipeline.py          # ⭐ Main orchestrator
├── ingest_unified_data.py        # Data ingestion engine
├── create_schema.py              # Schema creation
├── create_materialized_views.py  # Materialized views (required)
├── refresh_materialized_views.py # Async refresh
├── refresh_materialized_views_sync.py # Sync refresh
├── clear_all_tables.py           # Cleanup utility
├── db_connection.py              # DB connection utilities
│
├── config/                       # Configuration
│   └── product_matching_config.py
│
├── core/                         # Core utilities
│   ├── logger.py
│   └── exceptions.py
│
├── utils/                        # Helper functions
│   ├── text_normalization.py
│   └── product_matcher.py
│
└── tests/                        # Test scripts
    ├── test_data_cleaning.py
    └── test_emoji_removal.py
```

## Pipeline Stages

### Stage 1: Schema Creation

**Script:** `create_schema.py`

**What it does:**
- Reads `schemas/unified_schema.sql`
- Creates all tables:
  - `unified_locations`
  - `unified_categories`
  - `unified_products`
  - `unified_orders`
  - `unified_order_items`
  - `unified_order_item_modifiers`
  - `unified_payments`
  - Mapping tables
- Creates base analytics views:
  - `v_daily_sales_summary`
  - `v_product_sales_summary`
  - `v_hourly_sales_pattern`

**When to run:** Once (or when schema changes)

### Stage 2: Materialized Views (Required)

**Script:** `create_materialized_views.py`

**What it does:**
- Reads `schemas/optimization_materialized_views.sql`
- Creates 8 materialized views for performance
- Creates 20+ indexes
- Pre-computes aggregations

**When to run:** Required before data ingestion (analytics depend on these)

### Stage 3: Data Ingestion

**Script:** `ingest_unified_data.py`

**What it does:**
1. Setup reference data (locations, categories)
2. For each source (Toast, DoorDash, Square):
   - Load JSON data
   - Normalize and clean text
   - Match products across sources
   - Transform to unified format
   - Insert into database
3. Commit transaction
4. Refresh materialized views (if created)

**Data Flow:**
```
Source JSON → Cleaning → Normalization → Product Matching → Transformation → Database
```

**When to run:** After schema creation, whenever new data arrives

### Stage 5: Materialized View Refresh

**Scripts:** `refresh_materialized_views_sync.py` (or async version)

**What it does:**
- Refreshes materialized views with latest data
- Supports full or incremental refresh
- Can refresh concurrently (non-blocking)

**When to run:**
- Automatically after ingestion (default)
- Manually after bulk updates
- Scheduled (every 15 minutes)

## Data Sources

### Toast POS
- **File:** `data/sources/toast_pos_export.json`
- **Structure:** Nested (Orders → Checks → Selections)
- **Special handling:** Modifiers, nested payments

### DoorDash
- **File:** `data/sources/doordash_orders.json`
- **Structure:** Flat order structure
- **Special handling:** Commissions, delivery fees

### Square
- **Directory:** `data/sources/square/`
- **Files:** `orders.json`, `catalog.json`, `payments.json`, `locations.json`
- **Special handling:** Catalog-based product structure

## Error Handling

The orchestrator script provides:
- ✅ Database connection validation before each step
- ✅ Transaction rollback on errors
- ✅ Detailed error messages with stack traces
- ✅ Step-by-step progress tracking
- ✅ Graceful handling of optional components

## Best Practices

1. **Use the orchestrator** for regular operations
2. **Run full pipeline** for initial setup
3. **Use ingestion-only** for regular data updates
4. **Create materialized views** for production
5. **Schedule refresh** for real-time analytics
6. **Test with dry-run** before production loads
7. **Monitor refresh duration** (should be < 60s)

## Troubleshooting

### Schema Already Exists
- **Error:** `relation already exists`
- **Solution:** Safe to ignore, or drop tables first with `clear_all_tables.py`

### Import Errors
- **Error:** `ModuleNotFoundError`
- **Solution:** Ensure you're running from project root, check `requirements.txt`

### Database Connection Failed
- **Error:** Connection timeout
- **Solution:** Check `DATABASE_URL` in `.env` file

### Materialized Views Not Refreshing
- **Error:** Views stale after ingestion
- **Solution:** Ensure views were created, check refresh logs

## Next Steps

After running the pipeline:
1. Query data using `schemas/EXAMPLE_QUERIES.sql`
2. Use analytics views for reporting
3. Set up scheduled refresh for materialized views
4. Monitor pipeline performance

