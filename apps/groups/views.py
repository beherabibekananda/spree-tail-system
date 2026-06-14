from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import date
from decimal import Decimal
from .models import Group, GroupMembership
from .forms import GroupForm, GroupMembershipForm
from apps.expenses.balance import get_member_balance
from apps.expenses.models import Expense, Settlement

@login_required
def groups_dashboard(request):
    memberships = GroupMembership.objects.filter(user=request.user)
    groups_data = []
    
    for m in memberships:
        balance_info = get_member_balance(request.user.id, m.group.id)
        groups_data.append({
            'group': m.group,
            'membership': m,
            'balance': balance_info['net_balance'],
            'total_paid': balance_info['total_paid_shares'],
            'total_owed': balance_info['total_owed_shares']
        })
        
    return render(request, 'groups/dashboard.html', {
        'groups_data': groups_data
    })

@login_required
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            
            # Creator is automatically a member starting today
            GroupMembership.objects.create(
                user=request.user,
                group=group,
                joined_at=date.today()
            )
            messages.success(request, f"Group '{group.name}' created successfully!")
            return redirect('group_detail', group_id=group.id)
    else:
        form = GroupForm()
        
    return render(request, 'groups/group_form.html', {
        'form': form,
        'title': 'Create New Group'
    })

@login_required
def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Verify user is a member
    user_membership = get_object_or_404(GroupMembership, group=group, user=request.user)
    
    # Calculate balance for this user
    balance_info = get_member_balance(request.user.id, group.id)
    
    # Calculate balances for ALL group members to compute net settlements
    memberships = GroupMembership.objects.filter(group=group)
    member_balances = []
    
    for m in memberships:
        m_bal = get_member_balance(m.user.id, group.id)
        member_balances.append({
            'username': m.user.username,
            'name': m.user.first_name or m.user.username,
            'balance': m_bal['net_balance'],
            'membership': m
        })
        
    # Solve debt settlements (Aisha's requirement)
    # debtors = negative balance, creditors = positive balance
    debtors = []
    creditors = []
    
    # Filter and round balances to 2 decimal places
    for mb in member_balances:
        bal = round(mb['balance'], 2)
        if bal < -0.01:
            debtors.append({'name': mb['name'], 'balance': -bal}) # store as positive for matching
        elif bal > 0.01:
            creditors.append({'name': mb['name'], 'balance': bal})
            
    # Sort debtors descending, creditors descending
    debtors.sort(key=lambda x: x['balance'], reverse=True)
    creditors.sort(key=lambda x: x['balance'], reverse=True)
    
    suggested_settlements = []
    
    i = 0
    j = 0
    while i < len(debtors) and j < len(creditors):
        db = debtors[i]
        cr = creditors[j]
        
        amount = min(db['balance'], cr['balance'])
        if amount > 0.01:
            suggested_settlements.append({
                'debtor': db['name'],
                'creditor': cr['name'],
                'amount': amount
            })
            
        db['balance'] -= amount
        cr['balance'] -= amount
        
        if db['balance'] <= 0.01:
            i += 1
        if cr['balance'] <= 0.01:
            j += 1

    # Get recent expenses
    expenses = Expense.objects.filter(group=group).order_by('-expense_date', '-id')[:10]
    # Get recent settlements
    settlements = Settlement.objects.filter(group=group).order_by('-settlement_date', '-id')[:10]
    
    member_form = GroupMembershipForm()
    
    return render(request, 'groups/group_detail.html', {
        'group': group,
        'user_membership': user_membership,
        'balance_info': balance_info,
        'member_balances': member_balances,
        'suggested_settlements': suggested_settlements,
        'expenses': expenses,
        'settlements': settlements,
        'member_form': member_form
    })

@login_required
def group_member_add(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Check if logged-in user is a member
    get_object_or_404(GroupMembership, group=group, user=request.user)
    
    if request.method == 'POST':
        form = GroupMembershipForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('user_username')
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(request, f"User '{username}' does not exist.")
                return redirect('group_detail', group_id=group.id)
                
            # Check if already a member
            if GroupMembership.objects.filter(group=group, user=user).exists():
                messages.error(request, f"User '{username}' is already a member of this group.")
                return redirect('group_detail', group_id=group.id)
                
            membership = form.save(commit=False)
            membership.group = group
            membership.user = user
            membership.save()
            messages.success(request, f"Successfully added {user.username} to {group.name}!")
        else:
            messages.error(request, "Failed to add member. Please verify fields.")
            
    return redirect('group_detail', group_id=group.id)

@login_required
def group_member_leave(request, group_id, membership_id):
    group = get_object_or_404(Group, id=group_id)
    # Verify logged-in user is a member
    get_object_or_404(GroupMembership, group=group, user=request.user)
    
    membership = get_object_or_404(GroupMembership, id=membership_id, group=group)
    
    if request.method == 'POST':
        leave_date_str = request.POST.get('left_at')
        try:
            leave_date = date.today()
            if leave_date_str:
                from datetime import datetime
                leave_date = datetime.strptime(leave_date_str, "%Y-%m-%d").date()
                
            if leave_date < membership.joined_at:
                messages.error(request, "Leave date cannot be earlier than joined date.")
                return redirect('group_detail', group_id=group.id)
                
            membership.left_at = leave_date
            membership.save()
            messages.success(request, f"Set {membership.user.username}'s exit date to {leave_date}.")
        except Exception as e:
            messages.error(request, f"Error setting leave date: {e}")
            
    return redirect('group_detail', group_id=group.id)
