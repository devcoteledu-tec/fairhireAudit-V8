import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=== AUDITS TABLE ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'audits'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:40s} {r[1]}")

print("\n=== UPLOADS TABLE ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'uploads'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:40s} {r[1]}")

conn.close()
