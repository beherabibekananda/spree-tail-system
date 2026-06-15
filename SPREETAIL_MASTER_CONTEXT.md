# 🧾 Spreetail Assignment: Shared Expenses App — Master Context File
> Use this file as your primary context prompt when working with any AI tool (ChatGPT, Gemini, Cursor, Copilot, etc.)
> Paste the relevant sections into your AI tool along with your specific question.

---

## 📌 ABOUT THIS ASSIGNMENT

You are acting as both **Product Manager and Developer** for Spreetail's internship assignment.

**Goal:** Build and deploy a shared expenses web app in 2 days.

**You will be evaluated live** — a 45-minute session where interviewers will:
- Pick CSV anomalies and ask you to trace them in your code
- Ask you to modify features live (e.g., change rounding rules, add split types)
- Point at any line of code and ask why it exists
- Walk through balance calculations by hand for one member

> ⚠️ A rough app you understand completely scores HIGHER than a polished app you cannot explain.

---

## 👥 THE PEOPLE (Characters in the Story)

| Person | Role | Active Period | Special Notes |
|--------|------|--------------|---------------|
| Aisha | Flatmate | Feb → present | Wants: one net number per person |
| Rohan | Flatmate | Feb → present | Wants: full audit trail for every balance |
| Priya | Flatmate | Feb → present | Wants: proper USD→INR currency conversion |
| Meera | Flatmate | Feb → end of March | Moved out. Wants: approve before anything is deleted |
| Dev | Guest | Trip only | Joined for a trip. Some expenses in USD |
| Sam | New Flatmate | Mid-April → present | Wants: not to pay for expenses before he joined |

---

## 📋 WHAT EACH PERSON WANTS (PM Requirements)

```
Aisha  → "I just want one number per person. Who pays whom, how much, done."
          → FEATURE: Net settlement summary page

Rohan  → "No magic numbers. If the app says I owe ₹2,300, I want to see 
          exactly which expenses make that up."
          → FEATURE: Full expense audit trail behind every balance

Priya  → "Half the trip was in dollars. The sheet pretends a dollar is a 
          rupee. That can't be right."
          → FEATURE: Currency field + exchange rate on every expense

Sam    → "I moved in mid-April. Why would March electricity affect my balance?"
          → FEATURE: Membership date-aware splits (joined_at / left_at)

Meera  → "Clean up the duplicates — but I want to approve anything the 
          app deletes or changes."
          → FEATURE: Anomaly approval flow before import commits changes
```

---

## 📁 THE CSV FILE: expenses_export.csv

### What It Is
- A messy spreadsheet export from Google Sheets
- Contains expenses tracked since February by the flatmates
- Has **at least 12 deliberate data problems** embedded by Spreetail
- You CANNOT edit it by hand before importing — app must handle raw file

### How to Get It
- It should have been attached to Spreetail's assignment email
- Check your email attachments, Google Drive links, or assignment portal
- If missing: email Spreetail asking for the CSV file

### Expected CSV Structure (likely columns)
```
date, description, amount, currency, paid_by, split_type, 
participants, notes
```

### The 12 Known Data Problem Categories
Based on the assignment brief, these are the types of problems to detect:

| # | Problem Type | Example | Detection Strategy |
|---|-------------|---------|-------------------|
| 1 | Exact duplicate row | Same dinner logged twice | Hash entire row, find matches |
| 2 | Near-duplicate (same event, different amounts) | Two people logged same dinner ₹1200 vs ₹1350 | Match on date+description, flag amount diff |
| 3 | Settlement recorded as expense | "Rohan paid Aisha back" logged as expense | Detect keywords: paid back, settlement, transfer |
| 4 | USD amount treated as INR | $45 written as 45 with no currency marker | Check for $ symbol, inconsistent amounts |
| 5 | Expense after Meera's exit with Meera in split | April expense includes Meera | Check expense date vs membership left_at |
| 6 | Expense before Sam's join with Sam in split | March expense includes Sam | Check expense date vs membership joined_at |
| 7 | Inconsistent date formats | 15/03/2024 vs 03-15-2024 vs 2024-03-15 | Regex detect format, normalize to ISO |
| 8 | Inconsistent amount formats | ₹1,200 vs 1200 vs 1,200.00 vs Rs.1200 | Strip symbols, commas, normalize to Decimal |
| 9 | Negative amounts | -500 | Policy decision: treat as refund or flag as error |
| 10 | Missing payer | blank paid_by column | Flag as error, block that row |
| 11 | Unknown/misspelled person name | "Rohn" instead of "Rohan" | Fuzzy match against known members |
| 12 | Invalid/missing split type | blank or unknown split method | Flag, apply default equal split policy |

