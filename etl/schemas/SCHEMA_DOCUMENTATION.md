# Database Schema Documentation

## Overview

This document describes the database schemas designed for the restaurant data integration project. The schemas normalize and unify data from three different sources: Toast POS, DoorDash, and Square.

## Schema Architecture

### Unified Schema

**`unified_schema.sql`** combines all three data sources (Toast POS, DoorDash, Square) into a single, queryable schema optimized for analytics and natural language querying.

The unified schema:
- Preserves source system information via `source_system` fields
- Enables cross-source analytics and comparisons
- Maintains data lineage while providing unified structure
- Includes pre-built analytics views for common queries

## Design Principles

### Normalization Strategy

The unified schema follows a **balanced normalization approach**:

1. **Fully Normalized**: Reference data (locations, categories, products)
   - Reduces redundancy
   - Ensures data consistency
   - Simplifies updates

2. **Partially Denormalized**: Transaction data (orders, order items)
   - Stores source product names alongside unified product IDs
   - Improves query performance for analytics
   - Maintains data lineage

### Key Design Decisions

#### 1. Location Mapping

**Problem**: Each source uses different location identifiers:
- Toast: `loc_downtown_001`
- DoorDash: `str_downtown_001`
- Square: `LCN001DOWNTOWN`

**Solution**: 
- Created `unified_locations` table with standardized location codes
- `location_id_mapping` table maps source IDs to unified IDs
- Enables cross-source location-based queries

#### 2. Product Matching

**Problem**: Products have inconsistent naming across sources:
- "Classic Burger" (Toast) vs "Classic Burger" (Square) - Same product
- "Griled Chiken Sandwich" (DoorDash typo) vs "Grilled Chicken Sandwich" (Square)
- "French Fries" vs "Fries - Large" vs "Fries" (same product, different variations)

**Solution**:
- `unified_products` table stores canonical product definitions
- `product_name_mapping` table tracks source-specific names
- Includes `confidence_score` for fuzzy matches
- Stores both normalized and original names for traceability

**Product Matching Strategy** (to be implemented in data ingestion):
1. Exact name match (confidence: 1.0)
2. Normalized name match (remove emojis, lowercase, strip special chars) (confidence: 0.95)
3. Fuzzy string matching (Levenshtein distance) (confidence: 0.7-0.9)
4. Manual review flag for ambiguous matches (confidence: < 0.7)

#### 3. Category Normalization

**Problem**: Categories have emojis and inconsistent naming:
- "🍔 Burgers" vs "Burgers" vs "ENTREES"
- "🍟 Sides" vs "Sides" vs "Sides & Appetizers"

**Solution**:
- `unified_categories` stores clean category names (emoji-free)
- `display_name` preserves original for reference
- Category mapping happens during data ingestion

#### 4. Order Type Standardization

**Problem**: Different sources use different order type terminology:
- Toast: `DINE_IN`, `TAKE_OUT`, `DELIVERY`
- DoorDash: `MERCHANT_DELIVERY`, `PICKUP`
- Square: `DINE_IN`, `PICKUP`

**Solution**: Unified to standard types:
- `DINE_IN` - Customer dines at restaurant
- `TAKE_OUT` / `PICKUP` - Customer picks up order
- `DELIVERY` - Order delivered to customer

#### 5. Financial Data Normalization

**Problem**: Different sources track financials differently:
- Toast: Prices in cents, tips at check level
- DoorDash: Includes commissions, merchant payouts, dasher tips
- Square: Separate payments, tips at order level

**Solution**: Unified financial structure:
- All amounts in cents (integers) for precision
- Standardized fields: `subtotal_cents`, `tax_cents`, `tip_cents`, `total_cents`
- Source-specific fields preserved: `commission_cents`, `merchant_payout_cents`, `service_fee_cents`
- `net_revenue` calculated as: `total_cents - commission_cents - service_fee_cents`

#### 6. Payment Method Mapping

**Problem**: Payment types vary:
- Toast: `CREDIT`, `CASH`, `OTHER` with card types
- Square: `CARD`, `CASH`, `WALLET` with detailed card info
- DoorDash: Payments not tracked (handled by platform)

**Solution**: Unified payment structure:
- `payment_type`: `CREDIT`, `DEBIT`, `CASH`, `WALLET`, `OTHER`
- `card_brand`: `VISA`, `MASTERCARD`, `AMEX`, `DISCOVER`
- `wallet_type`: `APPLE_PAY`, `GOOGLE_PAY`

## Data Cleaning Strategy

### Text Normalization Rules

1. **Remove Emojis**: Strip emoji characters from category and product names
2. **Case Normalization**: Convert to lowercase for matching (store original)
3. **Whitespace**: Trim and normalize spaces
4. **Special Characters**: Remove or standardize punctuation
5. **Typos**: Create mapping table for common typos:
   - "Griled" → "Grilled"
   - "Chiken" → "Chicken"
   - "Sandwhich" → "Sandwich"
   - "expresso" → "Espresso"
   - "coffe" → "Coffee"

### Product Name Matching Algorithm

