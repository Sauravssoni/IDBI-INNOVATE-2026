import re

with open("frontend/app/cases/[caseId]/tabs/DecisionPackageTab.tsx", "r") as f:
    content = f.read()

new_breakdown = """                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>Liquidity: <span className="font-semibold text-white">{data.fhi_breakdown.liquidity?.score ?? "N/A"}</span></div>
                  <div>Cash Flow Capacity: <span className="font-semibold text-white">{data.fhi_breakdown.cash_flow_capacity?.score ?? "N/A"}</span></div>
                  <div>Revenue Growth: <span className="font-semibold text-white">{data.fhi_breakdown.revenue_growth?.score ?? "N/A"}</span></div>
                  <div>Repayment Burden: <span className="font-semibold text-white">{data.fhi_breakdown.repayment_burden?.score ?? "N/A"}</span></div>
                  <div>Compliance/Gov: <span className="font-semibold text-white">{data.fhi_breakdown.compliance_governance?.score ?? "N/A"}</span></div>
                  <div>Concentration/Risk: <span className="font-semibold text-white">{data.fhi_breakdown.concentration_risk?.score ?? "N/A"}</span></div>
                </div>"""

# we replace the grid in DecisionPackageTab.tsx
content = re.sub(
    r'<div className="grid grid-cols-2 gap-2 text-xs">\s*<div>Liquidity.*?</div>\s*<div>Solvency.*?</div>\s*<div>Efficiency.*?</div>\s*<div>Profitability.*?</div>\s*<div>Compliance.*?</div>\s*<div>Resilience.*?</div>\s*</div>',
    new_breakdown,
    content,
    flags=re.DOTALL
)

with open("frontend/app/cases/[caseId]/tabs/DecisionPackageTab.tsx", "w") as f:
    f.write(content)
