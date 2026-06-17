You are taking over an AI ticket-triage API for a customer support operations team. After a recent emergency change, on-call engineers reported that this service is no longer suitable as a stable auxiliary integration: results are inconsistent across different runtime modes, batch requests sometimes fail to return a complete set of results, and manual escalation and knowledge suggestions are no longer reliable for some tickets. You need to fix the existing service without changing the business boundaries so it again meets production integration requirements.

Input data is in `/app/workspace/`:

- `service/`: existing Node.js / TypeScript HTTP service code, including external endpoints for single-ticket triage, batch triage, and review suggestions.
- `data/tickets/`: realistic ticket samples, including in-domain and out-of-scope text, language, channel, and priority-related fields.
- `data/contracts/`: triage output contracts, field enums, provider adapter shapes, and related rules.
- `data/policies/`: queue mapping, manual escalation rules, knowledge suggestion constraints, and batch behavior requirements.
- `data/sandbox_cases/`: local cases and response examples for sandbox mode.
- `scripts/`: startup, reset, and baseline self-check scripts.

The environment also includes the following baseline directory:

- `/services/provider-sim/`: a local downstream provider simulator; it is part of the environment baseline and must not be edited.

Your tasks:

1. Fix the three HTTP flows (single-ticket triage, batch triage, review suggestions) so the service again satisfies the delivery contract relied upon by existing integrators; do not evade the existing issues by adding a parallel set of endpoints.
2. Ensure single and batch requests return stable, complete, machine-processable results across the existing runtime modes; within a batch, tickets must not be silently dropped, and failures must not be disguised as successes.
3. Preserve the existing business meaning and output capabilities so queues, intents, recommended actions, cited evidence, and manual escalation reasons are still produced from real input data and existing rules; when some information cannot be matched, the response structure must still remain stable.
4. When the live flow receives downstream results that are incomplete, unparsable, or untrustworthy, do not rewrite the same ticket into a different business conclusion; you must continue returning stable results based on the system-of-record facts already present in the repository.
5. Preserve and fix the real runtime flows, continuing to use the existing startup method, sandbox data, the local downstream provider simulator, and the existing API paths; you must not rewrite the task into an offline script, static result generation, or a manual process.
6. Keep the existing business boundaries unchanged and continue using the existing data files in the repository as the system-of-record sources.

Output:

- Directly modify the existing service code under `/app/workspace/service/`.

Notes:

- If needed, you may add a small amount of test helper code or server-side helper implementation.
- Preserve the existing startup entrypoints; validation will start the service using the repository's default method and verify via HTTP calls.
- After startup, the service must continue to provide single-ticket triage, batch triage, and review suggestions externally; it must not be downgraded to only output a report or only handle a single fixed sample.
- You may add necessary input validation, error handling, and server-side helper logic, but do not change the task's business goals.
- Do not modify any input data under `/app/workspace/data/` to evade issues.
- Do not claim the issue is solved by modifying existing self-checks, sample tests, or startup flows; you must fix the service itself, not the validation criteria.
- Do not edit the hidden environment baseline files under `/services/provider-sim/`.
- It is explicitly forbidden to replace real flows or remove functionality to evade issues. Also do not remove either the sandbox or live path, remove the batch endpoint, remove knowledge suggestions, remove manual escalation logic, or bypass downstream calls.
- Do not add a second service, reverse proxy, sidecar script, or pure mock responses to bypass the existing implementation.
- Do not hard-code outputs so they only work for fixed tickets, a fixed batch size, a fixed intent, a fixed language, or a fixed order.
- Do not fix only the happy path; the service must continue to correctly handle the different channels, different intents, batch inputs, invalid inputs, and manual escalation cases that already exist in the current dataset.
