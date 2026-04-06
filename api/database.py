"""
User database module. Async SQLite wrapper for user storage.
"""
import aiosqlite

# Default database path, overridden in tests.
DEFAULT_DB_PATH = "users.db"


async def init_db(db_path=DEFAULT_DB_PATH):
    """Create the users and email_samples tables if they do not exist."""
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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS email_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
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


# ---------------------------------------------------------------------------
# Email samples
# ---------------------------------------------------------------------------

MAX_EMAIL_SAMPLES = 5


async def create_email_sample(user_id, content, db_path=DEFAULT_DB_PATH):
    """Insert a new email sample. Raises ValueError if user already has MAX_EMAIL_SAMPLES."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        # Check limit
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM email_samples WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            if row["cnt"] >= MAX_EMAIL_SAMPLES:
                raise ValueError("Maximum of %d email samples reached." % MAX_EMAIL_SAMPLES)
        cursor = await db.execute(
            "INSERT INTO email_samples (user_id, content) VALUES (?, ?)",
            (user_id, content),
        )
        await db.commit()
        sample_id = cursor.lastrowid
        async with db.execute(
            "SELECT id, user_id, content, created_at FROM email_samples WHERE id = ?",
            (sample_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row)


async def get_email_samples(user_id, db_path=DEFAULT_DB_PATH):
    """Return all email samples for a user, ordered by creation date."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, content, created_at FROM email_samples WHERE user_id = ? ORDER BY created_at",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def delete_email_sample(sample_id, user_id, db_path=DEFAULT_DB_PATH):
    """Delete an email sample by ID, but only if it belongs to the given user.
    Returns True if deleted, False if not found or not owned."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "DELETE FROM email_samples WHERE id = ? AND user_id = ?",
            (sample_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_user_password(user_id, hashed_password, db_path=DEFAULT_DB_PATH):
    """Update the password hash for a user."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE users SET hashed_password = ? WHERE id = ?",
            (hashed_password, user_id),
        )
        await db.commit()
