import re
from datetime import datetime
from decimal import Decimal

def parse_date(date_str):
    """
    Attempts to parse date using multiple formats.
    Returns datetime.date or None if parsing fails.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%m-%d-%Y',
        '%m/%d/%Y',
        '%Y/%m/%d'
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    # Try formats like 'Mar-14' (Month-Day)
    for fmt in ['%b-%d', '%d-%b', '%d %b', '%b %d']:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(year=2026).date()
        except ValueError:
            continue

    # Try formats with 2-digit or 4-digit years like 'Mar-26'
    for fmt in ['%b-%y', '%y-%b', '%b-%Y', '%Y-%b']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    return None

def clean_amount(amount_str):
    """
    Strips symbols (₹, $, Rs., commas) and parses as Decimal.
    Returns (cleaned_decimal, is_usd).
    """
    if not amount_str:
        return Decimal('0.00'), False
    
    amount_str = amount_str.strip()
    is_usd = '$' in amount_str or 'usd' in amount_str.lower()
    
    # Strip symbols and commas
    cleaned = re.sub(r'[₹$a-zA-Z\s,]', '', amount_str)
    
    try:
        return Decimal(cleaned), is_usd
    except Exception:
        return Decimal('0.00'), is_usd

def parse_custom_split(notes_str):
    """
    Parses custom split mapping from notes if formatted as 'Name:Value, Name:Value...'
    or 'Name Value; Name Value...' (supporting percentage signs and space separators).
    Returns a dict of {username.lower(): value (float)} or None if no match.
    """
    if not notes_str:
        return None
    
    notes_str = notes_str.strip()
    if not notes_str:
        return None
        
    # Strip percent signs
    notes_str = notes_str.replace('%', '')
    
    # Split by comma or semicolon
    parts = re.split(r'[;,]', notes_str)
    res = {}
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Match "Name:Value" or "Name Value". Value can be a decimal, potentially negative.
        match = re.match(r'^([a-zA-Z\s]+?)(?::|\s+)(-?\d+(?:\.\d+)?)$', part)
        if match:
            name = match.group(1).strip().lower()
            val = float(match.group(2))
            res[name] = val
    return res if res else None

