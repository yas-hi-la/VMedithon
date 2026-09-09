"""ClinVar retrieval and normalization."""

from dataclasses import dataclass
import json
import os
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CLINVAR_SOURCE = "ClinVar"
CLINVAR_EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _ssl_context() -> ssl.SSLContext:
    configured_path = os.getenv("SSL_CERT_FILE")
    candidates = (
        configured_path,
        ssl.get_default_verify_paths().cafile,
        "/etc/ssl/cert.pem",
    )
    for path in candidates:
        if path and os.path.isfile(path):
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


@dataclass(frozen=True)
class RetrievedEvidence:
    evidence_id: str
    source: str
    source_ref: str | None
    summary: str
    classification: str | None
    review_status: str | None
    last_evaluated: str | None


@dataclass(frozen=True)
class EvidenceRetrievalResult:
    source: str
    status: str
    evidence: tuple[RetrievedEvidence, ...]
    message: str


class ClinVarRetrievalError(RuntimeError):
    """Raised when ClinVar cannot provide a usable response."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def _request_json(url: str, timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "VUSIGHT/1.0 (public evidence retrieval)",
        },
    )
    try:
        with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code == 429:
            raise ClinVarRetrievalError("ClinVar rate limit reached", 429) from error
        raise ClinVarRetrievalError(f"ClinVar returned HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ClinVarRetrievalError("ClinVar could not be reached") from error

    if not isinstance(payload, dict):
        raise ClinVarRetrievalError("ClinVar returned an unexpected response")
    return payload


def _search_ids(gene: str, hgvs_notation: str, timeout: float) -> list[str]:
    term = f"{gene}[Gene Name] AND {hgvs_notation}[Variant Name]"
    query = urlencode({"db": "clinvar", "term": term, "retmode": "json", "retmax": "10"})
    payload = _request_json(f"{CLINVAR_EUTILS_URL}/esearch.fcgi?{query}", timeout)
    result = payload.get("esearchresult")
    if not isinstance(result, dict) or not isinstance(result.get("idlist"), list):
        raise ClinVarRetrievalError("ClinVar search response was malformed")
    return [item for item in result["idlist"] if isinstance(item, str)]


def _summary_records(ids: list[str], timeout: float) -> list[dict[str, Any]]:
    if not ids:
        return []
    query = urlencode({"db": "clinvar", "id": ",".join(ids), "retmode": "json"})
    payload = _request_json(f"{CLINVAR_EUTILS_URL}/esummary.fcgi?{query}", timeout)
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("uids"), list):
        raise ClinVarRetrievalError("ClinVar summary response was malformed")
    records = []
    for uid in result["uids"]:
        record = result.get(uid)
        if isinstance(record, dict):
            records.append(record)
    return records


def _matches_variant(record: dict[str, Any], gene: str, hgvs_notation: str) -> bool:
    requested = hgvs_notation.lower()

    def matches(value: object) -> bool:
        if not isinstance(value, str):
            return False
        candidate = value.lower()
        if requested == candidate:
            return True
        return (
            requested.startswith(candidate)
            and candidate.endswith(("dup", "del", "ins"))
            and requested[len(candidate) :] != ""
            and all(base in "acgt" for base in requested[len(candidate) :])
        )

    title = record.get("title")
    if isinstance(title, str) and matches(title.split(":", 1)[-1].split(" ", 1)[0]):
        return True
    variation_set = record.get("variation_set")
    if not isinstance(variation_set, list):
        return False
    for variation in variation_set:
        if not isinstance(variation, dict):
            continue
        for key in ("variation_name", "cdna_change"):
            value = variation.get(key)
            if matches(value):
                return True
    return False


def normalize_clinvar_record(record: dict[str, Any]) -> RetrievedEvidence:
    accession = record.get("accession") or record.get("accession_version")
    if not isinstance(accession, str) or not accession:
        raise ClinVarRetrievalError("ClinVar record has no accession")

    classification_data = record.get("germline_classification")
    if not isinstance(classification_data, dict):
        classification_data = {}
    classification = classification_data.get("description")
    review_status = classification_data.get("review_status")
    last_evaluated = classification_data.get("last_evaluated")
    classification = classification if isinstance(classification, str) and classification else None
    review_status = review_status if isinstance(review_status, str) and review_status else None
    last_evaluated = last_evaluated if isinstance(last_evaluated, str) and last_evaluated else None

    details = []
    if classification:
        details.append(f"Asserted classification: {classification}.")
    if review_status:
        details.append(f"Review status: {review_status}.")
    if last_evaluated:
        details.append(f"Last evaluated: {last_evaluated}.")
    if not details:
        details.append("ClinVar record found; no germline classification was provided.")

    return RetrievedEvidence(
        evidence_id=f"clinvar-{accession}",
        source=CLINVAR_SOURCE,
        source_ref=accession,
        summary=" ".join(details),
        classification=classification,
        review_status=review_status,
        last_evaluated=last_evaluated,
    )


def retrieve_clinvar_evidence(
    gene: str,
    hgvs_notation: str,
    *,
    timeout: float = 10.0,
) -> EvidenceRetrievalResult:
    ids = _search_ids(gene, hgvs_notation, timeout)
    records = _summary_records(ids, timeout)
    evidence = tuple(
        normalize_clinvar_record(record)
        for record in records
        if _matches_variant(record, gene, hgvs_notation)
    )
    if not evidence:
        return EvidenceRetrievalResult(
            source=CLINVAR_SOURCE,
            status="not_found",
            evidence=(),
            message="No matching public evidence found",
        )
    return EvidenceRetrievalResult(
        source=CLINVAR_SOURCE,
        status="found",
        evidence=evidence,
        message=f"Found {len(evidence)} ClinVar record(s)",
    )
