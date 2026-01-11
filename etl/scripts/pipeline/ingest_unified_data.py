"""
Unified Schema Data Ingestion Script
Ingests data from all three sources (Toast, DoorDash, Square) into the unified schema
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from sqlalchemy import text
from tqdm import tqdm

# Setup paths BEFORE importing scripts modules
# Add etl directory to sys.path so we can import scripts.* (scripts is in etl/scripts/)
from pathlib import Path
_script_dir = Path(__file__).parent.parent  # pipeline -> scripts
_etl_dir = _script_dir.parent  # scripts -> etl
_etl_dir_str = str(_etl_dir)
if _etl_dir_str not in sys.path:
    sys.path.insert(0, _etl_dir_str)

# Setup paths (adds parent directory to sys.path)
from scripts.core.paths import setup_script_paths
setup_script_paths()

from scripts.database.db_connection import get_db_connection, test_connection
from scripts.utils.text_normalization import (
    normalize_text, normalize_category, normalize_product_name, create_product_code
)
from scripts.utils.product_matcher import ProductMatcher
from scripts.config.product_matching_config import (
    LOCATION_MAPPINGS, LOCATION_DETAILS, CATEGORY_NORMALIZATION
)


class UnifiedDataIngester:
    """Ingests data from all sources into unified schema."""
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.location_map = {}  # {source_system: {source_id: unified_location_id}}
        self.category_map = {}  # {normalized_name: category_id}
        self.product_matcher = ProductMatcher()
        self.stats = {
            'locations': 0,
            'categories': 0,
            'products': 0,
            'orders': 0,
            'order_items': 0,
            'payments': 0,
        }
    
    def setup_reference_data(self):
        """Set up locations and categories in unified schema."""
        print("Setting up reference data (locations, categories)...")
        
        # 1. Insert unified locations
        for location_code, details in LOCATION_DETAILS.items():
            query = text("""
                INSERT INTO unified_locations (
                    location_code, location_name, address_line1, city, state,
                    zip_code, country, timezone
                )
                VALUES (
                    :code, :name, :line1, :city, :state, :zip, :country, :timezone
                )
                ON CONFLICT (location_code) DO UPDATE
                SET location_name = EXCLUDED.location_name,
                    address_line1 = EXCLUDED.address_line1,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    zip_code = EXCLUDED.zip_code,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING location_id
            """)
            result = self.db_conn.execute(query, {
                'code': location_code,
                'name': details['name'],
                'line1': details['address_line1'],
                'city': details['city'],
                'state': details['state'],
                'zip': details['zip_code'],
                'country': details['country'],
                'timezone': details['timezone'],
            })
            unified_location_id = result.fetchone()[0]
            
            # 2. Create location mappings for all sources
            for source_system, source_mappings in LOCATION_MAPPINGS.items():
                if location_code in source_mappings.values():
                    # Find source ID for this location code
                    source_id = None
                    for sid, code in source_mappings.items():
                        if code == location_code:
                            source_id = sid
                            break
                    
                    if source_id:
                        if source_system not in self.location_map:
                            self.location_map[source_system] = {}
                        
                        # Insert mapping
                        map_query = text("""
                            INSERT INTO location_id_mapping (
                                unified_location_id, source_system, source_location_id
                            )
                            VALUES (:unified_id, :source, :source_id)
                            ON CONFLICT (source_system, source_location_id) DO NOTHING
                        """)
                        self.db_conn.execute(map_query, {
                            'unified_id': unified_location_id,
                            'source': source_system,
                            'source_id': source_id,
                        })
                        self.location_map[source_system][source_id] = unified_location_id
        
        # 3. Load existing categories
        cat_query = text("SELECT category_id, category_name FROM unified_categories")
        categories = self.db_conn.execute(cat_query).fetchall()
        for cat_id, cat_name in categories:
            self.category_map[cat_name.lower()] = cat_id
        
        # 4. Load existing products for matcher
        prod_query = text("SELECT product_id, product_code FROM unified_products")
        products = self.db_conn.execute(prod_query).fetchall()
        for prod_id, prod_code in products:
            if prod_code:
                self.product_matcher.add_product(prod_code, prod_id)
        
        locations_count = len(LOCATION_DETAILS)
        self.stats['locations'] = locations_count
        print(f"✓ Set up {locations_count} locations")
        self.db_conn.commit()
    
    def get_or_create_category(self, category_name: str) -> int:
        """Get or create category, return category_id."""
        if not category_name:
            return None
        
        normalized = normalize_category(category_name)
        key = normalized.lower()
        
        if key in self.category_map:
            return self.category_map[key]
        
        # Create new category
        query = text("""
            INSERT INTO unified_categories (category_name, display_name)
            VALUES (:name, :display)
            ON CONFLICT (category_name) DO UPDATE
            SET display_name = EXCLUDED.display_name
            RETURNING category_id
        """)
        result = self.db_conn.execute(query, {
            'name': normalized,
            'display': category_name,
        })
        cat_id = result.fetchone()[0]
        self.category_map[key] = cat_id
        self.stats['categories'] += 1
        return cat_id
    
    def get_or_create_product(
        self, product_name: str, category_name: str, source_system: str
    ) -> Tuple[int, float]:
        """
        Get or create product, return (product_id, confidence_score).
        """
        if not product_name:
            return None, 0.0
        
        # Try to match existing product
        product_id, confidence, match_type = self.product_matcher.match_product(
            product_name, source_system
        )
        
        if product_id:
            return product_id, confidence
        
        # Create new product
        normalized = normalize_product_name(product_name, preserve_case=True)
        product_code = create_product_code(product_name)
        category_id = self.get_or_create_category(category_name) if category_name else None
        
        query = text("""
            INSERT INTO unified_products (
                product_code, product_name, normalized_name, category_id
            )
            VALUES (:code, :name, :norm_name, :cat_id)
            ON CONFLICT (product_code) DO UPDATE
            SET product_name = EXCLUDED.product_name,
                normalized_name = EXCLUDED.normalized_name
            RETURNING product_id
        """)
        result = self.db_conn.execute(query, {
            'code': product_code,
            'name': product_name,
            'norm_name': normalized,
            'cat_id': category_id,
        })
        new_product_id = result.fetchone()[0]
        
        # Add to matcher
        self.product_matcher.add_product(product_code, new_product_id)
        
        # Add to product_name_mapping (check if exists first)
        check_map_query = text("""
            SELECT mapping_id FROM product_name_mapping
            WHERE unified_product_id = :prod_id AND source_system = :source
            AND source_product_name = :source_name
            LIMIT 1
        """)
        existing = self.db_conn.execute(check_map_query, {
            'prod_id': new_product_id,
            'source': source_system,
            'source_name': product_name,
        }).fetchone()
        
        if not existing:
            map_query = text("""
                INSERT INTO product_name_mapping (
                    unified_product_id, source_system, source_product_name,
                    source_item_id, confidence_score
                )
                VALUES (:prod_id, :source, :source_name, :item_id, :confidence)
            """)
            self.db_conn.execute(map_query, {
                'prod_id': new_product_id,
                'source': source_system,
                'source_name': product_name,
                'item_id': None,
                'confidence': 1.0,
            })
        
        self.stats['products'] += 1
        return new_product_id, 1.0
    
    def get_unified_location_id(self, source_system: str, source_location_id: str) -> Optional[int]:
        """Get unified location ID from source location ID."""
        if source_system in self.location_map:
            return self.location_map[source_system].get(source_location_id)
        return None
    
    def parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not dt_str:
            return None
        try:
            # Handle ISO format with Z
            dt_str = dt_str.replace('Z', '+00:00')
            return datetime.fromisoformat(dt_str)
        except:
            return None
    
    def ingest_toast_data(self, data_file: str):
        """Ingest Toast POS data."""
        print("\n" + "="*60)
        print("Ingesting Toast POS data...")
        print("="*60)
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for order in tqdm(data.get('orders', []), desc="Processing Toast orders"):
            # Get unified location ID
            source_loc_id = order.get('restaurantGuid')
            unified_loc_id = self.get_unified_location_id('toast', source_loc_id)
            if not unified_loc_id:
                continue
            
            # Process each check as a separate order
            for check in order.get('checks', []):
                check_guid = check.get('guid')
                
                # Parse dates
                order_date = datetime.fromisoformat(order.get('businessDate')).date()
                opened_ts = self.parse_datetime(order.get('openedDate'))
                closed_ts = self.parse_datetime(order.get('closedDate'))
                paid_ts = self.parse_datetime(order.get('paidDate'))
                
                dining_option = order.get('diningOption', {})
                order_type = dining_option.get('behavior', 'DINE_IN')
                # Preserve 'TAKE_OUT' as-is (schema supports it)
                
                server = order.get('server', {})
                server_name = f"{server.get('firstName', '')} {server.get('lastName', '')}".strip() or None
                
                # Insert Order
                order_query = text("""
                    INSERT INTO unified_orders (
                        unified_location_id, source_system, source_order_id, external_order_id,
                        order_date, order_timestamp, closed_timestamp, paid_timestamp,
                        order_type, source_type, subtotal_cents, tax_cents, tip_cents,
                        total_cents, status, voided, server_name
                    )
                    VALUES (
                        :loc_id, 'toast', :source_order_id, :ext_id,
                        :order_date, :order_ts, :closed_ts, :paid_ts,
                        :order_type, :source_type, :subtotal, :tax, :tip,
                        :total, :status, :voided, :server_name
                    )
                    ON CONFLICT (source_system, source_order_id) DO NOTHING
                    RETURNING order_id
                """)
                result = self.db_conn.execute(order_query, {
                    'loc_id': unified_loc_id,
                    'source_order_id': check_guid,
                    'ext_id': order.get('externalId'),
                    'order_date': order_date,
                    'order_ts': opened_ts,
                    'closed_ts': closed_ts,
                    'paid_ts': paid_ts,
                    'order_type': order_type,
                    'source_type': order.get('source', 'POS'),
                    'subtotal': check.get('amount', 0),
                    'tax': check.get('taxAmount', 0),
                    'tip': check.get('tipAmount', 0),
                    'total': check.get('totalAmount', 0),
                    'status': 'COMPLETED' if not order.get('voided') else 'CANCELLED',
                    'voided': order.get('voided', False),
                    'server_name': server_name,
                })
                
                row = result.fetchone()
                if not row:
                    # Order already exists, get its ID
                    get_order_query = text("""
                        SELECT order_id FROM unified_orders
                        WHERE source_system = 'toast' AND source_order_id = :source_order_id
                    """)
                    row = self.db_conn.execute(get_order_query, {'source_order_id': check_guid}).fetchone()
                
                if not row:
                    continue
                
                order_id = row[0]
                self.stats['orders'] += 1
                
                # Insert Order Items
                for selection in check.get('selections', []):
                    if selection.get('voided'):
                        continue
                    
                    item_group = selection.get('itemGroup', {})
                    category_name = item_group.get('name', '')
                    product_name = selection.get('displayName', '')
                    
                    # Normalize category name (remove emojis) for storage
                    normalized_category_name = normalize_category(category_name) if category_name else None
                    
                    product_id, confidence = self.get_or_create_product(
                        product_name, category_name, 'toast'
                    )
                    
                    quantity = selection.get('quantity', 1)
                    price_total = selection.get('price', 0)
                    unit_price = price_total // quantity if quantity > 0 else 0
                    
                    item_query = text("""
                        INSERT INTO unified_order_items (
                            order_id, unified_product_id, source_item_id,
                            product_name, normalized_product_name, category_name,
                            quantity, unit_price_cents, total_price_cents, tax_cents,
                            source_system, match_confidence
                        )
                        VALUES (
                            :order_id, :prod_id, :source_item_id,
                            :prod_name, :norm_name, :cat_name,
                            :qty, :unit_price, :total_price, :tax,
                            'toast', :confidence
                        )
                        RETURNING order_item_id
                    """)
                    result = self.db_conn.execute(item_query, {
                        'order_id': order_id,
                        'prod_id': product_id,
                        'source_item_id': selection.get('item', {}).get('guid'),
                        'prod_name': product_name,
                        'norm_name': normalize_product_name(product_name, preserve_case=True),
                        'cat_name': normalized_category_name,
                        'qty': quantity,
                        'unit_price': unit_price,
                        'total_price': price_total,
                        'tax': selection.get('tax', 0),
                        'confidence': confidence,
                    })
                    
                    order_item_id = result.fetchone()[0]
                    self.stats['order_items'] += 1
                    
                    # Insert Modifiers
                    for modifier in selection.get('modifiers', []):
                        mod_query = text("""
                            INSERT INTO unified_order_item_modifiers (
                                order_item_id, modifier_name, price_cents
                            )
                            VALUES (:item_id, :name, :price)
                        """)
                        self.db_conn.execute(mod_query, {
                            'item_id': order_item_id,
                            'name': modifier.get('displayName', ''),
                            'price': modifier.get('price', 0),
                        })
                
                # Insert Payments
                for payment in check.get('payments', []):
                    paid_ts = self.parse_datetime(payment.get('paidDate'))
                    if not paid_ts:
                        continue
                    
                    paid_date = paid_ts.date()
                    payment_type = payment.get('type', 'CREDIT')
                    card_type = payment.get('cardType')
                    
                    # Handle wallet types (Apple Pay, Google Pay in cardType for Toast)
                    wallet_type = None
                    if payment_type == 'OTHER' and card_type in ['APPLE_PAY', 'GOOGLE_PAY']:
                        wallet_type = card_type
                        payment_type = 'WALLET'
                    
                    pay_query = text("""
                        INSERT INTO unified_payments (
                            order_id, source_system, source_payment_id,
                            payment_timestamp, payment_date,
                            payment_type, card_brand, card_last_4, wallet_type,
                            amount_cents, tip_cents, processing_fee_cents,
                            status, refund_status
                        )
                        VALUES (
                            :order_id, 'toast', :source_payment_id,
                            :pay_ts, :pay_date,
                            :pay_type, :card_brand, :last4, :wallet_type,
                            :amount, :tip, :fee,
                            'COMPLETED', :refund_status
                        )
                        ON CONFLICT (source_system, source_payment_id) DO NOTHING
                    """)
                    self.db_conn.execute(pay_query, {
                        'order_id': order_id,
                        'source_payment_id': payment.get('guid'),
                        'pay_ts': paid_ts,
                        'pay_date': paid_date,
                        'pay_type': payment_type,
                        'card_brand': card_type if payment_type != 'WALLET' else None,
                        'last4': payment.get('last4Digits'),
                        'wallet_type': wallet_type,
                        'amount': payment.get('amount', 0),
                        'tip': payment.get('tipAmount', 0),
                        'fee': payment.get('originalProcessingFee', 0),
                        'refund_status': payment.get('refundStatus', 'NONE'),
                    })
                    self.stats['payments'] += 1
        
        self.db_conn.commit()
        print("✓ Toast data ingestion completed")
    
    def ingest_doordash_data(self, data_file: str):
        """Ingest DoorDash order data."""
        print("\n" + "="*60)
        print("Ingesting DoorDash data...")
        print("="*60)
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for order in tqdm(data.get('orders', []), desc="Processing DoorDash orders"):
            # Get unified location ID
            source_loc_id = order.get('store_id')
            unified_loc_id = self.get_unified_location_id('doordash', source_loc_id)
            if not unified_loc_id:
                continue
            
            # Parse dates
            created_ts = self.parse_datetime(order.get('created_at'))
            pickup_ts = self.parse_datetime(order.get('pickup_time'))
            delivery_ts = self.parse_datetime(order.get('delivery_time'))
            order_date = created_ts.date() if created_ts else None
            if not order_date:
                continue
            
            # Determine order type
            fulfillment_method = order.get('order_fulfillment_method', '')
            if fulfillment_method == 'MERCHANT_DELIVERY':
                order_type = 'DELIVERY'
            elif fulfillment_method == 'PICKUP':
                order_type = 'PICKUP'
            else:
                order_type = 'DELIVERY'
            
            # Customer name
            customer = order.get('customer', {})
            customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or None
            
            # Order status
            order_status = order.get('order_status', 'DELIVERED')
            status = 'COMPLETED' if order_status == 'DELIVERED' or order_status == 'PICKED_UP' else 'CANCELLED'
            
            # Insert Order
            order_query = text("""
                INSERT INTO unified_orders (
                    unified_location_id, source_system, source_order_id, external_order_id,
                    order_date, order_timestamp, closed_timestamp, paid_timestamp,
                    order_type, source_type, subtotal_cents, tax_cents, tip_cents,
                    service_fee_cents, delivery_fee_cents, total_cents,
                    commission_cents, merchant_payout_cents, status, customer_name
                )
                VALUES (
                    :loc_id, 'doordash', :source_order_id, :ext_order_id,
                    :order_date, :order_ts, :closed_ts, :paid_ts,
                    :order_type, 'THIRD_PARTY', :subtotal, :tax, :tip,
                    :service_fee, :delivery_fee, :total,
                    :commission, :payout, :status, :customer_name
                )
                ON CONFLICT (source_system, source_order_id) DO NOTHING
                RETURNING order_id
            """)
            result = self.db_conn.execute(order_query, {
                'loc_id': unified_loc_id,
                'source_order_id': order.get('external_delivery_id'),
                'ext_order_id': order.get('external_delivery_id'),
                'order_date': order_date,
                'order_ts': created_ts,
                'closed_ts': delivery_ts or pickup_ts,
                'paid_ts': created_ts,  # DoorDash orders are prepaid
                'order_type': order_type,
                'subtotal': order.get('order_subtotal', 0),
                'tax': order.get('tax_amount', 0),
                'tip': order.get('dasher_tip', 0),  # Tip to driver, not restaurant
                'service_fee': order.get('service_fee', 0),
                'delivery_fee': order.get('delivery_fee', 0),
                'total': order.get('total_charged_to_consumer', 0),
                'commission': order.get('commission', 0),
                'payout': order.get('merchant_payout', 0),
                'status': status,
                'customer_name': customer_name,
            })
            
            row = result.fetchone()
            if not row:
                get_order_query = text("""
                    SELECT order_id FROM unified_orders
                    WHERE source_system = 'doordash' AND source_order_id = :source_order_id
                """)
                row = self.db_conn.execute(get_order_query, {
                    'source_order_id': order.get('external_delivery_id')
                }).fetchone()
            
            if not row:
                continue
            
            order_id = row[0]
            self.stats['orders'] += 1
            
            # Insert Order Items
            for item in order.get('order_items', []):
                product_name = item.get('name', '')
                category_name = item.get('category', '')
                
                # Normalize category name (remove emojis) for storage
                normalized_category_name = normalize_category(category_name) if category_name else None
                
                product_id, confidence = self.get_or_create_product(
                    product_name, category_name, 'doordash'
                )
                
                quantity = item.get('quantity', 1)
                unit_price = item.get('unit_price', 0)
                total_price = item.get('total_price', 0)
                
                item_query = text("""
                    INSERT INTO unified_order_items (
                        order_id, unified_product_id, source_item_id,
                        product_name, normalized_product_name, category_name,
                        quantity, unit_price_cents, total_price_cents,
                        special_instructions, source_system, match_confidence
                    )
                    VALUES (
                        :order_id, :prod_id, :source_item_id,
                        :prod_name, :norm_name, :cat_name,
                        :qty, :unit_price, :total_price,
                        :instructions, 'doordash', :confidence
                    )
                    RETURNING order_item_id
                """)
                result = self.db_conn.execute(item_query, {
                    'order_id': order_id,
                    'prod_id': product_id,
                    'source_item_id': item.get('item_id'),
                    'prod_name': product_name,
                    'norm_name': normalize_product_name(product_name, preserve_case=True),
                    'cat_name': normalized_category_name,
                    'qty': quantity,
                    'unit_price': unit_price,
                    'total_price': total_price,
                    'instructions': item.get('special_instructions'),
                    'confidence': confidence,
                })
                
                order_item_id = result.fetchone()[0]
                self.stats['order_items'] += 1
                
                # Insert Options (modifiers)
                for option in item.get('options', []):
                    mod_query = text("""
                        INSERT INTO unified_order_item_modifiers (
                            order_item_id, modifier_name, price_cents
                        )
                        VALUES (:item_id, :name, :price)
                    """)
                    self.db_conn.execute(mod_query, {
                        'item_id': order_item_id,
                        'name': option.get('name', ''),
                        'price': option.get('price', 0),
                    })
            
            # DoorDash doesn't have payment records (handled by platform)
        
        self.db_conn.commit()
        print("✓ DoorDash data ingestion completed")
    
    def ingest_square_data(self, data_dir: str):
        """Ingest Square POS data."""
        print("\n" + "="*60)
        print("Ingesting Square data...")
        print("="*60)
        
        # Load Square data files
        with open(os.path.join(data_dir, 'orders.json'), 'r', encoding='utf-8') as f:
            orders_data = json.load(f)
        
        with open(os.path.join(data_dir, 'payments.json'), 'r', encoding='utf-8') as f:
            payments_data = json.load(f)
        
        with open(os.path.join(data_dir, 'catalog.json'), 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)
        
        # Build catalog lookup (variation_id -> item info)
        catalog_lookup = {}
        category_lookup = {}
        
        for obj in catalog_data.get('objects', []):
            if obj.get('type') == 'CATEGORY':
                category_lookup[obj.get('id')] = obj.get('category_data', {}).get('name', '')
            elif obj.get('type') == 'ITEM':
                item_data = obj.get('item_data', {})
                item_id = obj.get('id')
                category_id = item_data.get('category_id')
                item_name = item_data.get('name', '')
                
                for variation in item_data.get('variations', []):
                    var_data = variation.get('item_variation_data', {})
                    var_id = variation.get('id')
                    catalog_lookup[var_id] = {
                        'item_id': item_id,
                        'item_name': item_name,
                        'variation_name': var_data.get('name', ''),
                        'category_id': category_id,
                        'price': var_data.get('price_money', {}).get('amount', 0),
                    }
        
        # Build payments lookup (order_id -> payment)
        payments_lookup = {}
        for payment in payments_data.get('payments', []):
            order_id = payment.get('order_id')
            if order_id:
                payments_lookup[order_id] = payment
        
        # Process orders
        for order in tqdm(orders_data.get('orders', []), desc="Processing Square orders"):
            # Get unified location ID
            source_loc_id = order.get('location_id')
            unified_loc_id = self.get_unified_location_id('square', source_loc_id)
            if not unified_loc_id:
                continue
            
            # Parse dates
            created_ts = self.parse_datetime(order.get('created_at'))
            closed_ts = self.parse_datetime(order.get('closed_at'))
            order_date = created_ts.date() if created_ts else None
            if not order_date:
                continue
            
            # Get fulfillment type
            fulfillments = order.get('fulfillments', [])
            order_type = 'DINE_IN'  # Default
            if fulfillments:
                fulfillment_type = fulfillments[0].get('type', '')
                if fulfillment_type == 'PICKUP':
                    order_type = 'PICKUP'
                elif fulfillment_type == 'DINE_IN':
                    order_type = 'DINE_IN'
            
            # Source type
            source_name = order.get('source', {}).get('name', 'Square POS')
            source_type = 'ONLINE' if 'Online' in source_name else 'POS'
            
            # Order status
            state = order.get('state', 'COMPLETED')
            status = 'COMPLETED' if state == 'COMPLETED' else 'CANCELLED'
            
            # Get payment info
            payment_info = payments_lookup.get(order.get('id'), {})
            
            # Insert Order
            order_query = text("""
                INSERT INTO unified_orders (
                    unified_location_id, source_system, source_order_id,
                    order_date, order_timestamp, closed_timestamp, paid_timestamp,
                    order_type, source_type, subtotal_cents, tax_cents, tip_cents,
                    total_cents, status
                )
                VALUES (
                    :loc_id, 'square', :source_order_id,
                    :order_date, :order_ts, :closed_ts, :paid_ts,
                    :order_type, :source_type, :subtotal, :tax, :tip,
                    :total, :status
                )
                ON CONFLICT (source_system, source_order_id) DO NOTHING
                RETURNING order_id
            """)
            result = self.db_conn.execute(order_query, {
                'loc_id': unified_loc_id,
                'source_order_id': order.get('id'),
                'order_date': order_date,
                'order_ts': created_ts,
                'closed_ts': closed_ts,
                'paid_ts': closed_ts,
                'order_type': order_type,
                'source_type': source_type,
                'subtotal': order.get('total_money', {}).get('amount', 0) - order.get('total_tax_money', {}).get('amount', 0) - order.get('total_tip_money', {}).get('amount', 0),
                'tax': order.get('total_tax_money', {}).get('amount', 0),
                'tip': order.get('total_tip_money', {}).get('amount', 0),
                'total': order.get('total_money', {}).get('amount', 0),
                'status': status,
            })
            
            row = result.fetchone()
            if not row:
                get_order_query = text("""
                    SELECT order_id FROM unified_orders
                    WHERE source_system = 'square' AND source_order_id = :source_order_id
                """)
                row = self.db_conn.execute(get_order_query, {
                    'source_order_id': order.get('id')
                }).fetchone()
            
            if not row:
                continue
            
            order_id = row[0]
            self.stats['orders'] += 1
            
            # Insert Order Items
            for line_item in order.get('line_items', []):
                catalog_obj_id = line_item.get('catalog_object_id')
                catalog_item = catalog_lookup.get(catalog_obj_id, {})
                
                item_name = catalog_item.get('item_name', '')
                variation_name = catalog_item.get('variation_name', '')
                
                # Build full product name
                if variation_name and variation_name.lower() != 'regular':
                    product_name = f"{item_name} - {variation_name}"
                else:
                    product_name = item_name
                
                category_id = catalog_item.get('category_id')
                category_name = category_lookup.get(category_id, '') if category_id else ''
                
                # Normalize category name (remove emojis) for storage
                normalized_category_name = normalize_category(category_name) if category_name else None
                
                product_id, confidence = self.get_or_create_product(
                    product_name, category_name, 'square'
                )
                
                quantity = int(line_item.get('quantity', 1))
                gross_sales = line_item.get('gross_sales_money', {}).get('amount', 0)
                unit_price = gross_sales // quantity if quantity > 0 else 0
                total_price = line_item.get('total_money', {}).get('amount', 0)
                
                item_query = text("""
                    INSERT INTO unified_order_items (
                        order_id, unified_product_id, source_item_id,
                        product_name, normalized_product_name, category_name,
                        quantity, unit_price_cents, total_price_cents,
                        source_system, match_confidence
                    )
                    VALUES (
                        :order_id, :prod_id, :source_item_id,
                        :prod_name, :norm_name, :cat_name,
                        :qty, :unit_price, :total_price,
                        'square', :confidence
                    )
                    RETURNING order_item_id
                """)
                result = self.db_conn.execute(item_query, {
                    'order_id': order_id,
                    'prod_id': product_id,
                    'source_item_id': catalog_obj_id,
                    'prod_name': product_name,
                    'norm_name': normalize_product_name(product_name, preserve_case=True),
                    'cat_name': normalized_category_name,
                    'qty': quantity,
                    'unit_price': unit_price,
                    'total_price': total_price,
                    'confidence': confidence,
                })
                
                order_item_id = result.fetchone()[0]
                self.stats['order_items'] += 1
            
            # Insert Payment
            if payment_info:
                pay_ts = self.parse_datetime(payment_info.get('created_at'))
                if pay_ts:
                    pay_date = pay_ts.date()
                    
                    source_type = payment_info.get('source_type', 'CARD')
                    payment_type = 'CREDIT' if source_type == 'CARD' else source_type
                    
                    card_details = payment_info.get('card_details', {})
                    card_info = card_details.get('card', {}) if card_details else {}
                    card_brand = card_info.get('card_brand') if card_info else None
                    
                    wallet_details = payment_info.get('wallet_details', {})
                    wallet_type = wallet_details.get('brand') if wallet_details else None
                    if wallet_type:
                        payment_type = 'WALLET'
                    
                    pay_query = text("""
                        INSERT INTO unified_payments (
                            order_id, source_system, source_payment_id,
                            payment_timestamp, payment_date,
                            payment_type, card_brand, card_last_4, wallet_type,
                            amount_cents, tip_cents, processing_fee_cents,
                            status
                        )
                        VALUES (
                            :order_id, 'square', :source_payment_id,
                            :pay_ts, :pay_date,
                            :pay_type, :card_brand, :last4, :wallet_type,
                            :amount, :tip, :fee,
                            :status
                        )
                        ON CONFLICT (source_system, source_payment_id) DO NOTHING
                    """)
                    self.db_conn.execute(pay_query, {
                        'order_id': order_id,
                        'source_payment_id': payment_info.get('id'),
                        'pay_ts': pay_ts,
                        'pay_date': pay_date,
                        'pay_type': payment_type,
                        'card_brand': card_brand,
                        'last4': card_info.get('last_4') if card_info else None,
                        'wallet_type': wallet_type,
                        'amount': payment_info.get('amount_money', {}).get('amount', 0),
                        'tip': payment_info.get('tip_money', {}).get('amount', 0),
                        'fee': 0,  # Square doesn't provide processing fee in this data
                        'status': payment_info.get('status', 'COMPLETED'),
                    })
                    self.stats['payments'] += 1
        
        self.db_conn.commit()
        print("✓ Square data ingestion completed")
    
    def print_stats(self):
        """Print ingestion statistics."""
        print("\n" + "="*60)
        print("Ingestion Statistics")
        print("="*60)
        for key, value in self.stats.items():
            print(f"{key}: {value}")
        
        match_stats = self.product_matcher.get_stats()
        print("\nProduct Matching Statistics:")
        for key, value in match_stats.items():
            print(f"  {key}: {value}")


def main():
    """Main ingestion function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest data into unified schema')
    parser.add_argument('--toast', default='../data/sources/toast_pos_export.json',
                       help='Path to toast_pos_export.json')
    parser.add_argument('--doordash', default='../data/sources/doordash_orders.json',
                       help='Path to doordash_orders.json')
    parser.add_argument('--square-dir', default='../data/sources/square',
                       help='Path to square data directory')
    parser.add_argument('--all', action='store_true',
                       help='Ingest all sources')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform dry run without committing')
    parser.add_argument('--skip-refresh', action='store_true',
                       help='Skip materialized view refresh after ingestion')
    
    args = parser.parse_args()
    
    # Test connection
    if not test_connection():
        print("Please configure your database connection first.")
        sys.exit(1)
    
    conn = get_db_connection()
    
    try:
        ingester = UnifiedDataIngester(conn)
        ingester.setup_reference_data()
        
        if args.all or args.toast:
            ingester.ingest_toast_data(args.toast)
        
        if args.all or args.doordash:
            ingester.ingest_doordash_data(args.doordash)
        
        if args.all or args.square_dir:
            ingester.ingest_square_data(args.square_dir)
        
        if not args.dry_run:
            conn.commit()
            print("\n✓ Data ingestion completed and committed!")
            
            # Refresh materialized views after successful ingestion
            if not args.skip_refresh:
                print("\nRefreshing materialized views...")
                try:
                    # Ensure connection is clean before refresh
                    # Commit any pending changes and ensure clean transaction state
                    try:
                        conn.commit()
                    except Exception:
                        conn.rollback()
                    
                    # Try to import refresh module (may not exist if views aren't created yet)
                    try:
                        from scripts.refresh.refresh_materialized_views_sync import refresh_views_smart
                        refresh_result = refresh_views_smart(conn)
                        if refresh_result['success']:
                            print(f"✓ Materialized views refreshed successfully")
                            print(f"  Refreshed {len(refresh_result['views_refreshed'])} views in {refresh_result['duration_seconds']:.2f}s")
                        else:
                            print(f"⚠ Materialized view refresh failed: {refresh_result.get('message', 'Unknown error')}")
                    except ImportError:
                        print("⚠ Materialized view refresh module not found. Skipping refresh.")
                        print("  (This is normal if materialized views haven't been created yet)")
                except Exception as e:
                    print(f"⚠ Error refreshing materialized views: {e}")
                    # Don't fail the ingestion if refresh fails
        else:
            conn.rollback()
            print("\n✓ Data ingestion (DRY RUN) completed - no changes committed")
        
        ingester.print_stats()
    
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
