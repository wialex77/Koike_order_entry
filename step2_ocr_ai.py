"""
Step 2: OCR/AI Processing Module
Processes documents using OCR for images and AI for text extraction.
Outputs structured JSON with company info and line items.
"""

import os
import json
import base64
import io
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pytesseract
from PIL import Image
import PyPDF2
from docx import Document
from openai import OpenAI
from dotenv import load_dotenv
import requests
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()

@dataclass
class LineItem:
    """Represents a line item from the purchase order."""
    external_part_number: str
    description: str
    unit_price: float
    quantity: int

@dataclass
class CompanyInfo:
    """Represents company information from the purchase order."""
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

@dataclass
class PurchaseOrderData:
    """Complete purchase order data structure."""
    company_info: CompanyInfo
    line_items: List[LineItem]

class DocumentProcessor:
    """Processes various document types to extract purchase order information."""
    
    def __init__(self, openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        """
        Initialize the document processor.
        
        Args:
            openai_api_key: OpenAI API key for AI processing
            gemini_api_key: Google Gemini API key for image processing
        """
        # Ensure environment variables are loaded
        load_dotenv('config.env')
        
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.client = None
        self.gemini_model = None
        
        # Initialize OpenAI
        if self.openai_api_key:
            try:
                self.client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                self.client = None
        
        # Initialize Gemini for image processing
        if self.gemini_api_key:
            try:
                # Test the API key by making a simple request
                test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.gemini_api_key}"
                test_response = requests.get(test_url, timeout=10)
                if test_response.status_code == 200:
                    self.gemini_model = True  # Flag to indicate Gemini is available
                else:
                    self.gemini_model = None
            except Exception as e:
                pass
                self.gemini_model = None
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file (first 2 pages only to avoid terms/conditions)."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                # Only process first 2 pages to avoid terms/conditions and irrelevant content
                max_pages = min(2, len(pdf_reader.pages))
                for i in range(max_pages):
                    text += pdf_reader.pages[i].extract_text() + "\n"
                return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from Word document."""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from DOCX: {str(e)}")
    
    def extract_text_from_image_ocr(self, file_path: str) -> str:
        """Extract text from image using OCR."""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from image: {str(e)}")
    
    def extract_with_gemini_image_ai(self, file_path: str) -> str:
        """Extract text from image using Gemini 2.0 Flash image AI via REST API."""
        try:
            if not self.gemini_model:
                raise Exception("Gemini model not initialized")
            
            # For PDF files, convert to image first
            if file_path.lower().endswith('.pdf'):
                try:
                    # Convert PDF to image using PyMuPDF (much more reliable on Windows)
                    doc = fitz.open(file_path)
                    
                    # Process first 2 pages to avoid terms/conditions
                    max_pages = min(2, len(doc))
                    combined_images = []
                    
                    for page_num in range(max_pages):
                        page = doc[page_num]
                        
                        # Render page as image with high DPI for better quality
                        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                        pix = page.get_pixmap(matrix=mat)
                        
                        # Convert to PIL Image
                        img_data = pix.tobytes("png")
                        page_image = Image.open(io.BytesIO(img_data))
                        combined_images.append(page_image)
                    
                    doc.close()
                    
                    # For now, just use the first page image (Gemini API limitation)
                    # In the future, we could combine images or process them separately
                    image = combined_images[0]
                    print(f"Successfully converted PDF page 1 to image using PyMuPDF: {image.size} (processed {max_pages} pages)")
                    
                except Exception as pdf_error:
                    print(f"PyMuPDF conversion failed: {pdf_error}")
                    raise Exception(f"Could not convert PDF to image: {pdf_error}")
            else:
                # Load image directly
                image = Image.open(file_path)
            
            # Convert image to base64
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            # Create prompt for purchase order extraction
            prompt = """You are analyzing a purchase order document image. Extract ALL visible text exactly as it appears, preserving the layout and structure. 

Pay special attention to:
- Company names and addresses in headers/footers (HEADER COMPANY IS THE CUSTOMER)
- "Bill To", "Ship To", "Remit To", "Mail Invoice To" sections
- "Entered By", "Contact", "Buyer" information
- Phone numbers in headers
- Part numbers, descriptions, quantities, prices in line items
- Any supplier item numbers or model numbers

IMPORTANT: The company in the header/letterhead is the CUSTOMER (who issued the PO), NOT the "Ship To" company.

Return the complete text content of this document, maintaining the original formatting and structure as much as possible."""
            
            # Prepare the API request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": img_base64
                            }
                        }
                    ]
                }]
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Make the API request
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    text_content = result['candidates'][0]['content']['parts'][0]['text']
                    return text_content.strip()
                else:
                    raise Exception("No content in Gemini response")
            else:
                raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Gemini image AI failed: {e}")
            # Fall back to OCR
            return self.extract_text_from_image_ocr(file_path)
    
    def extract_addresses_with_gemini(self, file_path: str) -> Dict[str, str]:
        """
        Extract billing and shipping addresses directly from image using Gemini.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with 'billing_address' and 'shipping_address' keys
        """
        try:
            if not self.gemini_model:
                raise Exception("Gemini model not initialized")
            
            # Convert PDF to image (same as existing method)
            if file_path.lower().endswith('.pdf'):
                try:
                    doc = fitz.open(file_path)
                    page = doc[0]  # Use first page only
                    
                    # Render page as image with high DPI for better quality
                    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert to PIL Image
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    doc.close()
                    
                except Exception as pdf_error:
                    print(f"PyMuPDF conversion failed: {pdf_error}")
                    raise Exception(f"Could not convert PDF to image: {pdf_error}")
            else:
                # Load image directly
                image = Image.open(file_path)
            
            # Convert image to base64
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            # Create specific prompt for address extraction
            prompt = """Look at this purchase order image and identify the billing address and shipping address.

Return ONLY a JSON response with this exact format:
{
    "billing_address": "[full billing address here]",
    "shipping_address": "[full shipping address here]"
}

🚨🚨🚨 CRITICAL BUSINESS RULES - READ CAREFULLY 🚨🚨🚨

ABSOLUTE PROHIBITIONS:
❌ NEVER use "KOIKE" or "ARONSON" as billing address - these are SUPPLIER names
❌ NEVER use "635 WEST MAIN STREET" as billing address - this is SUPPLIER address
❌ NEVER use any address containing "KOIKE" or "ARONSON" for billing
❌ NEVER use "Ship To" company as the customer - that's just delivery location
❌ NEVER combine address lines from different sections of the document

✅ CORRECT IDENTIFICATION:
✅ The company in the header/letterhead is the CUSTOMER (who issued the PO)
✅ The "Bill To" or "Invoice To" address is the billing address
✅ The "Ship To" or "Deliver To" address is the shipping address
✅ PO Box addresses are typically billing addresses, NOT shipping addresses

ADDRESS IDENTIFICATION:
Look for labels like:
- "Bill To", "Billing Address", "Remit To", "Invoice To"
- "Ship To", "Shipping Address", "Deliver To", "Delivery Address"

The billing address is usually where invoices should be sent.
The shipping address is usually where goods should be delivered.

FORMATTING:
- Format addresses with proper line breaks: "COMPANY NAME\n123 STREET ADDRESS\nCITY, STATE ZIP"
- Extract the complete address including company name, street address, city, state, and zip code
- Use the company name from the BILLING address (the company paying for the order)

