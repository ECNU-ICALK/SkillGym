#!/usr/bin/env python3
"""
Invoice Agent — Payment Reminder Generator
Generates professional payment reminder emails/texts based on overdue invoices.
Supports escalation levels: gentle, firm, final.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

DATA_FILE = Path.home() / ".invoice-agent" / "data.json"

REMINDER_TEMPLATES = {
    "gentle": {
        "subject": "Friendly Reminder: Invoice {invoice_id} — {currency_symbol}{amount}",
        "body": """Hi {client_name},

I hope this message finds you well! I wanted to send a friendly reminder that Invoice {invoice_id} for {currency_symbol}{amount} was due on {due_date}.

I understand things get busy — if you've already sent payment, please disregard this message. Otherwise, I'd appreciate it if you could process this at your earliest convenience.

Here are the details:
  Invoice: {invoice_id}
  Amount Due: {currency_symbol}{amount}
  Due Date: {due_date}
  Days Overdue: {days_late}

If you have any questions or need to discuss payment arrangements, please don't hesitate to reach out.

Thank you so much!

Best regards,
{business_name}
{business_email}"""
    },
    "firm": {
        "subject": "Payment Required: Invoice {invoice_id} — {currency_symbol}{amount} (Overdue)",
        "body": """Dear {client_name},

I'm writing to follow up on Invoice {invoice_id} for {currency_symbol}{amount}, which was due on {due_date} and is now {days_late} days overdue.

This is my second reminder. I kindly request that payment be made as soon as possible to keep your account in good standing.

Invoice Details:
  Invoice: {invoice_id}
  Amount Due: {currency_symbol}{amount}
  Original Due Date: {due_date}
  Days Past Due: {days_late}
  Payment Terms: {payment_terms}

If payment has been sent, please share the confirmation number so I can update our records. If there are any issues preventing payment, please let me know so we can work out a solution.

Thank you for your prompt attention to this matter.

Regards,
{business_name}
{business_email}"""
    },
    "final": {
        "subject": "URGENT: Final Notice — Invoice {invoice_id} — {currency_symbol}{amount}",
        "body": """Dear {client_name},

This is my FINAL NOTICE regarding Invoice {invoice_id} for {currency_symbol}{amount}, which is now {days_late} days overdue.

Despite previous reminders, this invoice remains unpaid. I must receive payment within 7 business days, or I will be compelled to:
  • Refer this matter to a collections agency
  • Suspend all services until the balance is cleared
  • Pursue additional remedies as permitted by law

Invoice Details:
  Invoice: {invoice_id}
  Amount Due: {currency_symbol}{amount}
  Original Due Date: {due_date}
  Days Past Due: {days_late}

If payment is being processed, please confirm immediately. I would prefer to resolve this amicably and avoid any further action.

Sincerely,
{business_name}
{business_email}"""
    }
}

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥",
    "KRW": "₩", "INR": "₹", "AUD": "A$", "CAD": "C$"
}

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"invoices": [], "config": {}}

def get_reminder_level(days_late):
    if days_late <= 7:
        return "gentle"
    elif days_late <= 21:
        return "firm"
    else:
        return "final"

def generate_reminder(invoice, level=None):
    today = datetime.now()
    due_date = datetime.strptime(invoice["due_date"], "%Y-%m-%d")
    days_late = (today - due_date).days
    
    if level is None:
        level = get_reminder_level(days_late)
    
    template = REMINDER_TEMPLATES.get(level, REMINDER_TEMPLATES["gentle"])
    currency = invoice.get("currency", "USD")
    currency_symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    
    data = load_data()
    config = data.get("config", {})
    
    variables = {
        "client_name": invoice.get("client_name", ""),
        "invoice_id": invoice.get("id", ""),
        "amount": f"{invoice.get('total', 0):,.2f}",
        "due_date": invoice.get("due_date", ""),
        "days_late": str(days_late),
        "currency_symbol": currency_symbol,
        "payment_terms": invoice.get("payment_terms", config.get("payment_terms", "Net 30")),
        "business_name": invoice.get("business_name", config.get("business_name", "")),
        "business_email": invoice.get("business_email", config.get("business_email", "")),
    }
    
    subject = template["subject"]
    body = template["body"]
    for key, value in variables.items():
        subject = subject.replace("{" + key + "}", value)
        body = body.replace("{" + key + "}", value)
    
    return {
        "level": level,
        "days_late": days_late,
        "to": invoice.get("client_email", ""),
        "subject": subject,
        "body": body
    }

def main():
    data = load_data()
    invoices = data.get("invoices", [])
    
    # Find overdue invoices
    today = datetime.now().strftime("%Y-%m-%d")
    overdue = [i for i in invoices if i["status"] == "sent" and today > i["due_date"]]
    
    if not overdue:
        print("No overdue invoices found. 🎉")
        return
    
    print(f"Found {len(overdue)} overdue invoice(s):\n")
    
    for inv in overdue:
        reminder = generate_reminder(inv)
        print(f"{'='*60}")
        print(f"Invoice: {inv['id']} | Client: {inv['client_name']}")
        print(f"Amount: {inv['currency']} {inv['total']:,.2f} | Days Late: {reminder['days_late']}")
        print(f"Reminder Level: {reminder['level'].upper()}")
        print(f"{'='*60}")
        print(f"To: {reminder['to']}")
        print(f"Subject: {reminder['subject']}\n")
        print(reminder['body'])
        print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
