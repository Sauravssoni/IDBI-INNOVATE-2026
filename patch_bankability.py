import re

with open("backend/app/domain/bankability/path.py", "r") as f:
    content = f.read()

# MIL-001 (30-day)
# Remove:
#    if proj_lim_30 == 0 and current_state not in ("APPROVE", "READY_FOR_REVIEW"):
#        proj_lim_30 = (requested_amount * Decimal("0.60")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
content = re.sub(
    r'if proj_lim_30 == 0 and current_state not in \("APPROVE", "READY_FOR_REVIEW"\):\s*proj_lim_30 = \(requested_amount \* Decimal\("0\.60"\)\)\.quantize\(Decimal\("0\.01"\), rounding=ROUND_HALF_UP\)',
    '',
    content
)

# MIL-002 (60-day)
# Remove:
#    if proj_lim_60 == 0:
#        proj_lim_60 = (requested_amount * Decimal("0.80")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
#    elif proj_lim_60 < proj_lim_30:
#        proj_lim_60 = (proj_lim_30 * Decimal("1.20")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
content = re.sub(
    r'if proj_lim_60 == 0:\s*proj_lim_60 = \(requested_amount \* Decimal\("0\.80"\)\)\.quantize\(Decimal\("0\.01"\), rounding=ROUND_HALF_UP\)\s*elif proj_lim_60 < proj_lim_30:\s*proj_lim_60 = \(proj_lim_30 \* Decimal\("1\.20"\)\)\.quantize\(Decimal\("0\.01"\), rounding=ROUND_HALF_UP\)',
    '',
    content
)

# MIL-003 (90-day)
# Remove:
#    if proj_lim_90 < requested_amount:
#        proj_lim_90 = requested_amount
content = re.sub(
    r'if proj_lim_90 < requested_amount:\s*proj_lim_90 = requested_amount',
    '',
    content
)

# Replace target_tier and projected_limit_inr in milestones.
def repl_milestone_30(m):
    return '''            "target_tier": "BALANCED" if proj_lim_30 > 0 else "IMPACT_NOT_QUANTIFIABLE",
            "projected_limit_inr": float(proj_lim_30) if proj_lim_30 > 0 else "IMPACT_NOT_QUANTIFIABLE",'''
content = re.sub(
    r'"target_tier": "BALANCED" if proj_lim_30 > 0 else "CONSERVATIVE",\s*"projected_limit_inr": float\(proj_lim_30\),',
    repl_milestone_30,
    content
)

def repl_milestone_60(m):
    return '''            "target_tier": "BALANCED" if proj_lim_60 > 0 else "IMPACT_NOT_QUANTIFIABLE",
            "projected_limit_inr": float(proj_lim_60) if proj_lim_60 > 0 else "IMPACT_NOT_QUANTIFIABLE",'''
content = re.sub(
    r'"target_tier": "BALANCED",\s*"projected_limit_inr": float\(proj_lim_60\),',
    repl_milestone_60,
    content
)

def repl_milestone_90(m):
    return '''            "target_tier": "GROWTH" if proj_lim_90 > 0 else "IMPACT_NOT_QUANTIFIABLE",
            "projected_limit_inr": float(proj_lim_90) if proj_lim_90 > 0 else "IMPACT_NOT_QUANTIFIABLE",'''
content = re.sub(
    r'"target_tier": "GROWTH",\s*"projected_limit_inr": float\(proj_lim_90\),',
    repl_milestone_90,
    content
)

# Fix max_achievable
#    max_achievable = max([m.get("projected_limit_inr", 0.0) for m in milestones] + [curr_lim_flt])
def repl_max_achievable(m):
    return 'max_achievable = max([m.get("projected_limit_inr", 0.0) if isinstance(m.get("projected_limit_inr", 0.0), (int, float)) else 0.0 for m in milestones] + [curr_lim_flt])'
content = re.sub(
    r'max_achievable = max\(\[m\.get\("projected_limit_inr", 0\.0\) for m in milestones\] \+ \[curr_lim_flt\]\)',
    repl_max_achievable,
    content
)


with open("backend/app/domain/bankability/path.py", "w") as f:
    f.write(content)
