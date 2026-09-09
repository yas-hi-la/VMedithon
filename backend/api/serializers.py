"""Serialization for API-facing analysis responses."""

from typing import Any

from backend.analysis.types import AnalysisResult, EvidenceItem


def _serialize_evidence(item: EvidenceItem) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "criterion": item.criterion.value,
        "strength": item.strength.value,
        "direction": item.direction.value,
        "source": {
            "name": item.source.name,
            "reference": item.source.reference,
        },
        "summary": item.summary,
    }


def serialize_analysis_result(result: AnalysisResult) -> dict[str, Any]:
    return {
        "variant": {
            "id": result.variant.id,
            "gene": result.variant.gene,
            "hgvs_notation": result.variant.hgvs_notation,
        },
        "classification": result.classification.value,
        "status": result.status.value,
        "criteria_considered": [
            criterion.value for criterion in result.criteria_considered
        ],
        "evidence_used": [_serialize_evidence(item) for item in result.evidence_used],
        "criterion_evaluations": [
            {
                "criterion": evaluation.criterion.value,
                "direction": evaluation.direction.value,
                "strength": evaluation.strength.value,
                "evidence_ids": list(evaluation.evidence_ids),
                "supported": evaluation.supported,
                "explanation": evaluation.explanation,
            }
            for evaluation in result.criterion_evaluations
        ],
        "rule_evaluations": [
            {
                "rule_id": evaluation.rule_id,
                "classification": evaluation.classification.value,
                "satisfied": evaluation.satisfied,
                "evidence_ids": list(evaluation.evidence_ids),
                "explanation": evaluation.explanation,
            }
            for evaluation in result.rule_evaluations
        ],
        "satisfied_rules": list(result.satisfied_rules),
        "unsupported_rules": list(result.unsupported_rules),
        "decision_trace": list(result.decision_trace),
    }