---

## 🏗️ MINIMUM PRODUCT REQUIREMENTS

1. **Login module** — user authentication (register + login + logout)
2. **Groups** — create/manage groups, membership changes over time
3. **Expenses:**
   - Support every split type in the CSV
   - Group-wise balances and individual balance summary
   - Settle debts / record payments
4. **Import expenses_export.csv** through the app UI
5. **Use relational databases only** (no MongoDB, Firebase, etc.)

---

## 🗄️ DATABASE SCHEMA (Complete)

```sql
-- Core user accounts
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Groups (flatmate households)
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Membership with date tracking (solves Sam + Meera problem)
CREATE TABLE group_memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    group_id INTEGER REFERENCES groups(id),
    joined_at DATE NOT NULL,
    left_at DATE,               -- NULL means still active
    UNIQUE(user_id, group_id)
);

-- Expenses
CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id),
    description VARCHAR(255) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',      -- 'INR' or 'USD'
    exchange_rate DECIMAL(10,4) DEFAULT 1.0, -- rate to INR at time of expense
    amount_in_inr DECIMAL(12,2),            -- computed: total_amount * exchange_rate
    paid_by INTEGER REFERENCES users(id),
    expense_date DATE NOT NULL,
    split_type VARCHAR(50) NOT NULL,        -- 'equal', 'exact', 'percentage', 'share'
    category VARCHAR(100),
    notes TEXT,
    source VARCHAR(20) DEFAULT 'manual',    -- 'manual' or 'import'
    import_session_id INTEGER,              -- which import batch this came from
    created_at TIMESTAMP DEFAULT NOW()
);

-- How each expense is split per person
CREATE TABLE expense_splits (
    id SERIAL PRIMARY KEY,
    expense_id INTEGER REFERENCES expenses(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    amount_owed DECIMAL(12,2) NOT NULL,     -- in INR always
    is_settled BOOLEAN DEFAULT FALSE,
    settled_at TIMESTAMP
);

-- Settlements / payments between members
CREATE TABLE settlements (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id),
    payer_id INTEGER REFERENCES users(id),  -- person paying
    receiver_id INTEGER REFERENCES users(id), -- person receiving
    amount DECIMAL(12,2) NOT NULL,
    settlement_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Track each CSV import batch
CREATE TABLE import_sessions (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    imported_by INTEGER REFERENCES users(id),
    imported_at TIMESTAMP DEFAULT NOW(),
    total_rows INTEGER,
    clean_rows INTEGER,
    anomaly_rows INTEGER,
    status VARCHAR(20) DEFAULT 'pending'    -- 'pending', 'approved', 'committed'
);

-- Every anomaly found during import (Meera's approval requirement)
CREATE TABLE import_anomalies (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES import_sessions(id),
    row_number INTEGER,
    raw_data TEXT,                          -- original CSV row as JSON
    issue_type VARCHAR(100),               -- category of problem
    issue_description TEXT,                -- human readable explanation
    proposed_action VARCHAR(100),          -- what the system will do
    action_taken VARCHAR(100),             -- what was actually done
    approved_by INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending'   -- 'pending', 'approved', 'rejected', 'applied'
);
```

---

## ⚙️ TECH STACK

```
Backend:     Django (Python) — you already know this
Database:    PostgreSQL — relational, handles decimals correctly
Frontend:    Django Templates + TailwindCSS (CDN, no build step needed)
Deployment:  Railway.app or Render.com (free, PostgreSQL included)
Auth:        Django's built-in auth system
```

### Why These Choices
- Django → built-in auth covers login requirement instantly
- PostgreSQL → DECIMAL type for money (never use FLOAT for currency)
- TailwindCSS CDN → no webpack/npm needed, fast to style
- Railway/Render → GitHub integration, auto-deploys, free PostgreSQL

---

## 🔄 IMPORT PIPELINE ARCHITECTURE

