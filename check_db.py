#!/usr/bin/env python3
"""Quick database check script."""

from db.db_connection import get_engine
from db.models import Runner, Swimmer, TimeStandard
from sqlalchemy.orm import Session

def main():
    engine = get_engine()
    with Session(engine) as session:
        runner_count = session.query(Runner).count()
        swimmer_count = session.query(Swimmer).count()
        standards_count = session.query(TimeStandard).count()
        
        print(f"Current database state:")
        print(f"  Runners: {runner_count}")
        print(f"  Swimmers: {swimmer_count}")
        print(f"  Time Standards: {standards_count}")

if __name__ == "__main__":
    main()
