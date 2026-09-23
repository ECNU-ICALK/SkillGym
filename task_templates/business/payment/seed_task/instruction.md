You need to organize a set of vendor documents for this Accounts Payable payment batch and deliver an auditable batch result.

Input data is under `/root/data/`:

- `inbox/`: the input documents folder, containing documents within the scope of this review.
- `vendor_master.csv`: vendor master data, including canonical vendor names, aliases, expense categories, and default payment terms.
- `settlement_snapshot.csv`: an older export of payment status; may be missing entries or stale.
- `batch_context.json`: the batch id, cutoff date, and the entrypoint for the in-container ap review service.
- `filing_policy.yaml`: rules for document naming, output paths, duplicate detection, and manual review.

## Your Task

1. Based on all input documents, produce a complete document register.
2. Using vendor master data, the batch scope, the rules file, and the current results from the ap review service, decide whether each document is eligible for inclusion in the current payment batch.
3. For each input document, generate a rules-compliant output file path and prepare the corresponding organized file.
4. Summarize the payable documents and their amounts for the current batch, and write a short batch brief.

## Output

If `/root/output/` does not exist, create it first.

Write `/root/output/invoice_register.csv`. The column names must be exactly:

```csv
source_file,document_type,vendor_name_observed,vendor_name_canonical,invoice_number,invoice_date,due_date,currency,total_amount,tax_amount,expense_category,payment_status,eligible_for_batch,exclusion_reason,organized_relative_path
```

Requirements:

- `source_file` must preserve the relative path under the input directory.
- Each input file must appear exactly once in `invoice_register.csv`.
- `document_type` must be `invoice`, `receipt`, `credit_note`, or `other`.
- `invoice_date` and `due_date` use `YYYY-MM-DD`; if unknown, write an empty string.
- `total_amount` and `tax_amount` must be decimal numbers without currency symbols; if unknown, write an empty string.
- `payment_status` must be based on the current ap review service result and must be one of `unpaid`, `paid`, `credit`, or `unknown`.
- `eligible_for_batch` must be `true` or `false`.
- `exclusion_reason` must be an empty string or one of:
  - `already_paid`
  - `credit_note`
  - `duplicate_document`
  - `outside_batch_cutoff`
  - `missing_key_fields`
  - `manual_review_required`
- `organized_relative_path` must be the relative path (under `/root/output/`) of the organized document file.
- The organized file path and file name must satisfy `filing_policy.yaml`.
- If the rules require using an invoice number but it cannot be determined from the document, follow the fallback rules in `filing_policy.yaml`.
- The organized file must keep the original extension.

Write `/root/output/payment_batch.json` with the following structure:

```json
{
  "batch_id": "AP-000",
  "cutoff_date": "YYYY-MM-DD",
  "payable_documents": [
    {
      "source_file": "inbox/example.pdf",
      "vendor_name_canonical": "Example Vendor",
      "invoice_number": "INV-001",
      "due_date": "YYYY-MM-DD",
      "currency": "USD",
      "total_amount": 0.0,
      "expense_category": "cloud-infrastructure",
      "organized_relative_path": "organized/example.pdf"
    }
  ],
  "excluded_documents": [
    {
      "source_file": "inbox/example.pdf",
      "reason": "duplicate_document",
      "note": "Short explanation"
    }
  ],
  "currency_totals": [
    {
      "currency": "USD",
      "document_count": 0,
      "total_amount": 0.0
    }
  ],
  "service_checks": {
    "manifest": true,
    "documents": true,
    "document_reviews": true
  },
  "notes": [
    "Example note"
  ]
}
```

Requirements:

- `payable_documents` may include only documents with `eligible_for_batch = true`.
- `excluded_documents` must cover all documents with `eligible_for_batch = false`.
- `currency_totals` must summarize only `payable_documents`.
- `document_count` must match the number of `payable_documents` for the given currency.
- All 3 fields in `service_checks` must be `true`.
- All amount fields must be JSON numbers (not strings).
- `notes` must contain at least 2 brief batch notes.

Write `/root/output/batch_review.md`. The content must include:

- the batch id;
- the total number of reviewed documents in scope;
- the total number of payable documents in the batch;
- the list of documents excluded from the batch;
- the documents requiring manual review;
- the duplicate documents;
- the per-currency totals;
- a brief explanation of the data checks and inclusion logic used.

## Business Constraints

1. File names under `inbox/` are hints only; the document content, `vendor_master.csv`, `batch_context.json`, `filing_policy.yaml`, and the ap review service are the primary sources.
2. `inbox/` contains multiple nested directories; you must process input files recursively in all subdirectories, not just the top level.
3. Prefer the labeled invoice number field on the document, such as `Invoice Number`, `Invoice No`, `Facture n°`, `Rechnungsnr.`, `Factuurnummer`; do not substitute order numbers, customer numbers, product codes, or serial numbers.
4. If a document is missing a due date, but the vendor master provides default payment terms, derive and fill the due date accordingly.
5. Within the same duplicate group, both the kept item and the duplicate item must use a standard path that complies with `filing_policy.yaml`; do not append custom suffixes such as `COPY`, `duplicate`, or other ad-hoc tags.
6. Paid documents, credit notes, duplicate documents, documents requiring manual review, or documents outside the batch scope must not be included in `payable_documents`.
7. Documents whose key fields cannot be determined reliably must still be kept in the register and marked as not eligible for the current batch.
8. You may write results only under `/root/output/`; you must not delete, rewrite, or move any input files under `/root/data/`.
9. `settlement_snapshot.csv` is background reference only and must not replace the current ap review service.
10. Different spellings/variants for the same vendor must be normalized to `vendor_name_canonical`.

## Notes

- Do not modify any files under `/root/data/`.
- Do not skip any input files, and do not process only part of the directory tree.
- Do not treat the older snapshot export as the only source of truth, and do not bypass the in-container ap review service.
- Do not replace the real processing with hard-coded results, fabricated fields, or a manually invented batch list.
- Do not modify tests, verifier, task metadata, environment files, or anything under any `skills` directory.
- You may write helper scripts in the working directory, but the only required deliverables are the 3 files under `/root/output/`.
