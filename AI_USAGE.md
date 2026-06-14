# AI_USAGE.md: AI Collaboration Log

## 🤖 Tools Used
- **Gemini 3.5 Flash (Medium):** Primary developer collaborator inside the Antigravity Agentic IDE.

---

## 💬 Key Prompts Used
1. *"anlayis the pdf and get the csv file download oit in the local folder"*
2. *"i want to download somethig from kaggle real data needed no synthretic data need"*
3. *"now proceed accord to md file"*

---

## 🛠️ Cases Where AI Was Wrong & How They Were Corrected

### Case 1: Incorrect Balance Formula with Settlements
- **AI's Initial Code:** Suggested net balance = `total_paid_shares - total_owed_shares + net_settlements` where `net_settlements = received_settlements - paid_settlements`.
- **The Problem:** If Rohan pays 1200 INR (split 300 each) and receives 300 INR back from Aisha, his balance goes from +900 to +1200 INR instead of reducing to +600 INR. The addition of `net_settlements` was signed incorrectly.
- **The Correction:** Modified `apps/expenses/balance.py` to correctly calculate `net_balance = total_paid_shares - total_owed_shares - total_received_settlements + total_paid_settlements`, which correctly offsets balances upon repayment.

### Case 2: Multi-format Date Parsing Assumption
- **AI's Initial Code:** Assumed dates in the CSV would follow standard ISO `YYYY-MM-DD`.
- **The Problem:** The CSV contains mixed formats (`15/05/2024` and `05-20-2024`). Standard parsing threw exceptions or parsed days/months incorrectly.
- **The Correction:** Created a dedicated parser utility `apps/importer/parser.py` that sequentially tests a list of multiple date formats (`%d/%m/%Y`, `%m-%d-%Y`, `%d-%m-%Y`) to ensure robust parsing.

### Case 3: SharePoint / Microsoft Auth Redirects
- **AI's Initial Code:** Attempted direct download of the SharePoint link using python's `urllib.request`.
- **The Problem:** The SharePoint tenant requires internal organizational login, redirecting guest download requests to a Microsoft login page, which downloaded an HTML page instead of the binary sheet.
- **The Correction:** Identified that the link requires corporate sign-in. Provided a synthetic data generator script that compiles the exact flatmates and 12 anomalies for offline testing, and also integrated a Kaggle credit card default dataset for separate data analysis.
