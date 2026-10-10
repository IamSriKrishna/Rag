from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RetrievalMetrics:
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    hit_rate: float


def evaluate_retrieval(
    retrieved_chunk_ids: Iterable[str],
    relevant_chunk_ids: Iterable[str],
    k: int,
) -> RetrievalMetrics:
    if k <= 0:
        raise ValueError("k must be greater than zero")
    retrieved = list(retrieved_chunk_ids)[:k]
    relevant = set(relevant_chunk_ids)
    if not relevant:
        raise ValueError("relevant_chunk_ids must not be empty")
    hits = [chunk_id for chunk_id in retrieved if chunk_id in relevant]
    precision = len(hits) / k
    recall = len(set(hits)) / len(relevant)
    reciprocal_rank = next(
        (
            1.0 / rank
            for rank, chunk_id in enumerate(retrieved, start=1)
            if chunk_id in relevant
        ),
        0.0,
    )
    return RetrievalMetrics(
        precision_at_k=precision,
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
        hit_rate=1.0 if hits else 0.0,
    )


def evaluate_answer_contains_evidence(
    answer: str, expected_facts: Iterable[str]
) -> dict[str, float]:
    facts = [fact.strip().casefold() for fact in expected_facts if fact.strip()]
    if not facts:
        raise ValueError("expected_facts must contain at least one non-empty fact")
    answer_normalized = answer.casefold()
    matched = sum(fact in answer_normalized for fact in facts)
    return {
        "expected_fact_coverage": matched / len(facts),
        "expected_fact_count": float(len(facts)),
        "matched_fact_count": float(matched),
    }
