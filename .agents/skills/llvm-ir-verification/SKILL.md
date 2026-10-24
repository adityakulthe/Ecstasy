---
name: llvm-ir-verification
description: >-
  Use this skill when compiling C/C++ to LLVM IR, optimizing IR passes, stripping
  optnone attributes, or formally proving semantic equivalence with Z3 SMT and Alive2.
---

# LLVM IR Optimization & Formal Verification Skill

Follow this workflow whenever modifying compiler passes, LLVM IR transformations, or symbolic verification in `server/mcp_server.py`, `agents/ir_architect.py`, or `engine/symbolic_verifier.py`.

## Step-by-Step Workflow

1. **Compile Source to Unoptimized IR (`-O0`)**:
   - Call [`compile_to_ir(source_code, filename)`](file:///Users/adityakulthe/Ecstasy/server/mcp_server.py#L18-L130).
   - Ensure `.cpp`/`.cc`/`.cxx` files route to `clang++` and `.c` files route to `clang`.
2. **Normalize Before Optimization (`optnone` Stripping)**:
   - Clang `-O0` attaches `optnone` to functions, which silently blocks `opt -O2` and `clang -O2 -x ir`.
   - Always pass IR through [`compact_ir_for_llm(ir)`](file:///Users/adityakulthe/Ecstasy/agents/agent_rules.py#L79-L108) or `re.sub(r'\boptnone\b\s*', '', ir)` before running optimization passes.
3. **Run Fast $O(N)$ Pre-SMT Structural Gate**:
   - Validate any LLM or pass output with [`validate_llm_ir_output(source_ir, candidate_ir)`](file:///Users/adityakulthe/Ecstasy/agents/agent_rules.py#L132-L180) to catch unbalanced braces, return-type drift, or duplicate SSA register definitions (`%reg = ...`) before invoking Z3.
4. **Prove Equivalence with Z3 SMT / Alive2**:
   - Run the quick verification helper script:
     [quick_verify.py](./scripts/quick_verify.py)
   - Or invoke CLI directly:
     ```bash
     /Users/adityakulthe/Ecstasy/.venv/bin/python cli.py verify --orig orig.ll --opt opt.ll
     ```

## Supported Symbolic Constructs in `SymbolicIRVerifier`
- Integer bitwidths: `i1`, `i8`, `i16`, `i32`, `i64` (with `zext`, `sext`, `trunc`, `bitcast`, `freeze`).
- Arithmetic & bitwise: `add`, `sub`, `mul`, `sdiv`, `udiv`, `srem`, `urem`, `shl`, `lshr`, `ashr`, `and`, `or`, `xor` (including `nsw` poison refinement checks).
- Control flow & memory promotion: `icmp`, `select`, branch-aware `phi`, `alloca`/`store`/`load`, and conditional `if/else` store merging (`z3.If`).
- LLVM intrinsics: `@llvm.smax.*`, `@llvm.smin.*`, `@llvm.umax.*`, `@llvm.umin.*`, and `@llvm.abs.*`.
