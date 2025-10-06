"""
Supabase Database Manager
Manages parts and customers databases using Supabase PostgreSQL.
"""

import os
import pandas as pd
from collections import defaultdict
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from database_config import db_config

@dataclass
class Part:
    """Part data structure."""
    part_number: str
    description: str

@dataclass
class Customer:
    """Customer data structure."""
    customer_id: int
    company_name: str
    address: str
    city: str
    state_prov: str
    postal_code: str
    country: str

class SupabaseDatabaseManager:
    """Manages parts and customers databases using Supabase PostgreSQL."""
    
    def __init__(self):
        """Initialize the Supabase database manager."""
        self.parts_df = None
        self.customers_df = None
        
        # Search optimization indexes
        self.parts_by_exact_match = {}  # Exact part number lookup
        self.parts_by_keywords = defaultdict(list)  # Keyword-based lookup
        self.description_words = {}  # Word-based description index
        
        self.load_databases()
    
    def load_databases(self) -> None:
        """Load both parts and customers databases from Supabase."""
        print("Loading databases from Supabase...")
        self.load_parts_database()
        self.load_customers_database()
        
        # Build search indexes after loading
        self._build_search_indexes()
        print(f"✅ Loaded {len(self.parts_df)} parts and {len(self.customers_df)} customers from Supabase")
    
    def load_parts_database(self) -> None:
        """Load parts database from Supabase."""
        try:
            if db_config.is_postgres:
                # Load from Supabase PostgreSQL
                sql = "SELECT part_number, description FROM parts ORDER BY part_number"
                results = db_config.execute_raw_sql(sql)
                
                # Convert to DataFrame
                parts_data = []
                for row in results:
                    parts_data.append({
                        'internal_part_number': row[0],  # Map part_number to internal_part_number for compatibility
                        'description': row[1]
                    })
                
                self.parts_df = pd.DataFrame(parts_data)
                print(f"✅ Loaded {len(self.parts_df)} parts from Supabase")
            else:
                # Fallback to empty DataFrame if not PostgreSQL
                print("⚠️ Not using PostgreSQL, creating empty parts database")
                self.parts_df = pd.DataFrame(columns=['internal_part_number', 'description'])
                
        except Exception as e:
            print(f"❌ Error loading parts from Supabase: {e}")
            self.parts_df = pd.DataFrame(columns=['internal_part_number', 'description'])
    
    def load_customers_database(self) -> None:
        """Load customers database from Supabase."""
        try:
            if db_config.is_postgres:
                # Load from Supabase PostgreSQL
                sql = "SELECT customer_id, company_name, address, city, state_prov, postal_code, country FROM customers ORDER BY customer_id"
                results = db_config.execute_raw_sql(sql)
                
                # Convert to DataFrame
                customers_data = []
                for row in results:
                    customers_data.append({
                        'account_number': str(row[0]),  # Map customer_id to account_number for compatibility
                        'company_name': row[1],
                        'address': row[2] or '',
                        'state': row[4] or '',  # Map state_prov to state for compatibility
                        'city': row[3] or '',
                        'postal_code': row[5] or '',
                        'country': row[6] or ''
                    })
                
                self.customers_df = pd.DataFrame(customers_data)
                print(f"✅ Loaded {len(self.customers_df)} customers from Supabase")
            else:
                # Fallback to empty DataFrame if not PostgreSQL
                print("⚠️ Not using PostgreSQL, creating empty customers database")
                self.customers_df = pd.DataFrame(columns=['account_number', 'company_name', 'address', 'state'])
                
        except Exception as e:
            print(f"❌ Error loading customers from Supabase: {e}")
            self.customers_df = pd.DataFrame(columns=['account_number', 'company_name', 'address', 'state'])
    
    def _build_search_indexes(self) -> None:
        """Build search indexes for efficient lookups."""
        if self.parts_df is not None and not self.parts_df.empty:
            # Build exact match index
            self.parts_by_exact_match = {}
            for idx, row in self.parts_df.iterrows():
                part_num = str(row['internal_part_number']).strip().upper()
                self.parts_by_exact_match[part_num] = idx
            
            # Build keyword index
            self.parts_by_keywords = defaultdict(list)
            self.description_words = {}
            
            for idx, row in self.parts_df.iterrows():
                part_num = str(row['internal_part_number']).strip()
                description = str(row['description']).strip()
                
                # Add to keyword index
                keywords = self._extract_keywords(part_num, description)
                for keyword in keywords:
                    self.parts_by_keywords[keyword].append(idx)
                
                # Add to description words index
                words = self._extract_words(description)
                for word in words:
                    if word not in self.description_words:
                        self.description_words[word] = []
                    self.description_words[word].append(idx)
    
    def _extract_keywords(self, part_number: str, description: str) -> List[str]:
        """Extract searchable keywords from part number and description."""
        keywords = set()
        
        # Add part number variations
        keywords.add(part_number.upper())
        keywords.add(part_number.lower())
        
        # Add description words
        words = self._extract_words(description)
        keywords.update(words)
        
        # Add partial part numbers
        if len(part_number) > 3:
            for i in range(3, len(part_number) + 1):
                keywords.add(part_number[:i].upper())
        
        return list(keywords)
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract individual words from text for indexing."""
        if not text:
            return []
        
        # Clean and split text
        words = text.replace('\n', ' ').replace('\r', ' ').split()
        words = [word.strip('.,!?;:"()[]{}').upper() for word in words if len(word) > 2]
        
        return words
    
    def search_parts(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for parts using fuzzy matching."""
        if not query or self.parts_df is None or self.parts_df.empty:
            return []
        
        query = query.strip().upper()
        results = []
        
        # First try exact match
        if query in self.parts_by_exact_match:
            idx = self.parts_by_exact_match[query]
            row = self.parts_df.iloc[idx]
            results.append({
                'internal_part_number': row['internal_part_number'],
                'description': row['description'],
                'match_type': 'exact',
                'score': 1.0
            })
        
        # Then try keyword matching
        if len(results) < limit:
            keyword_matches = set()
            query_words = self._extract_words(query)
            
            for word in query_words:
                if word in self.parts_by_keywords:
                    keyword_matches.update(self.parts_by_keywords[word])
            
            for idx in keyword_matches:
                if len(results) >= limit:
                    break
                
                row = self.parts_df.iloc[idx]
                score = self._calculate_match_score(query, str(row['internal_part_number']), str(row['description']))
                
                if score > 0.3:  # Minimum threshold
                    results.append({
                        'internal_part_number': row['internal_part_number'],
                        'description': row['description'],
                        'match_type': 'fuzzy',
                        'score': score
                    })
        
        # Sort by score and return
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def _calculate_match_score(self, query: str, part_number: str, description: str) -> float:
        """Calculate match score for fuzzy search."""
        query = query.upper()
        part_number = part_number.upper()
        description = description.upper()
        
        score = 0.0
        
        # Part number similarity
        if query in part_number:
            score += 0.8
        elif any(word in part_number for word in query.split()):
            score += 0.6
        
        # Description similarity
        if query in description:
            score += 0.4
        elif any(word in description for word in query.split()):
            score += 0.2
        
        return min(score, 1.0)
    
    def search_customers(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for customers using fuzzy matching."""
        if not query or self.customers_df is None or self.customers_df.empty:
            return []
        
        query = query.strip().upper()
        results = []
        
        for idx, row in self.customers_df.iterrows():
            company_name = str(row['company_name']).upper()
            address = str(row['address']).upper()
            
            score = 0.0
            
            # Company name matching
            if query in company_name:
                score += 0.8
            elif any(word in company_name for word in query.split()):
                score += 0.6
            
            # Address matching
            if query in address:
                score += 0.3
            elif any(word in address for word in query.split()):
                score += 0.2
            
            if score > 0.3:  # Minimum threshold
                results.append({
                    'account_number': row['account_number'],
                    'company_name': row['company_name'],
                    'address': row['address'],
                    'state': row['state'],
                    'score': score
                })
        
        # Sort by score and return
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def get_part_by_number(self, part_number: str) -> Optional[Dict]:
        """Get a specific part by its number."""
        if not part_number or self.parts_df is None or self.parts_df.empty:
            return None
        
        part_number = part_number.strip().upper()
        
        if part_number in self.parts_by_exact_match:
            idx = self.parts_by_exact_match[part_number]
            row = self.parts_df.iloc[idx]
            return {
                'internal_part_number': row['internal_part_number'],
                'description': row['description']
            }
        
        return None
    
    def get_customer_by_account(self, account_number: str) -> Optional[Dict]:
        """Get a specific customer by account number."""
        if not account_number or self.customers_df is None or self.customers_df.empty:
            return None
        
        account_number = str(account_number).strip()
        
        # Search for exact match
        matches = self.customers_df[self.customers_df['account_number'] == account_number]
        if not matches.empty:
            row = matches.iloc[0]
            return {
                'account_number': row['account_number'],
                'company_name': row['company_name'],
                'address': row['address'],
                'state': row['state']
            }
        
        return None
    
    def add_part(self, part_number: str, description: str) -> bool:
        """Add a new part to the database."""
        try:
            if db_config.is_postgres:
                sql = "INSERT INTO parts (part_number, description) VALUES (%s, %s) ON CONFLICT (part_number) DO UPDATE SET description = EXCLUDED.description"
                db_config.execute_raw_sql(sql, (part_number, description))
                
                # Reload the database to update indexes
                self.load_parts_database()
                self._build_search_indexes()
                return True
            else:
                print("⚠️ Cannot add parts - not using PostgreSQL")
                return False
        except Exception as e:
            print(f"❌ Error adding part: {e}")
            return False
    
    def add_customer(self, account_number: str, company_name: str, address: str = "", state: str = "") -> bool:
        """Add a new customer to the database."""
        try:
            if db_config.is_postgres:
                sql = "INSERT INTO customers (customer_id, company_name, address, state_prov) VALUES (%s, %s, %s, %s) ON CONFLICT (customer_id) DO UPDATE SET company_name = EXCLUDED.company_name, address = EXCLUDED.address, state_prov = EXCLUDED.state_prov"
                db_config.execute_raw_sql(sql, (int(account_number), company_name, address, state))
                
                # Reload the database to update indexes
                self.load_customers_database()
                return True
            else:
                print("⚠️ Cannot add customers - not using PostgreSQL")
                return False
        except Exception as e:
            print(f"❌ Error adding customer: {e}")
            return False
    
    def get_parts_dataframe(self) -> pd.DataFrame:
        """Get the parts DataFrame."""
        return self.parts_df if self.parts_df is not None else pd.DataFrame()
    
    def get_customers_dataframe(self) -> pd.DataFrame:
        """Get the customers DataFrame."""
        return self.customers_df if self.customers_df is not None else pd.DataFrame()
