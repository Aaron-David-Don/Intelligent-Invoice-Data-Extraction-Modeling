"""
Evaluation Script - Measure extraction accuracy against ground truth
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List


class InvoiceEvaluator:
    """Evaluate extraction accuracy against ground truth labels"""
    
    def __init__(self, ground_truth_file: str):
        """
        Initialize evaluator with ground truth data
        
        Args:
            ground_truth_file: Path to JSON file with labeled data
        """
        with open(ground_truth_file, 'r') as f:
            self.ground_truth = json.load(f)
    
    def evaluate_field(self, predicted: str, actual: str, field_type: str = 'string') -> Dict:
        """
        Evaluate a single field
        
        Args:
            predicted: Predicted value
            actual: Ground truth value
            field_type: Type of field (string, number, date)
            
        Returns:
            Dictionary with match status and details
        """
        if field_type == 'string':
            # Case-insensitive, whitespace-normalized comparison
            pred_normalized = str(predicted).strip().lower()
            actual_normalized = str(actual).strip().lower()
            match = pred_normalized == actual_normalized
            
        elif field_type == 'number':
            # Numeric comparison with tolerance
            try:
                pred_float = float(predicted)
                actual_float = float(actual)
                match = abs(pred_float - actual_float) < 0.01
            except (ValueError, TypeError):
                match = False
                
        elif field_type == 'date':
            # Date comparison (normalized to YYYY-MM-DD)
            pred_str = str(predicted)[:10]  # Take first 10 chars
            actual_str = str(actual)[:10]
            match = pred_str == actual_str
            
        else:
            match = str(predicted) == str(actual)
        
        return {
            'match': match,
            'predicted': predicted,
            'actual': actual
        }
    
    def evaluate_invoice(self, invoice_data: Dict, source_file: str) -> Dict:
        """
        Evaluate a single invoice against ground truth
        
        Args:
            invoice_data: Extracted invoice data
            source_file: Source file name for lookup
            
        Returns:
            Evaluation results
        """
        # Find ground truth for this invoice
        gt = None
        for item in self.ground_truth:
            if item['source_file'] == source_file:
                gt = item
                break
        
        if not gt:
            return {
                'source_file': source_file,
                'error': 'No ground truth found'
            }
        
        # Evaluate each field
        results = {
            'source_file': source_file,
            'fields': {}
        }
        
        # Invoice number
        results['fields']['invoice_number'] = self.evaluate_field(
            invoice_data.get('invoice_number'),
            gt.get('invoice_number'),
            'string'
        )
        
        # Date
        results['fields']['date'] = self.evaluate_field(
            invoice_data.get('date'),
            gt.get('date'),
            'date'
        )
        
        # Vendor name
        results['fields']['vendor_name'] = self.evaluate_field(
            invoice_data.get('vendor_name'),
            gt.get('vendor_name'),
            'string'
        )
        
        # Total amount
        results['fields']['total_amount'] = self.evaluate_field(
            invoice_data.get('total_amount'),
            gt.get('total_amount'),
            'number'
        )
        
        # Calculate accuracy for this invoice
        total_fields = len(results['fields'])
        correct_fields = sum(1 for f in results['fields'].values() if f['match'])
        results['accuracy'] = correct_fields / total_fields if total_fields > 0 else 0
        results['correct_fields'] = correct_fields
        results['total_fields'] = total_fields
        
        return results
    
    def evaluate_all(self, invoices_csv: str) -> Dict:
        """
        Evaluate all invoices
        
        Args:
            invoices_csv: Path to extracted invoices CSV
            
        Returns:
            Overall evaluation results
        """
        invoices_df = pd.read_csv(invoices_csv)
        
        results = []
        for _, invoice in invoices_df.iterrows():
            result = self.evaluate_invoice(
                invoice.to_dict(),
                invoice['source_file']
            )
            results.append(result)
        
        # Calculate overall metrics
        total_invoices = len(results)
        total_fields = sum(r.get('total_fields', 0) for r in results)
        correct_fields = sum(r.get('correct_fields', 0) for r in results)
        
        overall_accuracy = correct_fields / total_fields if total_fields > 0 else 0
        
        # Field-level accuracy
        field_accuracy = {}
        for field in ['invoice_number', 'date', 'vendor_name', 'total_amount']:
            field_correct = sum(
                1 for r in results 
                if 'fields' in r and field in r['fields'] and r['fields'][field]['match']
            )
            field_total = sum(
                1 for r in results 
                if 'fields' in r and field in r['fields']
            )
            field_accuracy[field] = field_correct / field_total if field_total > 0 else 0
        
        summary = {
            'total_invoices': total_invoices,
            'total_fields': total_fields,
            'correct_fields': correct_fields,
            'overall_accuracy': overall_accuracy,
            'field_accuracy': field_accuracy,
            'invoice_results': results
        }
        
        return summary
    
    def print_report(self, results: Dict):
        """Print evaluation report"""
        print("=" * 60)
        print("EXTRACTION ACCURACY EVALUATION REPORT")
        print("=" * 60)
        
        print(f"\nTotal Invoices: {results['total_invoices']}")
        print(f"Total Fields: {results['total_fields']}")
        print(f"Correct Fields: {results['correct_fields']}")
        print(f"Overall Accuracy: {results['overall_accuracy']:.2%}")
        
        print("\n--- Field-Level Accuracy ---")
        for field, accuracy in results['field_accuracy'].items():
            print(f"{field:.<30} {accuracy:.2%}")
        
        print("\n--- Individual Invoice Results ---")
        for result in results['invoice_results']:
            if 'error' in result:
                print(f"\n{result['source_file']}: ERROR - {result['error']}")
            else:
                print(f"\n{result['source_file']}: {result['accuracy']:.2%} "
                      f"({result['correct_fields']}/{result['total_fields']})")
                
                for field, field_result in result['fields'].items():
                    status = "✓" if field_result['match'] else "✗"
                    print(f"  {status} {field}")
                    if not field_result['match']:
                        print(f"    Predicted: {field_result['predicted']}")
                        print(f"    Actual: {field_result['actual']}")
    
    def save_report(self, results: Dict, output_file: str):
        """Save evaluation report to JSON"""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Report saved to {output_file}")


def create_ground_truth_template(output_file: str = 'ground_truth_template.json'):
    """Create a template for ground truth labeling"""
    template = [
        {
            "source_file": "invoice_001.pdf",
            "invoice_number": "INV-12345",
            "date": "2025-03-15",
            "vendor_name": "Acme Corporation",
            "total_amount": 1250.00,
            "currency": "USD",
            "line_items": [
                {
                    "description": "Product A",
                    "quantity": 10,
                    "unit_price": 100.00,
                    "line_total": 1000.00
                },
                {
                    "description": "Product B",
                    "quantity": 5,
                    "unit_price": 50.00,
                    "line_total": 250.00
                }
            ]
        }
    ]
    
    with open(output_file, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"Ground truth template created: {output_file}")
    print("\nTo use:")
    print("1. Label 5-10 invoices manually")
    print("2. Fill in the template with correct values")
    print("3. Run evaluation: python evaluation.py")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'create-template':
        create_ground_truth_template()
    else:
        # Check if ground truth exists
        gt_file = 'ground_truth.json'
        if not Path(gt_file).exists():
            print(f"Ground truth file not found: {gt_file}")
            print("\nCreate a template with:")
            print("  python evaluation.py create-template")
            sys.exit(1)
        
        # Check if extracted data exists
        invoices_csv = 'output/invoices.csv'
        if not Path(invoices_csv).exists():
            print(f"Extracted data not found: {invoices_csv}")
            print("\nRun extraction first with:")
            print("  python main.py")
            sys.exit(1)
        
        # Run evaluation
        evaluator = InvoiceEvaluator(gt_file)
        results = evaluator.evaluate_all(invoices_csv)
        
        # Print report
        evaluator.print_report(results)
        
        # Save report
        evaluator.save_report(results, 'output/evaluation_report.json')
