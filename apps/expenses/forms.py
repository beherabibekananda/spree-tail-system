from django import forms
from .models import Expense, Settlement
from apps.groups.models import Group, GroupMembership
from django.contrib.auth.models import User
from datetime import date
from decimal import Decimal

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['group', 'description', 'total_amount', 'currency', 'exchange_rate', 'paid_by', 'expense_date', 'split_type', 'category', 'notes']
        widgets = {
            'group': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'description': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 outline-none', 'placeholder': 'e.g. Electricity bill'}),
            'total_amount': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none', 'step': '0.01'}),
            'currency': forms.Select(choices=[('INR', 'INR (₹)'), ('USD', 'USD ($)')], attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none', 'step': '0.0001'}),
            'paid_by': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'expense_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'split_type': forms.Select(choices=[
                ('equal', 'Split Equally'),
                ('exact', 'Exact Amounts'),
                ('percentage', 'Percentage splits'),
                ('share', 'Ratio / Shares')
            ], attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'category': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 outline-none', 'placeholder': 'e.g. Utilities'}),
            'notes': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 outline-none', 'rows': 2})
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expense_date'].initial = date.today()
        self.fields['exchange_rate'].initial = Decimal('1.0000')
        if user:
            # Filter groups to only show the ones where the user is a member
            memberships = GroupMembership.objects.filter(user=user)
            self.fields['group'].queryset = Group.objects.filter(id__in=[m.group_id for m in memberships])
            # Set default queryset for users
            self.fields['paid_by'].queryset = User.objects.all()

class SettlementForm(forms.ModelForm):
    class Meta:
        model = Settlement
        fields = ['group', 'payer', 'receiver', 'amount', 'settlement_date', 'notes']
        widgets = {
            'group': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'payer': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'receiver': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none', 'step': '0.01'}),
            'settlement_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:border-brand-500 outline-none'}),
            'notes': forms.Textarea(attrs={'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 outline-none', 'rows': 2})
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['settlement_date'].initial = date.today()
        if user:
            memberships = GroupMembership.objects.filter(user=user)
            self.fields['group'].queryset = Group.objects.filter(id__in=[m.group_id for m in memberships])
            self.fields['payer'].queryset = User.objects.all()
            self.fields['receiver'].queryset = User.objects.all()
