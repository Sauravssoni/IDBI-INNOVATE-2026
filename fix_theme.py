import re

with open("frontend/app/cases/[caseId]/tabs/DecisionPackageTab.tsx", "r") as f:
    content = f.read()

# Replace colors
content = content.replace('bg-white/5', 'bg-light-bg')
content = content.replace('border-white/10', 'border-light-border')
content = content.replace('text-white', 'text-light-text')
content = content.replace('text-gray-400', 'text-light-secondary')
content = content.replace('text-gray-300', 'text-light-text')
content = content.replace('text-gray-500', 'text-light-secondary')
content = content.replace('bg-black/20', 'bg-light-elevated')
content = content.replace('border-white/5', 'border-light-border')
content = content.replace('bg-black/40', 'bg-light-bg')
content = content.replace('bg-black/10', 'bg-light-bg opacity-50')
content = content.replace('bg-black/30', 'bg-light-bg')

content = content.replace('emerald-400', 'brand-teal')
content = content.replace('emerald-500/20', 'brand-softTeal')
content = content.replace('emerald-500/30', 'brand-teal/30')
content = content.replace('emerald-500', 'brand-teal')
content = content.replace('emerald-300', 'brand-teal')

content = content.replace('purple-400', 'indigo-600')
content = content.replace('purple-500/20', 'indigo-50')
content = content.replace('purple-500/30', 'indigo-200')
content = content.replace('purple-300', 'indigo-600')

content = content.replace('blue-400', 'blue-600')
content = content.replace('blue-500/20', 'blue-50')
content = content.replace('blue-500/30', 'blue-200')

content = content.replace('amber-400', 'brand-amber')
content = content.replace('amber-500/20', 'brand-softAmber')
content = content.replace('amber-500/30', 'brand-amber/30')

content = content.replace('red-400', 'brand-red')
content = content.replace('red-500/10', 'rose-50')
content = content.replace('red-500/20', 'rose-200')

with open("frontend/app/cases/[caseId]/tabs/DecisionPackageTab.tsx", "w") as f:
    f.write(content)
