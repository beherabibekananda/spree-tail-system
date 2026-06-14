from django.db import models

from django.contrib.auth.models import User
from decimal import Decimal
from apps.groups.models import Group

class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('1.0000'))
    amount_in_inr = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='paid_expenses')
    expense_date = models.DateField()
    split_type = models.CharField(max_length=50) # 'equal', 'exact', 'percentage', 'share'
    category = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=20, default='manual') # 'manual' or 'import'
    import_session_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.amount_in_inr = Decimal(str(self.total_amount)) * Decimal(str(self.exchange_rate))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} ({self.amount_in_inr} INR)"

class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='splits')
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2) # always stored in INR
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} owes {self.amount_owed} INR for {self.expense.description}"

class Settlement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_settlements')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_settlements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    settlement_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payer.username} paid {self.amount} INR to {self.receiver.username}"

