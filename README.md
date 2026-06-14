# Shared Expenses App (Spreetail Assignment)

A responsive, premium web application built with **Django** and **SQLite** to manage and split household expenses among flatmates. It features a complete CSV import validation pipeline, date-aware member splitting, and peer-to-peer settlement solving.

## 🚀 Setup & Execution

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Installation
Install project dependencies:
```bash
pip install -r requirements.txt
```
*(Dependencies: `Django`, `openpyxl`, `kagglehub`)*

### 3. Database Initialization & Seeding
Run migrations and seed the database with standard flatmate profiles (Aisha, Rohan, Priya, Meera, Sam, Dev) and their correct membership timelines:
```bash
python manage.py migrate
python manage.py seed_db
```
*Note: All seeded users have the password set to `password123`.*

### 4. Running the Dev Server
Launch the local web server:
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000/` in your browser.

### 5. Running Tests
Execute unit tests for split calculations, date-aware memberships, and anomaly detection:
```bash
python manage.py test apps/expenses apps/importer
```

## 👥 Seed Accounts for Testing
To test different views (Aisha's net settlements, Rohan's audit trails, Meera's anomaly approvals), you can log in as any of the following users with password `password123`:
- `aisha` (Active since Feb)
- `rohan` (Active since Feb)
- `priya` (Active since Feb)
- `meera` (Active Feb → end of March)
- `sam` (Active mid-April → present)
- `dev` (Active since Feb)
