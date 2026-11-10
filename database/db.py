import aiosqlite
from datetime import datetime
from typing import Optional
from config import DB_PATH

async def init_db():
    """Barcha moliyaviy jadvallarni yaratish va dastlabki sozlash"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # Foydalanuvchilar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Moliya (xarajat va daromadlar) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL, -- 'expense' yoki 'income'
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                payment_method TEXT DEFAULT 'Naqd', -- '💵 Naqd' yoki '💳 Karta'
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Qarzlar jadvali (Berdilar-Oldilar)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                person_name TEXT NOT NULL,
                debt_type TEXT NOT NULL, -- 'given' (haqqim bor), 'taken' (qarzdorman)
                amount REAL NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active', -- 'active', 'paid'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Oylik byudjet va limitlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT NOT NULL, -- 'Umumiy' yoki toifa nomi
                monthly_limit REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category) ON CONFLICT REPLACE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Mavjud bazalar uchun ustun qo'shish
        try:
            await db.execute("ALTER TABLE transactions ADD COLUMN payment_method TEXT DEFAULT 'Naqd'")
        except Exception:
            pass

        await db.commit()

async def register_user(user_id: int, full_name: str, username: str = None):
    """Foydalanuvchini bazaga kiritish yoki ma'lumotlarini yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, full_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username
        """, (user_id, full_name, username))
        await db.commit()

async def add_transaction(
    user_id: int,
    trans_type: str,
    amount: float,
    category: str,
    description: str = "",
    payment_method: str = "💵 Naqd"
) -> int:
    """Xarajat yoki daromad yozuvini qo'shish"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO transactions (user_id, type, amount, category, description, payment_method)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, trans_type, amount, category, description, payment_method))
        await db.commit()
        return cursor.lastrowid

async def get_summary(user_id: int, period: str = "month") -> dict:
    """
    Belgilangan davr uchun umumiy xarajat, daromad va kategoriyalar bo'yicha tahlil.
    period: 'today', 'week', 'month', 'all'
    """
    where_clause = "user_id = ?"
    params = [user_id]

    if period == "today":
        where_clause += " AND date(created_at, 'localtime') = date('now', 'localtime')"
    elif period == "week":
        where_clause += " AND date(created_at, 'localtime') >= date('now', 'localtime', '-7 days')"
    elif period == "month":
        where_clause += " AND strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Umumiy daromad va xarajat (Naqd va Karta bo'yicha ajratilgan)
        cursor = await db.execute(f"""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expense,
                COALESCE(SUM(CASE WHEN type = 'income' AND (payment_method LIKE '%Naqd%' OR payment_method = 'Naqd') THEN amount ELSE 0 END), 0) AS income_cash,
                COALESCE(SUM(CASE WHEN type = 'income' AND (payment_method LIKE '%Karta%' OR payment_method = 'Karta') THEN amount ELSE 0 END), 0) AS income_card,
                COALESCE(SUM(CASE WHEN type = 'expense' AND (payment_method LIKE '%Naqd%' OR payment_method = 'Naqd') THEN amount ELSE 0 END), 0) AS expense_cash,
                COALESCE(SUM(CASE WHEN type = 'expense' AND (payment_method LIKE '%Karta%' OR payment_method = 'Karta') THEN amount ELSE 0 END), 0) AS expense_card
            FROM transactions
            WHERE {where_clause}
        """, params)
        totals = await cursor.fetchone()
        
        # Kategoriyalar bo'yicha xarajatlar
        cursor_cat = await db.execute(f"""
            SELECT category, SUM(amount) AS sum_amount, COUNT(*) as count
            FROM transactions
            WHERE {where_clause} AND type = 'expense'
            GROUP BY category
            ORDER BY sum_amount DESC
        """, params)
        cat_rows = await cursor_cat.fetchall()

        # Oxirgi 5 ta tranzaksiya
        cursor_recent = await db.execute(f"""
            SELECT id, type, amount, category, payment_method, description, created_at
            FROM transactions
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT 5
        """, params)
        recent_rows = await cursor_recent.fetchall()

    inc = totals["total_income"] if totals else 0
    exp = totals["total_expense"] if totals else 0
    inc_cash = totals["income_cash"] if totals else 0
    inc_card = totals["income_card"] if totals else 0
    exp_cash = totals["expense_cash"] if totals else 0
    exp_card = totals["expense_card"] if totals else 0

    return {
        "period": period,
        "income": inc,
        "expense": exp,
        "balance": inc - exp,
        "income_cash": inc_cash,
        "income_card": inc_card,
        "expense_cash": exp_cash,
        "expense_card": exp_card,
        "cash_balance": inc_cash - exp_cash,
        "card_balance": inc_card - exp_card,
        "categories": [dict(r) for r in cat_rows],
        "recent": [dict(r) for r in recent_rows]
    }

async def delete_transaction(trans_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (trans_id, user_id))
        await db.commit()
        return cursor.rowcount > 0

