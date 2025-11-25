
import os
import sys
from pathlib import Path
from invoice_extractor import InvoiceExtractor
from query_engine import InvoiceQueryEngine, demo_queries


def setup_environment():
    print("=" * 60)
    print("INVOICE EXTRACTION PIPELINE - SETUP")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
   
    api_key = os.getenv('OPENAI_API_KEY')
    
   
    data_dir = Path("data/invoices")
    if not data_dir.exists():
        print(f"\n Invoice directory not found: {data_dir}")
        print("Creating directory...")
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f" Created directory: {data_dir}")
        print("\nPlease add your invoice files (PDF/images) to this directory.")
        return False
    
    invoice_files = list(data_dir.glob("*.*"))
    if not invoice_files:
        print(f"\n  No invoice files found in {data_dir}")
        print("Please add invoice files (PDF, PNG, JPG, etc.) to the data/invoices directory.")
        return False
    
    print(f" Found {len(invoice_files)} invoice files")
    
    return True


def run_extraction(invoice_folder: str = "data/invoices"):
    print("\n" + "=" * 60)
    print("STEP 1: EXTRACTING DATA FROM INVOICES")
    print("=" * 60)
    
    try:
        # Initialize extractor
        extractor = InvoiceExtractor()
        
        # Process all invoices
        print(f"\nProcessing invoices from: {invoice_folder}")
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
        print(f"Total amount: ${results['invoices']['total_amount'].sum():,.2f}")
        print(f"Unique vendors: {results['invoices']['vendor_name'].nunique()}")
        
        print("\n✓ Data saved to CSV files in 'output' directory")
        
        return results
        
    except Exception as e:
        print(f"\n Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_queries():
    print("\n" + "=" * 60)
    print("STEP 2: QUERYING AND ANALYZING DATA")
    print("=" * 60)
    
    try:
        invoices_path = "output/invoices.csv"
        line_items_path = "output/line_items.csv"
        
        if not Path(invoices_path).exists():
            print(" No data found. Please run extraction first.")
            return None
        
        engine = demo_queries(invoices_path, line_items_path)
        
        print("\n Query demo completed")
        
        return engine
        
    except Exception as e:
        print(f"\n Error during queries: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_menu():
    
    print("\n" + "=" * 60)
    print("INVOICE EXTRACTION PIPELINE - MENU")
    print("=" * 60)
    print("\n1. Run extraction pipeline")
    print("2. Run query demos")
    print("3. Launch Streamlit dashboard")
    print("4. Run full pipeline (1 + 2)")
    print("5. Exit")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    return choice


def launch_dashboard():
    
    print("\n" + "=" * 60)
    print("LAUNCHING DASHBOARD")
    print("=" * 60)
    
    try:
        import streamlit.web.cli as stcli
        import sys
        
        dashboard_path = str(Path(__file__).parent / "dashboard.py")
        
        print(f"\nStarting Streamlit dashboard...")
        print("The dashboard will open in your web browser.")
        print("Press Ctrl+C to stop the dashboard.\n")
        
        sys.argv = ["streamlit", "run", dashboard_path]
        sys.exit(stcli.main())
        
    except ImportError:
        print(" Streamlit not installed. Install with: pip install streamlit")
    except Exception as e:
        print(f" Error launching dashboard: {e}")


def main():
    
    print("\n" + "=" * 60)
    print("INTELLIGENT INVOICE DATA EXTRACTION & MODELING")
    print("=" * 60)
    
    # Setup environment
    if not setup_environment():
        print("\n  Setup incomplete. Please fix the issues above and try again.")
        return
    
    # Interactive mode
    while True:
        choice = show_menu()
        
        if choice == '1':
            run_extraction()
            input("\nPress Enter to continue...")
        
        elif choice == '2':
            run_queries()
            input("\nPress Enter to continue...")
        
        elif choice == '3':
            launch_dashboard()
            break
        
        elif choice == '4':
            results = run_extraction()
            if results is not None:
                run_queries()
            input("\nPress Enter to continue...")
        
        elif choice == '5':
            print("\n Goodbye!")
            break
        
        else:
            print("\n Invalid choice. Please enter 1-5.")


if __name__ == "__main__":
    main()
