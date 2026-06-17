# Store Management — Family Grocery

## Adding a Store

Any user can add a store. Triggers: "Add store [name]", "Add store [name] at [address]"

### Flow

1. **Check for existing store** — if a store with the same name already exists in `config.json`, ask: "[Store] is already registered at [address]. Update the address or cancel?"

2. **Resolve address**:
   - User provided an address in the command → go to step 3.
   - No address provided + web search available:
     - Search: "[store name] store address"
     - Present result: "Found: [Store Name] — [address]. Is this the right location? (yes / enter correct address)"
     - User confirms → use found address.
     - User provides a different address → use user's address.
   - No address provided + web search unavailable:
     - Ask: "What's the address for [store]?"

3. **Resolve store hours** (if web search available):
   - Search: "[store name] [address] store hours"
   - Present result: "Found hours: Mon–Sat 8am–9pm, Sun 9am–7pm. Correct? (yes / enter correct hours)"
   - User confirms → use found hours.
   - User provides different hours → use user's hours.
   - Web search unavailable → ask: "What are the store hours for [store]? (or skip)"
   - User skips → store hours left empty, can be added later.

4. **Write to `config.json`** under `stores` array:
   ```json
   { "name": "[Store Name]", "address": "[Full Address]", "hours": "[Store Hours]" }
   ```

5. **Confirm**: "Added [Store Name] — [address] ([hours]) to the store list."

---

## Setting the Primary Store (Admin only)

Triggers: "Set [store] as primary", "Make [store] the default store"

1. Verify store exists in `config.json`. If not → "I don't have [store] in the store list. Add it first."
2. Update `primary_store` in `config.json`.
3. Confirm: "[Store] is now the primary store. Items with no store specified will go here by default."

---

## Setting Fallback Order (Admin only)

Triggers: "Set fallback order: [store A] → [store B] → [store C]", "Fallback order: ..."

1. Verify all named stores exist in `config.json`.
2. Update `fallback_order` array in `config.json`.
3. Confirm: "Fallback order set: [store A] → [store B] → [store C]."

---

## Category→Store Mappings (Admin only)

Triggers: "Assign [category] to [store]", "Map [category] items to [store]"

Common categories: produce, dairy, meat, frozen, bakery, bulk, pharmacy, electronics, household, beverages

1. Verify store exists in `config.json`.
2. Update `category_store_map` in `config.json`.
3. Confirm: "[Category] items will now default to [store]."

To view current mappings: "Show category mappings"
Output: list each category → store from `config.json`.

---

## Listing Stores

Triggers: "What stores do we have?", "Show stores", "List stores"

Output:
```
Primary: Whole Foods — 123 Main St, Anytown
Fallback order: Whole Foods → Costco → Target

All stores:
- Whole Foods — 123 Main St, Anytown
- Costco — 456 Oak Ave, Anytown
- Target — 789 Elm Rd, Anytown
```

---

## config.json Reference

```json
{
  "primary_store": "Whole Foods",
  "stores": [
    { "name": "Whole Foods", "address": "123 Main St, Anytown", "hours": "Mon–Sat 8am–9pm, Sun 9am–7pm" },
    { "name": "Costco", "address": "456 Oak Ave, Anytown", "hours": "Mon–Fri 10am–8:30pm, Sat 9:30am–6pm, Sun 10am–6pm" },
    { "name": "Target", "address": "789 Elm Rd, Anytown", "hours": "8am–10pm daily" }
  ],
  "fallback_order": ["Whole Foods", "Costco", "Target"],
  "category_store_map": {
    "produce": "Whole Foods",
    "dairy": "Whole Foods",
    "bulk": "Costco",
    "electronics": "Target",
    "household": "Target"
  }
}
```
