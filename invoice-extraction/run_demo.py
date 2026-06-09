"""End-to-end offline demo — no API key required."""

from __future__ import annotations

import json

from batch_process import dry_run_batch
from confidence_router import route_by_confidence, split_batch_results
from validate import validate_extraction

GOOD = {
    "vendor": "Northwind Traders",
    "invoice_date": "2024-06-01",
    "invoice_number": "NW-8842",
    "currency": "USD",
    "line_items": [
        {"description": "Cable pack", "quantity": 3, "unit_price": 8.0, "line_total": 24.0},
        {"description": "Adapter", "quantity": 1, "unit_price": 12.0, "line_total": 12.0},
    ],
    "stated_total": 36.0,
    "calculated_total": 36.0,
    "confidence": {
        "vendor": 0.95,
        "invoice_date": 0.9,
        "line_items": 0.92,
        "stated_total": 0.93,
    },
    "notes": None,
}

MISSING_VENDOR = {
    **GOOD,
    "vendor": None,
    "confidence": {**GOOD["confidence"], "vendor": 0.4},
}

MISMATCH = {
    **GOOD,
    "stated_total": 999.0,
    "calculated_total": 36.0,
    "confidence": {**GOOD["confidence"], "stated_total": 0.5},
    "notes": "total_mismatch",
}


def main() -> None:
    print("=== Step 3 self-correction (good) ===")
    print(json.dumps(validate_extraction(GOOD).__dict__, indent=2))

    print("\n=== Step 3 self-correction (mismatch) ===")
    print(json.dumps(validate_extraction(MISMATCH).__dict__, indent=2))

    print("\n=== Step 7 confidence routing ===")
    for label, row in [("good", GOOD), ("missing vendor", MISSING_VENDOR), ("mismatch", MISMATCH)]:
        decision = route_by_confidence(row)
        print(label, json.dumps(decision.__dict__))

    auto, review = split_batch_results([GOOD, MISSING_VENDOR, MISMATCH])
    print(f"\nBatch split: {len(auto)} auto, {len(review)} human review")

    print("\n=== Step 6 batch dry-run (100 docs) ===")
    preview = dry_run_batch(100)
    print(f"request_count={preview['request_count']} sample_ids={preview['sample_custom_ids']}")


if __name__ == "__main__":
    main()
