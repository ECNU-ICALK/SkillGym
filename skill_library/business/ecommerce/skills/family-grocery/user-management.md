# User Management — Family Grocery

## How Identity Works

The admin registers a name for each family member in `users.md`. Each member's agent stores that same name in OpenClaw memory under `family_grocery_user`. On every invocation, the skill reads the name from the agent's memory and checks it against `users.md` — access is granted only if there is an exact match (case-insensitive).

The name is set once per agent (saved to OpenClaw memory on first use). After that, the skill never asks for it again.

---

## First-Time Setup (Admin)

Triggered when `family_grocery_path` is not in OpenClaw memory.

1. Ask for the shared path.
2. Create directory and initialize data files (see `memory-template.md`).
3. Write the admin's username (from `family_grocery_user`) to `users.md` as `admin`.
4. Save path to OpenClaw memory.

The first user who runs setup becomes the admin. There is one admin.

---

## Adding a User (Admin only)

Triggers: "Add user [name]", "Give [name] access"

1. Check current user is admin. If not → "Only the admin can add users."
2. Check if `[name]` already exists in `users.md`. If yes → "`[name]` is already on the list."
3. Append to `users.md`:
   ```
   | [name] | member | [YYYY-MM-DD] |
   ```
4. Confirm: "`[name]` has been added. Tell them to connect their agent to `[shared-path]` and enter `[name]` when the skill asks for their name."

---

## Listing Users (Admin only)

Triggers: "Who has access?", "Show users", "List family members"

Read `users.md` and display:
```
Family members:
- Abhishek (admin) — since 2026-03-01
- Nita (member) — since 2026-03-02
- Arjun (member) — since 2026-03-10
```

---

## Removing a User (Admin only)

Triggers: "Remove user [name]", "Revoke [name]'s access"

1. Check current user is admin.
2. Prevent removing self: "You can't remove yourself as admin."
3. Remove the entry from `users.md`.
4. Confirm: "[Name] has been removed. They can no longer access the grocery list."

---

## users.md Format

```markdown
# Family Members

| Name | Role | Added |
|------|------|-------|
| Abhishek | admin | 2026-03-01 |
| Nita | member | 2026-03-02 |
| Arjun | member | 2026-03-10 |
```

- Names are registered by the admin and must match exactly (case-insensitive) what each member's agent stores in OpenClaw memory.
- Roles:
  - `admin` — full access including user management, store config, category mappings
  - `member` — full access to grocery list and adding stores; cannot manage users or admin-level config
