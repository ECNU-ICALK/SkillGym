---
name: single-file-briefing-deck
description: Deliver a contract-complete single-file HTML briefing deck from local data snapshots, wireframes, and editorial notes. Use when a task asks for a browser-run briefing artifact with fixed page order, required modules, and local-file playback.
---

# Single File Briefing Deck

Build a browser-run briefing site that behaves like a compact deck while staying inside one HTML file.

## When to Use This Skill

- the task asks for a single-file HTML briefing or deck
- the workspace includes a contract, page outlines, or wireframes
- the deliverable must run from a local file path
- required charts, tables, and explanations must be assembled page by page

## Non-Negotiables

1. Read the contract before changing code.
2. Track page completion against the contract, not against visual intuition.
3. Keep one HTML output file and one manifest file.
4. Validate navigation and viewport fit in a browser before handoff.
5. Keep chart explanation in the same page section as the chart it explains.

## Working Pattern

### 1. Build a Contract Checklist

Start by reading:

- `/app/power_brief/contracts/layout_contract.json`
- `/app/power_brief/outlines/slide_outline.json`
- `/app/power_brief/notes/editorial_notes.md`
- `/app/power_brief/wireframes/`

Use the helper:

```bash
python3 {baseDir}/scripts/contract_check.py
```

This prints the page order, required modules, required charts, and wireframe files so you can work through the deck page by page.

### 2. Lock the Data Years

Before writing page copy, identify:

- latest common World Bank population year
- latest common World Bank GDP year
- latest common CO2 year
- latest common electricity year
- recent CO2 window required by the contract

Do not guess these years from memory. Derive them from the shipped files.

Use:

```bash
python3 {baseDir}/scripts/data_context.py
```

This prints the common years, the cross-country snapshot rows, and the recent CO2 window in one place so you can build copy and charts from the same dataset reading pass.

### 3. Assemble One Page at a Time

For each page:

- match the required page id
- place every required module
- place every required chart id
- keep the page title aligned with the outline
- add short explanation text where the contract requires it

Treat the wireframe as a page composition guide. It does not need pixel-perfect matching, but the page should respect the same hierarchy and block placement.

### 4. Use Stable Markers

Prefer predictable HTML markers so contract checks stay easy:

- `data-page-id` for each page
- `data-module-id` for each required module
- `data-chart-id` for each chart
- `data-role="progress"` for the progress label

### 5. Audit in the Browser

After the site builds, run:

```bash
python3 {baseDir}/scripts/browser_audit.py /app/output/north_america_power_mix_brief.html
```

The audit checks:

- every required page appears
- `Previous` and `Next` buttons exist
- progress text exists
- each page fits the required viewport profiles without internal scroll

If the audit fails, fix the failing pages before handoff.

### 6. Align the Manifest

The manifest should mirror the final HTML:

- page ids and order
- chart ids
- module ids
- data files used
- metric years
- embedded assets

Do not leave the manifest as a placeholder summary.

## Failure Patterns to Avoid

- building a generic long webpage instead of a page-by-page deck
- skipping wireframe review and then missing modules
- writing chart captions without the chart
- finishing the HTML without browser verification
- hardcoding years or findings that do not match the bundled data

## Handoff Checklist

- single HTML file exists
- manifest exists
- all contract pages exist in order
- navigation works by button and keyboard
- every page fits the viewport profiles
- no placeholder text remains
