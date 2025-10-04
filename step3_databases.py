"""
Step 3: Database Management Module
Manages the parts and customers databases for lookup and mapping operations.
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from fuzzywuzzy import fuzz, process
import re
from collections import defaultdict
import pickle
import hashlib

@dataclass
class Part:
    """Represents a part in the parts database."""
    internal_part_number: str
    description: str

@dataclass
class Customer:
    """Represents a customer in the customers database."""
    company_name: str
    account_number: str
    address: str
    state: str = ""

class DatabaseManager:
    """Manages parts and customers databases."""
    
    def __init__(self, parts_db_path: str = "data/parts.csv", customers_db_path: str = "data/customer_list.xlsx"):
        """
        Initialize the database manager.
        
        Args:
            parts_db_path: Path to the parts CSV file
            customers_db_path: Path to the customers Excel file
        """
        self.parts_db_path = parts_db_path
        self.customers_db_path = customers_db_path
        self.parts_df = None
        self.customers_df = None
        
        # Cache file paths
        self.cache_dir = "data/cache"
        self.parts_cache_path = os.path.join(self.cache_dir, "parts_indexes.pkl")
        self.customers_cache_path = os.path.join(self.cache_dir, "customers_data.pkl")
        self.cache_metadata_path = os.path.join(self.cache_dir, "cache_metadata.pkl")
        
        # Search optimization indexes
        self.parts_by_exact_match = {}  # Exact part number lookup
        self.parts_by_keywords = defaultdict(list)  # Keyword-based lookup
        self.description_words = {}  # Word-based description index
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(parts_db_path), exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.load_databases()
    
    def load_databases(self) -> None:
        """Load both parts and customers databases with caching."""
        # Try to load from cache first
        if self._load_from_cache():
            print("Loaded databases from cache")
            return
        
        # If cache is invalid or doesn't exist, load from source files
        print("Loading databases from source files...")
        self.load_parts_database_from_source()
        self.load_customers_database()
        
        # Build search indexes after loading from source
        self._build_search_indexes()
        
        # Save to cache for next time
        self._save_to_cache()
    
    def load_parts_database_from_source(self) -> None:
        """Load the parts database from CSV file (without building indexes)."""
        try:
            if os.path.exists(self.parts_db_path):
                self.parts_df = pd.read_csv(self.parts_db_path)
                
                # Handle different column name formats
                if 'Part' in self.parts_df.columns and 'Description' in self.parts_df.columns:
                    # Rename columns to match our expected format
                    self.parts_df = self.parts_df.rename(columns={
                        'Part': 'internal_part_number',
                        'Description': 'description'
                    })
                
                # Validate required columns
                required_columns = ['internal_part_number', 'description']
                missing_columns = [col for col in required_columns if col not in self.parts_df.columns]
                
                if missing_columns:
                    raise ValueError(f"Parts database missing required columns: {missing_columns}")
                
                # Clean up data
                self.parts_df['internal_part_number'] = self.parts_df['internal_part_number'].astype(str).str.strip()
                self.parts_df['description'] = self.parts_df['description'].astype(str).str.strip()
                
                # Clean up multi-line descriptions and normalize whitespace
                self.parts_df['description'] = self.parts_df['description'].str.replace('\n', ' ', regex=False)
                self.parts_df['description'] = self.parts_df['description'].str.replace('\r', ' ', regex=False)
                self.parts_df['description'] = self.parts_df['description'].str.replace(r'\s+', ' ', regex=True)
                self.parts_df['description'] = self.parts_df['description'].str.strip()
                
                # Remove empty rows
                self.parts_df = self.parts_df.dropna(subset=['internal_part_number', 'description'])
                self.parts_df = self.parts_df[self.parts_df['internal_part_number'] != '']
                self.parts_df = self.parts_df[self.parts_df['description'] != '']
                
                print(f"Loaded {len(self.parts_df)} parts from database")
            else:
                print(f"Parts database not found at {self.parts_db_path}. Creating empty database.")
                self.parts_df = pd.DataFrame(columns=['internal_part_number', 'description'])
                
        except Exception as e:
            print(f"Error loading parts database: {e}")
            self.parts_df = pd.DataFrame(columns=['internal_part_number', 'description'])
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get MD5 hash of a file for cache invalidation."""
        if not os.path.exists(file_path):
            return ""
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is valid by comparing file hashes."""
        if not os.path.exists(self.cache_metadata_path):
            return False
        
        try:
            with open(self.cache_metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            # Check if source files have changed
            parts_hash = self._get_file_hash(self.parts_db_path)
            customers_hash = self._get_file_hash(self.customers_db_path)
            
            return (metadata.get('parts_hash') == parts_hash and 
                    metadata.get('customers_hash') == customers_hash)
        except Exception:
            return False
    
    def _load_from_cache(self) -> bool:
        """Load databases from cache if valid."""
        if not self._is_cache_valid():
            return False
        
        try:
            # Load parts indexes
            if os.path.exists(self.parts_cache_path):
                with open(self.parts_cache_path, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.parts_by_exact_match = cache_data['parts_by_exact_match']
                    self.description_words = cache_data['description_words']
                    # Convert defaultdict back from regular dict
                    self.parts_by_keywords = defaultdict(list, cache_data['parts_by_keywords'])
            
            # Load customers data
            if os.path.exists(self.customers_cache_path):
                with open(self.customers_cache_path, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.parts_df = cache_data['parts_df']
                    self.customers_df = cache_data['customers_df']
            
            return True
        except Exception as e:
            print(f"Error loading from cache: {e}")
            return False
    
    def _save_to_cache(self) -> None:
        """Save databases to cache."""
        try:
            # Save parts indexes
            cache_data = {
                'parts_by_exact_match': self.parts_by_exact_match,
                'description_words': self.description_words,
                'parts_by_keywords': dict(self.parts_by_keywords)  # Convert defaultdict to dict
            }
            with open(self.parts_cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # Save customers data
            cache_data = {
                'parts_df': self.parts_df,
                'customers_df': self.customers_df
            }
            with open(self.customers_cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # Save metadata with file hashes
            metadata = {
                'parts_hash': self._get_file_hash(self.parts_db_path),
                'customers_hash': self._get_file_hash(self.customers_db_path)
            }
            with open(self.cache_metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            print("Cached databases saved successfully")
        except Exception as e:
            print(f"Error saving to cache: {e}")
    
    def load_customers_database(self) -> None:
        """Load the customers database from Excel file."""
        try:
            if os.path.exists(self.customers_db_path):
                self.customers_df = pd.read_excel(self.customers_db_path)
                
                # Handle different column name formats for Excel file
                if 'Customer' in self.customers_df.columns and 'Name' in self.customers_df.columns:
                    # Rename columns to match our expected format
                    self.customers_df = self.customers_df.rename(columns={
                        'Customer': 'account_number',
                        'Name': 'company_name'
                    })
                
                # Validate required columns
                required_columns = ['company_name', 'account_number', 'Address']
                optional_columns = ['State', 'state', 'STATE']
                missing_columns = [col for col in required_columns if col not in self.customers_df.columns]
                
                if missing_columns:
                    raise ValueError(f"Customers database missing required columns: {missing_columns}")
                
                # Clean up data
                self.customers_df['company_name'] = self.customers_df['company_name'].astype(str).str.strip()
                self.customers_df['account_number'] = self.customers_df['account_number'].astype(str).str.strip()
                self.customers_df['Address'] = self.customers_df['Address'].astype(str).str.strip()
                
                # Handle state column (check for different possible column names)
                state_column = None
                optional_columns = ['State/Prov', 'State', 'state', 'STATE', 'State/Province']
                for col in optional_columns:
                    if col in self.customers_df.columns:
                        state_column = col
                        break
                
                if state_column:
                    self.customers_df['state'] = self.customers_df[state_column].astype(str).str.strip()
                else:
                    self.customers_df['state'] = ""
                
                # Remove empty rows
                self.customers_df = self.customers_df.dropna(subset=['company_name', 'account_number'])
                self.customers_df = self.customers_df[self.customers_df['company_name'] != '']
                self.customers_df = self.customers_df[self.customers_df['account_number'] != '']
                
                print(f"Loaded {len(self.customers_df)} customers from database")
            else:
                print(f"Customers database not found at {self.customers_db_path}. Creating empty database.")
                self.customers_df = pd.DataFrame(columns=['company_name', 'account_number', 'Address'])
                
        except Exception as e:
            print(f"Error loading customers database: {e}")
            self.customers_df = pd.DataFrame(columns=['company_name', 'account_number', 'Address'])
    
    def _build_search_indexes(self) -> None:
        """Build search indexes for faster part lookups."""
        if self.parts_df is None or self.parts_df.empty:
            return
        
        print("Building search indexes for faster lookups...")
        
        # Clear existing indexes
        self.parts_by_exact_match.clear()
        self.parts_by_keywords.clear()
        self.description_words.clear()
        
        for idx, row in self.parts_df.iterrows():
            part_number = row['internal_part_number']
            description = row['description'].lower()
            
            # Exact part number lookup (for direct matches)
            self.parts_by_exact_match[part_number.upper()] = Part(
                internal_part_number=part_number,
                description=row['description']
            )
            
            # Extract keywords from description for faster searching
            # Split on common separators and clean
            words = re.findall(r'\b[a-zA-Z0-9]{2,}\b', description)
            
            for word in words:
                word_clean = word.lower().strip()
                if len(word_clean) >= 2:  # Skip very short words
                    if word_clean not in self.description_words:
                        self.description_words[word_clean] = []
                    self.description_words[word_clean].append(idx)
        
        print(f"Indexed {len(self.parts_by_exact_match)} parts with {len(self.description_words)} unique keywords")
    
    def find_part_by_exact_number(self, part_number: str) -> Optional[Part]:
        """Find part by exact part number match (fastest lookup)."""
        if not part_number:
            return None
        
        # Try exact match first (case insensitive)
        part_upper = part_number.upper().strip()
        if part_upper in self.parts_by_exact_match:
            return self.parts_by_exact_match[part_upper]
        
        # Simple KOI prefix removal: "KOI 30623" -> "30623" or "ΚΟΙ 30623" -> "30623"
        if part_upper.startswith(('KOI ', 'ΚΟΙ ')):  # Handle both Latin and Greek characters
            simple_number = part_upper[4:].strip()  # Remove "KOI " or "ΚΟΙ "
            if simple_number and simple_number in self.parts_by_exact_match:
                print(f"Simple KOI prefix removal: '{part_upper}' -> '{simple_number}'")
                return self.parts_by_exact_match[simple_number]
        
        # Try Koike part number transformations: "KOIZA323-2050" -> "ZA3232050"
        koike_transformed = self._transform_koike_part_number(part_upper)
        if koike_transformed and koike_transformed in self.parts_by_exact_match:
            print(f"Koike transformation match: '{part_upper}' -> '{koike_transformed}'")
            return self.parts_by_exact_match[koike_transformed]
        
        # Try partial matches for cases like "ZA3232062" vs "3232062" or "KOI KJ12250013" vs "KJ12250013"
        for stored_part, part_obj in self.parts_by_exact_match.items():
            # More precise partial matching - require substantial overlap
            if len(part_upper) > 3 and len(stored_part) > 3:
                # Check if one is a prefix/suffix of the other with significant overlap
                if (stored_part in part_upper and len(stored_part) >= len(part_upper) * 0.6) or \
                   (part_upper in stored_part and len(part_upper) >= len(stored_part) * 0.6):
                    # Additional check: ensure it's not just a small number contained in a larger string
                    if len(stored_part) >= 5 or len(part_upper) >= 5:  # Avoid matching single digits
                        print(f"Partial match found: '{part_upper}' matches '{stored_part}'")
                        return part_obj
        
        return None
    
    def _normalize_company_name(self, company_name: str) -> str:
        """
        Normalize company name by removing common company type indicators.
        This helps match companies that differ only in their legal structure.
        
        Examples:
        - "Indiana Oxygen Co." -> "Indiana Oxygen Co"
        - "Indiana Oxygen Co, Inc" -> "Indiana Oxygen Co"
        - "ABC Corp LLC" -> "ABC"
        - "XYZ Company Ltd" -> "XYZ"
        """
        if not company_name:
            return ""
        
        # Convert to uppercase for consistent matching
        normalized = company_name.upper().strip()
        
        # Common company type indicators to remove (with various punctuation)
        company_types = [
            r'\b(INC|INCORPORATED|CORP|CORPORATION|LLC|L\.L\.C\.|LTD|LIMITED|CO\.?|COMPANY|LP|L\.P\.|LLP|L\.L\.P\.)\b\.?',
            r'\b(INC|INCORPORATED|CORP|CORPORATION|LLC|L\.L\.C\.|LTD|LIMITED|CO\.?|COMPANY|LP|L\.P\.|LLP|L\.L\.P\.)\b,?\s*$',
            r'^,?\s*(INC|INCORPORATED|CORP|CORPORATION|LLC|L\.L\.C\.|LTD|LIMITED|CO\.?|COMPANY|LP|L\.P\.|LLP|L\.L\.P\.)\b',
        ]
        
        import re
        for pattern in company_types:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Clean up extra spaces and punctuation
        normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single space
        normalized = re.sub(r'[,\s]+$', '', normalized)  # Remove trailing commas and spaces
        normalized = re.sub(r'^[,\s]+', '', normalized)  # Remove leading commas and spaces
        normalized = normalized.strip()
        
        return normalized
    
    def _transform_koike_part_number(self, part_number: str) -> Optional[str]:
        """
        Transform Koike part numbers from PO format to database format.
        Examples: 
        - "KOIZA323-2050" -> "ZA3232050"
        - "KOIZA323-2030" -> "ZA3232030"
        """
        import re
        
        # Pattern for KOIZA323-XXXX format
        koike_pattern = r'KOI(ZA\d{3})-(\d{4})'
        match = re.match(koike_pattern, part_number)
        
        if match:
            prefix = match.group(1)  # ZA323
            suffix = match.group(2)  # 2050
            # Transform ZA323-2050 to ZA3232050 (insert the last digit of prefix into the number)
            if len(prefix) >= 5 and prefix.startswith('ZA'):
                za_number = prefix[2:]  # 323
                transformed = f"ZA{za_number}{suffix}"  # ZA3232050
                return transformed
        
        return None
    
    def find_part_by_description(self, description: str, threshold: int = 80) -> Optional[Part]:
        """
        Find internal part number by matching description using optimized search.
        
        Args:
            description: Description to search for
            threshold: Minimum similarity score (0-100)
            
        Returns:
            Part object if found, None otherwise
        """
        if self.parts_df is None or self.parts_df.empty:
            return None
        
        if not description or description.strip() == '':
            return None
        
        # First, try keyword-based pre-filtering for speed
        description_lower = description.lower()
        description_words = re.findall(r'\b[a-zA-Z0-9]{2,}\b', description_lower)
        
        candidate_indices = set()
        
        # Find parts that contain matching keywords
        for word in description_words:
            if word in self.description_words:
                candidate_indices.update(self.description_words[word])
        
        # If we have candidates, search only among them (much faster)
        if candidate_indices:
            candidate_descriptions = []
            candidate_indices_list = list(candidate_indices)
            
            for idx in candidate_indices_list:
                if idx < len(self.parts_df):
                    candidate_descriptions.append(self.parts_df.iloc[idx]['description'])
            
            if candidate_descriptions:
                # Fuzzy match only among candidates
                match = process.extractOne(description, candidate_descriptions, scorer=fuzz.ratio)
                
                if match and match[1] >= threshold:
                    # Find the original row
                    matching_row = self.parts_df[self.parts_df['description'] == match[0]].iloc[0]
                    return Part(
                        internal_part_number=matching_row['internal_part_number'],
                        description=matching_row['description']
                    )
        
        # Fallback to full search if no keyword matches (but with higher threshold)
        if threshold <= 85:  # Only do full search for high-confidence requests
            print(f"Performing full database search for: {description[:50]}...")
            descriptions = self.parts_df['description'].tolist()
            match = process.extractOne(description, descriptions, scorer=fuzz.ratio)
            
            if match and match[1] >= threshold:
                matching_row = self.parts_df[self.parts_df['description'] == match[0]].iloc[0]
                return Part(
                    internal_part_number=matching_row['internal_part_number'],
                    description=matching_row['description']
                )
        
        return None
    
    def find_customer_by_company_name(self, company_name: str, billing_address: str = "", threshold: int = 85) -> Optional[Customer]:
        """
        Find customer account number by matching company name and billing address.
        Uses ADDRESS-FIRST matching strategy for better accuracy.
        
        Args:
            company_name: Company name to search for
            billing_address: Billing address to help narrow down matches
            threshold: Minimum similarity score (0-100)
            
        Returns:
            Customer object if found, None otherwise
        """
        if self.customers_df is None or self.customers_df.empty:
            return None
        
        if not company_name or company_name.strip() == '':
            return None
        
        # Normalize input for better matching
        search_name = company_name.strip()
        
        # Address-first matching strategy (ONLY strategy - no name-only fallback)
        if billing_address and billing_address.strip():
            print(f"Using ADDRESS-FIRST matching strategy...")
            address_match = self._find_customer_by_address_then_name(search_name, billing_address, threshold)
            return address_match  # Returns Customer or None
        else:
            # No address provided - can't match without it
            print(f"  No billing address provided - cannot match customer")
            return None
    
    def _normalize_address_for_matching(self, address: str) -> str:
        """
        Extract and normalize just the street address (before city/state/zip).
        Database stores street separately from city/state/zip.
        
        Args:
            address: Full address string (may include company name, street, city, state, zip)
            
        Returns:
            Just the street address, normalized
        """
        addr = address.upper().strip()
        
        # Split by newlines to separate address lines
        lines = addr.split('\n')
        
        # Find the street address line (skip company name if present)
        street = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip if it looks like a company name (has business terms but no numbers)
            if any(term in line for term in ['INC', 'LLC', 'CORP']) and not re.search(r'\d', line):
                continue
            
            # Skip if it's just a company name without address indicators
            if not re.search(r'\d', line) and any(term in line for term in ['SUPPLY', 'WELDING', 'GAS', 'OXYGEN']):
                continue
            
            # Skip if it looks like city/state/zip line (state code + zip)
            if re.search(r'\b[A-Z]{2}\b\s+\d{5}', line):  # "KS 67201" pattern
                continue
            
            # If line has a number, it's likely the street address
            if re.search(r'\d', line):
                street = line
                break
        
        if not street:
            # Fallback: use first non-empty line
            street = next((line.strip() for line in lines if line.strip()), addr)
        
        # Handle suite/unit numbers intelligently
        # "SUITE 1700-1250 BOUL" → keep "1250 BOUL" (building number)
        # "SUITE 1700 123 MAIN ST" → keep "123 MAIN ST"
        suite_pattern = r'\b(SUITE|UNIT|APT|APARTMENT|#)\s*[\dA-Z]+\s*-\s*(\d+)'
        match = re.search(suite_pattern, street, flags=re.IGNORECASE)
        if match:
            # Keep the second number (building number), remove suite prefix
            building_num = match.group(2)
            street = re.sub(suite_pattern, building_num, street, flags=re.IGNORECASE)
        else:
            # Simple suite without hyphen - just remove it
            street = re.sub(r'\b(SUITE|UNIT|APT|APARTMENT|#)\s*[\dA-Z]+\s+', '', street, flags=re.IGNORECASE)
        
        # Normalize common abbreviations for better matching
        abbreviations = {
            r'\bBOULEVARD\b': 'BLVD',
            r'\bBOUL\.?\b': 'BLVD',  # French abbreviation
            r'\bSTREET\b': 'ST',
            r'\bAVENUE\b': 'AVE', 
            r'\bROAD\b': 'RD',
            r'\bDRIVE\b': 'DR',
            r'\bLANE\b': 'LN',
            r'\bPARK\b': 'PK',
            r'\bPARKWAY\b': 'PKWY'
        }
        
        for full, abbr in abbreviations.items():
            street = re.sub(full, abbr, street, flags=re.IGNORECASE)
        
        # Clean up whitespace and extra punctuation
        street = re.sub(r'\s+', ' ', street).strip()
        street = street.replace(',', ' ').strip()
        return street
    
    def _find_customer_by_address_then_name(self, company_name: str, billing_address: str, threshold: int = 85) -> Optional[Customer]:
        """
        Find customer by matching address first, then verifying with company name.
        
        Args:
            company_name: Company name to verify
            billing_address: Billing address to match
            threshold: Minimum similarity score
            
        Returns:
            Customer object if found, None otherwise
        """
        # Normalize address for matching (extract street, normalize abbreviations)
        search_address = self._normalize_address_for_matching(billing_address)
        
        # Get all addresses from database and normalize them
        addresses = self.customers_df['Address'].tolist()
        normalized_addresses = [(addr, self._normalize_address_for_matching(addr)) for addr in addresses]
        
        # Fuzzy match normalized addresses to get top 10 candidates
        normalized_db_addrs = [norm_addr for _, norm_addr in normalized_addresses]
        address_candidates = process.extract(search_address, normalized_db_addrs, scorer=fuzz.ratio, limit=10)
        
        # Map back to original addresses
        norm_to_orig = {norm: orig for orig, norm in normalized_addresses}
        address_candidates_orig = [(norm_to_orig.get(norm_addr, norm_addr), score) for norm_addr, score in address_candidates]
        
        print(f"  Normalized search address: {search_address}")
        print(f"  Top address matches:")
        for i, (addr, score) in enumerate(address_candidates_orig[:5], 1):
            print(f"    {i}. {addr} ({score}%)")
        
        # Split candidates by confidence level
        exact_matches = [(addr, score) for addr, score in address_candidates_orig if score >= 95]
        llm_candidates = [(addr, score) for addr, score in address_candidates_orig if 60 <= score < 95]
        
        # PRIORITY 1: Exact address matches (95%+) - trust immediately
        if exact_matches:
            print(f"  Found {len(exact_matches)} exact address match(es) (≥95%)")
            
            for matched_address, addr_score in exact_matches:
                matching_rows = self.customers_df[self.customers_df['Address'] == matched_address]
                
                for _, row in matching_rows.iterrows():
                    db_company_name = row['company_name']
                    print(f"  → {db_company_name} (address {addr_score}% - exact match, name check skipped)")
                    print(f"  ✅ MATCH FOUND via exact address!")
                    return Customer(
                        company_name=db_company_name,
                        account_number=row['account_number'],
                        address=row['Address'],
                        state=row.get('state', '')
                    )
        
        # PRIORITY 2: Potential matches (60-94%) - use LLM to decide with full context
        llm_match = None  # Initialize llm_match
        if llm_candidates:
            print(f"  Found {len(llm_candidates)} potential match(es) (60-94%)")
            print(f"  Using LLM to intelligently compare address + name context...")
            
            # Take top 10 candidates for LLM analysis
            top_candidates = address_candidates_orig[:10]
            llm_match = self._llm_address_name_comparison(
                company_name, 
                billing_address, 
                search_address,
                top_candidates
            )
            
        if llm_match:
            return llm_match
        else:
            print(f"  LLM could not confidently match (>95% confidence required)")
        # No potential matches found - try city fallback before giving up
        print(f"  No address matches above 60% threshold (best: {address_candidates_orig[0][1] if address_candidates_orig else 0}%)")
        
    
    def _extract_city_from_address(self, address: str) -> Optional[str]:
        """Extract city name from address string."""
        if not address:
            return None
        
        # Split by newlines and look for city/state/zip pattern
        lines = address.upper().split('\n')
        for line in lines:
            line = line.strip()
            # Look for pattern like "CITY, STATE ZIP" or "CITY STATE ZIP"
            if ',' in line:
                # "CITY, STATE ZIP" format
                parts = line.split(',')
                if len(parts) >= 2:
                    city = parts[0].strip()
                    if city and not any(word in city for word in ['PO BOX', 'BOX', 'SUITE', 'UNIT']):
                        return city
            elif re.search(r'\b[A-Z]{2}\b\s+\d{5}', line):
                # "CITY STATE ZIP" format - extract city before state
                match = re.search(r'^(.+?)\s+[A-Z]{2}\s+\d{5}', line)
                if match:
                    city = match.group(1).strip()
                    if city and not any(word in city for word in ['PO BOX', 'BOX', 'SUITE', 'UNIT']):
                        return city
        
        return None
    
    def _normalize_city_name(self, city: str) -> str:
        """Normalize city name for comparison (case-insensitive, handle hyphens)."""
        if not city:
            return ""
        
        # Convert to uppercase and replace hyphens with spaces
        normalized = city.upper().replace('-', ' ').strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _llm_address_name_comparison(self, company_name: str, full_billing_address: str, normalized_address: str, address_candidates: list) -> Optional[Customer]:
        """
        Use LLM to intelligently compare company name + address against top candidates.
        
        Args:
            company_name: Extracted company name from PO
            full_billing_address: Full billing address from PO
            normalized_address: Normalized street address
            address_candidates: List of (address, score) tuples
            
        Returns:
            Customer object if LLM confidently matches (>95%), None otherwise
        """
        try:
            from openai import OpenAI
            from dotenv import load_dotenv
            import os
            
            load_dotenv('config.env')
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                print("  No OpenAI API key found, skipping LLM comparison")
                return None
            
            client = OpenAI(api_key=openai_api_key)
            
            # Build candidate list with company names for each address
            candidates_list = []
            for i, (db_address, addr_score) in enumerate(address_candidates, 1):
                # Find all customers with this address
                matching_rows = self.customers_df[self.customers_df['Address'] == db_address]
                for _, row in matching_rows.iterrows():
                    candidates_list.append({
                        'number': i,
                        'company': row['company_name'],
                        'address': db_address,
                        'account': row['account_number'],
                        'score': addr_score
                    })
            
            # Format for LLM
            candidates_text = "\n".join([
                f"{c['number']}. {c['company']} | {c['address']} | Account: {c['account']} (address match: {c['score']}%)"
                for c in candidates_list
            ])
            
            prompt = f"""You are comparing a purchase order's billing information against database candidates to find the correct customer match.

