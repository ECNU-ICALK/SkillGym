# Invoice Agent — Reference Guide

## Table of Contents
- [Data Storage](#data-storage)
- [Invoice Lifecycle](#invoice-lifecycle)
- [CLI Commands Reference](#cli-commands-reference)
- [Currency Support](#currency-support)
- [Reminder Escalation](#reminder-escalation)
- [HTML Generation](#html-generation)

## Data Storage

All data is stored locally at `~/.invoice-agent/data.json`. Structure:

```json
{
  "invoices": [ ... ],
  "config": {
    "currency": "USD",
    "tax_rate": 0,
    "business_name": "",
    "business_address": "",
    "business_email": "",
    "payment_terms": "Net 30"
  }
}
```

No cloud, no API keys, no external dependencies. All data stays on the user's machine.

## Invoice Lifecycle

```
draft → sent → paid
          ↓
      overdue (automatic when past due_date)
          ↓
      cancelled (manual)
```

- **draft**: Invoice created, not yet sent to client
- **sent**: Invoice has been delivered to client
- **paid**: Payment received
- **cancelled**: Invoice voided (requires --force to delete)

## CLI Commands Reference

### Create Invoice
```bash
python3 scripts/invoice.py create \
  --client "Acme Corp" \
  --email "billing@acme.com" \
  --address "123 Main St, NY" \
  --items "Website Design|1|2500" "SEO Setup|1|500" "Hosting (monthly)|3|29.99" \
  --tax 8.5 \
  --currency USD \
  --due-days 30 \
  --notes "Thank you for choosing us!"
```

### List Invoices
```bash
python3 scripts/invoice.py list                    # All invoices
python3 scripts/invoice.py list --status sent      # Only sent
python3 scripts/invoice.py list --status paid      # Only paid
python3 scripts/invoice.py list --client "Acme"    # By client name
```

### Show Invoice Details
```bash
python3 scripts/invoice.py show --id INV-20260413-ABC123
```

### Update Status
```bash
python3 scripts/invoice.py update --id INV-XXX --status sent
python3 scripts/invoice.py update --id INV-XXX --status paid --method "Bank Transfer"
```

### Financial Summary
```bash
python3 scripts/invoice.py summary --period all     # All time
python3 scripts/invoice.py summary --period month   # This month
python3 scripts/invoice.py summary --period week    # This week
python3 scripts/invoice.py summary --period year    # This year
```

### Overdue Check
```bash
python3 scripts/invoice.py overdue
```

### Delete Invoice
```bash
python3 scripts/invoice.py delete --id INV-XXX              # Draft only
python3 scripts/invoice.py delete --id INV-XXX --force      # Any status
```

### Export Invoice JSON
```bash
python3 scripts/invoice.py export --id INV-XXX
# Outputs to ~/.invoice-agent/invoices/INV-XXX.json
```

### Configure Defaults
```bash
python3 scripts/invoice.py config \
  --business-name "John's Agency" \
  --business-address "456 Oak Ave, SF" \
  --business-email "john@agency.com" \
  --currency USD \
  --tax-rate 8.5 \
  --payment-terms "Net 15"
```

## Currency Support

Supported currency symbols (auto-detected from code):

| Code | Symbol | Code | Symbol |
|------|--------|------|--------|
| USD | $ | EUR | € |
| GBP | £ | JPY | ¥ |
| CNY | ¥ | KRW | ₩ |
| INR | ₹ | AUD | A$ |
| CAD | C$ | SGD | S$ |

Any unsupported code will display as "CODE " (e.g., "ZAR ").

## Reminder Escalation

The reminder system uses time-based escalation:

| Days Late | Level | Tone |
|-----------|-------|------|
| 1-7 | Gentle | Friendly, assume oversight |
| 8-21 | Firm | Professional, request action |
| 22+ | Final | Urgent, legal warning |

Run `python3 scripts/reminders.py` to generate reminders for all overdue invoices.

## HTML Generation

### From Invoice File
```bash
# Export invoice JSON first
python3 scripts/invoice.py export --id INV-XXX

# Generate HTML
python3 scripts/generate_invoice.py ~/.invoice-agent/invoices/INV-XXX.json output.html
```

### Customization
- Edit `assets/invoice-template.html` to change layout
- Change `BRAND_COLOR_DEFAULT` in `generate_invoice.py` for brand color
- Modify CSS in the template for custom styling
