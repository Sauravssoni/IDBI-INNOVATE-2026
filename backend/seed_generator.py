import re

def generate(source_file, target_file, replacements):
    with open(source_file, 'r') as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(target_file, 'w') as f:
        f.write(content)

base = 'app/seed/seed_shakti.py'

generate(base, 'app/seed/seed_navprerna.py', [
    ('seed_shakti', 'seed_navprerna'),
    ('SHAKTI_PRECISION_001', 'NAVPRERNA_TECH_001'),
    ('Shakti Precision Components Pvt Ltd', 'NavPrerna Tech Solutions'),
    ('Manufacturing - Auto Ancillary', 'IT/Services'),
    ('shakti', 'navprerna'),
    ('5000000.00', '1500000.00'),
    ('CaseStatus.INITIATED', 'CaseStatus.SUBMITTED')
])

generate(base, 'app/seed/seed_rangrez.py', [
    ('seed_shakti', 'seed_rangrez'),
    ('SHAKTI_PRECISION_001', 'RANGREZ_TEXTILE_001'),
    ('Shakti Precision Components Pvt Ltd', 'Rangrez Textiles'),
    ('Manufacturing - Auto Ancillary', 'Textiles'),
    ('shakti', 'rangrez'),
    ('5000000.00', '8000000.00'),
    ('CaseStatus.INITIATED', 'CaseStatus.RECOMMENDED')
])

generate(base, 'app/seed/seed_aarohan.py', [
    ('seed_shakti', 'seed_aarohan'),
    ('SHAKTI_PRECISION_001', 'AAROHAN_INFRA_001'),
    ('Shakti Precision Components Pvt Ltd', 'Aarohan Infrastructure'),
    ('Manufacturing - Auto Ancillary', 'Construction'),
    ('shakti', 'aarohan'),
    ('5000000.00', '10000000.00'),
    ('CaseStatus.INITIATED', 'CaseStatus.SANCTIONED')
])

