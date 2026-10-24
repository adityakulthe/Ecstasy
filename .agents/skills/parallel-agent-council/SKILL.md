---
name: parallel-agent-council
description: Orchestrate multiple specialist agents in parallel, facilitate peer-to-peer group discussion to resolve performance vs. safety vs. verification trade-offs, and enforce a 0% bad quality gate. Activate whenever starting a complex task, optimizing code, or coordinating multi-agent workflows.
---

# Parallel Multi-Agent Council & Group Deliberation Skill

Use this skill whenever starting a task that spans architecture, optimization, security, verification, or multi-file engineering so multiple agents work in parallel, communicate like a group roundtable discussion, resolve trade-offs, and guarantee **0% bad quality**.

## 1. Workflow: Fan-Out -> Group Discussion -> Trade-Off Consensus -> Zero-Defect Gate

```
                   ┌──────────────────────────────────────────┐
                   │       Task / Compilation Request         │
                   └────────────────────┬─────────────────────┘
                                        │ (Parallel Fan-Out)
        ┌───────────────────┬───────────┴───────────┬───────────────────┐
        ▼                   ▼                       ▼                   ▼
┌───────────────┐   ┌───────────────┐       ┌───────────────┐   ┌───────────────┐
│ Track 1:      │   │ Track 2:      │       │ Track 3:      │   │ Track 4:      │
│ Security &    │   │ Algorithmic & │       │ MicroArch &   │   │ Formal SMT    │
│ Bounds Audit  │   │ Loop Synthesis│       │ SIMD Tuning   │   │ Verification  │
└───────┬───────┘   └───────┬───────┘       └───────┬───────┘   └───────┬───────┘
        │                   │                       │                   │
        └───────────────────┴───────────┬───────────┴───────────────────┘
                                        ▼
                   ┌──────────────────────────────────────────┐
                   │   Group Discussion Bus (Roundtable)      │
                   │  Agents exchange messages & debate:      │
                   │  Speed vs. Safety vs. Verification Cost  │
                   └────────────────────┬─────────────────────┘
                                        ▼
                   ┌──────────────────────────────────────────┐
                   │   Zero-Defect Quality Gate (0% Bad)      │
                   │  • Z3/Alive2 Status == PROVED            │
                   │  • Safety Overhead <= 5.0%               │
                   │  • 100% Pytest Suite Passing             │
                   └──────────────────────────────────────────┘
```

## 2. Step-by-Step Execution Protocol

### Step 1: Parallel Task Assignment (Fan-Out)
- **In Code (`agents/supervisor.py`)**: Execute specialist agents concurrently via `concurrent.futures.ThreadPoolExecutor`:
  - `TreefinementSupervisor`: Structural AST/CFG block hierarchy refinement.
  - `CEGARSupervisor`: Counterexample-guided loop invariant synthesis.
  - `AlgorithmicSynthesizer`: Closed-form algebraic & polyhedral reduction (`O(N) -> O(1)`).
  - `GlobalContextAgent`: Whole-program call graph & inter-procedural constant propagation.
  - `MicroArchTuner`: Target-specific SIMD vector width & register pressure tuning.
- **In Agentic IDE/CLI Sessions**: Launch independent file inspections, searches, or `research`/`self` subagents in parallel in a single turn.

### Step 2: Inter-Agent Group Discussion (`post_discussion_message`)
- Each specialist agent posts its findings and constraints to `SharedKnowledgeBase.post_discussion_message(sender, recipient, topic, position, tradeoff_axis, score_delta)`.
- Agents explicitly challenge and respond to each other's constraints:
  - *Performance position*: "Unrolling 4x + vectorizing increases register pressure; redundant inner-loop bounds checks will stall SIMD lanes."
  - *Safety position*: "Pointer arithmetic and signed additions require overflow/bounds traps; cannot drop safety checks unless loop bounds are proved invariant."
  - *Synthesis position*: "Hoist the bounds check to the loop preheader (`LICM`) or fold into closed-form arithmetic so inner-loop overhead is 0%."

### Step 3: Pareto Trade-Off Consensus (`conduct_group_deliberation`)
- Call `SharedKnowledgeBase.conduct_group_deliberation(topic, perf_overhead_pct, safety_hardened, proved)` to evaluate all agent messages and compute a `TradeoffConsensus`:
  - Balances `performance`, `safety`, and `verification` axes.
  - Rejects any proposal where `perf_overhead_pct > 5.0%` or `proved == False`.

### Step 4: Zero-Defect Quality Gate (0% Bad Quality Tolerance)
Never mark a task complete until every single check below passes with 0 defects:
1. `validate_llm_ir_output(ir)` returns `(True, "VALID")` (0 markdown fences, 0 hallucinated opcodes).
2. `SymbolicVerifier.verify_ir(orig_ir, opt_ir)` returns `"PROVED"` (0 Z3 counterexamples).
3. `conduct_group_deliberation(...)["quality_gate_passed"]` is `True`.
4. `.venv/bin/pytest -q` passes 100% of tests with 0 failures and 0 errors.
