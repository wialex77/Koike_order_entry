"""
Step 4: Part Number Mapping and Account Lookup
Takes the output from step 2, maps external part numbers to internal ones,
and adds account numbers based on customer database lookups.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from step3_databases import DatabaseManager, Part, Customer

@dataclass
class MappedLineItem:
    """Represents a line item with internal part number mapping."""
    external_part_number: str
    internal_part_number: str
    description: str
    unit_price: float
    quantity: int
    mapping_confidence: float  # Confidence score for the mapping (0-100)
    mapping_status: str  # "mapped", "not_found", "manual_review"
    candidate_suggestions: List[Dict[str, Any]]  # Top 3 candidates when confidence is moderate

@dataclass
class MappedCompanyInfo:
    """Represents company information with account number lookup."""
    company_name: str
    billing_address: str
    shipping_address: str
    email: str
    phone_number: str
    contact_person: str
    contact_person_email: str
    customer_po_number: str
    po_date: str
    notes: str
    subtotal: float
    tax_amount: float
    tax_rate: float
    grand_total: float
    shipping_method: str
    shipping_account_number: str
    account_number: str
    customer_match_confidence: float  # Confidence score for customer match (0-100)
    customer_match_status: str  # "matched", "not_found", "manual_review"

@dataclass
class MappedPurchaseOrderData:
    """Complete mapped purchase order data structure."""
    company_info: MappedCompanyInfo
    line_items: List[MappedLineItem]
    processing_summary: Dict[str, Any]

class PartNumberMapper:
    """Maps external part numbers to internal ones and looks up account numbers."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, openai_api_key: Optional[str] = None):
        """
        Initialize the part number mapper.
        
        Args:
            db_manager: Database manager instance (creates new one if None)
            openai_api_key: OpenAI API key for LLM operations
        """
        import os
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv('config.env')
        
        self.db_manager = db_manager or DatabaseManager()
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.mapping_stats = {
            "parts_processed": 0,
            "parts_mapped": 0,
            "parts_not_found": 0,
            "parts_manual_review": 0,
            "customer_matched": False,
            "customer_confidence": 0.0
        }
    
    def map_line_item(self, line_item: Dict[str, Any], confidence_threshold: int = 80) -> MappedLineItem:
        """
        Map a single line item from external to internal part number using fuzzy matching + LLM.
        
        Args:
            line_item: Original line item data
            confidence_threshold: Minimum confidence score for automatic mapping
            
        Returns:
            MappedLineItem with internal part number and mapping info
        """
        external_part_number = line_item.get('external_part_number', '')
        description = line_item.get('description', '')
        unit_price = float(line_item.get('unit_price', 0.0))
        quantity = int(line_item.get('quantity', 0))
        
        # OPTIMIZED APPROACH: Fast fuzzy pre-filter + LLM only when needed
        if external_part_number:
            # Get top 3 fuzzy matches from part numbers (reduced from 5 for speed)
            fuzzy_candidates = self._get_fuzzy_part_candidates(external_part_number, top_n=3)
            
            if fuzzy_candidates:
                # Check if top fuzzy match is already ≥95% - if so, use it directly (no LLM needed)
                top_fuzzy = fuzzy_candidates[0]
                if top_fuzzy['fuzzy_score'] >= 95:
                    matching_part = top_fuzzy['part']
                    confidence = top_fuzzy['fuzzy_score']
                    candidate_suggestions = []  # No candidates needed for high confidence matches
                    
                else:
                    # Only use LLM if we have good candidates (70%+)
                    if fuzzy_candidates and fuzzy_candidates[0]['fuzzy_score'] >= 70:
                        llm_result = self._llm_select_best_part(external_part_number, description, fuzzy_candidates)
                        
                        if llm_result:
                            matching_part = llm_result['part']
                            confidence = llm_result['confidence']
                            
                            # Only include candidates if confidence < 95%
                            if confidence < 95:
                                candidate_suggestions = llm_result['candidates']
                            else:
                                candidate_suggestions = []
                            
                        else:
                            matching_part = None
                            confidence = 0.0
                            candidate_suggestions = []
                    else:
                        # No good candidates - skip LLM call entirely
                        matching_part = None
                        confidence = 0.0
                        candidate_suggestions = []
            else:
                matching_part = None
                confidence = 0.0
                candidate_suggestions = []
        else:
            # No external part number - try description matching as fallback
            if description:
                matching_part = self.db_manager.find_part_by_description(description, threshold=confidence_threshold)
                if matching_part:
                    from fuzzywuzzy import fuzz
                    confidence = fuzz.ratio(description.lower(), matching_part.description.lower())
                else:
                    matching_part = None
                    confidence = 0.0
            else:
                matching_part = None
                confidence = 0.0
        candidate_suggestions = []
        
        # Determine status based on results
        if matching_part:
            if confidence >= 95:  # High confidence - auto-select
                status = "mapped"
                internal_part_number = matching_part.internal_part_number
                self.mapping_stats["parts_mapped"] += 1
                # Clear candidates for high confidence matches since they're auto-mapped
                candidate_suggestions = []
            else:
                status = "manual_review"
                internal_part_number = ""  # Require manual review
                self.mapping_stats["parts_manual_review"] += 1
                # Only keep high-confidence candidates (70%+)
                if not candidate_suggestions:
                    # Generate candidates for manual review if we don't have them
                    if 'fuzzy_candidates' in locals():
                        # Filter to only candidates with 70%+ confidence
                        high_confidence_candidates = [c for c in fuzzy_candidates if c['fuzzy_score'] >= 70]
                        if high_confidence_candidates:
                            candidate_suggestions = [{'internal_part_number': c['internal_part_number'], 'confidence': c['fuzzy_score'], 'description': c['part'].description} for c in high_confidence_candidates[:3]]
                        else:
                            # No good candidates - mark as insufficient information
                            candidate_suggestions = [{'internal_part_number': 'INSUFFICIENT_INFO', 'confidence': 0, 'description': 'Not enough information in PO for reliable part mapping - manual entry required'}]
        else:
            # No match found
            confidence = 0.0
            status = "not_found"
            internal_part_number = ""
            self.mapping_stats["parts_not_found"] += 1
            # Provide candidates for manual review even when no match found (70%+ only)
            if not candidate_suggestions and 'fuzzy_candidates' in locals() and fuzzy_candidates:
                # Filter to only candidates with 70%+ confidence
                high_confidence_candidates = [c for c in fuzzy_candidates if c['fuzzy_score'] >= 70]
                if high_confidence_candidates:
                    candidate_suggestions = [{'internal_part_number': c['internal_part_number'], 'confidence': c['fuzzy_score'], 'description': c['part'].description} for c in high_confidence_candidates[:3]]
                else:
                    # No good candidates - mark as insufficient information
                    candidate_suggestions = [{'internal_part_number': 'INSUFFICIENT_INFO', 'confidence': 0, 'description': 'Not enough information in PO for reliable part mapping - manual entry required'}]
        
        self.mapping_stats["parts_processed"] += 1
        
        return MappedLineItem(
            external_part_number=external_part_number,
            internal_part_number=internal_part_number,
            description=description,
            unit_price=unit_price,
            quantity=quantity,
            mapping_confidence=confidence,
            mapping_status=status,
            candidate_suggestions=candidate_suggestions
        )
    
    def _get_fuzzy_part_candidates(self, external_part_number: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Multi-strategy part number matching with proper fallbacks.
        Returns fuzzy candidates for LLM to choose from later.
        """
        if not external_part_number:
            return []

        try:
            from fuzzywuzzy import process, fuzz
            all_parts = self.db_manager.get_all_parts()
            
            # Strategy 1: Text search + fuzzy on pre-filtered results
            text_search_candidates = self._search_core_part_numbers(external_part_number, all_parts)
            
            # Strategy 2: Traditional fuzzy matching on entire database (always run as fallback)
            all_part_numbers = [part.internal_part_number for part in all_parts]
            fuzzy_matches = process.extractBests(
                external_part_number,
                all_part_numbers,
                scorer=fuzz.ratio,
                limit=top_n * 3,
                score_cutoff=60
            )
            
            fuzzy_candidates = []
            for match, score in fuzzy_matches:
                part_obj = next((p for p in all_parts if p.internal_part_number == match), None)
                if part_obj:
                    fuzzy_candidates.append({
                        'part': part_obj,
                        'fuzzy_score': score,
                        'internal_part_number': part_obj.internal_part_number,
                        'description': part_obj.description,
                        'match_type': 'fuzzy'
                    })
            
            # Combine both strategies
            all_candidates = text_search_candidates + fuzzy_candidates
            
            # Remove duplicates and sort
            seen = set()
            unique_candidates = []
            for candidate in all_candidates:
                if candidate['internal_part_number'] not in seen:
                    seen.add(candidate['internal_part_number'])
                    unique_candidates.append(candidate)
            
            unique_candidates.sort(key=lambda x: x['fuzzy_score'], reverse=True)
            
            return unique_candidates[:top_n]
                
        except Exception as e:
            return []
    
    def _search_core_part_numbers(self, external_part_number: str, all_parts: List[Any]) -> List[Dict[str, Any]]:
        """
        Simple and effective part number matching using text search + fuzzy matching.
        For "103D7-2" → transform to "103D72" → find all parts containing "103D72", then fuzzy match on those.
        """
        external_upper = external_part_number.upper().strip()
        candidates = []
        
        # Step 1: Transform external part number (remove dashes and convert suffixes)
        # For "103D7-2" → "103D72", "103D7-3" → "103D73"
        transformed_external = self._transform_external_part_number(external_upper)
        
        # Step 2: Simple text search - find all parts that contain the transformed external part number
        containing_parts = []
        for part in all_parts:
            internal_part = part.internal_part_number.upper()
            if transformed_external in internal_part:
                containing_parts.append(part)
        
        # Special case: If external part starts with "KOI " (with space), also try without the space
        if external_upper.startswith("KOI ") and len(external_upper) > 4:
            koiless_external = external_upper[4:].strip()  # Remove "KOI " prefix
            for part in all_parts:
                internal_part = part.internal_part_number.upper()
                if koiless_external in internal_part:
                    containing_parts.append(part)
        
        if not containing_parts:
            return candidates
        
        # Step 2: Fuzzy matching only on the parts that contain the text
        from fuzzywuzzy import process, fuzz
        
        containing_part_numbers = [part.internal_part_number for part in containing_parts]
        
        fuzzy_matches = process.extractBests(
            transformed_external,  # Use transformed part number for fuzzy matching
            containing_part_numbers,
            scorer=fuzz.ratio,
            limit=len(containing_part_numbers),
            score_cutoff=60  # Lower threshold since we pre-filtered
        )
        
        # Step 3: Convert fuzzy matches back to part objects with confidence scores
        for match, score in fuzzy_matches:
            part_obj = next((p for p in containing_parts if p.internal_part_number == match), None)
            if part_obj:
                candidates.append({
                    'part': part_obj,
                    'fuzzy_score': score,
                    'internal_part_number': part_obj.internal_part_number,
                    'description': part_obj.description,
                    'match_type': 'text_search_fuzzy'
                })
        
        return candidates
    
    def _transform_external_part_number(self, external_part_number: str) -> str:
        """
        Transform external part number to match internal part number format.
        For "103D7-2" → "103D72", "103D7-3" → "103D73"
        """
        if not external_part_number:
            return ""
        
        # Convert to uppercase for consistency
        part = external_part_number.upper().strip()
        
        # Handle dash-suffix patterns like "103D7-2" → "103D72"
        if '-' in part:
            # Split on the last dash
            parts = part.rsplit('-', 1)
            if len(parts) == 2:
                base_part = parts[0]
                suffix = parts[1]
                
                # If suffix is a single digit or letter, append it directly
                if len(suffix) == 1 and (suffix.isdigit() or suffix.isalpha()):
                    return base_part + suffix
                
                # If suffix is a multi-character suffix, try common mappings
                suffix_mappings = {
                    '-1': '1', '-2': '2', '-3': '3', '-4': '4', '-5': '5',
                    '-6': '6', '-7': '7', '-8': '8', '-9': '9',
                    '-A': 'A', '-B': 'B', '-C': 'C', '-D': 'D', '-E': 'E', '-F': 'F'
                }
                
                if '-' + suffix in suffix_mappings:
                    return base_part + suffix_mappings['-' + suffix]
        
        # If no transformation needed, return as-is
        return part
    
    def _extract_core_part_number(self, part_number: str) -> str:
        """
        Extract the core part number by removing common prefixes and suffixes.
        
        Args:
            part_number: The part number to extract core from
            
        Returns:
            The core part number (alphanumeric characters only)
        """
        if not part_number:
            return ""
        
        # Convert to uppercase for consistency
        part = part_number.upper()
        
        # Remove common prefixes
        prefixes_to_remove = ['ZTIP', 'ZTI', 'ZT', 'Z', 'TIP', 'TI', 'T']
        for prefix in prefixes_to_remove:
            if part.startswith(prefix):
                part = part[len(prefix):]
                break
        
        # For external parts, remove common suffixes (like -1, -2, -3)
        # For internal parts, keep the full core (like 103D71, 103D73)
        if '-' in part_number:  # This is likely an external part number
            suffixes_to_remove = ['-1', '-2', '-3', '-A', '-B', '-C', '-D', '-E', '-F']
            for suffix in suffixes_to_remove:
                if part.endswith(suffix):
                    part = part[:-len(suffix)]
                    break
        
        # Keep only alphanumeric characters
        core = ''.join(c for c in part if c.isalnum())
        
        return core
    
    def _llm_select_best_part(self, external_part_number: str, description: str, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Use LLM to select the best part match from fuzzy candidates.
        Returns top 3 candidates with confidence scores.
        """
        if not candidates:
            return None
        
        try:
            # Prepare candidate info for LLM
            candidate_info = []
            for i, candidate in enumerate(candidates):
                candidate_info.append(f"""
                Option {i+1}:
                - Internal Part: {candidate['internal_part_number']}
                - Description: {candidate['description']}
                - Fuzzy Score: {candidate['fuzzy_score']}%
                """)
            
            prompt = f"""
            You are an expert at matching part numbers. Given an external part number from a purchase order, 
            pick the BEST matching internal part number from the candidates below.
            
            EXTERNAL PART NUMBER: {external_part_number}
            PO DESCRIPTION: {description}
            
            CANDIDATES:
            {chr(10).join(candidate_info)}
            
            RULES:
            1. Consider part number patterns and transformations (dashes, prefixes, suffixes)
            2. Consider description similarity and context
            3. Prefer exact or near-exact matches
            4. Consider manufacturing/industrial context
            5. For EXACT matches (identical part numbers), ALWAYS return 100% confidence
            
            EXAMPLES:
            - "ZA3232260" should match "ZA3232260" (exact match = 100% confidence)
            - "KOI 30623" should match "30623" (KOI prefix removal = 100% confidence)
            - "ZA323-2260" should match "ZA3232260" (dash removal = 95%+ confidence)
            - "KOIZA323-2260" should match "ZA3232260" (prefix removal + dash removal = 90%+ confidence)
            - "ZA3232260" should match "ZA323-2260" (dash addition = 95%+ confidence)
            - "103d7-1" should match "ZTIP103D71" (suffix -1 maps to ending 1 = 100% confidence - EXACT match after transformation)
            - "103d7-3" should match "ZTIP103D73" (suffix -3 maps to ending 3 = 100% confidence - EXACT match after transformation)
            - "ABC-2" should match "ZTIPABC2" (suffix -2 maps to ending 2 = 100% confidence - EXACT match after transformation)
            
            CRITICAL: Return ONLY valid JSON. Do not add any text, notes, explanations, or comments before or after the JSON.
            Do not add "Note:" or any other text. Return ONLY the JSON object.
            
            Return your response as JSON in this exact format:
            {{
                "best_match": "internal_part_number",
                "confidence": 100.0,
                "reasoning": "Brief explanation of why this is the best match",
                "top_3_candidates": [
                    {{"internal_part_number": "part1", "confidence": 100.0, "reasoning": "reason1"}},
                    {{"internal_part_number": "part2", "confidence": 85.0, "reasoning": "reason2"}},
                    {{"internal_part_number": "part3", "confidence": 75.0, "reasoning": "reason3"}}
                ]
            }}
            
            If no good match exists, set "best_match" to null and confidence to 0.
            
            REMEMBER: Return ONLY the JSON object. No additional text whatsoever.
            """
            
            # Check if we have OpenAI client available (need to get it from document processor)
            # For now, we'll use a simple approach - check if we can import OpenAI
            try:
                from openai import OpenAI
                # Try to get client from environment or create a test one
                import os
                from dotenv import load_dotenv
                load_dotenv('config.env')
                openai_key = os.getenv('OPENAI_API_KEY')
                if not openai_key:
                    raise Exception("No OpenAI API key")
                client = OpenAI(api_key=openai_key)
            except Exception:
                client = None
                print("No OpenAI client available, using fuzzy score as confidence")
                # Fallback to fuzzy score
                best_candidate = max(candidates, key=lambda x: x['fuzzy_score'])
                return {
                    'part': best_candidate['part'],
                    'confidence': best_candidate['fuzzy_score'],
                    'candidates': [{'internal_part_number': c['internal_part_number'], 'confidence': c['fuzzy_score']} for c in candidates[:3]]
                }
            
            response = client.chat.completions.create(
                model="gpt-4o",  # Fast and cheap
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0  # Deterministic
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up markdown code blocks if present
            if result_text.startswith('```json'):
                result_text = result_text[7:]  # Remove ```json
            if result_text.startswith('```'):
                result_text = result_text[3:]   # Remove ```
            if result_text.endswith('```'):
                result_text = result_text[:-3]  # Remove trailing ```
            result_text = result_text.strip()
            
            # Parse JSON response
            import json
            try:
                result = json.loads(result_text)
                
                if result.get('best_match'):
                    # Find the matching part object
                    best_part = next((c['part'] for c in candidates if c['internal_part_number'] == result['best_match']), None)
                    if best_part:
                        # Add descriptions to candidates from the original candidates list
                        enhanced_candidates = []
                        for llm_candidate in result.get('top_3_candidates', []):
                            # Find the original candidate with description
                            original_candidate = next((c for c in candidates if c['internal_part_number'] == llm_candidate['internal_part_number']), None)
                            if original_candidate:
                                enhanced_candidate = llm_candidate.copy()
                                enhanced_candidate['description'] = original_candidate['part'].description
                                enhanced_candidates.append(enhanced_candidate)
                        
                        return {
                            'part': best_part,
                            'confidence': result['confidence'],
                            'candidates': enhanced_candidates
                        }
                
                # If no best match or parsing failed, return top fuzzy match
                best_candidate = max(candidates, key=lambda x: x['fuzzy_score'])
                return {
                    'part': best_candidate['part'],
                    'confidence': best_candidate['fuzzy_score'],
                    'candidates': [{'internal_part_number': c['internal_part_number'], 'confidence': c['fuzzy_score']} for c in candidates[:3]]
                }
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response: {result_text}")
                # Fallback to fuzzy score
                best_candidate = max(candidates, key=lambda x: x['fuzzy_score'])
                return {
                    'part': best_candidate['part'],
                    'confidence': best_candidate['fuzzy_score'],
                    'candidates': [{'internal_part_number': c['internal_part_number'], 'confidence': c['fuzzy_score']} for c in candidates[:3]]
                }
                
        except Exception as e:
            print(f"LLM selection failed: {e}")
            # Fallback to fuzzy score
            best_candidate = max(candidates, key=lambda x: x['fuzzy_score'])
            return {
                'part': best_candidate['part'],
                'confidence': best_candidate['fuzzy_score'],
                'candidates': [{'internal_part_number': c['internal_part_number'], 'confidence': c['fuzzy_score']} for c in candidates[:3]]
            }

    
    def _fast_keyword_search(self, external_part_number: str, description: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """Fast keyword-based search as fallback."""
        candidates = []
        
        try:
            import re
            from fuzzywuzzy import fuzz
            
            # Prioritize external part number terms (like "ZOSP-2")
            search_terms = []
            if external_part_number:
                ext_terms = re.findall(r'\b[A-Za-z0-9\-]{3,}\b', external_part_number.upper())
                search_terms.extend(ext_terms)
            
            # Use the most specific term first
            primary_term = search_terms[0] if search_terms else None
            
            if primary_term:
                # Fast text search using pandas
                matching_rows = self.db_manager.parts_df[
                    self.db_manager.parts_df['description'].str.contains(primary_term, case=False, na=False)
                ]
                
                all_matches = []
                for _, row in matching_rows.iterrows():
                    similarity = fuzz.token_set_ratio(f"{external_part_number} {description}".lower(), row['description'].lower())
                    all_matches.append({
                        'internal_part_number': row['internal_part_number'],
                        'description': row['description'],
                        'confidence': similarity
                    })
                
                # Sort and deduplicate
                all_matches.sort(key=lambda x: x['confidence'], reverse=True)
                seen_parts = set()
                for match in all_matches:
                    if match['internal_part_number'] not in seen_parts and len(candidates) < top_n:
                        candidates.append(match)
                        seen_parts.add(match['internal_part_number'])
                        
        except Exception as e:
            print(f"Keyword search error: {e}")
            
        return candidates
    
    def _ai_similarity_search(self, combined_description: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """AI-powered semantic similarity search for part matching."""
        # This would use OpenAI embeddings for semantic search
        # For now, return empty to use keyword fallback
        print("AI similarity search not yet implemented, using keyword fallback")
        return []
    
    def lookup_customer_account(self, company_info: Dict[str, Any], confidence_threshold: int = 85) -> MappedCompanyInfo:
        """
        Look up customer account number based on company name.
        
        Args:
            company_info: Original company information
            confidence_threshold: Minimum confidence score for automatic matching
            
        Returns:
            MappedCompanyInfo with account number and matching info
        """
        company_name = company_info.get('company_name', '')
        billing_address = company_info.get('billing_address', '')
        shipping_address = company_info.get('shipping_address', '')
        email = company_info.get('email', '')
        phone_number = company_info.get('phone_number', '')
        contact_person = company_info.get('contact_person', '')
        contact_person_email = company_info.get('contact_person_email', '')
        customer_po_number = company_info.get('customer_po_number', '')
        po_date = company_info.get('po_date', '')
        notes = company_info.get('notes', '')
        subtotal = float(company_info.get('subtotal', 0.0))
        tax_amount = float(company_info.get('tax_amount', 0.0))
        tax_rate = float(company_info.get('tax_rate', 0.0))
        grand_total = float(company_info.get('grand_total', 0.0))
        shipping_method = company_info.get('shipping_method', 'GROUND')
        shipping_account_number = self._process_shipping_account_number(company_info.get('shipping_account_number', 'prepaid & add'))
        
        # Hardcoded business rule: Koike is never a customer, always the supplier
        if 'KOIKE' in company_name.upper() or 'ARONSON' in company_name.upper():
            print(f"Hardcoded filter: Ignoring Koike supplier as customer: {company_name}")
            company_name = ""  # Clear the company name so no lookup is attempted
        
        # NEW ADDRESS-FIRST APPROACH: Use billing address for accurate matching
        if company_name:
            # Use the new address-first matching strategy from step3_databases.py
            matched_customer = self.db_manager.find_customer_by_company_name(
                company_name=company_name,
                billing_address=billing_address,
                threshold=confidence_threshold
            )
            
            if matched_customer:
                # Customer found via address-first matching
                account_number = matched_customer.account_number
                confidence = 100.0  # High confidence from address matching
                status = "matched"
                
                print(f"✅ Customer matched via address-first: {matched_customer.company_name} (Account: {account_number})")
                
                self.mapping_stats["customer_matched"] = True
                self.mapping_stats["customer_confidence"] = confidence
                
                return MappedCompanyInfo(
                    company_name=company_name,
                    billing_address=billing_address,
                    shipping_address=shipping_address,
                    email=email,
                    phone_number=phone_number,
                    contact_person=contact_person,
                    contact_person_email=contact_person_email,
                    customer_po_number=customer_po_number,
                    po_date=po_date,
                    notes=notes,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    tax_rate=tax_rate,
                    grand_total=grand_total,
                    shipping_method=shipping_method,
                    shipping_account_number=shipping_account_number,
                    account_number=account_number,
                    customer_match_confidence=confidence,
                    customer_match_status=status
                )
            
            # Fallback: old approach if address-first fails (BILLING ADDRESS ONLY)
            fuzzy_candidates = self._get_fuzzy_customer_candidates(
                company_name, 
                top_n=3, 
                po_billing_address=billing_address,
                po_shipping_address=""  # NEVER use shipping for account matching
            )
            
            if fuzzy_candidates:
                # Check if we have multiple high-confidence candidates that might need address disambiguation
                high_confidence_candidates = [c for c in fuzzy_candidates if c['fuzzy_score'] >= 85]
                
                if len(high_confidence_candidates) > 1 and (billing_address or shipping_address):
                    print(f"🔍 Found {len(high_confidence_candidates)} high-confidence candidates (≥85%)")
                    print(f"   Using address matching to disambiguate between similar candidates...")
                    # Apply address matching to high-confidence candidates
                    high_confidence_candidates = self._apply_address_matching(
                        high_confidence_candidates, billing_address, shipping_address
                    )
                    # Re-sort after address matching
                    high_confidence_candidates.sort(key=lambda x: x['fuzzy_score'], reverse=True)
                    # Update the main fuzzy_candidates list
                    for i, candidate in enumerate(fuzzy_candidates):
                        updated_candidate = next((c for c in high_confidence_candidates if c['account_number'] == candidate['account_number']), None)
                        if updated_candidate:
                            fuzzy_candidates[i] = updated_candidate
                    # Re-sort the main list
                    fuzzy_candidates.sort(key=lambda x: x['fuzzy_score'], reverse=True)
                
                # NEW: Check for multiple ≥95% matches that need LLM address validation
                very_high_confidence_candidates = [c for c in fuzzy_candidates if c['fuzzy_score'] >= 95]
                
                if len(very_high_confidence_candidates) > 1 and (billing_address or shipping_address):
                    print(f"🚨 Found {len(very_high_confidence_candidates)} very high-confidence candidates (≥95%)")
                    print(f"   Using unified LLM to validate address matching and disambiguate...")
                    
                    # Use unified LLM function to validate which candidate has matching address
                    llm_result = self._llm_select_best_customer(
                        company_name, very_high_confidence_candidates, billing_address
                    )
                    
                    if llm_result and llm_result['confidence'] >= 95:
                        matching_customer = llm_result['customer']
                        confidence = llm_result['confidence']
                        status = "matched"
                        account_number = matching_customer.account_number
                        self.mapping_stats["customer_matched"] = True
                        self.mapping_stats["customer_confidence"] = confidence
                        print(f"✅ Unified LLM address validation: {company_name} -> {account_number} ({confidence:.1f}%)")
                    elif llm_result:
                        # LLM found matches but confidence < 95%
                        matching_customer = llm_result['customer']
                        confidence = llm_result['confidence']
                        status = "manual_review"
                        account_number = ""
                        self.mapping_stats["customer_confidence"] = confidence
                        print(f"⚠️ Unified LLM validation (manual review): {company_name} -> {matching_customer.company_name} ({confidence:.1f}%)")
                    else:
                        # LLM failed - send to manual review
                        matching_customer = None
                        confidence = 95.0  # High name confidence but needs manual review
                        status = "manual_review"
                        account_number = ""
                        self.mapping_stats["customer_confidence"] = confidence
                        print(f"⚠️ Multiple high-confidence matches require manual review: {company_name}")
                
                # Check if top fuzzy match is already ≥95% - if so, use it directly (no LLM needed)
                elif len(very_high_confidence_candidates) == 1:
                    top_fuzzy = fuzzy_candidates[0]
                    matching_customer = top_fuzzy['customer']
                    confidence = top_fuzzy['fuzzy_score']
                    status = "matched"
                    account_number = matching_customer.account_number
                    self.mapping_stats["customer_matched"] = True
                    self.mapping_stats["customer_confidence"] = confidence
                    
                    print(f"✅ Fast customer match: {company_name} -> {account_number} ({confidence:.1f}%) - No LLM needed")
                else:
                    # Use unified LLM to pick the best match from candidates (only when fuzzy < 95%)
                    llm_result = self._llm_select_best_customer(
                        company_name, fuzzy_candidates, billing_address
                    )
                    
                    if llm_result and llm_result['confidence'] >= 95:
                        matching_customer = llm_result['customer']
                        confidence = llm_result['confidence']
                        status = "matched"
                        account_number = matching_customer.account_number
                        self.mapping_stats["customer_matched"] = True
                        self.mapping_stats["customer_confidence"] = confidence
                        
                        print(f"✅ Unified LLM customer match: {company_name} -> {account_number} ({confidence:.1f}%)")
                    elif llm_result:
                        # LLM found matches but confidence < 95%
                        matching_customer = llm_result['customer']
                        confidence = llm_result['confidence']
                        status = "manual_review"
                        account_number = ""
                        self.mapping_stats["customer_confidence"] = confidence
                        
                        print(f"⚠️ Unified LLM customer match (manual review): {company_name} -> {matching_customer.company_name} ({confidence:.1f}%)")
                    else:
                        # LLM failed
                        matching_customer = None
                        confidence = 0.0
                        status = "manual_review"
                        account_number = ""
                        self.mapping_stats["customer_confidence"] = 0.0
            else:
                # No fuzzy matches found
                matching_customer = None
                confidence = 0.0
                status = "manual_review"
                account_number = ""
                self.mapping_stats["customer_confidence"] = 0.0
        
        return MappedCompanyInfo(
            company_name=company_name,
            billing_address=billing_address,
            shipping_address=shipping_address,
            email=email,
            phone_number=phone_number,
            contact_person=contact_person,
            contact_person_email=contact_person_email,
            customer_po_number=customer_po_number,
            po_date=po_date,
            notes=notes,
            subtotal=subtotal,
            tax_amount=tax_amount,
            tax_rate=tax_rate,
            grand_total=grand_total,
            shipping_method=shipping_method,
            shipping_account_number=shipping_account_number,
            account_number=account_number,
            customer_match_confidence=confidence,
            customer_match_status=status
        )

    
    def process_purchase_order(self, po_data: Dict[str, Any], 
                             part_confidence_threshold: int = 80,
                             customer_confidence_threshold: int = 85) -> MappedPurchaseOrderData:
        """
        Process complete purchase order data with mapping and lookups.
        
        Args:
            po_data: Original purchase order data from step 2
            part_confidence_threshold: Minimum confidence for part mapping
            customer_confidence_threshold: Minimum confidence for customer matching
            
        Returns:
            MappedPurchaseOrderData with all mappings applied
        """
        # Reset stats
        self.mapping_stats = {
            "parts_processed": 0,
            "parts_mapped": 0,
            "parts_not_found": 0,
            "parts_manual_review": 0,
            "customer_matched": False,
            "customer_confidence": 0.0
        }
        
        # Process company information
        mapped_company_info = self.lookup_customer_account(
            po_data.get('company_info', {}), 
            customer_confidence_threshold
        )
        
        # Process line items (filter out shipping/handling charges)
        mapped_line_items = []
        for line_item in po_data.get('line_items', []):
            # Skip shipping and handling charges - they don't have part numbers
            if self._is_shipping_charge(line_item):
                continue
                
            mapped_item = self.map_line_item(line_item, part_confidence_threshold)
            mapped_line_items.append(mapped_item)
        
        # Create processing summary
        processing_summary = {
            "total_parts": self.mapping_stats["parts_processed"],
            "parts_mapped": self.mapping_stats["parts_mapped"],
            "parts_not_found": self.mapping_stats["parts_not_found"],
            "parts_manual_review": self.mapping_stats["parts_manual_review"],
            "mapping_success_rate": (self.mapping_stats["parts_mapped"] / max(self.mapping_stats["parts_processed"], 1)) * 100,
            "customer_matched": self.mapping_stats["customer_matched"],
            "customer_confidence": self.mapping_stats["customer_confidence"],
            "part_confidence_threshold": part_confidence_threshold,
            "customer_confidence_threshold": customer_confidence_threshold,
            "requires_manual_review": (
                self.mapping_stats["parts_manual_review"] > 0 or 
                not self.mapping_stats["customer_matched"]
            )
        }
        
        return MappedPurchaseOrderData(
            company_info=mapped_company_info,
            line_items=mapped_line_items,
            processing_summary=processing_summary
        )
    
    def export_to_json(self, mapped_data: MappedPurchaseOrderData) -> Dict[str, Any]:
        """
        Export mapped purchase order data to JSON-serializable format.
        
        Args:
            mapped_data: Mapped purchase order data
            
        Returns:
            Dictionary that can be serialized to JSON
        """
        return {
            "company_info": asdict(mapped_data.company_info),
            "line_items": [asdict(item) for item in mapped_data.line_items],
            "processing_summary": mapped_data.processing_summary
        }
    
    def validate_for_epicor_export(self, mapped_data: MappedPurchaseOrderData) -> Dict[str, Any]:
        """
        Validate data is ready for Epicor export.
        
        Args:
            mapped_data: Mapped purchase order data
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "customer_valid": False,
            "parts_valid": [],
            "validation_errors": []
        }
        
        # Check customer mapping
        if mapped_data.company_info.customer_match_status != "matched":
            validation_result["is_valid"] = False
            validation_result["validation_errors"].append("Customer not matched")
        elif not mapped_data.company_info.account_number or mapped_data.company_info.account_number.strip() == "":
            validation_result["is_valid"] = False
            validation_result["validation_errors"].append("Customer account number is empty")
        else:
            validation_result["customer_valid"] = True
        
        # Check each line item
        for i, item in enumerate(mapped_data.line_items):
            part_validation = {
                "line_number": i + 1,
                "is_valid": True,
                "errors": []
            }
            
            if item.mapping_status != "mapped":
                part_validation["is_valid"] = False
                part_validation["errors"].append("Part not mapped")
            
            if not item.internal_part_number or item.internal_part_number.strip() == "":
                part_validation["is_valid"] = False
                part_validation["errors"].append("No internal part number assigned")
            
            validation_result["parts_valid"].append(part_validation)
            
            if not part_validation["is_valid"]:
                validation_result["is_valid"] = False
        
        return validation_result
    
    def parse_shipping_address(self, shipping_address: str) -> Dict[str, str]:
        """
        Parse shipping address into components for OTS fields using LLM for better accuracy.
        
        Args:
            shipping_address: Full shipping address string
            
        Returns:
            Dictionary with parsed address components
        """
        if not shipping_address:
            return {"name": "", "address1": "", "city": "", "state": "", "zip": ""}
        
        try:
            # Use LLM to parse the address
            return self._llm_parse_address(shipping_address)
        except Exception as e:
            print(f"LLM address parsing failed: {e}")
            # Fallback to simple parsing
            return self._simple_address_parse(shipping_address)
    
    def _llm_parse_address(self, address: str) -> Dict[str, str]:
        """Use LLM to parse address into components."""
        try:
            from openai import OpenAI
            
            if not self.openai_api_key:
                raise Exception("No OpenAI API key available")
            
            client = OpenAI(api_key=self.openai_api_key)
            
            prompt = f"""
Parse this shipping address into its components. Return ONLY valid JSON with no additional text.

Address to parse: "{address}"

Return this exact JSON structure:
{{
    "company_name": "string",
    "street_address": "string", 
    "city": "string",
    "state": "string",
    "zip": "string"
}}

Rules:
- company_name: The business/company name (e.g., "WEST PENN LACO, INC.")
- street_address: The street number and name (e.g., "331 OHIO STREET")
- city: The city name only (e.g., "PITTSBURGH")
- state: The state abbreviation (e.g., "PA")
- zip: The ZIP/postal code (e.g., "15209-2798")

Examples:
Input: "WEST PENN LACO, INC. 331 OHIO STREET PITTSBURGH PA 15209-2798"
Output: {{"company_name": "WEST PENN LACO, INC.", "street_address": "331 OHIO STREET", "city": "PITTSBURGH", "state": "PA", "zip": "15209-2798"}}

Input: "ABC COMPANY\n123 MAIN ST\nCHICAGO IL 60601"
Output: {{"company_name": "ABC COMPANY", "street_address": "123 MAIN ST", "city": "CHICAGO", "state": "IL", "zip": "60601"}}

Parse this address:
"""
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at parsing addresses. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.0
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse the JSON response
            import json
            
            # Try to extract JSON from the response if it's wrapped in text
            try:
                parsed = json.loads(result_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_text = result_text[start:end]
                    parsed = json.loads(json_text)
                else:
                    raise ValueError("Could not extract valid JSON from LLM response")
            
            # Map to our expected format
            return {
                "name": parsed.get("company_name", ""),
                "address1": parsed.get("street_address", ""),
                "city": parsed.get("city", ""),
                "state": parsed.get("state", ""),
                "zip": parsed.get("zip", "")
            }
            
        except Exception as e:
            print(f"LLM address parsing error: {e}")
            raise e
    
    def _simple_address_parse(self, address: str) -> Dict[str, str]:
        """Simple fallback address parsing."""
        import re
        
        lines = [line.strip() for line in address.strip().split('\n') if line.strip()]
        if not lines:
            return {"name": "", "address1": "", "city": "", "state": "", "zip": ""}
        
        # Initialize components
        name = ""
        address1 = ""
        city = ""
        state = ""
        zip_code = ""
        
        # Find city/state/zip line
        city_state_zip_line = ""
        city_line_index = -1
        
        for i, line in enumerate(lines):
            if re.search(r'[A-Z\s]+,?\s+[A-Z]{2}\.?\s+\d{5}', line):
                city_state_zip_line = line
                city_line_index = i
                break
        
        # Parse city, state, zip
        if city_state_zip_line:
            match = re.match(r'^(.+),\s*([A-Z]{2})\.?\s+(\d{5}(?:-\d{4})?)(?:\s+\d+)?$', city_state_zip_line)
            if match:
                city = match.group(1).strip()
                state = match.group(2).strip()
                zip_code = match.group(3).strip()
            else:
                match = re.match(r'^(.+)\s+([A-Z]{2})\.?\s+(\d{5}(?:-\d{4})?)(?:\s+\d+)?$', city_state_zip_line)
                if match:
                    city = match.group(1).strip()
                    state = match.group(2).strip()
                    zip_code = match.group(3).strip()
        
        # Simple name/address assignment
        if len(lines) == 1:
            name = lines[0]
        elif len(lines) >= 2:
            name = lines[0]
            if city_line_index > 1:
                address1 = lines[1]
        
        return {
            "name": name,
            "address1": address1,
            "city": city,
            "state": state,
            "zip": zip_code
        }
    
    def format_date_for_epicor(self, date_str: str) -> str:
        """
        Convert date string to Epicor ISO format.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            ISO formatted date string
        """
        if not date_str:
            from datetime import datetime
            return datetime.now().isoformat() + "Z"
        
        try:
            from datetime import datetime
            # Try common date formats
            formats = [
                "%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", 
                "%d/%m/%Y", "%Y/%m/%d"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat() + "Z"
                except ValueError:
                    continue
            
            # If no format works, use current date
            return datetime.now().isoformat() + "Z"
            
        except Exception:
            from datetime import datetime
            return datetime.now().isoformat() + "Z"
    
    def map_shipping_method_to_epicor(self, shipping_method: str) -> str:
        """
        Map shipping method from PO to Epicor ShipViaCode.
        
        Args:
            shipping_method: Shipping method from PO (e.g., "GROUND", "2ND DAY AIR")
            
        Returns:
            Epicor ShipViaCode
        """
        if not shipping_method:
            return "INVO"  # Default
        
        shipping_upper = shipping_method.upper().strip()
        
        # Map common shipping methods to Epicor codes
        if "GROUND" in shipping_upper:
            return "GRND"
        elif "SAME DAY" in shipping_upper or "SAME-DAY" in shipping_upper:
            return "SDAY"
        elif "2ND DAY" in shipping_upper or "2-DAY" in shipping_upper or "SECOND DAY" in shipping_upper:
            return "2DAY"
        elif "OVERNIGHT" in shipping_upper or "1 DAY" in shipping_upper or "NEXT DAY" in shipping_upper:
            return "OVNT"
        elif "FEDEX" in shipping_upper:
            return "FEDX"
        elif "UPS" in shipping_upper:
            return "UPS"
        elif "USPS" in shipping_upper or "POSTAL" in shipping_upper:
            return "USPS"
        elif "FREIGHT" in shipping_upper:
            return "FRGT"
        else:
            # Default to GROUND for unrecognized methods
            return "GRND"
    
    def export_to_epicor_json(self, mapped_data: MappedPurchaseOrderData) -> Dict[str, Any]:
        """
        Export to Epicor format - uses MISSING for invalid fields.
        
        Args:
            mapped_data: Mapped purchase order data
            
        Returns:
            Dictionary in Epicor format
        """
        # Always use unvalidated format - it handles MISSING fields properly
        return self._generate_epicor_format_unvalidated(mapped_data)
    
    def _generate_epicor_format_unvalidated(self, mapped_data: MappedPurchaseOrderData) -> Dict[str, Any]:
        """
        Generate Epicor format even when validation fails - use "MISSING" for missing fields.
        
        Args:
            mapped_data: Mapped purchase order data
            
        Returns:
            Dictionary in Epicor format with "MISSING" placeholders
        """
        # Parse shipping address for OTS fields
        shipping_components = self.parse_shipping_address(mapped_data.company_info.shipping_address)
        
        # Build Epicor OrderHed with "MISSING" for missing fields
        order_hed = {
            "OpenOrder": True,
            "CustNum": mapped_data.company_info.account_number if mapped_data.company_info.account_number else "MISSING",
            "PONum": mapped_data.company_info.customer_po_number or "MISSING",
            "EntryPerson": "Arzana",
            "ShipViaCode": "INVO",
            "OrderDate": self.format_date_for_epicor(""),
            "UseOTS": True,
            "OTSName": shipping_components["name"] or "MISSING",
            "OTSAddress1": shipping_components["address1"] or "MISSING",
            "OTSCity": shipping_components["city"] or "MISSING",
            "OTSState": shipping_components["state"] or "MISSING",
            "OTSZip": shipping_components["zip"] or "MISSING",
            "PayFlag": "SHIP",
            "RowMod": "A",
            "ShippingMethod": mapped_data.company_info.shipping_method or "MISSING",
            "ShippingAccountNumber": mapped_data.company_info.shipping_account_number or "MISSING"
        }
        
        # Build Epicor OrderDtl for all line items, using "MISSING" for unmapped parts
        order_dtl = []
        for item in mapped_data.line_items:
            # Use internal part number if available, otherwise "MISSING"
            part_num = item.internal_part_number if (item.internal_part_number and item.mapping_status == "mapped") else "MISSING"
            
            order_dtl.append({
                "OpenLine": True,
                "PartNum": part_num,
                "LineDesc": item.description or "MISSING",
                "SellingQuantity": str(item.quantity) if item.quantity else "MISSING",
                "OverridePriceList": True,
                "DocUnitPrice": f"{item.unit_price:.2f}" if item.unit_price else "MISSING",
                "RowMod": "A"
            })
        
        # Build final Epicor structure
        epicor_json = {
            "ds": {
                "OrderHed": [order_hed],
                "OrderDtl": order_dtl
            },
            "continueProcessingOnError": True,
            "rollbackParentOnChildError": True
        }
        
        return epicor_json
    
    def update_customer_mapping(self, mapped_data: MappedPurchaseOrderData, account_number: str) -> MappedPurchaseOrderData:
        """
        Update customer mapping with manual correction.
        
        Args:
            mapped_data: Current mapped data
            account_number: Manually selected account number
            
        Returns:
            Updated mapped data
        """
        # Update the company info
        mapped_data.company_info.account_number = account_number
        mapped_data.company_info.customer_match_status = "matched"
        mapped_data.company_info.customer_match_confidence = 100.0
        
        return mapped_data
    
    def update_part_mapping(self, mapped_data: MappedPurchaseOrderData, line_index: int, internal_part_number: str) -> MappedPurchaseOrderData:
        """
        Update part mapping with manual correction.
        
        Args:
            mapped_data: Current mapped data
            line_index: Index of the line item to update
            internal_part_number: Manually selected internal part number
            
        Returns:
            Updated mapped data
        """
        if 0 <= line_index < len(mapped_data.line_items):
            mapped_data.line_items[line_index].internal_part_number = internal_part_number
            mapped_data.line_items[line_index].mapping_status = "mapped"
            mapped_data.line_items[line_index].mapping_confidence = 100.0
        
        return mapped_data
    
    def save_mapped_data(self, mapped_data: MappedPurchaseOrderData, output_path: str) -> bool:
        """
        Save mapped purchase order data to JSON file in custom format (allows manual review items).
        
        Args:
            mapped_data: Mapped purchase order data
            output_path: Path to save the JSON file
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Export in custom format to allow manual review items
            json_data = self.export_to_json(mapped_data)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving mapped data: {e}")
            return False
    
    def generate_manual_review_report(self, mapped_data: MappedPurchaseOrderData) -> Dict[str, Any]:
        """
        Generate a report of items that need manual review.
        
        Args:
            mapped_data: Mapped purchase order data
            
        Returns:
            Dictionary with items needing manual review
        """
        review_items = []
        
        # Check customer matching - but ignore supplier/vendor names
        company_name = mapped_data.company_info.company_name.upper()
        is_supplier = any(supplier_keyword in company_name for supplier_keyword in [
            'KOIKE', 'ARONSON', 'VENDOR', 'SUPPLIER'
        ])
        
        if (mapped_data.company_info.customer_match_status != "matched" and 
            not is_supplier and 
            company_name.strip() != ""):
            review_items.append({
                "type": "customer",
                "issue": f"Customer not matched: {mapped_data.company_info.company_name}",
                "confidence": mapped_data.company_info.customer_match_confidence,
                "status": mapped_data.company_info.customer_match_status,
                "data": asdict(mapped_data.company_info)
            })
        
        # Check part mappings
        for i, item in enumerate(mapped_data.line_items):
            if item.mapping_status != "mapped":
                review_items.append({
                    "type": "part",
                    "issue": f"Part not mapped: {item.external_part_number} - {item.description}",
                    "confidence": item.mapping_confidence,
                    "status": item.mapping_status,
                    "line_number": i + 1,
                    "data": asdict(item)
                })
        
        return {
            "requires_review": len(review_items) > 0,
            "review_count": len(review_items),
            "items": review_items,
            "summary": mapped_data.processing_summary
        }
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """Get current mapping statistics."""
        return self.mapping_stats.copy()
    
    def _is_shipping_charge(self, line_item: Dict[str, Any]) -> bool:
        """
        Check if a line item is a shipping or handling charge that should be ignored.
        
        Args:
            line_item: Line item dictionary
            
        Returns:
            True if this is a shipping/handling charge that should be skipped
        """
        description = line_item.get('description', '').upper()
        external_part = line_item.get('external_part_number', '').strip()
        unit_price = float(line_item.get('unit_price', 0.0))
        
        # Skip if no external part number (common for shipping charges)
        if not external_part:
            # Check if description indicates shipping/handling
            shipping_keywords = [
                'SHIPPING', 'HANDLING', 'FREIGHT', 'DELIVERY', 'SHIP',
                'S&H', 'S & H', 'SHIPPING AND HANDLING', 'HANDLING CHARGE',
                'FREIGHT CHARGE', 'DELIVERY CHARGE', 'SHIP CHARGE'
            ]
            
            for keyword in shipping_keywords:
                if keyword in description:
                    return True
        
        # Also skip if it's a $0 value item with shipping-related description
        if unit_price == 0.0:
            shipping_keywords = [
                'SHIPPING', 'HANDLING', 'FREIGHT', 'DELIVERY', 'SHIP',
                'S&H', 'S & H', 'SHIPPING AND HANDLING', 'HANDLING CHARGE',
                'FREIGHT CHARGE', 'DELIVERY CHARGE', 'SHIP CHARGE'
            ]
            
            for keyword in shipping_keywords:
                if keyword in description:
                    return True
        
        return False
    
    def _extract_part_suffix(self, part_number: str) -> str:
        """
        Extract the suffix from a part number (e.g., -1, -2, -3, -A, -B, etc.).
        
        Args:
            part_number: The part number to extract suffix from
            
        Returns:
            The suffix if found, empty string otherwise
        """
        if not part_number:
            return ""
        
        # Convert to uppercase for consistency
        part = part_number.upper()
        
        # Check for common suffixes
        suffixes = ['-1', '-2', '-3', '-4', '-5', '-6', '-7', '-8', '-9',
                   '-A', '-B', '-C', '-D', '-E', '-F', '-G', '-H', '-I', '-J']
        
        for suffix in suffixes:
            if part.endswith(suffix):
                return suffix
        
        # For internal parts, check if it ends with a single digit or letter
        # (e.g., ZTIP103D71 -> suffix is "1")
        if len(part) > 1:
            last_char = part[-1]
            if last_char.isdigit() or last_char.isalpha():
                # For internal parts, we want the last character as suffix
                # (e.g., ZTIP103D71 -> "1", ZTIP103D7A -> "A")
                return last_char
        
        return ""
    
    def _normalize_address(self, address: str) -> str:
        """
        Normalize an address for better matching by:
        - Converting to uppercase
        - Removing extra whitespace
        - Standardizing common abbreviations
        - Removing punctuation differences
        
        Args:
            address: Address string to normalize
            
        Returns:
            Normalized address string
        """
        if not address:
            return ""
        
        import re
        
        # Convert to uppercase and strip
        normalized = address.upper().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Standardize common abbreviations
        abbreviations = {
            'STREET': 'ST',
            'AVENUE': 'AVE', 
            'BOULEVARD': 'BLVD',
            'DRIVE': 'DR',
            'ROAD': 'RD',
            'LANE': 'LN',
            'COURT': 'CT',
            'PLACE': 'PL',
            'PARKWAY': 'PKWY',
            'PARK': 'PK',
            'NORTH': 'N',
            'SOUTH': 'S',
            'EAST': 'E',
            'WEST': 'W',
            'NORTHEAST': 'NE',
            'NORTHWEST': 'NW',
            'SOUTHEAST': 'SE',
            'SOUTHWEST': 'SW'
        }
        
        # Handle P.O. Box variations - do this early and be more comprehensive
        normalized = re.sub(r'P\.O\.\s*BOX', 'PO BOX', normalized)
        normalized = re.sub(r'PO\.\s*BOX', 'PO BOX', normalized)
        normalized = re.sub(r'P\s+O\s+BOX', 'PO BOX', normalized)
        normalized = re.sub(r'P\.O\s+BOX', 'PO BOX', normalized)
        
        for full, abbrev in abbreviations.items():
            normalized = normalized.replace(f' {full} ', f' {abbrev} ')
            normalized = normalized.replace(f' {full}.', f' {abbrev}')
            normalized = normalized.replace(f' {full},', f' {abbrev},')
            normalized = normalized.replace(f' {full}$', f' {abbrev}')
        
        # Remove trailing punctuation
        normalized = re.sub(r'[.,;]+$', '', normalized)
        
        return normalized
    
    def _extract_street_address(self, full_address: str) -> str:
        """
        Extract just the street address portion from a full address.
        Removes company name, city, state, and zip code to get just the street.
        
        Args:
            full_address: Full address string that may include company name, city, state, zip
            
        Returns:
            Just the street address portion
        """
        if not full_address:
            return ""
        
        import re
        
        # Split by newlines to get individual lines
        lines = [line.strip() for line in full_address.split('\n') if line.strip()]
        
        if not lines:
            return ""
        
        # Look for the line that contains a street number (starts with digits)
        street_line = ""
        for line in lines:
            # Check if line starts with a number (street number)
            if re.match(r'^\d+', line.strip()):
                street_line = line.strip()
                break
        
        # If no street number found, try to find a line that looks like an address
        if not street_line:
            for line in lines:
                # Look for lines that contain common street indicators
                if any(indicator in line.upper() for indicator in ['ST', 'AVE', 'BLVD', 'DR', 'RD', 'LN', 'CT', 'PL', 'PKWY', 'PO BOX', 'P.O. BOX', 'BOX']):
                    street_line = line.strip()
                    break
        
        # If still no street found, try to find P.O. Box or similar patterns
        if not street_line:
            for line in lines:
                # Look for P.O. Box patterns
                if re.search(r'P\.?O\.?\s*BOX', line.upper()):
                    street_line = line.strip()
                    break
        
        # If still no street found, use the first non-empty line
        if not street_line and lines:
            street_line = lines[0]
        
        return street_line
    
    def _process_shipping_account_number(self, shipping_account_number: str) -> str:
        """
        Process shipping account number according to business rules:
        - If only FedEx account provided, it's prepaid and add
        - If both FedEx and UPS accounts provided, prioritize UPS
        - If no account provided, it's prepaid and add
        - Special case: Matheson should return 28Y05E
        """
        if not shipping_account_number or shipping_account_number.lower() in ['prepaid & add', 'prepaid', '']:
            return 'prepaid & add'
        
        # Special case for Matheson - always return 28Y05E
        if 'matheson' in shipping_account_number.lower() or shipping_account_number == '453491145':
            print(f"🏢 Matheson special case: returning 28Y05E instead of {shipping_account_number}")
            return '28Y05E'
        
        # Check if the account number contains multiple accounts (FedEx and UPS)
        # Look for patterns that might indicate multiple accounts
        account_text = shipping_account_number.lower()
        
        # Check for FedEx and UPS indicators
        has_fedex = any(indicator in account_text for indicator in ['fedex', 'fed ex', 'fedx'])
        has_ups = any(indicator in account_text for indicator in ['ups', 'united parcel'])
        
        # If both FedEx and UPS are mentioned, prioritize UPS
        if has_fedex and has_ups:
            print(f"🔍 Found both FedEx and UPS accounts, prioritizing UPS: {shipping_account_number}")
            # Extract UPS account (this is a simple heuristic - in practice you might need more sophisticated parsing)
            # For now, return the original account number but log the preference
            return shipping_account_number
        
        # If only FedEx is mentioned, it's prepaid and add
        elif has_fedex and not has_ups:
            print(f"📦 Only FedEx account found, treating as prepaid & add: {shipping_account_number}")
            return 'prepaid & add'
        
        # If only UPS or no specific carrier mentioned, use the account number
        else:
            # Check if it looks like a UPS account number (28Y05E format)
            if len(shipping_account_number) >= 6 and any(c.isalpha() for c in shipping_account_number):
                print(f"🚚 Using UPS account number: {shipping_account_number}")
                return shipping_account_number
            else:
                # Default case - use the account number as provided
                return shipping_account_number
    
    def _get_fuzzy_customer_candidates(self, company_name: str, top_n: int = 3, 
                                      po_billing_address: str = "", po_shipping_address: str = "") -> List[Dict[str, Any]]:
        """
        Get top N fuzzy matches for a company name from the database.
        When multiple customers have the same name, uses address matching for disambiguation.
        For companies with many locations (like Holston Gases), checks ALL customers with same name.
        
        Args:
            company_name: Company name to search for
            top_n: Number of top candidates to return
            po_billing_address: Billing address from PO for disambiguation
            po_shipping_address: Shipping address from PO for disambiguation
            
        Returns:
            List of candidate dictionaries with customer objects and scores
        """
        if not company_name:
            return []

        try:
            from fuzzywuzzy import process, fuzz
            
            # Get all customers from database
            all_customers = self.db_manager.get_all_customers()
            company_names = [customer.company_name for customer in all_customers]
            
            # Strategy 1: Check for exact substring matches (highest priority)
            substring_matches = []
            for customer in all_customers:
                internal_name = customer.company_name.upper()
                external_name = company_name.upper()
                
                # Check if external name is contained in internal name
                if external_name in internal_name:
                    # Calculate confidence based on length ratio
                    confidence = (len(external_name) / len(internal_name)) * 100
                    substring_matches.append({
                        'customer': customer,
                        'fuzzy_score': min(confidence + 20, 100),  # Boost confidence for substring matches
                        'company_name': customer.company_name,
                        'account_number': customer.account_number,
                        'match_type': 'substring'
                    })
            
            # Strategy 2: Extract core company name and match
            core_matches = []
            external_core = self._extract_core_company_name(company_name)
            if external_core and len(external_core) >= 3:  # Only if we have a meaningful core
                for customer in all_customers:
                    internal_core = self._extract_core_company_name(customer.company_name)
                    if internal_core and external_core in internal_core:
                        confidence = (len(external_core) / len(internal_core)) * 100
                        core_matches.append({
                            'customer': customer,
                            'fuzzy_score': min(confidence + 15, 95),  # Slightly lower than substring
                            'company_name': customer.company_name,
                            'account_number': customer.account_number,
                            'match_type': 'core'
                        })
            
            # Strategy 3: Traditional fuzzy matching (fallback)
            fuzzy_matches = process.extractBests(
                company_name,
                company_names,
                scorer=fuzz.ratio,
                limit=top_n * 2,  # Get more candidates for variety
                score_cutoff=50  # Lower threshold for more candidates
            )
            
            fuzzy_candidates = []
            for match, score in fuzzy_matches:
                customer_obj = next((c for c in all_customers if c.company_name == match), None)
                if customer_obj:
                    fuzzy_candidates.append({
                        'customer': customer_obj,
                        'fuzzy_score': score,
                        'company_name': customer_obj.company_name,
                        'account_number': customer_obj.account_number,
                        'match_type': 'fuzzy'
                    })
            
            # Combine and deduplicate results
            all_candidates = substring_matches + core_matches + fuzzy_candidates
            
            # Remove duplicates based on account_number (not company_name) to allow multiple customers with same name
            seen = set()
            unique_candidates = []
            for candidate in all_candidates:
                if candidate['account_number'] not in seen:
                    seen.add(candidate['account_number'])
                    unique_candidates.append(candidate)
            
            # Sort by score (highest first)
            unique_candidates.sort(key=lambda x: x['fuzzy_score'], reverse=True)
            
            # PRIORITY 1: Find ALL customers with the same/similar company name for address matching
            # This is critical for companies like Holston Gases with multiple locations
            same_name_candidates = [c for c in unique_candidates if c['company_name'].upper() == company_name.upper()]
            
            # If we don't have multiple exact matches, check if the search term contains a core company name
            if len(same_name_candidates) <= 1:
                # Extract core company name from the search term
                core_name = self._extract_core_company_name(company_name)
                if core_name and len(core_name) >= 3:
                    # Look for customers whose company name contains this core name
                    same_name_candidates = [c for c in unique_candidates if core_name in c['company_name'].upper()]
                    print(f"Found {len(same_name_candidates)} customers with core name '{core_name}'")
            
            # If we have multiple customers with same name AND addresses available, prioritize address matching
            if len(same_name_candidates) > 1 and (po_billing_address or po_shipping_address):
                print(f"🔍 Found {len(same_name_candidates)} customers with same/similar name '{company_name}'")
                print(f"   Using PO billing address for disambiguation: {po_billing_address}")
                print(f"   Applying address matching to ALL {len(same_name_candidates)} customers...")
                
                # Apply address matching to ALL customers with same name (not just top 3)
                same_name_candidates = self._apply_address_matching(
                    same_name_candidates, po_billing_address, po_shipping_address
                )
                
                # Check if address matching returned results
                if not same_name_candidates:
                    # Address matching failed - marked as MISSING
                    print(f"❌ Address matching marked as MISSING - no candidates returned")
                    return []
                
                # Check if we got a good address match (>= 30% similarity)
                best_address_match = max(c.get('address_match', 0) for c in same_name_candidates)
                if best_address_match >= 30:
                    print(f"✅ Found good address match ({best_address_match:.1f}%), using address-based selection")
                    # Replace the same-name candidates in the full list with address-matched versions
                    for i, candidate in enumerate(unique_candidates):
                        updated_candidate = next((c for c in same_name_candidates if c['account_number'] == candidate['account_number']), None)
                        if updated_candidate:
                            unique_candidates[i] = updated_candidate
                    # Re-sort after address matching
                    unique_candidates.sort(key=lambda x: x['fuzzy_score'], reverse=True)
                else:
                    print(f"⚠️  Poor address match ({best_address_match:.1f}%), falling back to state matching...")
                    # Apply state matching as fallback
                    same_name_candidates = self._apply_state_matching(
                        same_name_candidates, po_billing_address, po_shipping_address
                    )
                    # Replace the same-name candidates in the full list with state-matched versions
                    for i, candidate in enumerate(unique_candidates):
                        updated_candidate = next((c for c in same_name_candidates if c['account_number'] == candidate['account_number']), None)
                        if updated_candidate:
                            unique_candidates[i] = updated_candidate
                    # Re-sort after state matching
                    unique_candidates.sort(key=lambda x: x['fuzzy_score'], reverse=True)
            else:
                print(f"Single customer match or no address available, using name-only matching")
            
            # Get top candidates (address matching already applied above if needed)
            top_candidates = unique_candidates[:top_n]
            
            print(f"Multi-strategy customer candidates for '{company_name}': {len(top_candidates)} found")
            for i, candidate in enumerate(top_candidates):
                address_info = f" (address: {candidate.get('address_match', 0):.1f}%)" if 'address_match' in candidate else ""
                print(f"  {i+1}. {candidate['company_name']} (Account {candidate['account_number']}) ({candidate['fuzzy_score']:.1f}%) [{candidate['match_type']}]{address_info}")
            
            return top_candidates
            
        except Exception as e:
            print(f"Error getting fuzzy customer candidates: {e}")
            return []
    
    def _apply_address_matching(self, candidates: List[Dict[str, Any]], 
                               po_billing_address: str, po_shipping_address: str) -> List[Dict[str, Any]]:
        """
        Apply address matching to disambiguate customers with the same company name.
        
        Args:
            candidates: List of customer candidates with same company name
            po_billing_address: Billing address from PO
            po_shipping_address: Shipping address from PO
            
        Returns:
            List of candidates with updated scores based on address matching
        """
        if len(candidates) <= 1:
            return candidates
        
        try:
            from fuzzywuzzy import fuzz
            
            # CRITICAL: ONLY use billing address for account matching, NEVER shipping
            if not po_billing_address:
                return candidates
            
            addresses_to_try = [("billing", po_billing_address)]
            
            print(f"   📍 Using BILLING address ONLY for account matching:")
            print(f"     Billing: '{po_billing_address}'")
            
            # Calculate address similarity for each candidate using the best address
            best_address_match = 0
            best_candidate = None
            best_address_type = None
            
            for candidate in candidates:
                customer = candidate['customer']
                customer_address = customer.address if hasattr(customer, 'address') else ""
                
                if customer_address:
                    # Try all available addresses and use the best match
                    best_similarity = 0
                    best_addr_type = None
                    
                    for addr_type, po_addr in addresses_to_try:
                        # Extract street address from PO address (remove company name, city, state, zip)
                        po_street = self._extract_street_address(po_addr)
                        customer_normalized = self._normalize_address(customer_address)
                        
                        # Normalize both for comparison
                        po_normalized = self._normalize_address(po_street)
                        
                        # Debug: Show normalized addresses for troubleshooting
                        if best_similarity == 0:  # Only show for first comparison
                            print(f"       🔍 Address comparison:")
                            print(f"         PO normalized: '{po_normalized}'")
                            print(f"         DB normalized: '{customer_normalized}'")
                        
                        # Use both exact and fuzzy matching
                        if po_normalized == customer_normalized:
                            similarity = 100
                            print(f"       ✅ EXACT MATCH found!")
                        else:
                            # Try fuzzy matching on normalized addresses
                            similarity = fuzz.ratio(po_normalized, customer_normalized)
                            
                            # If fuzzy match is good but not perfect, try partial matching
                            if similarity >= 60 and similarity < 100:
                                # Check if street number and name match (partial match)
                                po_parts = po_normalized.split()
                                customer_parts = customer_normalized.split()
                                
                                # If first 2-3 parts match (street number + name), boost the score
                                if len(po_parts) >= 2 and len(customer_parts) >= 2:
                                    if po_parts[0] == customer_parts[0] and po_parts[1] == customer_parts[1]:
                                        similarity = min(similarity + 20, 95)  # Boost but cap at 95%
                        
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_addr_type = addr_type
                    
                    candidate['address_match'] = best_similarity
                    
                    # Track the best address match across all candidates
                    if best_similarity > best_address_match:
                        best_address_match = best_similarity
                        best_candidate = candidate
                        best_address_type = best_addr_type
                    
                    print(f"     • {candidate['company_name']} (Account {candidate['account_number']})")
                    print(f"       Address: '{customer_address}'")
                    print(f"       Best Similarity: {best_similarity:.1f}% ({best_addr_type})")
                else:
                    candidate['address_match'] = 0
                    print(f"     • {candidate['company_name']} (Account {candidate['account_number']})")
                    print(f"       Address: No address data available")
                    print(f"       Similarity: 0.0%")
            
            # Require minimum 50% address match - otherwise mark as MISSING
            if best_address_match < 50:
                print(f"   ❌ CRITICAL: Address matching failed")
                print(f"      Best address match: {best_address_match:.1f}% (need ≥50%)")
                print(f"      → Marking as MISSING - requires manual review")
                return []  # Don't guess
            
            # Give a boost to the customer with the best address match (≥50%)
            if best_candidate:
                # Scale the boost based on address match quality
                if best_address_match >= 80:
                    address_boost = 100  # Large boost for excellent matches
                elif best_address_match >= 60:
                    address_boost = 50   # Medium boost for good matches
                else:
                    address_boost = 25   # Small boost for moderate matches (50-59%)
                
                best_candidate['fuzzy_score'] = best_candidate['fuzzy_score'] + address_boost
                best_candidate['match_type'] = f"{best_candidate['match_type']}_address"
                print(f"   🎯 SELECTED: {best_candidate['company_name']} (Account {best_candidate['account_number']})")
                print(f"      Reason: Address match {best_address_match:.1f}% (≥50%) - applying +{address_boost}% boost")
            
            return candidates
            
        except Exception as e:
            print(f"Error in address matching: {e}")
            return candidates
    
    def _extract_core_company_name(self, company_name: str) -> str:
        """
        Extract the core company name by removing common suffixes.
        
        Args:
            company_name: The company name to extract core from
            
        Returns:
            The core company name
        """
        if not company_name:
            return ""
        
        # Convert to uppercase for consistency
        name = company_name.upper().strip()
        
        # Remove common suffixes
        suffixes_to_remove = [
            ', INC', ', INC.', ' INC', ' INC.',
            ', LLC', ', L.L.C.', ' LLC', ' L.L.C.',
            ', CORP', ', CORP.', ' CORP', ' CORP.',
            ', CO', ', CO.', ' CO', ' CO.',
            ', LTD', ', LTD.', ' LTD', ' LTD.',
            ', LP', ', L.P.', ' LP', ' L.P.',
            ', LLP', ', L.L.P.', ' LLP', ' L.L.P.'
        ]
        
        for suffix in suffixes_to_remove:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
                break
        
        return name
    
    def _apply_state_matching(self, candidates: List[Dict[str, Any]], 
                             po_billing_address: str, po_shipping_address: str) -> List[Dict[str, Any]]:
        """
        Apply state matching as fallback when address matching is poor.
        
        Args:
            candidates: List of customer candidates with same company name
            po_billing_address: Billing address from PO
            po_shipping_address: Shipping address from PO
            
        Returns:
            List of candidates sorted by state match (if any state matches found)
        """
        if len(candidates) <= 1:
            return candidates
        
        try:
            import re
            
            # Extract state from PO billing address ONLY (NEVER shipping)
            po_states = set()
            if po_billing_address:
                    # Look for 2-letter state codes (like LA, TX, CA) - be more specific
                    # Look for patterns like "City, ST" or "ST 12345" or "ST US"
                    state_patterns = [
                        r',\s*([A-Z]{2})\s+(?:\d{5}|US)',  # "City, ST 12345" or "City, ST US"
                        r'\b([A-Z]{2})\s+\d{5}',           # "ST 12345"
                        r'\b([A-Z]{2})\s+US\b',            # "ST US"
                        r',\s*([A-Z]{2})\s*$',             # "City, ST" at end
                    ]
                    
                    for pattern in state_patterns:
                        state_match = re.search(pattern, po_billing_address.upper())
                        if state_match:
                            state = state_match.group(1)
                            # Filter out common false positives
                            if state not in ['CO', 'ST', 'RD', 'DR', 'BL', 'AV', 'CT', 'PK', 'PL']:
                                po_states.add(state)
                                break
            
            if not po_states:
                print(f"   ⚠️  No state found in PO addresses")
                return []
            
            print(f"   📍 PO states found: {', '.join(po_states)}")
            
            # Check each candidate for state match
            state_matched_candidates = []
            for candidate in candidates:
                customer = candidate['customer']
                customer_state = getattr(customer, 'state', '').strip().upper()
                
                if customer_state:
                    if customer_state in po_states:
                        # State match found!
                        candidate['state_match'] = 100  # Perfect state match
                        candidate['matched_state'] = customer_state
                        state_matched_candidates.append(candidate)
                        print(f"     ✅ {candidate['company_name']} (Account {candidate['account_number']}) - State match: {customer_state}")
                    else:
                        candidate['state_match'] = 0
                        print(f"     ❌ {candidate['company_name']} (Account {candidate['account_number']}) - State: {customer_state} (no match)")
                else:
                    candidate['state_match'] = 0
                    print(f"     ❌ {candidate['company_name']} (Account {candidate['account_number']}) - No state data")
            
            # Sort by state match score (highest first)
            state_matched_candidates.sort(key=lambda x: x.get('state_match', 0), reverse=True)
            
            if state_matched_candidates:
                print(f"   🎯 Found {len(state_matched_candidates)} state matches")
                return state_matched_candidates
            else:
                print(f"   ⚠️  No state matches found")
                return []
                
        except Exception as e:
            print(f"Error in state matching: {e}")
            return []
    
    def _llm_select_best_customer(self, company_name: str, candidates: List[Dict[str, Any]], 
                                 po_billing_address: str = "") -> Optional[Dict[str, Any]]:
        """
        Unified LLM function to select the best customer match from fuzzy candidates.
        Intelligently handles both address validation for high-confidence matches and general selection.
        
        Args:
            company_name: Company name from PO
            candidates: List of fuzzy-matched customer candidates
            po_billing_address: Billing address from PO for disambiguation
            
        Returns:
            Dictionary with best customer match and confidence, or None if failed
        """
        if not candidates:
            return None
        
        try:
            # Get OpenAI client from document processor
            from step2_ocr_ai import DocumentProcessor
            doc_processor = DocumentProcessor()
            
            if not hasattr(doc_processor, 'client') or not doc_processor.client:
                return None
            
            # Check if we have multiple high-confidence candidates (≥95%)
            high_confidence_candidates = [c for c in candidates if c['fuzzy_score'] >= 95]
            is_high_confidence_scenario = len(high_confidence_candidates) > 1
            
            # Prepare candidate information with address data
            candidate_info = []
            for i, candidate in enumerate(candidates, 1):
                customer = candidate['customer']
                customer_address = customer.address if hasattr(customer, 'address') else "No address data"
                address_match = candidate.get('address_match', 0)
                
                candidate_info.append(
                    f"{i}. {candidate['company_name']} (Account: {candidate['account_number']})\n"
                    f"   Name Match: {candidate['fuzzy_score']:.1f}%\n"
                    f"   Address: {customer_address}\n"
                    f"   Address Match: {address_match:.1f}%"
                )
            
            # Prepare address information for the prompt
            po_address_info = ""
            if po_billing_address:
                po_address_info = f"\nPO BILLING ADDRESS:\n{po_billing_address}\n"
            
            # Create context-aware prompt based on scenario
            if is_high_confidence_scenario:
                prompt = f"""
                You are an expert at matching company addresses. Given multiple companies with very similar names (≥95% similarity),
                determine which one has the BEST address match to the PO address.
                
                PO COMPANY NAME: {company_name}{po_address_info}
                
                HIGH-CONFIDENCE CANDIDATES (≥95% name similarity):
                {chr(10).join(candidate_info)}
                
                CRITICAL RULES:
                1. Focus on ADDRESS matching since company names are nearly identical
                2. Consider partial address matches (street names, city, state, zip)
                3. PO Box numbers should match exactly
                4. Street numbers and names should be similar
                5. City and state should match
                6. If no good address match exists, return confidence < 95%
                7. If multiple candidates have equally good address matches, return confidence < 95%
                
                EXAMPLES:
                - "P.O. BOX 9390, WYOMING MI" should match "P.O. BOX 9390, WYOMING MI"
                - "P.O. BOX 9390, WYOMING MI" should NOT match "P.O. BOX 9391, WYOMING MI"
                - "123 Main St, Chicago IL" should match "123 Main Street, Chicago IL"
                - "456 Oak Ave, Detroit MI" should NOT match "123 Main St, Chicago IL"
                
                CRITICAL: Return ONLY valid JSON. Do not add any text, notes, explanations, or comments before or after the JSON.
                Do not add "Note:" or any other text. Return ONLY the JSON object.
                
                Return your response as JSON in this exact format:
                {{
                    "best_match": "company_name",
                    "confidence": xx.x,
                    "reasoning": "brief explanation of address match quality"
                }}
                
                If no good address match exists or multiple equally good matches exist, set "best_match" to null and confidence to 0.
                
                REMEMBER: Return ONLY the JSON object. No additional text whatsoever.
                """
                system_message = "You are an expert at matching company addresses for business databases."
            else:
                prompt = f"""
                You are an expert at matching company names and addresses. Given a company name and address from a purchase order, 
                pick the BEST matching company from the candidates below.
                
                PO COMPANY NAME: {company_name}{po_address_info}
                
                CANDIDATES:
                {chr(10).join(candidate_info)}
                
                RULES:
                1. Consider company name variations (Inc, LLC, Corp, Co, etc.)
                2. Consider abbreviations and full names
                3. Consider common business name patterns
                4. Prefer exact or near-exact matches
                5. Consider manufacturing/industrial context
                6. When multiple customers have the same company name, use address matching to disambiguate
                7. Address similarity is crucial for distinguishing between different locations of the same company
                8. Consider partial address matches (street names, city names, state, etc.)
                
                EXAMPLES:
                - "Indiana Oxygen Co." should match "Indiana Oxygen Co, Inc"
                - "ABC Manufacturing" should match "ABC Manufacturing LLC"
                - "XYZ Corp" should match "XYZ Corporation"
                - "GAS AND SUPPLY" with address "125 THRUWAY PK" should match the customer with that specific address
                
                CRITICAL: Return ONLY valid JSON. Do not add any text, notes, explanations, or comments before or after the JSON.
                Do not add "Note:" or any other text. Return ONLY the JSON object.
                
                Return your response as JSON in this exact format:
                {{
                    "best_match": "company_name",
                    "confidence": xx.x,
                    "reasoning": "brief explanation of match quality"
                }}
                
                If no good match exists, set "best_match" to null and confidence to 0.
                
                REMEMBER: Return ONLY the JSON object. No additional text whatsoever.
                """
                system_message = "You are an expert at matching company names for business databases."
            
            response = doc_processor.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.0
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up markdown code blocks if present
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            result_text = result_text.strip()
            
            # Parse JSON response
            import json
            try:
                llm_result = json.loads(result_text)
                
                best_match_name = llm_result.get('best_match')
                confidence = float(llm_result.get('confidence', 0))
                reasoning = llm_result.get('reasoning', '')
                
                if is_high_confidence_scenario:
                    print(f"   LLM Address Validation Reasoning: {reasoning}")
                else:
                    print(f"   LLM Selection Reasoning: {reasoning}")
                
                if best_match_name and confidence >= 95:
                    # Find the matching candidate
                    for candidate in candidates:
                        if candidate['company_name'] == best_match_name:
                            return {
                                'customer': candidate['customer'],
                                'confidence': confidence,
                                'reasoning': reasoning
                            }
                
                # If no best match or confidence < 95%, return top fuzzy match
                best_candidate = max(candidates, key=lambda x: x['fuzzy_score'])
                return {
                    'customer': best_candidate['customer'],
                    'confidence': best_candidate['fuzzy_score'],
                    'reasoning': f"Fallback to highest fuzzy score: {best_candidate['fuzzy_score']:.1f}%"
                }
                
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response: {result_text}")
                # Fallback to fuzzy score
                best_candidate = max(candidates, key=lambda x: x['fuzzy_score'])
                return {
                    'customer': best_candidate['customer'],
                    'confidence': best_candidate['fuzzy_score'],
                    'reasoning': "JSON parse error - using fuzzy fallback"
                }
                
        except Exception as e:
            print(f"LLM customer selection failed: {e}")
            # Fallback to fuzzy score
            best_candidate = max(candidates, key=lambda x: x['fuzzy_score'])
            return {
                'customer': best_candidate['customer'],
                'confidence': best_candidate['fuzzy_score'],
                'reasoning': f"LLM error - using fuzzy fallback: {e}"
            }

# Example usage
if __name__ == "__main__":
    # Test the part number mapper
    mapper = PartNumberMapper()
    
    # Example purchase order data (from step 2)
    sample_po_data = {
        "company_info": {
            "company_name": "ABC Manufacturing Inc",
            "address": "123 Industrial Way, Anytown, ST 12345",
            "email": "orders@abcmfg.com",
            "phone_number": "555-123-4567",
            "contact_person": "John Smith",
            "contact_person_email": "john.smith@abcmfg.com"
        },
        "line_items": [
            {
                "external_part_number": "ABC-12345",
                "description": "Widget Assembly Type A",
                "unit_price": 25.50,
                "quantity": 100
            },
            {
                "external_part_number": "XYZ-98765",
                "description": "Connector Cable 6ft",
                "unit_price": 15.75,
                "quantity": 50
            }
        ]
    }
    
    # Process the purchase order
    try:
        mapped_data = mapper.process_purchase_order(sample_po_data)
        
        # Print results
        print("Mapping Results:")
        print(f"Customer: {mapped_data.company_info.company_name}")
        print(f"Account Number: {mapped_data.company_info.account_number}")
        print(f"Customer Match Status: {mapped_data.company_info.customer_match_status}")
        print(f"Customer Confidence: {mapped_data.company_info.customer_match_confidence:.1f}%")
        
        print(f"\nLine Items ({len(mapped_data.line_items)}):")
        for i, item in enumerate(mapped_data.line_items, 1):
            print(f"  {i}. {item.external_part_number} -> {item.internal_part_number}")
            print(f"     Description: {item.description}")
            print(f"     Status: {item.mapping_status}")
            print(f"     Confidence: {item.mapping_confidence:.1f}%")
        
        print(f"\nProcessing Summary:")
        for key, value in mapped_data.processing_summary.items():
            print(f"  {key}: {value}")
        
        # Generate manual review report
        review_report = mapper.generate_manual_review_report(mapped_data)
        if review_report["requires_review"]:
            print(f"\nManual Review Required ({review_report['review_count']} items):")
            for item in review_report["items"]:
                print(f"  - {item['type'].upper()}: {item['issue']}")
        else:
            print("\nNo manual review required!")
            
    except Exception as e:
        print(f"Error processing purchase order: {e}")
