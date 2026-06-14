from django.test import TestCase

from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from apps.groups.models import Group
from apps.importer.detector import detect_anomalies, get_fuzzy_match

class AnomalyDetectorTestCase(TestCase):
    def setUp(self):
        # Create group & members for reference (though detector primarily uses names list)
        self.aisha = User.objects.create_user(username='aisha')
        self.rohan = User.objects.create_user(username='rohan')
        self.group = Group.objects.create(name='Flat 22B', created_by=self.aisha)

    def test_fuzzy_name_matching(self):
        known = ['aisha', 'rohan', 'priya', 'meera', 'sam', 'dev']
        self.assertEqual(get_fuzzy_match('Rohn', known), 'rohan')
        self.assertEqual(get_fuzzy_match('Aisha  ', known), 'aisha')
        self.assertEqual(get_fuzzy_match('unknown_person', known), None)

    def test_detect_anomalies_basic(self):
        # Test exact duplicate, misspelled payer, bad date, and bad amount
        test_rows = [
            # 1. Valid row
            {
                'date': '2024-02-10', 'description': 'Groceries', 'amount': '1200',
                'currency': 'INR', 'paid_by': 'Rohan', 'split_type': 'equal',
                'participants': 'Aisha, Rohan, Priya', 'notes': ''
            },
            # 2. Exact Duplicate of row 1
            {
                'date': '2024-02-10', 'description': 'Groceries', 'amount': '1200',
                'currency': 'INR', 'paid_by': 'Rohan', 'split_type': 'equal',
                'participants': 'Aisha, Rohan, Priya', 'notes': ''
            },
            # 3. Misspelled payer (Rohn) and inconsistent date format
            {
                'date': '12/02/2024', 'description': 'Internet', 'amount': 'Rs.1500',
                'currency': 'INR', 'paid_by': 'Rohn', 'split_type': 'equal',
                'participants': 'Aisha, Rohan, Priya', 'notes': ''
            },
            # 4. Settlement recorded as expense
            {
                'date': '2024-02-20', 'description': 'Rohan paid Aisha back', 'amount': '500',
                'currency': 'INR', 'paid_by': 'Rohan', 'split_type': 'equal',
                'participants': 'Aisha', 'notes': 'settlement'
            }
        ]

        anoms = detect_anomalies(test_rows, self.group.id)
        
        # We expect:
        # Row 2: Exact Duplicate
        # Row 3: Inconsistent Date Format, Inconsistent Amount Format, Misspelled Payer Name
        # Row 4: Settlement as Expense
        
        issue_types = [a['issue_type'] for a in anoms]
        
        self.assertIn('Exact Duplicate', issue_types)
        self.assertIn('Inconsistent Date Format', issue_types)
        self.assertIn('Inconsistent Amount Format', issue_types)
        self.assertIn('Misspelled Payer Name', issue_types)
        self.assertIn('Settlement as Expense', issue_types)

        # Confirm duplicates got flagged for Row 2
        dup_anoms = [a for a in anoms if a['issue_type'] == 'Exact Duplicate']
        self.assertEqual(dup_anoms[0]['row_number'], 2)

