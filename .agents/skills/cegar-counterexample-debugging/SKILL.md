---
name: cegar-counterexample-debugging
description: >-
  Use this skill when an LLVM IR optimization fails Alive2 or Z3 formal verification
  and you need to parse counterexamples, diagnose poison/overflow/UB mismatches,
  and apply a targeted patch.
---

# CEGAR Counterexample Debugging Skill

Use this workflow when `validate_translation` or `verify_ir_equivalence` returns `FAILED` with a counterexample.

## Step-by-Step Diagnosis & Repair

1. **Parse Multi-Line Counterexamples**:
   - Pass the verifier output to [`CEGARSupervisor.parse_counterexample(output)`](file:///Users/adityakulthe/Ecstasy/agents/cegar_supervisor.py#L92-L152).
   - Inspect `counterexample.failure_type` (`overflow`, `undefined_behavior`, `type_mismatch`, `value_mismatch`), `counterexample.values`, and `counterexample.root_cause`.
2. **Apply Surgical Repair by Failure Type**:
   - **Signed/Unsigned Overflow (`nsw` / `nuw`)**:
     - If `Source: poison` and `Target: <concrete>` because `nsw` was dropped while downstream code depends on no-wrap, restore `nsw`.
     - If `Target: poison` and `Source: <concrete>`, strip the invalid `nsw`/`nuw` flag added by the candidate pass via [`CEGARSupervisor.apply_targeted_patch`](file:///Users/adityakulthe/Ecstasy/agents/cegar_supervisor.py#L281-L312).
   - **Undefined / Uninitialized Value (`undef` / `poison`)**:
     - Insert `%frozen = freeze <ty> %val` before the branching or arithmetic instruction.
   - **Value Mismatch on Branch Merge**:
     - Verify `phi` predecessor labels match the `br i1 %cond, label %true_lbl, label %false_lbl` order.
3. **Verify Zero-Regression Performance Budget**:
   - Call [`CEGARSupervisor.analyze_performance_impact(orig_ir, patched_ir)`](file:///Users/adityakulthe/Ecstasy/agents/cegar_supervisor.py#L248-L279) and confirm `safety_overhead_percent <= 5.0%`.
