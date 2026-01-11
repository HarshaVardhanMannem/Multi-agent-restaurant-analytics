"""
Path utilities for script file resolution.
Centralizes common path operations used across scripts.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Cache project root to avoid repeated calculations
_project_root: Optional[Path] = None


def setup_script_paths() -> Path:
    """
    Setup script paths and return project root directory.
    
    This function handles the common pattern of adding parent directory to sys.path
    that is repeated across many scripts.
    
    Returns:
        Path object pointing to project root directory
    """
    global _project_root
    
    if _project_root is None:
        # Scripts are now in etl/scripts/core
        script_dir = Path(__file__).parent.parent  # etl/scripts/core -> etl/scripts
        _project_root = script_dir.parent.parent  # etl/scripts -> etl -> project root
        
        # Add project root to path if not already there
        project_root_str = str(_project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
    
    return _project_root


def _get_project_root() -> Path:
    """Internal helper to get project root without side effects."""
    if _project_root is None:
        return setup_script_paths()
    return _project_root


def get_schemas_dir() -> Path:
    """Get path to schemas directory."""
    project_root = _get_project_root()
    # Schemas are now in etl/schemas/
    return project_root / 'etl' / 'schemas'


def get_data_dir() -> Path:
    """Get path to data directory."""
    project_root = _get_project_root()
    return project_root / 'data'


def get_schema_file(filename: str) -> Path:
    """
    Get path to a schema SQL file.
    
    Args:
        filename: Name of the SQL file (e.g., 'unified_schema.sql')
    
    Returns:
        Path object to the schema file
    """
    return get_schemas_dir() / filename


def get_data_source_path(source_name: Optional[str] = None) -> Path:
    """
    Get path to data sources directory or specific source.
    
    Args:
        source_name: Optional source file/directory name
    
    Returns:
        Path to data sources directory or specific source
    """
    data_dir = get_data_dir() / 'sources'
    if source_name:
        return data_dir / source_name
    return data_dir