🚨 REMINDER: The header company is the customer who issued the purchase order, NOT the supplier.
🚨 If you see KOIKE or ARONSON anywhere, that is the SUPPLIER, NOT the customer billing address!"""
            
            # Prepare the API request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": img_base64
                            }
                        }
                    ]
                }]
            }
            
            response = requests.post(url, json=payload)
            result = response.json()
            
            if 'error' in result:
                raise Exception(f"Gemini API error: {result['error']['message']}")
            
            # Extract the text response
            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if parts:
                        text_response = parts[0].get('text', '')
                        
                        # Parse JSON from the response
                        import json
                        import re
                        
                        # Extract JSON from markdown code blocks if present
                        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text_response, re.DOTALL)
                        if json_match:
                            json_text = json_match.group(1)
                        else:
                            # Try to find JSON directly
                            json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
                            if json_match:
                                json_text = json_match.group(0)
                            else:
                                raise ValueError("No JSON found in Gemini response")
                        
                        addresses = json.loads(json_text)
                        
                        # Validate that we got both addresses
                        if 'billing_address' not in addresses or 'shipping_address' not in addresses:
                            raise ValueError("Missing billing or shipping address in Gemini response")
                        
                        # 🚨 CRITICAL VALIDATION: NEVER allow Koike/Aronson as billing address
                        billing_addr = addresses['billing_address'].upper()
                        if 'KOIKE' in billing_addr or 'ARONSON' in billing_addr:
                            raise ValueError(f"🚨 CRITICAL ERROR: Koike/Aronson cannot be billing address! Got: {addresses['billing_address']}")
                        
                        if '635 WEST MAIN STREET' in billing_addr:
                            raise ValueError(f"🚨 CRITICAL ERROR: Supplier address cannot be billing address! Got: {addresses['billing_address']}")
                        
                        print(f"✅ Gemini successfully extracted addresses:")
                        print(f"   Billing:  {addresses['billing_address'][:50]}...")
                        print(f"   Shipping: {addresses['shipping_address'][:50]}...")
                        
                        return addresses
            
            raise Exception("No valid response from Gemini")
            
        except Exception as e:
            print(f"Gemini address extraction failed: {e}")
            return None
    
    def extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text from various file types.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            # Try regular PDF text extraction first
            try:
                text = self.extract_text_from_pdf(file_path)
                # For PDFs with headers/images, always try image AI for better extraction
                # Even if we get some text, the header info might be missing
                
                # Always try image AI for PDFs to catch header info that's in images
                if self.gemini_model:
                    try:
                        image_text = self.extract_with_gemini_image_ai(file_path)
                        # Combine both extractions - image AI often gets header info that text extraction misses
                        combined_text = f"=== IMAGE AI EXTRACTION ===\n{image_text}\n\n=== TEXT EXTRACTION ===\n{text}"
                        return combined_text
                    except Exception as img_error:
                        return text
                else:
                    return text
            except Exception as e:
                return self.extract_with_gemini_image_ai(file_path)
                
        elif file_ext in ['.doc', '.docx']:
            return self.extract_text_from_docx(file_path)
        elif file_ext in ['.txt']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            # Use image AI for better accuracy on complex layouts
            if self.gemini_model:
                return self.extract_with_gemini_image_ai(file_path)
            else:
                return self.extract_text_from_image_ocr(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def has_selectable_text(self, file_path: str) -> bool:
        """
        Determine if file has selectable text or needs OCR.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file has selectable text, False if needs OCR
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Image files always need OCR
        if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return False
        
        # Text-based files have selectable text
        if file_ext in ['.txt', '.doc', '.docx']:
            return True
        
        # For PDFs, check if text can be extracted
        if file_ext == '.pdf':
            try:
                text = self.extract_text_from_pdf(file_path)
                # If we get substantial text, it's selectable
                return len(text.strip()) > 50
            except:
                return False
        
        return False
    
    def create_shipping_prompt(self, text: str) -> str:
        """Create AI prompt for extracting shipping information."""
        return f"""
Please extract SHIPPING information from the following text and return it as a JSON object.

The JSON should have this exact structure:
{{
    "shipping_address": "string",
    "shipping_method": "string",
    "shipping_account_number": "string",
    "delivery_instructions": "string",
    "required_date": "string",
    "ship_via_code": "string"
}}

SHIPPING ADDRESS EXTRACTION - DETERMINISTIC LABEL-BASED STRATEGY:

STEP 1 - Scan for ALL address blocks in the document:
  * Identify every complete address block (company name + street + city/state/zip)
  * Note the position of each address block (top, middle, bottom of document)

STEP 2 - Look for VERTICAL OVAL LABELS next to each address:
  * CRITICAL: Look for text in VERTICAL OVAL SHAPES positioned to the LEFT of addresses
  * These labels contain words like "SHIP TO", "INVOICE", "BILL TO", etc.
  * Labels are rotated 90 degrees with letters stacked vertically (top to bottom)
  * Scan the ENTIRE document carefully - these labels are often small and faint
  * Look for oval-shaped containers with vertical text inside them

STEP 3 - Apply label-based rules:
  * If you find "SHIP TO" label → use that address as shipping_address
  * If you find "INVOICE" or "BILL TO" label → use the OTHER address as shipping_address
  * If no clear labels found → use the address that appears LOWER on the page

PRIORITY 2 - If only ONE address has a clear label:
  * If you find "INVOICE", "BILL TO", or "REMIT TO" labeled clearly but NO shipping label → the OTHER address (unlabeled one) is the shipping address
  * Use the unlabeled address as the shipping address
  * DO NOT use the billing/invoice address as shipping

PRIORITY 3 - If NO labels are readable (last resort):
  * The address appearing FURTHER DOWN the page (not at the very top) is the SHIPPING address
  * The top address is typically the billing address
  * Extract the LOWER/SECOND address as shipping_address

UNDERSTANDING "TOP" vs "LOWER" ADDRESSES:
- The document header (near "PURCHASE ORDER" title) = TOP = typically billing
- Addresses appearing in the body of the document (below header) = LOWER = typically shipping
- Physical position matters: measure from the top of the page downward
- Example layout:
  ```
  [TOP OF PAGE]
  PURCHASE ORDER
  Company Name          ← This address block is at the TOP
  123 Main St
  City, State Zip
  
  [MIDDLE/LOWER SECTION]
  Some address block    ← This address block is LOWER on the page
  456 Other St
  Town, State Zip
  [BOTTOM OF PAGE]
  ```

DISTINGUISHING SIMILAR ADDRESSES:
- If two addresses have similar/same company names, look for key differences:
  * PO Box vs Street Address → PO Box = billing, Street = shipping
  * "Repair" vs "Supply" vs headquarters name variations
  * Different street addresses = different locations = one is shipping destination

CRITICAL RULES:
- NEVER combine address lines from different sections of the document
- Format addresses with proper line breaks between company name, street address, and city/state/zip
- Extract the complete address including company name from the shipping section
- If you extract a PO Box as shipping address, you probably made an error - check for a street address instead
- shipping_method: Extract shipping method from notes or shipping instructions and return ONLY one of these three values:
  * "GROUND" - for standard ground shipping, freight, or any slow method
  * "NEXT DAY AIR" - for overnight, same day, express, priority overnight, 1-day
  * "2ND DAY AIR" - for 2-day, second day, two day shipping
  * If nothing mentioned or unclear, default to "GROUND"
- shipping_account_number: Look for FedEx/UPS account numbers in these patterns:
  * Formal patterns: "FedEx Account:", "UPS Account:", "Account Number:", "Acct #:"
  * Informal patterns: "UPS 12345", "UPS GRD 12345", "FedEx 12345", "UPS NDA 12345"
  * Extract account numbers like "123456789", "1234-5678-9", "6754W3", "50730F"
  * Look in shipping method fields like "Ship Via: UPS GRD 50730F" or "FREIGHT COLLECT PARCEL UPS 6754W3"
  * Extract alphanumeric codes that follow "UPS" or "FedEx" keywords (e.g., after "UPS GRD" extract the account number)
  * If none found, default to "prepaid & add"
- delivery_instructions: Extract special delivery instructions:
  * Look for "Leave at door", "Signature required", "Call before delivery", etc.
- required_date: Look for delivery date requirements:
  * Look for "Need By:", "Required Date:", "Ship Date:", "Delivery Date:", "Due Date:" or "ASAP"
- ship_via_code: Extract shipping carrier codes:
  * Look for codes like "UPS", "FEDX", "GRND", "2DAY", "OVNT", etc.

General Instructions:
- Focus ONLY on shipping-related information
- If any field is not found, use empty string "" for text fields
- Ensure the JSON is valid and properly formatted
- Return ONLY the JSON, no additional text

Text to process:
{text}
"""

    def create_line_items_prompt(self, text: str) -> str:
        """Create AI prompt for extracting line items and financial totals."""
        return f"""
Please extract LINE ITEMS and FINANCIAL TOTALS from the following text and return it as a JSON object.

The JSON should have this exact structure:
{{
    "line_items": [
        {{
            "external_part_number": "string",
            "description": "string",
            "unit_price": float,
            "quantity": integer
        }}
    ],
    "subtotal": float,
    "tax_amount": float,
    "tax_rate": float,
    "grand_total": float
}}

CRITICAL INSTRUCTIONS for part numbers:
- PRIORITY ORDER for external_part_number extraction:
  1. LOGICAL PART NUMBER PATTERNS (highest priority): Look for strings that match part number patterns:
     * Alphanumeric codes: "ZTIP107D75", "107D73", "ZA3232050", "KOIZA323-2050"
     * Mixed letters/numbers: "ABC123", "X-456", "TIP#5", "107D7"
  2. LABELED PART NUMBERS (second priority): Look for explicit labels:
     * "MFG #:", "Item Number:", "Part Number:", "SKU:", etc.
  3. CONTEXTUAL EXTRACTION (third priority): Extract from logical context:
     * Near product descriptions, before/after quantities
     * In line item structures (even without "ITEM" column headers)

LOGICAL PART NUMBER IDENTIFICATION:
- Part numbers are typically: alphanumeric, contain letters AND numbers, look like codes
- Part numbers are NOT: prices ($19.80), quantities (5), dates (09/26/25), addresses
- Part numbers often contain: manufacturer codes, product type codes, size/version numbers
- If you see "TIP 107D7 #5" in description, extract "107D7" as the part number
- If you see "CUTTING TIP KOIKE #3", look for related part numbers like "107D73"

ROBUST EXTRACTION STRATEGY:
- Look for the most "part-number-like" string in each line item
- Prioritize strings that look like manufacturer codes or product identifiers
- Avoid prices, quantities, dates, and addresses
- Use context clues: part numbers are usually near product descriptions
- For description, use the full product description text
- The goal is to extract the part number that will most likely match our internal database

TOTALS AND TAX EXTRACTION:
- subtotal: Look for "Subtotal:", "Sub Total:", "Net Amount:", or calculate from line items (quantity × unit_price)
- tax_amount: Look for "Tax:", "Sales Tax:", "Tax Amount:", "GST:", "VAT:", etc. Extract the dollar amount
- tax_rate: Look for tax percentage like "8.5%", "Tax Rate:", etc. Convert to decimal (e.g., 8.5% = 8.5)
- grand_total: Look for "Total:", "Grand Total:", "Amount Due:", "Total Amount:", or calculate as subtotal + tax_amount
- If tax information is not found, set tax_amount=0.0, tax_rate=0.0
- If totals are not explicitly shown, calculate from line items: subtotal = sum(quantity × unit_price)

General Instructions:
- Focus ONLY on line items and financial totals
- Extract all line items with part numbers, descriptions, unit prices, and quantities
- If any field is not found, use empty string "" for text fields, 0.0 for prices, 0 for quantities
- Ensure the JSON is valid and properly formatted
- Return ONLY the JSON, no additional text

Text to process:
{text}
"""

    def create_billing_prompt(self, text: str) -> str:
        """Create AI prompt for extracting billing information."""
        return f"""
Please extract BILLING information from the following text and return it as a JSON object.

The JSON should have this exact structure:
{{
    "company_name": "string",
    "billing_address": "string",
    "email": "string",
    "phone_number": "string",
    "contact_person": "string",
    "contact_person_email": "string",
    "customer_po_number": "string",
    "po_date": "string",
    "notes": "string"
}}

BILLING ADDRESS EXTRACTION - DETERMINISTIC LABEL-BASED STRATEGY:

STEP 1 - Scan for ALL address blocks in the document:
  * Identify every complete address block (company name + street + city/state/zip)
  * Note the position of each address block (top, middle, bottom of document)

STEP 2 - Look for VERTICAL OVAL LABELS next to each address:
  * CRITICAL: Look for text in VERTICAL OVAL SHAPES positioned to the LEFT of addresses
  * These labels contain words like "INVOICE", "BILL TO", "SHIP TO", etc.
  * Labels are rotated 90 degrees with letters stacked vertically (top to bottom)
  * Scan the ENTIRE document carefully - these labels are often small and faint
  * Look for oval-shaped containers with vertical text inside them

STEP 3 - Apply label-based rules:
  * If you find "INVOICE" or "BILL TO" label → use that address as billing_address
  * If you find "SHIP TO" label → use the OTHER address as billing_address
  * If no clear labels found → use the address that appears HIGHER on the page

PRIORITY 2 - If only ONE address has a clear label:
  * If you find "SHIP TO" labeled clearly but NO billing label → the OTHER address (unlabeled one) is the billing address
  * Use the unlabeled address as the billing address
  * DO NOT use the "SHIP TO" address as billing

PRIORITY 3 - If NO labels are readable (last resort):
  * The address appearing CLOSEST TO THE TOP of the document is the BILLING address
  * Companies typically place their own (billing) information at the top of their purchase orders
  * The address appearing FURTHER DOWN the page would be the shipping address
  * Extract the TOP address as billing_address

UNDERSTANDING "TOP" vs "LOWER" ADDRESSES:
- The document header (near "PURCHASE ORDER" title) = TOP = typically billing
- Addresses appearing in the body of the document (below header) = LOWER = typically shipping
- Physical position matters: measure from the top of the page downward
- Example layout:
  ```
  [TOP OF PAGE]
  PURCHASE ORDER
  Company Name          ← This address block is at the TOP (billing)
  123 Main St
  City, State Zip
  
  [MIDDLE/LOWER SECTION]
  Some address block    ← This address block is LOWER on the page (shipping)
  456 Other St
  Town, State Zip
  [BOTTOM OF PAGE]
  ```

DISTINGUISHING SIMILAR ADDRESSES:
- If two addresses have similar/same company names, look for key differences:
  * PO Box vs Street Address → PO Box = billing, Street = shipping
  * "Repair" vs "Supply" vs headquarters name variations
  * Different street addresses = different locations = determine which is billing vs shipping based on position/labels

CRITICAL RULES:
- company_name: Use the company name from the BILLING address (the company paying for the order)
- NEVER use "Ship To" company as the customer - that's just where it's being delivered
- IGNORE any addresses with "KOIKE", "ARONSON", "635 WEST MAIN STREET" - these are supplier info
- NEVER combine address lines from different sections of the document
- Format addresses with proper line breaks between company name, street address, and city/state/zip
- PO Box addresses are typically billing addresses, NOT shipping addresses

PURCHASE ORDER DETAILS EXTRACTION:
- customer_po_number: Look for "PURCHASE ORDER:", "P/O NO:", "PO Number:", "Purchase Order No:", "Order No:", or similar labels
  * CRITICAL: Look specifically for "PURCHASE ORDER:" followed by a number - this is usually the main PO number
  * PRIORITY RULES: If multiple PO numbers are found, prioritize in this order:
    1. The number directly after "PURCHASE ORDER:" label
    2. Numeric PO numbers (like "12345678") over text references (like "ABC")
    3. Longer numbers over shorter ones
    4. Numbers near the document header over those in customer reference sections
  * IGNORE these numbers (they are NOT the customer PO number):
    - Vendor numbers (like "VENDOR NO: KOIK")
    - Page numbers (like "PAGE NO: 01")
    - Reference numbers that are not labeled as purchase order numbers
  * Look for labeled sections with clear indicators like "PURCHASE ORDER:", "P/O NO:", "PO Number:", etc.
  * The customer PO number is typically the main order number, not vendor references or page numbers
- po_date: Look for "P/O DATE:", "PO Date:", "DATE:", "Date:", "Order Date:", or similar labels. Format as MM/DD/YYYY if possible
  * The date is typically near the purchase order number in the document header
  * Look for date patterns like MM/DD/YY, MM/DD/YYYY, or MM-DD-YY
- notes: Extract shipping instructions, payment terms, delivery dates, and any other important information:
  * Shipping method: "GROUND", "FREIGHT", "OVERNIGHT", "2-DAY", etc.
  * Payment terms: "NET 30", "COD", "PREPAID", etc.
  * Delivery dates: Look for "Need By:", "Required Date:", "Ship Date:", "Delivery Date:", "Due Date:" or "ASAP"
  * Special instructions: "Please ship ground", "Duplicate", "Rush order", etc.
  * Combine all relevant notes into a single field, separated by semicolons

General Instructions:
- Extract CUSTOMER company information (the buyer, not Koike the supplier)
- Focus ONLY on billing-related information
- If any field is not found, use empty string "" for text fields
- Ensure the JSON is valid and properly formatted
- Return ONLY the JSON, no additional text

Text to process:
{text}
"""
    
    def process_with_ai_parallel(self, text: str, file_path: str = None) -> Dict[str, Any]:
        """
        Process text using OpenAI API with parallel specialized prompts.
        
        Args:
            text: Raw text from document
            
        Returns:
            Structured purchase order data as dictionary
        """
        if not self.client:
            # Return a fallback structure if no OpenAI client is available
            print("Warning: No OpenAI API key provided. Using fallback data structure.")
            return self._create_fallback_structure()
        
        try:
            print("🔄 Using SPLIT PROMPT approach (3 specialized prompts in parallel)...")
            
            # Create the three specialized prompts
            shipping_prompt = self.create_shipping_prompt(text)
            line_items_prompt = self.create_line_items_prompt(text)
            billing_prompt = self.create_billing_prompt(text)
            
            # Execute all three prompts in parallel
            import concurrent.futures
            import threading
            
            def call_openai(prompt, prompt_type):
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": f"You are an expert at extracting {prompt_type} from purchase orders. Return only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=1500,
                        temperature=0.0
                    )
                    
                    result_text = response.choices[0].message.content.strip()
                    
                    # Try to parse as JSON
                    try:
                        return json.loads(result_text)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, try to extract JSON from the response
                        start = result_text.find('{')
                        end = result_text.rfind('}') + 1
                        if start != -1 and end != -1:
                            json_text = result_text[start:end]
                            return json.loads(json_text)
                        else:
                            raise ValueError(f"Could not extract valid JSON from {prompt_type} response")
                            
                except Exception as e:
                    print(f"Error in {prompt_type} extraction: {str(e)}")
                    return None
            
            # Execute all prompts in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all three tasks
                shipping_future = executor.submit(call_openai, shipping_prompt, "shipping")
                line_items_future = executor.submit(call_openai, line_items_prompt, "line items and totals")
                billing_future = executor.submit(call_openai, billing_prompt, "billing")
                
                # Wait for all results
                shipping_result = shipping_future.result()
                line_items_result = line_items_future.result()
                billing_result = billing_future.result()
            
            # Validate that we got at least some results
            if not any([shipping_result, line_items_result, billing_result]):
                raise Exception("All parallel extraction attempts failed")
            
            # Merge the results into the expected structure
            merged_result = self._merge_extraction_results(shipping_result, line_items_result, billing_result, text)
            
            # Validate the merged structure
            self._validate_merged_structure(merged_result, raw_text=text, file_path=file_path)
            
            print("✅ Split prompt approach completed successfully!")
            return merged_result
                    
        except Exception as e:
            print(f"❌ Split prompt extraction failed: {str(e)}")
            print("🔄 Falling back to MONOLITHIC approach...")
            return self.process_with_ai_fallback(text, file_path)
    
    def process_with_ai_fallback(self, text: str, file_path: str = None) -> Dict[str, Any]:
        """
        Fallback method using the original monolithic prompt approach.
        
        Args:
            text: Raw text from document
            
        Returns:
            Structured purchase order data as dictionary
        """
        if not self.client:
            return self._create_fallback_structure()
        
        try:
            print("📝 Using MONOLITHIC FALLBACK approach (single large prompt)...")
            
            # Use the original monolithic prompt (recreated for fallback)
            prompt = f"""
Please extract purchase order information from the following text and return it as a JSON object.

The JSON should have this exact structure:
{{
    "company_info": {{
        "company_name": "string",
        "billing_address": "string",
        "shipping_address": "string",
        "email": "string",
        "phone_number": "string",
        "contact_person": "string",
        "contact_person_email": "string",
        "customer_po_number": "string",
        "po_date": "string",
        "notes": "string",
        "subtotal": float,
        "tax_amount": float,
        "tax_rate": float,
        "grand_total": float,
        "shipping_method": "string",
        "shipping_account_number": "string"
    }},
    "line_items": [
        {{
            "external_part_number": "string",
            "description": "string",
            "unit_price": float,
            "quantity": integer
        }}
    ]
}}

COMPANY INFORMATION EXTRACTION - MULTI-LEVEL FALLBACK STRATEGY:

BILLING ADDRESS:
PRIORITY 1 - Look for explicit labels:
  * Look for sections labeled "INVOICE", "BILL TO", "REMIT TO", or "MAIL INVOICE TO"
  * These labels may be vertical, rotated, in ovals/boxes, or faint
  * Extract the complete address from the labeled section ONLY

PRIORITY 2 - If only ONE address has a clear label:
  * If you find "SHIP TO" labeled clearly but NO billing label → the OTHER address (unlabeled one) is the billing address
  * Use the unlabeled address as the billing address

PRIORITY 3 - If NO labels are readable (last resort):
  * The address appearing CLOSEST TO THE TOP of the document is the BILLING address
  * Companies typically place their own (billing) information at the top of their purchase orders

SHIPPING ADDRESS:
PRIORITY 1 - Look for explicit labels:
  * Look for sections labeled "SHIP TO", "DELIVER TO", or "DELIVERY ADDRESS"
  * These labels may be vertical, rotated, in ovals/boxes, or faint - LOOK CAREFULLY
  * Check the LEFT SIDE of addresses for vertical labels in ovals
  * Extract the complete address from the labeled section ONLY

PRIORITY 2 - If only ONE address has a clear label:
  * If you find "INVOICE"/"BILL TO" labeled clearly but NO shipping label → the OTHER address (unlabeled one) is the shipping address

PRIORITY 3 - If NO labels are readable (last resort):
  * The address appearing FURTHER DOWN the page (not at the very top) is the SHIPPING address

UNDERSTANDING "TOP" vs "LOWER" ADDRESSES:
- The document header (near "PURCHASE ORDER" title) = TOP = typically billing
- Addresses appearing in the body of the document (below header) = LOWER = typically shipping
- Physical position matters: measure from the top of the page downward
- Example layout:
  ```
  [TOP OF PAGE]
  PURCHASE ORDER
  Company Name          ← This address block is at the TOP (billing)
  123 Main St
  City, State Zip
  
  [MIDDLE/LOWER SECTION]
  Some address block    ← This address block is LOWER on the page (shipping)
  456 Other St
  Town, State Zip
  [BOTTOM OF PAGE]
  ```

DISTINGUISHING SIMILAR ADDRESSES:
- If two addresses have similar/same company names, look for key differences:
  * PO Box vs Street Address → PO Box = billing, Street = shipping
  * "Repair" vs "Supply" vs headquarters name variations
  * Different street addresses = different locations = one is billing, other is shipping

CRITICAL RULES:
- company_name: Use the company name from the BILLING address (the company paying for the order)
- NEVER use "Ship To" company as the customer - that's just where it's being delivered
- IGNORE any addresses with "KOIKE", "ARONSON", "635 WEST MAIN STREET" - these are supplier info
- NEVER combine address lines from different sections of the document
- Format addresses with proper line breaks: "COMPANY NAME\n123 STREET ADDRESS\nCITY, STATE ZIP"
- PO Box addresses are typically billing addresses, NOT shipping addresses
- If you extract a PO Box as shipping address, you probably made an error - check for a street address instead

CRITICAL INSTRUCTIONS for part numbers:
- PRIORITY ORDER for external_part_number extraction:
  1. LOGICAL PART NUMBER PATTERNS (highest priority): Look for strings that match part number patterns:
     * Alphanumeric codes: "ZTIP107D75", "107D73", "ZA3232050", "KOIZA323-2050"
     * Mixed letters/numbers: "ABC123", "X-456", "TIP#5", "107D7"
     * Manufacturer prefixes: "KOI", "ZTIP", "ABC", "XYZ" followed by numbers
     * Common part patterns: "107D7", "TIP", "CUTTING", "VALVE", "FILTER" + numbers
  2. LABELED PART NUMBERS (second priority): Look for explicit labels:
     * "MFG #:", "Item Number:", "Part Number:", "SKU:", etc.
  3. CONTEXTUAL EXTRACTION (third priority): Extract from logical context:
     * Near product descriptions, before/after quantities
     * In line item structures (even without "ITEM" column headers)

LOGICAL PART NUMBER IDENTIFICATION:
- Part numbers are typically: alphanumeric, contain letters AND numbers, look like codes
- Part numbers are NOT: prices ($19.80), quantities (5), dates (09/26/25), addresses
- Part numbers often contain: manufacturer codes, product type codes, size/version numbers
- If you see "TIP 107D7 #5" in description, extract "107D7" as the part number
- If you see "CUTTING TIP KOIKE #3", look for related part numbers like "107D73"

ROBUST EXTRACTION STRATEGY:
- Look for the most "part-number-like" string in each line item
- Prioritize strings that look like manufacturer codes or product identifiers
- Avoid prices, quantities, dates, and addresses
- Use context clues: part numbers are usually near product descriptions
- For description, use the full product description text
- The goal is to extract the part number that will most likely match our internal database

PURCHASE ORDER DETAILS EXTRACTION:
- customer_po_number: Look for "PURCHASE ORDER:", "P/O NO:", "PO Number:", "Purchase Order No:", "Order No:", or similar labels
  * CRITICAL: Look specifically for "PURCHASE ORDER:" followed by a number - this is usually the main PO number
  * PRIORITY RULES: If multiple PO numbers are found, prioritize in this order:
    1. The number directly after "PURCHASE ORDER:" label
    2. Numeric PO numbers (like "12345678") over text references (like "ABC")
    3. Longer numbers over shorter ones
    4. Numbers near the document header over those in customer reference sections
  * IGNORE these numbers (they are NOT the customer PO number):
    - Vendor numbers (like "VENDOR NO: KOIK")
    - Page numbers (like "PAGE NO: 01")
    - Reference numbers that are not labeled as purchase order numbers
  * Look for labeled sections with clear indicators like "PURCHASE ORDER:", "P/O NO:", "PO Number:", etc.
  * The customer PO number is typically the main order number, not vendor references or page numbers
- po_date: Look for "P/O DATE:", "PO Date:", "DATE:", "Date:", "Order Date:", or similar labels. Format as MM/DD/YYYY if possible
  * The date is typically near the purchase order number in the document header
  * Look for date patterns like MM/DD/YY, MM/DD/YYYY, or MM-DD-YY
- notes: Extract shipping instructions, payment terms, delivery dates, and any other important information:
  * Shipping method: "GROUND", "FREIGHT", "OVERNIGHT", "2-DAY", etc.
  * Payment terms: "NET 30", "COD", "PREPAID", etc.
  * Delivery dates: Look for "Need By:", "Required Date:", "Ship Date:", "Delivery Date:", "Due Date:" or "ASAP"
  * Special instructions: "Please ship ground", "Duplicate", "Rush order", etc.
  * Combine all relevant notes into a single field, separated by semicolons

TOTALS AND TAX EXTRACTION:
- subtotal: Look for "Subtotal:", "Sub Total:", "Net Amount:", or calculate from line items (quantity × unit_price)
- tax_amount: Look for "Tax:", "Sales Tax:", "Tax Amount:", "GST:", "VAT:", etc. Extract the dollar amount
- tax_rate: Look for tax percentage like "8.5%", "Tax Rate:", etc. Convert to decimal (e.g., 8.5% = 8.5)
- grand_total: Look for "Total:", "Grand Total:", "Amount Due:", "Total Amount:", or calculate as subtotal + tax_amount
- If tax information is not found, set tax_amount=0.0, tax_rate=0.0
- If totals are not explicitly shown, calculate from line items: subtotal = sum(quantity × unit_price)

SHIPPING METHOD AND ACCOUNT EXTRACTION:
- shipping_method: Extract shipping method and return ONLY one of these three values:
  * "GROUND" - for standard ground shipping, freight, or any slow method
  * "NEXT DAY AIR" - for overnight, same day, express, priority overnight, 1-day
  * "2ND DAY AIR" - for 2-day, second day, two day shipping
  * If nothing mentioned or unclear, default to "GROUND"
- shipping_account_number: Look for FedEx/UPS account numbers in these patterns:
  * Formal patterns: "FedEx Account:", "UPS Account:", "Account Number:", "Acct #:"
  * Informal patterns: "UPS 12345", "UPS GRD 12345", "FedEx 12345", "UPS NDA 12345"
  * Extract account numbers like "123456789", "1234-5678-9", "6754W3", "50730F"
  * Look in shipping method fields like "Ship Via: UPS GRD 50730F" or "FREIGHT COLLECT PARCEL UPS 6754W3"
  * Extract alphanumeric codes that follow "UPS" or "FedEx" keywords (e.g., after "UPS GRD" extract the account number)
  * If none found, default to "prepaid & add"

General Instructions:
- Extract CUSTOMER company information (the buyer, not Koike the supplier)
- Extract all line items with part numbers, descriptions, unit prices, and quantities
- If any field is not found, use empty string "" for text fields, 0.0 for prices, 0 for quantities
- For shipping_method and shipping_account_number, use the defaults specified above if not found
- Ensure the JSON is valid and properly formatted
- Return ONLY the JSON, no additional text

Text to process:
{text}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from purchase orders. You excel at differentiating between customer information and vendor/supplier information. Always separate addresses completely - never mix parts from different address sections. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.0
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the response
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_text = result_text[start:end]
                    return json.loads(json_text)
                else:
                    raise ValueError("Could not extract valid JSON from AI response")
            
            print("✅ Monolithic fallback approach completed successfully!")
            return json.loads(result_text)
                    
        except Exception as e:
            print(f"❌ Monolithic fallback failed: {str(e)}")
            raise Exception(f"Error processing with AI fallback: {str(e)}")
    
    def process_with_ai(self, text: str, file_path: str = None) -> Dict[str, Any]:
        """
        Main method to process text using AI - tries parallel approach first, falls back to monolithic.
        
        Args:
            text: Raw text from document
            
        Returns:
            Structured purchase order data as dictionary
        """
        try:
            return self.process_with_ai_parallel(text, file_path)
        except Exception as e:
            print(f"Parallel processing failed: {str(e)}")
            return self.process_with_ai_fallback(text, file_path)
    
    def _create_fallback_structure(self) -> Dict[str, Any]:
        """Create a fallback data structure when API is unavailable."""
        return {
            "company_info": {
                "company_name": "Sample Company",
                "billing_address": "123 Main St, City, State 12345",
                "shipping_address": "",
                "email": "contact@company.com",
                "phone_number": "555-123-4567",
                "contact_person": "John Doe",
                "contact_person_email": "john@company.com",
                "customer_po_number": "",
                "po_date": "",
                "notes": "",
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "tax_rate": 0.0,
                "grand_total": 0.0,
                "shipping_method": "GROUND",
                "shipping_account_number": "prepaid & add"
            },
            "line_items": [
                {
                    "external_part_number": "EXT-001",
                    "description": "Sample Part Description",
                    "unit_price": 25.50,
                    "quantity": 10
                }
            ]
        }
    
    def _has_multiple_pos(self, text: str) -> bool:
        """
        Check if the document contains multiple PO numbers in different locations.
        If multiple POs found, use the one highest on the page.
        
        Args:
            text: Raw text from the document
            
        Returns:
            True if multiple unique PO numbers are found in different locations, False otherwise
        """
        import re
        
        # PO number patterns with position tracking
        po_patterns = [
            (r'PO\s*#?\s*:?\s*(\d+)', 'PO #'),
            (r'P\.O\.\s*#?\s*:?\s*(\d+)', 'P.O. #'),
            (r'Purchase\s+Order\s*#?\s*:?\s*(\d+)', 'Purchase Order #'),
            (r'Order\s*#?\s*:?\s*(\d+)', 'Order #'),
            (r'PO\s+Number\s*:?\s*(\d+)', 'PO Number'),
            (r'P\.O\.\s+Number\s*:?\s*(\d+)', 'P.O. Number'),
            (r'(\d+)\s+OD', 'OD Pattern'),  # Pattern like "77673596 OD"
            (r'Customer\s+PO#\s*(\d+)', 'Customer PO#'),  # Customer PO pattern
            (r'Purchase\s+Order\s+Number\s*(\d+)', 'Purchase Order Number')  # Full pattern
        ]
        
        found_pos = []
        for pattern, label in po_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                po_number = match.group(1)
                if len(po_number) >= 4:  # Filter out very short numbers
                    # Get the line number (approximate position)
                    line_num = text[:match.start()].count('\n')
                    found_pos.append({
                        'number': po_number,
                        'position': line_num,
                        'label': label,
                        'context': text[max(0, match.start()-20):match.end()+20]
                    })
        
        # Remove duplicates by PO number
        unique_pos = {}
        for po_info in found_pos:
            po_num = po_info['number']
            if po_num not in unique_pos or po_info['position'] < unique_pos[po_num]['position']:
                unique_pos[po_num] = po_info
        
        unique_pos_list = list(unique_pos.values())
        
        # Sort by position (highest on page first)
        unique_pos_list.sort(key=lambda x: x['position'])
        
        print(f"  🔍 PO Detection Results:")
        for i, po_info in enumerate(unique_pos_list, 1):
            print(f"    {i}. {po_info['number']} (line {po_info['position']}, {po_info['label']})")
            print(f"       Context: {po_info['context'].strip()}")
        
        # If multiple POs found, check if they're in significantly different locations
        if len(unique_pos_list) > 1:
            # Check if POs are in different sections (more than 10 lines apart)
            positions = [po['position'] for po in unique_pos_list]
            min_pos = min(positions)
            max_pos = max(positions)
            
            if max_pos - min_pos > 10:  # POs are in different sections
                print(f"  ⚠️  MULTIPLE POs in different locations detected!")
                print(f"     Using highest PO: {unique_pos_list[0]['number']}")
                return True
            else:
                print(f"  ✅ Multiple POs found but in same section - using highest: {unique_pos_list[0]['number']}")
                return False
        
        return False
    
    def _get_best_po_number(self, text: str, ai_extracted_po: str) -> str:
        """
        CONSERVATIVE approach: Only check for multiple POs if there are clear indicators.
        Default to AI-extracted PO unless there's obvious evidence of multiple POs.
        
        Args:
            text: Raw text from the document
            ai_extracted_po: PO number extracted by AI
            
        Returns:
            Best PO number to use
        """
        import re
        
        # Only look for multiple POs if there are clear indicators
        multiple_po_indicators = [
            r'REVISION\s+TO\s+ORIGINAL\s+PO',
            r'Purchase\s+Order\s+Number.*OD',
            r'Customer\s+PO#',
            r'Original\s+PO.*Revision'
        ]
        
        has_multiple_indicators = any(re.search(pattern, text, re.IGNORECASE) for pattern in multiple_po_indicators)
        
        if not has_multiple_indicators:
            # No clear indicators of multiple POs - use AI extracted PO
            print(f"  ✅ No multiple PO indicators found - using AI extracted PO: {ai_extracted_po}")
            return ai_extracted_po
        
        print(f"  🔍 Multiple PO indicators detected - checking for additional POs...")
        
        # Very strict patterns - only look for obvious PO numbers
        strict_po_patterns = [
            (r'Purchase\s+Order\s+Number\s+(\d+)\s+OD', 'Purchase Order Number OD'),
            (r'Customer\s+PO#\s+(\d+)', 'Customer PO#'),
            (r'PO\s+Number\s+(\d+)', 'PO Number'),
            (r'Purchase\s+Order\s+Number\s+(\d+)', 'Purchase Order Number')
        ]
        
        found_pos = []
        for pattern, label in strict_po_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                po_number = match.group(1)
                if len(po_number) >= 4:  # Filter out very short numbers
                    # Get the line number (approximate position)
                    line_num = text[:match.start()].count('\n')
                    found_pos.append({
                        'number': po_number,
                        'position': line_num,
                        'label': label,
                        'context': text[max(0, match.start()-20):match.end()+20]
                    })
        
        # Remove duplicates by PO number
        unique_pos = {}
        for po_info in found_pos:
            po_num = po_info['number']
            if po_num not in unique_pos or po_info['position'] < unique_pos[po_num]['position']:
                unique_pos[po_num] = po_info
        
        unique_pos_list = list(unique_pos.values())
        
        # Sort by position (highest on page first)
        unique_pos_list.sort(key=lambda x: x['position'])
        
        print(f"  🔍 Strict PO Detection Results:")
        for i, po_info in enumerate(unique_pos_list, 1):
            print(f"    {i}. {po_info['number']} (line {po_info['position']}, {po_info['label']})")
            print(f"       Context: {po_info['context'].strip()}")
        
        # If multiple POs found, check if they're in significantly different locations
        if len(unique_pos_list) > 1:
            # Check if POs are in different sections (more than 10 lines apart)
            positions = [po['position'] for po in unique_pos_list]
            min_pos = min(positions)
            max_pos = max(positions)
            
            if max_pos - min_pos > 10:  # POs are in different sections
                print(f"  ⚠️  MULTIPLE POs in different locations detected!")
                print(f"     Marking as MISSING for manual review")
                return "MISSING"  # Mark as MISSING for manual review
            else:
                print(f"  ✅ Multiple POs found but in same section - using highest: {unique_pos_list[0]['number']}")
                return unique_pos_list[0]['number']
        
        # If only one PO found, use it
        if len(unique_pos_list) == 1:
            print(f"  ✅ Single PO found: {unique_pos_list[0]['number']}")
            return unique_pos_list[0]['number']
        
        # Fallback to AI extracted PO
        print(f"  ✅ No additional POs found - using AI extracted PO: {ai_extracted_po}")
        return ai_extracted_po
    
    def _normalize_shipping_method(self, shipping_method: str) -> str:
        """
        Normalize shipping method to ONLY allowed values: GROUND, NEXT DAY AIR, 2ND DAY AIR.
        
        Args:
            shipping_method: Raw shipping method from extraction
            
        Returns:
            Normalized shipping method (one of three allowed values)
        """
        if not shipping_method:
            return "GROUND"
        
        method = shipping_method.upper().strip()
        
        # Check for NEXT DAY AIR variations
        next_day_patterns = ['NEXT DAY', 'NDA', 'OVERNIGHT', 'SAME DAY', '1 DAY', '1DAY', 'EXPRESS', 'PRIORITY OVERNIGHT']
        if any(pattern in method for pattern in next_day_patterns):
            return "NEXT DAY AIR"
        
        # Check for 2ND DAY AIR variations
        second_day_patterns = ['2ND DAY', '2 DAY', '2DAY', 'SECOND DAY', 'TWO DAY']
        if any(pattern in method for pattern in second_day_patterns):
            return "2ND DAY AIR"
        
        # Default to GROUND for everything else
        # (includes: GROUND, FREIGHT, STANDARD, UPS, FEDEX, etc.)
        return "GROUND"
    
    def _merge_extraction_results(self, shipping_result: Optional[Dict], line_items_result: Optional[Dict], billing_result: Optional[Dict], text: str = "") -> Dict[str, Any]:
        """
        Merge results from the three specialized prompts into the expected structure.
        
        Args:
            shipping_result: Result from shipping prompt
            line_items_result: Result from line items prompt  
            billing_result: Result from billing prompt
            
        Returns:
            Merged result in expected format
        """
        # Initialize the result structure
        merged = {
            "company_info": {
                "company_name": "",
                "billing_address": "",
                "shipping_address": "",
                "email": "",
                "phone_number": "",
                "contact_person": "",
                "contact_person_email": "",
                "customer_po_number": "",
                "po_date": "",
                "notes": "",
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "tax_rate": 0.0,
                "grand_total": 0.0,
                "shipping_method": "GROUND",
                "shipping_account_number": "prepaid & add"
            },
            "line_items": []
        }
        
        # Merge billing information
        if billing_result:
            if "company_name" in billing_result:
                merged["company_info"]["company_name"] = billing_result["company_name"]
            if "billing_address" in billing_result:
                merged["company_info"]["billing_address"] = billing_result["billing_address"]
            if "email" in billing_result:
                merged["company_info"]["email"] = billing_result["email"]
            if "phone_number" in billing_result:
                merged["company_info"]["phone_number"] = billing_result["phone_number"]
            if "contact_person" in billing_result:
                merged["company_info"]["contact_person"] = billing_result["contact_person"]
            if "contact_person_email" in billing_result:
                merged["company_info"]["contact_person_email"] = billing_result["contact_person_email"]
            if "customer_po_number" in billing_result:
                # Check for multiple POs and use the best one
                po_number = billing_result["customer_po_number"]
                best_po = self._get_best_po_number(text, po_number)
                merged["company_info"]["customer_po_number"] = best_po
            if "po_date" in billing_result:
                merged["company_info"]["po_date"] = billing_result["po_date"]
            if "notes" in billing_result:
                merged["company_info"]["notes"] = billing_result["notes"]
        
        # Merge shipping information
        if shipping_result:
            if "shipping_address" in shipping_result:
                merged["company_info"]["shipping_address"] = shipping_result["shipping_address"]
            
            # Extract shipping method and account number for OrderHed
            if "shipping_method" in shipping_result and shipping_result["shipping_method"]:
                # Normalize to only allowed values: GROUND, NEXT DAY AIR, 2ND DAY AIR
                merged["company_info"]["shipping_method"] = self._normalize_shipping_method(shipping_result["shipping_method"])
            if "shipping_account_number" in shipping_result and shipping_result["shipping_account_number"]:
                merged["company_info"]["shipping_account_number"] = shipping_result["shipping_account_number"]
            
            # Add other shipping-specific fields to notes if they exist
            shipping_notes = []
            if "required_date" in shipping_result and shipping_result["required_date"]:
                shipping_notes.append(f"REQUIRED DATE: {shipping_result['required_date']}")
            if "delivery_instructions" in shipping_result and shipping_result["delivery_instructions"]:
                shipping_notes.append(f"DELIVERY INSTRUCTIONS: {shipping_result['delivery_instructions']}")
            
            # Append shipping notes to existing notes
            if shipping_notes:
                existing_notes = merged["company_info"]["notes"]
                if existing_notes:
                    merged["company_info"]["notes"] = existing_notes + "; " + "; ".join(shipping_notes)
                else:
                    merged["company_info"]["notes"] = "; ".join(shipping_notes)
        
        # Merge line items and financial information
        if line_items_result:
            if "line_items" in line_items_result:
                merged["line_items"] = line_items_result["line_items"]
            if "subtotal" in line_items_result:
                merged["company_info"]["subtotal"] = line_items_result["subtotal"]
            if "tax_amount" in line_items_result:
                merged["company_info"]["tax_amount"] = line_items_result["tax_amount"]
            if "tax_rate" in line_items_result:
                merged["company_info"]["tax_rate"] = line_items_result["tax_rate"]
            if "grand_total" in line_items_result:
                merged["company_info"]["grand_total"] = line_items_result["grand_total"]
        
        return merged
    
    def _validate_merged_structure(self, data: Dict[str, Any], raw_text: str = None, file_path: str = None) -> None:
        """
        Validate the merged structure and perform cross-checks between prompts.
        
        Args:
            data: The merged data to validate
            raw_text: Raw text from document (for voting mechanism)
        """
        # Basic structure validation
        if "company_info" not in data:
            raise ValueError("Missing company_info in merged result")
        if "line_items" not in data:
            raise ValueError("Missing line_items in merged result")
        
        # Cross-validation checks
        self._cross_validate_addresses(data, raw_text=raw_text)
        self._cross_validate_financials(data)
        
        # Set default values for missing fields
        self._set_default_values(data)
    
    def _cross_validate_addresses(self, data: Dict[str, Any], raw_text: str = None) -> None:
        """Cross-validate address information between prompts."""
        import re
        
        company_info = data.get("company_info", {})
        billing_address = company_info.get("billing_address", "")
        shipping_address = company_info.get("shipping_address", "")
        
        # Check for PO Box in shipping address (almost certainly wrong!)
        if shipping_address and re.search(r'\bP\.?O\.?\s+BOX\b', shipping_address, re.IGNORECASE):
            print("⚠️  WARNING: Shipping address contains PO BOX (almost certainly wrong)!")
            print(f"   Shipping Address: {shipping_address}")
            print("   → Gemini should have provided correct addresses - please verify")
        
        # Check for consistency issues
        if billing_address and shipping_address:
            # If addresses are EXACTLY identical, log a warning
            if billing_address.strip() == shipping_address.strip():
                print("⚠️  WARNING: Billing and shipping addresses are IDENTICAL!")
                print(f"   Address: {billing_address}")
                print("   → Gemini should have provided correct addresses - please verify")
                    
            # If addresses are very similar, log a warning
            elif billing_address.replace(" ", "").upper() in shipping_address.replace(" ", "").upper():
                print("⚠️  WARNING: Billing and shipping addresses appear very similar - please verify")
                print(f"   Billing:  {billing_address}")
                print(f"   Shipping: {shipping_address}")
    
    
    def _cross_validate_financials(self, data: Dict[str, Any]) -> None:
        """Cross-validate financial calculations."""
        company_info = data.get("company_info", {})
        line_items = data.get("line_items", [])
        
        # Calculate expected totals from line items
        calculated_subtotal = 0.0
        for item in line_items:
            quantity = item.get("quantity", 0)
            unit_price = item.get("unit_price", 0.0)
            calculated_subtotal += quantity * unit_price
        
        # Compare with extracted totals
        extracted_subtotal = company_info.get("subtotal", 0.0)
        tax_amount = company_info.get("tax_amount", 0.0)
        grand_total = company_info.get("grand_total", 0.0)
        
        # Check for significant discrepancies
        if calculated_subtotal > 0 and extracted_subtotal > 0:
            difference = abs(calculated_subtotal - extracted_subtotal)
            if difference > 0.01:  # More than 1 cent difference
                print(f"Warning: Subtotal mismatch - Calculated: {calculated_subtotal:.2f}, Extracted: {extracted_subtotal:.2f}")
        
        # Check grand total calculation
        expected_grand_total = calculated_subtotal + tax_amount
        if expected_grand_total > 0 and grand_total > 0:
            difference = abs(expected_grand_total - grand_total)
            if difference > 0.01:
                print(f"Warning: Grand total mismatch - Expected: {expected_grand_total:.2f}, Extracted: {grand_total:.2f}")
    
    def _set_default_values(self, data: Dict[str, Any]) -> None:
        """Set default values for missing fields."""
        company_info = data.get("company_info", {})
        
        # Set default values for missing string fields
        string_fields = ['company_name', 'billing_address', 'shipping_address', 'email', 'phone_number', 
                        'contact_person', 'contact_person_email', 'customer_po_number', 'po_date', 'notes',
                        'shipping_method', 'shipping_account_number']
        for field in string_fields:
            if field not in company_info:
                if field == 'shipping_method':
                    company_info[field] = "GROUND"
                elif field == 'shipping_account_number':
                    company_info[field] = "prepaid & add"
                else:
                    company_info[field] = ""
        
        # Set default values for missing numeric fields
        numeric_fields = ['subtotal', 'tax_amount', 'tax_rate', 'grand_total']
        for field in numeric_fields:
            if field not in company_info:
                company_info[field] = 0.0
        
        # Ensure line_items is a list
        if not isinstance(data.get("line_items"), list):
            data["line_items"] = []
        
        # Set default values for line items
        for item in data["line_items"]:
            item_fields = ['external_part_number', 'description']
            for field in item_fields:
                if field not in item:
                    item[field] = ""
            
            if "unit_price" not in item:
                item["unit_price"] = 0.0
            if "quantity" not in item:
                item["quantity"] = 0

    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Main method to process a document and extract purchase order data.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Structured purchase order data as dictionary
        """
        try:
            # Step 1: Extract text from document
            text = self.extract_text_from_file(file_path)
            
            if not text or len(text.strip()) < 10:
                raise ValueError("No meaningful text could be extracted from the document")
            
            # Step 2: Process with AI to get structured data
            structured_data = self.process_with_ai(text, file_path)
            
            # Step 2.5: Use Gemini to extract addresses with IMMEDIATE VALIDATION and retry logic
            print("🔍 Using Gemini to extract addresses with validation...")
            gemini_addresses = self.extract_addresses_with_validation_retry(file_path)
            if gemini_addresses:
                # Override the addresses with Gemini's validated extraction
                company_info = structured_data.get('company_info', {})
                company_info['billing_address'] = gemini_addresses['billing_address']
                company_info['shipping_address'] = gemini_addresses['shipping_address']
                print("✅ Addresses updated with validated Gemini extraction")
            else:
                print("⚠️  Address extraction with validation failed - using MISSING values")
                company_info = structured_data.get('company_info', {})
                company_info['billing_address'] = "MISSING"
                company_info['shipping_address'] = "MISSING"
            
            # Store file path and raw text for voting mechanism
            structured_data['_file_path'] = file_path
            structured_data['_raw_text'] = text
            
            # Step 3: Validate the structure (pass raw text and file path for voting mechanism)
            self.validate_structure(structured_data, raw_text=text, file_path=file_path)
            
            # Step 4: Filter out Koike as customer (hardcoded business rule)
            self.filter_koike_from_customer(structured_data)
            
            # Step 5: Extract missing phone numbers from raw text
            self.extract_phone_from_raw_text(structured_data, text)
            
            # Clean up internal fields before returning
            structured_data.pop('_file_path', None)
            structured_data.pop('_raw_text', None)
            
            return structured_data
            
        except Exception as e:
            print(f"Error processing document: {e}")
            raise
    
    def validate_structure(self, data: Dict[str, Any], raw_text: str = None, file_path: str = None) -> None:
        """
        Validate that the extracted data has the correct structure.
        
        Args:
            data: The structured data to validate
            raw_text: Raw text from document (for voting mechanism)
        """
        required_keys = ['company_info', 'line_items']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")
        
        # Set default values for missing company info fields
        string_fields = ['company_name', 'billing_address', 'shipping_address', 'email', 'phone_number', 'contact_person', 'contact_person_email', 'customer_po_number', 'po_date', 'notes']
        numeric_fields = ['subtotal', 'tax_amount', 'tax_rate', 'grand_total']
        
        for key in string_fields:
            if key not in data['company_info']:
                data['company_info'][key] = ""
        
        for key in numeric_fields:
            if key not in data['company_info']:
                data['company_info'][key] = 0.0
        
        if not isinstance(data['line_items'], list):
            raise ValueError("line_items must be a list")
        
        line_item_keys = ['external_part_number', 'description', 'unit_price', 'quantity']
        for item in data['line_items']:
            for key in line_item_keys:
                if key not in item:
                    if key in ['unit_price']:
                        item[key] = 0.0
                    elif key in ['quantity']:
                        item[key] = 0
                    else:
                        item[key] = ""
    
    def filter_koike_from_customer(self, data: Dict[str, Any]) -> None:
        """
        Hardcoded business rule: Remove any Koike company info since Koike is the supplier, never the customer.
        
        Args:
            data: The structured data to filter
        """
        company_name = data.get('company_info', {}).get('company_name', '').upper()
        
        # Check if the extracted company contains Koike (our supplier)
        if 'KOIKE' in company_name or 'ARONSON' in company_name:
            # Clear all company info since this is supplier data, not customer data
            data['company_info'] = {
                "company_name": "",
                "billing_address": "",
                "shipping_address": "",
                "email": "",
                "phone_number": "",
                "contact_person": "",
                "contact_person_email": "",
                "customer_po_number": "",
                "po_date": "",
                "notes": "",
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "tax_rate": 0.0,
                "grand_total": 0.0
            }
    
    def extract_phone_from_raw_text(self, data: Dict[str, Any], raw_text: str) -> None:
        """
        Extract phone numbers from raw text if not found by AI.
        
        Args:
            data: The structured data to enhance
            raw_text: Raw text from document
        """
        import re
        
        # If phone number is already found, don't override
        if data.get('company_info', {}).get('phone_number', '').strip():
            return
        
        # Phone number patterns to look for (prioritize header phones over vendor contact)
        phone_patterns = [
            r'\((\d{3})\)(\d{3})-(\d{4})',           # (936)931-1072 - header format
            r'\((\d{3})\)\s*(\d{3})-(\d{4})',        # (936) 931-1072 - header format with space
            r'(\d{3})-(\d{3})-(\d{4})',              # 936-931-1072
            r'(\d{3})\.(\d{3})\.(\d{4})',            # 936.931.1072
            r'Phone\s*(\d{3})\s*(\d{3})\s*(\d{4})',  # Phone800 252 5232 - vendor contact (lower priority)
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, raw_text)
            if matches:
                match = matches[0]
                if isinstance(match, tuple):
                    # Format as (XXX) XXX-XXXX
                    phone = f"({match[0]}) {match[1]}-{match[2]}"
                else:
                    phone = match
                
                data['company_info']['phone_number'] = phone
                print(f"Extracted phone number from raw text: {phone}")
                break
    
    def save_json_output(self, data: Dict[str, Any], output_path: str) -> None:
        """
        Save the structured data to a JSON file.
        
        Args:
            data: The structured data to save
            output_path: Path where to save the JSON file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Error saving JSON output: {str(e)}")

    def validate_shipping_address_po_box(self, shipping_address: str) -> bool:
        """
        IMMEDIATE VALIDATION: Check if shipping address contains PO Box.
        Called right after address extraction.
        
        Args:
            shipping_address: The shipping address to validate
            
        Returns:
            True if valid (no PO Box), False if invalid (contains PO Box)
        """
        import re
        
        if not shipping_address or shipping_address.strip() == "":
            print("❌ VALIDATION FAILED: Shipping address is empty")
            return False
        
        # Common PO Box patterns (case insensitive)
        po_box_patterns = [
            r'\bP\.?\s*O\.?\s*BOX\s*\d+',
            r'\bPOST\s*OFFICE\s*BOX\s*\d+',
            r'\bPO\s*BOX\s*\d+',
            r'\bP\.O\.\s*BOX\s*\d+',
            r'\bBOX\s*\d+.*POST\s*OFFICE',
            r'\bPOST\s*BOX\s*\d+'
        ]
        
        address_upper = shipping_address.upper()
        
        for pattern in po_box_patterns:
            if re.search(pattern, address_upper):
                print(f"❌ VALIDATION FAILED: Shipping address contains PO Box: {shipping_address}")
                return False
        
        print(f"✅ PO Box validation passed: {shipping_address[:50]}...")
        return True

    def validate_addresses_not_koike_aronson(self, billing_address: str, shipping_address: str) -> bool:
        """
        IMMEDIATE VALIDATION: Check if addresses contain Koike/Aronson supplier information.
        Called right after address extraction.
        
        Args:
            billing_address: The billing address to validate
            shipping_address: The shipping address to validate
            
        Returns:
            True if valid (no supplier info), False if invalid (contains supplier info)
        """
        import re
        
        # Koike/Aronson supplier patterns (case insensitive)
        supplier_patterns = [
            r'\bKOIKE\b',
            r'\bARONSON\b',
            r'\b635\s*WEST\s*MAIN\s*STREET\b',
            r'\b635\s*W\s*MAIN\s*ST\b',
            r'\bKOIKE\s*AMERICA\b',
            r'\bARONSON\s*LIGHTING\b'
        ]
        
        # Check billing address
        if billing_address:
            billing_upper = billing_address.upper()
            for pattern in supplier_patterns:
                if re.search(pattern, billing_upper):
                    print(f"❌ VALIDATION FAILED: Billing address contains Koike/Aronson: {billing_address}")
                    return False
        
        # Check shipping address
        if shipping_address:
            shipping_upper = shipping_address.upper()
            for pattern in supplier_patterns:
                if re.search(pattern, shipping_upper):
                    print(f"❌ VALIDATION FAILED: Shipping address contains Koike/Aronson: {shipping_address}")
                    return False
        
        print(f"✅ Koike/Aronson validation passed")
        return True

    def extract_addresses_with_validation_retry(self, file_path: str, max_retries: int = 2) -> Dict[str, str]:
        """
        Extract addresses with immediate validation and retry logic.
        
        Args:
            file_path: Path to the file
            max_retries: Maximum number of retry attempts (default: 2)
            
        Returns:
            Dictionary with 'billing_address' and 'shipping_address' keys
            Sets fields to "MISSING" if validation fails after max retries
        """
        retry_count = 0
        constraints = {}
        
        while retry_count <= max_retries:
            print(f"🔄 Address extraction attempt {retry_count + 1}/{max_retries + 1}")
            
            try:
                # Extract addresses (with constraints if retry)
                if retry_count == 0:
                    # First attempt - use standard prompt
                    addresses = self.extract_addresses_with_gemini(file_path)
                else:
                    # Retry attempts - use enhanced prompt with constraints
                    addresses = self.extract_addresses_with_constraints(file_path, constraints)
                
                if not addresses:
                    raise Exception("No addresses extracted")
                
                # IMMEDIATE VALIDATION 1: Check for PO Box in shipping address
                if not self.validate_shipping_address_po_box(addresses['shipping_address']):
                    if retry_count < max_retries:
                        retry_count += 1
                        constraints["po_box_constraint"] = """
