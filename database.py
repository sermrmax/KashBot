import sqlite3
from datetime import datetime


# =========================================================
# 1. НАСТРОЙКИ БАЗЫ ДАННЫХ
# =========================================================

# SQLite хранит всю базу в одном локальном файле.
DB_NAME = "expenses.db"


# =========================================================
# 2. ИНИЦИАЛИЗАЦИЯ БАЗЫ
# =========================================================

def init_db():
    """
    Создаёт необходимые таблицы, если их ещё нет.

    Эта функция вызывается при запуске бота.
    Уже существующие таблицы и данные не удаляются.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # -----------------------------------------------------
    # Обычные расходы
    # -----------------------------------------------------
    #
    # Здесь хранятся все разовые расходы пользователя.
    #
    # Пример:
    # 500 ₽ / Еда / 2026-09-07
    #

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

    # -----------------------------------------------------
    # Лимиты по категориям
    # -----------------------------------------------------
    #
    # Хранит месячный лимит для каждой категории.
    #
    # Например:
    # Еда -> 20000 ₽
    # Транспорт -> 10000 ₽
    #
    # UNIQUE(user_id, category) не позволяет создать
    # два разных лимита для одной категории пользователя.
    #

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

    # -----------------------------------------------------
    # Регулярные расходы
    # -----------------------------------------------------
    #
    # Здесь находятся постоянные ежемесячные платежи.
    #
    # Например:
    # Интернет / 900 ₽ / Покупки / 10 число
    #
    # is_active оставлен на будущее:
    # 1 = активен
    # 0 = отключён
    #

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS recurring_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            day_of_month INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )

    # -----------------------------------------------------
    # Общий месячный бюджет
    # -----------------------------------------------------
    #
    # Для каждого пользователя хранится один текущий
    # месячный бюджет.
    #
    # Например:
    # user_id = 123
    # amount = 100000
    #
    # UNIQUE(user_id) означает:
    # один пользователь -> один бюджет.
    #

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            amount REAL NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# =========================================================
# 3. ОБЫЧНЫЕ РАСХОДЫ
# =========================================================


def add_expense(
    user_id: int,
    amount: float,
    category: str,
) -> int:
    """
    Добавляет новый обычный расход.

    Возвращает ID созданной записи.

    Этот ID нужен, например, для кнопки:
    ↩️ Отменить
    """

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

    # SQLite автоматически присваивает новый ID.
    expense_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return expense_id


def get_expenses_by_period(
    user_id: int,
    start_date: str,
    end_date: str,
):
    """
    Возвращает расходы пользователя
    за выбранный период.

    start_date и end_date передаются в формате:

    YYYY-MM-DD

    Например:
    2026-09-01
    2026-09-07
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            amount,
            category,
            created_at
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


def get_recent_expenses(
    user_id: int,
    limit: int = 10,
):
    """
    Возвращает последние расходы пользователя.

    По умолчанию возвращается 10 записей.

    Используется для:
    - удаления расхода
    - редактирования расхода
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            amount,
            category,
            created_at
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


def delete_expense(
    expense_id: int,
    user_id: int,
):
    """
    Удаляет конкретный расход.

    Проверяется не только ID расхода,
    но и user_id.

    Благодаря этому пользователь
    не сможет удалить чужую запись.
    """

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


def update_expense_amount(
    expense_id: int,
    user_id: int,
    new_amount: float,
):
    """
    Изменяет сумму обычного расхода.
    """

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


def update_expense_category(
    expense_id: int,
    user_id: int,
    new_category: str,
):
    """
    Изменяет категорию обычного расхода.
    """

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
# 4. ЛИМИТЫ ПО КАТЕГОРИЯМ
# =========================================================


def set_category_limit(
    user_id: int,
    category: str,
    amount: float,
):
    """
    Создаёт или обновляет лимит категории.

    Если лимита для такой категории ещё нет:
    -> создаётся новая запись.

    Если уже есть:
    -> сумма обновляется.
    """

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
        DO UPDATE SET
            amount = excluded.amount
        """,
        (
            user_id,
            category,
            amount,
        )
    )

    conn.commit()
    conn.close()


def get_category_limits(
    user_id: int,
):
    """
    Возвращает все лимиты пользователя.

    Сортировка идёт по названию категории.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            category,
            amount
        FROM category_limits
        WHERE user_id = ?
        ORDER BY category
        """,
        (user_id,)
    )

    limits = cursor.fetchall()

    conn.close()

    return limits


