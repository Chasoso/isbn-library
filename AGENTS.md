# AGENTS.md

This repository uses issue-first, Codex-friendly rules so short prompts can be executed safely.

## Repository rules

- The development base branch is `develop`.
- Never push directly to `develop` or `main`.
- GitHub Issues are the source of implementation requirements.
- Read the full issue body before changing code.
- Respect `Scope`, `Out of scope`, `Acceptance criteria`, and `Validation`.
- Keep unrelated changes out of the same branch or PR.
- Do not use `git commit --no-verify`.
- Do not use `git push --no-verify`.
- Do not create a PR if required validation fails.
- Do not commit secrets, credentials, or tokens.
- Do not weaken tests or quality gates to make CI pass.

## Execution modes

### Single-issue mode

Use this by default.

- 1 issue
- 1 branch
- 1 PR

Branch examples:

- `feat/issue-1-rakuten-books-fallback`
- `feat/issue-2-ndl-fallback`
- `feat/issue-3-manual-book-registration`
- `fix/issue-xxx-...`
- `chore/issue-xxx-...`
- `docs/issue-xxx-...`

For feature branches that target `develop`, use `Related to #<issue-number>` instead of `Closes #<issue-number>`.

### Work-package mode

Use work-package mode only when the human explicitly groups multiple related issues into one branch and PR.

Recommended only when the issues:

- share one goal or milestone
- have a clear execution order
- are reviewable together
- are technically related or dependent

Rules:

- 1 work package
- 1 branch
- 1 PR
- keep commit boundaries as focused as practical
- preserve issue order
- do not mix unrelated milestones

## Branch flow

- Feature, fix, chore, and docs branches should target `develop`.
- `develop` is the normal integration branch.
- `main` is the release and production branch.
- Do not open feature PRs directly against `main`.
- Promote `develop` to `main` with a release PR.

## Commit policy

- Use Conventional Commits.
- Keep commits focused on the issue or work package.

Examples:

```text
feat: add Rakuten Books lookup fallback
fix: handle missing bibliographic data
test: add lookup fallback coverage
chore: add Codex quality gates
docs: document development workflow
```

## Validation policy

Run the repository's real validation commands only.

Required gates for code changes:

- secret scan with Gitleaks
- frontend lint
- frontend typecheck
- backend pytest with coverage
- frontend tests
- frontend build
- Playwright E2E
- CDK synth when the local environment has the required Python dependencies

Do not invent validation commands that do not exist in this repository.
Do not weaken validation to make a PR green.
Do not include network-dependent tests in the default gate.
Mock external API calls by default.

## Retry policy

For transient or environment-related failures:

1. Retry once without code changes.
2. If it fails again, inspect the logs and fix the in-scope problem.
3. Retry once after the fix.
4. Stop if the third attempt still fails.

Do not auto-retry authentication failures, permission failures, secret-scan findings, or destructive operations.

## Autonomous decision boundary

Codex may proceed without asking when the change stays within issue scope and repository patterns.

Stop and ask before making changes that would:

- change authentication or authorization
- require production credentials
- perform destructive operations
- change AWS deployment architecture significantly
- delete or migrate DynamoDB data
- exceed the issue scope
- conflict with another issue

## Self-review before PR

Before creating a PR:

- Re-read the issue body.
- Review the full diff.
- Verify acceptance criteria.
- Check for unintended files.
- Search for secrets, debug code, TODOs, and temporary files.
- Re-run validation.

## PR requirements

The PR body must include:

- Summary
- Related Issue
- Changes
- Validation
- Commands run
- Notes for reviewer

For release PRs from `develop` to `main`, use `Closes #<issue-number>` only for issues that are fully complete.

