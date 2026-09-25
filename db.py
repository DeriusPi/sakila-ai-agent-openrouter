import os

import mysql.connector
from dotenv import load_dotenv


# Load .env from the project folder, whatever the current working dir.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def _setting(name, default=None):
    """
    Read a setting from environment variables first, then from
    Streamlit secrets (Streamlit Community Cloud), then the default.
    """

    value = os.getenv(name)

    if value not in (None, ""):
        return value

    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])

        # Also support a [mysql] / [database] section in secrets.toml
        for section in ("mysql", "database", "db"):
            if section in st.secrets:
                key = name.lower().replace("db_", "")
                block = st.secrets[section]
                if key in block:
                    return str(block[key])
                if name.lower() in block:
                    return str(block[name.lower()])
    except Exception:
        pass

    return default


def get_connection():
    """
    Create and return a MySQL connection to the Sakila database.

    Settings (env var or Streamlit secret):
        DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
        DB_SSL_DISABLED=true   (optional, some hosted MySQL need SSL)
    """

    params = {
        "host": _setting("DB_HOST", "localhost"),
        "port": int(_setting("DB_PORT", 3306)),
        "user": _setting("DB_USER", "root"),
        "password": _setting("DB_PASSWORD", ""),
        "database": _setting("DB_NAME", "sakila"),
        "connection_timeout": int(_setting("DB_TIMEOUT", 15)),
        "charset": "utf8mb4",
        "use_unicode": True,
    }

    ssl_disabled = str(_setting("DB_SSL_DISABLED", "")).lower()

    if ssl_disabled in {"1", "true", "yes"}:
        params["ssl_disabled"] = True

    return mysql.connector.connect(**params)
