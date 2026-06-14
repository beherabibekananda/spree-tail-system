from django import forms
from django.contrib.auth.models import User
from .models import Group, GroupMembership

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none transition-all',
                'placeholder': 'e.g. Flat 22B Household'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none transition-all',
                'placeholder': 'Describe this sharing group...',
                'rows': 3
            })
        }

class GroupMembershipForm(forms.ModelForm):
    user_username = forms.CharField(
        label="Member Username",
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none transition-all',
            'placeholder': 'Enter flatmate\'s username'
        })
    )
    joined_at = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none transition-all'
        })
    )
    left_at = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none transition-all'
        })
    )

    class Meta:
        model = GroupMembership
        fields = ['joined_at', 'left_at']
