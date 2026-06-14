# SCOPE.md: Anomaly Log & Database Schema

## 🗄️ Database Schema

We implemented the following relational database tables in SQLite for local development (which maps 1:1 to the required PostgreSQL schema):

```sql
-- Accounts (uses Django's django.contrib.auth.models.User)
CREATE TABLE auth_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL, -- Mapped to Display Name
    email VARCHAR(254) NOT NULL,
    password VARCHAR(128) NOT NULL
);

-- Groups
CREATE TABLE groups_group (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_by_id INTEGER REFERENCES auth_user(id),
    created_at DATETIME NOT NULL
);

-- Date-aware memberships
CREATE TABLE groups_groupmembership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES auth_user(id),
    group_id INTEGER REFERENCES groups_group(id),
    joined_at DATE NOT NULL,
    left_at DATE, -- NULL means active
    UNIQUE(user_id, group_id)
);

-- Expenses
CREATE TABLE expenses_expense (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER REFERENCES groups_group(id),
    description VARCHAR(255) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    exchange_rate DECIMAL(10,4) NOT NULL,
    amount_in_inr DECIMAL(12,2) NOT NULL, -- computed total_amount * exchange_rate
    paid_by_id INTEGER REFERENCES auth_user(id),
    expense_date DATE NOT NULL,
    split_type VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    notes TEXT,
    source VARCHAR(20) NOT NULL, -- 'manual' or 'import'
    import_session_id INTEGER,
    created_at DATETIME NOT NULL
);

-- Splits per member
CREATE TABLE expenses_expensesplit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id INTEGER REFERENCES expenses_expense(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES auth_user(id),
    amount_owed DECIMAL(12,2) NOT NULL,
    is_settled BOOLEAN NOT NULL,
    settled_at DATETIME
);

-- Settlements / payback payments
CREATE TABLE expenses_settlement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER REFERENCES groups_group(id),
    payer_id INTEGER REFERENCES auth_user(id),
    receiver_id INTEGER REFERENCES auth_user(id),
    amount DECIMAL(12,2) NOT NULL,
    settlement_date DATE NOT NULL,
    notes TEXT,
    created_at DATETIME NOT NULL
);

-- CSV import batches
CREATE TABLE importer_importsession (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) NOT NULL,
    imported_by_id INTEGER REFERENCES auth_user(id),
    imported_at DATETIME NOT NULL,
    total_rows INTEGER NOT NULL,
    clean_rows INTEGER NOT NULL,
    anomaly_rows INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- CSV anomaly reviews
CREATE TABLE importer_importanomaly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES importer_importsession(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    raw_data TEXT NOT NULL, -- JSON row
    issue_type VARCHAR(100) NOT NULL,
    issue_description TEXT NOT NULL,
    proposed_action VARCHAR(100) NOT NULL,
    action_taken VARCHAR(100),
    approved_by_id INTEGER REFERENCES auth_user(id),
    status VARCHAR(20) NOT NULL
);
```

***

## ⚠️ CSV Anomalies Log

| # | Anomaly Type | Target Row(s) | Description | Applied Policy | Rationale |
|---|---|---|---|---|---|
| 1 | Exact duplicate row | Row 7 | Row 7 is identical to Row 6 (Electricity bill). | Flagged. Skipped / deleted on approval. | Avoids double-billing the household. |
| 2 | Near-duplicate | Row 12 | Row 12 (Trip Cab $90) shares the date and description with Row 11 ($80). | Flagged. Approved keeps higher amount or splits both. | Safest guess or user resolution. |
| 3 | Settlement as expense | Row 13 | `"Rohan paid Aisha back"` logged in description. | Auto-reclassified from expenses to settlements. | Prevents balance calculations from treating debt paybacks as overhead. |
| 4 | USD amount treated as INR | Row 10 | Amount contains `$` but currency column is blank. | Converted at RBI rate (June 2024: ₹83.50/$). | Converts USD expenses to group currency (INR). |
| 5 | Expense after exit | Row 18 | `April Cleaning supplies` includes ex-member Meera. | Removed Meera from split; redistributed to active members. | Meera moved out on Mar 31 and shouldn't pay. |
| 6 | Expense before join | Row 17 | `March Water bill` includes Sam (joined mid-April). | Removed Sam from split; redistributed to active members. | Sam hadn't moved in yet and shouldn't pay. |
| 7 | Inconsistent date format | Row 21, 22 | Dates like `15/05/2024` or `05-20-2024` instead of YYYY-MM-DD. | Normalized to ISO date objects. | Uniform date filtering and sorting. |
| 8 | Inconsistent amount format | Row 4, 15 | Amounts logged as `₹1,500.00` or `Rs.600`. | Stripped symbols/commas and parsed as clean Decimal. | Prevents parser crash; retains exact float accuracy. |
| 9 | Negative amount | Row 20 | Grocery refund recorded as `-1200`. | Processed as refund (negative expense) to credit participants. | Accurately credits members for refunds. |
| 10 | Missing payer | Row 23 | `June planning snacks` has a blank paid_by field. | Blocked row. Prompted user for correction. | Cannot evaluate balance without knowing who paid. |
| 11 | Unknown misspelled name | Row 14 | Payer name spelled `Rohn` instead of `Rohan`. | Fuzzy matched to closest name `Rohan`. | Prevents data loss on minor spelling typos. |
| 12 | Invalid split type | Row 16 | `March Gas bill` has a blank split method. | Applied default equal split policy. | Fallback ensures splitting doesn't crash the import. |
