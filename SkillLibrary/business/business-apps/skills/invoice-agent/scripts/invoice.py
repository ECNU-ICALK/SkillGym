#!/usr/bin/env python3
"""
Invoice Agent — Core invoice management CLI
Stores all data in a local JSON database (~/.invoice-agent/data.json)
Supports: create, list, update status, summary, overdue, delete, export
"""

import json
import os
import sys
import uuid
import argparse
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / ".invoice-agent"
DATA_FILE = DATA_DIR / "data.json"
INVOICES_DIR = DATA_DIR / "invoices"
CONFIG_FILE = DATA_DIR / "config.json"

def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INVOICES_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    ensure_dirs()
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"invoices": [], "config": {"currency": "USD", "tax_rate": 0, "business_name": "", "business_address": "", "business_email": "", "payment_terms": "Net 30"}}

def save_data(data):
    ensure_dirs()
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def generate_invoice_id():
    return f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

def create_invoice(args):
    data = load_data()
    config = data.get("config", {})
    
    items = []
    if args.items:
        for item_str in args.items:
            parts = item_str.split("|")
            if len(parts) >= 2:
                item = {
                    "description": parts[0].strip(),
                    "quantity": float(parts[1].strip()) if len(parts) > 1 else 1,
                    "unit_price": float(parts[2].strip()) if len(parts) > 2 else 0,
                    "amount": float(parts[1].strip()) * float(parts[2].strip()) if len(parts) > 2 else float(parts[1].strip())
                }
                items.append(item)
    
    subtotal = sum(i["amount"] for i in items)
    tax_rate = float(args.tax) if args.tax else config.get("tax_rate", 0)
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount
    
    due_days = int(args.due_days) if args.due_days else 30
    due_date = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")
    
    invoice = {
        "id": generate_invoice_id(),
        "client_name": args.client,
        "client_email": args.email or "",
        "client_address": args.address or "",
        "business_name": args.business_name or config.get("business_name", ""),
        "business_address": args.business_address or config.get("business_address", ""),
        "business_email": args.business_email or config.get("business_email", ""),
        "items": items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "currency": args.currency or config.get("currency", "USD"),
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "due_date": due_date,
        "notes": args.notes or "",
        "payment_terms": args.payment_terms or config.get("payment_terms", "Net 30")
    }
    
    data["invoices"].append(invoice)
    save_data(data)
    
    print(json.dumps(invoice, indent=2))
    return invoice

def list_invoices(args):
    data = load_data()
    invoices = data.get("invoices", [])
    
    if args.status:
        invoices = [i for i in invoices if i["status"] == args.status]
    if args.client:
        invoices = [i for i in invoices if args.client.lower() in i["client_name"].lower()]
    
    if not invoices:
        print("No invoices found.")
        return
    
    for inv in invoices:
        overdue = ""
        if inv["status"] == "sent" and datetime.now().strftime("%Y-%m-%d") > inv["due_date"]:
            overdue = " ⚠️ OVERDUE"
        print(f"  {inv['id']} | {inv['client_name']:20s} | {inv['currency']} {inv['total']:>10.2f} | {inv['status']:8s} | Due: {inv['due_date']}{overdue}")
    
    print(f"\nTotal: {len(invoices)} invoice(s)")

def update_status(args):
    data = load_data()
    for inv in data["invoices"]:
        if inv["id"] == args.id:
            old_status = inv["status"]
            inv["status"] = args.status
            if args.status == "paid":
                inv["paid_at"] = datetime.now().isoformat()
                inv["paid_method"] = args.method or "unspecified"
            elif args.status == "sent":
                inv["sent_at"] = datetime.now().isoformat()
            save_data(data)
            print(json.dumps({"updated": True, "id": inv["id"], "old_status": old_status, "new_status": args.status}, indent=2))
            return
    print(f"Invoice {args.id} not found.")

