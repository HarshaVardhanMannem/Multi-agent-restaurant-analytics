"""
Product Matching Utility
Matches products across different data sources using fuzzy matching
"""

from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz, process
from utils.text_normalization import normalize_product_name, create_product_code
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.product_matching_config import PRODUCT_NAME_MAPPINGS, PRODUCT_VARIATIONS


class ProductMatcher:
    """
    Matches product names across different sources.
    Uses exact matching, mapping dictionary, and fuzzy matching.
    """
    
    def __init__(self, existing_products: Optional[Dict] = None):
        """
        Initialize ProductMatcher.
        
        Args:
            existing_products: Dictionary of existing products {product_code: product_id}
        """
        self.existing_products = existing_products or {}
        self.product_cache = {}  # Cache for normalized names
        self.matching_stats = {
            'exact_matches': 0,
            'mapped_matches': 0,
            'fuzzy_matches': 0,
            'new_products': 0,
        }
    
    def match_product(
        self, 
        source_product_name: str,
        source_system: str = 'unknown',
        threshold: float = 0.85
    ) -> Tuple[Optional[int], float, str]:
        """
        Match a product name to an existing product or create new.
        
        Args:
            source_product_name: Product name from source
            source_system: Source system identifier
            threshold: Minimum similarity score for fuzzy matching (0.0-1.0)
        
        Returns:
            Tuple of (product_id, confidence_score, match_type)
            - product_id: Matched product ID or None for new product
            - confidence_score: Matching confidence (0.0-1.0)
            - match_type: 'exact', 'mapped', 'fuzzy', or 'new'
        """
        if not source_product_name:
            return None, 0.0, 'none'
        
        # Normalize the input product name
        normalized_name = normalize_product_name(source_product_name)
        product_code = create_product_code(source_product_name)
        
        # Check cache
        cache_key = f"{source_system}:{normalized_name}"
        if cache_key in self.product_cache:
            return self.product_cache[cache_key]
        
        # Strategy 1: Exact match by product code
        if product_code in self.existing_products:
            result = (self.existing_products[product_code], 1.0, 'exact')
            self.product_cache[cache_key] = result
            self.matching_stats['exact_matches'] += 1
            return result
        
        # Strategy 2: Check mapping dictionary
        if source_product_name in PRODUCT_NAME_MAPPINGS:
            mapped_name = PRODUCT_NAME_MAPPINGS[source_product_name]
            mapped_code = create_product_code(mapped_name)
            if mapped_code in self.existing_products:
                result = (self.existing_products[mapped_code], 0.95, 'mapped')
                self.product_cache[cache_key] = result
                self.matching_stats['mapped_matches'] += 1
                return result
        
        # Strategy 3: Check product variations
        for canonical_name, variations in PRODUCT_VARIATIONS.items():
            if source_product_name in variations or normalized_name in [normalize_product_name(v) for v in variations]:
                canonical_code = create_product_code(canonical_name)
                if canonical_code in self.existing_products:
                    result = (self.existing_products[canonical_code], 0.9, 'variation')
                    self.product_cache[cache_key] = result
                    self.matching_stats['fuzzy_matches'] += 1
                    return result
        
        # Strategy 4: Fuzzy matching against existing products
        if self.existing_products:
            # Get all existing product names (reverse lookup)
            existing_names = {}  # {normalized_name: product_id}
            for code, prod_id in self.existing_products.items():
                # We need the original names, but we only have codes
                # For now, use code as proxy (in real implementation, you'd have a name lookup)
                existing_names[code] = prod_id
            
            # Fuzzy match against normalized names
            best_match = None
            best_score = 0
            
            for existing_code, prod_id in self.existing_products.items():
                # Calculate similarity
                score = fuzz.ratio(normalized_name, existing_code) / 100.0
                if score > best_score:
                    best_score = score
                    best_match = prod_id
            
            if best_match and best_score >= threshold:
                result = (best_match, best_score, 'fuzzy')
                self.product_cache[cache_key] = result
                self.matching_stats['fuzzy_matches'] += 1
                return result
        
        # Strategy 5: New product
        result = (None, 1.0, 'new')
        self.product_cache[cache_key] = result
        self.matching_stats['new_products'] += 1
        return result
    
    def add_product(self, product_code: str, product_id: int):
        """Add a product to the matcher's knowledge base."""
        self.existing_products[product_code] = product_id
    
    def get_stats(self) -> Dict[str, int]:
        """Get matching statistics."""
        return self.matching_stats.copy()
    
    def reset_stats(self):
        """Reset matching statistics."""
        self.matching_stats = {
            'exact_matches': 0,
            'mapped_matches': 0,
            'fuzzy_matches': 0,
            'new_products': 0,
        }


def create_product_matcher_from_db(db_connection) -> ProductMatcher:
    """
    Create a ProductMatcher pre-populated with existing products from database.
    
    Args:
        db_connection: Database connection object
    
    Returns:
        ProductMatcher instance
    """
    import pandas as pd
    
    # Query existing products
    query = """
        SELECT product_id, product_code, product_name, normalized_name
        FROM unified_products
    """
    
    df = pd.read_sql(query, db_connection)
    
    # Create mapping {product_code: product_id}
    existing_products = {}
    for _, row in df.iterrows():
        code = row['product_code'] or create_product_code(row['product_name'])
        existing_products[code] = row['product_id']
    
    return ProductMatcher(existing_products)


if __name__ == "__main__":
    # Test ProductMatcher
    matcher = ProductMatcher()
    
    # Add some test products
    matcher.add_product(create_product_code("Classic Burger"), 1)
    matcher.add_product(create_product_code("French Fries"), 2)
    matcher.add_product(create_product_code("Coffee"), 3)
    
    # Test matches
    test_products = [
        "Classic Burger",
        "Griled Chicken Sandwich",
        "French Fries",
        "Fries - Large",
        "Coffee",
        "Coffe",
        "New Product",
    ]
    
    print("Product Matching Tests:")
    print("=" * 80)
    print(f"{'Source Name':<30} {'Match ID':<10} {'Confidence':<12} {'Match Type':<15}")
    print("-" * 80)
    
    for product in test_products:
        prod_id, confidence, match_type = matcher.match_product(product)
        print(f"{product:<30} {str(prod_id):<10} {confidence:<12.2f} {match_type:<15}")
    
    print("\nMatching Statistics:")
    print("=" * 80)
    stats = matcher.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")



