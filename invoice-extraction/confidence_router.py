"""Confidence-based human review routing (Scenario 6 step 7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_THRESHOLD = 0.75


@dataclass
class RoutingDecision:
    auto_approve: bool
    human_review_fields: list[str]
    reason: str


def route_by_confidence(
    extraction: dict[str, Any],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> RoutingDecision:
    confidence = extraction.get("confidence") or {}
    low: list[str] = []

    for field in ("vendor", "invoice_date", "line_items", "stated_total"):
        score = confidence.get(field)
        if score is None or float(score) < threshold:
            low.append(field)

    notes = (extraction.get("notes") or "").lower()
    if "total_mismatch" in notes or "mismatch" in notes:
        return RoutingDecision(
            auto_approve=False,
            human_review_fields=sorted(set(low + ["stated_total", "line_items"])),
            reason="total_mismatch flagged during self-correction",
        )

    if low:
        return RoutingDecision(
            auto_approve=False,
            human_review_fields=low,
            reason=f"field confidence below {threshold}",
        )

    return RoutingDecision(
        auto_approve=True,
        human_review_fields=[],
        reason="all fields meet confidence threshold",
    )


def split_batch_results(
    extractions: list[dict[str, Any]], *, threshold: float = DEFAULT_THRESHOLD
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    auto: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for row in extractions:
        decision = route_by_confidence(row, threshold=threshold)
        tagged = {**row, "_routing": decision.__dict__}
        if decision.auto_approve:
            auto.append(tagged)
        else:
            review.append(tagged)
    return auto, review
