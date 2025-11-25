# Intelligent Invoice Data Extraction & Modeling

A machine learning-driven pipeline that extracts structured data from invoice documents using OpenAI's GPT-4 Vision API and stores it in a queryable CSV format.

## 🎯 Project Overview

This project automates financial operations by processing invoice documents (PDF or images) and extracting key metadata including:
- Invoice number
- Date
- Vendor name
- Total amount
- Line items (description, quantity, unit price, line total)

## 🏗️ Architecture

```
invoice_extraction_project/
├── invoice_extractor.py    # Main extraction pipeline
├── query_engine.py          # Data query and analysis module
├── dashboard.py             # Streamlit visualization dashboard
├── main.py                  # Interactive CLI interface
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (API keys)
├── data/
│   └── invoices/           # Input invoice files (PDF/images)
└── output/
    ├── invoices.csv        # Extracted invoice data
    ├── line_items.csv      # Extracted line items
    └── summary.json        # Extraction summary
```

## 🚀 Getting Started

### Installation

1. **Clone or download the project**

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up your OpenAI API key**

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_api_key_here
```

Or set as environment variable:
```bash
# Windows
set OPENAI_API_KEY=your_api_key_here

# Linux/Mac
export OPENAI_API_KEY=your_api_key_here
```

4. **Add invoice files**

Place your invoice files (PDF, PNG, JPG, etc.) in the `data/invoices/` directory.

## 📖 Usage

### Option 1: Interactive CLI (Recommended)

Run the main script for an interactive experience:

```bash
python main.py
```

This provides a menu to:
1. Run extraction pipeline
2. Run query demos
3. Launch Streamlit dashboard
4. Run full pipeline

### Option 2: Direct Extraction

```python
from invoice_extractor import InvoiceExtractor

# Initialize extractor
extractor = InvoiceExtractor()

# Process all invoices in a folder
results = extractor.process_folder("data/invoices")

# Save to CSV
extractor.save_to_csv(results, output_dir="output")

# Access the data
print(results['invoices'])
print(results['line_items'])
```

### Option 3: Query Existing Data

```python
from query_engine import InvoiceQueryEngine

# Load data
engine = InvoiceQueryEngine("output/invoices.csv", "output/line_items.csv")

# Get invoices from a specific vendor
vendor_invoices = engine.get_invoices_by_vendor("Acme Corp")

# Get invoices in date range
march_june = engine.get_invoices_by_date_range("2025-03-01", "2025-06-30")

# Total spend by vendor
spend = engine.get_total_spend_by_vendor()

# Get summary statistics
stats = engine.get_invoice_summary_stats()
```

### Option 4: Streamlit Dashboard

Launch the interactive dashboard:

```bash
streamlit run dashboard.py
```

Features:
- Summary statistics with metrics
- Spend by vendor visualization
- Monthly spending trends
- Invoice browser with filters
- Custom query interface
- Export capabilities

## 🔧 Key Features

### 1. Data Extraction Pipeline

- **Multi-format support**: PDF, PNG, JPG, JPEG, TIFF, BMP
- **Robust extraction**: Uses GPT-4 Vision API for accurate OCR and understanding
- **Error handling**: Retry mechanism with fallback for failed extractions
- **Metadata tracking**: Timestamps, confidence scores, source files

### 2. Data Modeling

**Invoices Table**
- invoice_id (Primary Key)
- invoice_number
- date
- vendor_name
- total_amount
- currency
- source_file
- extraction_timestamp
- confidence

**Line Items Table**
- line_item_id (Primary Key)
- invoice_id (Foreign Key)
- description
- quantity
- unit_price
- line_total

### 3. Query Capabilities

- Filter by vendor, date range
- Aggregate spending by vendor/month
- Search line items
- Generate vendor reports
- Summary statistics

### 4. Visualization Dashboard

- Interactive charts with Plotly
- Real-time filtering
- Export capabilities
- Custom query interface

## 💡 ML/LLM Approach

### Model Choice: GPT-4 Vision (gpt-4o)

**Why GPT-4 Vision?**
- **Zero-shot learning**: No training data required
- **Layout understanding**: Comprehends document structure
- **Multi-modal**: Processes both text and visual layout
- **Accuracy**: Superior to traditional OCR + NLP pipelines
- **Flexibility**: Handles varied invoice formats

### Trade-offs Analysis

| Approach | Pros | Cons | Use Case |
|----------|------|------|----------|
| **Regex** | Fast, deterministic | Brittle, format-specific | Standardized invoices |
| **OCR + LLM** | Good accuracy, flexible | Two-step process | Mixed quality documents |
| **Vision LLM** | Best accuracy, end-to-end | API cost, latency | Production quality needed |

### Why Not Other Options?

- **LayoutLMv3/Donut**: Require training data and fine-tuning
- **Tesseract OCR**: Poor on low-quality scans
- **Regex**: Fails on format variations
- **GPT-4 Vision**: Optimal balance of accuracy and ease of deployment

## 📊 Evaluation

The pipeline includes confidence scoring and error tracking. For production:

1. **Manual validation**: Label 10-20 sample invoices
2. **Metrics**: Calculate field-level F1 score
3. **Error analysis**: Review failed extractions
4. **Iteration**: Adjust prompts based on common errors

## 🔄 Scalability

Current approach scales to thousands of invoices:

**Optimizations for scale:**
- Batch processing with parallel API calls
- Caching for duplicate documents
- Database storage (SQLite → PostgreSQL)
- Async processing with queues
- Cost optimization with model selection

**Estimated costs (GPT-4 Vision):**
- ~$0.01-0.03 per invoice
- 1000 invoices ≈ $10-30

## 🚧 Limitations & Improvements

### Current Limitations

1. **Language**: English-only prompts
2. **Currency**: Assumes single currency per invoice
3. **Multi-page**: Processes first page only
4. **Handwriting**: Limited OCR for handwritten text

### Future Improvements

1. **Hybrid model**: Combine vision + text extraction for better accuracy
2. **Confidence scoring**: Per-field confidence levels
3. **Active learning**: Flag low-confidence extractions for review
4. **Multi-language**: Support for international invoices
5. **Table extraction**: Better handling of complex line item tables
6. **Duplicate detection**: Identify and flag duplicate invoices
7. **Validation rules**: Business logic validation (e.g., total = sum of line items)

## 📦 Dependencies

Key libraries:
- `openai>=1.0.0` - OpenAI API client
- `pandas>=2.0.0` - Data manipulation
- `streamlit>=1.28.0` - Web dashboard
- `plotly>=5.17.0` - Visualizations
- `PyPDF2>=3.0.0` - PDF processing
- `pdf2image>=1.16.0` - PDF to image conversion
- `pytesseract>=0.3.10` - OCR fallback

## 🔐 Security

- API keys stored in `.env` (never commit to git)
- Add `.env` to `.gitignore`
- Use environment variables in production

## 📝 License

This project is for educational/evaluation purposes.

## 🤝 Contributing

This is a take-home assignment project. Feedback welcome!

## 📧 Support

For issues or questions, please refer to the code documentation or create an issue.

---

