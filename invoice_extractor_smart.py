"""
Smart Invoice Data Extraction Pipeline with Template Learning
Learns invoice formats and reuses patterns for efficiency
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import pytesseract
from PIL import Image

from template_manager import TemplateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmartInvoiceExtractor:
    """
    Smart Invoice Extractor with Template Learning
    
    Features:
    - Learns invoice formats automatically
    - Uses regex patterns for known formats (fast & cheap)
    - Falls back to GPT-4 Vision for new formats
    - Caches templates for future use
    """
    
    def __init__(self, api_key: Optional[str] = None, use_templates: bool = True):
        """
        Initialize the smart extractor
        
        Args:
            api_key: OpenAI API key (if None, loads from environment)
            use_templates: Whether to use template learning (default: True)
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
        
        # Template management
        self.use_templates = use_templates
        self.template_manager = TemplateManager() if use_templates else None
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'template_extractions': 0,
            'gpt_extractions': 0,
            'failed_extractions': 0,
            'total_api_cost': 0.0
        }
    
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
    
    def extract_ocr_text(self, image_path: str) -> Optional[str]:
        """
        Extract text from image using OCR (Tesseract)
        This is fast and free, used for template matching
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text or None
        """
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
            return None
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_with_gpt(self, image_path: str, retry_count: int = 2) -> Optional[Dict]:
        """
        Extract invoice data using GPT-4 Vision API
        
        Args:
            image_path: Path to the invoice image
            retry_count: Number of retry attempts
            
        Returns:
            Dictionary containing extracted invoice data or None
        """
        logger.info(f"[GPT] Processing: {image_path}")
        
        for attempt in range(retry_count + 1):
            try:
                # Encode image
                base64_image = self.encode_image(image_path)
                
                # Call OpenAI Vision API
                response = self.client.chat.completions.create(
                    model="gpt-4o",
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
                    temperature=0
                )
                
                # Parse response
                content = response.choices[0].message.content
                
                # Extract JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # Parse JSON
                extracted_data = json.loads(content)
                
                # Add metadata
                extracted_data['source_file'] = os.path.basename(image_path)
                extracted_data['extraction_timestamp'] = datetime.now().isoformat()
                extracted_data['extraction_method'] = 'gpt'
                extracted_data['confidence'] = 'high'
                
                # Estimate cost (rough estimate: $0.01-0.03 per invoice)
                self.stats['total_api_cost'] += 0.02
                self.stats['gpt_extractions'] += 1
                
                logger.info(f"[GPT] Successfully extracted from {image_path}")
                return extracted_data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error (attempt {attempt + 1}): {e}")
                if attempt == retry_count:
                    self.stats['failed_extractions'] += 1
                    return self._create_error_entry(image_path, f"JSON error: {e}")
                    
            except Exception as e:
                logger.error(f"Error processing {image_path} (attempt {attempt + 1}): {e}")
                if attempt == retry_count:
                    self.stats['failed_extractions'] += 1
                    return self._create_error_entry(image_path, str(e))
        
        return None
    
    def extract_from_image(self, image_path: str) -> Optional[Dict]:
        """
        Smart extraction: Try template first, fallback to GPT
        
        Args:
            image_path: Path to invoice image
            
        Returns:
            Extracted data dictionary
        """
        self.stats['total_processed'] += 1
        
        # Step 1: Try OCR + Template matching (fast & free)
        if self.use_templates:
            ocr_text = self.extract_ocr_text(image_path)
            
            if ocr_text:
                # Try to find matching template
                template = self.template_manager.find_matching_template(ocr_text)
                
                if template:
                    logger.info(
                        f"[TEMPLATE] Found match for {image_path} "
                        f"(template: {template.template_id})"
                    )
                    
                    # Extract using template
                    extracted_data = self.template_manager.extract_with_template(
                        template, ocr_text
                    )
                    
                    if extracted_data:
                        # Success with template!
                        extracted_data['source_file'] = os.path.basename(image_path)
                        extracted_data['extraction_timestamp'] = datetime.now().isoformat()
                        extracted_data['confidence'] = 'high'
                        extracted_data['ocr_text'] = ocr_text  # Store for learning
                        
                        self.stats['template_extractions'] += 1
                        
                        logger.info(
                            f"[TEMPLATE] ✓ Successfully extracted using template "
                            f"(saved ~$0.02 API cost)"
                        )
                        return extracted_data
                    else:
                        logger.warning(
                            f"[TEMPLATE] ✗ Template extraction failed, falling back to GPT"
                        )
        
        # Step 2: Fallback to GPT-4 Vision (accurate but costly)
        extracted_data = self.extract_with_gpt(image_path)
        
        # Step 3: Learn from GPT extraction for future use
        if extracted_data and self.use_templates and 'error' not in extracted_data:
            ocr_text = self.extract_ocr_text(image_path)
            if ocr_text:
                template_id = self.template_manager.learn_template(
                    ocr_text, extracted_data
                )
                extracted_data['learned_template'] = template_id
                logger.info(f"[LEARNING] Learned template: {template_id}")
        
        return extracted_data
    
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
            'extraction_method': 'failed',
            'confidence': 'failed',
            'error': error_msg
        }
    
    def extract_from_pdf(self, pdf_path: str) -> Optional[Dict]:
        """Extract from PDF by converting to image"""
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(pdf_path, first_page=1, last_page=1)
            
            if not images:
                logger.error(f"Could not convert PDF: {pdf_path}")
                return self._create_error_entry(pdf_path, "PDF conversion failed")
            
            # Save temporary image
            temp_image_path = pdf_path.replace('.pdf', '_temp.jpg')
            images[0].save(temp_image_path, 'JPEG')
            
            # Extract from image
            result = self.extract_from_image(temp_image_path)
            
            if result:
                result['source_file'] = os.path.basename(pdf_path)
            
            # Clean up
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return self._create_error_entry(pdf_path, str(e))
    
    def process_folder(self, folder_path: str) -> Dict[str, pd.DataFrame]:
        """
        Process all invoices in a folder
        
        Args:
            folder_path: Path to folder containing invoices
            
        Returns:
            Dictionary with DataFrames for invoices and line_items
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        
        invoice_files = [
            f for f in folder_path.iterdir()
            if f.suffix.lower() in supported_extensions
        ]
        
        if not invoice_files:
            logger.warning(f"No invoice files found in {folder_path}")
            return {'invoices': pd.DataFrame(), 'line_items': pd.DataFrame()}
        
        logger.info(f"Found {len(invoice_files)} invoice files to process")
        
        # Reset stats
        self.stats = {
            'total_processed': 0,
            'template_extractions': 0,
            'gpt_extractions': 0,
            'failed_extractions': 0,
            'total_api_cost': 0.0
        }
        
        # Extract data from all invoices
        all_data = []
        for file_path in invoice_files:
            if file_path.suffix.lower() == '.pdf':
                data = self.extract_from_pdf(str(file_path))
            else:
                data = self.extract_from_image(str(file_path))
            
            if data:
                all_data.append(data)
        
        # Print statistics
        self.print_statistics()
        
        # Convert to DataFrames
        from invoice_extractor import InvoiceExtractor
        dummy_extractor = InvoiceExtractor()
        dataframes = dummy_extractor._create_dataframes(all_data)
        
        return dataframes
    
    def print_statistics(self):
        """Print extraction statistics"""
        print("\n" + "=" * 60)
        print("SMART EXTRACTION STATISTICS")
        print("=" * 60)
        print(f"Total Processed: {self.stats['total_processed']}")
        print(f"Template Extractions: {self.stats['template_extractions']} "
              f"(fast & free)")
        print(f"GPT Extractions: {self.stats['gpt_extractions']} "
              f"(accurate but costly)")
        print(f"Failed Extractions: {self.stats['failed_extractions']}")
        
        if self.stats['total_processed'] > 0:
            template_pct = (self.stats['template_extractions'] / 
                          self.stats['total_processed'] * 100)
            print(f"\nTemplate Usage: {template_pct:.1f}%")
            
        print(f"\nEstimated API Cost: ${self.stats['total_api_cost']:.2f}")
        
        # Calculate savings
        if self.stats['template_extractions'] > 0:
            saved_cost = self.stats['template_extractions'] * 0.02
            print(f"Cost Saved by Templates: ${saved_cost:.2f}")
        
        print("=" * 60)
    
    def save_to_csv(self, dataframes: Dict[str, pd.DataFrame], output_dir: str = 'output'):
        """Save DataFrames to CSV files"""
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
        
        # Save statistics
        stats_path = output_path / 'extraction_stats.json'
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        logger.info(f"Saved statistics to {stats_path}")
        
        # Save template stats if available
        if self.template_manager:
            self.template_manager.print_statistics()


if __name__ == "__main__":
    # Example usage
    extractor = SmartInvoiceExtractor(use_templates=True)
    
    # Process folder
    invoice_folder = "data/invoices"
    results = extractor.process_folder(invoice_folder)
    
    # Save results
    extractor.save_to_csv(results, output_dir='output')
    
    print("\n=== RESULTS ===")
    print(results['invoices'].head())
