import os
import requests
import numpy as np
import pandas as pd
import io

# 1. Generate sample CSV
def generate_sample_csv():
    rng = np.random.default_rng(42)
    n = 250
    gender = rng.choice(["male", "female"], n, p=[0.55, 0.45])
    disability = rng.choice([0, 1], n, p=[0.90, 0.10])
    age = rng.integers(22, 56, n)
    skin_colour = rng.choice(["fair", "light brown", "olive", "brown", "dark brown"], n, p=[0.15, 0.20, 0.25, 0.25, 0.15])
    institution = rng.choice(["IIT Bombay", "Delhi University", "Mumbai University", "Pune University", "NIT Trichy"], n, p=[0.15, 0.25, 0.30, 0.20, 0.10])
    marital_status = rng.choice(["Single", "Married", "Divorced"], n, p=[0.50, 0.40, 0.10])
    referral = rng.choice(["yes", "no"], n, p=[0.25, 0.75])
    caste = rng.choice(["General", "OBC", "SC", "ST"], n, p=[0.50, 0.25, 0.15, 0.10])
    shortlisted = np.where(gender == "male", rng.random(n) < 0.65, rng.random(n) < 0.42).astype(int)
    hired = np.where((shortlisted == 1) & (gender == "male"), rng.random(n) < 0.52, np.where(shortlisted == 1, rng.random(n) < 0.28, 0)).astype(int)
    
    df = pd.DataFrame({
        "gender": gender, "age": age, "institution": institution,
        "disability": disability, "shortlisted": shortlisted, "hired": hired,
        "skin_colour": skin_colour, "marital_status": marital_status,
        "referral": referral, "caste": caste,
    })
    
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf

# 2. Login to get token
API_BASE = "http://localhost:8080"
print("Logging in to get JWT token...")
login_res = requests.post(f"{API_BASE}/api/login", json={
    "email": "admin@fairhire.demo",
    "password": "admin123"
})
if not login_res.ok:
    print("Login failed:", login_res.status_code, login_res.text)
    exit(1)

token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Upload CSV to run audit
print("Uploading CSV to run audit...")
csv_buf = generate_sample_csv()
audit_res = requests.post(
    f"{API_BASE}/api/audit",
    headers=headers,
    files={"file": ("test_candidates.csv", csv_buf, "text/csv")}
)

if not audit_res.ok:
    print("Audit failed:", audit_res.status_code, audit_res.text)
    exit(1)

audit_data = audit_res.json()
print("Audit complete! Score:", audit_data.get("score"))

# 4. Prepare payload for report endpoint just like the React frontend does in Dashboard.jsx
print("Preparing report payload...")
d = audit_data
body = {
  "audit_id": d.get("id"),
  "score": d.get("score", 0),
  "label": d.get("label", "—"),
  "flags": d.get("flags", []),
  "row_count": d.get("row_count", 0),
  "original_filename": d.get("original_filename", "audit.csv"),
  "company_name": "FairHire Audit",
  "air_gender": d.get("air_gender", 0.0),
  "shortlisting_gap": d.get("shortlisting_gap", 0.0),
  "hiring_gap": d.get("hiring_gap", 0.0),
  "men_total": d.get("men_total", 0),
  "women_total": d.get("women_total", 0),
  "men_shortlisted": d.get("men_shortlisted", 0),
  "women_shortlisted": d.get("women_shortlisted", 0),
  "men_hired": d.get("men_hired", 0),
  "women_hired": d.get("women_hired", 0),
  "disability_air": d.get("disability_air", 0.0),
  "caste_stats": d.get("caste_stats", {}),
  "caste_flags": d.get("caste_flags", []),
  "caste_col": d.get("caste_col", None),
  "air_skin": d.get("air_skin", 0.0),
  "skin_best_rate": d.get("skin_best_rate", 0.0),
  "skin_worst_rate": d.get("skin_worst_rate", 0.0),
  "skin_stats": d.get("skin_stats", {}),
  "skin_flags": d.get("skin_flags", []),
  "referral_hire_rate": d.get("referral_hire_rate", 0.0),
  "non_referral_hire_rate": d.get("non_referral_hire_rate", 0.0),
  "referral_air": d.get("referral_air", 0.0),
  "referral_hhi": d.get("referral_hhi", 0.0),
  "referral_flags": d.get("referral_flags", []),
  "marital_stats": d.get("marital_stats", {}),
  "marital_flags": d.get("marital_flags", []),
  "marital_intersectional_stats": d.get("marital_intersectional_stats", {}),
  "age_flags": d.get("age_flags", []),
  "institution_flags": d.get("institution_flags", []),
  "proxy_flags": d.get("proxy_flags", []),
  "proxy_phi_scores": d.get("proxy_phi_scores", {}),
  "gender_stats": d.get("gender_stats", {}),
  "age_stats": d.get("age_stats", {}),
  "institution_stats": d.get("institution_stats", {}),
  "referral_stats": d.get("referral_stats", {}),
  "proxy_stats": d.get("proxy_stats", {}),
}

# 5. Call report endpoint
print("Calling report endpoint...")
report_res = requests.post(
    f"{API_BASE}/api/report",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=body
)

if report_res.ok:
    print("SUCCESS: Report generated! PDF size:", len(report_res.content))
else:
    print("FAILURE: Report endpoint failed with status:", report_res.status_code)
    print("Response detail:", report_res.text)
