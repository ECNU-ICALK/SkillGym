# List Operations — Family Grocery

## Adding an Item

### Full add flow

1. **Parse input** — extract item name and quantity from natural language.
   - "Add milk" → item: milk, qty: default (1)
   - "Add 2L of milk" → item: milk, qty: 2L
   - "Add a dozen eggs" → item: eggs, qty: x12

2. **Duplicate check** — fuzzy-match (case-insensitive, singular/plural) against all entries in `list.md`.
   - Match found → "Nita already added eggs (x12) on Mar 10. Add more, update quantity, or cancel?"
     - "Add more" → merge qty (e.g. x12 + x6 = x18), log merge in `history.md`
     - "Update to X" → replace qty, log update in `history.md`
     - "Cancel" → stop, do nothing
   - No match → continue to step 3.

3. **Resolve store** — in this order:
   1. Did the user specify a store? ("Add milk at Whole Foods") → use it.
   2. Does `config.json` have a category mapping for this item type? (e.g. dairy → Whole Foods) → use it, tell user: "Adding to Whole Foods (dairy category default)."
   3. Fall back to `primary_store` in `config.json` → tell user: "Adding to [primary store] (default)."

4. **Check availability** (if web search available):
   - Search: "[item] available at [store name] [store address]"
   - Found: "Confirmed available at [store]."
   - Not confirmed: "Couldn't confirm availability at [store] — adding anyway."
   - Web search unavailable: note once, proceed.

5. **Ask about fallback stores** (only if no fallback recorded for this item's store yet):
   - "Any fallback stores for items from [store]? (e.g. if they're out of stock)"
   - Save answer to `config.json` under `fallback_order` if not already set.

6. **Write to `list.md`** under the resolved store section:
   ```
   - [item] ([qty]) — added by [user] on [YYYY-MM-DD]
   ```

7. **Confirm**: "Added [item] ([qty]) to [store name]."

---

## Removing an Item

Triggers: "Remove [item]", "I got the [item]", "Delete [item]", "Cross off [item]"

1. Search `list.md` for the item (case-insensitive, fuzzy match).
2. Not found → "I don't see [item] on the list."
3. Found in one store → confirm and remove.
4. Found in multiple stores → ask: "I see [item] at [store A] and [store B]. Remove from which? (both / [store A] / [store B])"
5. Write removal to `history.md`:
   ```
   [YYYY-MM-DD HH:MM] REMOVE: [item] ([qty]) from [store] — by [user]
   ```
6. Confirm: "[Item] removed from [store] by [user]."

---

## Viewing the List

Triggers: "Show me the grocery list", "What do we need?", "Show the list"

Output format — group by store, sorted by store name. Each store heading includes full address. End with a total item count.

```
🏪 Whole Foods (123 Main St, Anytown) — Mon–Sat 8am–9pm, Sun 9am–7pm
- Milk, 2L
- Eggs, x12

🏪 Costco (456 Oak Ave, Anytown) — Mon–Fri 10am–8:30pm, Sat 9:30am–6pm, Sun 10am–6pm
- Olive oil, 3L

📋 Unassigned
- Batteries, x4

Total items: 4
```

- If store hours are missing for any store in the list:
  1. Before displaying, check `config.json` for stores with empty/missing `hours`.
  2. If web search available → search "[store name] [address] store hours" for each.
  3. Present results: "I found hours for [store]: [hours]. Correct? (yes / enter correct hours)"
  4. Save confirmed hours to `config.json`.
  5. Then display the list with the newly resolved hours.
  6. If web search unavailable → ask: "What are the hours for [store]? (or skip)"
  7. If user skips → omit hours from that store's heading for now.

- If list is empty → "The grocery list is empty."
- Unassigned items (no store) always appear last under `📋 Unassigned`.
- Total count includes all items across all stores (including unassigned).

---

## Viewing History

Triggers: "What changed recently?", "Show history", "What did Nita add?"

Read `history.md` and surface the relevant entries in plain language:

- "Nita added eggs (x12) on Mar 10."
- "Abhishek removed milk on Mar 11."
- "Merged: eggs x12 + x6 = x18 (Nita + Abhishek) on Mar 12."

Support filters: by user name, by date range, by action type (add/remove/merge).

---

## list.md Format

Group items by store. Each store section starts with a heading:

```markdown
## Whole Foods

- Milk (2L) — added by Nita on 2026-03-10
- Eggs (x12) — added by Abhishek on 2026-03-11

## Costco

- Olive oil (3L) — added by Nita on 2026-03-09

## Unassigned

- Batteries (x4) — added by Abhishek on 2026-03-12
```

---

## history.md Format

```markdown
# Grocery History

- 2026-03-10 09:14 | ADD | eggs (x12) | Whole Foods | by Nita
- 2026-03-11 14:02 | ADD | milk (2L) | Whole Foods | by Abhishek
- 2026-03-12 08:30 | MERGE | eggs x12+x6→x18 | Whole Foods | by Nita + Abhishek
- 2026-03-13 10:05 | REMOVE | milk (2L) | Whole Foods | by Abhishek
```
