"""SQLite database engine, session management, and table initialization."""

import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure SQLite file is persistently located in backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "changeradar.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce SQLite foreign key constraints, WAL mode, and busy timeout on every database connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides an active SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables if they do not exist, and ensure schema migrations are applied."""
    # Import models here to register them with Base before table creation
    from .models import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Lightweight migration: ensure render_js and user_id columns exist
    try:
        with engine.connect() as conn:
            cursor = conn.connection.cursor()
            
            # websites table migrations
            cursor.execute("PRAGMA table_info(websites)")
            columns = [row[1] for row in cursor.fetchall()]
            if "render_js" not in columns:
                cursor.execute("ALTER TABLE websites ADD COLUMN render_js BOOLEAN DEFAULT 0 NOT NULL")
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE websites ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
            
            # deadlines table migrations
            cursor.execute("PRAGMA table_info(deadlines)")
            columns = [row[1] for row in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE deadlines ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
            if "reminded_48h" not in columns:
                cursor.execute("ALTER TABLE deadlines ADD COLUMN reminded_48h BOOLEAN DEFAULT 0 NOT NULL")
            if "reminded_24h" not in columns:
                cursor.execute("ALTER TABLE deadlines ADD COLUMN reminded_24h BOOLEAN DEFAULT 0 NOT NULL")
            if "reminded_12h" not in columns:
                cursor.execute("ALTER TABLE deadlines ADD COLUMN reminded_12h BOOLEAN DEFAULT 0 NOT NULL")

            # notifications table migrations
            cursor.execute("PRAGMA table_info(notifications)")
            columns = [row[1] for row in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE notifications ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")

            conn.connection.commit()
            cursor.close()
    except Exception:
        pass
