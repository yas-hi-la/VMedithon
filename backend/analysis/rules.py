"""Small, explicit subset of ACMG/AMP combination rules."""

from dataclasses import dataclass

from backend.analysis.types import (
    Classification,
    CriterionStrength,
    EvidenceDirection,
)


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    classification: Classification
    direction: EvidenceDirection
    minimum_strength_counts: tuple[tuple[CriterionStrength, int], ...]
    explanation: str


SUPPORTED_RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        rule_id="P_VERY_STRONG_PLUS_STRONG",
        classification=Classification.PATHOGENIC,
        direction=EvidenceDirection.PATHOGENIC,
        minimum_strength_counts=(
            (CriterionStrength.VERY_STRONG, 1),
            (CriterionStrength.STRONG, 1),
        ),
        explanation="One very strong and one strong pathogenic criterion are present.",
    ),
    RuleDefinition(
        rule_id="P_TWO_STRONG",
        classification=Classification.PATHOGENIC,
        direction=EvidenceDirection.PATHOGENIC,
        minimum_strength_counts=((CriterionStrength.STRONG, 2),),
        explanation="Two strong pathogenic criteria are present.",
    ),
    RuleDefinition(
        rule_id="LP_VERY_STRONG_PLUS_MODERATE",
        classification=Classification.LIKELY_PATHOGENIC,
        direction=EvidenceDirection.PATHOGENIC,
        minimum_strength_counts=(
            (CriterionStrength.VERY_STRONG, 1),
            (CriterionStrength.MODERATE, 1),
        ),
        explanation="One very strong and one moderate pathogenic criterion are present.",
    ),
    RuleDefinition(
        rule_id="LP_STRONG_PLUS_MODERATE",
        classification=Classification.LIKELY_PATHOGENIC,
        direction=EvidenceDirection.PATHOGENIC,
        minimum_strength_counts=(
            (CriterionStrength.STRONG, 1),
            (CriterionStrength.MODERATE, 1),
        ),
        explanation="One strong and one moderate pathogenic criterion are present.",
    ),
    RuleDefinition(
        rule_id="LP_STRONG_PLUS_TWO_SUPPORTING",
        classification=Classification.LIKELY_PATHOGENIC,
        direction=EvidenceDirection.PATHOGENIC,
        minimum_strength_counts=(
            (CriterionStrength.STRONG, 1),
            (CriterionStrength.SUPPORTING, 2),
        ),
        explanation="One strong and two supporting pathogenic criteria are present.",
    ),
    RuleDefinition(
        rule_id="B_STAND_ALONE",
        classification=Classification.BENIGN,
        direction=EvidenceDirection.BENIGN,
        minimum_strength_counts=((CriterionStrength.STAND_ALONE, 1),),
        explanation="One stand-alone benign criterion is present.",
    ),
    RuleDefinition(
        rule_id="B_TWO_STRONG",
        classification=Classification.BENIGN,
        direction=EvidenceDirection.BENIGN,
        minimum_strength_counts=((CriterionStrength.STRONG, 2),),
        explanation="Two strong benign criteria are present.",
    ),
    RuleDefinition(
        rule_id="LB_STRONG_PLUS_SUPPORTING",
        classification=Classification.LIKELY_BENIGN,
        direction=EvidenceDirection.BENIGN,
        minimum_strength_counts=(
            (CriterionStrength.STRONG, 1),
            (CriterionStrength.SUPPORTING, 1),
        ),
        explanation="One strong and one supporting benign criterion are present.",
    ),
)

UNSUPPORTED_RULE_IDS = (
    "ADDITIONAL_ACMG_AMP_COMBINATIONS",
)