def get_category_limit(
    user_id: int,
    category: str,
) -> float | None:
    """
    Возвращает лимит конкретной категории.

    Если лимит существует:
    -> возвращает сумму.

    Если лимита нет:
    -> возвращает None.
    """

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


def delete_category_limit(
    user_id: int,
    limit_id: int,
):
    """
    Удаляет конкретный лимит пользователя.
    """

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


# =========================================================
# 5. РЕГУЛЯРНЫЕ РАСХОДЫ
# =========================================================


def add_recurring_expense(
    user_id: int,
    name: str,
    amount: float,
    category: str,
    day_of_month: int,
):
    """
    Добавляет новый регулярный расход.

    Например:
    Интернет
    900 ₽
    Покупки
    10 числа
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO recurring_expenses (
            user_id,
            name,
            amount,
            category,
            day_of_month
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            name,
            amount,
            category,
            day_of_month,
        )
    )

    conn.commit()
    conn.close()


def get_recurring_expenses(
    user_id: int,
):
    """
    Возвращает все активные
    регулярные расходы пользователя.

    Сначала сортируем по дню оплаты,
    затем по названию.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            amount,
            category,
            day_of_month
        FROM recurring_expenses
        WHERE user_id = ?
        AND is_active = 1
        ORDER BY day_of_month, name
        """,
        (user_id,)
    )

    expenses = cursor.fetchall()

    conn.close()

    return expenses


def get_recurring_expense(
    recurring_id: int,
    user_id: int,
):
    """
    Возвращает один конкретный
    регулярный расход.

    Используется при:
    - редактировании
    - отметке как оплаченного
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            amount,
            category,
            day_of_month
        FROM recurring_expenses
        WHERE id = ?
        AND user_id = ?
        AND is_active = 1
        """,
        (
            recurring_id,
            user_id,
        )
    )

    expense = cursor.fetchone()

    conn.close()

    return expense


def delete_recurring_expense(
    recurring_id: int,
    user_id: int,
):
    """
    Полностью удаляет регулярный расход.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM recurring_expenses
        WHERE id = ?
        AND user_id = ?
        """,
        (
            recurring_id,
            user_id,
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# 6. РЕДАКТИРОВАНИЕ РЕГУЛЯРНЫХ РАСХОДОВ
# =========================================================


def update_recurring_name(
    recurring_id: int,
    user_id: int,
    new_name: str,
):
    """
    Изменяет название регулярного расхода.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE recurring_expenses
        SET name = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            new_name,
            recurring_id,
            user_id,
        )
    )

    conn.commit()
    conn.close()


def update_recurring_amount(
    recurring_id: int,
    user_id: int,
    new_amount: float,
):
    """
    Изменяет сумму регулярного расхода.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE recurring_expenses
        SET amount = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            new_amount,
            recurring_id,
            user_id,
        )
    )

    conn.commit()
    conn.close()


def update_recurring_category(
    recurring_id: int,
    user_id: int,
    new_category: str,
):
    """
    Изменяет категорию регулярного расхода.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE recurring_expenses
        SET category = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            new_category,
            recurring_id,
            user_id,
        )
    )

    conn.commit()
    conn.close()


def update_recurring_day(
    recurring_id: int,
    user_id: int,
    new_day: int,
):
    """
    Изменяет день ежемесячной оплаты.

    Например:
    было 10 число
    стало 15 число.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE recurring_expenses
        SET day_of_month = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            new_day,
            recurring_id,
            user_id,
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# 7. ОБЩИЙ МЕСЯЧНЫЙ БЮДЖЕТ
# =========================================================


def set_monthly_budget(
    user_id: int,
    amount: float,
):
    """
    Создаёт или изменяет общий месячный бюджет.

    У пользователя может быть
    только один текущий бюджет.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO monthly_budget (
            user_id,
            amount
        )
        VALUES (?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            amount = excluded.amount
        """,
        (
            user_id,
            amount,
        )
    )

    conn.commit()
    conn.close()


def get_monthly_budget(
    user_id: int,
) -> float | None:
    """
    Возвращает текущий месячный бюджет.

    Если бюджет установлен:
    -> возвращает сумму.

    Если нет:
    -> возвращает None.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT amount
        FROM monthly_budget
        WHERE user_id = ?
        """,
        (user_id,)
    )

    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0]

    return None


def delete_monthly_budget(
    user_id: int,
):
    """
    Удаляет установленный месячный бюджет.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM monthly_budget
        WHERE user_id = ?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()