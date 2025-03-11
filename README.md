# JSON CSV Validator

A powerful tool for validating and fixing JSON data stored in CSV files.

## Overview

This utility helps you identify, validate, and fix JSON formatting issues in CSV files. It's particularly useful when working with data exports or imports that contain JSON objects within CSV cells.

## Features

- **JSON Validation**: Checks if JSON strings in CSV cells are properly formatted
- **Automatic Fixing**: Attempts to fix common JSON formatting issues
- **Schema Validation**: Validates JSON against provided schemas
- **Column-Specific Schemas**: Apply different schemas to different columns
- **Detailed Reporting**: Shows exactly where and what errors occur
- **Summary Statistics**: Provides an overview of validation results

## Requirements

- Python 3.6+
- Required dependencies are listed in `requirements.txt`

## Installation

1. Clone this repository or download the script
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```bash
python check.py your_file.csv
```

### With Schema Validation

```bash
python check.py your_file.csv --schema schema.json
```

### With Column-Specific Schemas

```bash
python check.py your_file.csv --column-schema 0 schema1.json --column-schema 1 schema2.json
```

### Create a Sample Schema

```bash
python check.py --create-sample-schema
```

### Summary Only (Less Verbose Output)

```bash
python check.py your_file.csv --summary-only
```

## How It Works

1. The tool reads your CSV file row by row
2. For each cell, it attempts to parse the content as JSON
3. If parsing fails, it tries to fix common JSON formatting issues:
   - Replacing single quotes with double quotes
   - Adding quotes to unquoted keys
   - Fixing missing commas between key-value pairs
   - Removing trailing commas
4. If a schema is provided, it validates the JSON against the schema
5. It generates a report of all issues found and fixed
6. If fixes were made, it creates a new file with the fixed data

## Common JSON Errors Fixed

- Single quotes instead of double quotes
- Missing quotes around keys
- Missing commas between key-value pairs
- Trailing commas in arrays and objects

## Example Schema

The tool can create a sample schema file to get you started:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "age": { "type": "number", "minimum": 0 },
    "email": { "type": "string", "format": "email" },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "address": {
      "type": "object",
      "properties": {
        "street": { "type": "string" },
        "city": { "type": "string" },
        "country": { "type": "string" }
      },
      "required": ["street", "city"]
    }
  },
  "required": ["id", "name"]
}
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
