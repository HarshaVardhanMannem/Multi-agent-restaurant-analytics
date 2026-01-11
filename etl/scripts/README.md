# Scripts Directory

This directory contains all data ingestion and processing scripts for the ETL pipeline.

**Note**: This directory is now located under `etl/scripts/` in the project structure.

## Quick Start

### Recommended: Use the ETL Pipeline Orchestrator

The easiest way to run the complete pipeline is using the main orchestrator script:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run full pipeline (schema + materialized views + ingestion)
python pipeline/run_etl_pipeline.py --full

# Only ingest data (assumes schema and materialized views exist)
python pipeline/run_etl_pipeline.py --ingest-only
```

### Manual Execution (Advanced)

For more control, you can run individual scripts:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create database schema
python database/create_schema.py

# 3. Create materialized views (required for analytics)
python database/create_materialized_views.py

# 4. Run ingestion
python pipeline/ingest_unified_data.py --all
```

## Main Scripts

### `run_etl_pipeline.py` ⭐ **RECOMMENDED**
Main ETL pipeline orchestrator. Manages the complete pipeline flow from schema creation to data ingestion.

**Usage:**
```bash
# Full pipeline
python pipeline/run_etl_pipeline.py --full

# Only ingestion (assumes schema and materialized views exist)
python pipeline/run_etl_pipeline.py --ingest-only

# Dry run (test without committing)
python pipeline/run_etl_pipeline.py --full --dry-run
```

See script help for all options: `python pipeline/run_etl_pipeline.py --help`

### `ingest_unified_data.py`
Main data ingestion script. Processes all three data sources and loads into unified schema.

**Usage**:
```bash
# Ingest all sources
python pipeline/ingest_unified_data.py --all

# Ingest specific source
python pipeline/ingest_unified_data.py --toast data/sources/toast_pos_export.json
python pipeline/ingest_unified_data.py --doordash data/sources/doordash_orders.json
python pipeline/ingest_unified_data.py --square-dir data/sources/square

# Dry run (test without committing)
python pipeline/ingest_unified_data.py --all --dry-run
```

### `create_schema.py`
Creates the unified database schema.

**Usage**:
```bash
python database/create_schema.py
```

### `clear_all_tables.py`
Clears all data from unified schema tables.

**Usage**:
```bash
python database/clear_all_tables.py --yes
```

### Materialized View Refresh Scripts

**`refresh/refresh_materialized_views_sync.py`** ⭐ (Used by ETL pipeline)
- Synchronous refresh for SQLAlchemy-based code
- Used automatically by `ingest_unified_data.py` and `run_etl_pipeline.py`
- Import in code: `from scripts.refresh.refresh_materialized_views_sync import refresh_views_smart`

**`refresh/refresh_materialized_views.py`** (Standalone CLI tool)
- Async refresh for standalone use or scheduled jobs
- Use for cron jobs or manual refresh
- Command line: `python refresh/refresh_materialized_views.py --smart`

## Directory Structure

```
scripts/
│
├── 🚀 pipeline/                     Entry Points & Orchestration
│   ├── run_etl_pipeline.py          ⭐ Main ETL orchestrator (RECOMMENDED)
│   └── ingest_unified_data.py       Main data ingestion script
│
├── 🗄️  database/                    Database Setup & Management
│   ├── create_schema.py             Create unified database schema
│   ├── create_materialized_views.py Create materialized views (required)
│   ├── clear_all_tables.py          Clear all data (dev/testing only)
│   └── db_connection.py             Database connection utilities
│
├── 🔄 refresh/                      Materialized View Refresh
│   ├── refresh_materialized_views_sync.py  ⭐ Sync refresh (used by pipeline)
│   └── refresh_materialized_views.py       Async refresh (standalone CLI)
│
├── ⚙️  core/                        Core Utilities
│   ├── constants.py                 Shared constants (materialized views list)
│   ├── logger.py                    Centralized logging configuration
│   ├── paths.py                     Path utilities (file resolution)
│   ├── sql_executor.py              SQL file execution utilities
│   └── exceptions.py                Custom exception classes
│
├── 🔧 utils/                        Processing Utilities
│   ├── text_normalization.py        Text cleaning and normalization
│   └── product_matcher.py           Product matching across sources
│
├── ⚙️  config/                      Configuration
│   └── product_matching_config.py   Product matching rules and mappings
│
├── 📚 docs/                         Documentation
│   ├── README_MATERIALIZED_VIEWS.md Materialized view refresh guide
│   └── ETL_PIPELINE_STRUCTURE.md    Pipeline structure documentation
│
├── 🧪 tests/                        Test Scripts
│   ├── test_data_cleaning.py        Test text normalization
│   └── test_emoji_removal.py        Test emoji removal
│
├── README.md                        This file
└── requirements.txt                 Python dependencies
```

## Documentation

For complete documentation, see:
- **[DATA_INGESTION_GUIDE.md](../docs/DATA_INGESTION_GUIDE.md)** - Complete pipeline guide

## Configuration

Edit `config/product_matching_config.py` to:
- Add typo corrections
- Configure category mappings
- Set location mappings

## Testing

```bash
# Test text normalization
python tests/test_data_cleaning.py

# Test emoji removal
python tests/test_emoji_removal.py
```