PURCHASE ORDER INFORMATION:
Company Name: {company_name}
Billing Address: {full_billing_address}
Normalized Street: {normalized_address}

DATABASE CANDIDATES (ranked by address similarity):
{candidates_text}

INSTRUCTIONS:
1. Compare the PO's company name AND address against each candidate
2. Consider that addresses may have minor variations (abbreviations, formatting)
3. The company name should be consistent (allowing for legal suffixes like Inc, LLC)
4. Only return a match if you are >95% confident this is the correct customer
5. If multiple candidates seem equally likely, return NONE (better to mark as MISSING than guess wrong)

Return your response in this exact format:
BEST_MATCH: [account number from list, or NONE]
CONFIDENCE: [0-100]
REASONING: [brief explanation]"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at matching customer records using both name and address information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.0
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse response
            lines = result_text.split('\n')
            best_match = None
            confidence = 0
            reasoning = ""
            
            for line in lines:
                if line.startswith('BEST_MATCH:'):
                    best_match = line.replace('BEST_MATCH:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = int(line.replace('CONFIDENCE:', '').strip())
                    except ValueError:
                        confidence = 0
                elif line.startswith('REASONING:'):
                    reasoning = line.replace('REASONING:', '').strip()
            
            print(f"  LLM Decision: {best_match} (confidence: {confidence}%)")
            print(f"  Reasoning: {reasoning}")
            
            # Only accept if confidence > 95% and match found
            if best_match and best_match != "NONE" and confidence > 95:
                # Find the customer by account number
                matching_row = self.customers_df[self.customers_df['account_number'] == best_match]
                if not matching_row.empty:
                    row = matching_row.iloc[0]
                    print(f"  ✅ LLM MATCH: {row['company_name']} (Account: {best_match})")
                    return Customer(
                        company_name=row['company_name'],
                        account_number=row['account_number'],
                        address=row['Address'],
                        state=row.get('state', '')
                    )
            
            return None
            
        except Exception as e:
            print(f"  LLM comparison failed: {e}")
            return None
    
    def _find_customer_with_llm(self, search_name: str, company_names: list, threshold: int) -> Optional[Customer]:
        """
        Use LLM to find the best customer match.
        
        Args:
            search_name: Company name to search for
            company_names: List of all company names in database
            threshold: Minimum confidence threshold
            
        Returns:
            Customer object if found, None otherwise
        """
        try:
            # Import OpenAI client (lazy import to avoid dependency issues)
            from openai import OpenAI
            from dotenv import load_dotenv
            import os
            
            # Load environment variables
            load_dotenv('config.env')
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                print("No OpenAI API key found, skipping LLM matching")
                return None
            
            client = OpenAI(api_key=openai_api_key)
            
            # Get top 30 fuzzy matches as candidates for LLM to evaluate
            # Using more candidates gives LLM better context to choose from
            candidates = process.extract(search_name, company_names, scorer=fuzz.ratio, limit=30)
            
            print(f"Top candidates for '{search_name}':")
            for i, (name, score) in enumerate(candidates[:5], 1):
                print(f"  {i}. {name} ({score}%)")
            
            if not candidates:
                print(f"No candidates found for LLM evaluation: '{search_name}'")
                return None
            
            # Prepare candidate list for LLM
            candidate_list = []
            for i, (name, score) in enumerate(candidates, 1):
                candidate_list.append(f"{i}. {name} (match score: {score:.1f}%)")
            
            candidates_text = "\n".join(candidate_list)
            
            # Create LLM prompt
            prompt = f"""You are an expert at matching company names. I need you to find the best match for a company name from a list of candidates.

SEARCH NAME: "{search_name}"

CANDIDATES (ranked by fuzzy matching):
{candidates_text}

Instructions:
1. Focus on the UNIQUE identifying part of the company name (usually the first word or acronym)
2. **CRITICAL MATCHING RULES**:
   - Match when only legal suffixes differ (Inc vs LLC vs Corp) → 95-100% confidence
   - Do NOT match when the core business identifier is different → <50% confidence
   - Consider location prefixes separately from the company name
3. Legal/descriptive suffixes that don't matter: Inc, LLC, Corp, Co, Company, Incorporated, Ltd
4. Industry terms that usually don't distinguish companies: Supply, Welding, Gas, Oxygen, Services, Industries
5. What DOES matter: The unique business name/identifier (the proper noun or acronym that makes it unique)
6. If only legal suffixes or minor abbreviations differ, give 95-100% confidence
7. If the unique identifying name is different, give low confidence even if industry terms match

Return your response in this exact format:
   BEST_MATCH: [exact company name from the list]
   CONFIDENCE: [0-100]

If no good match exists (confidence < 70), respond with:
BEST_MATCH: NONE
CONFIDENCE: 0"""

            # Call LLM
            response = client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o (same as existing code)
                messages=[
                    {"role": "system", "content": "You are an expert at company name matching for business databases."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1  # Low temperature for consistent results
            )
            
            llm_response = response.choices[0].message.content.strip()
            
            # Parse LLM response
            lines = llm_response.split('\n')
            best_match = None
            confidence = 0
            reasoning = ""
            
            for line in lines:
                if line.startswith('BEST_MATCH:'):
                    best_match = line.replace('BEST_MATCH:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = int(line.replace('CONFIDENCE:', '').strip())
                    except ValueError:
                        confidence = 0
                elif line.startswith('REASONING:'):
                    reasoning = line.replace('REASONING:', '').strip()
            
            # Check if we have a valid match
            if best_match and best_match != "NONE" and confidence >= threshold:
                # Find the customer record
                matching_row = self.customers_df[self.customers_df['company_name'] == best_match]
                if not matching_row.empty:
                    print(f"LLM matched '{search_name}' -> '{best_match}' (confidence: {confidence}%)")
                    return Customer(
                        company_name=matching_row.iloc[0]['company_name'],
                        account_number=matching_row.iloc[0]['account_number'],
                        address=matching_row.iloc[0]['Address'],
                        state=matching_row.iloc[0].get('state', '')
                    )
                else:
                    print(f"LLM found match '{best_match}' but it's not in database")
            else:
                print(f"LLM found no suitable match for '{search_name}' (confidence: {confidence}%)")
            
            return None
            
        except Exception as e:
            print(f"LLM matching failed: {e}")
            return None
    
    def _find_customer_with_fuzzy_matching(self, search_name: str, company_names: list, threshold: int) -> Optional[Customer]:
        """
        Fallback fuzzy matching using the original strategies.
        
        Args:
            search_name: Company name to search for
            company_names: List of all company names in database
            threshold: Minimum similarity score (0-100)
            
        Returns:
            Customer object if found, None otherwise
        """
        # Try multiple fuzzy matching strategies for better case handling
        best_match = None
        best_score = 0
        
        # Strategy 1: Direct fuzzy matching (handles most cases)
        match = process.extractOne(search_name, company_names, scorer=fuzz.ratio)
        if match and match[1] > best_score:
            best_match = match
            best_score = match[1]
        
        # Strategy 2: Case-insensitive token sort ratio (better for word order differences)
        match = process.extractOne(search_name, company_names, scorer=fuzz.token_sort_ratio)
        if match and match[1] > best_score:
            best_match = match
            best_score = match[1]
        
        # Strategy 3: Partial ratio (good for partial matches)
        match = process.extractOne(search_name, company_names, scorer=fuzz.partial_ratio)
        if match and match[1] > best_score:
            best_match = match
            best_score = match[1]
        
        # Strategy 4: Normalized company name matching (removes Inc, LLC, Corp, etc.)
        normalized_search = self._normalize_company_name(search_name)
        if normalized_search != search_name:  # Only if normalization changed something
            # Create normalized versions of all company names
            normalized_company_names = [self._normalize_company_name(name) for name in company_names]
            
            # Find best match among normalized names
            match = process.extractOne(normalized_search, normalized_company_names, scorer=fuzz.ratio)
            if match and match[1] > best_score:
                # Find the original company name that corresponds to this normalized match
                original_index = normalized_company_names.index(match[0])
                original_company = company_names[original_index]
                best_match = (original_company, match[1])
                best_score = match[1]
                print(f"Normalized company matching: '{search_name}' -> '{original_company}' (normalized: '{normalized_search}' -> '{match[0]}', score: {match[1]}%)")
        
        # Debug output for troubleshooting
        if best_match:
            print(f"Fuzzy matching: '{search_name}' -> '{best_match[0]}' (score: {best_score}%, threshold: {threshold}%)")
        
        if best_match and best_score >= threshold:
            matched_company = best_match[0]
            # Find the row with this company name
            matching_row = self.customers_df[self.customers_df['company_name'] == matched_company].iloc[0]
            
            return Customer(
                company_name=matching_row['company_name'],
                account_number=matching_row['account_number'],
                address=matching_row['Address'],
                state=matching_row.get('state', '')
            )
        
        # If no match found, show debug info
        if best_match:
            print(f"Fuzzy matching failed: '{search_name}' best match was '{best_match[0]}' with {best_score}% (below threshold {threshold}%)")
        else:
            print(f"Fuzzy matching failed: No matches found for '{search_name}'")
            
        return None
    
    def find_customer_with_confidence(self, company_name: str, threshold: int = 85) -> Tuple[Optional[Customer], float]:
        """
        Find customer account number by matching company name using LLM-enhanced matching.
        Returns both the customer object and the confidence score.
        
        Args:
            company_name: Company name to search for
            threshold: Minimum similarity score (0-100)
            
        Returns:
            Tuple of (Customer object if found, confidence score 0-100)
        """
        if self.customers_df is None or self.customers_df.empty:
            return None, 0.0
        
        if not company_name or company_name.strip() == '':
            return None, 0.0
        
        # Normalize input for better matching
        search_name = company_name.strip()
        
        # Get all company names for fuzzy matching
        company_names = self.customers_df['company_name'].tolist()
        
        # Try LLM-based matching first
        llm_result = self._find_customer_with_llm_and_confidence(search_name, company_names, threshold)
        if llm_result[0]:  # If customer found
            return llm_result
        
        # Fallback to traditional fuzzy matching strategies
        print(f"LLM matching failed or unavailable, falling back to fuzzy matching for: '{search_name}'")
        return self._find_customer_with_fuzzy_matching_and_confidence(search_name, company_names, threshold)
    
    def _find_customer_with_llm_and_confidence(self, search_name: str, company_names: list, threshold: int) -> Tuple[Optional[Customer], float]:
        """
        Use LLM to find the best customer match with confidence score.
        
        Args:
            search_name: Company name to search for
            company_names: List of all company names in database
            threshold: Minimum confidence threshold
            
        Returns:
            Tuple of (Customer object if found, confidence score 0-100)
        """
        try:
            # Import OpenAI client (lazy import to avoid dependency issues)
            from openai import OpenAI
            from dotenv import load_dotenv
            import os
            
            # Load environment variables
            load_dotenv('config.env')
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not openai_api_key:
                print("No OpenAI API key found, skipping LLM matching")
                return None, 0.0
            
            client = OpenAI(api_key=openai_api_key)
            
            # Get top 10 fuzzy matches as candidates for LLM to evaluate
            candidates = process.extract(search_name, company_names, scorer=fuzz.ratio, limit=10)
            
            if not candidates:
                print(f"No fuzzy candidates found for LLM evaluation: '{search_name}'")
                return None, 0.0
            
            # Prepare candidate list for LLM
            candidate_list = []
            for i, (name, score) in enumerate(candidates, 1):
                candidate_list.append(f"{i}. {name} (fuzzy score: {score}%)")
            
            candidates_text = "\n".join(candidate_list)
            
            # Create LLM prompt
            prompt = f"""You are an expert at matching company names. I need you to find the best match for a company name from a list of candidates.

SEARCH NAME: "{search_name}"

CANDIDATES (with fuzzy matching scores):
{candidates_text}

Instructions:
1. Determine which candidate best matches the search name
2. **CRITICAL**: If the only difference is a legal structure suffix (Inc, LLC, Corp, Co, Company, etc.), give 95-100% confidence
3. **CRITICAL**: If the core business name is identical and only legal structure differs, this is the same company
4. Consider abbreviations and variations (Company vs Co, Corporation vs Corp, etc.)
5. Consider that the same company might be listed with slight differences
6. **Examples of high confidence matches**:
   - "ABC Corp" matches "ABC Inc" (95%+ confidence)
   - "XYZ Company" matches "XYZ LLC" (95%+ confidence)
   - "Indiana Oxygen Co" matches "Indiana Oxygen Co, Inc" (95%+ confidence)
7. Return your response in this exact format:
   BEST_MATCH: [exact company name from the list]
   CONFIDENCE: [0-100]
   REASONING: [brief explanation of why this is the best match]

If no good match exists (confidence < 70), respond with:
BEST_MATCH: NONE
CONFIDENCE: 0
REASONING: No suitable match found"""

            # Call LLM
            response = client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o (same as existing code)
                messages=[
                    {"role": "system", "content": "You are an expert at company name matching for business databases."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1  # Low temperature for consistent results
            )
            
            llm_response = response.choices[0].message.content.strip()
            
            # Parse LLM response
            lines = llm_response.split('\n')
            best_match = None
            confidence = 0
            reasoning = ""
            
            for line in lines:
                if line.startswith('BEST_MATCH:'):
                    best_match = line.replace('BEST_MATCH:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = int(line.replace('CONFIDENCE:', '').strip())
                    except ValueError:
                        confidence = 0
                elif line.startswith('REASONING:'):
                    reasoning = line.replace('REASONING:', '').strip()
            
            # Check if we have a valid match
            if best_match and best_match != "NONE" and confidence >= threshold:
                # Find the customer record
                matching_row = self.customers_df[self.customers_df['company_name'] == best_match]
                if not matching_row.empty:
                    print(f"LLM matched '{search_name}' -> '{best_match}' (confidence: {confidence}%)")
                    return Customer(
                        company_name=matching_row.iloc[0]['company_name'],
                        account_number=matching_row.iloc[0]['account_number'],
                        address=matching_row.iloc[0]['Address'],
                        state=matching_row.iloc[0].get('state', '')
                    ), float(confidence)
                else:
                    print(f"LLM found match '{best_match}' but it's not in database")
            else:
                print(f"LLM found no suitable match for '{search_name}' (confidence: {confidence}%)")
            
            return None, 0.0
            
        except Exception as e:
            print(f"LLM matching failed: {e}")
            return None, 0.0
    
    def _find_customer_with_fuzzy_matching_and_confidence(self, search_name: str, company_names: list, threshold: int) -> Tuple[Optional[Customer], float]:
        """
        Fallback fuzzy matching using the original strategies with confidence score.
        
        Args:
            search_name: Company name to search for
            company_names: List of all company names in database
            threshold: Minimum similarity score (0-100)
            
        Returns:
            Tuple of (Customer object if found, confidence score 0-100)
        """
        # Try multiple fuzzy matching strategies for better case handling
        best_match = None
        best_score = 0
        
        # Strategy 1: Direct fuzzy matching (handles most cases)
        match = process.extractOne(search_name, company_names, scorer=fuzz.ratio)
        if match and match[1] > best_score:
            best_match = match
            best_score = match[1]
        
        # Strategy 2: Case-insensitive token sort ratio (better for word order differences)
        match = process.extractOne(search_name, company_names, scorer=fuzz.token_sort_ratio)
        if match and match[1] > best_score:
            best_match = match
            best_score = match[1]
        
        # Strategy 3: Partial ratio (good for partial matches)
        match = process.extractOne(search_name, company_names, scorer=fuzz.partial_ratio)
        if match and match[1] > best_score:
            best_match = match
            best_score = match[1]
        
        # Strategy 4: Normalized company name matching (removes Inc, LLC, Corp, etc.)
        normalized_search = self._normalize_company_name(search_name)
        if normalized_search != search_name:  # Only if normalization changed something
            # Create normalized versions of all company names
            normalized_company_names = [self._normalize_company_name(name) for name in company_names]
            
            # Find best match among normalized names
            match = process.extractOne(normalized_search, normalized_company_names, scorer=fuzz.ratio)
            if match and match[1] > best_score:
                # Find the original company name that corresponds to this normalized match
                original_index = normalized_company_names.index(match[0])
                original_company = company_names[original_index]
                best_match = (original_company, match[1])
                best_score = match[1]
                print(f"Normalized company matching: '{search_name}' -> '{original_company}' (normalized: '{normalized_search}' -> '{match[0]}', score: {match[1]}%)")
        
        # Debug output for troubleshooting
        if best_match:
            print(f"Fuzzy matching: '{search_name}' -> '{best_match[0]}' (score: {best_score}%, threshold: {threshold}%)")
        
        if best_match and best_score >= threshold:
            matched_company = best_match[0]
            # Find the row with this company name
            matching_row = self.customers_df[self.customers_df['company_name'] == matched_company].iloc[0]
            
            return Customer(
                company_name=matching_row['company_name'],
                account_number=matching_row['account_number'],
                address=matching_row['Address'],
                state=matching_row.get('state', '')
            ), float(best_score)
        
        # If no match found, show debug info
        if best_match:
            print(f"Fuzzy matching failed: '{search_name}' best match was '{best_match[0]}' with {best_score}% (below threshold {threshold}%)")
        else:
            print(f"Fuzzy matching failed: No matches found for '{search_name}'")
            
        return None, 0.0
    
    def get_all_parts(self) -> List[Part]:
        """Get all parts from the database."""
        if self.parts_df is None or self.parts_df.empty:
            return []
        
        parts = []
        for _, row in self.parts_df.iterrows():
            parts.append(Part(
                internal_part_number=row['internal_part_number'],
                description=row['description']
            ))
        return parts
    
    def get_all_customers(self) -> List[Customer]:
        """Get all customers from the database."""
        if self.customers_df is None or self.customers_df.empty:
            return []
        
        customers = []
        for _, row in self.customers_df.iterrows():
            customers.append(Customer(
                company_name=row['company_name'],
                account_number=row['account_number'],
                address=row['Address'],
                state=row.get('state', '')
            ))
        return customers
    
    def add_part(self, internal_part_number: str, description: str) -> bool:
        """
        Add a new part to the database.
        
        Args:
            internal_part_number: Internal part number
            description: Part description
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            if self.parts_df is None:
                self.parts_df = pd.DataFrame(columns=['internal_part_number', 'description'])
            
            # Check if part already exists
            existing = self.parts_df[self.parts_df['internal_part_number'] == internal_part_number]
            if not existing.empty:
                print(f"Part {internal_part_number} already exists")
                return False
            
            # Add new part
            new_part = pd.DataFrame({
                'internal_part_number': [internal_part_number],
                'description': [description]
            })
            self.parts_df = pd.concat([self.parts_df, new_part], ignore_index=True)
            
            return True
        except Exception as e:
            print(f"Error adding part: {e}")
            return False
    
    def add_customer(self, company_name: str, account_number: str) -> bool:
        """
        Add a new customer to the database.
        
        Args:
            company_name: Company name
            account_number: Account number in Epicor
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            if self.customers_df is None:
                self.customers_df = pd.DataFrame(columns=['company_name', 'account_number'])
            
            # Check if customer already exists
            existing = self.customers_df[self.customers_df['company_name'] == company_name]
            if not existing.empty:
                print(f"Customer {company_name} already exists")
                return False
            
            # Add new customer
            new_customer = pd.DataFrame({
                'company_name': [company_name],
                'account_number': [account_number]
            })
            self.customers_df = pd.concat([self.customers_df, new_customer], ignore_index=True)
            
            return True
        except Exception as e:
            print(f"Error adding customer: {e}")
            return False
    
    def find_customer_by_account_number(self, account_number: str) -> Optional[Customer]:
        """
        Find a customer by their account number.
        
        Args:
            account_number: The account number to search for
            
        Returns:
            Customer object if found, None otherwise
        """
        try:
            if self.customers_df is None or self.customers_df.empty:
                return None
            
            # Search for exact account number match
            matching_rows = self.customers_df[
                self.customers_df['account_number'].astype(str).str.strip() == str(account_number).strip()
            ]
            
            if not matching_rows.empty:
                row = matching_rows.iloc[0]
                return Customer(
                    company_name=row['company_name'],
                    account_number=row['account_number'],
                    address=row.get('Address', ''),
                    state=row.get('state', '')
                )
            
            return None
            
        except Exception as e:
            print(f"Error finding customer by account number: {e}")
            return None
    
    def save_databases(self) -> Tuple[bool, bool]:
        """
        Save both databases to CSV files.
        
        Returns:
            Tuple of (parts_saved, customers_saved)
        """
        parts_saved = self.save_parts_database()
        customers_saved = self.save_customers_database()
        return parts_saved, customers_saved
    
    def save_parts_database(self) -> bool:
        """Save the parts database to CSV file."""
        try:
            if self.parts_df is not None:
                self.parts_df.to_csv(self.parts_db_path, index=False)
                return True
            return False
        except Exception as e:
            print(f"Error saving parts database: {e}")
            return False
    
    def save_customers_database(self) -> bool:
        """Save the customers database to Excel file."""
        try:
            if self.customers_df is not None:
                self.customers_df.to_excel(self.customers_db_path, index=False)
                return True
            return False
        except Exception as e:
            print(f"Error saving customers database: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the databases."""
        parts_count = len(self.parts_df) if self.parts_df is not None else 0
        customers_count = len(self.customers_df) if self.customers_df is not None else 0
        
        return {
            "parts_count": parts_count,
            "customers_count": customers_count,
            "parts_db_exists": os.path.exists(self.parts_db_path),
            "customers_db_exists": os.path.exists(self.customers_db_path),
            "parts_db_path": self.parts_db_path,
            "customers_db_path": self.customers_db_path
        }

# Example usage
if __name__ == "__main__":
    # Test the database manager
    db_manager = DatabaseManager()
    
    # Print database stats
    stats = db_manager.get_database_stats()
    print("Database Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Example searches (would work with actual data)
    print("\nTesting search functionality...")
    part = db_manager.find_part_by_description("Sample part description")
    if part:
        print(f"Found part: {part.internal_part_number} - {part.description}")
    else:
        print("No matching part found")
    
    customer = db_manager.find_customer_by_company_name("Sample Company Inc")
    if customer:
        print(f"Found customer: {customer.company_name} - Account: {customer.account_number}")
    else:
        print("No matching customer found")
