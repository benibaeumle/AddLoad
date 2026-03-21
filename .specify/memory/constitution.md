<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0 (initial ratification)
Added sections:
  - Core Principles (4 principles: Code Quality, Testing Standards, UX Consistency, Performance Requirements)
  - Quality Gates
  - Governance
Modified principles: N/A (initial constitution)
Removed sections: N/A (initial constitution)
Templates reviewed and updated:
  - .specify/templates/constitution-template.md ✅ (source, unchanged)
  - .specify/templates/plan-template.md ✅ (Constitution Check gates aligned)
  - .specify/templates/spec-template.md ✅ (Success Criteria aligned to performance + UX)
  - .specify/templates/tasks-template.md ✅ (task categories reflect principle-driven types)
  - .specify/templates/agent-file-template.md ✅ (no outdated agent-specific references)
  - .specify/templates/checklist-template.md ✅ (no outdated agent-specific references)
Deferred TODOs:
  - RATIFICATION_DATE set to 2026-03-21 (today, first creation)
-->

# AddLoad Constitution

## Core Principles

### I. Code Quality (NON-NEGOTIABLE)

Every unit of code MUST be readable, maintainable, and self-evidently correct to a reviewer
unfamiliar with its history. The following rules are non-negotiable:

- Code MUST follow the language's idiomatic style (PEP 8 for Python, etc.) and pass automated
  linting/formatting checks before any PR is merged.
- Functions and methods MUST have a single, clearly stated responsibility (Single Responsibility
  Principle). Functions exceeding 40 lines MUST be decomposed unless a documented justification
  is provided.
- All public APIs, classes, and non-trivial functions MUST have docstrings or inline documentation
  describing purpose, parameters, return values, and raised exceptions.
- Magic numbers, hardcoded strings, and unexplained constants MUST be replaced with named
  constants or configuration values.
- Dead code, commented-out blocks, and TODO comments older than one sprint MUST be removed or
  converted to tracked issues before merge.

**Rationale**: Unreadable code accumulates hidden defects and slows every future change.
Quality is a prerequisite for sustainable velocity, not a trade-off against it.

### II. Testing Standards (NON-NEGOTIABLE)

Tests MUST be written before or alongside implementation — never deferred as a follow-up task.
The following rules MUST be enforced:

- Every new feature, bug fix, and non-trivial refactor MUST be accompanied by automated tests
  that cover the happy path, at least one error/edge case, and any documented acceptance criteria.
- Unit tests MUST run in isolation (no network, no file system, no database) using mocks/stubs
  where necessary.
- Integration and contract tests MUST cover all inter-service or inter-module boundaries.
- Test coverage MUST NOT regress below the project-defined threshold (default: 80% line coverage).
  Any deliberate exclusion MUST be marked with a `# nocover` annotation and a justification comment.
- Tests MUST be deterministic: no random seeds, no time-dependent assertions without explicit
  controls, no order-dependent test suites.
- The Red-Green-Refactor cycle MUST be followed: tests MUST fail before implementation is written.

**Rationale**: Tests are the only machine-checkable proof that the system behaves as specified.
Deferred testing is not testing — it is deferred risk.

### III. User Experience Consistency

Every user-facing surface (UI, CLI, API responses, error messages) MUST behave consistently and
predictably across the entire product. The following rules apply:

- Terminology, naming conventions, and interaction patterns MUST be unified across all
  user-facing surfaces. A concept named identically in two places MUST behave identically.
- Error messages presented to end users MUST be human-readable, actionable, and free of raw
  stack traces or internal identifiers.
- All user-facing changes MUST be reviewed against existing interaction patterns to detect
  regressions in consistency before merge.
- UI components and CLI commands MUST follow a documented style guide. Introducing a new
  pattern requires explicit justification and style-guide update.
- Accessibility MUST NOT be treated as optional: interactive elements MUST meet WCAG 2.1 AA
  or platform-equivalent standards.

**Rationale**: Inconsistency erodes user trust and increases support burden. Every deviation
from established patterns forces users to relearn and introduces latent confusion.

### IV. Performance Requirements

Performance is a feature, not an afterthought. Every feature MUST define and meet explicit
performance targets before it can be considered complete:

- Each feature specification MUST declare performance acceptance criteria (e.g., p95 latency,
  throughput, memory ceiling, startup time) during the design phase — not post-implementation.
- Performance-sensitive code paths MUST be benchmarked. Benchmark results MUST be committed
  alongside the implementation so regressions are detectable in CI.
- No change that causes a measurable regression (>10% on any declared performance metric)
  may be merged without a documented justification and an approved remediation plan.
- Resource leaks (memory, file handles, connections, threads) MUST be treated as blocking bugs,
  not technical debt.
- Premature optimization is prohibited: MUST NOT optimize without a benchmark proving a
  performance problem exists. Complexity introduced for performance MUST be justified by data.

**Rationale**: Performance regressions compound silently. Declaring targets upfront creates
accountability and makes regressions visible at the point of introduction, not in production.

## Quality Gates

Every pull request or change set MUST pass all of the following gates before merge:

- **Linting & Formatting**: Automated linter and formatter report zero violations.
- **Test Suite**: All tests pass; coverage threshold is met; no skipped tests without annotation.
- **Performance Benchmarks**: Declared performance metrics show no regression >10%.
- **Constitution Check**: Reviewer explicitly confirms compliance with all four Core Principles
  in the PR description.
- **UX Review**: Any user-facing change is confirmed consistent with existing patterns and the
  style guide.

## Development Workflow

- Features MUST be developed against a specification (`spec.md`) and implementation plan
  (`plan.md`) before coding begins.
- Tasks MUST be tracked in `tasks.md` with explicit dependency order.
- Each user story MUST be independently testable and deployable as an MVP increment.
- Complexity violations MUST be logged in the Complexity Tracking table in `plan.md` before
  the complexity is introduced — not after.

## Governance

This constitution supersedes all other project-level practices. In cases of conflict, this
document takes precedence.

**Amendment procedure**:

1. Propose the amendment in writing, stating which principle is affected and why.
2. Increment `CONSTITUTION_VERSION` per semantic versioning rules (see below).
3. Update all dependent templates in `.specify/templates/` to reflect the change.
4. Record the amendment in a Sync Impact Report (HTML comment at top of this file).
5. Obtain explicit approval before the amendment is considered ratified.

**Versioning policy**:

- MAJOR: Removal or redefinition of an existing principle (backward incompatible governance change).
- MINOR: New principle or section added, or material expansion of existing guidance.
- PATCH: Wording clarifications, typo fixes, non-semantic refinements.

**Compliance review**: All PRs MUST include a Constitution Check confirming adherence to all
four Core Principles. Violations block merge unless a justified exception is recorded in the
Complexity Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-03-21 | **Last Amended**: 2026-03-21
