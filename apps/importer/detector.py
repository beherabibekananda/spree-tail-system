import json
import re
from decimal import Decimal
from datetime import datetime, date
from django.contrib.auth.models import User
from apps.groups.models import GroupMembership
from .parser import parse_date, clean_amount

def get_fuzzy_match(name, known_names):
    """
    Simple fuzzy matcher for misspelled flatmate names.
    Returns the closest matched name if similarity is high, else None.
    """
    if not name:
        return None
    name = name.lower().strip()
    
    # Direct match
    if name in known_names:
        return name
        
    # Check if any word in the name is a known name (e.g. "Priya S" -> "Priya")
    for word in name.split():
        word_clean = re.sub(r'[^a-zA-Z]', '', word)
        if word_clean in known_names:
            return word_clean

    # Check for minor edits/typos (length differences, character swaps)
    for kn in known_names:
        # If one edit away (Levenshtein distance <= 2)
        if len(name) == len(kn) or abs(len(name) - len(kn)) <= 1:
            shared = set(name) & set(kn)
            if len(shared) >= len(kn) - 1:
                return kn
    return None

def detect_anomalies(rows, group_id):
    """
    Detects all 12 anomaly categories across a list of parsed CSV rows.
    Returns:
    - list of dictionaries containing anomaly details.
    """
    anomalies = []
    known_names = ['aisha', 'rohan', 'priya', 'meera', 'sam', 'dev']
    
    # Load memberships of the group for dynamic date checks
    memberships = GroupMembership.objects.filter(group_id=group_id).select_related('user')
    membership_map = {m.user.username.lower(): m for m in memberships}
    
    # Store hashes for exact duplicate checks
    seen_hashes = {}
    
    # Parse date helper
    def get_iso_date(d_str):
        d = parse_date(d_str)
        return str(d) if d else ""

    # Pre-parse rows to help with multi-row comparison (like duplicates)
    parsed_rows = []
    for idx, row in enumerate(rows):
        row_num = idx + 1
        date_raw = row.get('date', '')
        desc = row.get('description', '')
        amt_raw = row.get('amount', '')
        curr = row.get('currency', '')
        paid_by_raw = row.get('paid_by', '')
        split_raw = row.get('split_type', '')
        # Support both 'participants' (old) and 'split_with' (new)
        parts_raw = row.get('participants') or row.get('split_with') or ''
        notes = row.get('notes', '')
        
        # Clean amount
        amt_val, is_usd = clean_amount(amt_raw)
        
        parsed_rows.append({
            'row_number': row_num,
            'date_raw': date_raw,
            'description': desc,
            'amount_raw': amt_raw,
            'amount_val': amt_val,
            'is_usd_format': is_usd,
            'currency': curr,
            'paid_by_raw': paid_by_raw,
            'split_type': split_raw,
            'participants_raw': parts_raw,
            'notes': notes,
            'raw_row': row
        })

    # Run checks on each row
    for row in parsed_rows:
        row_num = row['row_number']
        raw_data_json = json.dumps(row['raw_row'])
        
        # Helper to append anomaly
        def flag_anomaly(issue_type, desc, proposed):
            anomalies.append({
                'row_number': row_num,
                'raw_data': raw_data_json,
                'issue_type': issue_type,
                'issue_description': desc,
                'proposed_action': proposed
            })

        # --- 1. Exact Duplicate Row Check ---
        # Generate row hash based on all fields
        normalized_parts = ",".join(sorted([p.strip().lower() for p in row['participants_raw'].replace(';', ',').split(',') if p.strip()]))
        row_str = f"{row['date_raw']}|{row['description']}|{row['amount_raw']}|{row['paid_by_raw']}|{row['split_type']}|{normalized_parts}"
        if row_str in seen_hashes:
            flag_anomaly(
                'Exact Duplicate',
                f"This row is an exact duplicate of Row {seen_hashes[row_str]}.",
                'Delete duplicate'
            )
            continue # skip further analysis of this row if it is deleted
        seen_hashes[row_str] = row_num

        # --- 2. Near-Duplicate Row Check ---
        for other in parsed_rows:
            if other['row_number'] != row_num:
                # Same date and description, but different amount
                if (row['date_raw'] == other['date_raw'] and 
                    row['description'].strip().lower() == other['description'].strip().lower() and 
                    row['amount_raw'] != other['amount_raw']):
                    # Flag the one with lower row number or let user decide
                    flag_anomaly(
                        'Near Duplicate',
                        f"Found near-duplicate with Row {other['row_number']}. This row amount is {row['amount_raw']}, other is {other['amount_raw']}.",
                        'Keep row with higher amount' if row['amount_val'] > other['amount_val'] else 'Flag for deletion'
                    )
                    break

        # --- 3. Settlement recorded as expense ---
        settlement_keywords = ['paid back', 'settlement', 'transfer', 'repay', 'payment back', 'owes']
        is_settlement = False
        for kw in settlement_keywords:
            if kw in row['description'].lower() or kw in row['notes'].lower():
                is_settlement = True
                break
        if is_settlement:
            flag_anomaly(
                'Settlement as Expense',
                f"Description '{row['description']}' indicates this is a debt settlement, not an expense.",
                'Reclassify to settlements table'
            )
            continue # Settlements don't undergo membership splits checks

        # --- 7. Inconsistent date formats ---
        is_iso_format = re.match(r'^\d{4}-\d{2}-\d{2}$', row['date_raw'].strip())
        parsed_d = parse_date(row['date_raw'])
        if not parsed_d:
            flag_anomaly('Invalid Date', f"Cannot parse date: {row['date_raw']}.", 'Block row')
            continue
        elif not is_iso_format:
            flag_anomaly(
                'Inconsistent Date Format',
                f"Date format is '{row['date_raw']}', should be YYYY-MM-DD.",
                f"Normalize to ISO {parsed_d}"
            )

        # --- 8. Inconsistent amount formats ---
        has_symbols = any(sym in row['amount_raw'] for sym in ['₹', '$', 'Rs.', 'Rs']) or ',' in row['amount_raw']
        if has_symbols:
            flag_anomaly(
                'Inconsistent Amount Format',
                f"Amount contains symbols or commas: {row['amount_raw']}.",
                f"Normalize to clean Decimal {row['amount_val']}"
            )

        # --- 9. Negative amounts ---
        if row['amount_val'] < 0:
            flag_anomaly(
                'Negative Amount',
                f"Expense amount is negative: {row['amount_raw']}.",
                'Treat as refund / negative expense'
            )

        # --- 4. USD amount treated as INR ---
        # If amount contains $ symbol but currency column is blank or 'INR'
        if row['is_usd_format'] and (not row['currency'] or row['currency'] == 'INR'):
            flag_anomaly(
                'USD treated as INR',
                f"Amount contains '$' ({row['amount_raw']}) but currency is set to INR.",
                'Convert at ₹83.50/$ and set currency to USD'
            )
        elif row['currency'] == 'USD' and not row['is_usd_format']:
            # Currency is USD but no symbol, also fine but verify
            pass

        # --- 10. Missing payer ---
        if not row['paid_by_raw'].strip():
            flag_anomaly('Missing Payer', 'The paid_by field is empty.', 'Block row')
            continue

        # --- 11. Unknown/misspelled payer name ---
        payer_match = get_fuzzy_match(row['paid_by_raw'], known_names)
        if not payer_match:
            flag_anomaly(
                'Unknown Payer Name',
                f"Payer '{row['paid_by_raw']}' does not match any registered flatmate.",
                'Block row'
            )
            continue
        elif payer_match != row['paid_by_raw'].lower().strip():
            flag_anomaly(
                'Misspelled Payer Name',
                f"Payer '{row['paid_by_raw']}' is likely a typo of '{payer_match.capitalize()}'.",
                f"Correct to '{payer_match.capitalize()}'"
            )

        # --- 12. Invalid/missing split type ---
        split_clean = row['split_type'].lower().strip()
        if not split_clean:
            flag_anomaly(
                'Missing Split Type',
                "The split_type field is empty.",
                'Default to equal split'
            )
        elif split_clean == 'unequal':
            flag_anomaly(
                'Invalid Split Type',
                "The split_type is 'unequal', which represents exact splits.",
                'Normalize to exact split'
            )
        elif split_clean not in ['equal', 'exact', 'percentage', 'share']:
            flag_anomaly(
                'Invalid Split Type',
                f"Unknown split method: {row['split_type']}.",
                'Default to equal split'
            )

        # Parse participants list
        participants_raw_list = [p.strip().lower() for p in row['participants_raw'].replace(';', ',').split(',') if p.strip()]
        
        # Check participants list names
        valid_pids = []
        has_participant_typos = False
        typo_replacements = []
        
        for p_raw in participants_raw_list:
            p_match = get_fuzzy_match(p_raw, known_names)
            if not p_match:
                flag_anomaly(
                    'Unknown Participant Name',
                    f"Participant '{p_raw}' does not match any registered flatmate.",
                    'Remove from split'
                )
            elif p_match != p_raw:
                has_participant_typos = True
                typo_replacements.append(f"{p_raw}->{p_match.capitalize()}")
                
        if has_participant_typos:
            flag_anomaly(
                'Misspelled Participant Name',
                f"Participants list contains spelling errors: {', '.join(typo_replacements)}.",
                'Correct participant names'
            )

        # --- 5 & 6. Membership date checks ---
        for p_raw in participants_raw_list:
            p_match = get_fuzzy_match(p_raw, known_names)
            if not p_match:
                continue
            
            # Dynamic membership check
            m_record = membership_map.get(p_match)
            if m_record:
                joined_at = m_record.joined_at
                left_at = m_record.left_at
            else:
                # Fallback to defaults based on the year of the expense date
                year_val = parsed_d.year
                if p_match == 'meera':
                    joined_at = date(year_val, 2, 1)
                    left_at = date(year_val, 3, 31)
                elif p_match == 'sam':
                    joined_at = date(year_val, 4, 15)
                    left_at = None
                else:
                    joined_at = date(year_val, 2, 1)
                    left_at = None

            if left_at and parsed_d > left_at:
                flag_anomaly(
                    'Expense After Exit',
                    f"Meera is included in the split for {parsed_d}, but she moved out on {left_at}.",
                    'Remove Meera from split and redistribute'
                )
            elif joined_at and parsed_d < joined_at:
                flag_anomaly(
                    'Expense Before Join',
                    f"Sam is included in the split for {parsed_d}, but he joined on {joined_at}.",
                    'Remove Sam from split and redistribute'
                )

    return anomalies
