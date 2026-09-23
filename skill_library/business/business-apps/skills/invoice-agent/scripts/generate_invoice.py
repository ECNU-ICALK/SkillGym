#!/usr/bin/env python3
"""
Invoice Agent — HTML Invoice Generator
Reads an invoice JSON and generates a professional HTML invoice file.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥",
    "KRW": "₩", "INR": "₹", "AUD": "A$", "CAD": "C$", "CHF": "CHF ",
    "BRL": "R$", "MXN": "MX$", "SGD": "S$", "HKD": "HK$", "NZD": "NZ$"
}

BRAND_COLOR_DEFAULT = "#2563eb"

def get_currency_symbol(currency_code):
    return CURRENCY_SYMBOLS.get(currency_code, currency_code + " ")

def generate_item_rows(items, currency_symbol):
    rows = []
    for item in items:
        qty = item.get("quantity", 1)
        unit_price = item.get("unit_price", item.get("amount", 0))
        amount = item.get("amount", qty * unit_price)
        rows.append(f"""      <tr>
        <td>{item['description']}</td>
        <td>{qty:g}</td>
        <td>{currency_symbol}{unit_price:,.2f}</td>
        <td>{currency_symbol}{amount:,.2f}</td>
      </tr>""")
    return "\n".join(rows)

def generate_html(invoice_data, template_path=None):
    if template_path is None:
        template_path = Path(__file__).parent.parent / "assets" / "invoice-template.html"
    
    with open(template_path) as f:
        template = f.read()
    
    currency = invoice_data.get("currency", "USD")
    currency_symbol = get_currency_symbol(currency)
    status = invoice_data.get("status", "draft").lower()
    
    created = invoice_data.get("created_at", datetime.now().isoformat())
    issue_date = created[:10] if len(created) >= 10 else datetime.now().strftime("%Y-%m-%d")
    
    replacements = {
        "{{INVOICE_ID}}": invoice_data.get("id", "INV-000000"),
        "{{STATUS}}": status.upper(),
        "{{STATUS_CLASS}}": status,
        "{{ISSUE_DATE}}": issue_date,
        "{{DUE_DATE}}": invoice_data.get("due_date", ""),
        "{{BUSINESS_NAME}}": invoice_data.get("business_name", "Your Business"),
        "{{BUSINESS_ADDRESS}}": invoice_data.get("business_address", ""),
        "{{BUSINESS_EMAIL}}": invoice_data.get("business_email", ""),
        "{{CLIENT_NAME}}": invoice_data.get("client_name", ""),
        "{{CLIENT_ADDRESS}}": invoice_data.get("client_address", ""),
        "{{CLIENT_EMAIL}}": invoice_data.get("client_email", ""),
        "{{ITEMS_ROWS}}": generate_item_rows(invoice_data.get("items", []), currency_symbol),
        "{{SUBTOTAL}}": f"{invoice_data.get('subtotal', 0):,.2f}",
        "{{TAX_RATE}}": f"{invoice_data.get('tax_rate', 0):g}",
        "{{TAX_AMOUNT}}": f"{invoice_data.get('tax_amount', 0):,.2f}",
        "{{TOTAL}}": f"{invoice_data.get('total', 0):,.2f}",
        "{{CURRENCY_SYMBOL}}": currency_symbol,
        "{{PAYMENT_TERMS}}": invoice_data.get("payment_terms", "Net 30"),
        "{{NOTES}}": invoice_data.get("notes", "Thank you for your business!"),
        "{{GENERATED_DATE}}": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        "{{BRAND_COLOR}}": BRAND_COLOR_DEFAULT,
    }
    
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, str(value))
    
    return template

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_invoice.py <invoice.json> [output.html]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    with open(input_file) as f:
        invoice_data = json.load(f)
    
    html = generate_html(invoice_data)
    
    if output_file:
        with open(output_file, "w") as f:
            f.write(html)
        print(f"✅ Invoice HTML generated: {output_file}")
    else:
        print(html)

if __name__ == "__main__":
    main()
