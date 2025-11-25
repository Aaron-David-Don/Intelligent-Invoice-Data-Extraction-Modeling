# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up Your API Key

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_api_key_here
```

Get your API key from: https://platform.openai.com/api-keys

### Step 3: Add Invoice Files

Place your invoice files (PDF, PNG, JPG) in the `data/invoices/` folder.

### Step 4: Run the Pipeline

**Option A: Interactive Menu (Recommended)**
```bash
python main.py
```

**Option B: Direct Script**
```bash
python invoice_extractor.py
```

**Option C: Jupyter Notebook**
```bash
jupyter notebook invoice_extraction_demo.ipynb
```

**Option D: Streamlit Dashboard**
```bash
streamlit run dashboard.py
```

### Step 5: View Results

Results are saved in the `output/` directory:
- `invoices.csv` - Extracted invoice data
- `line_items.csv` - Extracted line item data
- `summary.json` - Extraction summary

## 📊 What You Can Do

### Query Examples

```python
from query_engine import InvoiceQueryEngine

# Load data
engine = InvoiceQueryEngine("output/invoices.csv", "output/line_items.csv")

# Get invoices from vendor
vendor_invoices = engine.get_invoices_by_vendor("Acme Corp")

# Get invoices in date range
march_june = engine.get_invoices_by_date_range("2025-03-01", "2025-06-30")

# Total spend by vendor
spend = engine.get_total_spend_by_vendor()

# Summary statistics
stats = engine.get_invoice_summary_stats()
```

### Dashboard Features

The Streamlit dashboard (`streamlit run dashboard.py`) provides:
- 📈 Summary statistics with key metrics
- 💰 Spend by vendor visualization
- 📅 Monthly spending trends
- 🔍 Invoice browser with filters
- 🔎 Custom query interface
- 📥 Export capabilities

## 🛠️ Troubleshooting

### API Key Not Found
```
Error: OpenAI API key not found
```
**Solution**: Create a `.env` file with your API key or set it as an environment variable.

### PDF Processing Error
```
Error: pdf2image not installed
```
**Solution**: 
1. Install pdf2image: `pip install pdf2image`
2. Install Poppler:
   - Windows: Download from [here](https://github.com/oschwartz10612/poppler-windows/releases/)
   - Mac: `brew install poppler`
   - Linux: `sudo apt-get install poppler-utils`

### No Invoice Files Found
```
Warning: No invoice files found
```
**Solution**: Add invoice files (PDF, PNG, JPG) to the `data/invoices/` directory.

### Import Error
```
ModuleNotFoundError: No module named 'openai'
```
**Solution**: Run `pip install -r requirements.txt`

## 💡 Tips

1. **Test with a few invoices first** - Start with 2-3 invoices to verify the pipeline works
2. **Check confidence scores** - Review low-confidence extractions manually
3. **Validate totals** - Use the validation notebook to check accuracy
4. **Monitor API costs** - GPT-4 Vision costs ~$0.01-0.03 per invoice
5. **Use the dashboard** - It's the easiest way to explore your data

## 📖 Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Explore the [Jupyter notebook](invoice_extraction_demo.ipynb) for examples
3. Customize the extraction prompt in `invoice_extractor.py` for better accuracy
4. Add validation rules in `query_engine.py`
5. Extend the dashboard with custom visualizations

## 🤔 Common Questions

**Q: Can it handle different invoice formats?**  
A: Yes! GPT-4 Vision understands various layouts and formats.

**Q: What languages are supported?**  
A: Currently optimized for English. Prompts can be modified for other languages.

**Q: How accurate is the extraction?**  
A: Typically 95%+ for clear, well-formatted invoices. Test with your specific documents.

**Q: Can I use a different LLM?**  
A: Yes! Modify the `invoice_extractor.py` to use Claude, Gemini, or other vision models.

**Q: Is my data secure?**  
A: Data is sent to OpenAI API. For sensitive data, consider:
  - Using local models (LayoutLMv3, Donut)
  - Azure OpenAI with private endpoints
  - Self-hosted solutions

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review error messages in console output
3. Check the logs in `output/` directory
4. Verify your API key is valid
5. Ensure all dependencies are installed

---

**Happy Invoice Extracting! 📄✨**
