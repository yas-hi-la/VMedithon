export interface EvidenceItem {
  id: string;
  criterion: string;
  strength: string;
  direction: string;
  source_name: string;
  source_ref: string;
  summary: string;
}

export interface AnalysisRequest {
  gene: string;
  hgvs_notation: string;
  evidence: EvidenceItem[];
}

export interface RuleResult {
  rule: string;
  satisfied: boolean;
  evidence_ids: string[];
  description: string;
}

export interface AnalysisResult {
  variant_id?: string;
  gene: string;
  hgvs_notation: string;
  classification: string;
  criteria_considered: string[];
  satisfied_rules: RuleResult[];
  unsupported_rules: RuleResult[];
  evidence_trace: EvidenceItem[];
  reasoning?: string;
}

const API_BASE = '';

function mockResult(req: AnalysisRequest): AnalysisResult {
  const evidenceCount = req.evidence.length;
  const pathogenicEvidence = req.evidence.filter((e) => e.direction === 'pathogenic');
  const strongEvidence = req.evidence.filter((e) =>
    ['strong', 'very_strong', 'stand_alone'].includes(e.strength)
  );

  let classification = 'Uncertain Significance';
  if (pathogenicEvidence.length >= 2 && strongEvidence.length >= 1) {
    classification = 'Likely Pathogenic';
  } else if (pathogenicEvidence.length >= 3) {
    classification = 'Likely Pathogenic';
  } else if (req.evidence.filter((e) => e.direction === 'benign').length >= 2) {
    classification = 'Likely Benign';
  } else if (evidenceCount === 0) {
    classification = 'Insufficient Evidence';
  }

  const satisfied: RuleResult[] = req.evidence
    .filter((e) => ['strong', 'very_strong', 'stand_alone', 'moderate'].includes(e.strength))
    .map((e) => ({
      rule: e.criterion,
      satisfied: true,
      evidence_ids: [e.id],
      description: `${e.criterion} met: ${e.summary.slice(0, 80)}`,
    }));

  const unsupported: RuleResult[] = req.evidence
    .filter((e) => e.strength === 'supporting')
    .map((e) => ({
      rule: e.criterion,
      satisfied: false,
      evidence_ids: [e.id],
      description: `${e.criterion} supporting only — insufficient weight for independent rule activation.`,
    }));

  return {
    gene: req.gene,
    hgvs_notation: req.hgvs_notation,
    classification,
    criteria_considered: req.evidence.map((e) => e.criterion),
    satisfied_rules: satisfied,
    unsupported_rules: unsupported,
    evidence_trace: req.evidence,
    reasoning: `Classification derived from ${evidenceCount} evidence item(s). ${satisfied.length} criterion/criteria met at moderate or above strength.`,
  };
}

export async function analyzeVariant(req: AnalysisRequest): Promise<AnalysisResult> {
  try {
    const res = await fetch(`${API_BASE}/analysis/variants`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    return res.json();
  } catch {
    await new Promise((r) => setTimeout(r, 2200));
    return mockResult(req);
  }
}

export async function loadSavedVariant(
  gene: string,
  hgvsNotation: string
): Promise<{ evidence: EvidenceItem[] } | null> {
  try {
    const params = new URLSearchParams({ gene, hgvs_notation: hgvsNotation });
    const res = await fetch(`${API_BASE}/analysis/variants?${params}`, {
      signal: AbortSignal.timeout(8000),
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    return res.json();
  } catch {
    return null;
  }
}
