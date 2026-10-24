# Parallel Multi-Agent Group Deliberation & Zero-Defect Quality Gate (`multi-agent-consensus.md`)

> Mandatory protocol for parallel multi-agent task decomposition, inter-agent group discussion, Pareto trade-off resolution, and 0% Bad Quality enforcement.

## 1. Parallel Task Decomposition (Fan-Out Execution)
- **Never Run Independent Specialists Sequentially**: Whenever starting a multi-faceted engineering or compilation task, immediately decompose the work into independent specialist tracks and run them concurrently in parallel:
  - **Track A — Security & Memory Bounds (`MemorySentinel` / `TreefinementSupervisor` / `CEGARSupervisor`)**: Audits pointer provenance, spatial bounds (`getelementptr`), temporal lifetimes, and overflow invariants (`sadd_ovf`).
  - **Track B — Algorithmic & Inter-Procedural Optimization (`IRArchitect` / `AlgorithmicSynthesizer` / `GlobalContextAgent`)**: Synthesizes loop reductions, strength reductions, and inter-procedural constant propagation (IPCP).
  - **Track C — Hardware Microarchitecture Tuning (`MicroArchTuner`)**: Computes target register pressure (Apple AMX / AVX-512 / NEON), L1D cache line utilization, and FMA vectorization width.
  - **Track D — Formal Verification (`SymbolicVerifier` / Alive2 / Z3)**: Proves mathematical refinement (`orig_ir ⊑ opt_ir`) in parallel via content-addressed SHA-256 memoization.
- **Antigravity Subagent Parallelism**: When exploring or implementing across multiple subsystems in the IDE/CLI, invoke subagents (`invoke_subagent`) or batch tool calls (`view_file`, `grep_search`, `run_command`) in parallel within a single turn.

## 2. Group Discussion & Trade-Off Deliberation Protocol
- **Peer-to-Peer Broadcast Bus (`SharedKnowledgeBase.post_discussion_message`)**: Every specialist agent must post structured position statements to the shared roundtable bus specifying:
  - `sender` and `recipient` (`"ALL"` for group broadcast or a specific peer agent)
  - `topic` (e.g., `"Vectorization Width vs. Spatial Bounds Check Overhead"`)
  - `position` (concrete technical claim backed by IR instruction counts or Z3 predicates)
  - `tradeoff_axis` (`"performance"` | `"safety"` | `"verification"` | `"pareto_consensus"`)
  - `score_delta` (quantified impact on speedup or safety margin)
- **Roundtable Trade-Off Resolution (`SharedKnowledgeBase.conduct_group_deliberation`)**:
  - When **Performance** (`IRArchitect` / `MicroArchTuner`) conflicts with **Safety** (`MemorySentinel`), agents must negotiate a Pareto-optimal compromise rather than sacrificing either axis:
    1. Keep spatial/overflow safety guards (`llvm.sadd.with.overflow`, bounds checks) intact.
    2. Hoist loop-invariant bounds checks (`LICM`) outside the inner vectorized preheader so safety overhead remains $\le 5.0\%$.
    3. Require `SymbolicVerifier` (Z3 SMT) to certify `status == "PROVED"` (`0` counterexamples) before ratifying the consensus.

## 3. Zero-Defect Quality Gate (0% Bad Quality Tolerance)
- **Strict Veto Power**: Any single specialist agent or verification check has absolute veto power if quality drops below 100%:
  - **0 Unverified Transformations**: Every IR rewrite must pass `_verify_ir_semantics` and Z3/Alive2 equivalence (`PROVED`).
  - **0 Unbounded Overhead**: Safety instrumentation overhead must stay within the $\le 5.0\%$ performance budget (`perf_overhead_pct <= 5.0`).
  - **0 Broken Tests or Regressions**: Full test suite (`pytest -q`) must pass 100% with zero skipped or broken assertions before task completion.
  - **0 Hallucinated Instructions**: All emitted LLVM IR must pass `validate_llm_ir_output` before touching `opt` or `clang`.
