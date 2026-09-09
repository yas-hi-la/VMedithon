"""Deterministic ACMG/AMP-style analysis over supplied evidence."""

from collections.abc import Iterable
from collections import defaultdict

from backend.analysis.rules import SUPPORTED_RULES, UNSUPPORTED_RULE_IDS
from backend.analysis.types import (
    AnalysisResult,
    AnalysisStatus,
    Classification,
    CriterionCode,
    CriterionEvaluation,
    CriterionStrength,
    EvidenceDirection,
    EvidenceItem,
    RuleEvaluation,
)
from backend.models.variant import Variant


def _evaluate_criteria(
    evidence_items: tuple[EvidenceItem, ...],
) -> tuple[
    tuple[CriterionEvaluation, ...],
    dict[tuple[EvidenceDirection, CriterionStrength], list[tuple[CriterionCode, tuple[str, ...]]]],
]:
    grouped: dict[CriterionCode, list[EvidenceItem]] = defaultdict(list)
    for item in evidence_items:
        grouped[item.criterion].append(item)

    evaluations: list[CriterionEvaluation] = []
    usable: dict[
        tuple[EvidenceDirection, CriterionStrength],
        list[tuple[CriterionCode, tuple[str, ...]]],
    ] = defaultdict(list)
    for criterion in sorted(grouped, key=lambda item: item.value):
        items = grouped[criterion]
        directions = {item.direction for item in items}
        strengths = {item.strength for item in items}
        evidence_ids = tuple(sorted(item.evidence_id for item in items))
        if len(directions) == 1 and len(strengths) == 1:
            direction = next(iter(directions))
            strength = next(iter(strengths))
            evaluations.append(
                CriterionEvaluation(
                    criterion=criterion,
                    direction=direction,
                    strength=strength,
                    evidence_ids=evidence_ids,
                    supported=True,
                    explanation="Criterion is explicitly supplied with one direction and strength.",
                )
            )
            usable[(direction, strength)].append((criterion, evidence_ids))
            continue

        direction = next(iter(directions))
        strength = next(iter(strengths))
        evaluations.append(
            CriterionEvaluation(
                criterion=criterion,
                direction=direction,
                strength=strength,
                evidence_ids=evidence_ids,
                supported=False,
                explanation=(
                    "Criterion has conflicting supplied directions or strengths and "
                    "was excluded from rule combination."
                ),
            )
        )
    return tuple(evaluations), usable


def _evaluate_rules(
    usable: dict[
        tuple[EvidenceDirection, CriterionStrength],
        list[tuple[CriterionCode, tuple[str, ...]]],
    ],
) -> tuple[tuple[RuleEvaluation, ...], tuple[RuleEvaluation, ...]]:
    evaluations: list[RuleEvaluation] = []
    satisfied: list[RuleEvaluation] = []
    for rule in SUPPORTED_RULES:
        contributing_ids: list[str] = []
        rule_satisfied = True
        for strength, minimum_count in rule.minimum_strength_counts:
            candidates = usable.get((rule.direction, strength), [])
            if len(candidates) < minimum_count:
                rule_satisfied = False
                continue
            for _, evidence_ids in candidates[:minimum_count]:
                contributing_ids.extend(evidence_ids)
        evaluation = RuleEvaluation(
            rule_id=rule.rule_id,
            classification=rule.classification,
            satisfied=rule_satisfied,
            evidence_ids=tuple(sorted(set(contributing_ids))),
            explanation=rule.explanation,
        )
        evaluations.append(evaluation)
        if rule_satisfied:
            satisfied.append(evaluation)
    return tuple(evaluations), tuple(satisfied)


def analyze_variant(
    variant: Variant,
    evidence: Iterable[EvidenceItem],
) -> AnalysisResult:
    """Analyze supplied evidence without inferring missing clinical evidence."""
    if not isinstance(variant, Variant):
        raise TypeError("variant must be a Variant")

    evidence_items = tuple(evidence)
    if any(not isinstance(item, EvidenceItem) for item in evidence_items):
        raise TypeError("evidence must contain only EvidenceItem values")
    evidence_ids = [item.evidence_id for item in evidence_items]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("evidence_id values must be unique")

    criteria_considered = tuple(
        sorted({item.criterion for item in evidence_items}, key=lambda item: item.value)
    )
    criterion_evaluations, usable = _evaluate_criteria(evidence_items)
    rule_evaluations, satisfied_rules = _evaluate_rules(usable)
    directions = {item.direction for item in evidence_items}

    if not evidence_items:
        classification = Classification.INSUFFICIENT_EVIDENCE
        status = AnalysisStatus.INSUFFICIENT
        trace = (
            "No structured evidence was supplied; missing evidence is not treated "
            "as benign or pathogenic.",
        )
    elif directions == {
        EvidenceDirection.PATHOGENIC,
        EvidenceDirection.BENIGN,
    }:
        classification = Classification.CONFLICTING
        status = AnalysisStatus.CONFLICTING
        trace = (
            "Both pathogenic and benign evidence are present; conflicting evidence "
            "is reported explicitly.",
        )
    elif satisfied_rules:
        selected_rule = satisfied_rules[0]
        classification = selected_rule.classification
        status = AnalysisStatus.SUPPORTED
        trace = (
            f"Rule {selected_rule.rule_id} is satisfied by evidence IDs: "
            f"{', '.join(selected_rule.evidence_ids)}. {selected_rule.explanation}",
        )
    else:
        classification = Classification.INSUFFICIENT_EVIDENCE
        status = AnalysisStatus.UNSUPPORTED
        trace = (
            "Structured evidence was supplied, but no ACMG/AMP combination rule "
            "is currently supported for this combination; classification remains "
            "insufficient.",
        )

    return AnalysisResult(
        variant=variant,
        classification=classification,
        criteria_considered=criteria_considered,
        evidence_used=evidence_items,
        decision_trace=trace,
        status=status,
        criterion_evaluations=criterion_evaluations,
        rule_evaluations=rule_evaluations,
        satisfied_rules=tuple(rule.rule_id for rule in satisfied_rules),
        unsupported_rules=UNSUPPORTED_RULE_IDS,
    )
