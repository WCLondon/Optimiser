#!/usr/bin/env python3
"""
Excel to Supabase Migration Script

This script imports data from an Excel workbook into Supabase Postgres tables.
It preserves the exact schema and column names from Excel.

Usage:
    python import_excel_to_supabase.py <excel_file_path>

Example:
    python import_excel_to_supabase.py data/HabitatBackend_WITH_STOCK.xlsx
"""

import sys
import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st
from pathlib import Path


def get_db_url():
    """Get database URL from Streamlit secrets."""
    try:
        db_url = st.secrets.get("database", {}).get("url")
        if not db_url:
            print("❌ Database URL not found in Streamlit secrets.")
            print("Please configure [database] url in .streamlit/secrets.toml")
            sys.exit(1)
        return db_url
    except Exception as e:
        print(f"❌ Error reading secrets: {e}")
        print("Make sure .streamlit/secrets.toml exists and contains [database] url")
        sys.exit(1)


def import_sheet(excel_file: str, sheet_name: str, engine):
    """Import a single Excel sheet to database table."""
    try:
        # Read Excel sheet
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        if df.empty:
            print(f"⚠️  {sheet_name}: Sheet is empty, skipping")
            return 0
        
        # Clean column names (remove leading/trailing spaces)
        df.columns = df.columns.str.strip()
        
        # Import to database
        # Use if_exists='replace' to overwrite existing data
        df.to_sql(sheet_name, engine, if_exists='replace', index=False, method='multi')
        
        print(f"✓ {sheet_name}: Imported {len(df)} rows")
        return len(df)
    
    except Exception as e:
        print(f"✗ {sheet_name}: Error - {e}")
        return 0


def verify_import(engine):
    """Verify that tables were created and populated."""
    print("\n" + "="*60)
    print("Verifying Import...")
    print("="*60)
    
    tables = ["Banks", "Pricing", "HabitatCatalog", "Stock", 
              "DistinctivenessLevels", "SRM", "TradingRules"]
    
    with engine.connect() as conn:
        for table_name in tables:
            try:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                count = result.fetchone()[0]
                status = "✓" if count > 0 else "⚠️"
                print(f"{status} {table_name}: {count} rows")
            except Exception as e:
                print(f"✗ {table_name}: Error - {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_excel_to_supabase.py <excel_file_path>")
        print("\nExample:")
        print("  python import_excel_to_supabase.py data/HabitatBackend_WITH_STOCK.xlsx")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    
    # Check if file exists
    if not Path(excel_file).exists():
        print(f"❌ File not found: {excel_file}")
        sys.exit(1)
    
    print("="*60)
    print("Excel to Supabase Import")
    print("="*60)
    print(f"Excel file: {excel_file}")
    
    # Get database connection
    print("\nConnecting to database...")
    db_url = get_db_url()
    engine = create_engine(db_url)
    
    try:
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Import sheets
    print("\n" + "="*60)
    print("Importing Excel Sheets...")
    print("="*60)
    
    sheets = [
        "Banks",
        "Pricing",
        "HabitatCatalog",
        "Stock",
        "DistinctivenessLevels",
        "SRM",
        "TradingRules"
    ]
    
    total_rows = 0
    for sheet_name in sheets:
        rows = import_sheet(excel_file, sheet_name, engine)
        total_rows += rows
    
    # Verify import
    verify_import(engine)
    
    # Summary
    print("\n" + "="*60)
    print("Import Complete!")
    print("="*60)
    print(f"Total rows imported: {total_rows}")
    print("\nNext steps:")
    print("1. Run: streamlit run app.py")
    print("2. Check Admin Dashboard for reference table status")
    print("3. Verify optimizer functionality")
    

if __name__ == "__main__":
    main()
