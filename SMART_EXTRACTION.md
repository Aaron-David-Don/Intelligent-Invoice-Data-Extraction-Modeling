# 🧠 Smart Invoice Extraction with Template Learning

## Overview

The Smart Invoice Extraction system intelligently learns invoice formats and reuses patterns for efficient extraction. This dramatically reduces API costs and improves speed for repeat invoice formats.

## 🎯 Key Innovation

**Problem**: Calling GPT-4 Vision API for every invoice is expensive (~$0.02 per invoice) and slow, especially when processing multiple invoices from the same vendor with the same format.

**Solution**: 
1. **First invoice from a vendor**: Use GPT-4 Vision (accurate but costly)
2. **Learn the format**: Extract the layout pattern and field positions
3. **Subsequent invoices**: Use fast regex extraction (free and instant)
4. **Fallback**: If pattern matching fails, use GPT-4 Vision again

## 📊 Cost Savings Example

```
Scenario: 100 invoices from 10 different vendors (10 invoices each)

Traditional approach (GPT-4 Vision only):
- 100 invoices × $0.02 = $2.00

Smart approach (Template Learning):
- First invoice from each vendor: 10 × $0.02 = $0.20
- Remaining invoices (template): 90 × $0.00 = $0.00
- Total: $0.20 (90% savings!)

Scaling to 1000 invoices:
- Traditional: $20.00
- Smart: $2.00 (90% savings!)
```

## 🏗️ Architecture

### Components

1. **TemplateManager** (`template_manager.py`)
   - Learns invoice layouts
   - Stores regex patterns
   - Matches new invoices to templates
   - Tracks success rates

2. **SmartInvoiceExtractor** (`invoice_extractor_smart.py`)
   - Extraction orchestrator
   - Tries template first, falls back to GPT
   - Learns from GPT extractions
   - Tracks statistics

3. **Main Interface** (`main_smart.py`)
   - Interactive menu
   - Template statistics viewer
   - Option to disable templates

### Workflow

```
┌─────────────────────┐
│  New Invoice Image  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   OCR Extraction    │  ← Tesseract (fast & free)
│   (Get text)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Template Matching  │  ← Check for known format
│  (Find similar)     │
└──────────┬──────────┘
           │
      ┌────┴────┐
      │         │
   Match?    No Match
      │         │
      ▼         ▼
┌─────────┐  ┌─────────────────┐
│ Regex   │  │  GPT-4 Vision   │  ← Accurate extraction
│ Extract │  │  API Call       │
└────┬────┘  └────────┬────────┘
     │                │
     │                ▼
     │         ┌─────────────────┐
     │         │ Learn Template  │  ← Save for future
     │         │ (Extract pattern)│
     │         └────────┬────────┘
     │                  │
     └──────────┬───────┘
                ▼
        ┌──────────────┐
        │   Results    │
        └──────────────┘
```

## 🔍 How Template Learning Works

### 1. Layout Fingerprinting

When a new invoice is processed:
- Extract text using OCR (Tesseract)
- Normalize the text (replace numbers with `#`, normalize spaces)
- Identify structure keywords (invoice, total, date, etc.)
- Create a hash of the structure
- This hash is the "layout fingerprint"

```python
# Example
Original text: "Invoice #12345 Date: 2025-03-15 Total: $150.00"
Normalized: "invoice # date: #-#-# total: $#.#"
Fingerprint: md5("invoice date total") = "abc123..."
```

### 2. Pattern Learning

After GPT-4 Vision extracts data:
- For each field (invoice_number, date, total, etc.)
- Find the value in the OCR text
- Learn the regex pattern around it
- Store pattern for future use

```python
# Example patterns learned:
{
  "invoice_number": r"invoice\s*#?\s*:?\s*([A-Z0-9\-]+)",
  "date": r"date\s*:?\s*(\d{4}-\d{2}-\d{2})",
  "total_amount": r"total\s*:?\s*\$?\s*([\d,]+\.?\d*)"
}
```

### 3. Template Matching

For new invoices:
- Extract OCR text
- Generate layout fingerprint
- Search for matching template (same fingerprint)
- If found, use regex patterns to extract data
- If extraction succeeds, update template success count
- If fails, fallback to GPT-4 Vision

### 4. Confidence Tracking

Each template tracks:
- `success_count`: Number of successful extractions
- `failure_count`: Number of failed extractions
- `success_rate`: success / (success + failure)

Templates are only used if success_rate > 70%

## 📁 Files

### New Files

1. **`template_manager.py`**
   - `InvoiceTemplate`: Stores template data
   - `TemplateManager`: Manages all templates
   - Methods: `learn_template()`, `find_matching_template()`, `extract_with_template()`

2. **`invoice_extractor_smart.py`**
   - `SmartInvoiceExtractor`: Enhanced extractor
   - Methods: `extract_from_image()`, `extract_with_gpt()`, `extract_ocr_text()`
   - Automatic template learning

3. **`main_smart.py`**
   - Interactive interface for smart extraction
   - Template statistics viewer
   - Option to enable/disable templates

### Template Storage

Templates are saved in:
```
output/invoice_templates.json
```

