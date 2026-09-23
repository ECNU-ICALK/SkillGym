---
name: flow-crm
description: Interact with FlowDeck CRM API (clients, deals, proposals, receivables, expenses, contacts). Use for all CRM operations via the FlowDeck REST API through Supabase Edge Functions.
---

# FlowDeck CRM API

Interact with the FlowDeck CRM module via the REST API gateway
(base URL: `https://<supabase_url>/functions/v1/api-gateway`).

## Usage

Run the script using the absolute path (do NOT cd to the skill directory):

```bash
uv run ~/.codex/skills/flow-crm/scripts/flow_api.py <action> <resource> [options]
```

**Important:** Always run from the user's current working directory so any output files are saved where the user is working.

## Actions

| Action   | Description          | Example                                              |
|----------|----------------------|------------------------------------------------------|
| `list`   | List resources (paginated) | `uv run ... list clients --limit 50`           |
| `get`    | Get single resource  | `uv run ... get clients --id <uuid>`             |
| `create` | Create resource      | `uv run ... create clients --data '{"name":"Acme"}'` |
| `update` | Update resource      | `uv run ... update clients --id <uuid> --data '{"name":"Acme Inc"}'` |
| `delete` | Delete resource      | `uv run ... delete clients --id <uuid>`           |

## Client Creation Workflow (mandatory)

When creating a client (`create clients`), the API only requires `name`. However, you MUST proactively ask the user about every available field BEFORE calling the API. Collect as much data as possible, then build the payload. Even if the user skips many fields, you must have asked.

Ask about these fields (use the Portuguese/Portuñol terms the user will recognize):

1. **Tipo** — `client`, `supplier`, or `both` (default: `client`)
2. **Empresa** — Company name
3. **Email** — Main contact email
4. **Email financeiro** — Finance department email (`finance_email`)
5. **Telefone** — Phone number
6. **CPF/CNPJ** — Document (Brazilian tax ID)
7. **Website** — Company website
8. **Endereço** — Physical address
9. **País** — Country (`country`)
10. **Código IBGE da cidade** — `city_ibge_code`
11. **Status** — `active`, `inactive`, or `lead` (default: `active`)
12. **Observações** — Notes

Present these as a single structured block of questions (not one-by-one), e.g:

> Antes de criar o cliente, preciso preencher algumas informações. Me diga o que souber:
>
> - **Tipo:** [client/supplier/both]
> - **Empresa:**
> - **Email:**
> - **Email financeiro:**
> - **Telefone:**
> - **CPF/CNPJ:**
> - **Website:**
> - **Endereço:**
> - **País:**
> - **Código IBGE:**
> - **Observações:**
>
> (Pule os que não souber.)

If the user responds with partial data, use what they gave and leave the rest blank — but never skip asking first. Then build the `--data` JSON with all collected fields and create the client.

## CRM Resources

| Resource     | Endpoint         | Notes                          |
|-------------|------------------|--------------------------------|
| `clients`   | `/clients`       | Clients & suppliers (finance_parties) |
| `contacts`  | `/projects/{id}/contacts` | Project-scoped contacts |
| `deals`     | `/deals`         | CRM opportunities (crm_deals)  |
| `proposals` | `/proposals`     | Commercial proposals           |
| `receivables` | `/receivables` | Accounts receivable            |
| `expenses`  | `/expenses`      | Expenses                       |

## Filters for `list`

Common query parameters (supported varies by resource):

- `--limit N` (default 50, max 200)
- `--offset N` (default 0)
- `--status` — filter by status enum
- `--type` — filter by type (clients: client/supplier/both)
- `--stage` — filter by deal stage (deals: lead/qualified/proposal/negotiation/won/lost)
- `--party-id` — filter by client/supplier (party UUID)
- `--project-id` — parent project ID for scoped resources (contacts, cycles, tasks)
- `--priority` — filter task priority
- `--cycle-id` — filter tasks by cycle
- `--assignee-id` — filter tasks by assignee
- `--due-date-from` / `--due-date-to` — date range for receivables
- `--date-from` / `--date-to` — date range for expenses

## Status/Stage Enums

### Clients (PartyStatus)
`active`, `inactive`, `lead`

### Deals (CrmDealStage)
`lead` -> `qualified` -> `proposal` -> `negotiation` -> `won` / `lost`

### Proposals (CrmProposalStatus)
`draft` -> `sent` -> `viewed` -> `accepted` / `rejected` / `expired`

### Receivables (ReceivableStatus)
`pending`, `paid`, `partial`, `overdue`, `cancelled`

### Expenses (ExpenseStatus)
`pending`, `paid`, `partial`

## API Key

The script checks for API key in this order:
1. `--api-key` argument (use if user provided key in chat)
2. `FLOWDECK_API_KEY` environment variable

If neither is available, the script exits with an error message.

## API Key + Base URL Environment Variables

- `FLOWDECK_API_KEY` — Bearer API key
- `FLOWDECK_BASE_URL` — API base URL (default: `https://mycivgjuujlnyoycuwrz.supabase.co/functions/v1/api-gateway`)

## Preflight + Common Failures

- Preflight:
  - `command -v uv` (must exist)
  - `test -n "$FLOWDECK_API_KEY"` (or pass `--api-key`)
- Common failures:
  - `Error: No API key provided.` → set `FLOWDECK_API_KEY` or pass `--api-key`
  - `HTTP 401` → invalid/revoked key
  - `HTTP 404` → resource not found or doesn't belong to workspace
  - `"quota/permission/403"` → wrong key, no access, or quota exceeded

## Examples

**List active clients:**
```bash
uv run ~/.codex/skills/flow-crm/scripts/flow_api.py list clients --status active --limit 20
```

**Create a deal:**
```bash
uv run ~/.codex/skills/flow-crm/scripts/flow_api.py create deals \
  --data '{"title":"Website Redesign","client_id":"<uuid>","value":50000,"stage":"lead"}'
```

**Create a proposal:**
```bash
uv run ~/.codex/skills/flow-crm/scripts/flow_api.py create proposals \
  --data '{"title":"Proposta — Website Redesign","client_id":"<uuid>","deal_id":"<uuid>","currency":"BRL"}'
```

**Update a deal stage to won:**
```bash
uv run ~/.codex/skills/flow-crm/scripts/flow_api.py update deals \
  --id <uuid> --data '{"stage":"won"}'
```

**List overdue receivables for a client:**
```bash
uv run ~/.codex/skills/flow-crm/scripts/flow_api.py list receivables \
  --status overdue --party-id <uuid>
```
