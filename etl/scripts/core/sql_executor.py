"""
SQL file execution utilities.
Centralizes SQL file reading and execution logic.
"""

from pathlib import Path
from typing import List, Tuple
from sqlalchemy import text


def read_sql_file(sql_file: Path) -> str:
    """
    Read SQL file content.
    
    Args:
        sql_file: Path to SQL file
    
    Returns:
        SQL file content as string
    
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file}")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        return f.read()


def parse_sql_statements(sql_content: str, remove_comments: bool = True) -> List[str]:
    """
    Parse SQL content into individual statements.
    
    Args:
        sql_content: Raw SQL content
        remove_comments: Whether to skip comment-only lines
    
    Returns:
        List of SQL statements
    """
    statements = []
    current_statement = []
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        
        # Skip empty lines and comments if requested
        if remove_comments:
            if not stripped or stripped.startswith('--'):
                continue
        
        current_statement.append(line)
        
        # Check if line ends with semicolon (end of statement)
        if stripped.endswith(';'):
            statement = '\n'.join(current_statement)
            if statement.strip():
                statements.append(statement)
            current_statement = []
    
    # Add any remaining statement
    if current_statement:
        statement = '\n'.join(current_statement)
        if statement.strip():
            statements.append(statement)
    
    return statements


def execute_sql_file(
    db_conn,
    sql_file: Path,
    parse_statements: bool = False,
    verbose: bool = True
) -> Tuple[int, List[str]]:
    """
    Execute SQL file on database connection.
    
    Args:
        db_conn: Database connection (SQLAlchemy)
        sql_file: Path to SQL file
        parse_statements: If True, parse into individual statements (for detailed logging)
                         If False, execute as single block (faster)
        verbose: Whether to log progress
    
    Returns:
        Tuple of (statements_executed, list_of_errors)
    """
    sql_content = read_sql_file(sql_file)
    
    if parse_statements:
        statements = parse_sql_statements(sql_content)
        executed = 0
        errors = []
        
        for statement in statements:
            try:
                if not statement.strip():
                    continue
                
                db_conn.execute(text(statement))
                db_conn.commit()
                executed += 1
            except Exception as e:
                error_msg = f"Error executing statement: {str(e)}"
                errors.append(error_msg)
                if verbose:
                    print(f"⚠ {error_msg}")
                db_conn.rollback()
        
        return executed, errors
    else:
        # Execute as single block (faster, but less granular error reporting)
        try:
            db_conn.execute(text(sql_content))
            db_conn.commit()
            return 1, []
        except Exception as e:
            error_msg = f"Error executing SQL file: {str(e)}"
            db_conn.rollback()
            if verbose:
                print(f"⚠ {error_msg}")
            return 0, [error_msg]


def extract_object_name(statement: str, object_type: str = "VIEW") -> str:
    """
    Extract object name from CREATE statement.
    
    Args:
        statement: SQL CREATE statement
        object_type: Type of object (VIEW, INDEX, MATERIALIZED VIEW, etc.)
    
    Returns:
        Object name if found, empty string otherwise
    """
    statement_upper = statement.upper()
    search_term = f"CREATE {object_type}"
    
    if search_term not in statement_upper:
        return ""
    
    parts = statement.split()
    try:
        # Find CREATE and then object type
        create_idx = None
        for i, part in enumerate(parts):
            if part.upper() == 'CREATE':
                create_idx = i
                break
        
        if create_idx is None:
            return ""
        
        # Look for OR REPLACE or MATERIALIZED keywords
        next_idx = create_idx + 1
        if next_idx < len(parts):
            if parts[next_idx].upper() in ('OR', 'MATERIALIZED'):
                next_idx += 1
                if next_idx < len(parts) and parts[next_idx - 1].upper() == 'OR':
                    next_idx += 1  # Skip REPLACE
        
        # The object type should be here
        if next_idx < len(parts) and parts[next_idx].upper() == object_type.split()[-1]:
            # Object name should be next
            name_idx = next_idx + 1
            if name_idx < len(parts):
                # Remove semicolon if present
                name = parts[name_idx].rstrip(';')
                return name
    
    except (IndexError, ValueError):
        pass
    
    return ""

