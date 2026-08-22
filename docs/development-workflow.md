# Development Workflow

`isbn-library` uses an issue-first Codex workflow.

## Branch model

```text
Issue
  ↓
issue branch
  ↓
PR
  ↓
develop
  ↓
release PR
  ↓
main
  ↓
deployment
```

- `develop` is the normal integration branch.
- `main` is the release and production branch.
- Feature, fix, chore, and docs branches should target `develop`.
- Do not open feature PRs directly against `main`.

## Issue rules

- Read the full issue body before implementation.
- Treat the issue as the implementation spec.
- Respect `Scope`, `Out of scope`, `Acceptance criteria`, and `Validation`.
- Keep unrelated work out of the same branch or PR.
- Use `1 Issue = 1 branch = 1 PR` by default.

## Release PRs

- Feature PRs into `develop` should use `Related to #<issue-number>`.
- Release PRs from `develop` to `main` may use `Closes #<issue-number>` only when the issue is fully complete.
- Run the required validation again before opening the release PR.

## Validation

The default quality gates are:

- secret scan
- frontend lint
- frontend typecheck
- backend pytest with coverage
- frontend tests
- frontend build
- Playwright E2E
- CDK synth when the local Python environment is ready

The default gate stays no-network. External API calls should be mocked.

