from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event, text
import sqlite3, os

DATABASE_URL = "sqlite+aiosqlite:///./zombieguard.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")   # 64MB cache
        cursor.close()

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

async def get_db():
    """FastAPI dependency — yields async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Run schema.sql at startup. Also creates the bind for tables if needed."""
    from database.models import Base
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    # Let SQLAlchemy create the tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Also run the raw schema file just to be sure if there are any specific PRAGMAs or triggers
    # that SQLAlchemy declarative metadata might have missed. If the tables exist it uses IF NOT EXISTS
    async with engine.begin() as conn:
        if os.path.exists(schema_path):
            with open(schema_path) as f:
                sql = f.read()
            for statement in sql.split(";"):
                s = statement.strip()
                if s:
                    await conn.execute(text(s))
