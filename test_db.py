import asyncio
from sqlalchemy import text
from database.connection import init_db, get_db

async def test():
    print("Initializing DB...")
    await init_db()
    print("Database initialized successfully.")
    
    print("Testing DB session...")
    async for session in get_db():
        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result.fetchall()]
        print(f"Tables in DB: {tables}")
        break
    print("DB test completed.")

if __name__ == "__main__":
    asyncio.run(test())
