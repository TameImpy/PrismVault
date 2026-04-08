"""
Tests for config module — verifies environment-based configuration behaves correctly.
"""
import importlib
import os
import sys


def _reload_config(env_overrides=None):
    """Reload config module with specific env vars set.

    Patches load_dotenv to prevent .env file from overriding our test env vars.
    """
    from unittest.mock import patch

    # Ensure JWT_SECRET is set by default so non-JWT tests don't explode
    defaults = {"JWT_SECRET": "test-secret"}
    if env_overrides:
        defaults.update(env_overrides)
    env_overrides = defaults

    # Save originals and apply overrides
    saved = {}
    for k, v in env_overrides.items():
        saved[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    # Save and remove the original config module
    original_config = sys.modules.get("config")
    if "config" in sys.modules:
        del sys.modules["config"]
    try:
        with patch("dotenv.load_dotenv"):
            import config
            return config
    finally:
        # Restore env vars
        for k, original in saved.items():
            if original is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = original
        # Restore the original config module so other tests aren't affected
        if original_config is not None:
            sys.modules["config"] = original_config
        elif "config" in sys.modules:
            del sys.modules["config"]


def test_database_url_from_env():
    """DATABASE_URL should be normalised to include the async driver."""
    cfg = _reload_config({"DATABASE_URL": "postgresql://localhost/test"})
    assert cfg.DATABASE_URL == "postgresql+asyncpg://localhost/test"


def test_database_url_postgres_prefix():
    """postgres:// (Railway format) should be normalised to postgresql+asyncpg://."""
    cfg = _reload_config({"DATABASE_URL": "postgres://user:pass@host/db"})
    assert cfg.DATABASE_URL == "postgresql+asyncpg://user:pass@host/db"


def test_database_url_defaults_to_sqlite():
    """DATABASE_URL should default to sqlite+aiosqlite:///users.db for local dev."""
    cfg = _reload_config({"DATABASE_URL": None})
    assert cfg.DATABASE_URL == "sqlite+aiosqlite:///users.db"


def test_jwt_secret_raises_if_not_set():
    """JWT_SECRET must be set in environment — no silent default."""
    import pytest
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _reload_config({"JWT_SECRET": None})


def test_jwt_secret_from_env():
    """JWT_SECRET should be read from environment when set."""
    cfg = _reload_config({"JWT_SECRET": "my-test-secret"})
    assert cfg.JWT_SECRET == "my-test-secret"


def test_chroma_cloud_vars_default_to_empty():
    """Chroma Cloud vars should default to empty string (cloud mode off)."""
    cfg = _reload_config({
        "CHROMA_CLOUD_API_KEY": None,
        "CHROMA_CLOUD_TENANT": None,
        "CHROMA_CLOUD_DATABASE": None,
    })
    assert cfg.CHROMA_CLOUD_API_KEY == ""
    assert cfg.CHROMA_CLOUD_TENANT == ""
    assert cfg.CHROMA_CLOUD_DATABASE == ""


def test_chroma_cloud_vars_from_env():
    """Chroma Cloud vars should be read from environment when set."""
    cfg = _reload_config({
        "CHROMA_CLOUD_API_KEY": "ck-abc123",
        "CHROMA_CLOUD_TENANT": "my-tenant",
        "CHROMA_CLOUD_DATABASE": "my-db",
    })
    assert cfg.CHROMA_CLOUD_API_KEY == "ck-abc123"
    assert cfg.CHROMA_CLOUD_TENANT == "my-tenant"
    assert cfg.CHROMA_CLOUD_DATABASE == "my-db"
