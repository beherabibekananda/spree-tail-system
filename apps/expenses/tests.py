from django.test import TestCase

from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from apps.groups.models import Group, GroupMembership
from apps.expenses.models import Expense, ExpenseSplit, Settlement
from apps.expenses.balance import get_member_balance
from apps.expenses.utils import calculate_splits, get_active_participants_on_date

class BalanceEngineTestCase(TestCase):
    def setUp(self):
        # Create test users
        self.aisha = User.objects.create_user(username='aisha', password='password123')
        self.rohan = User.objects.create_user(username='rohan', password='password123')
        self.priya = User.objects.create_user(username='priya', password='password123')
        self.meera = User.objects.create_user(username='meera', password='password123')
        self.sam = User.objects.create_user(username='sam', password='password123')

        # Create group
        self.group = Group.objects.create(name='Flat 22B', created_by=self.aisha)

        # Create memberships:
        # Aisha, Rohan, Priya: joined Feb 1
        # Meera: joined Feb 1, left March 31
        # Sam: joined April 15
        GroupMembership.objects.create(user=self.aisha, group=self.group, joined_at=date(2024, 2, 1))
        GroupMembership.objects.create(user=self.rohan, group=self.group, joined_at=date(2024, 2, 1))
        GroupMembership.objects.create(user=self.priya, group=self.group, joined_at=date(2024, 2, 1))
        
        self.meera_membership = GroupMembership.objects.create(
            user=self.meera, group=self.group, 
            joined_at=date(2024, 2, 1), left_at=date(2024, 3, 31)
        )
        
        self.sam_membership = GroupMembership.objects.create(
            user=self.sam, group=self.group, 
            joined_at=date(2024, 4, 15)
        )

    def test_calculate_splits_equal_rounding(self):
        # Equal split of 10.00 among 3 participants
        # 10.00 / 3 = 3.33 each, remainder 0.01 goes to the first participant
        splits = calculate_splits(Decimal('10.00'), 'equal', [self.aisha.id, self.rohan.id, self.priya.id])
        self.assertEqual(splits[self.aisha.id], Decimal('3.34'))
        self.assertEqual(splits[self.rohan.id], Decimal('3.33'))
        self.assertEqual(splits[self.priya.id], Decimal('3.33'))
        self.assertEqual(sum(splits.values()), Decimal('10.00'))

    def test_calculate_splits_percentage(self):
        # Percentage split
        custom_data = {self.aisha.id: 50.0, self.rohan.id: 30.0, self.priya.id: 20.0}
        splits = calculate_splits(Decimal('100.00'), 'percentage', [self.aisha.id, self.rohan.id, self.priya.id], custom_data)
        self.assertEqual(splits[self.aisha.id], Decimal('50.00'))
        self.assertEqual(splits[self.rohan.id], Decimal('30.00'))
        self.assertEqual(splits[self.priya.id], Decimal('20.00'))

    def test_get_active_participants(self):
        pids = [self.aisha.id, self.rohan.id, self.meera.id, self.sam.id]
        
        # In March, Meera is active, Sam is not
        active_march = get_active_participants_on_date(self.group.id, pids, date(2024, 3, 10))
        self.assertIn(self.meera.id, active_march)
        self.assertNotIn(self.sam.id, active_march)

        # In May, Sam is active, Meera is not
        active_may = get_active_participants_on_date(self.group.id, pids, date(2024, 5, 10))
        self.assertNotIn(self.meera.id, active_may)
        self.assertIn(self.sam.id, active_may)

    def test_balance_calculation_with_settlements(self):
        # Rohan pays 1200 INR on Feb 15. Splits are equal among active members (Aisha, Rohan, Priya, Meera)
        expense = Expense.objects.create(
            group=self.group, description='Groceries', total_amount=Decimal('1200.00'),
            currency='INR', exchange_rate=Decimal('1.00'), paid_by=self.rohan,
            expense_date=date(2024, 2, 15), split_type='equal'
        )
        # Create splits manually (300 each)
        for u in [self.aisha, self.rohan, self.priya, self.meera]:
            ExpenseSplit.objects.create(expense=expense, user=u, amount_owed=Decimal('300.00'))

        # Check balances before settlements
        # Rohan spent 1200, owes 300 -> net +900
        # Others spent 0, owe 300 -> net -300 each
        rohan_bal = get_member_balance(self.rohan.id, self.group.id)
        aisha_bal = get_member_balance(self.aisha.id, self.group.id)
        self.assertEqual(rohan_bal['net_balance'], Decimal('900.00'))
        self.assertEqual(aisha_bal['net_balance'], Decimal('-300.00'))

        # Aisha pays Rohan 300 INR back on Feb 20 (Settlement)
        Settlement.objects.create(
            group=self.group, payer=self.aisha, receiver=self.rohan,
            amount=Decimal('300.00'), settlement_date=date(2024, 2, 20)
        )

        # Check balances after settlement
        # Rohan net should be +600 (Priya and Meera still owe him)
        # Aisha net should be 0 (repaid her debt)
        rohan_bal = get_member_balance(self.rohan.id, self.group.id)
        aisha_bal = get_member_balance(self.aisha.id, self.group.id)
        self.assertEqual(rohan_bal['net_balance'], Decimal('600.00'))
        self.assertEqual(aisha_bal['net_balance'], Decimal('0.00'))

