# ETL Pipeline

This directory contains all ETL (Extract, Transform, Load) pipeline components including database schemas and processing scripts.

## Directory Structure

```
etl/
├── schemas/                  Database schema definitions and SQL files
└── scripts/                  ETL pipeline scripts and utilities
```

## Quick Start

### Run the Complete Pipeline

```bash
# From project root
cd etl/scripts

# Install dependencies
pip install -r requirements.txt

# Run full pipeline
python pipeline/run_etl_pipeline.py --full
```

### Individual Components

See documentation in:
- **`scripts/README.md`** - Scripts documentation and usage
- **`schemas/README.md`** - Schema documentation

## Main Entry Points

1. **Pipeline Orchestrator**: `scripts/pipeline/run_etl_pipeline.py`
2. **Data Ingestion**: `scripts/pipeline/ingest_unified_data.py`
3. **Schema Creation**: `scripts/database/create_schema.py`

## Documentation

- `scripts/docs/` - Pipeline and refresh documentation
- `schemas/` - Schema SQL files and documentation

