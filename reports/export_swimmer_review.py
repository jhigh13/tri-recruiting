"""Export swimmer review results back to the recruitment spreadsheet.

Features:
- Auto-add review_date column to SQLite if missing (lightweight migration).
- Select runners where excel_match == True, excel_swimmer IS NULL, swimmer NOT NULL.
- Write/update columns: Swimmer, Match_Confidence, Rationale, Majority_Score, Review_Date, Runner_URL, Swim_URL.
- Preserve original casing of names (DB stores lowercase; spreadsheet expected mixed). Match is done case-insensitive.
- Supports --dry-run to preview actions and --output to write to a new file.

Usage (PowerShell):
  python -m reports.export_swimmer_review \
    --spreadsheet "etl/data/Recruitment Spreadsheet.xlsx" \
    --output "etl/data/Recruitment Spreadsheet UPDATED.xlsx"

  (Dry run)
  python -m reports.export_swimmer_review --spreadsheet "etl/data/Recruitment Spreadsheet.xlsx" --dry-run
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
import shutil
from typing import List, Tuple

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from db.db_connection import get_db_session
from db.models import Runner

REQUIRED_OUTPUT_COLUMNS = [
    "Swimmer",
    "Match_Confidence",
    "Rationale",
    "Majority_Score",
    "Review_Date",
    "Runner_URL",
    "Swim_URL",
]

NAME_COL_MAP = {
    "first_name": ["first_name", "First Name", "first", "First"],
    "last_name": ["last_name", "Last Name", "last", "Last"],
    "college": ["College", "college", "college_team", "College Team"],
}


def ensure_review_date_column(session) -> None:
    """Add review_date column to runners table if it does not exist (SQLite only).

    For PostgreSQL a proper migration tool (Alembic) is recommended; here we issue a direct ALTER.
    """
    inspector = inspect(session.bind)
    cols = [c["name"] for c in inspector.get_columns("runners")]
    if "review_date" not in cols:
        session.execute(text("ALTER TABLE runners ADD COLUMN review_date TIMESTAMP"))
        session.commit()


def locate_name_columns(df: pd.DataFrame) -> Tuple[str, str, str]:
    """Return the column names for first_name, last_name, college in the sheet.
    Raises ValueError if not found.
    """
    lowered = {c.lower(): c for c in df.columns}
    def find(candidates: List[str]) -> str:
        for cand in candidates:
            if cand.lower() in lowered:
                return lowered[cand.lower()]
        raise ValueError(f"Could not locate any of: {candidates}")
    return (
        find(NAME_COL_MAP["first_name"]),
        find(NAME_COL_MAP["last_name"]),
        find(NAME_COL_MAP["college"]),
    )


def fetch_target_runners(session) -> List[Runner]:
    return (
        session.query(Runner)
        .filter(
            Runner.excel_match.is_(True),
            Runner.excel_swimmer.is_(None),  # not given in spreadsheet
            Runner.swimmer.isnot(None),      # we have an AI decision
        )
        .all()
    )


def normalize(s: str | None) -> str:
    return (s or "").strip().lower()


def upsert_review_columns(df: pd.DataFrame) -> None:
    for col in REQUIRED_OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = None


def apply_updates(df: pd.DataFrame, first_col: str, last_col: str, college_col: str, runners: List[Runner], dry_run: bool) -> tuple[int, set[int]]:
    """Update DataFrame rows in place for the provided runners.

    Returns (number_of_updated_rows, set_of_runner_ids_updated).
    """
    updated = 0
    touched: set[int] = set()
    # Build a multi-index map for faster lookup (lowercased)
    # Key: (first,last,college)
    index_map = {}
    for idx, row in df.iterrows():
        key = (normalize(row[first_col]), normalize(row[last_col]), normalize(row[college_col]))
        index_map.setdefault(key, []).append(idx)

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    for r in runners:
        key = (normalize(r.first_name), normalize(r.last_name), normalize(r.college_team))
        if key not in index_map:
            continue
        for idx in index_map[key]:  # may correspond to multiple sheet rows
            df.at[idx, "Swimmer"] = r.swimmer
            df.at[idx, "Match_Confidence"] = r.match_confidence
            df.at[idx, "Rationale"] = r.rationale
            df.at[idx, "Majority_Score"] = r.majority_score
            df.at[idx, "Review_Date"] = now_str
            df.at[idx, "Runner_URL"] = r.runner_url
            df.at[idx, "Swim_URL"] = r.swim_url
            updated += 1
            touched.add(r.runner_id)
        if not dry_run:
            # Persist review_date back to DB
            r.review_date = datetime.utcnow()
    return updated, touched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export swimmer classification results back to recruitment spreadsheet.")
    parser.add_argument("--spreadsheet", required=True, help="Path to Recruitment Spreadsheet.xlsx")
    parser.add_argument("--output", help="Optional output path; default overwrites input (after backup).")
    parser.add_argument("--dry-run", action="store_true", help="Do not write Excel or DB changes; just show planned updates.")
    parser.add_argument("--summary-sheet", default="Agent_Swimmer_Summary", help="Name of summary sheet to create with new swimmer identifications.")
    parser.add_argument("--skip-summary", action="store_true", help="Do not generate summary sheet even if updates occur.")
    return parser.parse_args()


def main():
    args = parse_args()
    sheet_path = Path(args.spreadsheet)
    if not sheet_path.exists():
        raise FileNotFoundError(f"Spreadsheet not found: {sheet_path}")

    session = get_db_session()
    try:
        ensure_review_date_column(session)
        runners = fetch_target_runners(session)
        print(f"Found {len(runners)} target runners for export.")
        if not runners:
            return

        # Load workbook (all sheets) and process Men/Women if present else whole file
        book = pd.ExcelFile(sheet_path)
        output_frames = {}
        for sheet_name in book.sheet_names:
            df = book.parse(sheet_name)
            try:
                first_col, last_col, college_col = locate_name_columns(df)
            except ValueError:
                output_frames[sheet_name] = df  # leave untouched
                continue
            upsert_review_columns(df)
            updated_rows, touched = apply_updates(df, first_col, last_col, college_col, runners, args.dry_run)
            print(f"Sheet '{sheet_name}': updated {updated_rows} rows.")
            # Accumulate touched IDs across sheets (store on args for later summary extension)
            existing = getattr(args, "_touched_ids", set())
            setattr(args, "_touched_ids", existing.union(touched))
            output_frames[sheet_name] = df

        if args.dry_run:
            print("Dry run complete; no files written.")
            return

        # Commit DB review_date updates
        try:
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e

        # Backup original
        if args.output:
            out_path = Path(args.output)
        else:
            backup_path = sheet_path.with_suffix('.backup.xlsx')
            try:
                # Attempt atomic replace rename
                sheet_path.replace(backup_path)
            except PermissionError as e:
                if getattr(e, 'winerror', None) == 32:
                    # File in use (e.g., open in Excel) fallback to copy
                    temp_backup = backup_path
                    shutil.copy2(sheet_path, temp_backup)
                    print(f"WARNING: File in use. Created copy backup instead: {temp_backup.name}")
                else:
                    raise
            else:
                print(f"Original spreadsheet backed up to {backup_path.name}")
            out_path = sheet_path  # overwrite original name

        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            for name, frame in output_frames.items():
                frame.to_excel(writer, sheet_name=name, index=False)
            # Optional summary sheet
            if not args.skip_summary and getattr(args, "_touched_ids", None):
                # Re-fetch runners for reliable ordering
                id_set = getattr(args, "_touched_ids")
                if id_set:
                    refreshed = (
                        session.query(Runner)
                        .filter(Runner.runner_id.in_(list(id_set)))
                        .all()
                    )
                    # Build summary rows only for swimmers (swimmer truthy / == 'Yes' / == 1)
                    summary_rows = []
                    for r in refreshed:
                        swimmer_val = str(r.swimmer).strip().lower() if r.swimmer is not None else ""
                        is_swimmer = swimmer_val in {"yes", "true", "1"}
                        if not is_swimmer:
                            continue
                        summary_rows.append({
                            "First Name": r.first_name,
                            "Last Name": r.last_name,
                            "College": r.college_team,
                            "Swimmer": r.swimmer,
                            "Majority_Score": r.majority_score,
                            "Match_Confidence": r.match_confidence,
                            "Rationale": r.rationale,
                            "Review_Date": r.review_date.strftime("%Y-%m-%d %H:%M:%S") if r.review_date else None,
                            "Runner_URL": r.runner_url,
                            "Swim_URL": r.swim_url,
                        })
                    if summary_rows:
                        pd.DataFrame(summary_rows).sort_values(
                            by=["Majority_Score", "Last Name", "First Name"], ascending=[False, True, True]
                        ).to_excel(writer, sheet_name=args.summary_sheet, index=False)
                        print(f"Summary sheet '{args.summary_sheet}' written with {len(summary_rows)} swimmers.")
                    else:
                        print("No swimmer rows qualified for summary sheet (all non-swimmer or undecided).")
        print(f"Export complete -> {out_path}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
