-- =====================================================
-- Unified Restaurant Data Schema
-- =====================================================
-- This schema unifies data from Toast POS, DoorDash, and Square
-- Designed for natural language querying and analytics

-- =====================================================
-- CORE REFERENCE TABLES
-- =====================================================

-- Unified Locations
CREATE TABLE unified_locations (
    location_id SERIAL PRIMARY KEY,
    location_code VARCHAR(50) UNIQUE NOT NULL, -- 'DOWNTOWN', 'AIRPORT', 'MALL', 'UNIVERSITY'
    location_name VARCHAR(255) NOT NULL,
    address_line1 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(2) DEFAULT 'US',
    timezone VARCHAR(100) DEFAULT 'America/New_York',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Location ID Mapping (maps source-specific IDs to unified location_id)
CREATE TABLE location_id_mapping (
    mapping_id SERIAL PRIMARY KEY,
    unified_location_id INTEGER NOT NULL,
    source_system VARCHAR(50) NOT NULL, -- 'toast', 'doordash', 'square'
    source_location_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (unified_location_id) REFERENCES unified_locations(location_id) ON DELETE CASCADE,
    UNIQUE(source_system, source_location_id)
);

CREATE INDEX idx_source_location ON location_id_mapping (source_system, source_location_id);

-- Unified Categories (normalized, emoji-free)
CREATE TABLE unified_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255), -- Original name with emojis if applicable
    parent_category_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES unified_categories(category_id)
);

CREATE INDEX idx_category_name ON unified_categories (category_name);

-- Unified Products (Menu Items)
CREATE TABLE unified_products (
    product_id SERIAL PRIMARY KEY,
    product_code VARCHAR(100) UNIQUE, -- Standardized code for matching
    product_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL, -- Cleaned, standardized name
    category_id INTEGER,
    description TEXT,
    is_alcohol BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES unified_categories(category_id)
);

CREATE INDEX idx_product_code ON unified_products (product_code);
CREATE INDEX idx_normalized_name ON unified_products (normalized_name);
CREATE INDEX idx_category_id ON unified_products (category_id);

-- Product Name Mapping (maps source-specific product names to unified products)
CREATE TABLE product_name_mapping (
    mapping_id SERIAL PRIMARY KEY,
    unified_product_id INTEGER NOT NULL,
    source_system VARCHAR(50) NOT NULL, -- 'toast', 'doordash', 'square'
    source_product_name VARCHAR(255) NOT NULL,
    source_item_id VARCHAR(255), -- Source-specific item ID if available
    confidence_score DECIMAL(3,2) DEFAULT 1.0, -- Matching confidence (0.0-1.0)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (unified_product_id) REFERENCES unified_products(product_id) ON DELETE CASCADE
);

CREATE INDEX idx_source_product ON product_name_mapping (source_system, source_product_name);
CREATE INDEX idx_unified_product_mapping ON product_name_mapping (unified_product_id);

-- =====================================================
-- ORDER TABLES
-- =====================================================

-- Unified Orders
CREATE TABLE unified_orders (
    order_id SERIAL PRIMARY KEY,
    unified_location_id INTEGER NOT NULL,
    source_system VARCHAR(50) NOT NULL, -- 'toast', 'doordash', 'square'
    source_order_id VARCHAR(255) NOT NULL, -- Original order ID from source
    external_order_id VARCHAR(255), -- External reference (e.g., DoorDash delivery ID)
    
    -- Order Timing
    order_date DATE NOT NULL,
    order_timestamp TIMESTAMP NOT NULL,
    closed_timestamp TIMESTAMP,
    paid_timestamp TIMESTAMP,
    
    -- Order Type
    order_type VARCHAR(50) NOT NULL, -- 'DINE_IN', 'TAKE_OUT', 'DELIVERY', 'PICKUP'
    source_type VARCHAR(50) DEFAULT 'POS', -- 'POS', 'ONLINE', 'THIRD_PARTY'
    
    -- Financial Summary (all in cents)
    subtotal_cents BIGINT NOT NULL DEFAULT 0,
    tax_cents BIGINT NOT NULL DEFAULT 0,
    tip_cents BIGINT DEFAULT 0,
    service_fee_cents BIGINT DEFAULT 0, -- Delivery/platform service fees
    delivery_fee_cents BIGINT DEFAULT 0,
    discount_cents BIGINT DEFAULT 0,
    total_cents BIGINT NOT NULL,
    
    -- Third-party specific
    commission_cents BIGINT DEFAULT 0, -- Platform commission (DoorDash)
    merchant_payout_cents BIGINT, -- Amount merchant receives (DoorDash)
    
    -- Order Status
    status VARCHAR(50) DEFAULT 'COMPLETED', -- COMPLETED, CANCELLED, REFUNDED
    voided BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    server_name VARCHAR(255), -- Server/employee name
    customer_name VARCHAR(255), -- Customer name if available
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (unified_location_id) REFERENCES unified_locations(location_id),    
    UNIQUE(source_system, source_order_id)
);

