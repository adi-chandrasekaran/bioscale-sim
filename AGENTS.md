# Agent Constitution

This repository is maintained by coding agents and humans together. The goal is to keep the codebase understandable, reproducible, and easy to change without surprise regressions.

## Core rules

1. Preserve user work. Do not revert or overwrite unrelated changes that already exist in the worktree.
2. Prefer small, targeted edits over broad rewrites.
3. Make the repo easier to understand after each task: improve names, docs, config, or checks when the change naturally exposes a gap.
4. Keep behavior explicit. If a file is intended as demo data, fallback data, or generated output, say so in code or docs.
5. Treat docs as part of the product. If behavior changes, update the nearest relevant documentation.

## Change discipline

- Read the surrounding code before editing.
- Use repository-native tooling where possible.
- Keep manual edits deliberate and reviewable.
- Avoid introducing new dependencies unless they are justified by a concrete repo need.
- If a task touches multiple layers, update the tests or checks that exercise those layers.

## Validation

- Run the smallest verification that proves the change.
- Prefer tests, type checks, or build checks over manual reasoning alone.
- If verification cannot be completed, say exactly why.

## Documentation rules

- Keep the docs folder organized by purpose, not chronology.
- Put stable reference material near other reference material.
- Put plans and roadmaps together.
- Put audits and postmortems together.
- Prefer an index file over a flat, unstructured pile of markdown.

## Safety

- Never use destructive git commands unless explicitly asked.
- Never assume tracked generated files should be deleted just because they look disposable.
- When a repository already contains staged or modified work, treat it as intentional unless the user says otherwise.
