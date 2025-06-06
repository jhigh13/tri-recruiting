#!/usr/bin/env python3
"""
Extract USA Triathlon time standards from PDF and create CSV file.

This module uses pdfplumber to extract time standards from the 
"Time Standards Explanation.pdf" and converts them to a CSV format
suitable for loading into the time_standards table.

Usage:
    python etl/extract_standards.py
"""

import os
import sys
from pathlib import Path
import pandas as pd
import pdfplumber
import re
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Constants for time standards extraction
PDF_PATH = "docs/Time Standards Explanation.pdf"
OUTPUT_CSV = "data/time_standards.csv"

# Color mappings for classification tiers
COLOR_MAPPINGS = {
    "World Leading": "Dark_Green",
    "Internationally Ranked": "Green", 
    "Nationally Competitive": "Yellow",
    "Development Potential": "Orange"
}

# Display order for consistent sorting
DISPLAY_ORDER = {
    "World Leading": 1,
    "Internationally Ranked": 2,
    "Nationally Competitive": 3,
    "Development Potential": 4
}


def time_to_seconds(time_str: str) -> float:
    """
    Convert time string to total seconds.
    
    Args:
        time_str: Time in format "M:SS.ss" or "MM:SS.ss" or "S:SS.ss"
        
    Returns:
        float: Total seconds with decimal precision
        
    Examples:
        "1:48.23" -> 108.23
        "2:01.50" -> 121.50
        "4:15.75" -> 255.75
    """
    if not time_str or pd.isna(time_str):
        return 0.0
        
    # Clean the time string
    time_str = str(time_str).strip()
    
    # Handle MM:SS.ss format
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
    
    # Handle pure seconds (SS.ss)
    try:
        return float(time_str)
    except ValueError:
        print(f"Warning: Could not parse time '{time_str}', returning 0.0")
        return 0.0