CRITICAL ADDRESS EXTRACTION RULES:
1. SHIPPING ADDRESS: Must be a PHYSICAL STREET ADDRESS with building number and street name (e.g., '123 Main Street'). DO NOT use PO Box, Post Office Box, or any mailbox service for shipping address.
2. BILLING ADDRESS: Can be either physical street address OR PO Box. PO Boxes are perfectly acceptable for billing.

If you find both a PO Box and a physical address in the document:
- Use the PHYSICAL ADDRESS for shipping
- Use either the PO Box OR physical address for billing (whichever is clearly marked as billing)

If you only find a PO Box in the document:
- Mark shipping address as 'PHYSICAL ADDRESS REQUIRED - PO Box not acceptable for shipping'
- Use the PO Box for billing address
"""
                        print(f"🔄 Retrying with PO Box constraint...")
                        continue
                    else:
                        print(f"⚠️  Max retries reached for PO Box validation - setting shipping address to MISSING")
                        addresses['shipping_address'] = "MISSING"
                        break
                
                # IMMEDIATE VALIDATION 2: Check for Koike/Aronson in addresses
                if not self.validate_addresses_not_koike_aronson(addresses['billing_address'], addresses['shipping_address']):
                    if retry_count < max_retries:
                        retry_count += 1
                        constraints["koike_constraint"] = """
