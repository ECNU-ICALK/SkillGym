# Data File Templates — Family Grocery

These files are created in `[shared-path]/` during admin initialization.

---

## config.json

```json
{
  "primary_store": "",
  "stores": [],
  "fallback_order": [],
  "category_store_map": {}
}
```

---

## users.md

```markdown
# Family Members

| Name | Role | Added |
|------|------|-------|
```

The admin's name and today's date are written here during setup.

---

## list.md

```markdown
# Grocery List

<!-- Items are grouped by store. Each section uses ## [Store Name] as heading. -->
<!-- Unassigned items go under ## Unassigned at the bottom. -->
```

---

## history.md

```markdown
# Grocery History

<!-- Format: YYYY-MM-DD HH:MM | ACTION | item (qty) | store | by user -->
<!-- Actions: ADD, REMOVE, MERGE, UPDATE -->
```

---

## OpenClaw Memory Keys

These keys are saved per-agent (not in the shared path):

| Key | Value | Set when |
|-----|-------|----------|
| `family_grocery_user` | Name registered by admin (e.g. "Nita") | Must be set on the agent before first use — the skill will not ask for it |
| `family_grocery_path` | Shared path (e.g. "/Users/Shared/grocery") | Admin setup, or when a member connects |

- The admin registers names in `users.md`. The member's agent must store the exact same name.
- Name matching is case-insensitive.
- Members also need to save `family_grocery_path` to their own OpenClaw memory when they first connect.

To connect as a member: "Connect to family grocery at [shared-path]" → skill saves path to OpenClaw memory, asks for username if not already stored, then verifies username against `users.md`.
