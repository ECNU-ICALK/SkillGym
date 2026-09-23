#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Interact with FlowDeck REST API (CRM + Project Management).

Usage:
    uv run flow_api.py list clients [--limit 50] [--offset 0] [--status active]
    uv run flow_api.py get clients --id <uuid>
    uv run flow_api.py create clients --data '{"name":"Acme Corp"}'
    uv run flow_api.py update clients --id <uuid> --data '{"name":"Acme Inc"}'
    uv run flow_api.py delete clients --id <uuid>

Resources: clients, contacts, deals, proposals, receivables, expenses
           projects, cycles, tasks, comments, activity

Use --api-key or set FLOWDECK_API_KEY env var.
Use --base-url or set FLOWDECK_BASE_URL env var.
"""

import argparse
import json
import os
import sys

import httpx


SUPPORTED_RESOURCES = {
    "clients": {"base": "/clients", "path_param": False},
    "contacts": {"base": "/contacts/{id}", "path_param": True, "parent_base": "/projects/{projectId}/contacts"},
    "deals": {"base": "/deals", "path_param": False},
    "proposals": {"base": "/proposals", "path_param": False},
    "receivables": {"base": "/receivables", "path_param": False},
    "expenses": {"base": "/expenses", "path_param": False},
    "projects": {"base": "/projects", "path_param": False},
    "cycles": {"base": "/cycles/{id}", "path_param": True, "parent_base": "/projects/{projectId}/cycles"},
    "tasks": {"base": "/tasks/{id}", "path_param": True, "parent_base": "/projects/{projectId}/tasks"},
    "comments": {"base": "/comments/{id}", "path_param": True, "parent_base": "/tasks/{taskId}/comments"},
}

# Resources that support sub-resource payments
PAYABLE_RESOURCES = {"receivables", "expenses"}


def get_api_key(provided: str | None) -> str:
    if provided:
        return provided
    key = os.environ.get("FLOWDECK_API_KEY")
    if not key:
        print("Error: No API key provided.", file=sys.stderr)
        print("  Set FLOWDECK_API_KEY env var or pass --api-key", file=sys.stderr)
        sys.exit(1)
    return key


def get_base_url(provided: str | None) -> str:
    if provided:
        return provided.rstrip("/")
    val = os.environ.get("FLOWDECK_BASE_URL", "https://mycivgjuujlnyoycuwrz.supabase.co/functions/v1/api-gateway")
    return val.rstrip("/")


def parse_query_params(args: argparse.Namespace) -> dict:
    """Extract known query parameters from CLI args."""
    params = {}
    for key in ("limit", "offset", "status", "priority", "cycle_id",
                 "assignee_id", "stage", "party_id", "category_id",
                 "type", "due_date_from", "due_date_to", "date_from",
                 "date_to"):
        val = getattr(args, key, None)
        if val is not None:
            params[key] = str(val)
    return params


def build_url(resource: str, action: str, resource_id: str | None,
              parent_project_id: str | None) -> str:
    info = SUPPORTED_RESOURCES.get(resource)
    if not info:
        print(f"Error: Unknown resource '{resource}'.", file=sys.stderr)
        print(f"Supported: {', '.join(SUPPORTED_RESOURCES.keys())}", file=sys.stderr)
        sys.exit(1)

    if action == "list":
        if resource == "contacts" and parent_project_id:
            base = f"/projects/{parent_project_id}/contacts"
        elif resource == "cycles" and parent_project_id:
            base = f"/projects/{parent_project_id}/cycles"
        elif resource == "tasks" and parent_project_id:
            base = f"/projects/{parent_project_id}/tasks"
        elif resource == "comments" and parent_project_id:
            base = f"/tasks/{parent_project_id}/comments"
        else:
            base = info["base"]
        return base

    if action in ("create", "update") and info.get("parent_base"):
        # For creates that need a parent (contacts, cycles, tasks, comments)
        if resource == "contacts" and parent_project_id:
            return f"/projects/{parent_project_id}/contacts"
        if resource == "cycles" and parent_project_id:
            return f"/projects/{parent_project_id}/cycles"
        if resource == "tasks" and parent_project_id:
            return f"/projects/{parent_project_id}/tasks"
        if resource == "comments" and parent_project_id:
            return f"/tasks/{parent_project_id}/comments"
        # Fall through to parent_base interpolation
        return info["parent_base"].replace("{projectId}", str(parent_project_id or "")) \
                                 .replace("{taskId}", str(parent_project_id or ""))

    # Single resource operations
    if resource_id:
        base = info["base"]
        if "{id}" in base:
            return base.replace("{id}", resource_id)
        return f"{base}/{resource_id}"

    return info["base"]


def make_request(method: str, url: str, api_key: str,
                 query_params: dict | None = None,
                 body: dict | None = None):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = httpx.request(
        method,
        url,
        headers=headers,
        params=query_params,
        json=body,
        timeout=30,
    )
    return response


def main():
    parser = argparse.ArgumentParser(
        description="FlowDeck API CLI (CRM + Project Management)"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # list
    list_p = subparsers.add_parser("list", help="List resources")
    list_p.add_argument("resource", choices=SUPPORTED_RESOURCES.keys())
    list_p.add_argument("--limit", type=int)
    list_p.add_argument("--offset", type=int)
    list_p.add_argument("--status", type=str)
    list_p.add_argument("--type", type=str)
    list_p.add_argument("--priority", type=str)
    list_p.add_argument("--stage", type=str)
    list_p.add_argument("--cycle-id", dest="cycle_id")
    list_p.add_argument("--assignee-id", dest="assignee_id")
    list_p.add_argument("--party-id", dest="party_id")
    list_p.add_argument("--category-id", dest="category_id")
    list_p.add_argument("--due-date-from", dest="due_date_from")
    list_p.add_argument("--due-date-to", dest="due_date_to")
    list_p.add_argument("--date-from", dest="date_from")
    list_p.add_argument("--date-to", dest="date_to")
    list_p.add_argument("--project-id", dest="parent_id")

    # get
    get_p = subparsers.add_parser("get", help="Get single resource")
    get_p.add_argument("resource", choices=SUPPORTED_RESOURCES.keys())
    get_p.add_argument("--id", required=True)

    # create
    create_p = subparsers.add_parser("create", help="Create resource")
    create_p.add_argument("resource", choices=SUPPORTED_RESOURCES.keys())
    create_p.add_argument("--data", required=True,
                          help='JSON body string')
    create_p.add_argument("--project-id", dest="parent_id",
                          help="Parent project ID for contacts, cycles, tasks")

    # update
    update_p = subparsers.add_parser("update", help="Update resource")
    update_p.add_argument("resource", choices=SUPPORTED_RESOURCES.keys())
    update_p.add_argument("--id", required=True)
    update_p.add_argument("--data", required=True,
                          help='JSON body string')

    # delete
    delete_p = subparsers.add_parser("delete", help="Delete resource")
    delete_p.add_argument("resource", choices=SUPPORTED_RESOURCES.keys())
    delete_p.add_argument("--id", required=True)

    args = parser.parse_args()

    api_key = get_api_key(None)
    base_url = get_base_url(None)

    query = parse_query_params(args)
    parent_id = getattr(args, "parent_id", None)
    resource_id = getattr(args, "id", None)

    url = base_url + build_url(args.resource, args.action,
                               resource_id, parent_id)

    try:
        if args.action == "list":
            resp = make_request("GET", url, api_key, query_params=query)
        elif args.action == "get":
            resp = make_request("GET", url, api_key)
        elif args.action == "create":
            body = json.loads(args.data)
            resp = make_request("POST", url, api_key, body=body)
        elif args.action == "update":
            body = json.loads(args.data)
            resp = make_request("PATCH", url, api_key, body=body)
        elif args.action == "delete":
            resp = make_request("DELETE", url, api_key)

        if resp.status_code >= 400:
            print(f"Error: HTTP {resp.status_code}", file=sys.stderr)
            try:
                detail = resp.json()
                print(json.dumps(detail, ensure_ascii=False, indent=2),
                      file=sys.stderr)
            except Exception:
                print(resp.text, file=sys.stderr)
            sys.exit(1)

        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

    except httpx.RequestError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in --data: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
