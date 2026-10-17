from sqlalchemy import create_engine

engine = create_engine("postgresql://user:password@localhost:5432/realestate")
with engine.connect() as conn:
    result = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    for row in result:
        print(row[0])
