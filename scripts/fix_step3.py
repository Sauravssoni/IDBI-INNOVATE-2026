import os
import re

scorer_file = 'backend/app/core/scoring/scorer.py'
if os.path.exists(scorer_file):
    with open(scorer_file, 'r') as f:
        content = f.read()
    
    # Change post_loan_dscr to existing_dscr
    content = content.replace('post_loan_dscr', 'existing_dscr')
    content = content.replace('total_ds = existing_ds', '') # Since it was total_ds = existing_ds, we can just use existing_ds
    content = content.replace('operating_cash / max(Decimal("1"), total_ds)', 'operating_cash / max(Decimal("1"), existing_ds)')
    
    with open(scorer_file, 'w') as f:
        f.write(content)
print("Updated scorer.py for DSCR naming")
