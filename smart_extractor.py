"""
Smart Invoice Extractor with Template Learning
Uses GPT-4 Vision for first extraction, then learns templates for cost optimization
"""

import os
import json
import base64
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# Try to import OCR libraries
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TemplateManager:
    """Manage invoice templates for efficient extraction"""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """Load existing templates from disk"""
        templates = {}
        for template_file in self.templates_dir.glob("*.json"):
            with open(template_file, 'r') as f:
                template = json.load(f)
                templates[template['template_id']] = template
        return templates
    
    def get_image_hash(self, image_path: str) -> str:
        """Generate hash of image for similarity detection"""
        with open(image_path, 'rb') as f:
            # Use first 10KB for quick hash (layout usually visible in header)
            header = f.read(10240)
            return hashlib.md5(header).hexdigest()
    
    def find_matching_template(self, image_path: str, ocr_text: str = None) -> Optional[Dict]:
        """Find a matching template based on image similarity or text patterns"""
        if not self.templates:
            return None
        
        # Method 1: Hash-based matching (for identical formats)
        img_hash = self.get_image_hash(image_path)
        
        for template_id, template in self.templates.items():
            # Check hash similarity (for exact format matches)
            if template.get('image_hash') == img_hash:
                logger.info(f"✓ Found exact template match: {template['vendor_name']}")
                return template
            
            # Method 2: OCR text pattern matching (if available)
            if ocr_text and TESSERACT_AVAILABLE:
                # Check for vendor name patterns
                if template.get('vendor_name', '').lower() in ocr_text.lower():
                    # Check for layout similarity
                    template_keywords = template.get('layout_keywords', [])
                    matches = sum(1 for kw in template_keywords if kw.lower() in ocr_text.lower())
                    
                    if matches >= len(template_keywords) * 0.7:  # 70% match threshold
                        logger.info(f"✓ Found template match via OCR: {template['vendor_name']}")
                        return template
        
        return None
    
    def save_template(self, template_data: Dict, image_path: str):
        """Save a new template learned from extraction"""
        template_id = f"template_{len(self.templates) + 1}"
        
        template = {
            'template_id': template_id,
            'vendor_name': template_data.get('vendor_name'),
            'image_hash': self.get_image_hash(image_path),
            'date_pattern': template_data.get('date'),
            'amount_pattern': template_data.get('total_amount'),
            'layout_keywords': self._extract_layout_keywords(template_data),
            'extraction_method': 'gpt4_vision',
            'created_at': datetime.now().isoformat(),
            'usage_count': 0
        }
        
        # Save to disk
        template_file = self.templates_dir / f"{template_id}.json"
        with open(template_file, 'w') as f:
            json.dump(template, f, indent=2)
        
        self.templates[template_id] = template
        logger.info(f"✓ Template saved: {template_id} for {template['vendor_name']}")
    
    def _extract_layout_keywords(self, data: Dict) -> List[str]:
        """Extract keywords that indicate this invoice format"""
        keywords = []
        
        if data.get('vendor_name'):
            keywords.append(data['vendor_name'])
        
        if data.get('invoice_number'):
            keywords.append('invoice')
        
        keywords.extend(['total', 'amount', 'date', 'qty', 'quantity', 'price'])
        
        return keywords
    
    def increment_usage(self, template_id: str):
        """Track template usage for statistics"""
        if template_id in self.templates:
            self.templates[template_id]['usage_count'] = self.templates[template_id].get('usage_count', 0) + 1
            
            # Update on disk
            template_file = self.templates_dir / f"{template_id}.json"
            with open(template_file, 'w') as f:
                json.dump(self.templates[template_id], f, indent=2)


