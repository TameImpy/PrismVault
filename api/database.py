"""
Database module. Uses the `databases` library for async access to SQLite (dev/test)
or Postgres (production) via a shared connection pool.
"""
from databases import Database

import config

# Shared database instance — created lazily in connect() to avoid
# binding the asyncpg pool to the wrong event loop at import time.
database = None

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def connect():
    """Create the database instance and connect the pool. Call on app startup."""
    global database
    # Always create a fresh instance to avoid event loop mismatches
    database = Database(config.DATABASE_URL)
    await database.connect()


async def disconnect():
    """Disconnect the database pool. Call on app shutdown."""
    global database
    if database:
        try:
            await database.disconnect()
        except Exception:
            pass
        database = None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_is_postgres = config.DATABASE_URL.startswith("postgresql")

# Postgres uses SERIAL for auto-increment; SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT.
_PK = "SERIAL PRIMARY KEY" if _is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id %s,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""" % _PK

CREATE_EMAIL_SAMPLES = """
CREATE TABLE IF NOT EXISTS email_samples (
    id %s,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""" % _PK

CREATE_SCORES = """
CREATE TABLE IF NOT EXISTS scores (
    id %s,
    player_name TEXT NOT NULL,
    score INTEGER NOT NULL,
    lines INTEGER NOT NULL,
    level INTEGER NOT NULL,
    user_id TEXT,
    created_at TEXT NOT NULL
)
""" % _PK

CREATE_BRIEFS = """
CREATE TABLE IF NOT EXISTS briefs (
    id %s,
    user_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    advertiser TEXT NOT NULL,
    kpi TEXT NOT NULL,
    client_brief TEXT NOT NULL DEFAULT '',
    result_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""" % _PK


async def init_db():
    """Create all tables if they do not exist."""
    await database.execute(CREATE_USERS)
    await database.execute(CREATE_EMAIL_SAMPLES)
    await database.execute(CREATE_SCORES)
    await database.execute(CREATE_BRIEFS)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def _row_to_dict(row):
    """Convert a databases Record to a plain dict."""
    if row is None:
        return None
    return dict(row._mapping)


async def _insert_returning_id(query, values):
    """Execute an INSERT and return the new row's id.

    Postgres requires RETURNING id to get the auto-generated key.
    SQLite's execute() returns lastrowid automatically.
    """
    if _is_postgres:
        row = await database.fetch_one(query + " RETURNING id", values)
        return row._mapping["id"]
    return await database.execute(query, values)


async def create_user(email, name, hashed_password):
    """Insert a new user and return the created user dict."""
    query = "INSERT INTO users (email, name, hashed_password) VALUES (:email, :name, :hashed_password)"
    user_id = await _insert_returning_id(query, {"email": email, "name": name, "hashed_password": hashed_password})
    row = await database.fetch_one("SELECT id, email, name, created_at FROM users WHERE id = :id", {"id": user_id})
    return _row_to_dict(row)


async def get_user_by_email(email):
    """Return user dict by email, or None if not found."""
    row = await database.fetch_one(
        "SELECT id, email, name, hashed_password, created_at FROM users WHERE email = :email",
        {"email": email},
    )
    return _row_to_dict(row)


async def get_user_by_id(user_id):
    """Return user dict by ID, or None if not found."""
    row = await database.fetch_one(
        "SELECT id, email, name, hashed_password, created_at FROM users WHERE id = :id",
        {"id": user_id},
    )
    return _row_to_dict(row)


async def update_user_password(user_id, hashed_password):
    """Update the password hash for a user."""
    await database.execute(
        "UPDATE users SET hashed_password = :pw WHERE id = :id",
        {"pw": hashed_password, "id": user_id},
    )


# ---------------------------------------------------------------------------
# Email samples
# ---------------------------------------------------------------------------

MAX_EMAIL_SAMPLES = 5


async def create_email_sample(user_id, content):
    """Insert a new email sample. Raises ValueError if user already has MAX_EMAIL_SAMPLES."""
    row = await database.fetch_one(
        "SELECT COUNT(*) as cnt FROM email_samples WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    if row._mapping["cnt"] >= MAX_EMAIL_SAMPLES:
        raise ValueError("Maximum of %d email samples reached." % MAX_EMAIL_SAMPLES)
    sample_id = await _insert_returning_id(
        "INSERT INTO email_samples (user_id, content) VALUES (:user_id, :content)",
        {"user_id": user_id, "content": content},
    )
    row = await database.fetch_one(
        "SELECT id, user_id, content, created_at FROM email_samples WHERE id = :id",
        {"id": sample_id},
    )
    return _row_to_dict(row)


async def get_email_samples(user_id):
    """Return all email samples for a user, ordered by creation date."""
    rows = await database.fetch_all(
        "SELECT id, user_id, content, created_at FROM email_samples WHERE user_id = :user_id ORDER BY created_at",
        {"user_id": user_id},
    )
    return [_row_to_dict(r) for r in rows]


async def delete_email_sample(sample_id, user_id):
    """Delete an email sample by ID, but only if it belongs to the given user.
    Returns True if deleted, False if not found or not owned."""
    # databases library doesn't return rowcount from execute on DELETE,
    # so check existence first.
    row = await database.fetch_one(
        "SELECT id FROM email_samples WHERE id = :id AND user_id = :user_id",
        {"id": sample_id, "user_id": user_id},
    )
    if row is None:
        return False
    await database.execute(
        "DELETE FROM email_samples WHERE id = :id AND user_id = :user_id",
        {"id": sample_id, "user_id": user_id},
    )
    return True


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


async def submit_score(player_name, score, lines, level, user_id, created_at):
    """Insert a leaderboard score and return the row dict with rank."""
    row_id = await _insert_returning_id(
        "INSERT INTO scores (player_name, score, lines, level, user_id, created_at) "
        "VALUES (:player_name, :score, :lines, :level, :user_id, :created_at)",
        {
            "player_name": player_name,
            "score": score,
            "lines": lines,
            "level": level,
            "user_id": user_id,
            "created_at": created_at,
        },
    )
    rank_row = await database.fetch_one(
        "SELECT COUNT(*) as cnt FROM scores WHERE score > (SELECT score FROM scores WHERE id = :id)",
        {"id": row_id},
    )
    rank = rank_row._mapping["cnt"] + 1
    return {
        "id": row_id,
        "rank": rank,
        "player_name": player_name,
        "score": score,
        "lines": lines,
        "level": level,
        "created_at": created_at,
    }


async def get_leaderboard(player_name=None):
    """Return top 10 scores with dense ranking, total players, and optional player rank."""
    rows = await database.fetch_all(
        "SELECT player_name, score, lines, level, created_at FROM scores ORDER BY score DESC LIMIT 10"
    )

    top_10 = []
    prev_score = None
    rank = 0
    for i, row in enumerate(rows):
        r = row._mapping
        if r["score"] != prev_score:
            rank = i + 1
            prev_score = r["score"]
        top_10.append({
            "rank": rank,
            "player_name": r["player_name"],
            "score": r["score"],
            "lines": r["lines"],
            "level": r["level"],
            "created_at": r["created_at"],
        })

    total_row = await database.fetch_one("SELECT COUNT(*) as cnt FROM scores")
    total_players = total_row._mapping["cnt"]

    player_rank = None
    if player_name:
        best = await database.fetch_one(
            "SELECT MAX(score) as best_score FROM scores WHERE player_name = :name",
            {"name": player_name},
        )
        if best and best._mapping["best_score"] is not None:
            rank_row = await database.fetch_one(
                "SELECT COUNT(DISTINCT score) + 1 as rank FROM scores WHERE score > :score",
                {"score": best._mapping["best_score"]},
            )
            player_rank = rank_row._mapping["rank"]

    return {
        "top_10": top_10,
        "player_rank": player_rank,
        "total_players": total_players,
    }


# ---------------------------------------------------------------------------
# Briefs
# ---------------------------------------------------------------------------


async def save_brief(user_id, topic, advertiser, kpi, client_brief, result_json):
    """Insert a new brief and return the saved row dict."""
    brief_id = await _insert_returning_id(
        "INSERT INTO briefs (user_id, topic, advertiser, kpi, client_brief, result_json) "
        "VALUES (:user_id, :topic, :advertiser, :kpi, :client_brief, :result_json)",
        {
            "user_id": user_id,
            "topic": topic,
            "advertiser": advertiser,
            "kpi": kpi,
            "client_brief": client_brief,
            "result_json": result_json,
        },
    )
    row = await database.fetch_one(
        "SELECT id, user_id, topic, advertiser, kpi, client_brief, created_at "
        "FROM briefs WHERE id = :id",
        {"id": brief_id},
    )
    return _row_to_dict(row)