CRITICAL SUPPLIER CONSTRAINT:
- NEVER use "KOIKE" or "ARONSON" as billing address - these are SUPPLIER names
- NEVER use "635 WEST MAIN STREET" as billing address - this is SUPPLIER address  
- NEVER use any address containing "KOIKE" or "ARONSON" for billing or shipping
- The company in the header/letterhead is the CUSTOMER (who issued the PO)
- Look for "Bill To" or "Invoice To" address for billing
- Look for "Ship To" or "Deliver To" address for shipping
"""
                        print(f"🔄 Retrying with Koike/Aronson constraint...")
                        continue
                    else:
                        print(f"⚠️  Max retries reached for Koike/Aronson validation - setting addresses to MISSING")
                        if 'KOIKE' in addresses['billing_address'].upper() or 'ARONSON' in addresses['billing_address'].upper():
                            addresses['billing_address'] = "MISSING"
                        if 'KOIKE' in addresses['shipping_address'].upper() or 'ARONSON' in addresses['shipping_address'].upper():
                            addresses['shipping_address'] = "MISSING"
                        break
                
                # Both validations passed!
                print(f"✅ All address validations passed!")
                return addresses
                
            except Exception as e:
                print(f"❌ Address extraction attempt {retry_count + 1} failed: {e}")
                retry_count += 1
                if retry_count > max_retries:
                    print(f"⚠️  Max retries reached - setting addresses to MISSING")
                    return {"billing_address": "MISSING", "shipping_address": "MISSING"}
        
        # Fallback - should not reach here but just in case
        return {"billing_address": "MISSING", "shipping_address": "MISSING"}

    def extract_addresses_with_constraints(self, file_path: str, constraints: dict) -> Dict[str, str]:
        """
        Extract addresses with validation constraints applied.
        This is called during retry attempts.
        
        Args:
            file_path: Path to the file
            constraints: Dictionary with validation constraints
            
        Returns:
            Dictionary with 'billing_address' and 'shipping_address' keys
        """
        try:
            if not self.gemini_model:
                raise Exception("Gemini model not initialized")
            
            # Convert PDF to image (same as existing method)
            if file_path.lower().endswith('.pdf'):
                try:
                    doc = fitz.open(file_path)
                    page = doc[0]  # Use first page only
                    
                    # Render page as image with high DPI for better quality
                    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert to PIL Image
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    doc.close()
                    
                except Exception as pdf_error:
                    print(f"PyMuPDF conversion failed: {pdf_error}")
                    raise Exception(f"Could not convert PDF to image: {pdf_error}")
            else:
                # Load image directly
                image = Image.open(file_path)
            
            # Convert image to base64
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            # Build enhanced prompt with constraints
            base_prompt = """Look at this purchase order image and identify the billing address and shipping address.

