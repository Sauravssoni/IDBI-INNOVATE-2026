import os
import re

# Fix frontend page.tsx
page_file = 'frontend/app/decision-room/[caseId]/page.tsx'
if os.path.exists(page_file):
    with open(page_file, 'r') as f:
        content = f.read()
    
    # Remove prototype CSRF token
    content = re.sub(r'"X-CSRF-Token":\s*"prototype-csrf"', '"X-CSRF-Token": ""', content) 
    
    # Remove hardcoded Consent/KYC
    content = re.sub(r'<p className="mb-2"><strong>Consent Artefact:</strong> Verified \(Digital footprint linked\)</p>\n', '', content)
    content = re.sub(r'<p className="mb-2"><strong>KYC Status:</strong> <span className="text-emerald-400">Complete</span></p>\n', '', content)
    
    # Remove fake EVDs
    content = content.replace('"EVD-BANK-001"', '""')
    content = content.replace('"EVD-BUREAU-001"', '""')
    content = content.replace('"EVD-GST-001"', '""')
    
    with open(page_file, 'w') as f:
        f.write(content)

# Fix scorer.py
scorer_file = 'backend/app/core/scoring/scorer.py'
if os.path.exists(scorer_file):
    with open(scorer_file, 'r') as f:
        content = f.read()
    
    content = content.replace('"EVD-BANK-001"', 'self.features.get("bank_metrics", {}).get("evidence_id", "MISSING_BANK_EVD")')
    content = content.replace('"EVD-BUREAU-001"', 'self.features.get("bureau_metrics", {}).get("evidence_id", "MISSING_BUREAU_EVD")')
    content = content.replace('"EVD-GST-001"', 'self.features.get("gst_metrics", {}).get("evidence_id", "MISSING_GST_EVD")')
    
    # Remove assumed 50000 EMI
    content = content.replace('total_ds = existing_ds + Decimal("50000") # Assume typical EMI for score context if unknown', 'total_ds = existing_ds')
    
    with open(scorer_file, 'w') as f:
        f.write(content)

# Fix stress/engine.py
stress_file = 'backend/app/domain/stress/engine.py'
if os.path.exists(stress_file):
    with open(stress_file, 'r') as f:
        content = f.read()
    
    content = content.replace('["EVD-BANK-001"]', '[]')
    
    with open(stress_file, 'w') as f:
        f.write(content)

# Fix ocen.py
ocen_file = 'backend/app/api/routers/ocen.py'
if os.path.exists(ocen_file):
    with open(ocen_file, 'r') as f:
        content = f.read()
    
    content = content.replace('"UNSEALED_PROTOTYPE"', '""')
    
    with open(ocen_file, 'w') as f:
        f.write(content)

print("Step 2 completed")
