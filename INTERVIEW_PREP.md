# Spreetail Live Interview Preparation Guide

This guide maps the **8 questions you will be asked live during the 45-minute interviewer session** to the exact files and logic in this codebase.

---

### 1. "Walk me through what happens when row 14 of the CSV hits your importer"
- **Step 1: Upload & Parse**
  - In [importer/views.py](file:///Users/bibekanandabehera/Desktop/Speertail/apps/importer/views.py#L12), the `import_csv` view saves the file to disk and parses rows into dictionaries using python's `csv.DictReader`.
- **Step 2: Anomaly Detection**
  - It runs `detect_anomalies` from [importer/detector.py](file:///Users/bibekanandabehera/Desktop/Speertail/apps/importer/detector.py#L32), which runs 12 validation checks.
  - If it finds issues (e.g. misspelled names, date formatting, duplicate entries), it writes them to the `ImportAnomaly` database table with a `'pending'` status and renders the review dashboard [importer/import_review.html](file:///Users/bibekanandabehera/Desktop/Speertail/templates/importer/import_review.html#L1).
- **Step 3: User Review & Resolution**
  - The flatmates review proposed resolutions and click **Approve** or **Reject** (handled via AJAX endpoint `import_anomaly_action` in `importer/views.py`).
- **Step 4: Committing to Database**
  - Clicking **Commit Import** triggers `import_commit` in [importer/views.py](file:///Users/bibekanandabehera/Desktop/Speertail/apps/importer/views.py#L122). It parses the row again, applies the approved correction policies, creates the `Expense`/`Settlement` records, and generates the `ExpenseSplit` breakdown.

---

### 2. "Why did you use a fixed exchange rate instead of a live API?"
- **Answer:** Historical transactions occurred in the past (e.g., February/March 2024). Calling a live exchange rate API would fetch *today's* exchange rate, which is incorrect for historical balances.
- **Reference:** Documented in [DECISIONS.md](file:///Users/bibekanandabehera/Desktop/Speertail/DECISIONS.md#L3) (Decision 1).

---

### 3. "How does your app know Sam shouldn't pay March electricity?"
- **Answer:** In [expenses/utils.py](file:///Users/bibekanandabehera/Desktop/Speertail/apps/expenses/utils.py#L4), the helper `get_active_participants_on_date` checks each participant's `GroupMembership` dates. 
- Since Sam's `joined_at` is `2024-04-15`, any expense dated in March (e.g., March electricity) fails the condition `membership.joined_at <= expense_date`, and Sam is excluded from participating in that split.

---

### 4. "Show me the query that produces Rohan's balance"
- **Answer:** Point them to [expenses/balance.py](file:///Users/bibekanandabehera/Desktop/Speertail/apps/expenses/balance.py#L4) (`get_member_balance`).
- **Logic:** 
  1. Queries all expenses paid by Rohan to add to his credit.
  2. Queries all `ExpenseSplit` records where Rohan is a participant (excluding expenses he paid himself) to calculate what he owes.
  3. Queries all settlements where Rohan is the payer (adds to credit) or receiver (subtracts from credit).
  4. Returns the sum total alongside a granular audit trail.

---

### 5. "Change the rounding rule from floor to banker's rounding — do it live"
- **Answer:** In [expenses/utils.py](file:///Users/bibekanandabehera/Desktop/Speertail/apps/expenses/utils.py#L22) (`calculate_splits`), we use Python's `Decimal.quantize()`.
- Python's default rounding mode for `.quantize(Decimal('0.01'))` is **`ROUND_HALF_EVEN`** (which is banker's rounding!).
- To change it to floor (truncation), change it to:
  `per_person = (total / n).quantize(Decimal('0.01'), rounding=rounding.ROUND_DOWN)`
  *(Remember to import `ROUND_DOWN` / `ROUND_HALF_EVEN` from `decimal`)*

---

### 6. "What happens if the same person is listed in a split twice?"
- **Answer:** In [importer/detector.py](file:///Users/bibekanandabehera/Desktop/Speertail/apps/importer/detector.py#L32), the parser strips duplicates, and the detector will log any duplicate participant names as anomalies, removing duplicates and flagging them for user review.

---

### 7. "Why is your settlement table separate from expenses?"
- **Answer:** Settlements represent direct transfers between members to repay debts, which affect net balances but are not collective overhead expenses. Mixing them with expenses corrupts balance calculations.
- **Reference:** Documented in [DECISIONS.md](file:///Users/bibekanandabehera/Desktop/Speertail/DECISIONS.md#L37) (Decision 4).

---

### 8. "Add a new split type — 'by room size' — live"
- **Answer:** 
  1. In [expenses/utils.py](file:///Users/bibekanandabehera/Desktop/Speertail/apps/expenses/utils.py#L22) (`calculate_splits`), add a new `elif split_type == 'room_size':` block.
  2. Map room sizes in `custom_data` (e.g. Rohan: 150 sq ft, Priya: 120 sq ft).
  3. Distribute the expense proportionally: `amount = total * room_size / total_room_size`.
  4. Distribute the rounding remainder to the first participant.