Return ONLY a JSON response with this exact format:
{
    "billing_address": "[full billing address here]",
    "shipping_address": "[full shipping address here]"
}

🚨🚨🚨 CRITICAL BUSINESS RULES - READ CAREFULLY 🚨🚨🚨

ABSOLUTE PROHIBITIONS:
❌ NEVER use "KOIKE" or "ARONSON" as billing address - these are SUPPLIER names
❌ NEVER use "635 WEST MAIN STREET" as billing address - this is SUPPLIER address
❌ NEVER use any address containing "KOIKE" or "ARONSON" for billing
❌ NEVER use "Ship To" company as the customer - that's just delivery location
❌ NEVER combine address lines from different sections of the document

✅ CORRECT IDENTIFICATION:
✅ The company in the header/letterhead is the CUSTOMER (who issued the PO)
✅ The "Bill To" or "Invoice To" address is the billing address
✅ The "Ship To" or "Deliver To" address is the shipping address
✅ PO Box addresses are typically billing addresses, NOT shipping addresses

ADDRESS IDENTIFICATION:
Look for labels like:
- "Bill To", "Billing Address", "Remit To", "Invoice To"
- "Ship To", "Shipping Address", "Deliver To", "Delivery Address"

The billing address is usually where invoices should be sent.
The shipping address is usually where goods should be delivered.

