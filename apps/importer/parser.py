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
        '%m-%d-%Y',
        '%d-%m-%Y',
        '%Y/%m/%d'
    ]
    for fmt in formats:
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
    Returns a dict of {username.lower(): value (float)} or None if no match.
    """
    if not notes_str:
        return None
    
    # Pattern: Name:Value (separated by commas or semicolons)
    pattern = r'([a-zA-Z]+)\s*:\s*(-?\d+(?:\.\d+)?)'
    matches = re.findall(pattern, notes_str)
    if not matches:
        return None
        
    res = {}
    for name, val in matches:
        res[name.lower().strip()] = float(val)
    return res
