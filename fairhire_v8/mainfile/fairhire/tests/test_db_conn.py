import psycopg2

PROJECT_REFS = ["bvnzbxgdqrllzehvhzlc", "xhmisvxohwofpzxkizpi"]
PASSWORD = "Fairness#2026@"

print("Starting direct connection tests...")

for ref in PROJECT_REFS:
    host = f"db.{ref}.supabase.co"
    user = "postgres"
    port = 5432
    dbname = "postgres"
    
    print(f"\nTesting direct connection for ref={ref}...", flush=True)
    try:
        conn = psycopg2.connect(
            host=host,
            database=dbname,
            user=user,
            password=PASSWORD,
            port=port,
            sslmode="require",
            connect_timeout=5
        )
        print(f">>> SUCCESS! Working direct connection found:")
        print(f"Host: {host}")
        conn.close()
        exit(0)
    except Exception as e:
        err_msg = str(e).strip()
        print(f"  Failed: {err_msg}", flush=True)

print("\nCould not find any working direct connection.")
