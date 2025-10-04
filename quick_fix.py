#!/usr/bin/env python3
"""
Quick fix for the step4_mapping.py file
"""

# Read the current file
with open('step4_mapping.py', 'r') as f:
    content = f.read()

# Fix the JSON parsing issue - add markdown cleanup
old_json_parsing = '''            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            try:
                result = json.loads(result_text)'''

new_json_parsing = '''            result_text = response.choices[0].message.content.strip()
            
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
                result = json.loads(result_text)'''

# Apply the fix
if old_json_parsing in content:
    content = content.replace(old_json_parsing, new_json_parsing)
    print("Applied JSON parsing fix")
else:
    print("JSON parsing fix not found or already applied")

# Write the fixed file
with open('step4_mapping.py', 'w') as f:
    f.write(content)

print("Quick fix applied successfully!")
