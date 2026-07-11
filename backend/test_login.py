import os
import requests

url = "https://vyapar-pulse-backend.vercel.app/api/auth/login"
res = requests.post(url, json={"email": "credit@bank.example", "password": "VyaparPulseDemo2026!"})
print(res.status_code)
print(res.text)
