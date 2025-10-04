"""
Process Lampton and export Epicor JSON to file
"""
import json
import os
from datetime import datetime
from step2_ocr_ai import DocumentProcessor
from step3_databases import DatabaseManager
from step4_mapping import PartNumberMapper

# Initialize
processor = DocumentProcessor()
db_mgr = DatabaseManager()
db_mgr.load_databases()
mapper = PartNumberMapper(db_mgr)

# Process Lampton PO
print("Processing Lampton PO...")
extracted = processor.process_document('samplePOs/lampton00599468.pdf')
mapped = mapper.process_purchase_order(extracted)
epicor_json = mapper.export_to_epicor_json(mapped)

# Save to file
os.makedirs('processed/epicor_batch', exist_ok=True)
output_file = 'processed/epicor_batch/lampton00599468_epicor.json'

with open(output_file, 'w') as f:
    json.dump(epicor_json, f, indent=2)

print(f"\n✅ Saved to: {output_file}")
print("\nEPICOR JSON:")
print(json.dumps(epicor_json, indent=2))

