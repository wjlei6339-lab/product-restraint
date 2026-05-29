# Repository Guidelines

## Project Structure & Module Organization

This repository is a Claude Code skill project, not an application. The primary deliverable is the `product-restraint` skill prose.

- `SKILL.md`: primary skill behavior, including frontmatter, review principles, scoring rubric, template, and self-checks.
- `references/frameworks.md`: supporting framework notes used when deeper rationale is needed.
- `docs/design.md`: design rationale and product decisions for the skill.

## Build, Test, and Development Commands

There is no package build step and no automated test suite. Skill behavior changes are made by editing Markdown and validating manually: open a Claude Code session, describe a product idea to trigger the skill, and inspect the three-part output against the goals in Testing Guidelines.

The skill is wired up via a symlink: `~/.claude/skills/product-restraint` should point at this repository.

## Coding Style & Naming Conventions

Most files are Markdown or JSON. Keep prose concise, concrete, and in Chinese unless a surrounding file requires English. Preserve the direct, skeptical product-review tone.

When editing `SKILL.md`, keep the three-part output contract intact: feasibility evaluation, short summary, and detailed explanation. If you add or rename scoring dimensions, update the rubric and output template together.

## Testing Guidelines

There is no automated test suite. After changing skill behavior, validate manually: open a Claude Code session, describe a product idea, and inspect the three-part output against these goals:

- weak wrapper ideas should receive specific, non-generic rejection;
- vague one-liners should treat missing information as risk;
- evidence-backed ideas should not be dismissed reflexively.

## Commit & Pull Request Guidelines

Recent history uses concise commits with optional Conventional Commit style. Prefer imperative, scoped messages such as `docs: clarify review workflow`.

Pull requests should describe the behavior change. For substantial prompt changes, include before/after notes.

## Security & Configuration Tips

Do not create a second source of truth for the skill. Edit this repository directly and rely on the symlink. Avoid committing credentials, local CLI state, or cache files.
