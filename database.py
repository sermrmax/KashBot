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