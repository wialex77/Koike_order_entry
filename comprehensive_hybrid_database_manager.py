"""
Comprehensive Hybrid Database Manager
Handles parts, customers, and processing results with PostgreSQL Transaction Pooler + REST API fallback.
"""

import os
import json
import socket
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
from dotenv import load_dotenv

# Import existing classes
from step5_metrics_db_postgres import ProcessingResult, ProcessingStatus, ValidationStatus, ErrorType

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

class ComprehensiveHybridDatabaseManager:
    """Comprehensive database manager with hybrid connection for all databases."""
    
    def __init__(self):
        """Initialize the comprehensive hybrid database manager."""
        self.use_postgres = True
        self.use_rest_api = False
        self.connection_method = "PostgreSQL Pooler"  # Track current connection method
        self.supabase_url = None
        self.api_key = None
        
        # Data storage - now loaded on demand
        self.parts_df = None
        self.customers_df = None
        self._parts_loaded = False
        self._customers_loaded = False
        
        # Search optimization indexes - now built on demand
        self.parts_by_exact_match = {}
        self.parts_by_keywords = defaultdict(list)
        self.description_words = {}
        
        # Load environment variables
        self._load_environment()
        
        # Try PostgreSQL first, fallback to REST API
        self._initialize_connection()
        
        # Don't load databases at startup - load on demand
        print("✅ Database manager initialized (lazy loading enabled)")
    
    def _load_environment(self):
        """Load environment variables from AWS environment variables."""
        # In AWS, environment variables are already set, no need to load from file
        # Locally, we'll comment this out for now since config.env doesn't exist in AWS
        # env_file = os.path.join(os.path.dirname(__file__), 'config.env')
        # if os.path.exists(env_file):
        #     load_dotenv(env_file)
        
        # Extract Supabase project info from AWS environment variables
        db_host = os.environ.get('DB_HOST', 'aws-1-us-east-2.pooler.supabase.co')
        if 'pooler.supabase.com' in db_host:
            project_ref = db_host.split('.')[0].replace('aws-1-us-east-2', 'lctdvwthxetczwyslibv')
        else:
            project_ref = db_host.replace('db.', '').replace('.supabase.co', '')
        
        self.supabase_url = f"https://{project_ref}.supabase.co"
        self.api_key = os.environ.get('SUPABASE_ANON_KEY')
    
    def _force_ipv4(self):
        """Force IPv4 connections by monkey-patching socket."""
        original_getaddrinfo = socket.getaddrinfo
        
        def getaddrinfo_ipv4(*args, **kwargs):
            responses = original_getaddrinfo(*args, **kwargs)
            return [response for response in responses if response[0] == socket.AF_INET]
        
        socket.getaddrinfo = getaddrinfo_ipv4
    
    def _initialize_connection(self):
        """Initialize connection, trying PostgreSQL first, then REST API."""
        print("🔍 Initializing comprehensive hybrid database connection...")
        
        # Try PostgreSQL Transaction Pooler first
        try:
            self._force_ipv4()
            os.environ['FLASK_ENV'] = 'production'
            
            from database_config import db_config
            
            # Test PostgreSQL connection
            test_sql = "SELECT 1 as test"
            result = db_config.execute_raw_sql_single(test_sql)
            
            if result:
                self.use_postgres = True
                self.use_rest_api = False
                self.connection_method = "PostgreSQL Pooler"
                print("✅ Using PostgreSQL Transaction Pooler (primary)")
                return
                
        except Exception as e:
            print(f"⚠️ PostgreSQL connection failed: {e}")
            self.connection_method = "REST API"
        
        # Fallback to REST API
        try:
            if not self.api_key:
                raise Exception("No Supabase API key found")
            
            # Test REST API connection
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(self.supabase_url, headers=headers, timeout=10)
            
            if response.status_code in [200, 404]:  # 404 is expected for root endpoint
                self.use_postgres = False
                self.use_rest_api = True
                self.connection_method = "REST API"
                print("✅ Using Supabase REST API (fallback)")
                return
                
        except Exception as e:
            print(f"❌ REST API connection failed: {e}")
        
        # If both fail
        self.use_postgres = False
        self.use_rest_api = False
        print("❌ Both PostgreSQL and REST API connections failed")
    
    def load_databases(self) -> None:
        """Load both parts and customers databases."""
        print("Loading parts and customers databases...")
        self.load_parts_database()
        self.load_customers_database()
        
        # Build search indexes after loading
        self._build_search_indexes()
        print(f"✅ Loaded {len(self.parts_df)} parts and {len(self.customers_df)} customers")
    
    def load_parts_database(self) -> None:
        """Load parts database."""
        try:
            if self.use_postgres:
                self._load_parts_postgres()
            elif self.use_rest_api:
                self._load_parts_rest_api()
            else:
                print("⚠️ No database connection available")
                self.parts_df = pd.DataFrame(columns=['internal_part_number', 'description'])
                
        except Exception as e:
            print(f"❌ Error loading parts: {e}")
            self.parts_df = pd.DataFrame(columns=['internal_part_number', 'description'])
    
    def _load_parts_postgres(self) -> None:
        """Load parts database using PostgreSQL."""
        from database_config import db_config
        
        sql = "SELECT part_number, description FROM parts ORDER BY part_number"
        results = db_config.execute_raw_sql(sql)
        
        # Convert to DataFrame
        parts_data = []
        for row in results:
            parts_data.append({
                'internal_part_number': row[0],
                'description': row[1]
            })
        
        self.parts_df = pd.DataFrame(parts_data)
        print(f"✅ Loaded {len(self.parts_df)} parts from PostgreSQL")
    
    def _load_parts_rest_api(self) -> None:
        """Load parts database using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        query_url = f"{self.supabase_url}/rest/v1/parts"
        params = {
            'select': 'part_number,description',
            'order': 'part_number'
        }
        
        response = requests.get(query_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            parts_data = []
            for record in data:
                parts_data.append({
                    'internal_part_number': record.get('part_number', ''),
                    'description': record.get('description', '')
                })
            
            self.parts_df = pd.DataFrame(parts_data)
            print(f"✅ Loaded {len(self.parts_df)} parts from REST API")
        else:
            print(f"❌ REST API parts query failed: {response.status_code}")
            self.parts_df = pd.DataFrame(columns=['internal_part_number', 'description'])
    
    def load_customers_database(self) -> None:
        """Load customers database."""
        try:
            if self.use_postgres:
                self._load_customers_postgres()
            elif self.use_rest_api:
                self._load_customers_rest_api()
            else:
                print("⚠️ No database connection available")
                self.customers_df = pd.DataFrame(columns=['account_number', 'company_name', 'address', 'state'])
                
        except Exception as e:
            print(f"❌ Error loading customers: {e}")
            self.customers_df = pd.DataFrame(columns=['account_number', 'company_name', 'address', 'state'])
    
    def _load_customers_postgres(self) -> None:
        """Load customers database using PostgreSQL."""
        from database_config import db_config
        
        sql = "SELECT customer_id, company_name, address, city, state_prov, postal_code, country FROM customers ORDER BY customer_id"
        results = db_config.execute_raw_sql(sql)
        
        # Convert to DataFrame
        customers_data = []
        for row in results:
            customers_data.append({
                'account_number': str(row[0]),
                'company_name': row[1],
                'address': row[2] or '',
                'state': row[4] or '',
                'city': row[3] or '',
                'postal_code': row[5] or '',
                'country': row[6] or ''
            })
        
        self.customers_df = pd.DataFrame(customers_data)
        print(f"✅ Loaded {len(self.customers_df)} customers from PostgreSQL")
    
    def _load_customers_rest_api(self) -> None:
        """Load customers database using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        query_url = f"{self.supabase_url}/rest/v1/customers"
        params = {
            'select': 'customer_id,company_name,address,city,state_prov,postal_code,country',
            'order': 'customer_id'
        }
        
        response = requests.get(query_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            customers_data = []
            for record in data:
                customers_data.append({
                    'account_number': str(record.get('customer_id', '')),
                    'company_name': record.get('company_name', ''),
                    'address': record.get('address', ''),
                    'state': record.get('state_prov', ''),
                    'city': record.get('city', ''),
                    'postal_code': record.get('postal_code', ''),
                    'country': record.get('country', '')
                })
            
            self.customers_df = pd.DataFrame(customers_data)
            print(f"✅ Loaded {len(self.customers_df)} customers from REST API")
        else:
            print(f"❌ REST API customers query failed: {response.status_code}")
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
    
    # Parts search methods - now using direct database queries
    def search_parts(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for parts using direct database queries."""
        if not query:
            return []
        
        query = query.strip()
        
        try:
            if self.use_postgres:
                return self._search_parts_postgres(query, limit)
            elif self.use_rest_api:
                return self._search_parts_rest_api(query, limit)
            else:
                print("❌ No database connection available for search")
                return []
        except Exception as e:
            print(f"❌ Error searching parts: {e}")
            return []
    
    def _search_parts_postgres(self, query: str, limit: int) -> List[Dict]:
        """Search parts using PostgreSQL with optimized queries."""
        from database_config import db_config
        
        # First try exact match
        exact_sql = """
            SELECT internal_part_number, description 
            FROM parts 
            WHERE UPPER(internal_part_number) = :query
            LIMIT 1
        """
        exact_results = db_config.execute_raw_sql(exact_sql, {'query': query.upper()})
        
        results = []
        if exact_results:
            results.append({
                'internal_part_number': exact_results[0][0],
                'description': exact_results[0][1],
                'match_type': 'exact',
                'score': 1.0
            })
        
        # If we need more results, do fuzzy search
        if len(results) < limit:
            fuzzy_sql = """
                SELECT internal_part_number, description,
                       CASE 
                           WHEN UPPER(internal_part_number) LIKE :query_start THEN 0.9
                           WHEN UPPER(internal_part_number) LIKE :query_contains THEN 0.7
                           WHEN UPPER(description) LIKE :query_start THEN 0.6
                           WHEN UPPER(description) LIKE :query_contains THEN 0.4
                           ELSE 0.3
                       END as score
                FROM parts 
                WHERE UPPER(internal_part_number) LIKE :query_contains 
                   OR UPPER(description) LIKE :query_contains
                ORDER BY score DESC, internal_part_number
                LIMIT :limit
            """
            
            fuzzy_results = db_config.execute_raw_sql(fuzzy_sql, {
                'query_start': f'{query.upper()}%',
                'query_contains': f'%{query.upper()}%',
                'limit': limit
            })
            
            for row in fuzzy_results:
                if len(results) >= limit:
                    break
                results.append({
                    'internal_part_number': row[0],
                    'description': row[1],
                    'match_type': 'fuzzy',
                    'score': float(row[2])
                })
        
        return results
    
    def _search_parts_rest_api(self, query: str, limit: int) -> List[Dict]:
        """Search parts using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Try exact match first
        exact_url = f"{self.supabase_url}/rest/v1/parts"
        exact_params = {
            'select': 'internal_part_number,description',
            'internal_part_number': f'eq.{query.upper()}',
            'limit': '1'
        }
        
        exact_response = requests.get(exact_url, headers=headers, params=exact_params, timeout=30)
        results = []
        
        if exact_response.status_code == 200:
            exact_data = exact_response.json()
            if exact_data:
                results.append({
                    'internal_part_number': exact_data[0]['internal_part_number'],
                    'description': exact_data[0]['description'],
                    'match_type': 'exact',
                    'score': 1.0
                })
        
        # If we need more results, do fuzzy search
        if len(results) < limit:
            fuzzy_url = f"{self.supabase_url}/rest/v1/parts"
            fuzzy_params = {
                'select': 'internal_part_number,description',
                'or': f'internal_part_number.ilike.%{query}%,description.ilike.%{query}%',
                'limit': str(limit)
            }
            
            fuzzy_response = requests.get(fuzzy_url, headers=headers, params=fuzzy_params, timeout=30)
            
            if fuzzy_response.status_code == 200:
                fuzzy_data = fuzzy_response.json()
                for item in fuzzy_data:
                    if len(results) >= limit:
                        break
                    results.append({
                        'internal_part_number': item['internal_part_number'],
                        'description': item['description'],
                        'match_type': 'fuzzy',
                        'score': 0.5  # Default score for REST API
                    })
        
        return results
    
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
        """Search for customers using direct database queries."""
        if not query:
            return []
        
        query = query.strip()
        
        try:
            if self.use_postgres:
                return self._search_customers_postgres(query, limit)
            elif self.use_rest_api:
                return self._search_customers_rest_api(query, limit)
            else:
                print("❌ No database connection available for customer search")
                return []
        except Exception as e:
            print(f"❌ Error searching customers: {e}")
            return []
    
    def _search_customers_postgres(self, query: str, limit: int) -> List[Dict]:
        """Search customers using PostgreSQL with optimized queries."""
        from database_config import db_config
        
        sql = """
            SELECT account_number, company_name, address, city, state_prov, postal_code, country,
                   CASE 
                       WHEN UPPER(company_name) LIKE :query_start THEN 0.9
                       WHEN UPPER(company_name) LIKE :query_contains THEN 0.7
                       WHEN UPPER(address) LIKE :query_start THEN 0.6
                       WHEN UPPER(address) LIKE :query_contains THEN 0.4
                       WHEN UPPER(city) LIKE :query_start THEN 0.5
                       WHEN UPPER(city) LIKE :query_contains THEN 0.3
                       ELSE 0.2
                   END as score
            FROM customers 
            WHERE UPPER(company_name) LIKE :query_contains 
               OR UPPER(address) LIKE :query_contains
               OR UPPER(city) LIKE :query_contains
            ORDER BY score DESC, company_name
            LIMIT :limit
        """
        
        results = db_config.execute_raw_sql(sql, {
            'query_start': f'{query.upper()}%',
            'query_contains': f'%{query.upper()}%',
            'limit': limit
        })
        
        return [{
            'account_number': row[0],
            'company_name': row[1],
            'address': row[2],
            'city': row[3],
            'state': row[4],
            'postal_code': row[5],
            'country': row[6],
            'score': float(row[7])
        } for row in results]
    
    def _search_customers_rest_api(self, query: str, limit: int) -> List[Dict]:
        """Search customers using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.supabase_url}/rest/v1/customers"
        params = {
            'select': 'account_number,company_name,address,city,state_prov,postal_code,country',
            'or': f'company_name.ilike.%{query}%,address.ilike.%{query}%,city.ilike.%{query}%',
            'limit': str(limit)
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return [{
                'account_number': item['account_number'],
                'company_name': item['company_name'],
                'address': item['address'],
                'city': item['city'],
                'state': item['state_prov'],
                'postal_code': item['postal_code'],
                'country': item['country'],
                'score': 0.5  # Default score for REST API
            } for item in data]
        
        return []
    
    def get_part_by_number(self, part_number: str) -> Optional[Dict]:
        """Get a specific part by its number using direct database query."""
        if not part_number:
            return None
        
        part_number = part_number.strip()
        
        try:
            if self.use_postgres:
                return self._get_part_by_number_postgres(part_number)
            elif self.use_rest_api:
                return self._get_part_by_number_rest_api(part_number)
            else:
                print("❌ No database connection available")
                return None
        except Exception as e:
            print(f"❌ Error getting part by number: {e}")
            return None
    
    def _get_part_by_number_postgres(self, part_number: str) -> Optional[Dict]:
        """Get part by number using PostgreSQL."""
        from database_config import db_config
        
        sql = """
            SELECT internal_part_number, description 
            FROM parts 
            WHERE UPPER(internal_part_number) = :part_number
            LIMIT 1
        """
        
        result = db_config.execute_raw_sql_single(sql, {'part_number': part_number.upper()})
        
        if result:
            return {
                'internal_part_number': result[0],
                'description': result[1]
            }
        return None
    
    def _get_part_by_number_rest_api(self, part_number: str) -> Optional[Dict]:
        """Get part by number using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.supabase_url}/rest/v1/parts"
        params = {
            'select': 'internal_part_number,description',
            'internal_part_number': f'eq.{part_number.upper()}',
            'limit': '1'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                return {
                    'internal_part_number': data[0]['internal_part_number'],
                    'description': data[0]['description']
                }
        return None
    
    def get_customer_by_account(self, account_number: str) -> Optional[Dict]:
        """Get a specific customer by account number using direct database query."""
        if not account_number:
            return None
        
        account_number = str(account_number).strip()
        
        try:
            if self.use_postgres:
                return self._get_customer_by_account_postgres(account_number)
            elif self.use_rest_api:
                return self._get_customer_by_account_rest_api(account_number)
            else:
                print("❌ No database connection available")
                return None
        except Exception as e:
            print(f"❌ Error getting customer by account: {e}")
            return None
    
    def _get_customer_by_account_postgres(self, account_number: str) -> Optional[Dict]:
        """Get customer by account number using PostgreSQL."""
        from database_config import db_config
        
        sql = """
            SELECT account_number, company_name, address, city, state_prov, postal_code, country
            FROM customers 
            WHERE account_number = :account_number
            LIMIT 1
        """
        
        result = db_config.execute_raw_sql_single(sql, {'account_number': account_number})
        
        if result:
            return {
                'account_number': result[0],
                'company_name': result[1],
                'address': result[2],
                'city': result[3],
                'state': result[4],
                'postal_code': result[5],
                'country': result[6]
            }
        return None
    
    def _get_customer_by_account_rest_api(self, account_number: str) -> Optional[Dict]:
        """Get customer by account number using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.supabase_url}/rest/v1/customers"
        params = {
            'select': 'account_number,company_name,address,city,state_prov,postal_code,country',
            'account_number': f'eq.{account_number}',
            'limit': '1'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                return {
                    'account_number': data[0]['account_number'],
                    'company_name': data[0]['company_name'],
                    'address': data[0]['address'],
                    'city': data[0]['city'],
                    'state': data[0]['state_prov'],
                    'postal_code': data[0]['postal_code'],
                    'country': data[0]['country']
                }
        return None
    
    # Processing results methods (same as HybridDatabaseManager)
    def get_processing_results(self, limit: int = 100) -> List[ProcessingResult]:
        """Get recent processing results."""
        if self.use_postgres:
            return self._get_processing_results_postgres(limit)
        elif self.use_rest_api:
            return self._get_processing_results_rest_api(limit)
        else:
            print("❌ No database connection available")
            return []
    
    def _get_processing_results_postgres(self, limit: int) -> List[ProcessingResult]:
        """Get processing results using PostgreSQL."""
        try:
            from database_config import db_config
            
            sql = '''
                SELECT * FROM processing_results 
                ORDER BY created_at DESC 
                LIMIT %s
            '''
            
            rows = db_config.execute_raw_sql(sql, (limit,))
            
            results = []
            for row in rows:
                # Convert row to ProcessingResult object
                error_types = [ErrorType(e) for e in json.loads(row[17] or '[]')]
                
                result = ProcessingResult(
                    id=row[0],
                    filename=row[1],
                    original_filename=row[2],
                    file_size=row[3],
                    processing_status=ProcessingStatus(row[4]),
                    validation_status=ValidationStatus(row[5]),
                    processing_start_time=row[6],
                    processing_end_time=row[7],
                    processing_duration=row[8],
                    total_parts=row[9] or 0,
                    parts_mapped=row[10] or 0,
                    parts_not_found=row[11] or 0,
                    parts_manual_review=row[12] or 0,
                    mapping_success_rate=row[13] or 0.0,
                    customer_matched=row[14] or False,
                    customer_match_confidence=row[15] or 0.0,
                    error_types=error_types,
                    error_details=row[16] or '',
                    manual_corrections_made=row[18] or 0,
                    epicor_ready=row[19] or False,
                    epicor_ready_with_one_click=row[20] or False,
                    missing_info_count=row[21] or 0,
                    processed_file_path=row[22] or '',
                    epicor_json_path=row[23],
                    raw_json_data=row[24] or '',
                    notes=row[25] or '',
                    created_at=row[26],
                    updated_at=row[27]
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Error getting processing results from PostgreSQL: {e}")
            return []
    
    def _get_processing_results_rest_api(self, limit: int) -> List[ProcessingResult]:
        """Get processing results using REST API."""
        try:
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            query_url = f"{self.supabase_url}/rest/v1/processing_results"
            params = {
                'select': '*',
                'limit': str(limit),
                'order': 'created_at.desc'
            }
            
            response = requests.get(query_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                results = []
                for record in data:
                    # Convert REST API record to ProcessingResult object
                    error_types = [ErrorType(e) for e in json.loads(record.get('error_types', '[]'))]
                    
                    result = ProcessingResult(
                        id=record.get('id'),
                        filename=record.get('filename', ''),
                        original_filename=record.get('original_filename', ''),
                        file_size=record.get('file_size', 0),
                        processing_status=ProcessingStatus(record.get('processing_status', 'pending')),
                        validation_status=ValidationStatus(record.get('validation_status', 'pending_review')),
                        processing_start_time=datetime.fromisoformat(record.get('processing_start_time', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('processing_start_time') else None,
                        processing_end_time=datetime.fromisoformat(record.get('processing_end_time', '').replace('Z', '+00:00')) if record.get('processing_end_time') else None,
                        processing_duration=record.get('processing_duration'),
                        total_parts=record.get('total_parts', 0),
                        parts_mapped=record.get('parts_mapped', 0),
                        parts_not_found=record.get('parts_not_found', 0),
                        parts_manual_review=record.get('parts_manual_review', 0),
                        mapping_success_rate=record.get('mapping_success_rate', 0.0),
                        customer_matched=record.get('customer_matched', False),
                        customer_match_confidence=record.get('customer_match_confidence', 0.0),
                        error_types=error_types,
                        error_details=record.get('error_details', ''),
                        manual_corrections_made=record.get('manual_corrections_made', 0),
                        epicor_ready=record.get('epicor_ready', False),
                        epicor_ready_with_one_click=record.get('epicor_ready_with_one_click', False),
                        missing_info_count=record.get('missing_info_count', 0),
                        processed_file_path=record.get('processed_file_path', ''),
                        epicor_json_path=record.get('epicor_json_path'),
                        raw_json_data=record.get('raw_json_data', ''),
                        notes=record.get('notes', ''),
                        created_at=datetime.fromisoformat(record.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('created_at') else None,
                        updated_at=datetime.fromisoformat(record.get('updated_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('updated_at') else None
                    )
                    results.append(result)
                
                return results
            else:
                print(f"❌ REST API query failed with status: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting processing results from REST API: {e}")
            return []
    
    def save_processing_result(self, result: ProcessingResult) -> int:
        """Save a processing result."""
        if self.use_postgres:
            return self._save_processing_result_postgres(result)
        elif self.use_rest_api:
            return self._save_processing_result_rest_api(result)
        else:
            print("❌ No database connection available")
            return None
    
    def _save_processing_result_postgres(self, result: ProcessingResult) -> int:
        """Save processing result using PostgreSQL."""
        try:
            from database_config import db_config
            
            # Convert enum lists to JSON strings
            error_types_json = json.dumps([e.value for e in result.error_types])
            
            # Prepare data for insertion
            data = {
                'filename': result.filename,
                'original_filename': result.original_filename,
                'file_size': result.file_size,
                'processing_status': result.processing_status.value,
                'validation_status': result.validation_status.value,
                'processing_start_time': result.processing_start_time,
                'processing_end_time': result.processing_end_time,
                'processing_duration': result.processing_duration,
                'total_parts': result.total_parts,
                'parts_mapped': result.parts_mapped,
                'parts_not_found': result.parts_not_found,
                'parts_manual_review': result.parts_manual_review,
                'mapping_success_rate': result.mapping_success_rate,
                'customer_matched': result.customer_matched,
                'customer_match_confidence': result.customer_match_confidence,
                'error_types': error_types_json,
                'error_details': result.error_details,
                'manual_corrections_made': result.manual_corrections_made,
                'epicor_ready': result.epicor_ready,
                'epicor_ready_with_one_click': result.epicor_ready_with_one_click,
                'missing_info_count': result.missing_info_count,
                'processed_file_path': result.processed_file_path,
                'epicor_json_path': result.epicor_json_path,
                'raw_json_data': result.raw_json_data,
                'notes': result.notes,
                'created_at': result.created_at,
                'updated_at': result.updated_at
            }
            
            # Build INSERT query
            if result.id is None:
                # New record
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['%s' for _ in data.keys()])
                
                sql = f'''
                    INSERT INTO processing_results ({columns})
                    VALUES ({placeholders})
                    RETURNING id
                '''
                values = [data[key] for key in data.keys()]
                result_id = db_config.execute_raw_sql_single(sql, values)[0]
            else:
                # Update existing record
                set_clause = ', '.join([f'{key} = %s' for key in data.keys() if key != 'id'])
                sql = f'''
                    UPDATE processing_results 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                '''
                data['id'] = result.id
                values = [data[key] for key in data.keys()]
                db_config.execute_raw_sql(sql, values)
                result_id = result.id
            
            return result_id
            
        except Exception as e:
            print(f"❌ Error saving processing result to PostgreSQL: {e}")
            return None
    
    def _save_processing_result_rest_api(self, result: ProcessingResult) -> int:
        """Save processing result using REST API."""
        try:
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Prepare data for REST API
            data = {
                'filename': result.filename,
                'original_filename': result.original_filename,
                'file_size': result.file_size,
                'processing_status': result.processing_status.value,
                'validation_status': result.validation_status.value,
                'processing_start_time': result.processing_start_time.isoformat() if result.processing_start_time else None,
                'processing_end_time': result.processing_end_time.isoformat() if result.processing_end_time else None,
                'processing_duration': result.processing_duration,
                'total_parts': result.total_parts,
                'parts_mapped': result.parts_mapped,
                'parts_not_found': result.parts_not_found,
                'parts_manual_review': result.parts_manual_review,
                'mapping_success_rate': result.mapping_success_rate,
                'customer_matched': result.customer_matched,
                'customer_match_confidence': result.customer_match_confidence,
                'error_types': json.dumps([e.value for e in result.error_types]),
                'error_details': result.error_details,
                'manual_corrections_made': result.manual_corrections_made,
                'epicor_ready': result.epicor_ready,
                'epicor_ready_with_one_click': result.epicor_ready_with_one_click,
                'missing_info_count': result.missing_info_count,
                'processed_file_path': result.processed_file_path,
                'epicor_json_path': result.epicor_json_path,
                'raw_json_data': result.raw_json_data,
                'notes': result.notes,
                'created_at': result.created_at.isoformat() if result.created_at else None,
                'updated_at': result.updated_at.isoformat() if result.updated_at else None
            }
            
            # Insert or update
            if result.id is None:
                # New record
                insert_url = f"{self.supabase_url}/rest/v1/processing_results"
                response = requests.post(insert_url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 201:
                    inserted_data = response.json()
                    return inserted_data[0]['id'] if inserted_data else None
                else:
                    print(f"❌ REST API insert failed with status: {response.status_code}")
                    return None
            else:
                # Update existing record
                update_url = f"{self.supabase_url}/rest/v1/processing_results"
                params = {'id': f'eq.{result.id}'}
                response = requests.patch(update_url, headers=headers, json=data, params=params, timeout=30)
                
                if response.status_code == 200:
                    return result.id
                else:
                    print(f"❌ REST API update failed with status: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error saving processing result to REST API: {e}")
            return None
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics."""
        if self.use_postgres:
            return self._get_dashboard_metrics_postgres()
        elif self.use_rest_api:
            return self._get_dashboard_metrics_rest_api()
        else:
            return {
                'total_files': 0,
                'successful_files': 0,
                'success_rate': 0,
                'avg_processing_time': 0
            }
    
    def _get_dashboard_metrics_postgres(self) -> Dict[str, Any]:
        """Get dashboard metrics using PostgreSQL."""
        try:
            from database_config import db_config
            
            # Get total files processed
            total_files_sql = "SELECT COUNT(*) FROM processing_results"
            total_files = db_config.execute_raw_sql_single(total_files_sql)[0] or 0
            
            # Get success rate
            success_sql = "SELECT COUNT(*) FROM processing_results WHERE processing_status = 'completed'"
            successful_files = db_config.execute_raw_sql_single(success_sql)[0] or 0
            success_rate = (successful_files / total_files * 100) if total_files > 0 else 0
            
            # Get average processing time
            avg_time_sql = '''
                SELECT AVG(processing_duration) 
                FROM processing_results 
                WHERE processing_duration IS NOT NULL
            '''
            avg_processing_time = db_config.execute_raw_sql_single(avg_time_sql)[0] or 0
            
            return {
                'total_files': total_files,
                'successful_files': successful_files,
                'success_rate': round(success_rate, 2),
                'avg_processing_time': round(avg_processing_time, 2) if avg_processing_time else 0
            }
            
        except Exception as e:
            print(f"❌ Error getting dashboard metrics from PostgreSQL: {e}")
            return {
                'total_files': 0,
                'successful_files': 0,
                'success_rate': 0,
                'avg_processing_time': 0
            }
    
    def _get_dashboard_metrics_rest_api(self) -> Dict[str, Any]:
        """Get dashboard metrics using REST API."""
        try:
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get all records to calculate metrics
            query_url = f"{self.supabase_url}/rest/v1/processing_results"
            params = {'select': 'processing_status,processing_duration'}
            
            response = requests.get(query_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                total_files = len(data)
                successful_files = len([r for r in data if r.get('processing_status') == 'completed'])
                success_rate = (successful_files / total_files * 100) if total_files > 0 else 0
                
                durations = [r.get('processing_duration') for r in data if r.get('processing_duration') is not None]
                avg_processing_time = sum(durations) / len(durations) if durations else 0
                
                return {
                    'total_files': total_files,
                    'successful_files': successful_files,
                    'success_rate': round(success_rate, 2),
                    'avg_processing_time': round(avg_processing_time, 2)
                }
            else:
                print(f"❌ REST API metrics query failed with status: {response.status_code}")
                return {
                    'total_files': 0,
                    'successful_files': 0,
                    'success_rate': 0,
                    'avg_processing_time': 0
                }
                
        except Exception as e:
            print(f"❌ Error getting dashboard metrics from REST API: {e}")
            return {
                'total_files': 0,
                'successful_files': 0,
                'success_rate': 0,
                'avg_processing_time': 0
            }
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            'using_postgres': self.use_postgres,
            'using_rest_api': self.use_rest_api,
            'connection_method': 'PostgreSQL Transaction Pooler' if self.use_postgres else 'REST API' if self.use_rest_api else 'None',
            'supabase_url': self.supabase_url,
            'has_api_key': bool(self.api_key),
            'parts_loaded': len(self.parts_df) if self.parts_df is not None else 0,
            'customers_loaded': len(self.customers_df) if self.customers_df is not None else 0
        }
    
    # Additional methods from MetricsDatabase for full compatibility
    def create_processing_result(self, filename: str, original_filename: str, file_size: int, 
                                processing_status: ProcessingStatus, validation_status: ValidationStatus,
                                processing_start_time: datetime, processed_file_path: str, 
                                raw_json_data: str, notes: str = "") -> int:
        """Create a new processing result."""
        print(f"🔍 Creating processing result - using {self.connection_method}")
        try:
            if self.use_postgres:
                return self._create_processing_result_postgres(filename, original_filename, file_size, 
                                                             processing_status, validation_status, 
                                                             processing_start_time, processed_file_path, 
                                                             raw_json_data, notes)
            elif self.use_rest_api:
                return self._create_processing_result_rest_api(filename, original_filename, file_size, 
                                                              processing_status, validation_status, 
                                                              processing_start_time, processed_file_path, 
                                                              raw_json_data, notes)
            else:
                print("❌ No database connection available")
                return 0
        except Exception as e:
            print(f"❌ Error creating processing result: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _create_processing_result_postgres(self, filename: str, original_filename: str, file_size: int, 
                                          processing_status: ProcessingStatus, validation_status: ValidationStatus,
                                          processing_start_time: datetime, processed_file_path: str, 
                                          raw_json_data: str, notes: str = "") -> int:
        """Create processing result using PostgreSQL."""
        from database_config import db_config
        
        sql = '''
            INSERT INTO processing_results (
                filename, original_filename, file_size, processing_status, validation_status,
                processing_start_time, processed_file_path, raw_json_data, notes, created_at, updated_at
            ) VALUES (:filename, :original_filename, :file_size, :processing_status, :validation_status,
                     :processing_start_time, :processed_file_path, :raw_json_data, :notes, :created_at, :updated_at)
            RETURNING id
        '''
        
        now = datetime.utcnow()
        params = {
            'filename': filename,
            'original_filename': original_filename,
            'file_size': file_size,
            'processing_status': processing_status.value,
            'validation_status': validation_status.value,
            'processing_start_time': processing_start_time,
            'processed_file_path': processed_file_path,
            'raw_json_data': raw_json_data,
            'notes': notes,
            'created_at': now,
            'updated_at': now
        }
        result = db_config.execute_raw_sql_single(sql, params)
        
        return result[0] if result else 0
    
    def _create_processing_result_rest_api(self, filename: str, original_filename: str, file_size: int, 
                                          processing_status: ProcessingStatus, validation_status: ValidationStatus,
                                          processing_start_time: datetime, processed_file_path: str, 
                                          raw_json_data: str, notes: str = "") -> int:
        """Create processing result using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'filename': filename,
            'original_filename': original_filename,
            'file_size': file_size,
            'processing_status': processing_status.value,
            'validation_status': validation_status.value,
            'processing_start_time': processing_start_time.isoformat(),
            'processed_file_path': processed_file_path,
            'raw_json_data': raw_json_data,
            'notes': notes,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        insert_url = f"{self.supabase_url}/rest/v1/processing_results"
        response = requests.post(insert_url, headers=headers, json=data, timeout=30)
        
        
        if response.status_code == 201:
            # Supabase REST API returns empty response on successful insert
            # We need to query the inserted record to get the ID
            try:
                # Query the most recent record with this filename to get the ID
                query_url = f"{self.supabase_url}/rest/v1/processing_results"
                params = {
                    'select': 'id',
                    'filename': f'eq.{filename}',
                    'order': 'created_at.desc',
                    'limit': '1'
                }
                
                query_response = requests.get(query_url, headers=headers, params=params, timeout=30)
                if query_response.status_code == 200:
                    query_data = query_response.json()
                    if query_data:
                        return query_data[0]['id']
                
                # Fallback: return a dummy ID if we can't get the real one
                return 999999
            except Exception as e:
                print(f"❌ Failed to get inserted record ID: {e}")
                return 999999
        else:
            print(f"❌ REST API create failed with status: {response.status_code}")
            return 0
    
    def update_processing_result(self, result_id: int, **kwargs) -> bool:
        """Update a processing result."""
        try:
            if not kwargs:
                return True
            
            if self.use_postgres:
                return self._update_processing_result_postgres(result_id, **kwargs)
            elif self.use_rest_api:
                return self._update_processing_result_rest_api(result_id, **kwargs)
            else:
                print("❌ No database connection available")
                return False
        except Exception as e:
            print(f"❌ Error updating processing result: {e}")
            return False
    
    def _update_processing_result_postgres(self, result_id: int, **kwargs) -> bool:
        """Update processing result using PostgreSQL."""
        from database_config import db_config
        
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if key == 'error_types' and isinstance(value, list):
                value = json.dumps([e.value if hasattr(e, 'value') else e for e in value])
            elif hasattr(value, 'value'):  # Enum
                value = value.value
            elif isinstance(value, datetime):
                value = value.isoformat()
                
            set_clauses.append(f"{key} = %s")
            values.append(value)
        
        if not set_clauses:
            return True
            
        set_clauses.append("updated_at = %s")
        values.append(datetime.utcnow())
        values.append(result_id)
        
        # Convert to named parameters
        set_clauses_named = []
        for i, clause in enumerate(set_clauses):
            param_name = f"param_{i}"
            set_clauses_named.append(f"{clause.split(' = ')[0]} = :{param_name}")
        
        sql = f'''
            UPDATE processing_results 
            SET {', '.join(set_clauses_named)}
            WHERE id = :result_id
        '''
        
        # Create named parameters dict
        params = {}
        for i, value in enumerate(values[:-1]):  # Exclude the last value (result_id)
            params[f"param_{i}"] = value
        params['result_id'] = values[-1]
        
        db_config.execute_raw_sql(sql, params)
        return True
    
    def _update_processing_result_rest_api(self, result_id: int, **kwargs) -> bool:
        """Update processing result using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Prepare data for REST API
        data = {}
        for key, value in kwargs.items():
            if key == 'error_types' and isinstance(value, list):
                data[key] = json.dumps([e.value if hasattr(e, 'value') else e for e in value])
            elif hasattr(value, 'value'):  # Enum
                data[key] = value.value
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
            else:
                data[key] = value
        
        data['updated_at'] = datetime.utcnow().isoformat()
        
        update_url = f"{self.supabase_url}/rest/v1/processing_results"
        params = {'id': f'eq.{result_id}'}
        response = requests.patch(update_url, headers=headers, json=data, params=params, timeout=30)
        
        
        return response.status_code in [200, 204]  # 204 is No Content, which is success for PATCH
    
    def get_processing_result(self, result_id: int) -> Optional[ProcessingResult]:
        """Get a processing result by ID."""
        try:
            if self.use_postgres:
                return self._get_processing_result_postgres(result_id)
            elif self.use_rest_api:
                return self._get_processing_result_rest_api(result_id)
            else:
                print("❌ No database connection available")
                return None
        except Exception as e:
            print(f"❌ Error getting processing result: {e}")
            return None
    
    def _get_processing_result_postgres(self, result_id: int) -> Optional[ProcessingResult]:
        """Get processing result by ID using PostgreSQL."""
        from database_config import db_config
        
        sql = """
            SELECT id, filename, original_filename, file_size, processing_status, 
                   validation_status, processing_start_time, processing_end_time, 
                   processing_duration, total_parts, parts_mapped, parts_not_found, 
                   parts_manual_review, mapping_success_rate, customer_matched, 
                   customer_match_confidence, error_details, error_types, 
                   manual_corrections_made, epicor_ready, epicor_ready_with_one_click, 
                   missing_info_count, processed_file_path, epicor_json_path, 
                   raw_json_data, notes, created_at, updated_at
            FROM processing_results WHERE id = :result_id
        """
        row = db_config.execute_raw_sql_single(sql, {'result_id': result_id})
        
        if row:
            # Parse error_types JSON safely
            try:
                error_types = [ErrorType(e) for e in json.loads(row[17] or '[]')]
            except (json.JSONDecodeError, ValueError):
                error_types = []
            
            return ProcessingResult(
                id=row[0],
                filename=row[1],
                original_filename=row[2],
                file_size=row[3],
                processing_status=ProcessingStatus(row[4]),
                validation_status=ValidationStatus(row[5]),
                processing_start_time=row[6],
                processing_end_time=row[7],
                processing_duration=row[8],
                total_parts=row[9] or 0,
                parts_mapped=row[10] or 0,
                parts_not_found=row[11] or 0,
                parts_manual_review=row[12] or 0,
                mapping_success_rate=row[13] or 0.0,
                customer_matched=row[14] or False,
                customer_match_confidence=row[15] or 0.0,
                error_types=error_types,
                error_details=row[16] or '',
                manual_corrections_made=row[18] or 0,
                epicor_ready=row[19] or False,
                epicor_ready_with_one_click=row[20] or False,
                missing_info_count=row[21] or 0,
                processed_file_path=row[22] or '',
                epicor_json_path=row[23],
                raw_json_data=row[24] or '',
                notes=row[25] or '',
                created_at=row[26],
                updated_at=row[27]
            )
        return None
    
    def _get_processing_result_rest_api(self, result_id: int) -> Optional[ProcessingResult]:
        """Get processing result by ID using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        query_url = f"{self.supabase_url}/rest/v1/processing_results"
        params = {
            'select': '*',
            'id': f'eq.{result_id}'
        }
        
        response = requests.get(query_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                record = data[0]
                # Convert REST API record to ProcessingResult object
                error_types = [ErrorType(e) for e in json.loads(record.get('error_types', '[]'))]
                
                return ProcessingResult(
                    id=record.get('id'),
                    filename=record.get('filename', ''),
                    original_filename=record.get('original_filename', ''),
                    file_size=record.get('file_size', 0),
                    processing_status=ProcessingStatus(record.get('processing_status', 'pending')),
                    validation_status=ValidationStatus(record.get('validation_status', 'pending_review')),
                    processing_start_time=datetime.fromisoformat(record.get('processing_start_time', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('processing_start_time') else None,
                    processing_end_time=datetime.fromisoformat(record.get('processing_end_time', '').replace('Z', '+00:00')) if record.get('processing_end_time') else None,
                    processing_duration=record.get('processing_duration'),
                    total_parts=record.get('total_parts', 0),
                    parts_mapped=record.get('parts_mapped', 0),
                    parts_not_found=record.get('parts_not_found', 0),
                    parts_manual_review=record.get('parts_manual_review', 0),
                    mapping_success_rate=record.get('mapping_success_rate', 0.0),
                    customer_matched=record.get('customer_matched', False),
                    customer_match_confidence=record.get('customer_match_confidence', 0.0),
                    error_types=error_types,
                    error_details=record.get('error_details', ''),
                    manual_corrections_made=record.get('manual_corrections_made', 0),
                    epicor_ready=record.get('epicor_ready', False),
                    epicor_ready_with_one_click=record.get('epicor_ready_with_one_click', False),
                    missing_info_count=record.get('missing_info_count', 0),
                    processed_file_path=record.get('processed_file_path', ''),
                    epicor_json_path=record.get('epicor_json_path'),
                    raw_json_data=record.get('raw_json_data', ''),
                    notes=record.get('notes', ''),
                    created_at=datetime.fromisoformat(record.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('created_at') else None,
                    updated_at=datetime.fromisoformat(record.get('updated_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('updated_at') else None
                )
        return None
    
    def delete_processing_result(self, result_id: int) -> bool:
        """Delete a processing result."""
        try:
            if self.use_postgres:
                return self._delete_processing_result_postgres(result_id)
            elif self.use_rest_api:
                return self._delete_processing_result_rest_api(result_id)
            else:
                print("❌ No database connection available")
                return False
        except Exception as e:
            print(f"❌ Error deleting processing result: {e}")
            return False
    
    def _delete_processing_result_postgres(self, result_id: int) -> bool:
        """Delete processing result using PostgreSQL."""
        from database_config import db_config
        
        sql = "DELETE FROM processing_results WHERE id = :result_id"
        db_config.execute_raw_sql(sql, {'result_id': result_id})
        return True
    
    def _delete_processing_result_rest_api(self, result_id: int) -> bool:
        """Delete processing result using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        delete_url = f"{self.supabase_url}/rest/v1/processing_results"
        params = {'id': f'eq.{result_id}'}
        response = requests.delete(delete_url, headers=headers, params=params, timeout=30)
        
        return response.status_code in [200, 204]  # 204 is No Content, which is success for DELETE
    
    def mark_as_correct(self, result_id: int) -> bool:
        """Mark a processing result as correct."""
        return self.update_processing_result(result_id, validation_status=ValidationStatus.CORRECT)
    
    def mark_as_contains_error(self, result_id: int, error_types: List[ErrorType], error_details: str = "") -> bool:
        """Mark a processing result as containing errors."""
        return self.update_processing_result(
            result_id, 
            validation_status=ValidationStatus.CONTAINS_ERROR,
            error_types=error_types,
            error_details=error_details
        )
    
    def update_raw_json_data(self, file_id: int, raw_json_data: str) -> bool:
        """Update raw JSON data for a file."""
        return self.update_processing_result(file_id, raw_json_data=raw_json_data)
    
    def update_validation_status(self, file_id: int, validation_status: str) -> bool:
        """Update validation status for a file."""
        return self.update_processing_result(file_id, validation_status=validation_status)
    
    def add_error_type(self, file_id: int, error_type: ErrorType) -> bool:
        """Add an error type to a file."""
        try:
            # Get current error types
            result = self.get_processing_result(file_id)
            if not result:
                return False
                
            current_errors = result.error_types
            if error_type not in current_errors:
                current_errors.append(error_type)
                
            return self.update_processing_result(file_id, error_types=current_errors)
            
        except Exception as e:
            print(f"❌ Error adding error type: {e}")
            return False
    
    def get_all_processing_results(self, limit: int = 100, offset: int = 0) -> List[ProcessingResult]:
        """Get all processing results with pagination."""
        try:
            if self.use_postgres:
                return self._get_all_processing_results_postgres(limit, offset)
            elif self.use_rest_api:
                return self._get_all_processing_results_rest_api(limit, offset)
            else:
                print("❌ No database connection available")
                return []
        except Exception as e:
            print(f"❌ Error getting all processing results: {e}")
            return []
    
    def _get_all_processing_results_postgres(self, limit: int, offset: int) -> List[ProcessingResult]:
        """Get all processing results using PostgreSQL."""
        from database_config import db_config
        
        sql = '''
            SELECT * FROM processing_results 
            ORDER BY created_at DESC 
            LIMIT :limit OFFSET :offset
        '''
        
        rows = db_config.execute_raw_sql(sql, {'limit': limit, 'offset': offset})
        
        results = []
        for row in rows:
            # Convert row to ProcessingResult object
            error_types = [ErrorType(e) for e in json.loads(row[17] or '[]')]
            
            result = ProcessingResult(
                id=row[0],
                filename=row[1],
                original_filename=row[2],
                file_size=row[3],
                processing_status=ProcessingStatus(row[4]),
                validation_status=ValidationStatus(row[5]),
                processing_start_time=row[6],
                processing_end_time=row[7],
                processing_duration=row[8],
                total_parts=row[9] or 0,
                parts_mapped=row[10] or 0,
                parts_not_found=row[11] or 0,
                parts_manual_review=row[12] or 0,
                mapping_success_rate=row[13] or 0.0,
                customer_matched=row[14] or False,
                customer_match_confidence=row[15] or 0.0,
                error_types=error_types,
                error_details=row[16] or '',
                manual_corrections_made=row[18] or 0,
                epicor_ready=row[19] or False,
                epicor_ready_with_one_click=row[20] or False,
                missing_info_count=row[21] or 0,
                processed_file_path=row[22] or '',
                epicor_json_path=row[23],
                raw_json_data=row[24] or '',
                notes=row[25] or '',
                created_at=row[26],
                updated_at=row[27]
            )
            results.append(result)
        
        return results
    
    def _get_all_processing_results_rest_api(self, limit: int, offset: int) -> List[ProcessingResult]:
        """Get all processing results using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        query_url = f"{self.supabase_url}/rest/v1/processing_results"
        params = {
            'select': '*',
            'limit': str(limit),
            'offset': str(offset),
            'order': 'created_at.desc'
        }
        
        response = requests.get(query_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            results = []
            for record in data:
                # Convert REST API record to ProcessingResult object
                error_types = [ErrorType(e) for e in json.loads(record.get('error_types', '[]'))]
                
                result = ProcessingResult(
                    id=record.get('id'),
                    filename=record.get('filename', ''),
                    original_filename=record.get('original_filename', ''),
                    file_size=record.get('file_size', 0),
                    processing_status=ProcessingStatus(record.get('processing_status', 'pending')),
                    validation_status=ValidationStatus(record.get('validation_status', 'pending_review')),
                    processing_start_time=datetime.fromisoformat(record.get('processing_start_time', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('processing_start_time') else None,
                    processing_end_time=datetime.fromisoformat(record.get('processing_end_time', '').replace('Z', '+00:00')) if record.get('processing_end_time') else None,
                    processing_duration=record.get('processing_duration'),
                    total_parts=record.get('total_parts', 0),
                    parts_mapped=record.get('parts_mapped', 0),
                    parts_not_found=record.get('parts_not_found', 0),
                    parts_manual_review=record.get('parts_manual_review', 0),
                    mapping_success_rate=record.get('mapping_success_rate', 0.0),
                    customer_matched=record.get('customer_matched', False),
                    customer_match_confidence=record.get('customer_match_confidence', 0.0),
                    error_types=error_types,
                    error_details=record.get('error_details', ''),
                    manual_corrections_made=record.get('manual_corrections_made', 0),
                    epicor_ready=record.get('epicor_ready', False),
                    epicor_ready_with_one_click=record.get('epicor_ready_with_one_click', False),
                    missing_info_count=record.get('missing_info_count', 0),
                    processed_file_path=record.get('processed_file_path', ''),
                    epicor_json_path=record.get('epicor_json_path'),
                    raw_json_data=record.get('raw_json_data', ''),
                    notes=record.get('notes', ''),
                    created_at=datetime.fromisoformat(record.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('created_at') else None,
                    updated_at=datetime.fromisoformat(record.get('updated_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('updated_at') else None
                )
                results.append(result)
            
            return results
        else:
            print(f"❌ REST API query failed with status: {response.status_code}")
            return []
    
    def get_processing_result_by_filename(self, filename: str) -> Optional[ProcessingResult]:
        """Get a processing result by filename."""
        try:
            if self.use_postgres:
                return self._get_processing_result_by_filename_postgres(filename)
            elif self.use_rest_api:
                return self._get_processing_result_by_filename_rest_api(filename)
            else:
                print("❌ No database connection available")
                return None
        except Exception as e:
            print(f"❌ Error getting processing result by filename: {e}")
            return None
    
    def _get_processing_result_by_filename_postgres(self, filename: str) -> Optional[ProcessingResult]:
        """Get processing result by filename using PostgreSQL."""
        from database_config import db_config
        
        sql = '''
            SELECT * FROM processing_results 
            WHERE filename = :filename 
            ORDER BY created_at DESC 
            LIMIT 1
        '''
        
        row = db_config.execute_raw_sql_single(sql, {'filename': filename})
        
        if row:
            # Convert row to ProcessingResult object
            error_types = [ErrorType(e) for e in json.loads(row[17] or '[]')]
            
            return ProcessingResult(
                id=row[0],
                filename=row[1],
                original_filename=row[2],
                file_size=row[3],
                processing_status=ProcessingStatus(row[4]),
                validation_status=ValidationStatus(row[5]),
                processing_start_time=row[6],
                processing_end_time=row[7],
                processing_duration=row[8],
                total_parts=row[9] or 0,
                parts_mapped=row[10] or 0,
                parts_not_found=row[11] or 0,
                parts_manual_review=row[12] or 0,
                mapping_success_rate=row[13] or 0.0,
                customer_matched=row[14] or False,
                customer_match_confidence=row[15] or 0.0,
                error_types=error_types,
                error_details=row[16] or '',
                manual_corrections_made=row[18] or 0,
                epicor_ready=row[19] or False,
                epicor_ready_with_one_click=row[20] or False,
                missing_info_count=row[21] or 0,
                processed_file_path=row[22] or '',
                epicor_json_path=row[23],
                raw_json_data=row[24] or '',
                notes=row[25] or '',
                created_at=row[26],
                updated_at=row[27]
            )
        
        return None
    
    def _get_processing_result_by_filename_rest_api(self, filename: str) -> Optional[ProcessingResult]:
        """Get processing result by filename using REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        query_url = f"{self.supabase_url}/rest/v1/processing_results"
        params = {
            'select': '*',
            'filename': f'eq.{filename}',
            'order': 'created_at.desc',
            'limit': '1'
        }
        
        response = requests.get(query_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                record = data[0]
                # Convert REST API record to ProcessingResult object
                error_types = [ErrorType(e) for e in json.loads(record.get('error_types', '[]'))]
                
                return ProcessingResult(
                    id=record.get('id'),
                    filename=record.get('filename', ''),
                    original_filename=record.get('original_filename', ''),
                    file_size=record.get('file_size', 0),
                    processing_status=ProcessingStatus(record.get('processing_status', 'pending')),
                    validation_status=ValidationStatus(record.get('validation_status', 'pending_review')),
                    processing_start_time=datetime.fromisoformat(record.get('processing_start_time', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('processing_start_time') else None,
                    processing_end_time=datetime.fromisoformat(record.get('processing_end_time', '').replace('Z', '+00:00')) if record.get('processing_end_time') else None,
                    processing_duration=record.get('processing_duration'),
                    total_parts=record.get('total_parts', 0),
                    parts_mapped=record.get('parts_mapped', 0),
                    parts_not_found=record.get('parts_not_found', 0),
                    parts_manual_review=record.get('parts_manual_review', 0),
                    mapping_success_rate=record.get('mapping_success_rate', 0.0),
                    customer_matched=record.get('customer_matched', False),
                    customer_match_confidence=record.get('customer_match_confidence', 0.0),
                    error_types=error_types,
                    error_details=record.get('error_details', ''),
                    manual_corrections_made=record.get('manual_corrections_made', 0),
                    epicor_ready=record.get('epicor_ready', False),
                    epicor_ready_with_one_click=record.get('epicor_ready_with_one_click', False),
                    missing_info_count=record.get('missing_info_count', 0),
                    processed_file_path=record.get('processed_file_path', ''),
                    epicor_json_path=record.get('epicor_json_path'),
                    raw_json_data=record.get('raw_json_data', ''),
                    notes=record.get('notes', ''),
                    created_at=datetime.fromisoformat(record.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('created_at') else None,
                    updated_at=datetime.fromisoformat(record.get('updated_at', datetime.now().isoformat()).replace('Z', '+00:00')) if record.get('updated_at') else None
                )
        return None
    
    # Lazy loading methods
    def _load_parts_database(self):
        """Load parts database on demand."""
        if self._parts_loaded:
            return
        
        print("📥 Loading parts database on demand...")
        try:
            if self.use_postgres:
                self._load_parts_postgres()
            elif self.use_rest_api:
                self._load_parts_rest_api()
            else:
                print("❌ No database connection available for parts loading")
                return
            
            self._parts_loaded = True
            print(f"✅ Loaded {len(self.parts_df)} parts from {self.connection_method}")
        except Exception as e:
            print(f"❌ Error loading parts database: {e}")
    
    def _load_customers_database(self):
        """Load customers database on demand."""
        if self._customers_loaded:
            return
        
        print("📥 Loading customers database on demand...")
        try:
            if self.use_postgres:
                self._load_customers_postgres()
            elif self.use_rest_api:
                self._load_customers_rest_api()
            else:
                print("❌ No database connection available for customers loading")
                return
            
            self._customers_loaded = True
            print(f"✅ Loaded {len(self.customers_df)} customers from {self.connection_method}")
        except Exception as e:
            print(f"❌ Error loading customers database: {e}")
    
    def _load_parts_postgres(self):
        """Load parts from PostgreSQL."""
        from database_config import db_config
        
        sql = "SELECT internal_part_number, description FROM parts ORDER BY internal_part_number"
        rows = db_config.execute_raw_sql(sql)
        
        data = []
        for row in rows:
            data.append({
                'internal_part_number': row[0],
                'description': row[1]
            })
        
        self.parts_df = pd.DataFrame(data)
        self._build_search_indexes()
    
    def _load_parts_rest_api(self):
        """Load parts from REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.supabase_url}/rest/v1/parts"
        params = {
            'select': 'internal_part_number,description',
            'order': 'internal_part_number'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            self.parts_df = pd.DataFrame(data)
            self._build_search_indexes()
        else:
            print(f"❌ Failed to load parts from REST API: {response.status_code}")
            self.parts_df = pd.DataFrame()
    
    def _load_customers_postgres(self):
        """Load customers from PostgreSQL."""
        from database_config import db_config
        
        sql = "SELECT account_number, company_name, address, city, state_prov, postal_code, country FROM customers ORDER BY company_name"
        rows = db_config.execute_raw_sql(sql)
        
        data = []
        for row in rows:
            data.append({
                'account_number': row[0],
                'company_name': row[1],
                'address': row[2],
                'city': row[3],
                'state': row[4],
                'postal_code': row[5],
                'country': row[6]
            })
        
        self.customers_df = pd.DataFrame(data)
    
    def _load_customers_rest_api(self):
        """Load customers from REST API."""
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.supabase_url}/rest/v1/customers"
        params = {
            'select': 'account_number,company_name,address,city,state_prov,postal_code,country',
            'order': 'company_name'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            self.customers_df = pd.DataFrame(data)
        else:
            print(f"❌ Failed to load customers from REST API: {response.status_code}")
            self.customers_df = pd.DataFrame()
    
    def _build_search_indexes(self):
        """Build search indexes for parts."""
        if self.parts_df is None or self.parts_df.empty:
            return
        
        # Build exact match index
        self.parts_by_exact_match = {}
        for idx, row in self.parts_df.iterrows():
            part_number = str(row['internal_part_number']).upper()
            self.parts_by_exact_match[part_number] = idx
        
        # Build keyword index
        self.parts_by_keywords = defaultdict(list)
        for idx, row in self.parts_df.iterrows():
            part_number = str(row['internal_part_number']).upper()
            description = str(row['description']).upper()
            
            # Extract words from part number and description
            words = self._extract_words(part_number + " " + description)
            for word in words:
                self.parts_by_keywords[word].append(idx)
    
    # Compatibility methods for existing code
    def get_parts_dataframe(self) -> pd.DataFrame:
        """Get the parts DataFrame (lazy loading)."""
        if not self._parts_loaded:
            self._load_parts_database()
        return self.parts_df if self.parts_df is not None else pd.DataFrame()
    
    def get_customers_dataframe(self) -> pd.DataFrame:
        """Get the customers DataFrame (lazy loading)."""
        if not self._customers_loaded:
            self._load_customers_database()
        return self.customers_df if self.customers_df is not None else pd.DataFrame()
