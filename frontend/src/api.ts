export interface EvidenceItem {
  id: string
  criterion: string
  strength: string
  direction: string
  source_name: string
  source_ref: string
  summary: string
}

export interface AnalysisRequest {
  gene: string
  hgvs_notation: string
  evidence: EvidenceItem[]
}

export interface RuleResult {
  rule: string
  satisfied: boolean
  evidence_ids: string[]
  description: string
}

export interface AnalysisResult {
  variant_id?: string
  gene: string
  hgvs_notation: string
  classification: string
  status: string
  criteria_considered: string[]
  satisfied_rules: RuleResult[]
  unsupported_rules: RuleResult[]
  evidence_trace: EvidenceItem[]
  decision_trace: string[]
  reasoning?: string
}

interface BackendEvidence {
  evidence_id: string
  criterion: string
  strength: string
  direction: string
  source: {
    name: string
    reference: string | null
  }
  summary: string
}

interface BackendRuleEvaluation {
  rule_id: string
  classification: string
  satisfied: boolean
  evidence_ids: string[]
  explanation: string
}

interface BackendAnalysisResult {
  variant: {
    id?: string | number;
    gene: string
    hgvs_notation: string
  }
  classification: string
  status: string
  criteria_considered: string[]
  evidence_used: BackendEvidence[]
  rule_evaluations: BackendRuleEvaluation[]
  satisfied_rules: string[]
  unsupported_rules: string[]
  decision_trace: string[]
}

interface BackendSavedVariant {
  evidence: BackendEvidence[]
}

export class ApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "")

function toBackendEvidence(item: EvidenceItem): BackendEvidence {
  return {
    evidence_id: item.id,
    criterion: item.criterion,
    strength: item.strength,
    direction: item.direction,
    source: {
      name: item.source_name,
      reference: item.source_ref || null,
    },
    summary: item.summary,
  }
}

function toFrontendEvidence(item: BackendEvidence): EvidenceItem {
  return {
    id: item.evidence_id,
    criterion: item.criterion,
    strength: item.strength,
    direction: item.direction,
    source_name: item.source.name,
    source_ref: item.source.reference ?? "",
    summary: item.summary,
  }
}

function classificationLabel(classification: string): string {
  const labels: Record<string, string> = {
    pathogenic: "Pathogenic",
    likely_pathogenic: "Likely Pathogenic",
    uncertain_significance: "Uncertain Significance",
    likely_benign: "Likely Benign",
    benign: "Benign",
    conflicting: "Conflicting",
    insufficient_evidence: "Insufficient Evidence",
  }
  return labels[classification] ?? classification
}

function toRuleResult(evaluation: BackendRuleEvaluation): RuleResult {
  return {
    rule: evaluation.rule_id,
    satisfied: evaluation.satisfied,
    evidence_ids: evaluation.evidence_ids,
    description: evaluation.explanation,
  }
}

function mapAnalysisResult(result: BackendAnalysisResult): AnalysisResult {
  const evaluations = result.rule_evaluations.map(toRuleResult)
  const satisfiedIds = new Set(result.satisfied_rules)
  const satisfiedRules = evaluations.filter(
    (evaluation) => evaluation.satisfied || satisfiedIds.has(evaluation.rule),
  )
  const evaluatedRuleIds = new Set(
    evaluations.map((evaluation) => evaluation.rule),
  )
  const unsupportedRules = [
    ...evaluations.filter((evaluation) => !evaluation.satisfied),
    ...result.unsupported_rules
      .filter((rule) => !evaluatedRuleIds.has(rule))
      .map((rule) => ({
        rule,
        satisfied: false,
        evidence_ids: [],
        description: "This rule is not currently supported by the backend.",
      })),
  ]

  return {
    variant_id: result.variant.id === undefined ? undefined : String(result.variant.id),
    gene: result.variant.gene,
    hgvs_notation: result.variant.hgvs_notation,
    classification: classificationLabel(result.classification),
    status: result.status,
    criteria_considered: result.criteria_considered,
    satisfied_rules: satisfiedRules,
    unsupported_rules: unsupportedRules,
    evidence_trace: result.evidence_used.map(toFrontendEvidence),
    decision_trace: result.decision_trace,
    reasoning: result.decision_trace.join(" "),
  }
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { message?: string } }
    return body.error?.message ?? `Server error ${response.status}`
  } catch {
    return `Server error ${response.status}`
  }
}

async function request<T>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(input, init)
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Network request failed"
    throw new ApiError(`Backend unavailable: ${message}`)
  }

  if (!response.ok) {
    throw new ApiError(await getErrorMessage(response), response.status)
  }
  return (await response.json()) as T
}

export async function analyzeVariant(
  req: AnalysisRequest,
): Promise<AnalysisResult> {
  const result = await request<BackendAnalysisResult>(
    `${API_BASE}/analysis/variants`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        variant: {
          gene: req.gene,
          hgvs_notation: req.hgvs_notation,
        },
        evidence: req.evidence.map(toBackendEvidence),
      }),
      signal: AbortSignal.timeout(15000),
    },
  )
  return mapAnalysisResult(result)
}

export async function loadSavedVariant(
  gene: string,
  hgvsNotation: string,
): Promise<{ evidence: EvidenceItem[] } | null> {
  const params = new URLSearchParams({ gene, hgvs_notation: hgvsNotation })
  try {
    const result = await request<BackendSavedVariant>(
      `${API_BASE}/analysis/variants?${params}`,
      { signal: AbortSignal.timeout(8000) },
    )
    return { evidence: result.evidence.map(toFrontendEvidence) }
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}
