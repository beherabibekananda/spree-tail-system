# DECISIONS.md: Decision Log

## Decision 1: Fixed vs Live Exchange Rate for USD
- **Options Considered:**
  - **A: Live Exchange Rate API:** Call an external API (like Fixer.io or ExchangeRate-API) on import.
  - **B: Fixed Exchange Rate at Import Time:** Use a fixed exchange rate (e.g. ₹83.50/$ based on RBI June 2024 rate) specified at import or pre-filled.
- **Decision:** **Option B (Fixed Rate)**
- **Rationale:** Expenses recorded are historical. A live API fetches today's rate, which is incorrect for transactions that occurred months ago. A fixed rate is auditable, repeatable, doesn't require an external API key, and guarantees consistent calculations between imports.

---

## Decision 2: Allocation of Rounding Remainders
- **Options Considered:**
  - **A: Distribute remainder to the payer:** Add the remaining paise to the member who paid for the expense.
  - **B: Distribute remainder to the first participant:** Add the remainder to the first person listed in the participants list.
- **Decision:** **Option B (First Participant)**
- **Rationale:** This is standard practice in split engines to ensure the sum of splits equals the exact transaction total. Adding it to the first participant is simple to implement and avoids coupling split allocation directly to the payer's identity.

---

## Decision 3: Local Database Selection
- **Options Considered:**
  - **A: PostgreSQL:** Install local PostgreSQL server on developer's laptop.
  - **B: SQLite:** Use Django's default built-in SQLite engine locally.
- **Decision:** **Option B (SQLite)**
- **Rationale:** Setting up a local PostgreSQL server requires system-level admin installations, and since the database CLI was not available on the terminal, SQLite was used for rapid development. SQLite is relational, has full support for Django's `DecimalField` (storing values as strings to prevent float arithmetic errors), and can easily transition to PostgreSQL in production via environment configuration (`dj-database-url`).

---

## Decision 4: Handling Ex-Member and Before-Join Splits
- **Options Considered:**
  - **A: Block import of the entire row:** If a member is included in a split outside their active membership dates, fail the row.
  - **B: Remove ex-member from split and redistribute:** Skip the inactive member and divide their portion among the other active participants.
- **Decision:** **Option B (Remove and Redistribute)**
- **Rationale:** This prevents data entry errors (or automated sheets mistakes) from halting the entire import pipeline while maintaining the business rule that ex-members shouldn't pay for expenses logged after they left (Sam & Meera's requirement).
