#!/usr/bin/env python3
"""
Script to fix the step4_mapping.py file by replacing the broken map_line_item method
with the working version from step4_mapping_fixed.py
"""

# Read the working method from the fixed file
with open('step4_mapping_fixed.py', 'r') as f:
    fixed_method = f.read()

# Read the main file
with open('step4_mapping.py', 'r') as f:
    lines = f.readlines()

# Find the start and end of the map_line_item method
start_line = None
end_line = None

for i, line in enumerate(lines):
    if line.strip().startswith('def map_line_item('):
        start_line = i
    elif start_line is not None and line.strip().startswith('def _get_fuzzy_part_candidates('):
        end_line = i
        break

if start_line is None or end_line is None:
    print("Could not find method boundaries")
    exit(1)

print(f"Found method from line {start_line + 1} to {end_line}")

# Replace the method with the working version (add proper indentation)
working_lines = []
for line in fixed_method.split('\n'):
    if line.strip():  # Skip empty lines
        working_lines.append('    ' + line + '\n')
    else:
        working_lines.append('\n')

# Create new file content
new_lines = lines[:start_line] + working_lines + lines[end_line:]

# Write the fixed file
with open('step4_mapping.py', 'w') as f:
    f.writelines(new_lines)

print("Fixed step4_mapping.py successfully!")
