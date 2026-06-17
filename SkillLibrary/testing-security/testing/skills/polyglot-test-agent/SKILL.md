---
name: polyglot-test-agent
description: Generate or extend high-quality automated tests across multiple languages and test frameworks. Use when the task is to add unit or integration tests and the stack may be Jest, Pytest, JUnit, NUnit, MSTest, TUnit, Vue/Pinia, Spring Boot, or a mixed-language codebase.
---

# Polyglot Test Agent

Use this skill when the user asks for tests and the repository is not limited to a single language or framework.

## Goals

- Identify the active test stack before writing tests.
- Reuse existing project test conventions instead of inventing new patterns.
- Prefer focused tests that validate behavior, not implementation trivia.
- Add or extend fixtures, helpers, and mocks only when they are required by the target behavior.

## Workflow

1. Detect the language, package manager, and test framework already used by the repository.
2. Inspect neighboring tests for naming, setup, fixtures, assertions, and mocking patterns.
3. Map the requested behavior into concrete test cases:
   - happy path
   - validation and error paths
   - edge cases
   - regression coverage for the reported bug or scenario
4. Write tests in the native framework for that area:
   - JavaScript/TypeScript: Jest, Vitest, Playwright, or existing frontend tooling
   - Python: Pytest or existing project tooling
   - Java/Kotlin: JUnit or Spring test patterns
   - .NET: xUnit, NUnit, MSTest, or TUnit
   - Vue: follow Pinia/component patterns already present
5. Run the narrowest relevant test command first, then broaden only if needed.

## Rules

- Do not introduce a new framework if the project already has one.
- Do not rewrite existing tests unless the task requires it.
- Keep test data minimal and readable.
- Mock only unstable or external boundaries; prefer real code paths when practical.
- If the code is hard to test, note the seam and add the smallest viable refactor to enable coverage.

## Output

- Add tests in the closest existing test location.
- Match local naming and folder conventions.
- Report what behavior is covered and what remains unverified if execution is blocked.
