"""
Product Matching Configuration
Defines product name mappings, typos, and normalization rules
"""

# Common typos and corrections
TYPO_CORRECTIONS = {
    "griled": "grilled",
    "chiken": "chicken",
    "sandwhich": "sandwich",
    "expresso": "espresso",
    "coffe": "coffee",
    "appitizers": "appetizers",
    "nachos supreme": "nachos supreme",  # Keep as is, but normalize case
    "lg coke": "large coca-cola",
    "fountain soda": "soda",
    "hashbrowns": "Hash browns",
    "hash browns": "Hash browns",
}

# Category normalization mappings
CATEGORY_NORMALIZATION = {
    # Toast categories
    "🍔 Burgers": "Burgers",
    "🍟 Sides": "Sides",
    "🥤 Beverages": "Beverages",
    "🌅 Breakfast": "Breakfast",
    "🍰 Desserts": "Desserts",
    "Sandwiches": "Sandwiches",
    "Salads": "Salads",
    "Entrees": "Entrees",
    "Appetizers": "Appetizers",
    "Wine": "Alcohol",
    "Beer": "Alcohol",
    
    # DoorDash categories
    "ENTREES": "Entrees",
    "Sides": "Sides",
    "🍟 Sides": "Sides",
    "🥤 Drinks": "Beverages",
    "Beverages": "Beverages",
    "🍗 Appetizers": "Appetizers",
    "Breakfast": "Breakfast",
    
    # Square categories
    "🍔 Burgers": "Burgers",
    "🍟 Sides & Appetizers": "Sides",
    "Drinks": "Beverages",
    "🌅 Breakfast": "Breakfast",
    "🍰 Desserts": "Desserts",
    "Beer & Wine": "Alcohol",
}

# Product name mappings (source-specific to canonical)
# These are known matches that should be mapped directly
PRODUCT_NAME_MAPPINGS = {
    # Toast → Canonical
    "Griled Chicken Sandwhich": "Grilled Chicken Sandwich",
    "Coffe": "Coffee",
    
    # DoorDash → Canonical
    "Griled Chiken Sandwich": "Grilled Chicken Sandwich",
    "Fries - Large": "French Fries",
    "Lg Coke": "Coca-Cola",
    "nachos supreme": "Nachos Grande",
    "Wings 12pc": "Buffalo Wings",
    
    # Square → Canonical
    "expresso": "Espresso",
    "coffe": "Coffee",
    "fountain soda": "Soda",
    "Hashbrowns": "Hash Browns",
    "Lg Coke": "Coca-Cola",
    "Churros 12pcs": "Churros",
    "churos 6pc": "Churros",
    "Buffalo Wings 12pc": "Buffalo Wings",
}

# Known product variations (same product, different names/sizes)
PRODUCT_VARIATIONS = {
    "Classic Burger": ["Classic Burger", "Burger"],
    "French Fries": ["French Fries", "Fries", "Fries - Large", "Fries - Small", "French Fries - Large", "French Fries - Small"],
    "Grilled Chicken Sandwich": ["Grilled Chicken Sandwich", "Griled Chicken Sandwich", "Griled Chiken Sandwich"],
    "Coffee": ["Coffee", "Coffe", "coffe - reg", "coffee - reg", "Coffee - Regular", "Regular Coffee"],
    "Espresso": ["Espresso", "espresso", "expresso", "Espresso - Double", "Espresso - Single", "espresso - dbl shot", "Double Espresso", "Single Espresso"],
    "Coke": ["Coke", "Coca-Cola", "Lg Coke", "Large Coca-Cola", "fountain soda", "fountain soda - lg", "Soda", "soda - lg"],
    "Hash Browns": ["Hash Browns", "Hashbrowns"],
    "Buffalo Wings": ["Buffalo Wings", "Wings 12pc", "Buffalo Wings 12pc", "Wings"],
    "Nachos Grande": ["Nachos Grande", "Nachos Supreme", "nachos supreme"],
    "Churros": ["Churros", "Churros 12pcs", "churos 6pc"],
    "Chocolate Milkshake": ["Chocolate Milkshake", "Milkshake - Chocolate", "Choc Milkshake", "Milkshake Chocolate"],
}

# Category hierarchy (for future use)
CATEGORY_HIERARCHY = {
    "Entrees": None,  # Top level
    "Burgers": "Entrees",
    "Sandwiches": "Entrees",
    "Sides": None,
    "Appetizers": "Sides",
    "Salads": "Sides",
    "Beverages": None,
    "Alcohol": "Beverages",
    "Breakfast": None,
    "Desserts": None,
}

# Location ID mappings (source ID → unified code)
LOCATION_MAPPINGS = {
    "toast": {
        "loc_downtown_001": "DOWNTOWN",
        "loc_airport_002": "AIRPORT",
        "loc_mall_003": "MALL",
        "loc_univ_004": "UNIVERSITY",
    },
    "doordash": {
        "str_downtown_001": "DOWNTOWN",
        "str_airport_002": "AIRPORT",
        "str_mall_003": "MALL",
        "str_university_004": "UNIVERSITY",
    },
    "square": {
        "LCN001DOWNTOWN": "DOWNTOWN",
        "LCN002AIRPORT": "AIRPORT",
        "LCN003MALL": "MALL",
        "LCN004UNIV": "UNIVERSITY",
    },
}

# Location details (for unified_locations table)
LOCATION_DETAILS = {
    "DOWNTOWN": {
        "name": "Downtown",
        "address_line1": "123 Main St",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "country": "US",
        "timezone": "America/New_York",
    },
    "AIRPORT": {
        "name": "Airport",
        "address_line1": "456 Terminal Blvd",
        "city": "Jamaica",
        "state": "NY",
        "zip_code": "11430",
        "country": "US",
        "timezone": "America/New_York",
    },
    "MALL": {
        "name": "Mall Location",
        "address_line1": "789 Shopping Center Dr",
        "city": "New York",
        "state": "NY",
        "zip_code": "10019",
        "country": "US",
        "timezone": "America/New_York",
    },
    "UNIVERSITY": {
        "name": "University",
        "address_line1": "321 College Ave",
        "city": "New York",
        "state": "NY",
        "zip_code": "10027",
        "country": "US",
        "timezone": "America/New_York",
    },
}

