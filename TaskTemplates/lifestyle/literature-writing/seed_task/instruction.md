You are preparing a launch copy package for a developer tool campaign.

Input data is available in the local environment:

- `/workspace/work_order.json`: campaign id, required deliverables, mandatory topics, audience notes, and word limits.
- `/workspace/service_manifest.json`: the local content-service endpoint map for this task.
- `http://127.0.0.1:8080`: local content service with source material, terminology guidance, banned phrases, a rejected draft record, and validation support.
- `/workspace/notes/editorial_constraints.json`: release constraints and wording requirements.
- `/workspace/examples/approved_copy/`: approved reference copy for tone alignment.
- `/workspace/drafts/rejected_copy.json`: the previous draft package that failed review.

Your task:

1. Read the work order and collect the source material needed for this campaign from the local environment.
2. Produce a publishable developer-facing copy package that covers all required deliverables and mandatory topics.
3. Keep the writing clear, technically grounded, and suitable for developers. Use only information supported by the provided materials.
4. Include source tracking for material claims used in the final copy.
5. Include brief revision notes describing the main edits made to improve accuracy, clarity, and tone.
6. Ensure the final package satisfies the task requirements and any validation provided in the local environment.

Output:

Save the final result to `/root/final_launch_copy_package.json` as valid UTF-8 JSON with this top-level structure:

```json
{
  "campaign_id": "string",
  "source_trace": [
    {
      "source": "string",
      "purpose": "string"
    }
  ],
  "deliverables": {
    "homepage_hero": {
      "headline": "string",
      "subheadline": "string",
      "body": "string"
    },
    "feature_page_section": {
      "title": "string",
      "body": "string"
    },
    "docs_intro": {
      "title": "string",
      "body": "string"
    },
    "release_note": {
      "title": "string",
      "what_changed": "string",
      "how_it_works": "string",
      "why_it_matters": "string"
    },
    "short_update": {
      "body": "string"
    }
  },
  "fact_ledger": [
    {
      "claim_id": "string",
      "claim": "string",
      "source": "string",
      "used_in": ["string"]
    }
  ],
  "revision_notes": [
    {
      "issue": "string",
      "change": "string"
    }
  ],
  "quality_report": {
    "scorecard": {},
    "banned_phrase_scan": [],
    "final_gate": {
      "passed": true,
      "details": "string"
    }
  }
}
```

Notes:

- Cover every required deliverable.
- In `source_trace`, list each workspace file and each local service endpoint you actually used with its exact local path or local endpoint string, such as `/workspace/work_order.json` or `/api/document/parallel_agents_docs`.
- Use `source_trace` for content and editorial sources used to draft or revise the package. Do not add validation-only endpoints there.
- Do not replace local source identifiers with public reference URLs in `source_trace` or `fact_ledger`.
- In `fact_ledger`, reuse the task fact ids from the provided materials when available, keep `source` tied to the supporting file or document endpoint, and use exact deliverable field paths in `used_in`, such as `homepage_hero.body` or `release_note.how_it_works`.
- Do not invent capabilities, metrics, dates, compatibility statements, or endorsement claims.
- Do not modify the local content service, input files, tests, or validation scripts.
- Do not hardcode validation results or write output to a different path.
- Do not rely on private accounts, login state, or external third-party services.
