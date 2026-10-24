# Ecstasy — Agent & LLM Efficiency Rules (`AGENTS.md`)

> **Litmus Test**: Every rule in this file prevents a concrete compiler, formal verification, or agent-execution failure mode. Keep this file under 120 lines to prevent context-window dilution.

## 1. Architecture & Stack Contract
- **Runtime**: Python 3.11+ (`/Users/adityakulthe/Ecstasy/.venv/bin/python`), Clang/LLVM (`clang`, `opt`), `z3-solver` (`engine/symbolic_verifier.py`), and `alive-tv` (when installed).
- **Entrypoints**:
  - CLI: `cli.py` (`compile`, `verify`, `audit`, `certify`, `ui`)
  - MCP / Compiler Core: `server/mcp_server.py`
  - Symbolic SMT Verifier: `engine/symbolic_verifier.py`
  - LLM Rulebook & Pre-Gate: `agents/agent_rules.py`
  - 9-Agent Pipeline: `agents/supervisor.py`, `ir_architect.py`, `memory_sentinel.py`, `treefinement_supervisor.py`, `cegar_supervisor.py`, `algorithmic_synthesizer.py`, `global_context_agent.py`, `microarch_tuner.py`, `safety_vault.py`
- **No Unapproved Dependencies**: Do not add external packages to `requirements.txt` or `pyproject.toml` without explicit user approval.

## 2. High-Impact Agent & LLM Efficiency Rules

### Rule 1 — Context & Token Discipline (Read-Before-Edit)
- **Targeted Reads Only**: Use `grep_search` or line-bounded `view_file` (`StartLine`/`EndLine`) instead of reading entire large files into context.
- **LLM Prompt Compaction**: Always pass LLVM IR through `compact_ir_for_llm()` (`agents/agent_rules.py`) before LLM inference to strip `optnone` and boilerplate Clang comments (saves 25–45% prompt tokens).
- **Zero-Token Fast Path**: Skip LLM calls in `memory_sentinel.py` when the input IR contains no pointer/memory operations (`getelementptr`, `load`, `store`) or unsafe C library calls.

### Rule 2 — Alive2 / Z3 Formal Refinement Law ($\text{Target} \sqsubseteq \text{Source}$)
- **Never Widen Undefined Behavior**: Any IR transformation MUST be verified via `validate_translation()` (`server/mcp_server.py`) or `verify_ir_equivalence()` (`engine/symbolic_verifier.py`).
- **Flag Discipline**: Never strip `nsw`/`nuw` if downstream code relies on no-wrap semantics, and never inject `nsw`/`nuw`/`exact` unless proven poison-safe across all 32/64-bit inputs.
- **Pre-SMT Structural Gate**: Always run `validate_llm_ir_output(source_ir, candidate_ir)` in $O(N)$ to catch unbalanced braces, signature drift, or duplicate SSA register assignments before invoking Z3/Alive2.

### Rule 3 — Strict SSA, Bitwidth, and `-O0` IR Normalization
- **Strip `optnone` Before LLVM `opt`**: Clang `-O0` attaches `optnone` to functions. Always strip `\boptnone\b` before running `opt -O2` or `clang -O2 -x ir`.
- **Bitwidth Exactness**: Never mix `i8`, `i16`, `i32`, and `i64` in Z3 or LLVM IR without explicit `sext`, `zext`, or `trunc`.
- **Phi & Conditional Store Merging**: When splitting basic blocks for bounds checks or evaluating `-O0` `if/else` diamond CFGs, preserve `phi` predecessor labels and merge conditional `alloca` stores using `z3.If(cond, true_val, false_val)`.

### Rule 4 — Dual-Mode Offline / Online Resilience
- **Lazy Cloud Imports**: Never import `ibm_watsonx_ai` at module top-level without a lazy loader (`get_model()`).
- **100% Offline Determinism**: Every agent MUST succeed when `WATSONX_APIKEY` is unset by falling back to deterministic LLVM `-O2` passes and Z3 SMT symbolic verification.

### Rule 5 — The 3-Strike Root-Cause Protocol
- **No Blind Retries**: If an optimization, verification check, or test fails 3 consecutive times, halt blind retries immediately.
- **Counterexample-Driven Repair**: Inspect the exact Z3 counterexample (`Example: %var = val`, `Source:`, `Target:`) or pytest traceback, isolate the root-cause instruction, and apply a surgical fix.

### Rule 6 — Temp-File & Resource Hygiene
- **Guaranteed Cleanup**: Every `tempfile.NamedTemporaryFile` or `tempfile.mkstemp` creating `.ll`, `.c`, or `.out` files MUST unlink temporary files inside a `finally:` block.

### Rule 7 — Mandatory Verification Gate Before Completion
- Before declaring any code change complete, run:
  ```bash
  /Users/adityakulthe/Ecstasy/.venv/bin/pytest -q
  ```
- All tests in `tests/` MUST pass with 0 failures and 0 leaked temp files.
