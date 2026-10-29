# Domain documentation

## Before exploring

Use the single-context layout: read root `GLOSSARY.md` and the ADRs in `docs/adr/` that relate to the work. If these do not exist, proceed without creating placeholders. Domain-modeling work creates them when terminology or decisions are actually resolved.

The assistant feature specification is `docs/ASSISTANT_SPEC_V1.md`. Its implementation and verification limits are recorded in `docs/ASSISTANT_DIAGNOSTICS.md`. Read these when changing assistant diagnosis, incident state, runbook permissions, or ticket handoff. Consult `docs/SRS.md` and `docs/SDD.md` for broader requirements and design.

## Use consistent terminology

Use glossary terms in issues, hypotheses, tests, and documentation. If a necessary term is absent, distinguish a genuine domain gap from an unnecessary synonym; resolve real gaps through domain modeling.

## Respect recorded decisions

When a proposed change conflicts with an ADR, identify the ADR and explain why reopening the decision is warranted. Do not silently override it. Keep business decisions and their rationale in ADRs rather than expanding the always-loaded agent guidance.

