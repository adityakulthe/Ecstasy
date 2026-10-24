# LLVM IR & Z3 SMT Formal Verification Rules

## 1. LLVM IR Structural Invariants
- **Function Extraction**: Always account for linkage and parameter attributes (`dso_local`, `internal`, `noundef`, `signext`, `zeroext`, `local_unnamed_addr`) and support both single-line and multi-line function bodies.
- **SSA Single Assignment**: Every virtual register (`%reg`) in a function body must be assigned at most once (`validate_llm_ir_output`).
- **Instruction Counting**: Exclude module headers (`source_filename`, `target datalayout`, `target triple`, `attributes #`, `!llvm.module.flags`) when calculating instruction overhead in `CEGARSupervisor` and `MicroArchitecturalTuner`.

## 2. Z3 BitVector Symbolic Execution Rules (`engine/symbolic_verifier.py`)
- **Explicit Operand Bitwidth Tracking**: Track the active type token (`i64`, `i32`, `i16`, `i8`, `i1`) across operands so integer literals are instantiated with matching `z3.BitVecVal(val, width)`.
- **Skip Alignment Metadata**: Ignore `align <N>` tokens on `alloca`, `load`, and `store` instructions during operand parsing.
- **Branch-Aware `phi` and Store Merging**:
  - Match `phi` incoming block labels against the preceding conditional branch's `(true_label, false_label)` rather than assuming positional order.
  - Merge conditional `store` operations across `true_label` and `false_label` into `z3.If(cond, true_val, false_val)` for `-O0` to `-O2` equivalence proofs.
- **Sound Bailout on Unsupported Constructs**: Return `(params, None, overflow_checks)` when encountering external `call` instructions, `getelementptr`, floating-point ops, or loop back-edges so the verifier never emits false counterexamples.