class SmartInvoiceExtractor:
    """Smart extractor that learns templates to minimize API costs"""
    
    def __init__(self, api_key: Optional[str] = None):
        load_dotenv()
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.template_manager = TemplateManager()
        self.stats = {
            'gpt_calls': 0,
            'template_matches': 0,
            'ocr_extractions': 0,
            'total_cost': 0.0
        }
    
    def extract_with_ocr(self, image_path: str) -> Optional[str]:
        """Extract text using Tesseract OCR"""
        if not TESSERACT_AVAILABLE:
            return None
        
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
            return None
    
    def extract_with_template(self, template: Dict, ocr_text: str) -> Optional[Dict]:
        """Extract data using a learned template (regex patterns)"""
        if not ocr_text:
            return None
        
        try:
            import re
            
            # This is a simplified example - in production, you'd have more sophisticated patterns
            extracted = {
                'vendor_name': template['vendor_name'],
                'invoice_number': None,
                'date': None,
                'total_amount': 0.0,
                'currency': 'USD',
                'line_items': []
            }
            
            # Extract invoice number
            inv_patterns = [r'invoice[#:\s]+(\S+)', r'inv[#:\s]+(\S+)', r'#\s*(\d+)']
            for pattern in inv_patterns:
                match = re.search(pattern, ocr_text, re.IGNORECASE)
                if match:
                    extracted['invoice_number'] = match.group(1)
                    break
            
            # Extract date
            date_patterns = [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})'
            ]
            for pattern in date_patterns:
                match = re.search(pattern, ocr_text)
                if match:
                    extracted['date'] = match.group(1)
                    break
            
            # Extract total amount
            amount_patterns = [
                r'total[:\s]+\$?(\d+\.?\d*)',
                r'amount[:\s]+\$?(\d+\.?\d*)',
                r'\$(\d+\.\d{2})\s*$'
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, ocr_text, re.IGNORECASE)
                if match:
                    extracted['total_amount'] = float(match.group(1))
                    break
            
            self.stats['ocr_extractions'] += 1
            return extracted
            
        except Exception as e:
            logger.warning(f"Template extraction failed: {e}")
            return None
    
    def extract_with_gpt(self, image_path: str) -> Optional[Dict]:
        """Extract using GPT-4 Vision (full extraction)"""
        logger.info(f"[GPT] Processing: {image_path}")
        
        try:
            # Encode image
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            
            # Extraction prompt
            prompt = """
            Extract the following information from this invoice in JSON format:
            - invoice_number
            - date (YYYY-MM-DD)
            - vendor_name
            - total_amount (number only)
            - currency
            - line_items: [{description, quantity, unit_price, line_total}]
            
            Return ONLY valid JSON.
            """
            
            # Call GPT-4 Vision
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0
            )
            
            # Parse response
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            extracted_data = json.loads(content)
            
            # Update stats
            self.stats['gpt_calls'] += 1
            self.stats['total_cost'] += 0.02  # Approximate cost
            
            # Learn template for future use
            self.template_manager.save_template(extracted_data, image_path)
            
            logger.info(f"✓ GPT extraction successful (Cost: ~$0.02)")
            return extracted_data
            
        except Exception as e:
            logger.error(f"GPT extraction failed: {e}")
            return None
    
    def extract_from_invoice(self, image_path: str) -> Optional[Dict]:
        """
        Smart extraction with template learning
        
        Flow:
        1. Try to find matching template
        2. If template found, use OCR + regex (fast & cheap)
        3. If no template, use GPT-4 Vision and learn template
        """
        logger.info(f"Processing: {image_path}")
        
        # Step 1: Extract OCR text (if available)
        ocr_text = self.extract_with_ocr(image_path) if TESSERACT_AVAILABLE else None
        
        # Step 2: Try to find matching template
        template = self.template_manager.find_matching_template(image_path, ocr_text)
        
        if template:
            # Use template-based extraction (cheap!)
            logger.info(f"✓ Using template: {template['vendor_name']} (Cost: ~$0.001)")
            extracted = self.extract_with_template(template, ocr_text)
            
            if extracted:
                self.template_manager.increment_usage(template['template_id'])
                self.stats['template_matches'] += 1
                self.stats['total_cost'] += 0.001
                
                extracted['source_file'] = os.path.basename(image_path)
                extracted['extraction_method'] = 'template'
                extracted['extraction_timestamp'] = datetime.now().isoformat()
                return extracted
        
        # Step 3: No template found, use GPT-4 Vision
        logger.info("No template match, using GPT-4 Vision...")
        extracted = self.extract_with_gpt(image_path)
        
        if extracted:
            extracted['source_file'] = os.path.basename(image_path)
            extracted['extraction_method'] = 'gpt4_vision'
            extracted['extraction_timestamp'] = datetime.now().isoformat()
        
        return extracted
    
    def process_folder(self, folder_path: str) -> Dict[str, pd.DataFrame]:
        """Process all invoices in folder with smart extraction"""
        folder_path = Path(folder_path)
        
        # Find invoice files
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        invoice_files = [f for f in folder_path.iterdir() if f.suffix.lower() in supported_extensions]
        
        logger.info(f"Found {len(invoice_files)} invoice files to process")
        
        # Process each invoice
        all_data = []
        for file_path in invoice_files:
            data = self.extract_from_invoice(str(file_path))
            if data:
                all_data.append(data)
        
        # Print cost savings summary
        self.print_cost_summary()
        
        # Convert to DataFrames
        return self._create_dataframes(all_data)
    
    def print_cost_summary(self):
        """Print cost analysis and savings"""
        print("\n" + "="*60)
        print("COST ANALYSIS & SAVINGS")
        print("="*60)
        print(f"GPT-4 Vision calls: {self.stats['gpt_calls']} × $0.02 = ${self.stats['gpt_calls'] * 0.02:.2f}")
        print(f"Template matches: {self.stats['template_matches']} × $0.001 = ${self.stats['template_matches'] * 0.001:.3f}")
        print(f"OCR extractions: {self.stats['ocr_extractions']}")
        print(f"\nTotal cost: ${self.stats['total_cost']:.3f}")
        
        # Calculate savings
        total_invoices = self.stats['gpt_calls'] + self.stats['template_matches']
        if total_invoices > 0:
            without_templates = total_invoices * 0.02
            savings = without_templates - self.stats['total_cost']
            savings_pct = (savings / without_templates) * 100 if without_templates > 0 else 0
            
            print(f"\nWithout templates: ${without_templates:.2f}")
            print(f"💰 Savings: ${savings:.3f} ({savings_pct:.1f}%)")
    
    def _create_dataframes(self, data: List[Dict]) -> Dict[str, pd.DataFrame]:
        """Convert to DataFrames (same as original)"""
        invoices_data = []
        line_items_data = []
        
        for idx, invoice in enumerate(data, 1):
            invoice_record = {
                'invoice_id': idx,
                'invoice_number': invoice.get('invoice_number'),
                'date': invoice.get('date'),
                'vendor_name': invoice.get('vendor_name'),
                'total_amount': invoice.get('total_amount', 0),
                'currency': invoice.get('currency', 'USD'),
                'source_file': invoice.get('source_file'),
                'extraction_method': invoice.get('extraction_method'),
                'extraction_timestamp': invoice.get('extraction_timestamp'),
            }
            invoices_data.append(invoice_record)
            
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
        
        return {
            'invoices': pd.DataFrame(invoices_data),
            'line_items': pd.DataFrame(line_items_data)
        }
    
    def save_to_csv(self, dataframes: Dict[str, pd.DataFrame], output_dir: str = 'output'):
        """Save to CSV"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        dataframes['invoices'].to_csv(output_path / 'invoices.csv', index=False)
        dataframes['line_items'].to_csv(output_path / 'line_items.csv', index=False)
        
        logger.info(f"✓ Data saved to {output_dir}/")


if __name__ == "__main__":
    extractor = SmartInvoiceExtractor()
    results = extractor.process_folder("data/invoices")
    extractor.save_to_csv(results)
    
    print("\n=== RESULTS ===")
    print(results['invoices'])
