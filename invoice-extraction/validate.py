"""Validation helpers for invoice extraction (Scenario 6 steps 3–4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]


def sum_line_items(line_items: list[dict[str, Any]]) -> float:
    total = 0.0
    for item in line_items:
        total += float(item.get("line_total") or 0)
    return round(total, 2)


def validate_extraction(data: dict[str, Any]) -> ValidationResult:
    """Self-correction: flag when stated_total != calculated_total."""
    errors: list[str] = []
    line_items = data.get("line_items") or []
    if not isinstance(line_items, list):
        errors.append("line_items must be an array")
        return ValidationResult(False, errors)

    computed = sum_line_items(line_items)
    stated = data.get("stated_total")
    recorded_calc = data.get("calculated_total")

    if recorded_calc is not None and abs(float(recorded_calc) - computed) > 0.01:
        errors.append(
            f"calculated_total {recorded_calc} does not match line item sum {computed}"
        )

    if stated is not None and abs(float(stated) - computed) > 0.01:
        errors.append(
            f"stated_total {stated} does not match line item sum {computed} (total_mismatch)"
        )

    confidence = data.get("confidence") or {}
    for field in ("vendor", "invoice_date", "line_items", "stated_total"):
        score = confidence.get(field)
        if score is not None and not (0 <= float(score) <= 1):
            errors.append(f"confidence.{field} must be between 0 and 1")

    return ValidationResult(len(errors) == 0, errors)


def build_retry_user_message(
    document: str, failed: dict[str, Any], errors: list[str]
) -> str:
    """Targeted retry payload (step 4): document + failed extraction + specific errors."""
    err_text = "; ".join(errors)
    return (
        "Your previous extraction failed validation.\n"
        f"Validation errors: {err_text}\n\n"
        f"Failed extraction JSON:\n{failed}\n\n"
        "Re-read the invoice and fix only the incorrect fields. "
        "Return null for missing values; do not invent data.\n\n"
        f"Invoice document:\n{document}"
    )
