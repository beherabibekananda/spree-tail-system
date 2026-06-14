from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from decimal import Decimal
import json

from .models import Expense, ExpenseSplit, Settlement
from .forms import ExpenseForm, SettlementForm
from apps.groups.models import Group, GroupMembership
from django.contrib.auth.models import User
from .utils import get_active_participants_on_date, calculate_splits

@login_required
def expenses_list(request):
    group_id = request.GET.get('group_id')
    memberships = GroupMembership.objects.filter(user=request.user)
    my_group_ids = [m.group_id for m in memberships]
    
    if group_id:
        if int(group_id) not in my_group_ids:
            return HttpResponseForbidden("You do not have access to this group's expenses.")
        expenses = Expense.objects.filter(group_id=group_id).order_by('-expense_date', '-id')
        active_group = get_object_or_404(Group, id=group_id)
    else:
        expenses = Expense.objects.filter(group_id__in=my_group_ids).order_by('-expense_date', '-id')
        active_group = None
        
    return render(request, 'expenses/expenses_list.html', {
        'expenses': expenses,
        'my_groups': Group.objects.filter(id__in=my_group_ids),
        'active_group': active_group
    })

@login_required
def expense_create(request):
    user_memberships = GroupMembership.objects.filter(user=request.user)
    my_group_ids = [m.group_id for m in user_memberships]
    
    if not my_group_ids:
        messages.error(request, "You must create or join a group before logging expenses.")
        return redirect('groups_dashboard')

    # Prep group member mapping for interactive JavaScript split checkboxes
    group_members_map = {}
    for m in user_memberships:
        group_members = GroupMembership.objects.filter(group_id=m.group_id)
        members_list = []
        for gm in group_members:
            # Only list members currently active or who haven't left yet
            members_list.append({
                'id': gm.user.id,
                'username': gm.user.username,
                'name': gm.user.first_name or gm.user.username,
                'joined_at': str(gm.joined_at),
                'left_at': str(gm.left_at) if gm.left_at else None
            })
        group_members_map[m.group_id] = members_list

    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            
            # Read selected split participants
            participant_ids = request.POST.getlist('split_participants')
            participant_ids = [int(pid) for pid in participant_ids]
            
            # Filter active participants on expense date
            active_pids = get_active_participants_on_date(expense.group_id, participant_ids, expense.expense_date)
            if not active_pids:
                messages.error(request, "No selected participants are active members on the expense date.")
                return render(request, 'expenses/expense_form.html', {
                    'form': form,
                    'group_members_json': json.dumps(group_members_map),
                    'group_id': request.GET.get('group_id')
                })
                
            # Collect custom split values (e.g. shares, percents, exact)
            custom_data = {}
            for pid in active_pids:
                input_name = f"split_val_{pid}"
                val_str = request.POST.get(input_name, '0')
                try:
                    custom_data[pid] = float(val_str)
                except ValueError:
                    custom_data[pid] = 0.0
            
            # Double check exact/percentage constraints
            # Calculate amount in INR
            expense.amount_in_inr = Decimal(str(expense.total_amount)) * Decimal(str(expense.exchange_rate))
            
            if expense.split_type == 'percentage':
                total_pct = sum(custom_data.values())
                if abs(total_pct - 100.0) > 0.01:
                    messages.error(request, f"Percentages must sum to 100%. Current sum: {total_pct}%")
                    return render(request, 'expenses/expense_form.html', {
                        'form': form,
                        'group_members_json': json.dumps(group_members_map),
                        'group_id': request.GET.get('group_id')
                    })
            elif expense.split_type == 'exact':
                total_exact = sum(custom_data.values())
                if abs(Decimal(str(total_exact)) - expense.amount_in_inr) > Decimal('0.02'):
                    messages.error(request, f"Exact amounts must sum to total in INR ({expense.amount_in_inr} INR). Current sum: {total_exact} INR")
                    return render(request, 'expenses/expense_form.html', {
                        'form': form,
                        'group_members_json': json.dumps(group_members_map),
                        'group_id': request.GET.get('group_id')
                    })
            
            # Save expense
            expense.save()
            
            # Calculate splits
            splits_dict = calculate_splits(expense.amount_in_inr, expense.split_type, active_pids, custom_data)
            
            # Create splits records
            for uid, amount in splits_dict.items():
                ExpenseSplit.objects.create(
                    expense=expense,
                    user_id=uid,
                    amount_owed=amount
                )
                
            messages.success(request, f"Expense '{expense.description}' logged successfully!")
            return redirect('group_detail', group_id=expense.group_id)
        else:
            messages.error(request, "Failed to log expense. Please correct the errors.")
    else:
        group_id_param = request.GET.get('group_id')
        form = ExpenseForm(user=request.user)
        if group_id_param and int(group_id_param) in my_group_ids:
            form.fields['group'].initial = int(group_id_param)
            
    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'group_members_json': json.dumps(group_members_map),
        'group_id': request.GET.get('group_id')
    })

@login_required
def expense_delete(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    # Check if user is a member of this expense's group
    get_object_or_404(GroupMembership, group=expense.group, user=request.user)
    
    if request.method == 'POST':
        group_id = expense.group_id
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
        return redirect('group_detail', group_id=group_id)
        
    return HttpResponseForbidden("Method not allowed.")

@login_required
def settlement_create(request):
    user_memberships = GroupMembership.objects.filter(user=request.user)
    my_group_ids = [m.group_id for m in user_memberships]
    
    if not my_group_ids:
        messages.error(request, "You must create or join a group before logging payments.")
        return redirect('groups_dashboard')

    # Map members per group for JS dropdown filters
    group_members_map = {}
    for m in user_memberships:
        group_members = GroupMembership.objects.filter(group_id=m.group_id)
        members_list = []
        for gm in group_members:
            members_list.append({
                'id': gm.user.id,
                'name': gm.user.first_name or gm.user.username
            })
        group_members_map[m.group_id] = members_list

    if request.method == 'POST':
        form = SettlementForm(request.POST, user=request.user)
        if form.is_valid():
            settlement = form.save()
            messages.success(request, f"Recorded payment: {settlement.payer.username} paid {settlement.amount} INR to {settlement.receiver.username}.")
            return redirect('group_detail', group_id=settlement.group_id)
        else:
            messages.error(request, "Failed to record payment. Please check inputs.")
    else:
        group_id_param = request.GET.get('group_id')
        form = SettlementForm(user=request.user)
        if group_id_param and int(group_id_param) in my_group_ids:
            form.fields['group'].initial = int(group_id_param)
            
    return render(request, 'expenses/settlement_form.html', {
        'form': form,
        'group_members_json': json.dumps(group_members_map)
    })
