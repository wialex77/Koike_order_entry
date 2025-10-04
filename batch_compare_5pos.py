#!/usr/bin/env python3
"""
Batch process 5 POs and compare old vs new outputs.
"""

import sys
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from step2_ocr_ai import DocumentProcessor
from step3_databases import DatabaseManager
from step4_mapping import PartNumberMapper

def process_single_po(po_path, po_name):
    """Process a single PO and return the result."""
    try:
        print(f"🔄 Processing {po_name}...")
        
        # Initialize components for this thread
        processor = DocumentProcessor()
        db_manager = DatabaseManager()
        db_manager.load_databases()
        part_mapper = PartNumberMapper(db_manager)
        
        # Process document
        structured_data = processor.process_document(po_path)
        
        # Map to internal format
        mapped_data = part_mapper.process_purchase_order(structured_data)
        
        # Export to Epicor format
        epicor_json = part_mapper.export_to_epicor_json(mapped_data)
        
        # Save new output
        output_file = f'processed/epicor_batch/{po_name}_BATCH_NEW.json'
        with open(output_file, 'w') as f:
            json.dump(epicor_json, f, indent=2)
        
        print(f"✅ {po_name} completed - saved to {output_file}")
        return po_name, output_file, None
        
    except Exception as e:
        print(f"❌ Error processing {po_name}: {str(e)}")
        return po_name, None, str(e)

def compare_outputs():
    """Compare old vs new outputs."""
    print("\n🔍 COMPARING OLD vs NEW OUTPUTS")
    print("=" * 60)
    
    # List of files to compare
    files_to_compare = [
        ('alltex65700_epicor.json', 'alltex65700_BATCH_NEW.json'),
        ('indianaoxygen_epicor.json', 'indianaoxygen_BATCH_NEW.json'),
        ('matheson08925123_epicor.json', 'matheson08925123_BATCH_NEW.json'),
        ('nexair01958333_epicor.json', 'nexair01958333_BATCH_NEW.json'),
        ('centralmcgowan00664002_epicor.json', 'centralmcgowan00664002_BATCH_NEW.json')
    ]
    
    for old_file, new_file in files_to_compare:
        print(f'\n📋 Comparing {old_file} vs {new_file}:')
        
        try:
            # Load both files
            with open(f'processed/epicor_batch/{old_file}', 'r') as f:
                old_data = json.load(f)
            with open(f'processed/epicor_batch/{new_file}', 'r') as f:
                new_data = json.load(f)
            
            # Compare key fields
            differences = []
            
            # Check customer account
            old_cust = old_data.get('CustNum', '')
            new_cust = new_data.get('CustNum', '')
            if old_cust != new_cust:
                differences.append(f'Customer: OLD="{old_cust}" NEW="{new_cust}"')
            
            # Check company name
            old_company = old_data.get('Company', '')
            new_company = new_data.get('Company', '')
            if old_company != new_company:
                differences.append(f'Company: OLD="{old_company}" NEW="{new_company}"')
            
            # Check billing address (OTS fields)
            old_billing_name = old_data.get('OTSName', '')
            new_billing_name = new_data.get('OTSName', '')
            if old_billing_name != new_billing_name:
                differences.append(f'Billing Name: OLD="{old_billing_name}" NEW="{new_billing_name}"')
            
            old_billing_addr = old_data.get('OTSAddress1', '')
            new_billing_addr = new_data.get('OTSAddress1', '')
            if old_billing_addr != new_billing_addr:
                differences.append(f'Billing Address: OLD="{old_billing_addr}" NEW="{new_billing_addr}"')
            
            # Check shipping address (OTS fields)
            old_shipping_city = old_data.get('OTSCity', '')
            new_shipping_city = new_data.get('OTSCity', '')
            if old_shipping_city != new_shipping_city:
                differences.append(f'Shipping City: OLD="{old_shipping_city}" NEW="{new_shipping_city}"')
            
            old_shipping_state = old_data.get('OTSState', '')
            new_shipping_state = new_data.get('OTSState', '')
            if old_shipping_state != new_shipping_state:
                differences.append(f'Shipping State: OLD="{old_shipping_state}" NEW="{new_shipping_state}"')
            
            # Check PO number
            old_po = old_data.get('PONum', '')
            new_po = new_data.get('PONum', '')
            if old_po != new_po:
                differences.append(f'PO Number: OLD="{old_po}" NEW="{new_po}"')
            
            if differences:
                print('   🔄 DIFFERENCES FOUND:')
                for diff in differences:
                    print(f'     • {diff}')
            else:
                print('   ✅ NO DIFFERENCES - Identical outputs')
                
        except Exception as e:
            print(f'   ❌ Error comparing: {str(e)}')

def main():
    """Main function to run batch processing and comparison."""
    print("🚀 BATCH PROCESSING 5 POs WITH NEW HYBRID APPROACH")
    print("=" * 60)
    
    # List of POs to process
    pos_to_process = [
        ('samplePOs/alltex65700.pdf', 'alltex65700'),
        ('samplePOs/indianaoxygen.pdf', 'indianaoxygen'),
        ('samplePOs/matheson08925123.pdf', 'matheson08925123'),
        ('samplePOs/nexair01958333.pdf', 'nexair01958333'),
        ('samplePOs/centralmcgowan00664002.pdf', 'centralmcgowan00664002')
    ]
    
    start_time = time.time()
    
    # Process POs in parallel
    print(f"\n📋 Processing {len(pos_to_process)} POs in parallel...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks
        future_to_po = {
            executor.submit(process_single_po, po_path, po_name): (po_path, po_name)
            for po_path, po_name in pos_to_process
        }
        
        # Collect results
        results = []
        for future in as_completed(future_to_po):
            po_path, po_name = future_to_po[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"❌ Exception for {po_name}: {str(e)}")
                results.append((po_name, None, str(e)))
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"\n⏱️  Total processing time: {processing_time:.2f} seconds")
    print(f"📊 Average time per PO: {processing_time/len(pos_to_process):.2f} seconds")
    
    # Count successes and failures
    successes = sum(1 for _, _, error in results if error is None)
    failures = sum(1 for _, _, error in results if error is not None)
    
    print(f"✅ Successful: {successes}")
    print(f"❌ Failed: {failures}")
    
    # Compare outputs
    compare_outputs()
    
    print("\n🎉 Batch processing and comparison complete!")

if __name__ == "__main__":
    main()
