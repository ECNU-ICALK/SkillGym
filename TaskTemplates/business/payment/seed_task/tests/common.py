from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pypdf
import yaml


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))
SERVICE_ROOT = Path(os.environ.get("TASK_SERVICE_ROOT", "/services/ap-review"))

REGISTER_PATH = OUTPUT_ROOT / "invoice_register.csv"
BATCH_PATH = OUTPUT_ROOT / "payment_batch.json"
REVIEW_PATH = OUTPUT_ROOT / "batch_review.md"

REGISTER_FIELDS = [
    "source_file",
    "document_type",
    "vendor_name_observed",
    "vendor_name_canonical",
    "invoice_number",
    "invoice_date",
    "due_date",
    "currency",
    "total_amount",
    "tax_amount",
    "expense_category",
    "payment_status",
    "eligible_for_batch",
    "exclusion_reason",
    "organized_relative_path",
]

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "janvier": 1,
    "fevrier": 2,
    "fevr": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}


def load_batch_context() -> dict:
    return json.loads((DATA_ROOT / "batch_context.json").read_text(encoding="utf-8"))


def load_policy() -> dict:
    return yaml.safe_load((DATA_ROOT / "filing_policy.yaml").read_text(encoding="utf-8"))


def load_vendor_rows() -> list[dict]:
    with (DATA_ROOT / "vendor_master.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_live_review_fixture() -> list[dict]:
    payload = json.loads((SERVICE_ROOT / "live_review.json").read_text(encoding="utf-8"))
    return payload["documents"]


def load_register_rows() -> list[dict]:
    with REGISTER_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_batch_payload() -> dict:
    return json.loads(BATCH_PATH.read_text(encoding="utf-8"))


def normalize_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError(f"Invalid bool value: {value}")


def strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def search_required(text: str, *patterns: str) -> re.Match[str]:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match
    raise AssertionError(f"Pattern not found. Tried: {patterns}")


def slugify(text: str, *, lowercase: bool = True, uppercase: bool = False) -> str:
    ascii_text = strip_accents(text)
    if uppercase:
        ascii_text = ascii_text.upper()
    elif lowercase:
        ascii_text = ascii_text.lower()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "item"


def parse_decimal(token: str) -> Decimal:
    cleaned = token.replace("€", "").replace("$", "").replace("PLN", "").replace(",", ".").strip()
    return Decimal(cleaned)


def decimal_to_str(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value.quantize(Decimal("0.01")), "f")


def parse_date_token(token: str) -> str:
    raw = normalize_space(token.replace(" ,", ",").replace("  ", " "))
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    compact = raw.replace(",", "")
    try:
        return datetime.strptime(compact, "%B %d %Y").date().isoformat()
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{1,2})\.?\s+([A-Za-zÀ-ÿ]+)\s+(\d{2,4})", raw)
    if not match:
        raise ValueError(f"Unsupported date token: {token}")
    day = int(match.group(1))
    month_word = strip_accents(match.group(2)).lower()
    year = int(match.group(3))
    if year < 100:
        year += 2000
    month = MONTHS[month_word]
    return date(year, month, day).isoformat()


