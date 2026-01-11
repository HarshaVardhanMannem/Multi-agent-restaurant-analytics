"""
Text Normalization Utilities
Functions for cleaning and normalizing product names, categories, etc.
"""

import re
import unicodedata
from typing import Dict, Optional

# Optional: unidecode for accent removal (not currently used)
try:
    from unidecode import unidecode
except ImportError:
    unidecode = None

# Import configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.product_matching_config import TYPO_CORRECTIONS, CATEGORY_NORMALIZATION, PRODUCT_VARIATIONS


def remove_emojis(text: str) -> str:
    """
    Remove emoji characters from text using comprehensive Unicode ranges.
    
    This function removes emojis while preserving the rest of the text.
    If the text becomes empty after emoji removal, it returns the original text
    to prevent data loss.
    
    Args:
        text: Input text that may contain emojis
    
    Returns:
        Text with emojis removed, or original text if result would be empty
    """
    if not text:
        return text
    
    # Comprehensive emoji pattern covering all major emoji ranges
    emoji_pattern = re.compile(
        "["
        # Emoticons
        "\U0001F600-\U0001F64F"
        # Symbols & Pictographs
        "\U0001F300-\U0001F5FF"
        # Transport & Map Symbols
        "\U0001F680-\U0001F6FF"
        # Flags
        "\U0001F1E0-\U0001F1FF"
        # Dingbats
        "\U00002702-\U000027B0"
        # Enclosed Characters
        "\U000024C2-\U0001F251"
        # Supplemental Symbols & Pictographs (newer emojis)
        "\U0001F900-\U0001F9FF"
        # Symbols & Pictographs Extended-A
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        # Miscellaneous Symbols (weather, zodiac, etc.)
        "\U00002600-\U000026FF"
        # Variation Selectors (emoji modifiers)
        "\U0000FE00-\U0000FE0F"
        # Zero-Width Joiner (for combined emojis)
        "\U0000200D"
        "]+",
        flags=re.UNICODE
    )
    
    cleaned = emoji_pattern.sub('', text)
    
    # Normalize whitespace (collapse multiple spaces and trim)
    cleaned = normalize_whitespace(cleaned)
    
    # Prevent data loss: if text becomes empty after emoji removal,
    # check if original was emoji-only and preserve it (but strip whitespace)
    if not cleaned:
        # Strip whitespace from original and return if it's emoji-only
        original_stripped = text.strip()
        # If original is just emoji with spaces, return trimmed emoji
        if original_stripped and not re.sub(r'[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\s]', '', original_stripped):
            return original_stripped
        # Otherwise return empty
        return cleaned
    
    return cleaned


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace (trim and collapse multiple spaces)."""
    if not text:
        return text
    return ' '.join(text.split())


def fix_typos(text: str, typo_dict: Dict[str, str] = None) -> str:
    """
    Fix common typos in text while preserving case structure.
    Uses word boundaries to avoid partial matches.
    
    Example:
        "coffe" → "coffee" (fixes typo)
        "Coffee" → "Coffee" (no match, word boundary prevents "Coffe" from matching "Coffee")
        "COFFE" → "COFFEE" (fixes typo, preserves case)
        "coffe drink" → "coffee drink" (fixes typo in word)
    """
    if not text:
        return text
    
    typo_dict = typo_dict or TYPO_CORRECTIONS
    
    # Sort by length (longest first) to avoid partial replacements
    sorted_typos = sorted(typo_dict.items(), key=lambda x: len(x[0]), reverse=True)
    
    # Apply typo corrections with case preservation and word boundaries
    for typo, correction in sorted_typos:
        # Use word boundaries to match whole words only
        # This prevents "coffe" from matching inside "Coffee"
        pattern = re.compile(r'\b' + re.escape(typo) + r'\b', re.IGNORECASE)
        
        def replace_with_case(match):
            matched_text = match.group(0)
            # Preserve the case of the matched text
            if matched_text.isupper():
                return correction.upper()
            elif matched_text.istitle() or (matched_text[0].isupper() and len(matched_text) > 1 and matched_text[1:].islower()):
                return correction.title()
            else:
                return correction.lower()
        
        text = pattern.sub(replace_with_case, text)
    
    return text


def normalize_text(text: str, remove_emoji: bool = True, fix_typos_flag: bool = True, lowercase: bool = False) -> str:
    """
    Comprehensive text normalization.
    
    Args:
        text: Input text to normalize
        remove_emoji: Whether to remove emojis
        fix_typos_flag: Whether to fix typos
        lowercase: Whether to convert to lowercase (default: False, preserves case)
    
    Returns:
        Normalized text
    """
    if not text:
        return text
    
    # Convert to string if not already
    text = str(text)
    
    # Remove emojis (this also normalizes whitespace)
    if remove_emoji:
        text = remove_emojis(text)
    
    # Normalize Unicode (NFD → NFC)
    text = unicodedata.normalize('NFD', text)
    
    # Remove diacritics (optional - converts é to e, etc.)
    # text = unidecode(text)  # Uncomment if you want to remove accents
    
    # Fix typos (preserves case)
    if fix_typos_flag:
        text = fix_typos(text)
    
    # Normalize whitespace (in case emoji removal wasn't called)
    text = normalize_whitespace(text)
    
    # Convert to lowercase if requested
    if lowercase:
        text = text.lower()
    
    # Trim
    text = text.strip()
    
    return text


def normalize_category(category: str) -> str:
    """
    Normalize category name using mapping dictionary.
    
    Args:
        category: Original category name
    
    Returns:
        Normalized category name
    """
    if not category:
        return category
    
    # First normalize text (remove emojis, fix typos, etc.)
    normalized = normalize_text(category, remove_emoji=True, fix_typos_flag=True)
    
    # Check mapping dictionary
    if category in CATEGORY_NORMALIZATION:
        return CATEGORY_NORMALIZATION[category]
    
    if normalized in CATEGORY_NORMALIZATION:
        return CATEGORY_NORMALIZATION[normalized]
    
    # If not in mapping, return normalized version
    return normalized


def normalize_product_name(product_name: str, preserve_case: bool = False) -> str:
    """
    Normalize product name for matching.
    
    First checks if the product name matches any known variation in PRODUCT_VARIATIONS.
    If a match is found, returns the canonical name (the key).
    Otherwise, applies standard text normalization.
    
    Args:
        product_name: Original product name
        preserve_case: If True, preserve original case; if False, lowercase
    
    Returns:
        Normalized product name (canonical name if variation match found)
    """
    if not product_name:
        return product_name
    
    # First, check if product matches any known variation
    canonical_name = get_canonical_product_name(product_name)
    if canonical_name:
        if not preserve_case:
            return canonical_name.lower()
        return canonical_name
    
    # Fall back to standard text normalization
    normalized = normalize_text(product_name, remove_emoji=True, fix_typos_flag=True)
    
    # Lowercase for matching (unless preserve_case is True)
    if not preserve_case:
        normalized = normalized.lower()
    
    return normalized


def get_canonical_product_name(product_name: str) -> Optional[str]:
    """
    Check if a product name matches any known variation and return the canonical name.
    
    Matches are case-insensitive and also check against normalized versions
    of the variations.
    
    Args:
        product_name: Original product name to check
    
    Returns:
        Canonical product name if a match is found, None otherwise
    """
    if not product_name:
        return None
    
    product_name_lower = product_name.lower().strip()
    
    # Check each canonical product and its variations
    for canonical_name, variations in PRODUCT_VARIATIONS.items():
        # Check exact match (case-insensitive)
        for variation in variations:
            if product_name_lower == variation.lower().strip():
                return canonical_name
        
        # Check against normalized versions of variations
        for variation in variations:
            # Normalize the variation using basic text normalization (without recursion)
            normalized_variation = normalize_text(variation, remove_emoji=True, fix_typos_flag=True).lower()
            normalized_input = normalize_text(product_name, remove_emoji=True, fix_typos_flag=True).lower()
            if normalized_input == normalized_variation:
                return canonical_name
    
    return None


def create_product_code(product_name: str) -> str:
    """
    Create a standardized product code from product name.
    Used for product matching and identification.
    
    Args:
        product_name: Product name
    
    Returns:
        Standardized product code
    """
    if not product_name:
        return ""
    
    # Normalize
    code = normalize_product_name(product_name, preserve_case=False)
    
    # Remove special characters, keep only alphanumeric and spaces
    code = re.sub(r'[^a-z0-9\s]', '', code)
    
    # Replace spaces with underscores
    code = re.sub(r'\s+', '_', code)
    
    # Remove leading/trailing underscores
    code = code.strip('_')
    
    return code


def title_case_smart(text: str) -> str:
    """
    Convert text to title case intelligently.
    Handles special cases like "Lg" → "Large", etc.
    
    Args:
        text: Input text
    
    Returns:
        Title-cased text
    """
    if not text:
        return text
    
    # Common abbreviations and their expansions
    abbreviations = {
        'lg': 'Large',
        'sm': 'Small',
        'med': 'Medium',
        'pc': 'Piece',
        'pcs': 'Pieces',
    }
    
    # Split into words
    words = text.lower().split()
    
    # Expand abbreviations
    expanded_words = []
    for word in words:
        # Remove punctuation for matching
        word_clean = re.sub(r'[^\w]', '', word)
        if word_clean in abbreviations:
            # Replace abbreviation with expansion
            expanded = abbreviations[word_clean]
            # Preserve original punctuation
            word = word.replace(word_clean, expanded)
        expanded_words.append(word)
    
    # Join and title case
    result = ' '.join(expanded_words).title()
    
    return result


if __name__ == "__main__":
    # Test functions
    test_cases = [
        "🍔 Burgers",
        "Griled Chiken Sandwich",
        "Coffe",
        "expresso",
        "🍟 Sides",
        "Hashbrowns",
        "Lg Coke",
        "nachos supreme",
        "French Fries - Large",
    ]
    
    print("Text Normalization Tests:")
    print("=" * 60)
    for test in test_cases:
        normalized = normalize_text(test)
        code = create_product_code(test)
        print(f"Original: {test:30} → Normalized: {normalized:30} → Code: {code}")
    
    print("\nCategory Normalization Tests:")
    print("=" * 60)
    categories = ["🍔 Burgers", "🍟 Sides", "🥤 Beverages", "ENTREES", "Sides"]
    for cat in categories:
        norm_cat = normalize_category(cat)
        print(f"{cat:30} → {norm_cat}")

