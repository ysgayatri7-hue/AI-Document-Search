import re
from dataclasses import dataclass

from app.models.entities import VerificationStatus


@dataclass(frozen=True)
class Verification:
    status: VerificationStatus
    rationale: str
    evidence_indexes: list[int]


def split_claims(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 12]


def verify_claim(claim: str, evidence: list[str]) -> Verification:
    significant = {w for w in re.findall(r"[a-z0-9]+", claim.lower()) if len(w) > 3}
    if not significant or not evidence:
        return Verification(VerificationStatus.unsupported, "No adequate evidence passage was available.", [])
    scores = []
    for index, passage in enumerate(evidence):
        words = set(re.findall(r"[a-z0-9]+", passage.lower()))
        overlap = len(significant & words) / len(significant)
        negated = bool({"not", "never", "no"} & words) != bool({"not", "never", "no"} & set(claim.lower().split()))
        scores.append((overlap, negated, index))
    overlap, negated, index = max(scores)
    if overlap >= 0.65 and negated:
        return Verification(VerificationStatus.contradicted, "The closest passage uses conflicting negation.", [index])
    if overlap >= 0.65:
        return Verification(VerificationStatus.supported, "The claim has strong lexical support in the cited passage.", [index])
    if overlap >= 0.35:
        return Verification(VerificationStatus.partially_supported, "The passage supports only part of the claim.", [index])
    return Verification(VerificationStatus.unsupported, "Retrieved passages do not adequately support this claim.", [])


def validate_citation(chunk_id: str, page_number: int, available: dict, document_id: str | None = None) -> bool:
    if chunk_id not in available:
        return False
    stored = available[chunk_id]
    if isinstance(stored, tuple):
        stored_page, stored_document = stored
        return stored_page == page_number and (document_id is None or stored_document == document_id)
    return stored == page_number