```
Step 1: FILE UPLOAD
  User uploads expenses_export.csv via browser
  ↓
Step 2: PARSE & NORMALIZE
  - Read every row
  - Normalize dates → ISO 8601 (YYYY-MM-DD)
  - Normalize amounts → strip ₹, $, Rs., commas → Python Decimal
  - Detect currency: $ symbol or 'USD' text → mark as USD
  - Store exchange rate used (document: fixed rate from assignment date)
  ↓
Step 3: ANOMALY DETECTION (run all checks)
  For each row:
  - Check for exact duplicates (hash comparison)
  - Check for near-duplicates (date+description similarity)
  - Check for settlement keywords
  - Check membership dates (Meera/Sam problem)
  - Check for missing required fields
  - Check for unknown person names (fuzzy match)
  - Check for negative amounts
  - Check for invalid split types
  → Write every flag to import_anomalies table
  ↓
Step 4: SURFACE TO USER (Import Review Page)
  Show table of all anomalies with:
  - Row number
  - Original data
  - Problem description  
  - Proposed action
  - Approve / Reject buttons (Meera's requirement)
  ↓
Step 5: COMMIT APPROVED ROWS
  - Apply approved actions
  - Import clean rows + approved-action rows into expenses table
  - Generate Import Report
  - Mark import_session as 'committed'
```

---

## 💰 BALANCE CALCULATION LOGIC

```python
def get_member_balance(user_id, group_id):
    """
    Returns net balance for a user in a group.
    Positive = they are owed money
    Negative = they owe money
    """
    # 1. Get all expenses where user is active member on that date
    expenses_paid_by_user = Expense.objects.filter(
        group_id=group_id, 
        paid_by=user_id
    )
    
    # 2. Sum what others owe this user
    total_paid = sum(e.amount_in_inr for e in expenses_paid_by_user)
    
    # 3. Sum what this user owes to others
    splits_owed = ExpenseSplit.objects.filter(
        expense__group_id=group_id,
        user_id=user_id,
        is_settled=False
    )
    total_owed = sum(s.amount_owed for s in splits_owed)
    
    # 4. Account for settlements
    paid_settlements = Settlement.objects.filter(group_id=group_id, payer_id=user_id)
    received_settlements = Settlement.objects.filter(group_id=group_id, receiver_id=user_id)
    
    net_settlements = (
        sum(s.amount for s in received_settlements) - 
        sum(s.amount for s in paid_settlements)
    )
    
    # 5. Net balance
    net = total_paid - total_owed + net_settlements
    
    # 6. Return with audit trail (Rohan's requirement)
    return {
        'net_balance': net,
        'total_paid': total_paid,
        'total_owed': total_owed,
        'contributing_expenses': list(splits_owed.values('expense_id', 'amount_owed')),
        'settlements': list(paid_settlements) + list(received_settlements)
    }
```

### Membership-Date-Aware Split Creation
```python
def create_splits_for_expense(expense, participant_ids):
    """
    Only create splits for members who were ACTIVE at expense date.
    This solves both Sam and Meera's problem.
    """
    active_members = []
    for user_id in participant_ids:
        membership = GroupMembership.objects.get(
            user_id=user_id, 
            group_id=expense.group_id
        )
        if membership.joined_at <= expense.expense_date:
            if membership.left_at is None or membership.left_at >= expense.expense_date:
                active_members.append(user_id)
            # else: member had left by this date — skip them
        # else: member hadn't joined yet — skip them
    
    return active_members
```

---

## 📂 PROJECT FOLDER STRUCTURE

```
spreetail-expenses/
├── manage.py
├── requirements.txt
├── README.md
├── SCOPE.md
├── DECISIONS.md
├── AI_USAGE.md
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── accounts/           ← Login, register, user profiles
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   │
│   ├── groups/             ← Groups + membership management
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   │
│   ├── expenses/           ← Expenses, splits, balance engine
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── balance.py      ← Balance calculation logic (separate file)
│   │   └── templates/
│   │
│   └── importer/           ← CSV import pipeline
│       ├── models.py       ← ImportSession, ImportAnomaly
│       ├── views.py        ← Upload, review, approve, commit
│       ├── parser.py       ← Normalize dates, amounts, currency
│       ├── detector.py     ← All 12 anomaly detection checks
│       ├── policies.py     ← What to do for each anomaly type
│       └── templates/
│
└── templates/
    └── base.html
```

---

## 📄 REQUIRED DELIVERABLE FILES

### 1. README.md
```markdown
# Shared Expenses App

## Setup
1. Clone repo
2. pip install -r requirements.txt
3. Set DATABASE_URL env variable
4. python manage.py migrate
5. python manage.py createsuperuser
6. python manage.py runserver

## Deployment
Deployed on Railway: [URL]

## AI Tools Used
- Claude (Anthropic) — architecture decisions, code scaffolding
- [List others]
```