Format:
```json
{
  "templates": [
    {
      "template_id": "TPL_abc12345_1",
      "vendor_name": "Acme Corp",
      "layout_hash": "abc123...",
      "patterns": {
        "invoice_number": "regex pattern",
        "date": "regex pattern",
        "total_amount": "regex pattern"
      },
      "success_count": 15,
      "failure_count": 1,
      "created_at": "2025-11-25T10:00:00",
      "last_used": "2025-11-25T12:00:00"
    }
  ]
}
```

## 🚀 Usage

### Basic Usage

```python
from invoice_extractor_smart import SmartInvoiceExtractor

# Initialize with template learning enabled
extractor = SmartInvoiceExtractor(use_templates=True)

# Process folder
results = extractor.process_folder("data/invoices")

# Save results
extractor.save_to_csv(results, "output")

# View statistics
extractor.print_statistics()
```

### Interactive Menu

```bash
python main_smart.py
```

Options:
1. Run smart extraction (with templates) ← **Recommended**
2. Run extraction without templates (GPT only)
3. View template statistics
4. Run query demos
5. Launch dashboard
6. Run full pipeline

### Template Statistics

```bash
python main_smart.py
# Select option 3: View template statistics
```

Output:
```
============================================================
TEMPLATE USAGE STATISTICS
============================================================

Total Templates: 3

Template Details:
------------------------------------------------------------

Template: TPL_abc12345_1
  Vendor: Acme Corp
  Total Uses: 25
  Success Rate: 96.0%
  Last Used: 2025-11-25T12:00:00

Template: TPL_def67890_2
  Vendor: Global Systems Inc
  Total Uses: 15
  Success Rate: 93.3%
  Last Used: 2025-11-25T11:30:00
```

## 🎛️ Configuration

### Enable/Disable Templates

```python
# With templates (recommended)
extractor = SmartInvoiceExtractor(use_templates=True)

# Without templates (GPT-4 only)
extractor = SmartInvoiceExtractor(use_templates=False)
```

### Confidence Threshold

Edit `template_manager.py`:
```python
# Line ~180
if success_rate > 0.7:  # Change threshold here (0.0 to 1.0)
    # Use template
```

Higher threshold = more conservative (fewer template uses)
Lower threshold = more aggressive (more template uses, but might fail)

## 📊 Statistics Tracking

The system tracks:
- Total invoices processed
- Template extractions (fast & free)
- GPT extractions (accurate but costly)
- Failed extractions
- Estimated API cost
- Cost savings from templates

## 🔧 Advanced Features

### 1. Template Refinement

Templates improve over time:
- More successful extractions → Higher confidence
- Failed extractions → Template marked unreliable
- Patterns can be manually edited in `invoice_templates.json`

### 2. Manual Pattern Addition

You can manually add patterns:

```json
{
  "template_id": "TPL_manual_1",
  "vendor_name": "Custom Vendor",
  "patterns": {
    "invoice_number": "Inv\\s*#\\s*(\\d+)",
    "date": "(\\d{2}/\\d{2}/\\d{4})",
    "total_amount": "Total:\\s*\\$([\\d,]+\\.\\d{2})"
  }
}
```

### 3. Template Debugging

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## ⚠️ Limitations

1. **Requires OCR**: Tesseract must be installed for template matching
2. **Layout sensitivity**: Major layout changes create new templates
3. **First invoice cost**: First invoice from each vendor still uses GPT
4. **Handwritten text**: OCR may fail on handwritten invoices

## 🎯 Best Practices

1. **Process in batches**: Group invoices by vendor for maximum savings
2. **Review templates**: Check template statistics regularly
3. **Manual verification**: Validate first few template extractions
4. **Keep templates**: Don't delete `invoice_templates.json`
5. **Monitor success rates**: Remove or retrain low-performing templates

## 💡 When to Use Templates

**Use templates when**:
✅ Processing multiple invoices from same vendors
✅ Invoices have consistent formats
✅ Working with high-volume datasets
✅ Cost optimization is important

**Skip templates when**:
❌ Processing single invoices
❌ Every invoice has unique format
❌ Maximum accuracy is critical (use GPT-4 only)
❌ OCR quality is poor

## 🚦 Performance Comparison

| Metric | Traditional | Smart (with templates) |
|--------|-------------|------------------------|
| Speed | 3-5 sec/invoice | 0.1-3 sec/invoice |
| Cost | $0.02/invoice | $0.002-0.02/invoice |
| Accuracy | 95-98% | 93-98% |
| Scalability | Linear cost | Sublinear cost |

## 📈 Future Enhancements

Possible improvements:
1. **Machine learning**: Use ML to improve pattern matching
2. **Active learning**: Flag uncertain extractions for manual review
3. **Multi-language**: Support for international invoices
4. **Cloud storage**: Share templates across teams
5. **Auto-correction**: Learn from manual corrections

## 🤔 FAQ

**Q: What if template extraction fails?**
A: Automatically falls back to GPT-4 Vision. The failure is logged and template confidence is updated.

**Q: Can I force GPT-4 for specific vendors?**
A: Yes, set `use_templates=False` or manually delete the vendor's template.

**Q: How accurate are templates compared to GPT-4?**
A: For well-formatted invoices: ~95% as accurate. For complex layouts: GPT-4 is better.

**Q: Do templates work with PDFs?**
A: Yes! PDFs are converted to images, then OCR is applied.

**Q: Can I share templates with my team?**
A: Yes! Share the `invoice_templates.json` file.

---

**Built with ❤️ for efficiency and cost optimization**
