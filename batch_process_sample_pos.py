#!/usr/bin/env python3
"""
Batch Process Sample POs
Randomly selects 5 POs from samplePOs folder and processes them in parallel.
Exports Epicor-formatted JSON to batch_results folder.
"""

import os
import json
import random
import asyncio
import aiohttp
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import tempfile

class BatchPOProcessor:
    def __init__(self, sample_pos_folder: str = "samplePOs", output_folder: str = "batch_results"):
        self.sample_pos_folder = Path(sample_pos_folder)
        self.output_folder = Path(output_folder)
        self.base_url = "http://127.0.0.1:5000"
        
        # Create output folder if it doesn't exist
        self.output_folder.mkdir(exist_ok=True)
        
    def get_random_pos(self, count: int = 5) -> List[Path]:
        """Get random PO files from samplePOs folder."""
        if not self.sample_pos_folder.exists():
            raise FileNotFoundError(f"Sample POs folder not found: {self.sample_pos_folder}")
        
        # Get all PDF files
        pdf_files = list(self.sample_pos_folder.glob("*.pdf"))
        
        if len(pdf_files) < count:
            print(f"Warning: Only {len(pdf_files)} PDF files found, using all available")
            return pdf_files
        
        return random.sample(pdf_files, count)
    
    async def upload_and_process_po(self, session: aiohttp.ClientSession, po_file: Path) -> Dict[str, Any]:
        """Upload and process a single PO file."""
        print(f"Processing: {po_file.name}")
        
        try:
            # Prepare file for upload
            with open(po_file, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=po_file.name, content_type='application/pdf')
                
                # Upload and process
                async with session.post(f"{self.base_url}/upload", data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('success'):
                            # Get the processed filename
                            processed_filename = result['processed_file']
                            
                            # Download the Epicor-formatted JSON
                            async with session.get(f"{self.base_url}/download/{processed_filename}") as download_response:
                                if download_response.status == 200:
                                    epicor_json = await download_response.json()
                                    
                                    return {
                                        'success': True,
                                        'original_file': po_file.name,
                                        'processed_file': processed_filename,
                                        'epicor_json': epicor_json,
                                        'validation': result.get('validation', {}),
                                        'error': None
                                    }
                                else:
                                    return {
                                        'success': False,
                                        'original_file': po_file.name,
                                        'error': f"Failed to download Epicor JSON: {download_response.status}"
                                    }
                        else:
                            return {
                                'success': False,
                                'original_file': po_file.name,
                                'error': result.get('error', 'Unknown processing error')
                            }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'original_file': po_file.name,
                            'error': f"Upload failed: {response.status} - {error_text}"
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'original_file': po_file.name,
                'error': f"Exception during processing: {str(e)}"
            }
    
    async def process_all_pos(self, po_files: List[Path]) -> List[Dict[str, Any]]:
        """Process all POs in parallel."""
        print(f"Starting parallel processing of {len(po_files)} POs...")
        
        # Create semaphore to limit concurrent requests (avoid overwhelming the server)
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        
        async def process_with_semaphore(session, po_file):
            async with semaphore:
                return await self.upload_and_process_po(session, po_file)
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
            tasks = [process_with_semaphore(session, po_file) for po_file in po_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions that occurred
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        'success': False,
                        'original_file': po_files[i].name,
                        'error': f"Task exception: {str(result)}"
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
    
    def save_results(self, results: List[Dict[str, Any]]):
        """Save all results to JSON files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save individual Epicor JSON files
        for result in results:
            if result['success'] and 'epicor_json' in result:
                # Create filename based on original file
                original_name = Path(result['original_file']).stem
                output_filename = f"{original_name}_epicor_{timestamp}.json"
                output_path = self.output_folder / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result['epicor_json'], f, indent=2, ensure_ascii=False)
                
                print(f"Saved Epicor JSON: {output_path}")
        
        # Save summary report
        summary_filename = f"batch_processing_summary_{timestamp}.json"
        summary_path = self.output_folder / summary_filename
        
        summary = {
            'timestamp': timestamp,
            'total_files': len(results),
            'successful': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success']),
            'results': results
        }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"Saved summary report: {summary_path}")
        return summary
    
    async def run_batch_processing(self, count: int = 5):
        """Main method to run batch processing."""
        print("=== Batch PO Processing ===")
        print(f"Sample POs folder: {self.sample_pos_folder}")
        print(f"Output folder: {self.output_folder}")
        
        # Get random PO files
        try:
            po_files = self.get_random_pos(count)
            print(f"\nSelected {len(po_files)} PO files:")
            for po_file in po_files:
                print(f"  - {po_file.name}")
        except Exception as e:
            print(f"Error selecting PO files: {e}")
            return
        
        # Process all POs
        results = await self.process_all_pos(po_files)
        
        # Save results
        summary = self.save_results(results)
        
        # Print summary
        print(f"\n=== Processing Complete ===")
        print(f"Total files processed: {summary['total_files']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        
        if summary['failed'] > 0:
            print("\nFailed files:")
            for result in results:
                if not result['success']:
                    print(f"  - {result['original_file']}: {result['error']}")
        
        print(f"\nResults saved to: {self.output_folder.absolute()}")

def main():
    """Main function to run the batch processor."""
    processor = BatchPOProcessor()
    
    # Run the batch processing
    asyncio.run(processor.run_batch_processing(count=5))

if __name__ == "__main__":
    main()
