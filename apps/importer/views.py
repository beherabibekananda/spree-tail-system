from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from decimal import Decimal
import csv
import json
import os
from datetime import datetime, date

from .models import ImportSession, ImportAnomaly
from .detector import detect_anomalies, get_fuzzy_match
from .parser import parse_date, clean_amount, parse_custom_split
from apps.groups.models import Group, GroupMembership
from apps.expenses.models import Expense, ExpenseSplit, Settlement
from apps.expenses.utils import calculate_splits, get_active_participants_on_date
from django.contrib.auth.models import User

@login_required
def import_csv(request):
    groups = Group.objects.filter(memberships__user=request.user)
    if not groups.exists():
        messages.error(request, "You must create or join a group before you can import expenses.")
        return redirect('groups_dashboard')
        
    if request.method == 'POST':
        group_id = request.POST.get('group_id')
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file:
            messages.error(request, "Please select a CSV file to upload.")
            return redirect('import_csv')
            
        group = get_object_or_404(Group, id=group_id)
        
        # Save temp copy of CSV to run parser
        temp_dir = "/Users/bibekanandabehera/Desktop/Speertail/"
        os.makedirs(temp_dir, exist_ok=True)
        csv_path = os.path.join(temp_dir, "expenses_export.csv")
        
        # Overwrite current file with upload
        with open(csv_path, 'wb+') as destination:
            for chunk in csv_file.chunks():
                destination.write(chunk)
                
        # Parse CSV rows
        rows = []
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                # Standardize field names by striping whitespace
                reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
                for row in reader:
                    # Clean dictionary keys
                    clean_row = {k.strip().lower(): v.strip() if v else '' for k, v in row.items()}
                    rows.append(clean_row)
        except Exception as e:
            messages.error(request, f"Failed to parse CSV: {e}")
            return redirect('import_csv')
            
        if not rows:
            messages.error(request, "The uploaded CSV file is empty.")
            return redirect('import_csv')

        # Create import session
        session = ImportSession.objects.create(
            filename=csv_file.name,
            imported_by=request.user,
            total_rows=len(rows),
            status='pending'
        )

        # Run anomaly detection
        anomalies = detect_anomalies(rows, group.id)
        
        for anomaly in anomalies:
            ImportAnomaly.objects.create(
                session=session,
                row_number=anomaly['row_number'],
                raw_data=anomaly['raw_data'],
                issue_type=anomaly['issue_type'],
                issue_description=anomaly['issue_description'],
                proposed_action=anomaly['proposed_action'],
                status='pending'
            )
            
        session.anomaly_rows = len(anomalies)
        session.clean_rows = len(rows) - len(anomalies)
        session.save()
        
        messages.success(request, f"CSV uploaded successfully! Found {len(anomalies)} anomalies in {len(rows)} rows.")
        return redirect('import_review', session_id=session.id)
        
    return render(request, 'importer/import_form.html', {
        'groups': groups
    })

@login_required
def import_review(request, session_id):
    session = get_object_or_404(ImportSession, id=session_id)
    anomalies = session.anomalies.all().order_by('row_number', 'id')
    groups = Group.objects.filter(memberships__user=request.user)
    
    return render(request, 'importer/import_review.html', {
        'session': session,
        'anomalies': anomalies,
        'groups': groups
    })

