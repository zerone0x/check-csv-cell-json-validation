import csv
import json
import sys
import os
import re
import argparse
try:
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    print("Warning: jsonschema library not found. Advanced schema validation will not be available.")
    print("To install: pip install jsonschema")

def fix_json_string(json_str):
    """
    Attempt to fix common JSON formatting issues
    """
    # Replace single quotes with double quotes
    fixed_str = json_str.replace("'", "\"")
    
    # Add quotes to keys that are missing them
    fixed_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', fixed_str)
    
    # Fix missing commas between key-value pairs
    # Look for patterns like "key1":"value1""key2":"value2" or "key1":value1"key2":value2
    fixed_str = re.sub(r'(["}\d])\s*(["{\w])', r'\1,\2', fixed_str)
    
    # Try to fix trailing commas in arrays and objects
    fixed_str = re.sub(r',\s*}', '}', fixed_str)
    fixed_str = re.sub(r',\s*]', ']', fixed_str)
    
    return fixed_str

def get_column_letter(index):
    """
    Convert column index to letter (0 = A, 1 = B, etc.)
    Handles multi-letter columns (Z, AA, AB, etc.)
    """
    result = ""
    while True:
        index, remainder = divmod(index, 26)
        result = chr(65 + remainder) + result
        if index == 0:
            break
        index -= 1
    return result

def validate_json_schema(json_obj, schema=None):
    """
    Validate JSON object against a schema
    Returns (is_valid, error_message)
    """
    if not JSONSCHEMA_AVAILABLE:
        return True, "Schema validation skipped (jsonschema not installed)"
    
    if schema is None:
        return True, "No schema provided for validation"
    
    try:
        validate(instance=json_obj, schema=schema)
        return True, "JSON is valid according to schema"
    except ValidationError as e:
        return False, f"Schema validation error: {e.message}"

def get_all_validation_errors(json_obj, schema):
    """
    Get all validation errors for a JSON object against a schema
    """
    if not JSONSCHEMA_AVAILABLE:
        return []
    
    validator = Draft7Validator(schema)
    return list(validator.iter_errors(json_obj))