### 2. SCOPE.md — Anomaly Log + Schema
```markdown
# SCOPE.md

## Database Schema
[Paste full schema here]

## CSV Anomalies Found

| # | Row | Problem | Policy Applied |
|---|-----|---------|----------------|
| 1 | 14  | Exact duplicate of row 7 | Flagged for approval, deleted if approved |
| 2 | 23  | USD amount without currency marker | Converted at ₹83.50/$ (RBI rate June 2024) |
...
```

### 3. DECISIONS.md — Decision Log
```markdown
# DECISIONS.md

## Decision 1: Fixed vs Live Exchange Rate for USD
Options:
- A) Live API (e.g., Fixer.io) — accurate but adds dependency
- B) Fixed rate at import time — simpler, auditable, no API key needed
Decision: Fixed rate. Reason: expenses are historical, rate at transaction 
date matters more than today's rate. We document which rate we used.

## Decision 2: What to do with negative amounts
Options:
- A) Treat as error, block import
- B) Treat as refund (negative expense)
Decision: Treat as refund. Reason: real-world expense tracking commonly 
uses negative values for refunds/reversals.
...
```

### 4. AI_USAGE.md
```markdown
# AI_USAGE.md

## Tools Used
- Claude (claude.ai) — primary development collaborator
- [others]

## Key Prompts Used
1. "Help me design a database schema for..."
2. "Write the anomaly detection logic for..."

## Cases Where AI Was Wrong

### Case 1: Wrong balance formula
AI suggested: balance = paid - owed
Problem: This ignored settlements between members
Fix: Added settlement table lookups to balance calculation

### Case 2: Date parsing assumption
AI assumed all dates were in MM/DD/YYYY
Problem: CSV has mixed formats including DD-MM-YYYY
Fix: Wrote multi-format parser with explicit format detection

### Case 3: Currency detection
AI used string "USD" to detect currency
Problem: CSV uses "$" symbol, not "USD" text
Fix: Added regex for $ symbol in amount field
```

---

## 🧪 ANOMALY HANDLING POLICIES (Document in SCOPE.md)

| Anomaly Type | Policy | Reason |
|-------------|--------|--------|
| Exact duplicate row | Flag → require user approval to delete | Meera's requirement |
| Near-duplicate (same event, diff amounts) | Flag both, suggest keeping higher amount | Safer assumption |
| Settlement as expense | Auto-reclassify to settlements table | Wrong table, not wrong data |
| USD without currency marker | Convert at fixed rate, flag for awareness | Priya's requirement |
| Expense after member left | Remove ex-member from split, redistribute | Sam/Meera requirement |
| Expense before member joined | Remove new member from split, redistribute | Sam's requirement |
| Negative amount | Treat as refund (negative expense) | Common real-world pattern |
| Bad date format | Parse with multi-format parser, flag if ambiguous | Don't silently guess |
| Missing payer | Block that row, show error | Cannot calculate balance without payer |
| Unknown person name | Fuzzy match, flag for user confirmation | Avoid silent data loss |
| Invalid split type | Default to equal split, flag | Safe fallback |
| Missing amount | Block that row, show error | Cannot process without amount |

---

## 🎯 SPLIT TYPES TO SUPPORT

```python
SPLIT_TYPES = {
    'equal': 'Split equally among all participants',
    'exact': 'Each person owes a specific fixed amount',
    'percentage': 'Each person owes a percentage of total',
    'share': 'Split by ratio/shares (e.g., 2:1:1)',
}

def calculate_split(expense, split_type, participants, custom_data=None):
    """
    Returns dict of {user_id: amount_owed}
    All amounts in INR.
    """
    total = expense.amount_in_inr
    n = len(participants)
    
    if split_type == 'equal':
        per_person = round(total / n, 2)
        # Handle rounding remainder: add to first person (payer)
        splits = {uid: per_person for uid in participants}
        remainder = total - (per_person * n)
        splits[participants[0]] += remainder
        return splits
    
    elif split_type == 'exact':
        # custom_data = {user_id: amount}
        assert sum(custom_data.values()) == total
        return custom_data
    
    elif split_type == 'percentage':
        # custom_data = {user_id: percentage}
        assert sum(custom_data.values()) == 100
        return {uid: round(total * pct / 100, 2) for uid, pct in custom_data.items()}
    
    elif split_type == 'share':
        # custom_data = {user_id: shares}
        total_shares = sum(custom_data.values())
        return {uid: round(total * shares / total_shares, 2) 
                for uid, shares in custom_data.items()}
```

---

