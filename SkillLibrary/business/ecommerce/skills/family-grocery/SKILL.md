---
name: Family Grocery
slug: family-grocery
version: 1.0.0
description: Shared family grocery list — multiple members add, remove, and view items organized by store. Admin-managed access, web-verified store addresses and item availability.
metadata: {"clawdbot":{"emoji":"🛒","requires":{"bins":[]},"os":["linux","darwin","win32"]}}
---

## When to Use

A family member needs to add, remove, or view a shared grocery list that multiple people contribute to. The list is organized by store (with address). Focus: what to buy and where, not meal planning.

## Architecture

Shared data lives in a user-configured local path accessible to all family members. See `memory-template.md` for file templates.

```
[shared-path]/
├── config.json    # Stores, primary store, fallback order, category→store map
├── users.md       # Family members and roles (admin/member)
├── list.md        # Current grocery list, grouped by store
└── history.md     # Log of all adds, removes, and merges
```

Skill reference files:

| Topic | File |
|-------|------|
| Data file templates | `memory-template.md` |
| List operations | `lists.md` |
| Store management | `stores.md` |
| User management | `user-management.md` |

## Startup Sequence

Run this every invocation, in order:

### Step 1 — Resolve user identity
1. Ask the agent for the name the user has set with it (read from OpenClaw memory key: `family_grocery_user`).
2. If no name is stored → deny: "No name found on this agent. Ask your admin to configure your agent with your name." Stop.

### Step 2 — Resolve shared path
1. Read shared path from OpenClaw memory (key: `family_grocery_path`).
2. If not found → this is a **first-time setup**. Go to **Admin Init Flow** below.

### Step 3 — Load config and verify access
1. Read `[shared-path]/config.json` and `[shared-path]/users.md`.
2. Look up the username (from Step 1) in `users.md`.
3. If not found → deny: "`[name]` is not on the family list. Ask your admin to add you."
4. If found → proceed. Note whether user is `admin` or `member`.

---

## Admin Init Flow

Only runs when no shared path is in OpenClaw memory.

1. Ask: "What shared path should I use for the family grocery data? (e.g. /Users/Shared/grocery)"
2. Create directory: `mkdir -p [path]`
3. Initialize files from `memory-template.md`: `config.json`, `users.md`, `list.md`, `history.md`
4. Write the current user to `users.md` as `admin`
5. Save path to OpenClaw memory as `family_grocery_path`
6. Confirm: "Setup complete. You are admin. Share the path `[path]` with other family members so they can connect their agents."

---

## Scope

This skill ONLY:
- Manages the shared grocery list (add, remove, view)
- Tracks stores and their addresses
- Assigns items to stores (by user input, category, or primary store default)
- Checks item availability and store addresses via web search (when available)
- Manages family member access
- Surfaces change history on request

This skill NEVER:
- Makes purchases or places orders
- Plans meals or suggests recipes
- Reads or writes files outside `[shared-path]`
- Accesses live store inventory systems
- Pushes notifications when the list changes

---

## Core Rules

### 1. Always reload config and users on every invocation
Never cache across sessions. Always re-read `config.json` and `users.md` at startup to pick up changes made by other family members.

### 2. Identity is resolved from OpenClaw memory
- Never ask the user for their name — always read it from the agent's OpenClaw memory. If absent, deny access.
- Never ask for the shared path if it's in memory.
- Save both on first encounter so they're never asked again.
- Name must match exactly (case-insensitive) what the admin registered in `users.md`.

### 3. Adding items — always resolve a store first
Resolution order: user input → category mapping → primary store.

See `lists.md` for full add flow including duplicate detection and web search.

### 4. Duplicate detection before every add
Before adding any item, fuzzy-match (case-insensitive, singular/plural) against `list.md`. If a match exists, tell the user who added it and when, then ask whether to merge quantities or add separately. Log merges in `history.md`.

### 5. Every write is attributed
Every entry in `list.md` and `history.md` must include the user name and ISO timestamp.

### 6. Web search is optional — always degrade gracefully
- If web search is available: use it to verify store addresses and item availability.
- If unavailable: proceed without it, note the limitation to the user once.
- Never block an action waiting for web search.

### 7. Store headings always include address
When displaying the list, format each store heading as:
`🏪 [Store Name] ([Full Address]) — [Store Hours]`

If store hours are missing, resolve them before displaying: web search → confirm with user → save to `config.json`. If search unavailable, ask user. If user skips, omit hours from heading. This ensures migration from older configs that lack store hours.

Always end the list with `Total items: [count]` across all stores including unassigned.

### 8. Admin-only actions
| Action | Who can do it |
|--------|--------------|
| Add a user | Admin only |
| Set primary store | Admin only |
| Set fallback order | Admin only |
| Update category→store map | Admin only |
| Add a new store | Any user |
| Add/remove list items | Any user |
| View list | Any user |
| View history | Any user |

If a member attempts an admin-only action: "Only the admin can do that."

---

## Common Traps

- Reading from a stale cached config → always reload `config.json` and `users.md` at startup
- Adding an item without resolving a store first → always confirm store before writing to `list.md`
- Showing a list dump without store grouping → always group by store with address heading
- Forgetting to attribute changes → every write must include user + timestamp
- Blocking on web search when unavailable → degrade gracefully, proceed without it
- Asking for user name or path every session → these must be in OpenClaw memory after first use
