"""
Query and Analysis Module for Invoice Data
Provides functions to query and analyze extracted invoice data
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


class InvoiceQueryEngine:
    """Query engine for analyzing invoice data"""
    
    def __init__(self, invoices_csv: str, line_items_csv: str):
        """
        Initialize query engine with CSV data
        
        Args:
            invoices_csv: Path to invoices CSV file
            line_items_csv: Path to line items CSV file
        """
        self.invoices_df = pd.read_csv(invoices_csv)
        self.line_items_df = pd.read_csv(line_items_csv)
        
        # Convert date column to datetime
        if 'date' in self.invoices_df.columns:
            self.invoices_df['date'] = pd.to_datetime(
                self.invoices_df['date'], 
                errors='coerce'
            )
    
    def get_invoices_by_vendor(self, vendor_name: str) -> pd.DataFrame:
        """
        Get all invoices from a specific vendor
        
        Args:
            vendor_name: Name of the vendor (case-insensitive, partial match)
            
        Returns:
            DataFrame of matching invoices
        """
        mask = self.invoices_df['vendor_name'].str.contains(
            vendor_name, 
            case=False, 
            na=False
        )
        return self.invoices_df[mask].sort_values('date', ascending=False)
    
    def get_invoices_by_date_range(
        self, 
        start_date: str, 
        end_date: str,
        vendor_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get invoices within a date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            vendor_name: Optional vendor filter
            
        Returns:
            DataFrame of matching invoices
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        mask = (self.invoices_df['date'] >= start) & (self.invoices_df['date'] <= end)
        
        if vendor_name:
            vendor_mask = self.invoices_df['vendor_name'].str.contains(
                vendor_name, 
                case=False, 
                na=False
            )
            mask = mask & vendor_mask
        
        return self.invoices_df[mask].sort_values('date')
    
    def get_total_spend_by_vendor(self) -> pd.DataFrame:
        """
        Calculate total spend by vendor
        
        Returns:
            DataFrame with vendor spending summary
        """
        spend_by_vendor = self.invoices_df.groupby('vendor_name').agg({
            'total_amount': ['sum', 'count', 'mean'],
            'invoice_id': 'count'
        }).round(2)
        
        spend_by_vendor.columns = [
            'total_spend', 
            'invoice_count', 
            'average_invoice_amount',
            'num_invoices'
        ]
        
        # Keep only total_spend and invoice_count
        spend_by_vendor = spend_by_vendor[['total_spend', 'invoice_count']]
        
        return spend_by_vendor.sort_values('total_spend', ascending=False)
    
    def get_total_spend_by_month(self) -> pd.DataFrame:
        """
        Calculate total spend by month
        
        Returns:
            DataFrame with monthly spending
        """
        df = self.invoices_df.copy()
        df['month'] = df['date'].dt.to_period('M')
        
        monthly_spend = df.groupby('month').agg({
            'total_amount': 'sum',
            'invoice_id': 'count'
        }).round(2)
        
        monthly_spend.columns = ['total_spend', 'invoice_count']
        return monthly_spend
    
    def get_invoice_details(self, invoice_id: int) -> Dict:
        """
        Get complete details for a specific invoice
        
        Args:
            invoice_id: ID of the invoice
            
        Returns:
            Dictionary with invoice and line items data
        """
        invoice = self.invoices_df[
            self.invoices_df['invoice_id'] == invoice_id
        ].iloc[0].to_dict()
        
        line_items = self.line_items_df[
            self.line_items_df['invoice_id'] == invoice_id
        ].to_dict('records')
        
        return {
            'invoice': invoice,
            'line_items': line_items
        }
    
    def get_top_spending_periods(self, top_n: int = 5) -> pd.DataFrame:
        """
        Get the top N highest spending periods
        
        Args:
            top_n: Number of top periods to return
            
        Returns:
            DataFrame with top spending months
        """
        monthly = self.get_total_spend_by_month()
        return monthly.nlargest(top_n, 'total_spend')
    
    def get_invoice_summary_stats(self) -> Dict:
        """
        Get summary statistics for all invoices
        
        Returns:
            Dictionary with summary statistics
        """
        return {
            'total_invoices': len(self.invoices_df),
            'total_amount': float(self.invoices_df['total_amount'].sum()),
            'average_invoice_amount': float(self.invoices_df['total_amount'].mean()),
            'median_invoice_amount': float(self.invoices_df['total_amount'].median()),
            'unique_vendors': int(self.invoices_df['vendor_name'].nunique()),
            'date_range': {
                'start': str(self.invoices_df['date'].min()),
                'end': str(self.invoices_df['date'].max())
            },
            'total_line_items': len(self.line_items_df)
        }
    
    def search_line_items(self, search_term: str) -> pd.DataFrame:
        """
        Search for line items by description
        
        Args:
            search_term: Term to search for in descriptions
            
        Returns:
            DataFrame with matching line items and invoice info
        """
        mask = self.line_items_df['description'].str.contains(
            search_term, 
            case=False, 
            na=False
        )
        
        matching_items = self.line_items_df[mask]
        
        # Join with invoice data
        result = matching_items.merge(
            self.invoices_df[['invoice_id', 'vendor_name', 'date', 'invoice_number']],
            on='invoice_id',
            how='left'
        )
        
        return result.sort_values('date', ascending=False)
    
    def get_vendor_list(self) -> List[str]:
        """Get list of unique vendors"""
        return sorted(self.invoices_df['vendor_name'].unique().tolist())
    
    def export_vendor_report(self, vendor_name: str, output_path: str):
        """
        Export a detailed report for a specific vendor
        
        Args:
            vendor_name: Name of the vendor
            output_path: Path to save the report CSV
        """
        invoices = self.get_invoices_by_vendor(vendor_name)
        
        # Get all line items for these invoices
        invoice_ids = invoices['invoice_id'].tolist()
        line_items = self.line_items_df[
            self.line_items_df['invoice_id'].isin(invoice_ids)
        ]
        
        # Merge data
        report = line_items.merge(
            invoices[['invoice_id', 'invoice_number', 'date', 'vendor_name']],
            on='invoice_id',
            how='left'
        )
        
        report.to_csv(output_path, index=False)
        print(f"Vendor report saved to {output_path}")
        
        return report


def demo_queries(invoices_csv: str, line_items_csv: str):
    """
    Demonstrate various query capabilities
    
    Args:
        invoices_csv: Path to invoices CSV
        line_items_csv: Path to line items CSV
    """
    print("=" * 60)
    print("INVOICE DATA QUERY DEMO")
    print("=" * 60)
    
    engine = InvoiceQueryEngine(invoices_csv, line_items_csv)
    
    # Summary statistics
    print("\n--- SUMMARY STATISTICS ---")
    stats = engine.get_invoice_summary_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"{key}: {value}")
    
    # Total spend by vendor
    print("\n--- TOTAL SPEND BY VENDOR ---")
    vendor_spend = engine.get_total_spend_by_vendor()
    print(vendor_spend.head(10))
    
    # Monthly spending
    print("\n--- MONTHLY SPENDING ---")
    monthly = engine.get_total_spend_by_month()
    print(monthly.tail(10))
    
    # Vendor list
    print("\n--- UNIQUE VENDORS ---")
    vendors = engine.get_vendor_list()
    print(f"Found {len(vendors)} unique vendors:")
    for vendor in vendors[:10]:
        print(f"  - {vendor}")
    
    return engine


if __name__ == "__main__":
    # Example usage
    invoices_path = "output/invoices.csv"
    line_items_path = "output/line_items.csv"
    
    # Run demo queries
    engine = demo_queries(invoices_path, line_items_path)
    
    # Custom query examples
    print("\n--- CUSTOM QUERY EXAMPLES ---")
    
    # Example: Get invoices from a specific vendor
    # vendor = "Acme Corp"
    # invoices = engine.get_invoices_by_vendor(vendor)
    # print(f"\nInvoices from {vendor}:")
    # print(invoices)
    
    # Example: Get invoices in date range
    # invoices = engine.get_invoices_by_date_range("2025-03-01", "2025-06-30")
    # print("\nInvoices from March to June 2025:")
    # print(invoices)
