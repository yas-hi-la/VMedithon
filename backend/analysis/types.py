"""Domain types for deterministic variant analysis."""

from dataclasses import dataclass
from enum import Enum

from backend.models.variant import Variant


class CriterionCode(str, Enum):
    """ACMG/AMP criteria currently accepted as structured evidence."""

    BP4 = "BP4"
    BS1 = "BS1"
    PM2 = "PM2"
    PP3 = "PP3"
    PS3 = "PS3"


class CriterionStrength(str, Enum):
    """ACMG/AMP evidence strength labels."""

    SUPPORTING = "supporting"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"
    STAND_ALONE = "stand_alone"


class EvidenceDirection(str, Enum):
    PATHOGENIC = "pathogenic"
    BENIGN = "benign"


class Classification(str, Enum):
    PATHOGENIC = "pathogenic"
    LIKELY_PATHOGENIC = "likely_pathogenic"
    UNCERTAIN_SIGNIFICANCE = "uncertain_significance"
    LIKELY_BENIGN = "likely_benign"
    BENIGN = "benign"
    CONFLICTING = "conflicting"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class AnalysisStatus(str, Enum):
    SUPPORTED = "supported"
    INSUFFICIENT = "insufficient"
    CONFLICTING = "conflicting"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class EvidenceSource:
    name: str
    reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("evidence source name must be a non-empty string")
        if self.reference is not None and not isinstance(self.reference, str):
            raise ValueError("evidence source reference must be a string or None")


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    criterion: CriterionCode
    strength: CriterionStrength
    direction: EvidenceDirection
    source: EvidenceSource
    summary: str

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("evidence_id must be a non-empty string")
        if not isinstance(self.criterion, CriterionCode):
            raise ValueError("criterion must be a supported CriterionCode")
        if not isinstance(self.strength, CriterionStrength):
            raise ValueError("strength must be a supported CriterionStrength")
        if not isinstance(self.direction, EvidenceDirection):
            raise ValueError("direction must be an EvidenceDirection")
        if not isinstance(self.source, EvidenceSource):
            raise ValueError("source must be an EvidenceSource")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")


@dataclass(frozen=True)
class CriterionEvaluation:
    criterion: CriterionCode
    direction: EvidenceDirection
    strength: CriterionStrength
    evidence_ids: tuple[str, ...]
    supported: bool
    explanation: str


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    classification: Classification
    satisfied: bool
    evidence_ids: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class AnalysisResult:
    variant: Variant
    classification: Classification
    criteria_considered: tuple[CriterionCode, ...]
    evidence_used: tuple[EvidenceItem, ...]
    decision_trace: tuple[str, ...]
    status: AnalysisStatus = AnalysisStatus.INSUFFICIENT
    criterion_evaluations: tuple[CriterionEvaluation, ...] = ()
    rule_evaluations: tuple[RuleEvaluation, ...] = ()
    satisfied_rules: tuple[str, ...] = ()
    unsupported_rules: tuple[str, ...] = ()