@login_required
def import_anomaly_action(request, anomaly_id):
    anomaly = get_object_or_404(ImportAnomaly, id=anomaly_id)
    # Verify permission
    get_object_or_404(GroupMembership, group__created_by=anomaly.session.imported_by, user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action') # 'approve' or 'reject'
        if action == 'approve':
            anomaly.status = 'approved'
            anomaly.action_taken = anomaly.proposed_action
        elif action == 'reject':
            anomaly.status = 'rejected'
            anomaly.action_taken = 'Kept original row details'
        else:
            anomaly.status = 'pending'
            anomaly.action_taken = None
            
        anomaly.approved_by = request.user
        anomaly.save()
        
        return JsonResponse({
            'success': True,
            'status': anomaly.status,
            'action_taken': anomaly.action_taken or 'None'
        })
        
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def import_commit(request, session_id):
    session = get_object_or_404(ImportSession, id=session_id)
    
    if session.status == 'committed':
        messages.error(request, "This import session has already been committed.")
        return redirect('groups_dashboard')
        
    group_id = request.POST.get('group_id')
    group = get_object_or_404(Group, id=group_id)
    
    csv_path = "/Users/bibekanandabehera/Desktop/Speertail/expenses_export.csv"
    if not os.path.exists(csv_path):
        messages.error(request, f"Source CSV file not found at {csv_path}!")
        return redirect('import_review', session_id=session.id)
        
    # Read rows
    rows = []
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        for row in reader:
            clean_row = {k.strip().lower(): v.strip() if v else '' for k, v in row.items()}
            rows.append(clean_row)
            
    # Load all anomalies of this session
    anomalies = session.anomalies.all()
    anomalies_map = {}
    for a in anomalies:
        if a.row_number not in anomalies_map:
            anomalies_map[a.row_number] = []
        anomalies_map[a.row_number].append(a)
        
    committed_count = 0
    skipped_count = 0
    reclassified_count = 0
    
    known_names = ['aisha', 'rohan', 'priya', 'meera', 'sam', 'dev']
    users_cache = {u.username: u for u in User.objects.all()}
    
    # Load memberships of the group for dynamic date checks
    group_memberships = GroupMembership.objects.filter(group=group).select_related('user')
    membership_map = {m.user.username.lower(): m for m in group_memberships}

    # Commit transactions in a loop
    for idx, row in enumerate(rows):
        row_num = idx + 1
        row_anomalies = anomalies_map.get(row_num, [])
        
        # Determine if we should skip/delete this row
        should_skip = False
        is_settlement = False
        
        # Pre-process flags
        correct_date = None
        correct_amount = None
        correct_currency = None
        correct_exchange_rate = None
        correct_payer = None
        correct_split_type = None
        correct_participants = None
        
        for a in row_anomalies:
            if a.status == 'approved':
                if 'Delete duplicate' in a.proposed_action or 'Flag for deletion' in a.proposed_action:
                    should_skip = True
                elif 'Block row' in a.proposed_action:
                    should_skip = True
                elif 'Reclassify to settlements' in a.proposed_action:
                    is_settlement = True
                elif 'Normalize to ISO' in a.proposed_action:
                    # Parse date correctly
                    correct_date = parse_date(row['date'])
                elif 'Normalize to clean Decimal' in a.proposed_action:
                    correct_amount, _ = clean_amount(row['amount'])
                elif 'Convert at' in a.proposed_action:
                    correct_currency = 'USD'
                    correct_exchange_rate = Decimal('83.5000')
                    raw_val, _ = clean_amount(row['amount'])
                    correct_amount = raw_val
                elif 'Correct to' in a.proposed_action:
                    match = re.search(r"'(.*)'", a.proposed_action)
                    if match:
                        correct_payer = match.group(1).lower()
                elif 'Default to equal split' in a.proposed_action:
                    correct_split_type = 'equal'
                elif 'Normalize to exact split' in a.proposed_action:
                    correct_split_type = 'exact'
            elif a.status == 'pending':
                # Block commit if there are pending actions (Meera's requirement)
                messages.error(request, f"Cannot commit import. Row {row_num} has pending anomalies that must be approved or rejected.")
                return redirect('import_review', session_id=session.id)
                
        if should_skip:
            skipped_count += 1
            continue
            
        # Standard Parsing/Resolution
        expense_date = correct_date if correct_date else parse_date(row['date'])
        if not expense_date:
            skipped_count += 1
            continue # block invalid dates
            
        total_amount, is_usd = clean_amount(row['amount'])
        if correct_amount is not None:
            total_amount = correct_amount
            
        currency = row['currency'].strip().upper() if row['currency'] else ('USD' if is_usd else 'INR')
        if correct_currency:
            currency = correct_currency
            
        exchange_rate = Decimal('1.0000')
        if currency == 'USD':
            exchange_rate = Decimal('83.5000')
        if correct_exchange_rate is not None:
            exchange_rate = correct_exchange_rate
            
        # Parse Payer username
        payer_raw = row['paid_by'].strip().lower()
        if correct_payer:
            payer_raw = correct_payer
        else:
            payer_raw = get_fuzzy_match(payer_raw, known_names) or payer_raw
            
        paid_by = users_cache.get(payer_raw)
        if not paid_by:
            skipped_count += 1
            continue # Block missing payers
            
        # Split Type
        split_type = row['split_type'].strip().lower() if row['split_type'] else 'equal'
        if correct_split_type:
            split_type = correct_split_type
            
        # Participants (support split_with and semicolon separator)
        parts_raw = row.get('participants') or row.get('split_with') or ''
        parts_raw_list = [p.strip().lower() for p in parts_raw.replace(';', ',').split(',') if p.strip()]
        resolved_participants_list = []
        for p in parts_raw_list:
            p_match = get_fuzzy_match(p, known_names)
            if p_match:
                resolved_participants_list.append(p_match)
                
        # Handle settlement reclassification
        if is_settlement:
            # Reclassify to settlements table
            # Find receiver (usually listed in participants or notes)
            receiver_raw = resolved_participants_list[0] if resolved_participants_list else 'aisha'
            receiver = users_cache.get(receiver_raw) or paid_by # fallback
            
            Settlement.objects.create(
                group=group,
                payer=paid_by,
                receiver=receiver,
                amount=total_amount * exchange_rate, # convert to INR
                settlement_date=expense_date,
                notes=f"Reclassified from import: {row['description']}. Notes: {row['notes']}"
            )
            reclassified_count += 1
            continue

        # Adjust participant list for ex-members / before-joins
        final_participants = []
        for p_name in resolved_participants_list:
            # Dynamic membership check
            m_record = membership_map.get(p_name)
            if m_record:
                joined_at = m_record.joined_at
                left_at = m_record.left_at
            else:
                # Fallback to defaults based on the year of the expense date
                year_val = expense_date.year
                if p_name == 'meera':
                    joined_at = date(year_val, 2, 1)
                    left_at = date(year_val, 3, 31)
                elif p_name == 'sam':
                    joined_at = date(year_val, 4, 15)
                    left_at = None
                else:
                    joined_at = date(year_val, 2, 1)
                    left_at = None

            if left_at and expense_date > left_at:
                # If approved, we skip this member. If rejected, we keep them
                exit_anom = [a for a in row_anomalies if p_name in a.issue_description.lower() and 'exit' in a.issue_type]
                if exit_anom and exit_anom[0].status == 'approved':
                    continue
            elif joined_at and expense_date < joined_at:
                # If approved, we skip this member. If rejected, we keep them
                join_anom = [a for a in row_anomalies if p_name in a.issue_description.lower() and 'join' in a.issue_type]
                if join_anom and join_anom[0].status == 'approved':
                    continue
            final_participants.append(p_name)
            
        # Get active user instances for splits
        active_users = [users_cache[name] for name in final_participants if name in users_cache]
        
        # Check active members on date again
        active_pids = get_active_participants_on_date(group.id, [u.id for u in active_users], expense_date)
        if not active_pids:
            # If no active members found, split among creator and payer as fallback
            active_pids = [paid_by.id]
            
        # Parse custom splits data if present (support split_details and notes)
        split_details_str = row.get('split_details') or row.get('notes') or ''
        custom_data = parse_custom_split(split_details_str) or {}
        # Convert custom_data keys to user IDs
        custom_data_ids = {}
        for username, val in custom_data.items():
            user_inst = users_cache.get(username)
            if user_inst:
                custom_data_ids[user_inst.id] = val
                
        # Create Expense instance
        expense = Expense(
            group=group,
            description=row['description'],
            total_amount=total_amount,
            currency=currency,
            exchange_rate=exchange_rate,
            paid_by=paid_by,
            expense_date=expense_date,
            split_type=split_type,
            category=row.get('category', 'Imported'),
            notes=row.get('notes', ''),
            source='import',
            import_session_id=session.id
        )
        expense.save() # calculates amount_in_inr automatically
        
        # Compute splits
        splits_dict = calculate_splits(expense.amount_in_inr, split_type, active_pids, custom_data_ids)
        
        # Save splits
        for uid, amount in splits_dict.items():
            ExpenseSplit.objects.create(
                expense=expense,
                user_id=uid,
                amount_owed=amount
            )
            
        committed_count += 1

    session.status = 'committed'
    session.save()
    
    messages.success(request, f"Successfully committed import! Created {committed_count} expenses and reclassified {reclassified_count} settlements. Skipped/deleted {skipped_count} rows.")
    return redirect('import_report', session_id=session.id)


@login_required
def import_report(request, session_id):
    session = get_object_or_404(ImportSession, id=session_id)
    if session.status != 'committed':
        messages.error(request, "This import session has not been committed yet.")
        return redirect('import_review', session_id=session.id)
        
    anomalies = session.anomalies.all().order_by('row_number', 'id')
    
    # Calculate counts dynamically
    skipped_count = len([a for a in anomalies if a.status == 'approved' and ('Delete' in a.proposed_action or 'Block' in a.proposed_action)])
    reclassified_count = len([a for a in anomalies if a.status == 'approved' and 'Reclassify' in a.proposed_action])
    committed_count = session.total_rows - skipped_count - reclassified_count
    
    # Try to find the group these expenses were imported into
    first_expense = Expense.objects.filter(import_session_id=session.id).first()
    group = first_expense.group if first_expense else Group.objects.filter(memberships__user=request.user).first()
    
    return render(request, 'importer/import_report.html', {
        'session': session,
        'anomalies': anomalies,
        'group': group,
        'committed_count': committed_count,
        'skipped_count': skipped_count,
        'reclassified_count': reclassified_count
    })
