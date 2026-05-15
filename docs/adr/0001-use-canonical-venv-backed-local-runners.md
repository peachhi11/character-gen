# ADR-0001: Use Canonical Venv-Backed Local Runners

**Date**: 2026-05-15
**Status**: Accepted
**Decision Makers**: Megan McKinnon, Codex

## Context

CharacterGen local verification was vulnerable to interpreter drift: a command run with bare `python3` could skip, fail, or pass differently than the app's actual virtual environment. The project also needs one predictable launch path on this Mac, because Qt/PyQt behavior is sensitive to the Python environment and platform setup. The goal is to remove ambiguity so "passed locally" always means "passed under the CharacterGen runtime."

## Decision

We use `./start.sh` as the only supported local launch path and `./test.sh` as the only supported full test path. Both scripts resolve and verify the shared CharacterGen virtual environment through `scripts/ensure_charactergen_venv.sh` before running app or test code.

## Alternatives Considered

### Alternative 1: Let developers run `python3` commands directly
- **Pros**: Simple and familiar for ad hoc testing.
- **Cons**: Uses whichever interpreter happens to be first on the shell path, which can miss venv-only dependencies or behave differently from the app runtime.
- **Why not chosen**: It preserves the exact failure mode this decision is meant to remove.

### Alternative 2: Document the venv path but keep manual commands
- **Pros**: Avoids adding wrapper scripts and keeps command behavior transparent.
- **Cons**: Relies on humans to remember the correct interpreter and environment variables every time.
- **Why not chosen**: The project needs a reliable default, not a convention that can be bypassed accidentally.

### Alternative 3: Use a repo-local `.venv`
- **Pros**: Common Python project layout and easy to inspect from the repository root.
- **Cons**: This machine already has a shared CharacterGen venv expectation, and multiple worktrees can drift if each manages a separate environment.
- **Why not chosen**: A shared user-level CharacterGen venv better supports the current local workflow across related worktrees.

## Consequences

### Positive Consequences
- Local launch and full tests use the same Python environment and pinned runtime dependencies.
- Tests can fail loudly when run outside the canonical runner instead of producing misleading results.
- New contributors have one documented launch command and one documented test command.

### Negative Consequences
- Ad hoc `python3 -m unittest` is intentionally unsupported for full-suite verification.
- The wrapper scripts become part of the test contract and must be maintained with dependency changes.

### Risks
- The shared venv can still drift if dependency pins change without rerunning the resolver. This is mitigated by hashing `requirements.txt` and reinstalling when it changes.
- Qt can behave differently on non-macOS systems. This ADR records the local macOS workflow; cross-platform support should be captured in a future ADR if it becomes a project goal.
