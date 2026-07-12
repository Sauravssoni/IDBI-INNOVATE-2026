const fs = require('fs');
const file = 'frontend/app/cases/[caseId]/tabs/EvidenceTab.tsx';
let content = fs.readFileSync(file, 'utf8');

// Add state for envelope
content = content.replace(
  'const [loading, setLoading] = useState(true);',
  'const [loading, setLoading] = useState(true);\n  const [envelope, setEnvelope] = useState<any>(null);'
);

// Fetch envelope
content = content.replace(
  'apiFetch<ObligationEvidence[]>(`/api/cases/${caseId}/evidence/obligations`)',
  'apiFetch<ObligationEvidence[]>(`/api/cases/${caseId}/evidence/obligations`),\n        apiFetch<any>(`/api/cases/${caseId}/evidence-envelope`)'
);
content = content.replace(
  'const [gstRes, bankRes, invoiceRes, empRes, obRes] = await Promise.all([',
  'const [gstRes, bankRes, invoiceRes, empRes, obRes, envRes] = await Promise.all(['
);
content = content.replace(
  'if (obRes.status === 200) setObligationRecords(obRes.data || []);',
  'if (obRes.status === 200) setObligationRecords(obRes.data || []);\n      if (envRes.status === 200) setEnvelope(envRes.data);'
);

// UI for envelope
const uiCode = `
      {/* Evidence Envelope */}
      {envelope && (
        <div className="glass-card p-6 border border-light-border shadow-sm mb-6 bg-gradient-to-r from-light-bg to-light-elevated">
          <h3 className="text-lg font-bold text-light-text flex items-center gap-2 mb-4">
            <ShieldAlert className="w-5 h-5 text-brand-teal" />
            Evidence Confidence Envelope
          </h3>
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 bg-light-bg rounded-xl border border-light-border">
              <div className="text-sm text-light-secondary mb-1">Certainty</div>
              <div className="text-xl font-mono text-brand-teal">{(envelope.certainty * 100).toFixed(0)}%</div>
            </div>
            <div className="p-4 bg-light-bg rounded-xl border border-light-border">
              <div className="text-sm text-light-secondary mb-1">Freshness</div>
              <div className="text-xl font-mono text-light-text">{envelope.freshness}</div>
            </div>
            <div className="p-4 bg-light-bg rounded-xl border border-light-border">
              <div className="text-sm text-light-secondary mb-1">Unresolved Ratio</div>
              <div className="text-xl font-mono text-brand-red">{(envelope.unresolved_ratio * 100).toFixed(1)}%</div>
            </div>
            <div className="p-4 bg-light-bg rounded-xl border border-light-border">
              <div className="text-sm text-light-secondary mb-1">Reason Codes</div>
              <div className="text-xs font-mono text-light-text mt-1 space-y-1">
                {envelope.reason_codes?.length ? envelope.reason_codes.map((c: string) => <div key={c}>{c}</div>) : "None"}
              </div>
            </div>
          </div>
        </div>
      )}
`;

content = content.replace(
  'if (loading) {',
  uiCode + '\n  if (loading) {'
);

fs.writeFileSync(file, content);
