"""
Main Script for Smart Invoice Extraction with Template Learning
"""

import os
import sys
from pathlib import Path
from invoice_extractor_smart import SmartInvoiceExtractor
from template_manager import TemplateManager
from query_engine import InvoiceQueryEngine, demo_queries


def setup_environment():
    """Check and setup the environment"""
    print("=" * 60)
    print("SMART INVOICE EXTRACTION PIPELINE - SETUP")
    print("=" * 60)
    
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n⚠️  OpenAI API key not found!")
        print("Please set your API key:")
        print("  1. Create a .env file in the project directory")
        print("  2. Add: OPENAI_API_KEY=your_api_key_here")
        print("\nOr set it as an environment variable:")
        print("  Windows: set OPENAI_API_KEY=your_api_key_here")
        print("  Linux/Mac: export OPENAI_API_KEY=your_api_key_here")
        return False
    
    print("✓ OpenAI API key found")
    
    # Check for Tesseract (OCR)
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        print("✓ Tesseract OCR found")
    except Exception:
        print("\n⚠️  Tesseract OCR not found (optional but recommended)")
        print("  Template matching will be limited without OCR")
        print("  Install from: https://github.com/tesseract-ocr/tesseract")
    
    # Check for data directory
    data_dir = Path("data/invoices")
    if not data_dir.exists():
        print(f"\n⚠️  Invoice directory not found: {data_dir}")
        print("Creating directory...")
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {data_dir}")
        print("\nPlease add your invoice files (PDF/images) to this directory.")
        return False
    
    # Check for invoice files
    invoice_files = list(data_dir.glob("*.*"))
    supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
    invoice_files = [f for f in invoice_files if f.suffix.lower() in supported_extensions]
    
    if not invoice_files:
        print(f"\n⚠️  No invoice files found in {data_dir}")
        print("Please add invoice files (PDF, PNG, JPG) to process")
        print()
        return False
    
    print(f"✓ Found {len(invoice_files)} invoice file(s)")
    
    return True


def run_extraction(invoice_folder: str = "data/invoices", use_templates: bool = True):
    """Run the smart extraction pipeline"""
    print("\n" + "=" * 60)
    print("STEP 1: SMART EXTRACTION WITH TEMPLATE LEARNING")
    print("=" * 60)
    
    if use_templates:
        print("\n📚 Template Learning: ENABLED")
        print("   - First extraction: Uses GPT-4 Vision")
        print("   - Learns invoice format")
        print("   - Repeat invoices: Fast regex extraction")
        print("   - Saves ~$0.02 per repeat invoice")
    else:
        print("\n📚 Template Learning: DISABLED")
        print("   - All extractions use GPT-4 Vision")
    
    try:
        # Initialize smart extractor
        extractor = SmartInvoiceExtractor(use_templates=use_templates)
        
        # Check existing templates
        if use_templates:
            template_manager = TemplateManager()
            stats = template_manager.get_statistics()
            if stats['total_templates'] > 0:
                print(f"\n✓ Found {stats['total_templates']} existing template(s)")
                print("   These will be used for matching invoices")
        
        # Process all invoices
        print(f"\nProcessing invoices from: {invoice_folder}")
        print("-" * 60)
        
        results = extractor.process_folder(invoice_folder)
        
        # Save to CSV
        output_dir = "output"
        Path(output_dir).mkdir(exist_ok=True)
        extractor.save_to_csv(results, output_dir=output_dir)
        
        # Display summary
        print("\n" + "-" * 60)
        print("EXTRACTION SUMMARY")
        print("-" * 60)
        print(f"Total invoices processed: {len(results['invoices'])}")
        print(f"Total line items: {len(results['line_items'])}")
        
        if not results['invoices'].empty:
            print(f"Total amount: ${results['invoices']['total_amount'].sum():,.2f}")
            print(f"Unique vendors: {results['invoices']['vendor_name'].nunique()}")
        
        print(f"\n✓ Data saved to CSV files in '{output_dir}' directory")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_template_stats():
    """Show template statistics"""
    print("\n" + "=" * 60)
    print("TEMPLATE STATISTICS")
    print("=" * 60)
    
    try:
        template_manager = TemplateManager()
        template_manager.print_statistics()
        
        stats = template_manager.get_statistics()
        
        if stats['total_templates'] > 0:
            print("\n💡 Tips:")
            print("  - Templates improve with more usage")
            print("  - High success rate = reliable template")
            print("  - Low success rate = template needs refinement")
            
            total_uses = sum(t['total_uses'] for t in stats['templates'])
            if total_uses > 10:
                saved_cost = total_uses * 0.02
                print(f"\n💰 Estimated savings: ${saved_cost:.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def run_queries():
    """Run demo queries"""
    print("\n" + "=" * 60)
    print("STEP 2: QUERYING AND ANALYZING DATA")
    print("=" * 60)
    
    try:
        invoices_path = "output/invoices.csv"
        line_items_path = "output/line_items.csv"
        
        if not Path(invoices_path).exists():
            print("❌ No data found. Please run extraction first.")
            return None
        
        # Run demo queries
        engine = demo_queries(invoices_path, line_items_path)
        
        print("\n✓ Query demo completed")
        
        return engine
        
    except Exception as e:
        print(f"\n❌ Error during queries: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_menu():
    """Show interactive menu"""
    print("\n" + "=" * 60)
    print("SMART INVOICE EXTRACTION - MENU")
    print("=" * 60)
    print("\n1. Run smart extraction (with template learning)")
    print("2. Run extraction without templates (GPT only)")
    print("3. View template statistics")
    print("4. Run query demos")
    print("5. Launch Streamlit dashboard")
    print("6. Run full pipeline (1 + 4)")
    print("7. Exit")
    
    choice = input("\nEnter your choice (1-7): ").strip()
    return choice


def launch_dashboard():
    """Launch Streamlit dashboard"""
    print("\n" + "=" * 60)
    print("LAUNCHING DASHBOARD")
    print("=" * 60)
    
    try:
        import streamlit.web.cli as stcli
        
        dashboard_path = str(Path(__file__).parent / "dashboard.py")
        
        print(f"\nStarting Streamlit dashboard...")
        print("The dashboard will open in your web browser.")
        print("Press Ctrl+C to stop the dashboard.\n")
        
        sys.argv = ["streamlit", "run", dashboard_path]
        sys.exit(stcli.main())
        
    except ImportError:
        print("❌ Streamlit not installed. Install with: pip install streamlit")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("SMART INVOICE DATA EXTRACTION & MODELING")
    print("With Template Learning for Cost Optimization")
    print("=" * 60)
    
    # Setup environment
    if not setup_environment():
        print("\n⚠️  Setup incomplete. Please fix the issues above and try again.")
        return
    
    # Interactive mode
    while True:
        choice = show_menu()
        
        if choice == '1':
            run_extraction(use_templates=True)
            input("\nPress Enter to continue...")
        
        elif choice == '2':
            run_extraction(use_templates=False)
            input("\nPress Enter to continue...")
        
        elif choice == '3':
            show_template_stats()
            input("\nPress Enter to continue...")
        
        elif choice == '4':
            run_queries()
            input("\nPress Enter to continue...")
        
        elif choice == '5':
            launch_dashboard()
            break
        
        elif choice == '6':
            results = run_extraction(use_templates=True)
            if results is not None:
                run_queries()
            input("\nPress Enter to continue...")
        
        elif choice == '7':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("\n❌ Invalid choice. Please enter 1-7.")


if __name__ == "__main__":
    main()
