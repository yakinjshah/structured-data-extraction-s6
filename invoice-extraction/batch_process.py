"""Message Batches API overnight processing (Scenario 6 step 6)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from extract import EXTRACT_INVOICE_TOOL, build_messages, load_prompt_bundle

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "sample_invoices"


def batch_requests_for_invoices(
    invoices: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Build batch requests with stable custom_id per invoice."""
    system, few_shot = load_prompt_bundle()
    requests: list[dict[str, Any]] = []
    for custom_id, text in invoices:
        requests.append(
            {
                "custom_id": custom_id,
                "params": {
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 1024,
                    "system": f"{system}\n\n{few_shot}",
                    "tools": [EXTRACT_INVOICE_TOOL],
                    "tool_choice": {"type": "tool", "name": "extract_invoice"},
                    "messages": build_messages(text),
                },
            }
        )
    return requests


def load_sample_batch(limit: int = 100) -> list[tuple[str, str]]:
    files = sorted(SAMPLES.glob("*.txt"))
    rows: list[tuple[str, str]] = []
    for i in range(limit):
        path = files[i % len(files)]
        rows.append((f"INV-{i + 1:03d}", path.read_text(encoding="utf-8")))
    return rows


def resubmit_failed_only(
    all_results: list[dict[str, Any]],
    invoices_by_id: dict[str, str],
) -> list[dict[str, Any]]:
    """Re-queue only errored custom_id entries instead of reprocessing the full batch."""
    retry: list[dict[str, Any]] = []
    for row in all_results:
        if row.get("result", {}).get("type") != "error":
            continue
        cid = row.get("custom_id")
        if cid and cid in invoices_by_id:
            retry.extend(batch_requests_for_invoices([(cid, invoices_by_id[cid])]))
    return retry


def dry_run_batch(limit: int = 100) -> dict[str, Any]:
    invoices = load_sample_batch(limit)
    return {
        "request_count": len(invoices),
        "sample_custom_ids": [cid for cid, _ in invoices[:5]],
        "requests": batch_requests_for_invoices(invoices[:3]),
    }


def submit_batch(limit: int = 100) -> str:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY required for live batch submit")

    client = anthropic.Anthropic(api_key=api_key)
    invoices = load_sample_batch(limit)
    requests = batch_requests_for_invoices(invoices)
    batch = client.messages.batches.create(requests=requests)
    return batch.id


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    if args.dry_run:
        print(json.dumps(dry_run_batch(args.limit), indent=2))
    else:
        print(submit_batch(args.limit))
