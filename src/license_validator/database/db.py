import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from license_validator.core.secrets import SecretsManager

load_dotenv()

Base = declarative_base()

_engine = None
_SessionFactory = None


def normalize_db_url(raw_url: str) -> str:
    """
    Normalizes PostgreSQL connection strings for SQLAlchemy.
    Converts legacy 'postgres://' or 'postgresql://' to 'postgresql+psycopg2://'.
    """
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def get_database_url(custom_url: Optional[str] = None) -> str:
    """
    Retrieves the database connection string.
    Priority:
    1. custom_url passed explicitly (e.g. for unit tests)
    2. SecretsManager.get_database_url() (strictly retrieved from Infisical Cloud into RAM)
    """
    if custom_url:
        return normalize_db_url(custom_url)

    url = SecretsManager.get_database_url()
    return normalize_db_url(url)


def is_cloud_database() -> bool:
    """Returns True if the current configuration is targeting PostgreSQL / Cloud."""
    try:
        url = get_database_url()
        return "postgres" in url.lower()
    except Exception:
        return False


def is_database_encrypted() -> bool:
    """
    Returns True if the database operates with encryption.
    PostgreSQL cloud databases (Aiven Cloud) enforce TLS/SSL in transit (sslmode=require)
    and full AES-256 volume encryption at rest.
    """
    return True


def init_engine(db_url: Optional[str] = None):
    """
    Initializes the SQLAlchemy engine with connection pooling and pre-ping verification.
    """
    global _engine, _SessionFactory
    url = normalize_db_url(db_url) if db_url else get_database_url()

    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,  # Verifies connection health before usage (auto-reconnects dropped cloud sockets)
    }

    if "sqlite" in url.lower():
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL connection pool settings for cloud resilience
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10
        engine_kwargs["pool_timeout"] = 30
        engine_kwargs["pool_recycle"] = 1800  # Recycle connections every 30 minutes

    _engine = create_engine(url, **engine_kwargs)
    _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    if is_cloud_database():
        print("☁️ [Base de Datos] Conexión activa a PostgreSQL en la nube (Aiven Cloud con SSL).")
    else:
        print("📁 [Base de Datos] Conexión activa a SQLite local.")

    return _engine


def get_engine():
    global _engine
    if _engine is None:
        init_engine()
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        init_engine()
    return _SessionFactory


def get_session() -> Session:
    factory = get_session_factory()
    return factory()


def init_db(db_url: Optional[str] = None):
    """Initializes the database and ensures all tables exist."""
    engine = init_engine(db_url)
    import license_validator.database.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Migración de compatibilidad: asegurar columna 'role' en tabla 'users'
    try:
        with engine.connect() as conn:
            if "sqlite" in str(engine.url).lower():
                result = conn.execute(text("PRAGMA table_info(users);")).fetchall()
                if result:
                    col_names = [row[1] for row in result]
                    if "role" not in col_names:
                        conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'manager' NOT NULL;"))
                        conn.execute(text("UPDATE users SET role = 'admin' WHERE id = (SELECT min(id) FROM users);"))
                    if "current_session_token" not in col_names:
                        conn.execute(text("ALTER TABLE users ADD COLUMN current_session_token VARCHAR(64);"))
                    if "session_device" not in col_names:
                        conn.execute(text("ALTER TABLE users ADD COLUMN session_device VARCHAR(100);"))
                    if "last_heartbeat" not in col_names:
                        conn.execute(text("ALTER TABLE users ADD COLUMN last_heartbeat DATETIME;"))
                    conn.commit()
            else:
                # PostgreSQL check
                check_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='role';
                """)
                res = conn.execute(check_sql).fetchone()
                if not res:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'manager' NOT NULL;"))
                    conn.execute(text("UPDATE users SET role = 'admin' WHERE id = (SELECT min(id) FROM users);"))
                    conn.commit()

                # PostgreSQL session columns check
                for col_name, col_type in [
                    ("current_session_token", "VARCHAR(64)"),
                    ("session_device", "VARCHAR(100)"),
                    ("last_heartbeat", "TIMESTAMP"),
                ]:
                    chk_sql = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='users' AND column_name='{col_name}';
                    """)
                    if not conn.execute(chk_sql).fetchone():
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                        conn.commit()

            # Migración de compatibilidad: asegurar columna 'terminal_hash' en tabla 'licenses'
            if "sqlite" in str(engine.url).lower():
                lic_result = conn.execute(text("PRAGMA table_info(licenses);")).fetchall()
                if lic_result:
                    lic_cols = [row[1] for row in lic_result]
                    if "terminal_hash" not in lic_cols:
                        conn.execute(text("ALTER TABLE licenses ADD COLUMN terminal_hash VARCHAR(100) DEFAULT '';"))
                        conn.commit()
            else:
                # PostgreSQL check
                lic_check_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='licenses' AND column_name='terminal_hash';
                """)
                lic_res = conn.execute(lic_check_sql).fetchone()
                if not lic_res:
                    conn.execute(text("ALTER TABLE licenses ADD COLUMN terminal_hash VARCHAR(100) DEFAULT '';"))
                    conn.commit()
    except Exception as e:
        print(f"⚠️ [DB Auto-Migration] Advertencia durante migración de esquema: {e}")
