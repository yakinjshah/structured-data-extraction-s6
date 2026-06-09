"""
Invoice extraction pipeline (Scenario 6 steps 1–4).

- Step 1: extraction tool + JSON schema + forced tool_choice
- Step 2: nullable optional fields (vendor, date, etc.)
- Step 3: self-correction via stated_total vs calculated_total
- Step 4: validation-retry loop with targeted error feedback
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from validate import ValidationResult, build_retry_user_message, validate_extraction

ROOT = Path(__file__).resolve().parent

EXTRACT_INVOICE_TOOL: dict[str, Any] = {
    "name": "extract_invoice",
    "description": "Extract structured invoice fields from raw text.",
    "input_schema": {
        "type": "object",
        "required": [
            "invoice_number",
            "stated_total",
            "calculated_total",
            "line_items",
            "confidence",
        ],
        "properties": {
            "vendor": {"type": ["string", "null"]},
            "invoice_date": {"type": ["string", "null"]},
            "invoice_number": {"type": ["string", "null"]},
            "currency": {
                "type": ["string", "null"],
                "enum": ["USD", "EUR", "GBP", "INR", None],
            },
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["description", "quantity", "unit_price", "line_total"],
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "number"},
                        "line_total": {"type": "number"},
                    },
                },
            },
            "stated_total": {"type": ["number", "null"]},
            "calculated_total": {"type": ["number", "null"]},
            "confidence": {
                "type": "object",
                "required": ["vendor", "invoice_date", "line_items", "stated_total"],
                "properties": {
                    "vendor": {"type": "number"},
                    "invoice_date": {"type": "number"},
                    "line_items": {"type": "number"},
                    "stated_total": {"type": "number"},
                },
            },
            "notes": {"type": ["string", "null"]},
        },
    },
}


def load_prompt_bundle() -> tuple[str, str]:
    system = (ROOT / "prompts" / "system.txt").read_text(encoding="utf-8")
    few_shot = (ROOT / "prompts" / "few_shot_examples.txt").read_text(encoding="utf-8")
    return system, few_shot


def build_messages(document: str) -> list[dict[str, str]]:
    return [
        {
            "role": "user",
            "content": f"Extract invoice fields from this document:\n\n{document}",
        }
    ]


def parse_tool_output(response: Any) -> dict[str, Any] | None:
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_invoice":
            return dict(block.input)
    return None


def extract_with_client(
    client: Any,
    document: str,
    *,
    max_retries: int = 3,
) -> tuple[dict[str, Any], ValidationResult]:
    system, few_shot = load_prompt_bundle()
    messages = build_messages(document)
    last_data: dict[str, Any] = {}
    last_result = ValidationResult(False, ["no attempts"])

    for attempt in range(max_retries):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=f"{system}\n\n{few_shot}",
            tools=[EXTRACT_INVOICE_TOOL],
            tool_choice={"type": "tool", "name": "extract_invoice"},
            messages=messages,
        )
        data = parse_tool_output(response)
        if not data:
            last_result = ValidationResult(False, ["model did not call extract_invoice"])
            continue

        last_data = data
        last_result = validate_extraction(data)
        if last_result.ok:
            return data, last_result

        if attempt + 1 < max_retries:
            messages = [
                {
                    "role": "user",
                    "content": build_retry_user_message(document, data, last_result.errors),
                }
            ]

    return last_data, last_result


def extract_document(document: str, *, max_retries: int = 3) -> dict[str, Any]:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY required for live extraction")

    client = anthropic.Anthropic(api_key=api_key)
    data, result = extract_with_client(client, document, max_retries=max_retries)
    return {"extraction": data, "validation": result.__dict__}


if __name__ == "__main__":
    import sys

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sample_invoices" / "table_format.txt"
    print(json.dumps(extract_document(path.read_text(encoding="utf-8")), indent=2))