## 🌐 DEPLOYMENT STEPS (Railway.app)

```bash
# 1. Push code to GitHub

# 2. Go to railway.app → New Project → Deploy from GitHub

# 3. Add PostgreSQL plugin in Railway

# 4. Set environment variables in Railway:
DATABASE_URL=<auto-set by Railway>
SECRET_KEY=<generate random string>
DEBUG=False
ALLOWED_HOSTS=<your-railway-domain>

# 5. Add Procfile to repo:
echo "web: gunicorn config.wsgi" > Procfile

# 6. Add to requirements.txt:
gunicorn
psycopg2-binary
whitenoise   # for static files

# 7. In settings.py:
import os
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
}
```

---

## 📅 2-DAY BUILD PLAN

### Day 1 (Focus: Core App)
| Time | Task |
|------|------|
| Hour 1 | Django project setup, PostgreSQL, all models |
| Hour 2 | Django auth (login/register/logout) |
| Hour 3 | Groups + membership views |
| Hour 4 | Expense create/edit/delete views |
| Hour 5 | Balance calculation engine (balance.py) |
| Hour 6 | Balance display UI + settlement recording |

### Day 2 (Focus: Import + Deploy + Docs)
| Time | Task |
|------|------|
| Hour 1 | CSV parser + normalizer |
| Hour 2 | Anomaly detector (all 12 checks) |
| Hour 3 | Import review page (approve/reject UI) |
| Hour 4 | Import commit + report generation |
| Hour 5 | Deploy to Railway, test end-to-end |
| Hour 6 | Write SCOPE.md, DECISIONS.md, AI_USAGE.md |

---

## ❓ QUESTIONS THE LIVE SESSION WILL ASK

Prepare answers for all of these:

1. **"Walk me through what happens when row 14 of the CSV hits your importer"**
   → Know your parser.py → detector.py → import_anomalies table flow

2. **"Why did you use a fixed exchange rate instead of a live API?"**
   → Historical expenses need the rate at transaction time, not today's rate.
   Fixed rate is auditable and doesn't add external dependencies.

3. **"How does your app know Sam shouldn't pay March electricity?"**
   → GroupMembership.joined_at = mid-April. Importer checks expense_date 
   vs joined_at. If expense_date < joined_at, Sam is removed from splits.

4. **"Show me the query that produces Rohan's balance"**
   → Point to balance.py. Walk through ExpenseSplit query → sum → settlements.

5. **"Change the rounding rule from floor to banker's rounding — do it live"**
   → It's one line in calculate_split(). Know where it is before the session.

6. **"What happens if the same person is listed in a split twice?"**
   → Detector catches it. Deduplicate, flag as anomaly, record in import_anomalies.

7. **"Why is your settlement table separate from expenses?"**
   → Settlements clear debts but aren't expenses. Mixing them (as the CSV did) 
   corrupts balance calculations. One of the 12 anomalies is exactly this.

8. **"Add a new split type — 'by room size' — live"**
   → It's just a new case in calculate_split() + a new SPLIT_TYPES entry.
   Know where that function is.

---

## 🚀 AI TOOL USAGE GUIDE

When using this file with other AI tools, use these section headers as prompts:

### For ChatGPT / Gemini
```
Context: [paste TECH STACK section]
Task: [paste DATABASE SCHEMA section]
Question: Generate Django models.py for this schema
```

### For Cursor / GitHub Copilot
```
// Context: Spreetail shared expenses app
// See SPREETAIL_MASTER_CONTEXT.md for full schema
// Task: implement anomaly detector for CSV import
```

### For Claude
```
Using the context in SPREETAIL_MASTER_CONTEXT.md,
help me implement the [specific feature] described in 
the [IMPORT PIPELINE / BALANCE CALCULATION / etc.] section.
```

---

## ⚡ QUICK REFERENCE: Key Business Rules

1. **Money is always stored in INR** — USD converted at import time
2. **Splits only include members active on the expense date** — check joined_at and left_at
3. **Settlements are NOT expenses** — different table, different calculation
4. **Every balance must trace to specific expense_split rows** — Rohan's requirement
5. **No anomaly is silently handled** — every issue goes to import_anomalies table
6. **Meera must approve deletions** — status field on import_anomalies
7. **Rounding remainder goes to first person (payer)** — document this in DECISIONS.md
8. **Exchange rate is fixed at import time** — document which rate and why

---

*Generated for Spreetail Internship Assignment — Shared Expenses App*
*Use this as master context for all AI tools you work with*
