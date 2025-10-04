#!/usr/bin/env python3
"""
Test for addresses with city information.
"""

from step3_databases import DatabaseManager

def test_full_addresses():
    """Test for addresses with city information."""
    
    db_manager = DatabaseManager()
    db_manager.load_databases()
    
    # Look for addresses that might have city info
    print("Looking for addresses with city information:")
    found_cities = 0
    
    for i, (_, row) in enumerate(db_manager.customers_df.iterrows()):
        address = str(row['Address']).upper()
        city = db_manager._extract_city_from_address(address)
        
        if city:
            found_cities += 1
            print(f"{found_cities}. {row['company_name']}")
            print(f"   Address: {row['Address']}")
            print(f"   Extracted city: {city}")
            print()
            
            if found_cities >= 10:  # Show first 10
                break
    
    print(f"Found {found_cities} addresses with city information out of {len(db_manager.customers_df)} total")

if __name__ == "__main__":
    test_full_addresses()
