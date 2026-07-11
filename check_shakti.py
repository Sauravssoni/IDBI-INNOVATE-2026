import requests

API_URL = "https://vyapar-pulse-backend.vercel.app"

session = requests.Session()
login_res = session.post(f"{API_URL}/api/auth/demo/session", json={"role": "CREDIT_ANALYST"})
if not login_res.ok:
    print(f"Login failed: {login_res.text}")
    exit(1)

csrf_token = login_res.cookies.get("vyapar_csrf_token")
if csrf_token:
    session.headers.update({"X-CSRF-Token": csrf_token})

cases_res = session.get(f"{API_URL}/api/cases/")
if not cases_res.ok:
    print(f"Cases failed: {cases_res.text}")
    exit(1)

cases = cases_res.json()
shakti = next((c for c in cases if c.get("business_id") == "SHAKTI_PRECISION_001"), None)
import json
print(json.dumps(shakti, indent=2))
