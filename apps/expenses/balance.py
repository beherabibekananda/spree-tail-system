from decimal import Decimal
from apps.expenses.models import Expense, ExpenseSplit, Settlement
from django.contrib.auth.models import User

def get_member_balance(user_id, group_id):
    """
    Calculates the net balance and full audit trail for a user in a group.
    Returns:
    - net_balance: positive means others owe them, negative means they owe others
    - total_paid_shares: total of splits others owe them for expenses they paid
    - total_owed_shares: total of splits they owe others for expenses others paid
    - total_paid_settlements: total settlements they paid to others
    - total_received_settlements: total settlements they received from others
    - audit_trail: list of dicts detailing contributing items
    """
    user = User.objects.get(id=user_id)
    net_balance = Decimal('0.00')
    audit_trail = []
    
    # 1. Look at all expenses in this group
    expenses = Expense.objects.filter(group_id=group_id).order_by('expense_date', 'id')
    
    total_paid_shares = Decimal('0.00')
    total_owed_shares = Decimal('0.00')
    
    for expense in expenses:
        splits = ExpenseSplit.objects.filter(expense=expense)
        user_split = splits.filter(user_id=user_id).first()
        
        if expense.paid_by_id == user_id:
            # User paid for this expense. Others owe this user their respective splits.
            # Total others owe = expense.amount_in_inr - (user's own split if any)
            own_split_amount = user_split.amount_owed if user_split else Decimal('0.00')
            owed_to_user = expense.amount_in_inr - own_split_amount
            
            if owed_to_user > 0:
                net_balance += owed_to_user
                total_paid_shares += owed_to_user
                audit_trail.append({
                    'type': 'expense_paid',
                    'date': expense.expense_date,
                    'description': expense.description,
                    'total_amount': expense.amount_in_inr,
                    'user_share': own_split_amount,
                    'net_effect': owed_to_user, # positive effect
                    'details': f"You paid {expense.amount_in_inr} INR; others owe you {owed_to_user} INR"
                })
        else:
            # Someone else paid. User owes their split amount if they participated.
            if user_split and user_split.amount_owed > 0:
                net_balance -= user_split.amount_owed
                total_owed_shares += user_split.amount_owed
                audit_trail.append({
                    'type': 'expense_owed',
                    'date': expense.expense_date,
                    'description': expense.description,
                    'total_amount': expense.amount_in_inr,
                    'user_share': user_split.amount_owed,
                    'net_effect': -user_split.amount_owed, # negative effect
                    'details': f"Paid by {expense.paid_by.username}; you owe {user_split.amount_owed} INR"
                })

    # 2. Look at all settlements in this group
    settlements = Settlement.objects.filter(group_id=group_id).order_by('settlement_date', 'id')
    total_paid_settlements = Decimal('0.00')
    total_received_settlements = Decimal('0.00')
    
    for s in settlements:
        if s.payer_id == user_id:
            # User paid back someone else. This reduces what they owe or increases what they are owed.
            net_balance += s.amount
            total_paid_settlements += s.amount
            audit_trail.append({
                'type': 'settlement_paid',
                'date': s.settlement_date,
                'description': f"Payment to {s.receiver.username}",
                'total_amount': s.amount,
                'net_effect': s.amount, # positive effect
                'details': f"You paid {s.receiver.username} {s.amount} INR"
            })
        elif s.receiver_id == user_id:
            # User was paid back by someone else. This reduces what others owe them.
            net_balance -= s.amount
            total_received_settlements += s.amount
            audit_trail.append({
                'type': 'settlement_received',
                'date': s.settlement_date,
                'description': f"Payment from {s.payer.username}",
                'total_amount': s.amount,
                'net_effect': -s.amount, # negative effect
                'details': f"Received {s.amount} INR from {s.payer.username}"
            })

    return {
        'net_balance': net_balance,
        'total_paid_shares': total_paid_shares,
        'total_owed_shares': total_owed_shares,
        'total_paid_settlements': total_paid_settlements,
        'total_received_settlements': total_received_settlements,
        'audit_trail': audit_trail
    }
