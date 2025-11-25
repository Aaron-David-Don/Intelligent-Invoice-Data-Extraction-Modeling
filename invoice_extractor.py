"""
Invoice Data Extraction Pipeline using OpenAI API
Extracts structured data from invoice documents (PDF/images)
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InvoiceExtractor:
    """Extract structured data from invoices using OpenAI Vision API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the extractor with OpenAI API key
        
        Args:
            api_key: OpenAI API key (if None, loads from environment)
        """
        load_dotenv()
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass it to the constructor."
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.extraction_prompt = self._create_extraction_prompt()
    
    def _create_extraction_prompt(self) -> str:
        """Create the prompt for invoice data extraction"""
        return """
        You are an expert at extracting structured data from invoices. 
        Analyze this invoice image and extract ALL the following information in JSON format.
        
        Required fields:
        - invoice_number: The invoice or reference number
        - date: Invoice date (format as YYYY-MM-DD)
        - vendor_name: Name of the company/vendor issuing the invoice
        - total_amount: Total amount due (numeric value only, no currency symbols)
        - currency: Currency code (e.g., USD, EUR, GBP)
        - line_items: Array of items with:
          - description: Item description
          - quantity: Quantity ordered
          - unit_price: Price per unit
          - line_total: Total for this line item
        
        Return ONLY valid JSON with this exact structure:
        {
          "invoice_number": "...",
          "date": "YYYY-MM-DD",
          "vendor_name": "...",
          "total_amount": 0.00,
          "currency": "USD",
          "line_items": [
            {
              "description": "...",
              "quantity": 0,
              "unit_price": 0.00,
              "line_total": 0.00
            }
          ]
        }
        
        If a field cannot be found, use null for strings or 0 for numbers.
        Ensure all numeric values are actual numbers, not strings.
        """
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_from_image(self, image_path: str, retry_count: int = 2) -> Optional[Dict]:
        """
        Extract invoice data from an image using OpenAI Vision API
        
        Args:
            image_path: Path to the invoice image
            retry_count: Number of retry attempts on failure
            
        Returns:
            Dictionary containing extracted invoice data or None on failure
        """
        logger.info(f"Processing: {image_path}")
        
        for attempt in range(retry_count + 1):
            try:
                # Encode image
                base64_image = self.encode_image(image_path)
                
                # Call OpenAI Vision API
                response = self.client.chat.completions.create(
                    model="gpt-4o",  # Using GPT-4 with vision
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": self.extraction_prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,
                    temperature=0  # Deterministic output
                )
                
                # Parse response
                content = response.choices[0].message.content
                
                # Extract JSON from response (handle markdown code blocks)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # Parse JSON
                extracted_data = json.loads(content)
                
                # Add metadata
                extracted_data['source_file'] = os.path.basename(image_path)
                extracted_data['extraction_timestamp'] = datetime.now().isoformat()
                extracted_data['confidence'] = 'high'
                
                logger.info(f"Successfully extracted data from {image_path}")
                return extracted_data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error (attempt {attempt + 1}): {e}")
                if attempt == retry_count:
                    logger.error(f"Failed to parse JSON after {retry_count + 1} attempts")
                    return self._create_error_entry(image_path, f"JSON parsing error: {e}")
                    
            except Exception as e:
                logger.error(f"Error processing {image_path} (attempt {attempt + 1}): {e}")
                if attempt == retry_count:
                    return self._create_error_entry(image_path, str(e))
        
        return None
    
    def _create_error_entry(self, image_path: str, error_msg: str) -> Dict:
        """Create an error entry for failed extractions"""
        return {
            'source_file': os.path.basename(image_path),
            'invoice_number': 'ERROR',
            'date': None,
            'vendor_name': 'EXTRACTION_FAILED',
            'total_amount': 0.0,
            'currency': 'USD',
            'line_items': [],
            'extraction_timestamp': datetime.now().isoformat(),
            'confidence': 'failed',
            'error': error_msg
        }
    
    def extract_from_pdf(self, pdf_path: str) -> Optional[Dict]:
        """
        Extract invoice data from PDF by converting to images
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted invoice data
        """
        try:
            from pdf2image import convert_from_path
            
            # Convert PDF to images (first page only for invoices)
            images = convert_from_path(pdf_path, first_page=1, last_page=1)
            
            if not images:
                logger.error(f"Could not convert PDF to image: {pdf_path}")
                return self._create_error_entry(pdf_path, "PDF conversion failed")
            
            # Save temporary image
            temp_image_path = pdf_path.replace('.pdf', '_temp.jpg')
            images[0].save(temp_image_path, 'JPEG')
            
            # Extract from image
            result = self.extract_from_image(temp_image_path)
            
            # Update source file to original PDF
            if result:
                result['source_file'] = os.path.basename(pdf_path)
            
            # Clean up temp file
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            
            return result
            
        except ImportError:
            logger.error("pdf2image not installed. Install with: pip install pdf2image")
            return self._create_error_entry(pdf_path, "pdf2image not installed")
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return self._create_error_entry(pdf_path, str(e))
    
    def process_folder(self, folder_path: str, output_format: str = 'both') -> Dict[str, pd.DataFrame]:
        """
        Process all invoices in a folder
        
        Args:
            folder_path: Path to folder containing invoices
            output_format: 'csv', 'json', or 'both'
            
        Returns:
            Dictionary with DataFrames for invoices and line_items
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # Supported file extensions
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        
        # Find all invoice files
        invoice_files = [
            f for f in folder_path.iterdir()
            if f.suffix.lower() in supported_extensions
        ]
        
        if not invoice_files:
            logger.warning(f"No invoice files found in {folder_path}")
            return {'invoices': pd.DataFrame(), 'line_items': pd.DataFrame()}
        
        logger.info(f"Found {len(invoice_files)} invoice files to process")
        
        # Extract data from all invoices
        all_data = []
        for file_path in invoice_files:
            if file_path.suffix.lower() == '.pdf':
                data = self.extract_from_pdf(str(file_path))
            else:
                data = self.extract_from_image(str(file_path))
            
            if data:
                all_data.append(data)
        
        logger.info(f"Successfully processed {len(all_data)} invoices")
        
        # Convert to DataFrames
        dataframes = self._create_dataframes(all_data)
        
        return dataframes
    
    def _create_dataframes(self, data: List[Dict]) -> Dict[str, pd.DataFrame]:
        """
        Convert extracted data to normalized DataFrames
        
        Args:
            data: List of extracted invoice dictionaries
            
        Returns:
            Dictionary with 'invoices' and 'line_items' DataFrames
        """
        invoices_data = []
        line_items_data = []
        
        for idx, invoice in enumerate(data, 1):
            # Create invoice record
            invoice_record = {
                'invoice_id': idx,
                'invoice_number': invoice.get('invoice_number'),
                'date': invoice.get('date'),
                'vendor_name': invoice.get('vendor_name'),
                'total_amount': invoice.get('total_amount', 0),
                'currency': invoice.get('currency', 'USD'),
                'source_file': invoice.get('source_file'),
                'extraction_timestamp': invoice.get('extraction_timestamp'),
                'confidence': invoice.get('confidence', 'medium'),
            }
            
            if 'error' in invoice:
                invoice_record['error'] = invoice['error']
            
            invoices_data.append(invoice_record)
            
            # Create line items records
            for item_idx, item in enumerate(invoice.get('line_items', []), 1):
                line_item = {
                    'line_item_id': f"{idx}_{item_idx}",
                    'invoice_id': idx,
                    'description': item.get('description'),
                    'quantity': item.get('quantity', 0),
                    'unit_price': item.get('unit_price', 0),
                    'line_total': item.get('line_total', 0)
                }
                line_items_data.append(line_item)
        
        # Create DataFrames
        invoices_df = pd.DataFrame(invoices_data)
        line_items_df = pd.DataFrame(line_items_data)
        
        # Validate and normalize
        invoices_df = self._validate_invoices_df(invoices_df)
        line_items_df = self._validate_line_items_df(line_items_df)
        
        return {
            'invoices': invoices_df,
            'line_items': line_items_df
        }
    
    def _validate_invoices_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize invoices DataFrame"""
        if df.empty:
            return df
        
        # Convert date to datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Ensure numeric fields are numeric
        numeric_fields = ['total_amount', 'invoice_id']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
        
        # Fill NaN values appropriately
        df['currency'] = df['currency'].fillna('USD')
        df['confidence'] = df['confidence'].fillna('low')
        
        return df
    
    def _validate_line_items_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize line items DataFrame"""
        if df.empty:
            return df
        
        # Ensure numeric fields are numeric
        numeric_fields = ['quantity', 'unit_price', 'line_total', 'invoice_id']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)
        
        return df
    
    def save_to_csv(self, dataframes: Dict[str, pd.DataFrame], output_dir: str = 'output'):
        """
        Save DataFrames to CSV files
        
        Args:
            dataframes: Dictionary with invoices and line_items DataFrames
            output_dir: Directory to save CSV files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save invoices
        invoices_path = output_path / 'invoices.csv'
        dataframes['invoices'].to_csv(invoices_path, index=False)
        logger.info(f"Saved invoices to {invoices_path}")
        
        # Save line items
        line_items_path = output_path / 'line_items.csv'
        dataframes['line_items'].to_csv(line_items_path, index=False)
        logger.info(f"Saved line items to {line_items_path}")
        
        # Save summary statistics
        self._save_summary(dataframes, output_path)
    
    def _save_summary(self, dataframes: Dict[str, pd.DataFrame], output_path: Path):
        """Save summary statistics"""
        invoices_df = dataframes['invoices']
        
        if invoices_df.empty:
            return
        
        summary = {
            'total_invoices': len(invoices_df),
            'total_amount': float(invoices_df['total_amount'].sum()),
            'unique_vendors': int(invoices_df['vendor_name'].nunique()),
            'date_range': {
                'start': str(invoices_df['date'].min()) if 'date' in invoices_df else None,
                'end': str(invoices_df['date'].max()) if 'date' in invoices_df else None
            },
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        summary_path = output_path / 'summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Saved summary to {summary_path}")


if __name__ == "__main__":
    # Example usage
    extractor = InvoiceExtractor()
    
    # Process folder of invoices
    invoice_folder = "data/invoices"  # Update this path
    results = extractor.process_folder(invoice_folder)
    
    # Save to CSV
    extractor.save_to_csv(results, output_dir='output')
    
    # Display results
    print("\n=== INVOICES ===")
    print(results['invoices'].head())
    
    print("\n=== LINE ITEMS ===")
    print(results['line_items'].head())
