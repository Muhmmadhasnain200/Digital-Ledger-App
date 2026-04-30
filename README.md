# Income & Expense Tracker

A beginner-friendly full-stack web app to manage monthly budgets, track expenses, and visualize spending behavior.

## Tech Stack

- Frontend: HTML, CSS, JavaScript, Chart.js
- Backend: Python Flask
- Database: SQLite

## Features

- Set and update monthly budget
- Add and delete expenses with amount, date, category, and description
- Expense list/table view
- Auto calculations:
  - Total monthly expenses
  - Remaining budget
  - Profit or loss
- Insights:
  - Weekly increase/decrease spending message
  - Top spending category
- Visualizations:
  - Pie chart by category
  - Bar chart weekly comparison
- Data persistence using SQLite
- Dark mode toggle (saved in browser local storage)
- Budget alerts when budget is near/exceeded
- Export expenses to CSV

## Project Structure

```text
income-expense-tracker/
  backend/
    app.py
    requirements.txt
    tracker.db (auto-created at runtime)
  frontend/
    index.html
    styles.css
    app.js
  README.md
```

## Setup & Run (Step-by-step)

### 1) Backend Setup

1. Open terminal in `income-expense-tracker/backend`
2. Create virtual environment:
   - Windows PowerShell:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run backend:
   ```powershell
   python app.py
   ```
5. API starts at `http://127.0.0.1:5000`

### 2) Frontend Setup

1. Open another terminal in `income-expense-tracker/frontend`
2. Start any static server (pick one option):

   - Python:
     ```powershell
     python -m http.server 5500
     ```

3. Open browser:
   - `http://127.0.0.1:5500`

## How to Use

1. Set your monthly budget from the top form.
2. Add expense entries with date, category, and amount.
3. Watch dashboard stats update automatically.
4. Check insights and charts to understand spending patterns.
5. Export your records using **Export CSV**.

## Notes

- SQLite database file `tracker.db` is auto-created and persists data between restarts.
- If frontend cannot reach backend, ensure Flask app is running on port `5000`.
