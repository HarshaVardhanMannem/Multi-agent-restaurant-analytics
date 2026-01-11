# Schema Mapping Reference

This document provides a quick reference for mapping fields between source schemas and the unified schema.

## Location Mapping

| Unified | Toast | DoorDash | Square |
|---------|-------|----------|--------|
| `location_id` | `location_guid` | `store_id` | `location_id` |
| `location_code` | N/A | N/A | N/A |
| `location_name` | `name` | `name` | `name` |
| `address_line1` | `address.line1` | `address.street` | `address.address_line_1` |
| `city` | `address.city` | `address.city` | `address.locality` |
| `state` | `address.state` | `address.state` | `address.administrative_district_level_1` |
| `zip_code` | `address.zip` | `address.zip_code` | `address.postal_code` |
| `country` | `address.country` | `address.country` | `address.country` |
| `timezone` | `timezone` | `timezone` | `timezone` |

### Location ID Examples

| Location Name | Unified Code | Toast GUID | DoorDash Store ID | Square Location ID |
|---------------|--------------|------------|-------------------|-------------------|
| Downtown | `DOWNTOWN` | `loc_downtown_001` | `str_downtown_001` | `LCN001DOWNTOWN` |
| Airport | `AIRPORT` | `loc_airport_002` | `str_airport_002` | `LCN002AIRPORT` |
| Mall Location | `MALL` | `loc_mall_003` | `str_mall_003` | `LCN003MALL` |
| University | `UNIVERSITY` | `loc_univ_004` | `str_university_004` | `LCN004UNIV` |

## Order Mapping

| Unified Field | Toast | DoorDash | Square |
|---------------|-------|----------|--------|
| `source_system` | `'toast'` | `'doordash'` | `'square'` |
| `source_order_id` | `guid` | `external_delivery_id` | `id` |
| `external_order_id` | `externalId` | `external_delivery_id` | N/A |
| `order_date` | `businessDate` | `created_at` (date) | `created_at` (date) |
| `order_timestamp` | `openedDate` | `created_at` | `created_at` |
| `closed_timestamp` | `closedDate` | `delivery_time` or `pickup_time` | `closed_at` |
| `paid_timestamp` | `paidDate` | `created_at` | `closed_at` |
| `order_type` | `diningOption.behavior` | `order_fulfillment_method` | `fulfillments[0].type` |
| `source_type` | `source` | `'THIRD_PARTY'` | `source.name` |
| `subtotal_cents` | Sum of check `amount` | `order_subtotal` | Sum of line items |
| `tax_cents` | Sum of check `taxAmount` | `tax_amount` | `total_tax_money.amount` |
| `tip_cents` | Sum of check `tipAmount` | `dasher_tip` | `total_tip_money.amount` |
| `service_fee_cents` | 0 | `service_fee` | 0 |
| `delivery_fee_cents` | 0 | `delivery_fee` | 0 |
| `total_cents` | Sum of check `totalAmount` | `total_charged_to_consumer` | `total_money.amount` |
| `commission_cents` | 0 | `commission` | 0 |
| `merchant_payout_cents` | `total_cents` | `merchant_payout` | `total_cents` |
| `status` | Based on `voided` | `order_status` | `state` |
| `voided` | `voided` | `false` | `false` (check state) |

### Order Type Mapping

| Source Value | Unified Value |
|--------------|---------------|
| Toast: `DINE_IN` | `DINE_IN` |
| Toast: `TAKE_OUT` | `TAKE_OUT` |
| Toast: `DELIVERY` | `DELIVERY` |
| DoorDash: `MERCHANT_DELIVERY` | `DELIVERY` |
| DoorDash: `PICKUP` | `PICKUP` |
| Square: `DINE_IN` | `DINE_IN` |
| Square: `PICKUP` | `PICKUP` |

## Order Item Mapping

| Unified Field | Toast | DoorDash | Square |
|---------------|-------|----------|--------|
| `order_id` | From `check.order_guid` | `order_id` | `order_id` |
| `unified_product_id` | Matched via `product_name_mapping` | Matched via `product_name_mapping` | Matched via `catalog_object_id` → `variation_id` → product |
| `source_item_id` | `selection.item.guid` | `item_id` | `catalog_object_id` |
| `product_name` | `selection.displayName` | `item.name` | Lookup from catalog |
| `normalized_product_name` | Cleaned `displayName` | Cleaned `name` | Cleaned catalog name |
| `category_name` | `selection.itemGroup.name` | `item.category` | Lookup from catalog |
| `quantity` | `selection.quantity` | `item.quantity` | `line_item.quantity` |
| `unit_price_cents` | `selection.price` | `item.unit_price` | `line_item.gross_sales_money.amount / quantity` |
| `total_price_cents` | `selection.price * quantity` | `item.total_price` | `line_item.total_money.amount` |
| `tax_cents` | `selection.tax` | 0 (tax at order level) | 0 (tax at order level) |
| `special_instructions` | N/A | `item.special_instructions` | N/A |

**Note**: Toast items are nested in `orders → checks → selections`. DoorDash and Square items are directly under orders.

## Payment Mapping

| Unified Field | Toast | DoorDash | Square |
|---------------|-------|----------|--------|
| `order_id` | From `check.order_guid` | N/A (payments handled by platform) | `order_id` |
| `source_payment_id` | `payment.guid` | N/A | `payment.id` |
| `payment_timestamp` | `payment.paidDate` | N/A | `payment.created_at` |
| `payment_date` | `payment.paidBusinessDate` | N/A | `payment.created_at` (date) |
| `payment_type` | `payment.type` | N/A | `payment.source_type` |
| `card_brand` | `payment.cardType` | N/A | `payment.card_details.card.card_brand` |
| `card_last_4` | `payment.last4Digits` | N/A | `payment.card_details.card.last_4` |
| `wallet_type` | N/A (in `cardType`) | N/A | `payment.wallet_details.brand` |
| `amount_cents` | `payment.amount` | N/A | `payment.amount_money.amount` |
| `tip_cents` | `payment.tipAmount` | N/A | `payment.tip_money.amount` |
| `processing_fee_cents` | `payment.originalProcessingFee` | N/A | 0 |
| `status` | Based on `refundStatus` | N/A | `payment.status` |
| `refund_status` | `payment.refundStatus` | N/A | N/A |

