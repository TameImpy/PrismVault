"""
User database module. Async SQLite wrapper for user storage.
"""
import aiosqlite

# Default database path, overridden in tests.
DEFAULT_DB_PATH = "users.db"


async def init_db(db_path=DEFAULT_DB_PATH):
    """Create the users table if it does not exist."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def create_user(email, name, hashed_password, db_path=DEFAULT_DB_PATH):
    """Insert a new user and return the created user dict."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO users (email, name, hashed_password) VALUES (?, ?, ?)",
            (email, name, hashed_password),
        )
        await db.commit()
        user_id = cursor.lastrowid
        async with db.execute(
            "SELECT id, email, name, created_at FROM users WHERE id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row)


async def get_user_by_email(email, db_path=DEFAULT_DB_PATH):
    """Return user dict by email, or None if not found."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, email, name, hashed_password, created_at FROM users WHERE email = ?",
            (email,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_by_id(user_id, db_path=DEFAULT_DB_PATH):
    """Return user dict by ID, or None if not found."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, email, name, hashed_password, created_at FROM users WHERE id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
