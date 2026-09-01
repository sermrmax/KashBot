import sqlite3
from datetime import datetime

DB_NAME = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()

def add_expense(user_id: int, amount: float, category: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO expenses (user_id, amount, category, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            amount,
            category,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()

def get_today_expenses(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    today = datetime.now().date().isoformat()

    cursor.execute(
        """
        SELECT amount, category, created_at
        FROM expenses
        WHERE user_id = ?
        AND DATE(created_at) = ?
        """,
        (
            user_id,
            today
        )
    )

    expenses = cursor.fetchall()

    conn.close()

    return expenses

def get_month_expenses(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    current_month = datetime.now().strftime("%Y-%m")

    cursor.execute(
        """
        SELECT amount, category, created_at
        FROM expenses
        WHERE user_id = ?
        AND strftime('%Y-%m', created_at) = ?
        ORDER BY created_at DESC
        """,
        (
            user_id,
            current_month
        )
    )

    expenses = cursor.fetchall()

    conn.close()

    return expenses

def get_recent_expenses(user_id: int, limit: int = 10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, amount, category, created_at
        FROM expenses
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    )

    expenses = cursor.fetchall()

    conn.close()

    return expenses

def delete_expense(expense_id: int, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM expenses
        WHERE id = ?
        AND user_id = ?
        """,
        (
            expense_id,
            user_id
        )
    )

    conn.commit()
    conn.close()

def update_expense_amount(expense_id: int, user_id: int, new_amount: float):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE expenses
        SET amount = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            new_amount,
            expense_id,
            user_id,
        )
    )

    conn.commit()
    conn.close()

def update_expense_category(expense_id: int, user_id: int, new_category: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE expenses
        SET category = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            new_category,
            expense_id,
            user_id,
        )
    )

    conn.commit()
    conn.close()