def summary(args):
    data = load_data()
    invoices = data.get("invoices", [])
    
    now = datetime.now()
    if args.period == "month":
        invoices = [i for i in invoices if i["created_at"][:7] == now.strftime("%Y-%m")]
    elif args.period == "week":
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        invoices = [i for i in invoices if i["created_at"][:10] >= week_ago]
    elif args.period == "year":
        invoices = [i for i in invoices if i["created_at"][:4] == now.strftime("%Y")]
    
    total_invoiced = sum(i["total"] for i in invoices)
    total_paid = sum(i["total"] for i in invoices if i["status"] == "paid")
    total_pending = sum(i["total"] for i in invoices if i["status"] == "sent")
    total_draft = sum(i["total"] for i in invoices if i["status"] == "draft")
    total_overdue = sum(i["total"] for i in invoices if i["status"] == "sent" and now.strftime("%Y-%m-%d") > i["due_date"])
    
    currency = invoices[0]["currency"] if invoices else "USD"
    
    summary = {
        "period": args.period or "all",
        "total_invoices": len(invoices),
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_pending": total_pending,
        "total_draft": total_draft,
        "total_overdue": total_overdue,
        "currency": currency,
        "collection_rate": (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0
    }
    
    print(json.dumps(summary, indent=2))

def overdue(args):
    data = load_data()
    now = datetime.now().strftime("%Y-%m-%d")
    overdue = [i for i in data["invoices"] if i["status"] == "sent" and now > i["due_date"]]
    
    if not overdue:
        print("No overdue invoices! 🎉")
        return
    
    total_overdue = sum(i["total"] for i in overdue)
    print(f"⚠️  {len(overdue)} overdue invoice(s) — Total: {total_overdue:.2f}\n")
    for inv in overdue:
        days_late = (datetime.now() - datetime.strptime(inv["due_date"], "%Y-%m-%d")).days
        print(f"  {inv['id']} | {inv['client_name']:20s} | {inv['currency']} {inv['total']:>10.2f} | Due: {inv['due_date']} ({days_late} days late)")

def delete_invoice(args):
    data = load_data()
    for i, inv in enumerate(data["invoices"]):
        if inv["id"] == args.id:
            if args.force or inv["status"] == "draft":
                del data["invoices"][i]
                save_data(data)
                print(json.dumps({"deleted": True, "id": args.id}, indent=2))
            else:
                print(f"Cannot delete invoice with status '{inv['status']}'. Use --force to override.")
            return
    print(f"Invoice {args.id} not found.")

def export_invoice(args):
    data = load_data()
    for inv in data["invoices"]:
        if inv["id"] == args.id:
            filepath = INVOICES_DIR / f"{inv['id']}.json"
            with open(filepath, "w") as f:
                json.dump(inv, f, indent=2)
            print(f"Exported to: {filepath}")
            return
    print(f"Invoice {args.id} not found.")

def configure(args):
    data = load_data()
    if args.currency:
        data["config"]["currency"] = args.currency
    if args.tax_rate is not None:
        data["config"]["tax_rate"] = float(args.tax_rate)
    if args.business_name:
        data["config"]["business_name"] = args.business_name
    if args.business_address:
        data["config"]["business_address"] = args.business_address
    if args.business_email:
        data["config"]["business_email"] = args.business_email
    if args.payment_terms:
        data["config"]["payment_terms"] = args.payment_terms
    save_data(data)
    print(json.dumps(data["config"], indent=2))

def show_invoice(args):
    data = load_data()
    for inv in data["invoices"]:
        if inv["id"] == args.id:
            print(json.dumps(inv, indent=2))
            return
    print(f"Invoice {args.id} not found.")

def get_config():
    data = load_data()
    return data.get("config", {})

def main():
    parser = argparse.ArgumentParser(description="Invoice Agent — Invoice Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # create
    p_create = subparsers.add_parser("create", help="Create a new invoice")
    p_create.add_argument("--client", required=True, help="Client name")
    p_create.add_argument("--email", help="Client email")
    p_create.add_argument("--address", help="Client address")
    p_create.add_argument("--items", nargs="+", help='Items as "description|quantity|unit_price"')
    p_create.add_argument("--tax", help="Tax rate percentage")
    p_create.add_argument("--currency", help="Currency code (e.g. USD, EUR)")
    p_create.add_argument("--due-days", help="Days until due (default: 30)")
    p_create.add_argument("--notes", help="Invoice notes")
    p_create.add_argument("--payment-terms", help="Payment terms")
    p_create.add_argument("--business-name", help="Your business name")
    p_create.add_argument("--business-address", help="Your business address")
    p_create.add_argument("--business-email", help="Your business email")
    
    # list
    p_list = subparsers.add_parser("list", help="List invoices")
    p_list.add_argument("--status", help="Filter by status (draft/sent/paid/overdue)")
    p_list.add_argument("--client", help="Filter by client name")
    
    # show
    p_show = subparsers.add_parser("show", help="Show invoice details")
    p_show.add_argument("--id", required=True, help="Invoice ID")
    
    # update
    p_update = subparsers.add_parser("update", help="Update invoice status")
    p_update.add_argument("--id", required=True, help="Invoice ID")
    p_update.add_argument("--status", required=True, help="New status (sent/paid/cancelled)")
    p_update.add_argument("--method", help="Payment method (for paid status)")
    
    # summary
    p_summary = subparsers.add_parser("summary", help="Financial summary")
    p_summary.add_argument("--period", choices=["week", "month", "year", "all"], default="all")
    
    # overdue
    subparsers.add_parser("overdue", help="List overdue invoices")
    
    # delete
    p_delete = subparsers.add_parser("delete", help="Delete an invoice")
    p_delete.add_argument("--id", required=True, help="Invoice ID")
    p_delete.add_argument("--force", action="store_true", help="Force delete non-draft invoices")
    
    # export
    p_export = subparsers.add_parser("export", help="Export invoice to file")
    p_export.add_argument("--id", required=True, help="Invoice ID")
    
    # config
    p_config = subparsers.add_parser("config", help="Configure business defaults")
    p_config.add_argument("--currency", help="Default currency")
    p_config.add_argument("--tax-rate", help="Default tax rate %")
    p_config.add_argument("--business-name", help="Business name")
    p_config.add_argument("--business-address", help="Business address")
    p_config.add_argument("--business-email", help="Business email")
    p_config.add_argument("--payment-terms", help="Default payment terms")
    
    # get-config
    subparsers.add_parser("get-config", help="Show current configuration")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        "create": create_invoice,
        "list": list_invoices,
        "show": show_invoice,
        "update": update_status,
        "summary": summary,
        "overdue": overdue,
        "delete": delete_invoice,
        "export": export_invoice,
        "config": configure,
        "get-config": lambda a: print(json.dumps(get_config(), indent=2))
    }
    
    commands[args.command](args)

if __name__ == "__main__":
    main()
