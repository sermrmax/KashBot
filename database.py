import sqlite3

from datetime import datetime


DB_NAME = "expenses.db"


# =========================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ
# =========================================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Расходы
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

    # Лимиты по категориям
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS category_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            UNIQUE(user_id, category)
        )
        """
    )

    conn.commit()
    conn.close()


# =========================================================
# ДОБАВЛЕНИЕ РАСХОДА
# =========================================================

def add_expense(
    user_id: int,
    amount: float,
    category: str,
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO expenses (
            user_id,
            amount,
            category,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            amount,
            category,
            datetime.now().isoformat(),
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# РАСХОДЫ ЗА СЕГОДНЯ
# =========================================================

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
            today,
        )
    )

    expenses = cursor.fetchall()

    conn.close()

    return expenses


# =========================================================
# РАСХОДЫ ЗА ТЕКУЩИЙ МЕСЯЦ
# =========================================================

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
            current_month,
        )
    )

    expenses = cursor.fetchall()

    conn.close()

    return expenses


# =========================================================
# РАСХОДЫ ЗА ВЫБРАННЫЙ ПЕРИОД
# =========================================================

def get_expenses_by_period(
    user_id: int,
    start_date: str,
    end_date: str,
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT amount, category, created_at
        FROM expenses
        WHERE user_id = ?
        AND DATE(created_at) BETWEEN ? AND ?
        ORDER BY created_at DESC
        """,
        (
            user_id,
            start_date,
            end_date,
        )
    )

    expenses = cursor.fetchall()

    conn.close()

    return expenses


# =========================================================
# ПОСЛЕДНИЕ РАСХОДЫ
# =========================================================

def get_recent_expenses(
    user_id: int,
    limit: int = 10,
):
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
            limit,
        )
    )

    expenses = cursor.fetchall()

    conn.close()

    return expenses


# =========================================================
# УДАЛЕНИЕ РАСХОДА
# =========================================================

def delete_expense(
    expense_id: int,
    user_id: int,
):
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
            user_id,
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# ИЗМЕНЕНИЕ СУММЫ
# =========================================================

def update_expense_amount(
    expense_id: int,
    user_id: int,
    new_amount: float,
):
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


# =========================================================
# ИЗМЕНЕНИЕ КАТЕГОРИИ
# =========================================================

def update_expense_category(
    expense_id: int,
    user_id: int,
    new_category: str,
):
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


# =========================================================
# УСТАНОВИТЬ / ИЗМЕНИТЬ ЛИМИТ
# =========================================================

def set_category_limit(
    user_id: int,
    category: str,
    amount: float,
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO category_limits (
            user_id,
            category,
            amount
        )
        VALUES (?, ?, ?)

        ON CONFLICT(user_id, category)
        DO UPDATE SET amount = excluded.amount
        """,
        (
            user_id,
            category,
            amount,
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# ПОЛУЧИТЬ ВСЕ ЛИМИТЫ
# =========================================================

def get_category_limits(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, category, amount
        FROM category_limits
        WHERE user_id = ?
        ORDER BY category
        """,
        (
            user_id,
        )
    )

    limits = cursor.fetchall()

    conn.close()

    return limits


# =========================================================
# ПОЛУЧИТЬ ЛИМИТ КОНКРЕТНОЙ КАТЕГОРИИ
# =========================================================

def get_category_limit(
    user_id: int,
    category: str,
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT amount
        FROM category_limits
        WHERE user_id = ?
        AND category = ?
        """,
        (
            user_id,
            category,
        )
    )

    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0]

    return None


# =========================================================
# УДАЛИТЬ ЛИМИТ
# =========================================================

def delete_category_limit(
    user_id: int,
    limit_id: int,
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM category_limits
        WHERE id = ?
        AND user_id = ?
        """,
        (
            limit_id,
            user_id,
        )
    )

    conn.commit()
    conn.close()