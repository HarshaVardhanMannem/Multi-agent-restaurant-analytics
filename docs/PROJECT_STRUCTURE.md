# Project Structure

## Directory Layout

```
clave-take-home/
├── data/
│   └── sources/              # Source JSON data files
│       ├── toast_pos_export.json
│       ├── doordash_orders.json
│       └── square/
│           ├── orders.json
│           ├── catalog.json
│           ├── payments.json
│           └── locations.json
│
├── docs/
│   ├── DATA_INGESTION_GUIDE.md    # ⭐ Main documentation
│   ├── PROJECT_STRUCTURE.md       # This file
│   └── SCHEMA_HINTS.md            # Original schema hints
│
├── schemas/
│   ├── unified_schema.sql         # ⭐ Main unified schema
│   ├── toast_schema.sql            # Optional: Toast-specific schema
│   ├── doordash_schema.sql         # Optional: DoorDash-specific schema
│   ├── square_schema.sql           # Optional: Square-specific schema
│   ├── EXAMPLE_QUERIES.sql         # SQL query examples
│   ├── QUERY_BY_SOURCE_SYSTEM.md   # How to query by source
│   ├── README.md                   # Schema overview
│   ├── SCHEMA_DOCUMENTATION.md     # Detailed schema docs
│   ├── SCHEMA_MAPPING.md           # Field mappings
│   └── SCHEMA_SUMMARY.md           # Schema summary
│
├── scripts/
│   ├── config/                     # Configuration files
│   │   └── product_matching_config.py
│   │
│   ├── core/                       # Core utilities
│   │   ├── logger.py               # Logging setup
│   │   └── exceptions.py           # Custom exceptions
│   │
│   ├── utils/                      # Utility functions
│   │   ├── text_normalization.py   # Text cleaning
│   │   └── product_matcher.py      # Product matching
│   │
│   ├── ingest_unified_data.py      # ⭐ Main ingestion script
│   ├── create_schema.py            # Schema creation
│   ├── clear_all_tables.py         # Database cleanup
│   ├── db_connection.py            # Database connection
│   ├── requirements.txt            # Python dependencies
│   │
│   └── [test scripts]              # Testing utilities
│
├── .env                            # Database credentials (not in repo)
└── README.md                       # Project overview
```

## Key Files

### Main Entry Points

1. **`scripts/ingest_unified_data.py`** - Main data ingestion script
   ```bash
   python scripts/ingest_unified_data.py --all
   ```

2. **`scripts/create_schema.py`** - Create database schema
   ```bash
   python scripts/create_schema.py
   ```

3. **`scripts/clear_all_tables.py`** - Clear all data
   ```bash
   python scripts/clear_all_tables.py --yes
   ```

### Core Modules

1. **`scripts/utils/text_normalization.py`**
   - Emoji removal
   - Typo correction
   - Category/product normalization

2. **`scripts/utils/product_matcher.py`**
   - Product matching across sources
   - Fuzzy string matching
   - Confidence scoring

3. **`scripts/config/product_matching_config.py`**
   - Typo corrections
   - Category mappings
   - Location mappings
   - Product name mappings

4. **`scripts/db_connection.py`**
   - Database connection management
   - Connection testing

### Documentation

1. **`docs/DATA_INGESTION_GUIDE.md`** - ⭐ **Main documentation**
   - Complete pipeline flow
   - Data cleaning process
   - Setup instructions
   - Troubleshooting

2. **`schemas/unified_schema.sql`** - Database schema definition

3. **`schemas/EXAMPLE_QUERIES.sql`** - SQL query examples

## Module Dependencies

```
ingest_unified_data.py
├── db_connection.py
├── utils/
│   ├── text_normalization.py
│   │   └── config/product_matching_config.py
│   └── product_matcher.py
│       └── utils/text_normalization.py
└── config/
    └── product_matching_config.py
```

## Data Flow

```
Source JSON Files
    ↓
ingest_unified_data.py
    ↓
text_normalization.py (cleaning)
    ↓
product_matcher.py (matching)
    ↓
Database (unified_schema)
```

## Configuration

All configuration is in:
- `scripts/config/product_matching_config.py` - Product matching rules
- `.env` file - Database credentials

## Testing

Test scripts:
- `test_data_cleaning.py` - Test text normalization
- `test_emoji_removal.py` - Test emoji removal
- `check_database_emojis.py` - Verify emoji removal in DB