def extract_tables_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract time standards tables from PDF.
    
    Args:
        pdf_path: Path to the Time Standards PDF
        
    Returns:
        List of dictionaries containing extracted standards data
    """
    standards_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Extracting from PDF: {pdf_path}")
            print(f"Total pages: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"Processing page {page_num}...")
                
                # Extract tables from the page
                tables = page.extract_tables()
                
                if not tables:
                    print(f"  No tables found on page {page_num}")
                    continue
                
                for table_num, table in enumerate(tables, 1):
                    print(f"  Processing table {table_num} ({len(table)} rows)")
                    
                    if len(table) < 2:  # Need at least header + 1 data row
                        continue
                    
                    # Parse the table structure
                    headers = table[0] if table[0] else []
                    
                    # Look for swimming events in headers
                    swimming_events = []
                    for header in headers:
                        if header and any(event in str(header).upper() for event in ['FREE', 'SWIM', '200', '400', '800', '1500', '1650']):
                            swimming_events.append(header)
                    
                    if not swimming_events:
                        print(f"    No swimming events detected in table {table_num}")
                        continue
                    
                    print(f"    Found swimming events: {swimming_events}")
                    
                    # Extract data rows
                    for row_num, row in enumerate(table[1:], 1):
                        if not row or len(row) < 2:
                            continue
                        
                        # Look for category indicators in first column
                        first_col = str(row[0]).strip() if row[0] else ""
                        
                        # Determine category and gender from context
                        category = None
                        gender = None
                        
                        if any(keyword in first_col.upper() for keyword in ['WORLD', 'LEADING']):
                            category = "World Leading"
                        elif any(keyword in first_col.upper() for keyword in ['INTERNATIONAL', 'RANKED']):
                            category = "Internationally Ranked"
                        elif any(keyword in first_col.upper() for keyword in ['NATIONAL', 'COMPETITIVE']):
                            category = "Nationally Competitive"
                        elif any(keyword in first_col.upper() for keyword in ['DEVELOPMENT', 'POTENTIAL']):
                            category = "Development Potential"
                        
                        # Determine gender from page context or table headers
                        page_text = page.extract_text().upper()
                        if 'MEN' in page_text or 'MALE' in page_text:
                            gender = 'M'
                        elif 'WOMEN' in page_text or 'FEMALE' in page_text:
                            gender = 'F'
                        else:
                            # Default based on common patterns
                            gender = 'M'  # Will need manual review
                        
                        if category:
                            # Extract times from subsequent columns
                            for col_num, cell in enumerate(row[1:], 1):
                                if cell and col_num < len(headers):
                                    event_header = headers[col_num]
                                    if event_header and any(event in str(event_header).upper() for event in ['FREE', 'SWIM']):
                                        time_seconds = time_to_seconds(str(cell))
                                        if time_seconds > 0:
                                            standards_data.append({
                                                'gender': gender,
                                                'age_group': 'Open',  # Default, may need adjustment
                                                'event': normalize_event_name(event_header),
                                                'category': category,
                                                'cutoff_seconds': time_seconds,
                                                'color_code': COLOR_MAPPINGS.get(category, 'Red'),
                                                'display_order': DISPLAY_ORDER.get(category, 999),
                                                'source_page': page_num,
                                                'source_table': table_num
                                            })
                
            print(f"Extracted {len(standards_data)} standards from PDF")
            return standards_data
            
    except Exception as e:
        print(f"Error extracting from PDF: {e}")
        return []


def normalize_event_name(event_header: str) -> str:
    """
    Normalize event names to consistent format.
    
    Args:
        event_header: Raw event name from PDF
        
    Returns:
        Normalized event name
    """
    if not event_header:
        return ""
    
    event = str(event_header).upper().strip()
    
    # Normalize common swimming events
    if '200' in event and 'FREE' in event:
        if 'LCM' in event or 'LONG' in event:
            return "200_Free_LCM"
        else:
            return "200_Free_YDS"
    elif '400' in event and 'FREE' in event:
        return "400_Free_LCM"
    elif '500' in event and 'FREE' in event:
        return "500_Free_YDS"
    elif '800' in event and 'FREE' in event:
        return "800_Free_LCM"
    elif '1000' in event and 'FREE' in event:
        return "1000_Free_YDS"
    elif '1500' in event and 'FREE' in event:
        return "1500_Free_LCM"
    elif '1650' in event and 'FREE' in event:
        return "1650_Free_YDS"
    
    # Return original if no match
    return event.replace(' ', '_')


def create_manual_standards() -> List[Dict[str, Any]]:
    """
    Create manual time standards based on common USA Triathlon benchmarks.
    
    This function provides fallback data if PDF extraction fails or
    needs supplementation with known standards.
    
    Returns:
        List of standard time dictionaries
    """
    manual_standards = []
    
    # Example standards (these should be verified against actual USA Triathlon data)
    standards_data = {
        # Men's Swimming Standards (LCM)
        'M': {
            '200_Free_LCM': {
                'World Leading': 109.50,
                'Internationally Ranked': 113.00,
                'Nationally Competitive': 116.50,
                'Development Potential': 120.00
            },
            '400_Free_LCM': {
                'World Leading': 230.00,
                'Internationally Ranked': 238.00,
                'Nationally Competitive': 246.00,
                'Development Potential': 254.00
            },
            '800_Free_LCM': {
                'World Leading': 480.00,
                'Internationally Ranked': 495.00,
                'Nationally Competitive': 510.00,
                'Development Potential': 525.00
            },
            '1500_Free_LCM': {
                'World Leading': 915.00,
                'Internationally Ranked': 945.00,
                'Nationally Competitive': 975.00,
                'Development Potential': 1005.00
            }
        },
        # Women's Swimming Standards (LCM)
        'F': {
            '200_Free_LCM': {
                'World Leading': 119.00,
                'Internationally Ranked': 123.50,
                'Nationally Competitive': 128.00,
                'Development Potential': 132.50
            },
            '400_Free_LCM': {
                'World Leading': 250.00,
                'Internationally Ranked': 260.00,
                'Nationally Competitive': 270.00,
                'Development Potential': 280.00
            },
            '800_Free_LCM': {
                'World Leading': 525.00,
                'Internationally Ranked': 545.00,
                'Nationally Competitive': 565.00,
                'Development Potential': 585.00
            },
            '1500_Free_LCM': {
                'World Leading': 1020.00,
                'Internationally Ranked': 1060.00,
                'Nationally Competitive': 1100.00,
                'Development Potential': 1140.00
            }
        }
    }
    
    for gender, events in standards_data.items():
        for event, categories in events.items():
            for category, time_seconds in categories.items():
                manual_standards.append({
                    'gender': gender,
                    'age_group': 'Open',
                    'event': event,
                    'category': category,
                    'cutoff_seconds': time_seconds,
                    'color_code': COLOR_MAPPINGS.get(category, 'Red'),
                    'display_order': DISPLAY_ORDER.get(category, 999),
                    'source_page': 0,
                    'source_table': 0
                })
    
    return manual_standards


def save_to_csv(standards_data: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save extracted standards to CSV file.
    
    Args:
        standards_data: List of standards dictionaries
        output_path: Path for output CSV file
    """
    if not standards_data:
        print("No standards data to save")
        return
    
    # Create DataFrame
    df = pd.DataFrame(standards_data)
    
    # Ensure data directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(exist_ok=True)
    
    # Sort by gender, event, display_order
    df = df.sort_values(['gender', 'event', 'display_order'])
    
    # Remove duplicate entries (keep first occurrence)
    df = df.drop_duplicates(subset=['gender', 'age_group', 'event', 'category'], keep='first')
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} standards to {output_path}")
    
    # Display summary
    print("\nStandards Summary:")
    print(f"  Total records: {len(df)}")
    print(f"  Genders: {sorted(df['gender'].unique())}")
    print(f"  Events: {sorted(df['event'].unique())}")
    print(f"  Categories: {sorted(df['category'].unique())}")


def main():
    """Main extraction function."""
    print("USA Triathlon Time Standards Extraction")
    print("=" * 50)
    
    # Check if PDF exists
    if not os.path.exists(PDF_PATH):
        print(f"Warning: PDF not found at {PDF_PATH}")
        print("Using manual standards instead...")
        standards_data = create_manual_standards()
    else:
        # Extract from PDF
        standards_data = extract_tables_from_pdf(PDF_PATH)
        
        # If PDF extraction yields few results, supplement with manual data
        if len(standards_data) < 10:
            print("PDF extraction yielded limited results, supplementing with manual standards...")
            manual_data = create_manual_standards()
            standards_data.extend(manual_data)
    
    if standards_data:
        save_to_csv(standards_data, OUTPUT_CSV)
        print(f"\n✅ SUCCESS: Time standards extracted to {OUTPUT_CSV}")
        print("\nNext step: Run 'python etl/standards_loader.py' to load into database")
    else:
        print("❌ No standards data extracted")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
