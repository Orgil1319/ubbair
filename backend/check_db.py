import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://user:password@localhost:5432/realestate")
    rows = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    for row in rows:
        print(row['table_name'])
        
    # Also get some counts
    if any(r['table_name'] == 'properties' for r in rows):
        count = await conn.fetchval("SELECT count(*) FROM properties")
        print("Properties count:", count)
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
