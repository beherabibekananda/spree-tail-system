from decimal import Decimal
from apps.groups.models import GroupMembership

def get_active_participants_on_date(group_id, participant_ids, expense_date):
    """
    Returns the subset of participant_ids who were active members of group_id on expense_date.
    """
    active_members = []
    for user_id in participant_ids:
        try:
            membership = GroupMembership.objects.get(user_id=user_id, group_id=group_id)
            if membership.joined_at <= expense_date:
                if membership.left_at is None or membership.left_at >= expense_date:
                    active_members.append(user_id)
        except GroupMembership.DoesNotExist:
            pass # Not a member
    return active_members

def calculate_splits(total_amount_in_r, split_type, participants, custom_data=None):
    """
    Calculates amount owed per participant.
    Parameters:
    - total_amount_in_r: Decimal, total expense amount in INR
    - split_type: 'equal', 'exact', 'percentage', 'share'
    - participants: list of User instances (or user IDs)
    - custom_data: dict of {user_id: value}
    Returns:
    - dict of {user_id: amount_owed_in_inr (Decimal)}
    """
    total = Decimal(str(total_amount_in_r))
    n = len(participants)
    if n == 0:
        return {}
        
    p_ids = [getattr(p, 'id', p) for p in participants]
    
    if split_type == 'equal':
        per_person = (total / n).quantize(Decimal('0.01'))
        splits = {uid: per_person for uid in p_ids}
        remainder = total - (per_person * n)
        splits[p_ids[0]] += remainder
        return splits
        
    elif split_type == 'exact':
        # custom_data is {user_id: amount}
        splits = {}
        for uid in p_ids:
            splits[uid] = Decimal(str(custom_data.get(uid, 0.0))).quantize(Decimal('0.01'))
        # Adjust remainder if any due to string rounding
        remainder = total - sum(splits.values())
        splits[p_ids[0]] += remainder
        return splits
        
    elif split_type == 'percentage':
        # custom_data is {user_id: percentage}
        splits = {}
        for uid in p_ids:
            pct = Decimal(str(custom_data.get(uid, 0.0)))
            splits[uid] = (total * pct / Decimal('100.00')).quantize(Decimal('0.01'))
        remainder = total - sum(splits.values())
        splits[p_ids[0]] += remainder
        return splits
        
    elif split_type == 'share':
        # custom_data is {user_id: shares}
        splits = {}
        total_shares = sum(Decimal(str(custom_data.get(uid, 0.0))) for uid in p_ids)
        if total_shares == 0:
            # Fallback to equal
            return calculate_splits(total, 'equal', p_ids)
            
        for uid in p_ids:
            shares = Decimal(str(custom_data.get(uid, 0.0)))
            splits[uid] = (total * shares / total_shares).quantize(Decimal('0.01'))
        remainder = total - sum(splits.values())
        splits[p_ids[0]] += remainder
        return splits
        
    return {}
