# LLM & Multi-Agent Efficiency Rules

## 1. Prompt & Token Optimization Rules
- **Pre-Inference Compaction (`compact_ir_for_llm`)**: Strip `optnone`, `; ModuleID`, `; Function Attrs:`, and redundant blank lines before sending IR to `UniversalLLMClient` (`agents/llm_client.py`).
- **Zero-Prose Output Contract**: System prompts for `@ir-architect`, `@memory-sentinel`, and `@cegar-repair` must enforce raw LLVM IR output with zero conversational filler.
- **Fast-Path Gating**:
  - `@memory-sentinel`: Bypass LLM inference when the IR contains no memory/pointer instructions or unsafe C library calls.
  - `validate_translation`: Immediately return `PROVED` when `orig_ir.strip() == opt_ir.strip()` before spawning subprocesses or Z3 solvers.

## 2. Multi-Agent Coordination Rules (`SharedKnowledgeBase` & `CompilerSupervisor`)
- **Idempotent Conflict Detection**: `SharedKnowledgeBase.detect_conflicts()` must deduplicate `(agents, conflict_type, description)` tuples across repeated invocations.
- **Pattern Specificity Ordering**: `AlgorithmicSynthesizer.detect_pattern()` must evaluate high-specificity patterns (`BUBBLE_SORT`, confidence `0.9`) before generic loop-depth heuristics (`NESTED_LOOP_SUM`, confidence `0.8`).
- **Whole-Program Call Graph Completeness**: `GlobalContextAgent` must compute `call_count` only after all translation units are ingested, inspect the final token of typed LLVM arguments (`i32 noundef 7`), and never flag `@main` as a dead function.
- **Cryptographic Attestation Gate**: `SafetyVault` certificate generation in `CompilerSupervisor` runs only after both formal verification (`final_verdict == "PROVED"`) and binary compilation succeed.
