---
name: "api-connector-builder"
description: "Use when a task asks you to add a new provider, connector, or integration to an existing codebase without inventing a parallel architecture, especially when the repository already contains working connectors you should imitate."
---

# API Connector Builder

Use this skill when the task is about adding one new connector-like capability to an existing repository rather than repairing an unrelated bug or starting a brand-new service from zero.

For this task family, treat any shared provider loader as part of the connector contract. If the repository has files such as `schedule_gateway/provider_loader.js`, `scripts/provider_audit.sh`, or `scripts/provider_compare.sh`, you must inspect them before finalizing. A cache keyed only by provider id is not enough when the same process can mount two different data roots.

For this exact template family, do not stop when visible HTTP and export look correct. The visible gateway path can already appear healthy while the delivery is still incomplete. The likely missing work is in shared provider instance scope across multiple mounted roots.

Preserve the existing provider catalog. This task is additive and integrative:
- do not remove `demo_static`
- do not remove `city_reference`
- do not collapse the registry to only `mta_static`
- keep `/v1/providers` returning the existing providers plus the GTFS-backed provider

Concrete rule for this template family:
- If `provider_loader.js` currently looks like `loadProvider(cacheKey, buildProvider)`, that is a likely bug source.
- The fix is usually to make the loader accept an instance key derived from the mounted data root or source path, for example `loadProvider(cacheKey, instanceKey, buildProvider)`.
- Then update every caller that mounts providers from local files or GTFS roots, especially `registry.js` and any same-process compare utility.
- A safe implementation pattern is:
  - build `const compositeKey = `${cacheKey}::${instanceKey}``
  - cache on `compositeKey`
  - pass `dataPath(dataRoot, "...")` or the GTFS root path as `instanceKey`
  - update any compare/audit utility that mounts two roots in one process

## Recommended workflow

1. Inspect at least two existing providers before editing.
   - Compare directory layout, factory shape, config injection, response objects, and export or registration hooks.
   - If a shared provider loader or registry cache exists, inspect it before coding. Treat cache scope and instance keys as part of the delivery surface.
   - Confirm where the repository expects new integrations to be registered.
   - In this template family, inspect these files early when present:
     - `schedule_gateway/registry.js`
     - `schedule_gateway/provider_loader.js`
     - `scripts/provider_audit.sh`
     - `scripts/provider_compare.sh`
   - After reading them, decide whether provider instances are scoped only by provider id or by both provider id and mounted source path. For this task family, the second is the safe choice.
2. Map the delivery surface before coding.
   - List the existing HTTP routes, CLI or script entrypoints, config inputs, and output files the new capability must participate in.
   - Do not fix only one visible path if the same capability is also consumed by export or background flows.
   - If `provider_compare.sh` exists, assume the verifier will care about same-process multi-root behavior even if the instruction only names HTTP and export explicitly.
   - In this template family, if the visible `mta_static` HTTP routes already answer correctly, treat that as a false finish line and continue into the shared loader path.
   - A common miss here is: HTTP and export pass, but `provider_audit.sh` or `provider_compare.sh` reuse the first mounted root because `provider_loader.js` caches too broadly.
3. Keep the new capability inside the repository's current integration shape.
   - Reuse the existing provider interface, factory pattern, data-root injection, and response contracts.
   - Avoid controller-only special cases and avoid adding a second parallel execution path for the same behavior.
   - Preserve existing providers and keep the provider catalog additive. Fix scope and mounting behavior without deleting unrelated providers.
   - If `provider_loader.js` exists, make the instance key include the mounted data root or source path used by that provider.
   - In practice, that usually means editing:
     - `schedule_gateway/provider_loader.js`
     - `schedule_gateway/registry.js`
     - `schedule_gateway/provider_compare.js`
     - and any other provider-mount caller that creates the same provider id under more than one root
   - If those files exist and the task uses multiple mounted roots, you should expect all three to change together.
4. Validate behavior against real task data and against at least one non-visible variation.
   - Re-run the entrypoints with the supplied data and check that the same capability still works when the dataset shape changes.
   - If the repository includes a local audit or probe entrypoint, run it against two different mounted data roots before finalizing.
   - If there is a compare utility for two mounted roots in one process, use it. Provider caches keyed only by provider id are not safe enough for this task shape.
   - Prefer generic parsing and mapping over visible stop-id or route-id special cases.
   - Minimum bar before finalizing when these files exist:
     - `scripts/provider_audit.sh` still returns the second root's own results when `SCHEDULE_AUDIT_COMPARE_ROOT` is set.
     - `scripts/provider_compare.sh` still returns distinct baseline/comparison results when `SCHEDULE_COMPARE_ROOT` is set.
   - If the main HTTP and export path pass before these checks pass, the task is still incomplete.
   - If you cannot run those exact env-var combinations locally, still make the loader and its callers data-root-scoped before you stop.

## Handy checks

- `scripts/probe_registry.js`: prints the current provider catalog and the data root each provider sees.
- `scripts/probe_snapshot.js`: runs the batch export path and prints a compact summary of the generated snapshot.
- `scripts/probe_audit.js`: runs the local audit path once, and can optionally compare a second mounted data root in the same Node process.
- `scripts/probe_compare.js`: runs the local compare path that mounts two data roots in one process. Use this when a shared provider loader or cache is present.

Use the probes to shorten diagnosis time, but always confirm the task's exact contract file, output file name, and required endpoints before finalizing.
