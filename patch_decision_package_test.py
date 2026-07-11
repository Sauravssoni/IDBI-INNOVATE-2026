import re

with open("frontend/tests/decision-package.test.tsx", "r") as f:
    content = f.read()

content = content.replace("const mockData: DecisionPackageResponse = {", "const mockData = {")
content = content.replace("data: mockData", "data: mockData as unknown as DecisionPackageResponse")

with open("frontend/tests/decision-package.test.tsx", "w") as f:
    f.write(content)
