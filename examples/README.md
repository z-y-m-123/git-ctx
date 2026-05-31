# Example

This directory contains a worked example of a `.ai-rules.json` and its version history.

## Scenario

You're building a **Python FastAPI backend** with an AI coding assistant. Over several iterations, you refine the rules to improve the assistant's output:

| Version | Message | What changed |
|---|---|---|
| 1 | init | Default template |
| 2 | add Python + FastAPI stack | Declared tech stack |
| 3 | add coding standards | Added style / linting rules |
| 4 | add architecture decisions | Documented key design choices |
| 5 | switch to async SQLAlchemy | Updated tech stack + architecture |

## Files

- [`.ai-rules.json`](./.ai-rules.json) — the working file at version 5
- The `.git-ctx/` directory (not included here) would contain snapshots `1.json` through `5.json`

## Try It Yourself

```bash
cd examples/
git-ctx init

git-ctx diff
git-ctx commit -m "add Python + FastAPI stack"
# ... repeat for each version ...

git-ctx log

# New features
git-ctx tag add 5 production
git-ctx star 5
git-ctx branch experiment
git-ctx switch experiment
git-ctx validate
git-ctx export -f claude
```