```python
# Pseudocode for product matching
def match_product(source_name, source_system):
    # Step 1: Normalize name
    normalized = normalize_text(source_name)
    
    # Step 2: Exact match
    exact_match = find_exact_match(normalized)
    if exact_match:
        return exact_match, confidence=1.0
    
    # Step 3: Fuzzy match (Levenshtein distance)
    fuzzy_matches = find_fuzzy_matches(normalized, threshold=0.85)
    if fuzzy_matches:
        best_match = max(fuzzy_matches, key=lambda x: x.similarity)
        return best_match, confidence=best_match.similarity
    
    # Step 4: Create new product entry
    return create_new_product(source_name), confidence=1.0
```

### Category Mapping Rules

| Source Category | Unified Category |
|----------------|------------------|
| 🍔 Burgers | Burgers |
| 🍟 Sides | Sides |
| 🥤 Beverages / 🥤 Drinks | Beverages |
| 🌅 Breakfast | Breakfast |
| 🍰 Desserts | Desserts |
| Beer & Wine | Alcohol |
| Entrees / ENTREES | Entrees |
| Sandwiches | Sandwiches |
| Salads | Salads |
| Appetizers / 🍗 Appetizers | Appetizers |

## Schema Relationships

### Unified Schema Entity Relationship

```
unified_locations
    └── unified_orders (1:N)
            ├── unified_order_items (1:N)
            │       ├── unified_products (N:1)
            │       └── unified_order_item_modifiers (1:N)
            └── unified_payments (1:N)

unified_categories
    └── unified_products (1:N)

location_id_mapping
    └── unified_locations (N:1)

product_name_mapping
    └── unified_products (N:1)
```

## Indexing Strategy

### Primary Indexes

All tables have primary keys on ID columns.

### Foreign Key Indexes

All foreign key columns are indexed for join performance.

### Analytics Indexes

Additional indexes for common query patterns:

1. **Time-based queries**:
   - `unified_orders(order_date)`
   - `unified_orders(order_timestamp)`
   - `unified_payments(payment_date)`

2. **Location-based queries**:
   - `unified_orders(unified_location_id, order_date)` - Composite index

3. **Product analysis**:
   - `unified_order_items(unified_product_id)`
   - `unified_order_items(product_name)` - For unmapped items

4. **Source tracking**:
   - `unified_orders(source_system, source_order_id)`

## Data Types

### Monetary Values

- **Storage**: `BIGINT` in cents (integer)
- **Display**: Divide by 100.0 for dollar amounts
- **Rationale**: Avoids floating-point precision errors

### Timestamps

- **Type**: `TIMESTAMP` (with timezone)
- **Format**: ISO 8601 (YYYY-MM-DD HH:MM:SS)
- **Timezone**: UTC for storage, convert to location timezone for display

### Text Fields

- **Names**: `VARCHAR(255)` - Sufficient for product/order names
- **Descriptions**: `TEXT` - Unlimited length for notes/descriptions
- **IDs**: `VARCHAR(255)` - Accommodate various ID formats

## Analytics Views

The unified schema includes pre-built views for common analytics queries:

### 1. `v_daily_sales_summary`

Daily aggregated sales by location, order type, and source system.

**Use Cases**:
- "Show me daily sales for Downtown location"
- "Compare DoorDash vs POS sales"
- "Daily revenue by order type"

### 2. `v_product_sales_summary`

Product-level sales aggregations.

**Use Cases**:
- "Top 10 selling products"
- "Product revenue by category"
- "Average order value by product"

### 3. `v_hourly_sales_pattern`

Hourly and day-of-week sales patterns.

**Use Cases**:
- "Peak hours analysis"
- "Weekday vs weekend patterns"
- "Hourly revenue trends"

## Data Ingestion Strategy

### Recommended Ingestion Order

1. **Reference Data** (independent):
   - Locations → `unified_locations` + `location_id_mapping`
   - Categories → `unified_categories`
   - Products → `unified_products` + `product_name_mapping`

2. **Transaction Data** (dependent):
   - Orders → `unified_orders`
   - Order Items → `unified_order_items` (with product matching)
   - Payments → `unified_payments`

### Data Quality Checks

1. **Referential Integrity**: All foreign keys must exist
2. **Amount Validation**: `total_cents = subtotal_cents + tax_cents + tip_cents`
3. **Timestamp Consistency**: `closed_timestamp >= order_timestamp`
4. **Product Matching**: Flag items with low confidence scores for review

## Query Optimization Tips

1. **Use views** for common aggregations
2. **Filter early** using date/location indexes
3. **Prefer unified_product_id** joins over product_name matches
4. **Use materialized views** for heavy aggregations (refresh periodically)

## Future Enhancements

1. **Materialized Views**: Convert analytics views to materialized views for better performance
2. **Partitioning**: Partition `unified_orders` by `order_date` for large datasets
3. **Full-Text Search**: Add full-text indexes on product names for better search
4. **Audit Tables**: Track data changes and ingestion timestamps
5. **Data Quality Metrics**: Track matching confidence scores and unmapped items

## Migration Notes

When migrating from individual schemas to unified schema:

1. **Preserve Source Data**: Keep individual schemas for audit/reference
2. **Incremental Migration**: Migrate one source at a time
3. **Validation**: Compare aggregated totals before and after migration
4. **Rollback Plan**: Maintain source data until unified schema is validated

