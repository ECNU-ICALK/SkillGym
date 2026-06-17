---
name: invoice-agent
license: Proprietary — see LICENSE file. Sold as a single-user license via ClawHub.
description: >
  Professional invoice and payment management skill. Create, track, and manage invoices with
  natural language. Supports multi-currency, tax calculations, payment reminders with escalation,
  HTML invoice generation, overdue tracking, and financial summaries. Use when: (1) creating
  invoices from natural language descriptions, (2) tracking payment status and overdue invoices,
  (3) generating professional HTML invoices, (4) sending payment reminders with escalation levels,
  (5) viewing financial summaries and revenue reports, (6) managing client billing workflows.
  Perfect for freelancers, agencies, and small businesses. All data stored locally — no cloud
  dependencies or API keys required.
---

# Invoice Agent 💰

Professional invoice management entirely from the command line. All data stored locally at `~/.invoice-agent/data.json`.

## Setup (one-time)

```bash
# Configure your business defaults
python3 SKILL_DIR/scripts/invoice.py config \
  --business-name "Your Business" \
  --business-email "you@business.com" \
  --currency USD \
  --tax-rate 0
```

## Quick Workflows

### Create an Invoice (natural language → invoice)
```
User: "Create an invoice for Acme Corp for website design $2500 and SEO setup $500, due in 30 days"
```
```bash
python3 SKILL_DIR/scripts/invoice.py create \
  --client "Acme Corp" \
  --items "Website Design|1|2500" "SEO Setup|1|500" \
  --due-days 30
```

### Generate Professional HTML Invoice
```bash
# Export first
python3 SKILL_DIR/scripts/invoice.py export --id INV-XXX
# Generate HTML
python3 SKILL_DIR/scripts/generate_invoice.py ~/.invoice-agent/invoices/INV-XXX.json invoice.html
```

### Check Overdue Payments & Send Reminders
```bash
python3 SKILL_DIR/scripts/invoice.py overdue
python3 SKILL_DIR/scripts/reminders.py
```

### Financial Dashboard
```bash
python3 SKILL_DIR/scripts/invoice.py summary --period month
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `create --client NAME --items "desc\|qty\|price"` | New invoice |
| `list [--status STATUS]` | List/filter invoices |
| `show --id INV-XXX` | Full invoice details |
| `update --id INV-XXX --status paid` | Mark as paid/sent |
| `summary --period month` | Revenue report |
| `overdue` | List overdue invoices |
| `reminders.py` | Generate reminder emails |
| `generate_invoice.py` | HTML invoice from JSON |
| `config [--business-name NAME ...]` | Set defaults |

## Item Format
Items use pipe-separated format: `"Description|Quantity|UnitPrice"`
- `"Website Design|1|2500"` → 1 × $2,500 = $2,500
- `"Hosting|3|29.99"` → 3 × $29.99 = $89.97
- `"Consulting|2|150"` → 2 × $150 = $300

## Reminder Escalation
Auto-escalation based on days overdue:
- **1-7 days**: Gentle/friendly tone
- **8-21 days**: Firm/professional tone
- **22+ days**: Final notice with legal warning

## References
- Full command reference: see `references/guide.md`
- HTML template: edit `assets/invoice-template.html` for custom branding
- Customize brand color: change `BRAND_COLOR_DEFAULT` in `scripts/generate_invoice.py`
