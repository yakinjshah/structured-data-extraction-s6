# Invoice extraction pipeline (Scenario 6)

Student work for CCA-F Structured Data Extraction — built on top of the anthropic-cookbook fork.

## Steps implemented

1. **Extraction tool + JSON schema** — `schema/invoice.schema.json`, `extract.py` (`EXTRACT_INVOICE_TOOL`, forced `tool_choice`)
2. **Nullable missing fields** — optional vendor/date/line_items return `null`, never invented
3. **Self-correction** — `validate.py` compares `stated_total` vs `calculated_total`
4. **Validation-retry loop** — `extract.py` resends document + failed JSON + specific error (max 3 tries)
5. **Few-shot examples** — `prompts/few_shot_examples.txt` (inline list, table, narrative layouts)
6. **Batch processing** — `batch_process.py` uses Message Batches API; retries failed `custom_id` only
7. **Confidence routing** — `confidence_router.py` sends low-confidence fields to human review queue

## Quick demo (no API key)

```bash
cd invoice-extraction
python run_demo.py
```

## Live extraction (requires `ANTHROPIC_API_KEY`)

```bash
python extract.py sample_invoices/table_format.txt
python batch_process.py --dry-run   # prints batch request shape
```
