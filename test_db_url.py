from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

async def test_engine():
    try:
        engine = create_async_engine("dummy-db-url")
        print("Engine created successfully (unexpected)")
    except Exception as e:
        print(f"Caught expected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_engine())
