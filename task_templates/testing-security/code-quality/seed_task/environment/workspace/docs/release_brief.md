Toolchain Release Digest collects local npm-registry and GitHub-release snapshots for TypeScript, ESLint, and Prettier and turns them into a compact release matrix for internal review.

Release promotion rules for this package:
- The candidate must pass the repository's existing verification loop.
- The candidate must satisfy the remaining promotion review gates in the release contract.
- Audit output should summarize the current candidate only; no repository files should be edited during assessment.