### Payment Type Mapping

| Source Value | Unified Value |
|--------------|---------------|
| Toast: `CREDIT` | `CREDIT` |
| Toast: `CASH` | `CASH` |
| Toast: `OTHER` | `OTHER` (check `cardType` for wallet) |
| Square: `CARD` | `CREDIT` or `DEBIT` (determine by card type) |
| Square: `CASH` | `CASH` |
| Square: `WALLET` | `WALLET` |

### Card Brand Mapping

| Source Value | Unified Value |
|--------------|---------------|
| `VISA` | `VISA` |
| `MASTERCARD` | `MASTERCARD` |
| `AMEX` | `AMEX` |
| `DISCOVER` | `DISCOVER` |
| `APPLE_PAY` | `APPLE_PAY` (wallet_type) |
| `GOOGLE_PAY` | `GOOGLE_PAY` (wallet_type) |

## Product/Catalog Mapping

### Toast Products
- Stored in `toast_menu_items` (extracted from order selections)
- Category from `toast_menu_groups`
- No separate catalog file

### DoorDash Products
- Stored in order items (no separate catalog)
- Category from `order_items.category`
- Items identified by `item_id`

### Square Products
- Catalog stored in `square/catalog.json`
- Structure: `objects[]` with type `ITEM`, `CATEGORY`, `MODIFIER_LIST`
- Items have variations (sizes, types)
- Items linked to categories via `category_id`
- Items linked to locations via `present_at_location_ids`

### Unified Product Matching

Products are matched using the following strategy:

1. **Square Catalog** (most complete):
   - Use `square_catalog_items` as base
   - Match variations to products

2. **Toast Products** (from orders):
   - Match `selection.item.name` or `selection.displayName`
   - Link to categories via `selection.itemGroup.name`

3. **DoorDash Products** (from orders):
   - Match `order_item.name`
   - Link to categories via `order_item.category`

## Category Mapping

| Unified Category | Toast Examples | DoorDash Examples | Square Examples |
|------------------|----------------|-------------------|-----------------|
| `Burgers` | 🍔 Burgers | Entrees | 🍔 Burgers |
| `Sides` | 🍟 Sides | Sides | 🍟 Sides & Appetizers |
| `Beverages` | 🥤 Beverages | 🥤 Drinks / Beverages | Drinks |
| `Breakfast` | Breakfast | Breakfast | 🌅 Breakfast |
| `Desserts` | 🍰 Desserts | (in Entrees) | 🍰 Desserts |
| `Alcohol` | Wine | Beverages | Beer & Wine |
| `Entrees` | Entrees | Entrees | Entrees |
| `Sandwiches` | Sandwiches | Entrees | Sandwiches |
| `Salads` | Salads | Salads | (in Sides) |
| `Appetizers` | (in Sides) | Appetizers / 🍗 Appetizers | (in Sides & Appetizers) |

**Note**: Categories require normalization to remove emojis and standardize names.

## Modifier Mapping

| Unified Field | Toast | DoorDash | Square |
|---------------|-------|----------|--------|
| `order_item_id` | `selection_guid` | `order_item_id` | `line_item_uid` |
| `modifier_name` | `modifier.displayName` | `option.name` | Lookup from `modifier_id` |
| `price_cents` | `modifier.price` | `option.price` | Lookup from modifier catalog |

**Note**: Square modifiers are referenced by ID and must be looked up from the catalog.

## Data Ingestion Flow

```
1. Locations
   └─> unified_locations + location_id_mapping

2. Categories (Square catalog first)
   └─> unified_categories

3. Products (Square catalog first, then match Toast/DoorDash)
   └─> unified_products + product_name_mapping

4. Orders
   └─> unified_orders

5. Order Items (with product matching)
   └─> unified_order_items + unified_order_item_modifiers

6. Payments (Toast and Square only)
   └─> unified_payments
```

## Common Transformation Patterns

### 1. Extract Date from Timestamp
```sql
-- Toast
DATE(businessDate)

-- DoorDash  
DATE(created_at)

-- Square
DATE(created_at)
```

### 2. Convert Order Type
```sql
-- Toast
CASE dining_option.behavior
    WHEN 'DINE_IN' THEN 'DINE_IN'
    WHEN 'TAKE_OUT' THEN 'TAKE_OUT'
    WHEN 'DELIVERY' THEN 'DELIVERY'
END

-- DoorDash
CASE order_fulfillment_method
    WHEN 'MERCHANT_DELIVERY' THEN 'DELIVERY'
    WHEN 'PICKUP' THEN 'PICKUP'
END

-- Square
CASE fulfillment.type
    WHEN 'DINE_IN' THEN 'DINE_IN'
    WHEN 'PICKUP' THEN 'PICKUP'
END
```

### 3. Normalize Product Name
```sql
-- Remove emojis, lowercase, trim
REGEXP_REPLACE(LOWER(TRIM(product_name)), '[^\w\s]', '', 'g')
```

### 4. Calculate Unit Price
```sql
-- Toast: Already per unit
selection.price

-- DoorDash: Already per unit
order_item.unit_price

-- Square: Calculate from total
line_item.gross_sales_money.amount / line_item.quantity
```