def check_and_fix_json_in_csv(filename, schema_file=None, column_schemas=None, summary_only=False):
    """
    Check and fix JSON in CSV cells
    
    Args:
        filename: CSV file to check
        schema_file: Optional JSON schema file for validation
        column_schemas: Optional dict mapping column indices to schema files
        summary_only: If True, only show summary statistics, not detailed logs
    """
    temp_filename = filename + ".temp"
    fixed_rows = []
    has_fixes = False
    
    # Load schema if provided
    schema = None
    if schema_file and JSONSCHEMA_AVAILABLE:
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            if not summary_only:
                print(f"Loaded schema from {schema_file}")
        except Exception as e:
            print(f"Error loading schema file: {e}")
    
    # Load column-specific schemas if provided
    column_specific_schemas = {}
    if column_schemas and JSONSCHEMA_AVAILABLE:
        for col_idx, schema_path in column_schemas.items():
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    column_specific_schemas[col_idx] = json.load(f)
                if not summary_only:
                    print(f"Loaded schema for column {get_column_letter(int(col_idx))} from {schema_path}")
            except Exception as e:
                print(f"Error loading schema for column {get_column_letter(int(col_idx))}: {e}")
    
    # Statistics
    total_cells_checked = 0
    total_json_cells = 0
    total_errors = 0
    fixed_errors = 0
    unfixed_errors = 0
    schema_errors = 0
    error_types = {}
    
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        # Read header if exists
        header = next(reader, None)
        fixed_rows.append(header)
        
        row_num = 1 if header else 0
        for row in reader:
            row_num += 1
            fixed_row = row.copy()
            
            # Skip if row is empty
            if not row:
                fixed_rows.append(row)
                continue
                
            # Check all columns
            for col_idx in range(0, len(row)):
                cell = row[col_idx]
                total_cells_checked += 1
                
                # Skip empty cells
                if cell.strip() == "":
                    continue
                
                # Determine which schema to use for this column
                current_schema = None
                if str(col_idx) in column_specific_schemas:
                    current_schema = column_specific_schemas[str(col_idx)]
                elif col_idx in column_specific_schemas:
                    current_schema = column_specific_schemas[col_idx]
                else:
                    current_schema = schema
                    
                try:
                    # Try to parse as JSON
                    json_obj = json.loads(cell)
                    total_json_cells += 1
                    
                    # Validate against schema if available
                    if current_schema and JSONSCHEMA_AVAILABLE:
                        is_valid, error_msg = validate_json_schema(json_obj, current_schema)
                        if not is_valid:
                            schema_errors += 1
                            if not summary_only:
                                col_letter = get_column_letter(col_idx)
                                print(f"Row {row_num}, Column {col_letter}: {error_msg}")
                                
                                # Get all validation errors
                                all_errors = get_all_validation_errors(json_obj, current_schema)
                                for err in all_errors:
                                    print(f"  - {err.message} at {'.'.join(str(p) for p in err.path)}")
                        
                except json.JSONDecodeError as e:
                    total_errors += 1
                    error_msg = str(e)
                    error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                    
                    if not summary_only:
                        col_letter = get_column_letter(col_idx)
                        print(f"Row {row_num}, Column {col_letter}: JSON format is incorrect - {e}")
                    
                    # Try to fix the JSON
                    fixed_json_str = fix_json_string(cell)
                    try:
                        json_obj = json.loads(fixed_json_str)
                        fixed_errors += 1
                        if not summary_only:
                            col_letter = get_column_letter(col_idx)
                            print(f"Row {row_num}, Column {col_letter}: JSON fixed successfully")
                        
                        # Validate fixed JSON against schema
                        if current_schema and JSONSCHEMA_AVAILABLE:
                            is_valid, error_msg = validate_json_schema(json_obj, current_schema)
                            if not is_valid and not summary_only:
                                schema_errors += 1
                                col_letter = get_column_letter(col_idx)
                                print(f"Row {row_num}, Column {col_letter}: Fixed JSON fails schema validation - {error_msg}")
                        
                        fixed_row[col_idx] = fixed_json_str
                        has_fixes = True
                    except json.JSONDecodeError as e2:
                        unfixed_errors += 1
                        if not summary_only:
                            col_letter = get_column_letter(col_idx)
                            print(f"Row {row_num}, Column {col_letter}: Could not fix JSON - {e2}")
            
            fixed_rows.append(fixed_row)
    
    # Write the fixed data back to a new file if there were any fixes
    if has_fixes:
        with open(temp_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(fixed_rows)
        
        print(f"\nFixed CSV saved as: {temp_filename}")
        print(f"To replace the original file, rename {temp_filename} to {filename}")
    else:
        print("\nNo JSON errors were fixed.")
    
    # Print summary
    print("\n===== JSON Check Summary =====")
    print(f"Total cells checked: {total_cells_checked}")
    print(f"Total JSON cells found: {total_json_cells}")
    print(f"Total errors found: {total_errors}")
    print(f"Errors fixed: {fixed_errors}")
    print(f"Errors not fixed: {unfixed_errors}")
    print(f"Schema validation errors: {schema_errors}")
    
    if error_types:
        print("\nError types encountered:")
        for error_type, count in error_types.items():
            print(f"  - {error_type}: {count} occurrences")

def create_sample_schema():
    """
    Create a sample JSON schema file
    """
    sample_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "age": {"type": "number", "minimum": 0},
            "email": {"type": "string", "format": "email"},
            "tags": {
                "type": "array",
                "items": {"type": "string"}
            },
            "address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                    "country": {"type": "string"}
                },
                "required": ["street", "city"]
            }
        },
        "required": ["id", "name"]
    }
    
    with open("sample_schema.json", "w", encoding="utf-8") as f:
        json.dump(sample_schema, f, indent=2)
    
    print("Created sample schema file: sample_schema.json")
    print("You can use this as a starting point for your own schema.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check and fix JSON in CSV files")
    parser.add_argument("csv_file", nargs='?', help="CSV file to check")
    parser.add_argument("--schema", help="JSON schema file for validation")
    parser.add_argument("--column-schema", nargs=2, action="append", metavar=("COL_IDX", "SCHEMA_FILE"),
                        help="Schema file for a specific column (can be used multiple times)")
    parser.add_argument("--create-sample-schema", action="store_true", help="Create a sample schema file")
    parser.add_argument("--summary-only", action="store_true", help="Show only summary statistics, not detailed logs")
    
    args = parser.parse_args()
    
    if args.create_sample_schema:
        create_sample_schema()
        if not args.csv_file:
            sys.exit(0)
    
    if args.csv_file:
        # Convert column schemas to a dictionary
        column_schemas = {}
        if args.column_schema:
            for col_idx, schema_file in args.column_schema:
                column_schemas[col_idx] = schema_file
        
        check_and_fix_json_in_csv(args.csv_file, args.schema, column_schemas, args.summary_only)
    else:
        parser.print_help()

