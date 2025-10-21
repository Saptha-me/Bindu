---
name: PDF Processing
description: Extract text, fill forms, and extract tables from PDF documents. Use when working with PDF files, forms, or document extraction. Requires pypdf and pdfplumber packages.
version: 1.0.0
author: raahul@saptha.me
allowed-tools: Read, Write, Execute
---

# PDF Processing Agent

## Overview
This agent specializes in PDF document processing with support for text extraction, form filling, and table extraction. It handles both standard text-based PDFs and scanned documents (with OCR).

## Capabilities

### Text Extraction
- **Standard PDFs**: Direct text extraction from text-based PDFs
- **Scanned PDFs**: OCR-based extraction using Tesseract
- **Multi-language**: Supports English, Spanish, French, German
- **Preserves formatting**: Maintains paragraph structure and spacing

### Form Filling
- **Field types**: Text fields, checkboxes, dropdowns, radio buttons
- **Validation**: Validates field data before filling
- **Batch processing**: Can fill multiple forms with same template

### Table Extraction
- **Simple tables**: Clean grid-based tables
- **Complex tables**: Multi-column, merged cells
- **Output formats**: JSON, CSV, pandas DataFrame

## Use Cases

### When to Use This Agent
- User uploads a PDF and asks to extract text
- User needs to fill out PDF forms programmatically
- User wants to extract tables from reports/invoices
- User needs to process scanned documents

### When NOT to Use This Agent
- PDF editing (use pdf-editor agent)
- PDF creation from scratch (use pdf-generator agent)
- Image extraction from PDFs (use pdf-image-extractor agent)
- PDF merging/splitting (use pdf-manipulator agent)

## Input Requirements

### Accepted Formats
- `application/pdf`
- File size: Up to 50MB
- Pages: Up to 500 pages

### Input Structure
```json
{
  "file": "base64_encoded_pdf_or_url",
  "operation": "extract_text|fill_form|extract_tables",
  "options": {
    "ocr": true,
    "language": "eng",
    "extract_tables": true
  }
}
```

## Output Format

### Text Extraction
```json
{
  "success": true,
  "pages": [
    {
      "page_number": 1,
      "text": "Extracted text...",
      "confidence": 0.98
    }
  ],
  "metadata": {
    "total_pages": 10,
    "processing_time_ms": 1500,
    "ocr_used": false
  }
}
```

### Form Filling
```json
{
  "success": true,
  "output_file": "base64_encoded_filled_pdf",
  "fields_filled": 15,
  "validation_errors": []
}
```

### Table Extraction
```json
{
  "success": true,
  "tables": [
    {
      "page_number": 1,
      "table_index": 0,
      "headers": ["Item", "Quantity", "Price"],
      "rows": [
        ["Widget A", "10", "$50.00"],
        ["Widget B", "5", "$25.00"]
      ]
    }
  ]
}
```

## Performance Characteristics
- **Average processing time**: 2 seconds per page
- **Concurrent requests**: Up to 5
- **Memory usage**: ~500MB per request
- **Scalability**: Horizontal scaling supported

## Error Handling
- **Encrypted PDFs**: Returns error requesting password
- **Corrupted files**: Returns validation error with details
- **Unsupported operations**: Returns clear error message
- **Timeout**: 30 seconds per page

## Examples

### Example 1: Extract Text
**Input:**
```json
{
  "file": "https://example.com/document.pdf",
  "operation": "extract_text"
}
```

**Output:**
```json
{
  "success": true,
  "pages": [
    {
      "page_number": 1,
      "text": "This is the extracted text from page 1...",
      "confidence": 0.99
    }
  ],
  "metadata": {
    "total_pages": 1,
    "processing_time_ms": 850,
    "ocr_used": false
  }
}
```

### Example 2: Fill Form
**Input:**
```json
{
  "file": "base64_encoded_form_pdf",
  "operation": "fill_form",
  "form_data": {
    "name": "John Doe",
    "email": "john@example.com",
    "date": "2025-01-21"
  }
}
```

**Output:**
```json
{
  "success": true,
  "output_file": "base64_encoded_filled_pdf",
  "fields_filled": 3,
  "validation_errors": []
}
```

### Example 3: Extract Tables from Invoice
**Input:**
```json
{
  "file": "https://example.com/invoice.pdf",
  "operation": "extract_tables"
}
```

**Output:**
```json
{
  "success": true,
  "tables": [
    {
      "page_number": 1,
      "table_index": 0,
      "headers": ["Description", "Quantity", "Unit Price", "Total"],
      "rows": [
        ["Consulting Services", "10", "$150.00", "$1,500.00"],
        ["Software License", "1", "$500.00", "$500.00"]
      ]
    }
  ],
  "metadata": {
    "total_tables": 1,
    "processing_time_ms": 2100
  }
}
```

## Dependencies
- `pypdf>=3.0.0`
- `pdfplumber>=0.9.0`
- `pytesseract>=0.3.10` (for OCR)
- System: `tesseract-ocr`

## Installation
```bash
pip install pypdf pdfplumber pytesseract
# For OCR support (optional)
# macOS: brew install tesseract
# Ubuntu: apt-get install tesseract-ocr
```

## Versioning
- **v1.0.0**: Initial release with text extraction, form filling, and table extraction
- **v1.1.0**: Planned - Add PDF merging/splitting capabilities
- **v1.2.0**: Planned - Enhanced OCR with multiple language support

## Best Practices

### For Developers
1. Check file size before processing (max 50MB)
2. Use OCR only when necessary (slower processing)
3. Validate form data before filling
4. Handle errors gracefully with user-friendly messages

### For Orchestrators
1. Route PDF operations to this skill based on operation type
2. Check requirements (tesseract-ocr) before routing OCR requests
3. Consider file size for performance estimation
4. Chain with text-analysis for content understanding
5. Use performance metrics for load balancing

## Security Considerations
- Validates PDF structure before processing
- Sanitizes file inputs to prevent injection attacks
- Does not execute embedded JavaScript or macros
- Limits memory usage per request
