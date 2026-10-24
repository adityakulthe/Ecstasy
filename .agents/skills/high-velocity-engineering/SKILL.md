---
name: high-velocity-engineering
description: >-
  Use this skill when executing multi-file debugging, performance optimization,
  or feature implementation to maximize speed, accuracy, and verification reliability.
---

# High-Velocity & High-Accuracy Engineering Skill

Apply this execution protocol to maximize speed and accuracy on every engineering task:

## 1. Parallel Discovery & Targeted Context
- **Batch Independent Tool Calls**: When inspecting multiple files or running independent searches, issue `view_file` / `grep_search` calls in a single parallel turn instead of sequential round-trips.
- **Slice Reads (`StartLine`/`EndLine`)**: Never load an entire 600+ line file when `grep_search` gives the exact line numbers; read a focused 60–100 line window.

## 2. Root-Cause First (No Speculative Edits)
- Reproduce the failure or inspect the exact assertion/counterexample first.
- Trace the dataflow from input -> parser/regex -> state transition -> output before writing a single line of patch code.
- If 3 consecutive attempts fail, stop immediately, re-read the failing state, and isolate the violated invariant.

## 3. Atomic Edits & Immediate Verification
- Make all non-overlapping edits across separate files in parallel.
- Run the targeted test immediately (`pytest tests/<file>.py -k <test_name>`), then run the full suite (`pytest -q`) to confirm zero regressions.
