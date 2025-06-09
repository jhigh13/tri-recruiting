"""
Clear all Runner records from the database.

Executes a DELETE operation on the runners table via SQLAlchemy.
"""
import logging
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import delete

# Allow imports from project root
sys.path.append(str(Path(__file__).parent.parent))
from db.db_connection import get_engine
from db.models import Runner


def clear_runners() -> int:
    """Delete all records in the runners table and return count."""
    # Print database URL for debugging
    engine = get_engine()
    logging.info(f"Clearing runners using engine: {engine.url}")
    with Session(engine) as session:
        # Delete all Runner rows
        result = session.execute(delete(Runner))
        session.commit()
        deleted = result.rowcount if result.rowcount is not None else 0
    return deleted


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    deleted_count = clear_runners()
    print(f"Deleted {deleted_count} runner records from the database.")


if __name__ == "__main__":
    main()
