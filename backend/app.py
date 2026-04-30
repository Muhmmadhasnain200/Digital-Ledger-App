import csv
import io
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tracker.db"

app = Flask(__name__)
CORS(app)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            monthly_budget REAL NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK (amount >= 0),
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO settings(id, monthly_budget) VALUES(1, 0)
        """
    )
    conn.commit()
    conn.close()


def parse_iso_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/budget", methods=["GET"])
def get_budget():
    conn = get_db_connection()
    row = conn.execute("SELECT monthly_budget FROM settings WHERE id = 1").fetchone()
    conn.close()
    return jsonify({"monthly_budget": row["monthly_budget"] if row else 0})


@app.route("/api/budget", methods=["POST"])
def set_budget():
    data = request.get_json(silent=True) or {}
    budget = data.get("monthly_budget")

    if budget is None:
        return jsonify({"error": "monthly_budget is required"}), 400

    try:
        budget = float(budget)
    except (ValueError, TypeError):
        return jsonify({"error": "monthly_budget must be a number"}), 400

    if budget < 0:
        return jsonify({"error": "monthly_budget cannot be negative"}), 400

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE settings
        SET monthly_budget = ?
        WHERE id = 1
        """,
        (budget,),
    )
    conn.commit()
    conn.close()

    return jsonify({"monthly_budget": budget})


@app.route("/api/expenses", methods=["GET"])
def list_expenses():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT id, amount, date, category, description
        FROM expenses
        ORDER BY date DESC, id DESC
        """
    ).fetchall()
    conn.close()
    expenses = [dict(row) for row in rows]
    return jsonify(expenses)


@app.route("/api/expenses", methods=["POST"])
def create_expense():
    data = request.get_json(silent=True) or {}

    amount = data.get("amount")
    expense_date = data.get("date")
    category = (data.get("category") or "").strip()
    description = (data.get("description") or "").strip()

    if amount is None or not expense_date or not category:
        return jsonify({"error": "amount, date, and category are required"}), 400

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a number"}), 400

    if amount < 0:
        return jsonify({"error": "amount cannot be negative"}), 400

    try:
        parse_iso_date(expense_date)
    except ValueError:
        return jsonify({"error": "date must be in YYYY-MM-DD format"}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO expenses(amount, date, category, description)
        VALUES(?, ?, ?, ?)
        """,
        (amount, expense_date, category, description),
    )
    conn.commit()

    row = conn.execute(
        """
        SELECT id, amount, date, category, description
        FROM expenses
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return jsonify({"error": "expense not found"}), 404

    return jsonify({"deleted": expense_id})


def total_for_range(start_day, end_day):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE date >= ? AND date <= ?
        """,
        (start_day.isoformat(), end_day.isoformat()),
    ).fetchone()
    conn.close()
    return float(row["total"]) if row else 0.0


@app.route("/api/summary", methods=["GET"])
def get_summary():
    today = date.today()
    month_start = today.replace(day=1)

    conn = get_db_connection()
    budget_row = conn.execute(
        "SELECT monthly_budget FROM settings WHERE id = 1"
    ).fetchone()

    total_row = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE date >= ?
        """,
        (month_start.isoformat(),),
    ).fetchone()

    category_rows = conn.execute(
        """
        SELECT category, ROUND(SUM(amount), 2) AS total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
        """
    ).fetchall()

    # Weekly comparison: last 4 weeks including current week.
    weekly_totals = []
    for weeks_ago in range(3, -1, -1):
        end_day = today - timedelta(days=today.weekday()) - timedelta(days=7 * weeks_ago) + timedelta(days=6)
        start_day = end_day - timedelta(days=6)
        weekly_totals.append(
            {
                "label": f"{start_day.strftime('%b %d')} - {end_day.strftime('%b %d')}",
                "total": round(total_for_range(start_day, end_day), 2),
            }
        )

    conn.close()

    budget = float(budget_row["monthly_budget"]) if budget_row else 0.0
    total_expenses = float(total_row["total"]) if total_row else 0.0
    remaining_budget = budget - total_expenses
    profit_or_loss = remaining_budget

    current_week = weekly_totals[-1]["total"] if weekly_totals else 0
    previous_week = weekly_totals[-2]["total"] if len(weekly_totals) > 1 else 0

    if current_week > previous_week:
        week_insight = "You spent more this week than last week."
    elif current_week < previous_week:
        week_insight = "Good job! You spent less this week than last week."
    else:
        week_insight = "Your spending this week is the same as last week."

    top_category = category_rows[0]["category"] if category_rows else "N/A"
    top_category_text = f"Most money spent on: {top_category}"

    # Budget alert threshold at 90%.
    alert = None
    if budget > 0:
        used_pct = (total_expenses / budget) * 100
        if used_pct >= 100:
            alert = "Budget exceeded! You are over your monthly limit."
        elif used_pct >= 90:
            alert = "Warning: You are close to your budget limit."

    return jsonify(
        {
            "monthly_budget": round(budget, 2),
            "total_expenses": round(total_expenses, 2),
            "remaining_budget": round(remaining_budget, 2),
            "profit_or_loss": round(profit_or_loss, 2),
            "weekly_totals": weekly_totals,
            "category_totals": [dict(row) for row in category_rows],
            "insights": [week_insight, top_category_text],
            "alert": alert,
        }
    )


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT id, amount, date, category, description
        FROM expenses
        ORDER BY date DESC, id DESC
        """
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "amount", "date", "category", "description"])
    for row in rows:
        writer.writerow([row["id"], row["amount"], row["date"], row["category"], row["description"] or ""])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    output.close()

    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name="expenses_export.csv",
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
x``