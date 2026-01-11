# Data Source Guide

These data sources simulate real restaurant data from DoorDash, Square, and Toast POS systems. Each has its own structure and quirks.

Your task is to parse these files, clean the data, and normalize into a unified schema for querying and visualization.

## Source Structure

### Toast POS (`toast_pos_export.json`)
- Single JSON file with restaurant, locations, and orders
- Orders contain `checks` → `selections` (items) → `modifiers`
- Payments are nested inside checks

### DoorDash (`doordash_orders.json`)
- Single JSON file with merchant, stores, and orders
- Flat order structure with `order_items[]`
- Delivery fees, commissions, and tips at order level

### Square POS (`square/` folder)
- **Split across 4 files** like the real API:
  - `catalog.json` - Items, variations, categories, modifiers
  - `orders.json` - Orders with line_items (reference catalog by ID)
  - `payments.json` - Payments (reference orders by ID)
  - `locations.json` - Location details

## Location Mapping

All sources represent the same 4 locations:

| Location Name | Toast GUID | DoorDash Store ID | Square Location ID |
|--------------|------------|-------------------|-------------------|
| Downtown | `loc_downtown_001` | `str_downtown_001` | `LCN001DOWNTOWN` |
| Airport | `loc_airport_002` | `str_airport_002` | `LCN002AIRPORT` |
| Mall Location | `loc_mall_003` | `str_mall_003` | `LCN003MALL` |
| University | `loc_univ_004` | `str_university_004` | `LCN004UNIV` |

## Data Cleaning Challenges

**Expect real-world messiness:**

| Issue | Examples |
|-------|----------|
| **Typos** | "Griled Chiken", "expresso", "coffe", "Appitizers" |
| **Inconsistent naming** | "Hash Browns" vs "Hashbrowns" vs "Hashbrowns" |
| **Categories** | "🍔 Burgers" vs "Burgers" vs "BURGERS" |
| **Baked-in variations** | "Churros 12pcs" vs "Churros" + variation "12 piece" |
| **Format differences** | "Lg Coke" vs "Large Coca-Cola" vs "fountain soda" |
| **Case inconsistency** | "nachos supreme" vs "Nachos Supreme" |

**You'll need to decide:**
- How to match "similar" products across sources
- Whether "French Fries" and "Fries - Large" are the same item
- How to normalize categories with emojis
- How to handle quantities baked into names

## Data Date Range

All sources contain transactions from **January 1-4, 2025**.

Good luck! 🚀
