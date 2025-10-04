#!/usr/bin/env python3
"""
Test script to examine raw customer data from Excel
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

def test_raw_customer_data():
    """Test raw customer data from Excel"""
    print("Examining raw customer data from Excel:")
    print("=" * 60)
    
    try:
        # Load the Excel file directly
        df = pd.read_excel("data/customer_list.xlsx")
        
        print(f"Excel columns: {list(df.columns)}")
        print(f"Total rows: {len(df)}")
        print()
        
        # Find Red Ball Oxygen rows
        redball_rows = df[df['Company Name'].str.contains('RED BALL OXYGEN', case=False, na=False)]
        
        print(f"Found {len(redball_rows)} Red Ball Oxygen rows:")
        for idx, row in redball_rows.iterrows():
            print(f"Row {idx}:")
            for col in df.columns:
                print(f"  {col}: '{row[col]}'")
            print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_raw_customer_data()
