"""
Template Manager - Learn and reuse invoice formats
Caches patterns for efficient extraction of repeat invoice formats
"""

import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class InvoiceTemplate:
    """Represents a learned invoice template/pattern"""
    
    def __init__(self, template_id: str, vendor_name: str, layout_hash: str):
        self.template_id = template_id
        self.vendor_name = vendor_name
        self.layout_hash = layout_hash
        self.patterns = {}
        self.field_positions = {}
        self.success_count = 0
        self.failure_count = 0
        self.created_at = datetime.now().isoformat()
        self.last_used = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert template to dictionary"""
        return {
            'template_id': self.template_id,
            'vendor_name': self.vendor_name,
            'layout_hash': self.layout_hash,
            'patterns': self.patterns,
            'field_positions': self.field_positions,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'created_at': self.created_at,
            'last_used': self.last_used
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create template from dictionary"""
        template = cls(
            data['template_id'],
            data['vendor_name'],
            data['layout_hash']
        )
        template.patterns = data.get('patterns', {})
        template.field_positions = data.get('field_positions', {})
        template.success_count = data.get('success_count', 0)
        template.failure_count = data.get('failure_count', 0)
        template.created_at = data.get('created_at')
        template.last_used = data.get('last_used')
        return template


class TemplateManager:
    """Manages invoice templates and pattern matching"""
    
    def __init__(self, templates_file: str = "output/invoice_templates.json"):
        self.templates_file = Path(templates_file)
        self.templates: Dict[str, InvoiceTemplate] = {}
        self.load_templates()
    
    def load_templates(self):
        """Load existing templates from file"""
        if self.templates_file.exists():
            try:
                with open(self.templates_file, 'r') as f:
                    data = json.load(f)
                
                for template_data in data.get('templates', []):
                    template = InvoiceTemplate.from_dict(template_data)
                    self.templates[template.template_id] = template
                
                logger.info(f"Loaded {len(self.templates)} templates")
            except Exception as e:
                logger.error(f"Error loading templates: {e}")
    
    def save_templates(self):
        """Save templates to file"""
        try:
            self.templates_file.parent.mkdir(exist_ok=True)
            
            data = {
                'templates': [t.to_dict() for t in self.templates.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.templates_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.templates)} templates")
        except Exception as e:
            logger.error(f"Error saving templates: {e}")
    
    def extract_layout_features(self, text: str) -> str:
        """
        Extract layout features to create a fingerprint
        This helps identify if two invoices have the same format
        """
        # Normalize text
        normalized = re.sub(r'\d+', '#', text)  # Replace numbers with #
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        
        # Extract structure markers (keywords, labels)
        structure_words = re.findall(
            r'\b(invoice|bill|receipt|total|subtotal|tax|date|customer|vendor|'
            r'item|description|quantity|price|amount|number|no\.?|ref|reference)\b',
            normalized.lower()
        )
        
        # Create a structural fingerprint
        structure = ' '.join(sorted(set(structure_words)))
        
        # Hash it for quick comparison
        layout_hash = hashlib.md5(structure.encode()).hexdigest()
        
        return layout_hash
    
    def learn_template(self, ocr_text: str, extracted_data: Dict) -> str:
        """
        Learn a new template from successful extraction
        
        Args:
            ocr_text: Raw OCR text from the invoice
            extracted_data: Successfully extracted structured data
            
        Returns:
            template_id: ID of the learned template
        """
        layout_hash = self.extract_layout_features(ocr_text)
        vendor_name = extracted_data.get('vendor_name', 'Unknown')
        
        # Check if template already exists
        for template_id, template in self.templates.items():
            if template.layout_hash == layout_hash:
                # Update existing template
                self._update_template_patterns(template, ocr_text, extracted_data)
                template.success_count += 1
                template.last_used = datetime.now().isoformat()
                self.save_templates()
                logger.info(f"Updated existing template: {template_id}")
                return template_id
        
        # Create new template
        template_id = f"TPL_{layout_hash[:8]}_{len(self.templates) + 1}"
        template = InvoiceTemplate(template_id, vendor_name, layout_hash)
        
        # Learn patterns from this invoice
        self._update_template_patterns(template, ocr_text, extracted_data)
        template.success_count = 1
        
        self.templates[template_id] = template
        self.save_templates()
        
        logger.info(f"Learned new template: {template_id} for {vendor_name}")
        return template_id
    
    def _update_template_patterns(self, template: InvoiceTemplate, 
                                   ocr_text: str, extracted_data: Dict):
        """Update template patterns based on successful extraction"""
        
        # Learn regex patterns for each field
        for field, value in extracted_data.items():
            if field in ['line_items', 'source_file', 'extraction_timestamp', 
                        'confidence', 'error']:
                continue
            
            if value and str(value).strip():
                # Try to find the value in the OCR text and learn the pattern
                pattern = self._create_field_pattern(field, str(value), ocr_text)
                if pattern:
                    template.patterns[field] = pattern
    
    def _create_field_pattern(self, field: str, value: str, 
                              text: str) -> Optional[str]:
        """Create a regex pattern for extracting a field"""
        
        # Escape special regex characters in the value
        escaped_value = re.escape(value)
        
        # Try to find context around the value
        patterns = {
            'invoice_number': [
                r'invoice\s*(?:number|no\.?|#)?\s*:?\s*([A-Z0-9\-]+)',
                r'bill\s*(?:number|no\.?)?\s*:?\s*([A-Z0-9\-]+)',
                r'reference\s*:?\s*([A-Z0-9\-]+)',
            ],
            'date': [
                r'date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
            ],
            'total_amount': [
                r'total\s*:?\s*\$?\s*([\d,]+\.?\d*)',
                r'amount\s*(?:due)?\s*:?\s*\$?\s*([\d,]+\.?\d*)',
                r'grand\s*total\s*:?\s*\$?\s*([\d,]+\.?\d*)',
            ],
            'vendor_name': [
                r'^([A-Z][A-Za-z\s&]+(?:Inc|LLC|Corp|Ltd)?)',
                r'from\s*:?\s*([A-Z][A-Za-z\s&]+)',
            ]
        }
        
        # Try field-specific patterns
        if field in patterns:
            for pattern in patterns[field]:
                if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                    return pattern
        
        return None
    
    def find_matching_template(self, ocr_text: str) -> Optional[InvoiceTemplate]:
        """
        Find a matching template for the given OCR text
        
        Args:
            ocr_text: Raw OCR text from invoice
            
        Returns:
            Matching template or None
        """
        layout_hash = self.extract_layout_features(ocr_text)
        
        # Look for exact layout match
        for template in self.templates.values():
            if template.layout_hash == layout_hash:
                # Check confidence - only use if success rate > 70%
                total_attempts = template.success_count + template.failure_count
                if total_attempts > 0:
                    success_rate = template.success_count / total_attempts
                    if success_rate > 0.7:
                        logger.info(
                            f"Found matching template: {template.template_id} "
                            f"(success rate: {success_rate:.1%})"
                        )
                        return template
        
        return None
    
    def extract_with_template(self, template: InvoiceTemplate, 
                             ocr_text: str) -> Optional[Dict]:
        """
        Extract data using a known template
        
        Args:
            template: The template to use
            ocr_text: Raw OCR text
            
        Returns:
            Extracted data or None if extraction fails
        """
        try:
            extracted = {
                'template_id': template.template_id,
                'vendor_name': template.vendor_name,
                'extraction_method': 'template'
            }
            
            # Extract each field using learned patterns
            for field, pattern in template.patterns.items():
                match = re.search(pattern, ocr_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1) if match.groups() else match.group(0)
                    extracted[field] = value.strip()
            
            # Validate extraction
            required_fields = ['invoice_number', 'date', 'total_amount']
            if all(field in extracted for field in required_fields):
                template.success_count += 1
                template.last_used = datetime.now().isoformat()
                self.save_templates()
                
                logger.info(
                    f"Successfully extracted using template {template.template_id}"
                )
                return extracted
            else:
                logger.warning(
                    f"Template extraction incomplete, missing required fields"
                )
                return None
                
        except Exception as e:
            logger.error(f"Template extraction failed: {e}")
            template.failure_count += 1
            self.save_templates()
            return None
    
    def get_statistics(self) -> Dict:
        """Get template usage statistics"""
        stats = {
            'total_templates': len(self.templates),
            'templates': []
        }
        
        for template in self.templates.values():
            total = template.success_count + template.failure_count
            success_rate = (template.success_count / total * 100) if total > 0 else 0
            
            stats['templates'].append({
                'template_id': template.template_id,
                'vendor_name': template.vendor_name,
                'success_count': template.success_count,
                'failure_count': template.failure_count,
                'success_rate': f"{success_rate:.1f}%",
                'total_uses': total,
                'last_used': template.last_used
            })
        
        # Sort by usage
        stats['templates'].sort(key=lambda x: x['total_uses'], reverse=True)
        
        return stats
    
    def print_statistics(self):
        """Print template statistics"""
        stats = self.get_statistics()
        
        print("\n" + "=" * 60)
        print("TEMPLATE USAGE STATISTICS")
        print("=" * 60)
        print(f"\nTotal Templates: {stats['total_templates']}")
        
        if stats['templates']:
            print("\nTemplate Details:")
            print("-" * 60)
            for t in stats['templates']:
                print(f"\nTemplate: {t['template_id']}")
                print(f"  Vendor: {t['vendor_name']}")
                print(f"  Total Uses: {t['total_uses']}")
                print(f"  Success Rate: {t['success_rate']}")
                print(f"  Last Used: {t['last_used']}")
        else:
            print("\nNo templates learned yet.")


if __name__ == "__main__":
    # Demo usage
    manager = TemplateManager()
    manager.print_statistics()