def read_document_text(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return normalize_space(path.read_text(encoding="utf-8"))
    reader = pypdf.PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return normalize_space(text)


def vendor_lookup() -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for row in load_vendor_rows():
        candidates = [row["canonical_vendor"], *row["aliases"].split("|")]
        for candidate in candidates:
            lookup[candidate.lower()] = row
    return lookup


def resolve_vendor(observed: str) -> dict:
    lowered = observed.lower()
    for row in load_vendor_rows():
        candidates = [row["canonical_vendor"], *row["aliases"].split("|")]
        if any(candidate.lower() in lowered or lowered in candidate.lower() for candidate in candidates):
            return row
    raise KeyError(f"No vendor mapping for {observed}")


def same_vendor_alias(observed: str, canonical_vendor: str) -> bool:
    try:
        row = resolve_vendor(observed)
    except KeyError:
        return False
    return row["canonical_vendor"] == canonical_vendor


def extract_document_fields(source_file: str) -> dict:
    path = DATA_ROOT / source_file
    text = read_document_text(path)

    if source_file.endswith("statement-2014-08.pdf") or source_file.endswith("aws-statement-duplicate.pdf"):
        due_match = search_required(
            text,
            r"TOTAL AMOUNT DUE ON\s+([A-Za-z]+\s+\d+\s*,\s*\d{4})\s+\$([0-9]+\.[0-9]{2})",
        )
        invoice_date = parse_date_token(
            search_required(
                text,
                r"Invoice Date:\s*([A-Za-z]+\s+\d+\s*,\s*\d{4})",
            ).group(1)
        )
        due_date = parse_date_token(due_match.group(1))
        return {
            "document_type": "invoice",
            "vendor_name_observed": "Amazon Web Services, Inc.",
            "invoice_number": search_required(text, r"Invoice Number:\s*([0-9]+)").group(1),
            "invoice_date": invoice_date,
            "due_date": due_date,
            "currency": "USD",
            "total_amount": parse_decimal(due_match.group(2)),
            "tax_amount": None,
        }

    if source_file.endswith("q1-office-renewal.pdf"):
        return {
            "document_type": "invoice",
            "vendor_name_observed": "Azure Interior",
            "invoice_number": search_required(text, r"(INV/\d{4}/\d{2}/\d{4})").group(1),
            "invoice_date": parse_date_token(search_required(text, r"Invoice Date:\s*([0-9/]+)").group(1)),
            "due_date": parse_date_token(search_required(text, r"Due Date:\s*([0-9/]+)").group(1)),
            "currency": "USD",
            "total_amount": parse_decimal(search_required(text, r"Total\s+\$\s*([0-9]+\.[0-9]{2})").group(1)),
            "tax_amount": parse_decimal(
                search_required(text, r"Tax 15%\s+on\s+\$\s*[0-9]+\.[0-9]{2}\s+\$\s*([0-9]+\.[0-9]{2})").group(1)
            ),
        }

    if source_file.endswith("card-accessory-bill.pdf"):
        return {
            "document_type": "invoice",
            "vendor_name_observed": "WS Retail Services Pvt. Ltd.",
            "invoice_number": search_required(text, r"Invoice No : #\s*([A-Z0-9_]+)").group(1),
            "invoice_date": parse_date_token(
                search_required(
                    text,
                    r"(\d{2}-\d{2}-\d{4})\s+Invoice Date:",
                    r"(\d{2}-\d{2}-\d{4})\s*Invoice Date:",
                ).group(1)
            ),
            "due_date": "",
            "currency": "INR",
            "total_amount": parse_decimal(search_required(text, r"Grand Total\s+([0-9]+\.[0-9]{2})").group(1)),
            "tax_amount": parse_decimal(
                search_required(
                    text,
                    r"CST\s*([0-9]+\.[0-9]{2})\s+319\.00",
                    r"14\.50%\s*CST\s*([0-9]+\.[0-9]{2})\s+319\.00",
                ).group(1)
            ),
        }

    if source_file.endswith("netpresse-publication-invoice.pdf"):
        return {
            "document_type": "invoice",
            "vendor_name_observed": "NETPRESSE",
            "invoice_number": search_required(text, r"Facture n°\s*([0-9]+)").group(1),
            "invoice_date": parse_date_token(search_required(text, r"Date :\s*([0-9]{2}/[0-9]{2}/[0-9]{4})").group(1)),
            "due_date": "",
            "currency": "EUR",
            "total_amount": parse_decimal(search_required(text, r"Total TTC :\s*([0-9]+,\d{2})").group(1)),
            "tax_amount": parse_decimal(search_required(text, r"TVA 20% :\s*([0-9]+,\d{2})").group(1)),
        }

    if source_file.endswith("mail-hosting-may.pdf"):
        invoice_number_match = search_required(
            text,
            r"7\.\s*Mai\s*2014\s*([0-9]{5})\s*Rechnung",
            r"Rechnungsdatum.*?([0-9]{5})\s*Rechnung",
            r"Rechnungsnr\.\s*.*?([0-9]{5})",
            r"([0-9]{5})\s*Rechnung",
        )
        invoice_date_match = search_required(
            text,
            r"(\d{1,2}\.\s*[A-Za-zÀ-ÿ]+\s+\d{4})",
        )
        due_date_match = search_required(
            text,
            r"Zahlungsziel\s*([0-9]{2}\.[0-9]{2}\.[0-9]{2})",
        )
        total_match = search_required(
            text,
            r"Total\s+EUR\s*([0-9]+,\d{2})",
            r"EUR\s*([0-9]+,\d{2})\s*Pos\.",
        )
        return {
            "document_type": "invoice",
            "vendor_name_observed": "QualityHosting AG",
            "invoice_number": invoice_number_match.group(1),
            "invoice_date": parse_date_token(invoice_date_match.group(1)),
            "due_date": parse_date_token(due_date_match.group(1)),
            "currency": "EUR",
            "total_amount": parse_decimal(total_match.group(1)),
            "tax_amount": None,
        }

    if source_file.endswith("fiber-july.pdf"):
        return {
            "document_type": "invoice",
            "vendor_name_observed": "Free Service Abonné",
            "invoice_number": search_required(text, r"Facture n°\s*([0-9]+)").group(1),
            "invoice_date": parse_date_token(
                search_required(text, r"Facture n°[0-9]+\s+du\s+([0-9]{2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})").group(1)
            ),
            "due_date": parse_date_token(
                search_required(text, r"Date limite de paiement le\s+([0-9]{2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})").group(1)
            ),
            "currency": "EUR",
            "total_amount": parse_decimal(
                search_required(text, r"Somme à payer.*?([0-9]+\.[0-9]{2})\s*€ TTC").group(1)
            ),
            "tax_amount": parse_decimal(
                search_required(
                    text,
                    r"([0-9]+\.[0-9]{2})\s*TVA 20%",
                    r"TVA 20%\s*pay[ée]e?\s*sur.*?([0-9]+\.[0-9]{2})",
                ).group(1)
            ),
        }

    if source_file.endswith("hardware-order.pdf"):
        invoice_number_match = search_required(
            text,
            r"Factuurnummer:\s*([0-9]+)",
        )
        invoice_date_match = search_required(
            text,
            r"([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})\s*Factuurdatum",
            r"([0-9]{1,2}\s+[A-Za-zÀ-ÿ]+\s+[0-9]{4})Factuurdatum",
        )
        total_match = search_required(
            text,
            r"Totaal\s*€\s*([0-9]+,\d{2})",
            r"Totaal€\s*([0-9]+,\d{2})",
        )
        tax_match = search_required(
            text,
            r"BTW\s*21%\s*€\s*([0-9]+,\d{2})",
            r"BTW 21%€\s*([0-9]+,\d{2})",
        )
        return {
            "document_type": "invoice",
            "vendor_name_observed": "Coolblue B.V.",
            "invoice_number": invoice_number_match.group(1),
            "invoice_date": parse_date_token(invoice_date_match.group(1)),
            "due_date": "",
            "currency": "EUR",
            "total_amount": parse_decimal(total_match.group(1)),
            "tax_amount": parse_decimal(tax_match.group(1)),
        }

    if source_file.endswith("mobile-pay.txt"):
        return {
            "document_type": "invoice",
            "vendor_name_observed": "Polski Koncern Naftowy ORLEN S.A.",
            "invoice_number": normalize_space(
                search_required(text, r"Faktura nr:\s*(.*?)\s+Data wystawienia:").group(1)
            ),
            "invoice_date": parse_date_token(search_required(text, r"Data wystawienia:\s*([0-9-]{10})").group(1)),
            "due_date": "",
            "currency": "PLN",
            "total_amount": parse_decimal(
                search_required(text, r"Należność ogółem:\s*([0-9]+,\d{2})\s*PLN").group(1)
            ),
            "tax_amount": parse_decimal(
                search_required(
                    text,
                    r"Razem:\s*[0-9]+,\d{2}\s*([0-9]+,\d{2})\s*[0-9]+,\d{2}",
                    r"w tym:\s*[0-9]+,\d{2}\s+23\s+([0-9]+,\d{2})\s+[0-9]+,\d{2}",
                ).group(1)
            ),
        }

    raise AssertionError(f"Unhandled source file {source_file}")


def apply_due_date(default_terms_days: int, invoice_date: str, due_date: str) -> str:
    if due_date:
        return due_date
    if not invoice_date:
        return ""
    base = date.fromisoformat(invoice_date)
    return (base + timedelta(days=default_terms_days)).isoformat()


def build_organized_path(row: dict) -> str:
    policy = load_policy()
    invoice_date = row["invoice_date"] or policy["invoice_date_fallback"]
    ext = Path(row["source_file"]).suffix
    reference = row["invoice_number"] or policy["reference_fallback"]
    reference_sanitized = slugify(reference, lowercase=False, uppercase=True)
    vendor_slug = slugify(row["vendor_name_canonical"], lowercase=True)
    filename = policy["filename_template"].format(
        invoice_date=invoice_date,
        vendor_name_canonical=row["vendor_name_canonical"],
        document_type=row["document_type"],
        reference_sanitized=reference_sanitized,
        ext=ext,
    )
    return policy["path_template"].format(
        expense_category=row["expense_category"],
        vendor_slug=vendor_slug,
        filename=filename,
    )


def build_expected() -> dict:
    batch = load_batch_context()
    cutoff = batch["cutoff_date"]
    live_docs = load_live_review_fixture()
    live_by_source = {item["source_file"]: item for item in live_docs}

    extracted_rows = []
    for item in sorted(live_docs, key=lambda row: row["source_file"]):
        source_file = item["source_file"]
        extracted = extract_document_fields(source_file)
        vendor = resolve_vendor(extracted["vendor_name_observed"])
        invoice_date = extracted["invoice_date"]
        due_date = apply_due_date(int(vendor["default_terms_days"]), invoice_date, extracted["due_date"])
        extracted_rows.append(
            {
                "source_file": source_file,
                "document_type": extracted["document_type"],
                "vendor_name_observed": extracted["vendor_name_observed"],
                "vendor_name_canonical": vendor["canonical_vendor"],
                "invoice_number": extracted["invoice_number"],
                "invoice_date": invoice_date,
                "due_date": due_date,
                "currency": extracted["currency"],
                "total_amount_decimal": extracted["total_amount"],
                "tax_amount_decimal": extracted["tax_amount"],
                "expense_category": vendor["expense_category"],
                "payment_status": item["payment_status"],
                "manual_review_required": bool(item["manual_review_required"]),
                "review_note": item["review_note"],
            }
        )

    duplicate_groups: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    for row in extracted_rows:
        if row["vendor_name_canonical"] and row["invoice_number"] and row["currency"] and row["total_amount_decimal"] is not None:
            key = (
                row["vendor_name_canonical"],
                row["invoice_number"],
                row["currency"],
                decimal_to_str(row["total_amount_decimal"]),
            )
            duplicate_groups[key].append(row["source_file"])
    duplicate_primary: dict[str, str] = {}
    for source_files in duplicate_groups.values():
        if len(source_files) <= 1:
            continue
        primary = sorted(source_files)[0]
        for source_file in source_files:
            duplicate_primary[source_file] = primary

    register_rows = []
    for row in extracted_rows:
        exclusion_reason = ""
        if row["payment_status"] == "paid":
            exclusion_reason = "already_paid"
        elif row["payment_status"] == "credit":
            exclusion_reason = "credit_note"
        elif row["manual_review_required"]:
            exclusion_reason = "manual_review_required"
        elif row["source_file"] in duplicate_primary and duplicate_primary[row["source_file"]] != row["source_file"]:
            exclusion_reason = "duplicate_document"
        elif not all([row["vendor_name_canonical"], row["invoice_number"], row["invoice_date"], row["currency"]]) or row["total_amount_decimal"] is None:
            exclusion_reason = "missing_key_fields"
        elif row["due_date"] and row["due_date"] > cutoff:
            exclusion_reason = "outside_batch_cutoff"

        register_row = {
            "source_file": row["source_file"],
            "document_type": row["document_type"],
            "vendor_name_observed": row["vendor_name_observed"],
            "vendor_name_canonical": row["vendor_name_canonical"],
            "invoice_number": row["invoice_number"],
            "invoice_date": row["invoice_date"],
            "due_date": row["due_date"],
            "currency": row["currency"],
            "total_amount": decimal_to_str(row["total_amount_decimal"]),
            "tax_amount": decimal_to_str(row["tax_amount_decimal"]),
            "expense_category": row["expense_category"],
            "payment_status": row["payment_status"],
            "eligible_for_batch": exclusion_reason == "",
            "exclusion_reason": exclusion_reason,
        }
        register_row["organized_relative_path"] = build_organized_path(register_row)
        register_rows.append(register_row)

    payable_documents = []
    excluded_documents = []
    totals: dict[str, dict] = defaultdict(lambda: {"currency": "", "document_count": 0, "total_amount": Decimal("0.00")})
    duplicate_notes = []
    manual_review_notes = []

    for row in register_rows:
        if row["eligible_for_batch"]:
            payable_documents.append(
                {
                    "source_file": row["source_file"],
                    "vendor_name_canonical": row["vendor_name_canonical"],
                    "invoice_number": row["invoice_number"],
                    "due_date": row["due_date"],
                    "currency": row["currency"],
                    "total_amount": float(Decimal(row["total_amount"])),
                    "expense_category": row["expense_category"],
                    "organized_relative_path": row["organized_relative_path"],
                }
            )
            bucket = totals[row["currency"]]
            bucket["currency"] = row["currency"]
            bucket["document_count"] += 1
            bucket["total_amount"] += Decimal(row["total_amount"])
        else:
            live_item = live_by_source[row["source_file"]]
            if row["exclusion_reason"] == "duplicate_document":
                primary = duplicate_primary[row["source_file"]]
                note = f"Duplicate of {primary} under the filing policy."
                duplicate_notes.append(row["source_file"])
            elif row["exclusion_reason"] == "outside_batch_cutoff":
                note = f"Due date {row['due_date']} is after cutoff {cutoff}."
            else:
                note = live_item["review_note"]
            if row["exclusion_reason"] == "manual_review_required":
                manual_review_notes.append(row["source_file"])
            excluded_documents.append(
                {
                    "source_file": row["source_file"],
                    "reason": row["exclusion_reason"],
                    "note": note,
                }
            )

    currency_totals = [
        {
            "currency": item["currency"],
            "document_count": item["document_count"],
            "total_amount": float(item["total_amount"].quantize(Decimal("0.01"))),
        }
        for item in sorted(totals.values(), key=lambda entry: entry["currency"])
    ]

    batch_payload = {
        "batch_id": batch["batch_id"],
        "cutoff_date": batch["cutoff_date"],
        "payable_documents": payable_documents,
        "excluded_documents": excluded_documents,
        "currency_totals": currency_totals,
        "service_checks": {
            "manifest": True,
            "documents": True,
            "document_reviews": True,
        },
        "notes": [
            "The AP review service includes documents that are missing from the stale settlement snapshot.",
            f"Manual review documents: {', '.join(manual_review_notes) if manual_review_notes else 'none'}; duplicate documents: {', '.join(duplicate_notes) if duplicate_notes else 'none'}.",
        ],
    }

    review_text = "\n".join(
        [
            f"Batch ID: {batch['batch_id']}",
            f"Documents reviewed: {len(register_rows)}",
            f"Payable documents: {len(payable_documents)}",
            "Excluded documents:",
            *[f"- {item['source_file']} -> {item['reason']}" for item in excluded_documents],
            f"Manual review documents: {', '.join(manual_review_notes) if manual_review_notes else 'none'}",
            f"Duplicate documents: {', '.join(duplicate_notes) if duplicate_notes else 'none'}",
            "Currency totals:",
            *[f"- {item['currency']}: {item['document_count']} documents / {item['total_amount']:.2f}" for item in currency_totals],
            "Batch logic: current payment status and manual review flags come from the AP review service; duplicate handling, due-date fill, and organized paths follow the local policy and vendor master."
        ]
    ) + "\n"

    return {
        "batch": batch,
        "register_rows": register_rows,
        "batch_payload": batch_payload,
        "review_text": review_text,
        "live_only_source_files": [
            "inbox/office/coolblue/hardware-order.pdf",
            "inbox/fuel/orlen/mobile-pay.txt",
        ],
    }
