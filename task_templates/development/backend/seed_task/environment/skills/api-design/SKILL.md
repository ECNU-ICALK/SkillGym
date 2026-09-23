---
name: "api-design"
description: "Use when a task asks you to repair or standardize a partner-facing HTTP API without changing business scope, especially when symptoms involve unstable pagination, inconsistent response envelopes, duplicate writes on retries, or missing rate-limit semantics."
---

# API Design

Use this skill when a task asks you to repair or standardize a partner-facing HTTP API without changing the business scope. It is especially useful when the symptoms mention inconsistent resource routes, unstable pagination, mixed response shapes, duplicate writes on retries, or missing rate-limit semantics.

## Recommended workflow

1. Map the canonical resource surface first.
   - List the required routes, methods, request headers, query parameters, and success/error response shapes.
   - Keep one coherent versioned API family; do not leave the original canonical routes broken while adding a second parallel surface.
2. Normalize cross-cutting behavior before patching endpoint-specific bugs.
   - Authentication failures, authorization failures, validation errors, missing resources, conflicts, and rate limits should be distinguishable by both status code and machine-readable error code.
   - Make success bodies and error envelopes predictable across endpoints.
3. For list endpoints, apply the data pipeline in the correct order.
   - Filter first, then sort deterministically, then paginate.
   - Re-run the same query twice and confirm the returned slice is identical.
4. For create endpoints, handle retry safety explicitly.
   - Require and persist `Idempotency-Key` behavior for non-idempotent writes.
   - A replay with the same key and same payload should resolve to one logical write.
   - Reusing the same key with a different payload must fail safely.
5. Preserve real persistence and runtime state.
   - Fix the existing code path rather than replacing the service with static output.
   - Confirm that a successful write is visible from subsequent GET calls.
6. Validate rate-limit semantics end to end.
   - Limited and non-limited requests should be distinguishable.
   - Include the expected quota and retry headers on both success and `429` responses.

## Handy checks

- `scripts/probe_contract.js`: smoke-tests canonical routes, envelope shapes, auth classes, and pagination stability.
- `scripts/probe_idempotency.js`: exercises replay and conflicting reuse of one idempotency key.

Use the probes to shorten diagnosis time, but always check the task's exact route names, field names, and allowed error categories before finalizing.