async def get_all_transactions(user_id: int, period: str = "all") -> list[dict]:
    """Excel hisoboti uchun barcha tranzaksiyalarni olish"""
    where_clause = "user_id = ?"
    params = [user_id]

    if period == "today":
        where_clause += " AND date(created_at, 'localtime') = date('now', 'localtime')"
    elif period == "week":
        where_clause += " AND date(created_at, 'localtime') >= date('now', 'localtime', '-7 days')"
    elif period == "month":
        where_clause += " AND strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(f"""
            SELECT id, type, amount, category, payment_method, description, datetime(created_at, 'localtime') as created_at
            FROM transactions
            WHERE {where_clause}
            ORDER BY created_at ASC
        """, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

# ==================== QARZLAR (DEBTS) FUNKSIYALARI ====================

async def add_debt(
    user_id: int,
    person_name: str,
    debt_type: str,  # 'given' (berdim) yoki 'taken' (oldim)
    amount: float,
    description: str = ""
) -> int:
    """Yangi qarz yozuvini qo'shish"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO debts (user_id, person_name, debt_type, amount, description, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (user_id, person_name, debt_type, amount, description))
        await db.commit()
        return cursor.lastrowid

async def get_active_debts(user_id: int) -> dict:
    """Foydalanuvchining barcha faol qarzlarini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT id, person_name, debt_type, amount, description, datetime(created_at, 'localtime') as created_at
            FROM debts
            WHERE user_id = ? AND status = 'active'
            ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()

    given = [dict(r) for r in rows if r["debt_type"] == "given"]
    taken = [dict(r) for r in rows if r["debt_type"] == "taken"]

    total_given = sum(r["amount"] for r in given)
    total_taken = sum(r["amount"] for r in taken)

    return {
        "given": given,
        "taken": taken,
        "total_given": total_given,
        "total_taken": total_taken
    }

async def mark_debt_paid(debt_id: int, user_id: int) -> bool:
    """Qarzni to'langan deb belgilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE debts SET status = 'paid' WHERE id = ? AND user_id = ?
        """, (debt_id, user_id))
        await db.commit()
        return cursor.rowcount > 0

async def close_debt_by_name(user_id: int, person_name: str) -> Optional[dict]:
    """Ism bo'yicha eng oxirgi faol qarzni yopish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT id, person_name, debt_type, amount FROM debts
            WHERE user_id = ? AND status = 'active' AND LOWER(person_name) LIKE LOWER(?)
            ORDER BY id DESC LIMIT 1
        """, (user_id, f"%{person_name}%"))
        row = await cursor.fetchone()
        if row:
            debt_id = row["id"]
            await db.execute("UPDATE debts SET status = 'paid' WHERE id = ?", (debt_id,))
            await db.commit()
            return dict(row)
    return None

# ==================== BYUDJET VA LIMIT FUNKSIYALARI ====================

async def set_budget(user_id: int, category: str, monthly_limit: float):
    """Toifa yoki umumiy oy uchun xarajat limitini belgilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO budgets (user_id, category, monthly_limit)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit
        """, (user_id, category, monthly_limit))
        await db.commit()

async def get_budgets(user_id: int) -> list[dict]:
    """Foydalanuvchining oylik byudjet limitlarini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT category, monthly_limit FROM budgets WHERE user_id = ?
        """, (user_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def check_budget_alerts(user_id: int, category: str, amount_added: float = 0) -> list[str]:
    """
    Yangi xarajat qo'shilganda limitdan oshganlik yoki 80% yetganlik haqida ogohlantirishlarni tekshirish.
    """
    budgets = await get_budgets(user_id)
    if not budgets:
        return []

    alerts = []
    # Shu oy bo'yicha jami xarajatlarni olish
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Ushbu kategoriya bo'yicha xarajat
        cursor_cat = await db.execute("""
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM transactions
            WHERE user_id = ? AND type = 'expense' AND category = ?
              AND strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')
        """, (user_id, category))
        cat_spent = (await cursor_cat.fetchone())["spent"]

        # 2. Umumiy oylik xarajat
        cursor_all = await db.execute("""
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM transactions
            WHERE user_id = ? AND type = 'expense'
              AND strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')
        """, (user_id,))
        total_spent = (await cursor_all.fetchone())["spent"]

    for b in budgets:
        b_cat = b["category"]
        b_limit = b["monthly_limit"]
        
        spent = cat_spent if b_cat == category else (total_spent if b_cat.lower() in ["umumiy", "jami"] else None)
        if spent is None:
            continue

        pct = (spent / b_limit) * 100 if b_limit > 0 else 0
        def fmt(n: float) -> str:
            return f"{int(n):,}".replace(",", " ")

        if spent >= b_limit:
            alerts.append(
                f"🚨 <b>DIQQAT! «{b_cat}» bo'yicha belgilangan {fmt(b_limit)} so'mlik oylik limit to'ldi!</b> (Jami sarflandi: {fmt(spent)} so'm)"
            )
        elif pct >= 80:
            rem = b_limit - spent
            alerts.append(
                f"⚠️ <b>Eslatma: «{b_cat}» bo'yicha byudjetingizning {int(pct)}% sarflandi.</b> (Oylik reja: {fmt(b_limit)} so'm | Qoldiq: {fmt(rem)} so'm)"
            )

    return alerts
