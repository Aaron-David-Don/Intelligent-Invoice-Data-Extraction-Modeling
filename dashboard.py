"""
Streamlit Dashboard for Invoice Data Visualization
Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Import our query engine
from query_engine import InvoiceQueryEngine


def load_data():
    """Load invoice data from CSV files"""
    invoices_path = Path("output/invoices.csv")
    line_items_path = Path("output/line_items.csv")
    
    if not invoices_path.exists() or not line_items_path.exists():
        st.error("Data files not found. Please run the extraction pipeline first.")
        st.stop()
    
    return InvoiceQueryEngine(str(invoices_path), str(line_items_path))


def main():
    st.set_page_config(
        page_title="Invoice Analytics Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Invoice Data Analytics Dashboard")
    st.markdown("---")
    
    # Load data
    try:
        engine = load_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Get vendor list
    vendors = engine.get_vendor_list()
    selected_vendor = st.sidebar.selectbox(
        "Select Vendor (optional)",
        ["All Vendors"] + vendors
    )
    
    # Date range filter
    if not engine.invoices_df.empty and 'date' in engine.invoices_df.columns:
        min_date = engine.invoices_df['date'].min()
        max_date = engine.invoices_df['date'].max()
        
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    
    # Summary Statistics
    st.header("📈 Summary Statistics")
    stats = engine.get_invoice_summary_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Invoices", f"{stats['total_invoices']:,}")
    
    with col2:
        st.metric("Total Amount", f"${stats['total_amount']:,.2f}")
    
    with col3:
        st.metric("Avg Invoice", f"${stats['average_invoice_amount']:,.2f}")
    
    with col4:
        st.metric("Unique Vendors", stats['unique_vendors'])
    
    st.markdown("---")
    
    # Two column layout
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("💰 Total Spend by Vendor")
        vendor_spend = engine.get_total_spend_by_vendor()
        
        # Create bar chart
        fig = px.bar(
            vendor_spend.reset_index().head(10),
            x='total_spend',
            y='vendor_name',
            orientation='h',
            title="Top 10 Vendors by Total Spend",
            labels={'total_spend': 'Total Spend ($)', 'vendor_name': 'Vendor'},
            color='total_spend',
            color_continuous_scale='Blues'
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Show table
        st.dataframe(
            vendor_spend.head(10).style.format({
                'total_spend': '${:,.2f}',
                'invoice_count': '{:,.0f}'
            }),
            use_container_width=True
        )
    
    with col_right:
        st.subheader("📅 Monthly Spending Trend")
        monthly_spend = engine.get_total_spend_by_month()
        
        if not monthly_spend.empty:
            # Convert period to string for plotting
            monthly_df = monthly_spend.reset_index()
            monthly_df['month'] = monthly_df['month'].astype(str)
            
            # Create line chart
            fig = px.line(
                monthly_df,
                x='month',
                y='total_spend',
                title="Monthly Spending Trend",
                labels={'total_spend': 'Total Spend ($)', 'month': 'Month'},
                markers=True
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show table
            st.dataframe(
                monthly_spend.style.format({
                    'total_spend': '${:,.2f}',
                    'invoice_count': '{:,.0f}'
                }),
                use_container_width=True
            )
    
    st.markdown("---")
    
    # Invoice Browser
    st.header("🔍 Invoice Browser")
    
    # Filter options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if selected_vendor != "All Vendors":
            filtered_invoices = engine.get_invoices_by_vendor(selected_vendor)
            st.info(f"Showing invoices from: {selected_vendor}")
        else:
            filtered_invoices = engine.invoices_df
    
    with col2:
        search_term = st.text_input("Search line items", "")
    
    # Display invoices
    if not filtered_invoices.empty:
        display_columns = [
            'invoice_number', 'vendor_name', 'date', 
            'total_amount', 'currency', 'confidence'
        ]
        
        st.dataframe(
            filtered_invoices[display_columns].style.format({
                'total_amount': '${:,.2f}',
                'date': lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ''
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.warning("No invoices found matching the filters.")
    
    # Search results
    if search_term:
        st.subheader(f"Line Items matching '{search_term}'")
        search_results = engine.search_line_items(search_term)
        
        if not search_results.empty:
            st.dataframe(
                search_results.style.format({
                    'unit_price': '${:,.2f}',
                    'line_total': '${:,.2f}',
                    'quantity': '{:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("No matching line items found.")
    
    st.markdown("---")
    
    # Query Interface
    st.header("🔎 Custom Queries")
    
    query_type = st.selectbox(
        "Select Query Type",
        [
            "Invoices by Date Range",
            "Vendor Report",
            "Top Spending Periods"
        ]
    )
    
    if query_type == "Invoices by Date Range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")
        
        if st.button("Run Query"):
            results = engine.get_invoices_by_date_range(
                str(start_date), 
                str(end_date)
            )
            st.dataframe(results, use_container_width=True)
    
    elif query_type == "Vendor Report":
        vendor = st.selectbox("Select Vendor", vendors)
        
        if st.button("Generate Report"):
            invoices = engine.get_invoices_by_vendor(vendor)
            
            if not invoices.empty:
                st.write(f"### Report for {vendor}")
                st.write(f"**Total Invoices:** {len(invoices)}")
                st.write(f"**Total Spend:** ${invoices['total_amount'].sum():,.2f}")
                
                st.dataframe(invoices, use_container_width=True)
                
                # Download button
                csv = invoices.to_csv(index=False)
                st.download_button(
                    label="Download Report",
                    data=csv,
                    file_name=f"{vendor}_report.csv",
                    mime="text/csv"
                )
            else:
                st.warning(f"No invoices found for {vendor}")
    
    elif query_type == "Top Spending Periods":
        top_n = st.slider("Number of periods", 3, 10, 5)
        
        if st.button("Run Query"):
            results = engine.get_top_spending_periods(top_n)
            st.dataframe(
                results.style.format({
                    'total_spend': '${:,.2f}',
                    'invoice_count': '{:,.0f}'
                }),
                use_container_width=True
            )


if __name__ == "__main__":
    main()
