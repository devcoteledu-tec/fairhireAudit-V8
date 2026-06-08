import os
import traceback
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from report_generator import generate_premium_report

load_dotenv()

db_url = os.getenv("DATABASE_URL")
print("Connecting to DB...")
conn = psycopg2.connect(db_url)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Let's get the latest audit
cur.execute("SELECT * FROM audits ORDER BY computed_at DESC LIMIT 1")
row = cur.fetchone()
conn.close()

if not row:
    print("No audits found in database to test PDF generation.")
    exit(0)

print(f"Testing PDF generation for Audit ID: {row['id']}...")
data = dict(row)

# Deserialise JSONB fields just like api.py normalises them
import json
jsonb_fields = (
    "flags", "institution_flags", "age_flags", "caste_flags",
    "skin_flags", "referral_flags", "marital_flags", "proxy_flags",
    "skin_stats", "referral_stats", "marital_stats",
    "marital_intersectional_stats", "proxy_stats",
    "proxy_phi_scores", "caste_stats", "institution_stats",
    "age_stats", "module_results", "gender_stats"
)
for f in jsonb_fields:
    val = data.get(f)
    if isinstance(val, str):
        try:
            data[f] = json.loads(val)
        except Exception:
            pass
    elif val is None:
        if f in ("flags", "institution_flags", "age_flags", "caste_flags",
                  "skin_flags", "referral_flags", "marital_flags", "proxy_flags"):
            data[f] = []
        else:
            data[f] = {}

data["original_filename"] = "candidates.csv"
data["company_name"] = "Test Company"

try:
    pdf_buf = generate_premium_report(data)
    print("SUCCESS: PDF generated successfully!")
    print(f"PDF size: {len(pdf_buf.getvalue())} bytes")
except Exception as e:
    print("FAILURE: PDF generation failed!")
    traceback.print_exc()
