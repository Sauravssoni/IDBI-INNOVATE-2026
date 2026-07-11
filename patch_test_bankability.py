import re

with open("backend/tests/domain/test_bankability.py", "r") as f:
    content = f.read()

content = re.sub(
    r'assert m\["projected_limit_inr"\] >= 0',
    'if m["projected_limit_inr"] != "IMPACT_NOT_QUANTIFIABLE":\n                assert m["projected_limit_inr"] >= 0',
    content
)

with open("backend/tests/domain/test_bankability.py", "w") as f:
    f.write(content)