CREATE INDEX idx_order_date ON unified_orders (order_date);
CREATE INDEX idx_order_timestamp ON unified_orders (order_timestamp);
CREATE INDEX idx_location_date ON unified_orders (unified_location_id, order_date);
CREATE INDEX idx_source_order ON unified_orders (source_system, source_order_id);
CREATE INDEX idx_order_type ON unified_orders (order_type);
CREATE INDEX idx_status ON unified_orders (status);

-- Unified Order Items
CREATE TABLE unified_order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    unified_product_id INTEGER, -- NULL if product couldn't be matched
    source_item_id VARCHAR(255), -- Original item ID from source
    
    -- Product Information (denormalized for performance)
    product_name VARCHAR(255) NOT NULL, -- Original name from source
    normalized_product_name VARCHAR(255), -- Cleaned name
    category_name VARCHAR(255), -- Original category from source
    
    -- Quantity and Pricing (all in cents)
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price_cents BIGINT NOT NULL,
    total_price_cents BIGINT NOT NULL,
    tax_cents BIGINT DEFAULT 0,
    
    -- Modifiers/Special Instructions
    special_instructions TEXT,
    
    -- Matching metadata
    source_system VARCHAR(50) NOT NULL,
    match_confidence DECIMAL(3,2) DEFAULT 1.0, -- Product matching confidence
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id) REFERENCES unified_orders(order_id) ON DELETE CASCADE,   
    FOREIGN KEY (unified_product_id) REFERENCES unified_products(product_id)
);

CREATE INDEX idx_order_item_order_id ON unified_order_items (order_id);
CREATE INDEX idx_order_item_product_id ON unified_order_items (unified_product_id);
CREATE INDEX idx_order_item_product_name ON unified_order_items (product_name);

-- Order Item Modifiers
CREATE TABLE unified_order_item_modifiers (
    modifier_id SERIAL PRIMARY KEY,
    order_item_id INTEGER NOT NULL,
    modifier_name VARCHAR(255) NOT NULL,
    price_cents BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_item_id) REFERENCES unified_order_items(order_item_id) ON DELETE CASCADE
);

CREATE INDEX idx_modifier_order_item_id ON unified_order_item_modifiers (order_item_id);

-- =====================================================
-- PAYMENT TABLES
-- =====================================================

-- Unified Payments
CREATE TABLE unified_payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    source_payment_id VARCHAR(255) NOT NULL,
    
    -- Payment Timing
    payment_timestamp TIMESTAMP NOT NULL,
    payment_date DATE NOT NULL,
    
    -- Payment Method
    payment_type VARCHAR(50) NOT NULL, -- 'CREDIT', 'DEBIT', 'CASH', 'WALLET', 'OTHER'
    card_brand VARCHAR(50), -- VISA, MASTERCARD, AMEX, DISCOVER
    card_last_4 VARCHAR(4),
    wallet_type VARCHAR(50), -- APPLE_PAY, GOOGLE_PAY
    
    -- Payment Amounts (all in cents)
    amount_cents BIGINT NOT NULL,
    tip_cents BIGINT DEFAULT 0,
    processing_fee_cents BIGINT DEFAULT 0,
    
    -- Status
    status VARCHAR(50) DEFAULT 'COMPLETED',
    refund_status VARCHAR(50) DEFAULT 'NONE', -- NONE, PARTIAL, FULL
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id) REFERENCES unified_orders(order_id) ON DELETE CASCADE,   
    UNIQUE(source_system, source_payment_id)
);

CREATE INDEX idx_payment_order_id ON unified_payments (order_id);
CREATE INDEX idx_payment_date ON unified_payments (payment_date);
CREATE INDEX idx_payment_timestamp ON unified_payments (payment_timestamp);
CREATE INDEX idx_payment_type ON unified_payments (payment_type);

-- =====================================================
-- NOTE: Analytics are provided via materialized views (mv_*)
-- Create materialized views using: python etl/scripts/database/create_materialized_views.py
-- This project uses ONLY materialized views (mv_*) - no regular views
-- =====================================================

