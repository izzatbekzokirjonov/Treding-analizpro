import aiosqlite
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "trading_bot.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Default settings
        defaults = [
            ("channel_id", ""),
            ("channel_username", ""),
            ("channel_required", "0"),
            ("channel_auto_post", "0"),
            ("ton_wallet", ""),
            ("visa_card", ""),
            ("visa_owner", ""),
            ("premium_price_uzs", "50000"),
            ("premium_price_stars", "299"),
            ("premium_price_ton", "5"),
        ]
        for key, value in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                language TEXT DEFAULT 'uz',
                is_premium INTEGER DEFAULT 0,
                premium_until TEXT,
                analysis_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount TEXT,
                payment_type TEXT,
                status TEXT DEFAULT 'pending',
                screenshot_file_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                approved_at TEXT,
                approved_by INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrate: add referral columns if not present
        for col_sql in [
            "ALTER TABLE users ADD COLUMN referral_code TEXT",
            "ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN bonus_analyses INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN referred_by INTEGER",
        ]:
            try:
                await db.execute(col_sql)
            except Exception:
                pass
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()


async def create_or_update_user(user_id: int, username: str, full_name: str) -> bool:
    """Returns True if a new user was created, False if existing user was updated."""
    existing = await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        if not existing:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                (user_id, username, full_name)
            )
            await db.commit()
            return True
        else:
            await db.execute(
                "UPDATE users SET username=?, full_name=? WHERE user_id=?",
                (username, full_name, user_id)
            )
            await db.commit()
            return False


async def get_user_language(user_id: int) -> str:
    user = await get_user(user_id)
    if user:
        return user["language"]
    return "uz"


async def set_user_language(user_id: int, language: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET language=? WHERE user_id=?",
            (language, user_id)
        )
        await db.commit()


async def is_premium(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or not user["is_premium"]:
        return False
    if user["premium_until"]:
        until = datetime.fromisoformat(user["premium_until"])
        if datetime.now() > until:
            # Expired — remove premium
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET is_premium=0, premium_until=NULL WHERE user_id=?",
                    (user_id,)
                )
                await db.commit()
            return False
    return True


async def get_analysis_count(user_id: int) -> int:
    user = await get_user(user_id)
    return user["analysis_count"] if user else 0


async def increment_analysis_count(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET analysis_count = analysis_count + 1 WHERE user_id=?",
            (user_id,)
        )
        await db.commit()


async def activate_premium(user_id: int, days: int = 30):
    from datetime import timedelta
    until = (datetime.now() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
            (until, user_id)
        )
        await db.commit()


async def save_payment(user_id: int, amount: str, payment_type: str, screenshot_file_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO payments (user_id, amount, payment_type, screenshot_file_id) VALUES (?, ?, ?, ?)",
            (user_id, amount, payment_type, screenshot_file_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_payments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT p.*, u.full_name, u.username FROM payments p JOIN users u ON p.user_id=u.user_id WHERE p.status='pending' ORDER BY p.created_at DESC"
        ) as cursor:
            return await cursor.fetchall()


async def approve_payment(payment_id: int, admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE id=?", (payment_id,)) as cursor:
            payment = await cursor.fetchone()
        if not payment:
            return False
        await db.execute(
            "UPDATE payments SET status='approved', approved_at=CURRENT_TIMESTAMP, approved_by=? WHERE id=?",
            (admin_id, payment_id)
        )
        await db.commit()
        await activate_premium(payment["user_id"])
        return payment["user_id"]


async def reject_payment(payment_id: int, admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status='rejected', approved_by=? WHERE id=?",
            (admin_id, payment_id)
        )
        await db.commit()


async def save_analysis(user_id: int, result: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO analysis_history (user_id, result) VALUES (?, ?)",
            (user_id, result[:10000])
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            return await cursor.fetchall()


async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


async def get_all_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def get_analysis_history(user_id: int, limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM analysis_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            return await cursor.fetchall()


async def get_or_create_referral_code(user_id: int) -> str:
    import secrets
    import string
    user = await get_user(user_id)
    if user and user["referral_code"]:
        return user["referral_code"]
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET referral_code=? WHERE user_id=?", (code, user_id))
        await db.commit()
    return code


async def get_user_by_referral_code(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE referral_code=?", (code,)) as cursor:
            return await cursor.fetchone()


async def apply_referral(new_user_id: int, referral_code: str):
    """Returns referrer user_id if successful, else None."""
    referrer = await get_user_by_referral_code(referral_code)
    if not referrer:
        return None
    if referrer["user_id"] == new_user_id:
        return None
    new_user = await get_user(new_user_id)
    if not new_user or new_user["referred_by"]:
        return None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET referred_by=? WHERE user_id=?",
            (referrer["user_id"], new_user_id)
        )
        await db.execute(
            "UPDATE users SET referral_count=referral_count+1, bonus_analyses=bonus_analyses+1 WHERE user_id=?",
            (referrer["user_id"],)
        )
        await db.commit()
    return referrer["user_id"]


async def get_bonus_analyses(user_id: int) -> int:
    user = await get_user(user_id)
    return (user["bonus_analyses"] or 0) if user else 0