FORMATTING:
- Format addresses with proper line breaks: "COMPANY NAME\\n123 STREET ADDRESS\\nCITY, STATE ZIP"
- Extract the complete address including company name, street address, city, state, and zip code
- Use the company name from the BILLING address (the company paying for the order)

🚨 REMINDER: The header company is the customer who issued the purchase order, NOT the supplier.
🚨 If you see KOIKE or ARONSON anywhere, that is the SUPPLIER, NOT the customer billing address!"""
            
            # Add constraints to prompt
            if constraints.get("po_box_constraint"):
                base_prompt += f"\n\n🚨🚨🚨 ADDRESS CONSTRAINT - PO Box Policy 🚨🚨🚨\n{constraints['po_box_constraint']}"
            
            if constraints.get("koike_constraint"):
                base_prompt += f"\n\n🚨🚨🚨 SUPPLIER CONSTRAINT - Koike/Aronson Policy 🚨🚨🚨\n{constraints['koike_constraint']}"
            
            # Prepare the API request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": base_prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": img_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1000,
                    "responseMimeType": "application/json"
                }
            }
            
            # Make API request
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                raise Exception(f"Gemini API error: {result['error']['message']}")
            
            # Extract the text response
            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if parts:
                        text_response = parts[0].get('text', '')
                        
                        # Parse JSON from the response
                        import json
                        import re
                        
                        # Extract JSON from markdown code blocks if present
                        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text_response, re.DOTALL)
                        if json_match:
                            json_text = json_match.group(1)
                        else:
                            # Try to find JSON directly
                            json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
                            if json_match:
                                json_text = json_match.group(0)
                            else:
                                raise ValueError("No JSON found in Gemini response")
                        
                        addresses = json.loads(json_text)
                        
                        # Validate that we got both addresses
                        if 'billing_address' not in addresses or 'shipping_address' not in addresses:
                            raise ValueError("Missing billing or shipping address in Gemini response")
                        
                        print(f"✅ Gemini successfully extracted addresses with constraints:")
                        print(f"   Billing:  {addresses['billing_address'][:50]}...")
                        print(f"   Shipping: {addresses['shipping_address'][:50]}...")
                        
                        return addresses
            
            raise Exception("No valid response from Gemini")
            
        except Exception as e:
            print(f"Gemini address extraction with constraints failed: {e}")
            return None

# Example usage
if __name__ == "__main__":
    # Test the document processor
    processor = DocumentProcessor()
    
    # Example of processing a file (would need actual file)
    try:
        # result = processor.process_document("sample_po.pdf")
        # print(json.dumps(result, indent=2))
        print("Document processor initialized successfully")
        print("Supported file types: PDF, DOCX, TXT, PNG, JPG, JPEG, GIF, BMP, TIFF")
    except Exception as e:
        print(f"Error: {e}")
