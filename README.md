# Ecstasy — Agentic LLVM Optimization with Formal Verification

> **We don't rewrite the world's software. We make it safe and fast at the compiler level, and we prove it mathematically.**

<div align="center">

### [▶️ **WATCH THE FULL DEMO VIDEO ON YOUTUBE**](https://www.youtube.com/watch?v=FictO9BoHnk)

[![AI Compiler Demo - Click to Watch on YouTube](https://img.youtube.com/vi/FictO9BoHnk/maxresdefault.jpg)](https://www.youtube.com/watch?v=FictO9BoHnk)

[![Tests](https://img.shields.io/badge/tests-201/201_passing-success)](tests/)
[![Engine](https://img.shields.io/badge/formal_verification-Z3_SMT_+_Alive2-brightgreen)](engine/)
[![Compiler Driver](https://img.shields.io/badge/drop--in_compiler-ecstasy--cc-blue)](engine/compiler_driver.py)
[![GitHub Action](https://img.shields.io/badge/CI%2FCD-action.yml-2088FF)](action.yml)
[![Agents](https://img.shields.io/badge/agents-9_Parallel_Roundtable-blueviolet)](agents/)
[![CLI](https://img.shields.io/badge/cli-ecstasy_30_commands-blue)](cli.py)
[![MCP](https://img.shields.io/badge/FastMCP-26_Tools-orange)](server/mcp_server.py)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED)](Dockerfile)
[![CI/CD](https://img.shields.io/badge/CI-GitHub_Actions-2088FF)](.github/workflows/ci.yml)

</div>

---

## ⚡ Why Ecstasy?

- **The Problem**: 70% of critical CVEs stem from C/C++ memory safety bugs (`CWE-120`, `CWE-125`, `CWE-415`, `CWE-416`), while static compiler heuristics miss intent-level algebraic and inter-procedural optimizations. LLMs can synthesize aggressive LLVM IR rewrites, but **unverified AI output cannot be trusted in production compilers**.
- **The Solution**: Ecstasy intercepts code at the **LLVM Intermediate Representation (IR)** level, orchestrates **9 specialist agents in parallel** with a **Roundtable Trade-Off Consensus Bus**, hardens unsafe memory operations, and **mathematically proves semantic refinement ($\text{Target} \sqsubseteq \text{Source}$)** across all bitvector inputs using **Z3 SMT** and **Alive2** before emitting an HMAC-SHA256 attested binary.

---

## 🏗️ 9-Agent Parallel Roundtable Architecture

```
                         ┌──────────────────────────────────────────────┐
                         │         C / C++ / LLVM IR Source             │
                         └──────────────────────┬───────────────────────┘
                                                ▼
                         ┌──────────────────────────────────────────────┐
                         │  1. CompilerSupervisor (Universal LLM/Local) │
                         │  • 2. @ir-architect (LLVM -O2 / AI Rewrite)  │
                         │  • 3. @memory-sentinel (CWE Bounds Hardening)│
                         └──────────────────────┬───────────────────────┘
                                                │ (ThreadPoolExecutor Fan-Out)
        ┌───────────────────┬───────────────────┼───────────────────┬───────────────────┐
        ▼                   ▼                   ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ 4. Treefine   │   │ 5. CEGAR      │   │ 6. Synth      │   │ 7. GlobalCtx  │   │ 8. MicroArch  │
│ Multi-Branch  │   │ Loop Invariant│   │ O(n²)→O(1)    │   │ Whole-Program │   │ Apple M4 /    │
│ IR Search     │   │ SMT Synthesis │   │ Closed-Form   │   │ IPCP Inlining │   │ AVX-512 / EPYC│
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        └───────────────────┴───────────────────┼───────────────────┴───────────────────┘
                                                ▼
                         ┌──────────────────────────────────────────────┐
                         │   SharedKnowledgeBase Roundtable Consensus   │
                         │   • Speed vs. Safety vs. Verification Debate │
                         │   • Enforces <= 5.0% Safety Overhead (LICM)  │
                         │   • Zero-Defect Quality Gate (0% Bad Quality)│
                         └──────────────────────┬───────────────────────┘
                                                ▼
                         ┌──────────────────────────────────────────────┐
                         │   Z3 SMT + Alive2 Formal Verifier + Vault    │
                         │   • Bitvector Equivalence & Poison Checking  │
                         │   • SROA, Intrinsics, Switch & Mem2Reg Proofs│
                         │   • 9. SafetyVault HMAC-SHA256 CBOM & SARIF  │
                         └──────────────────────────────────────────────┘
```

---

## 📊 Whole-Corpus Benchmark (`ecstasy benchmark demo_corpus`)

Every file in [`demo_corpus/`](demo_corpus/) is compiled to `-O0` LLVM IR, optimized via Ecstasy's `-O2` pipeline, scanned for CWE vulnerabilities, and formally verified by Z3 SMT:

| Corpus File | `-O0` IR Insts | Optimized IR Insts | Instruction Reduction | CWE Guards | Z3 Verdict | Time |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `algorithms/dynamic_programming.c` | 1,239 | 1,017 | **17.9%** | 11 | `PROVED` | 87ms |
| `algorithms/graph.c` | 1,107 | 988 | **10.8%** | 5 | `PROVED` | 94ms |
| `algorithms/sorting.c` | 1,063 | 732 | **31.1%** | 6 | `PROVED` | 57ms |
| `math/matrix_ops.c` | 1,097 | 673 | **38.6%** | 3 | `PROVED` | 55ms |
| `math/numerical_methods.c` | 835 | 338 | **59.5%** | 1 | `PROVED` | 46ms |
| `math/statistics.c` | 1,016 | 589 | **42.0%** | 3 | `PROVED` | 51ms |
| `physics/nbody.c` | 969 | 455 | **53.0%** | 3 | `PROVED` | 48ms |
| `signal/fft.c` | 899 | 691 | **23.1%** | 4 | `PROVED` | 53ms |
| `unsafe/buffer_overflow.c` | 189 | 123 | **34.9%** | 9 | `PROVED` | 47ms |
| **TOTAL / AVERAGE (9/9 Files)** | **8,414** | **5,606** | **33.4% Reduced** | **45 CWEs** | **9/9 `PROVED`** | **536ms** |

---

## 🚀 Quickstart & CLI Reference

### 1. Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. Drop-in Clang Replacement (`ecstasy-cc` / `ecstasy-c++`)
Compile any existing Makefile or CMake codebase transparently with Provable Cyber Defense:
```bash
# Build existing project with Make
export CC=ecstasy-cc CXX=ecstasy-c++
make

# Or compile directly
ecstasy-cc -O2 main.c -o app
```

### 3. 1-Click AI Coding Agent Integration (Cursor & Claude)
Turn on Ecstasy's 26 formal verification tools inside Cursor IDE or Claude Desktop:
```bash
ecstasy mcp --install-cursor
ecstasy mcp --install-claude
```

### 4. Turnkey GitHub Actions CI/CD Protection
Add to `.github/workflows/ecstasy.yml`:
```yaml
- name: Run Ecstasy SMT Verification
  uses: adityakulthe/Ecstasy@main
  with:
    target: './src'
    fail-on-exploit: true
    pr-comment: true
```

👉 **For the complete guide, see [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)**.

---

### 5. Core CLI Commands (`ecstasy` / `python3 cli.py`)
```bash
# 1. System & Toolchain Diagnostics (Clang, LLVM Optimizer, Z3, Alive2, Signing Keys)
ecstasy doctor

# 2. Compile, Optimize (9-Agent Parallel Suite), Formally Verify & Emit Cryptographic Proof
ecstasy compile demo_corpus/math/numerical_methods.c --advanced -o numerical.out --cert --html

# 3. Standalone Z3 SMT / Alive2 Translation Validation on two LLVM IR files
ecstasy verify tests/fixtures/ipcp_combined.ll tests/fixtures/ipcp_combined.ll

# 4. Whole-Corpus Optimization, CWE Security & Z3 Verification Benchmark
ecstasy benchmark demo_corpus --report benchmark.json

# 5. CWE-Mapped Security Audit with JSON & OASIS SARIF 2.1.0 Export
ecstasy audit demo_corpus/unsafe/ --offline --report audit.json --sarif audit.sarif

# 6. Verify HMAC-SHA256 Cryptographic Proof Certificate & Binary Hash
ecstasy verify-cert demo_corpus/math/numerical_methods.proof.json -b numerical.out

# 7. Launch Interactive Dark Terminal Web IDE
ecstasy ui --port 8501
```

---

## 🔬 Formal Verification & CWE Security Capabilities

- **Pure-Python Z3 SMT Symbolic Verifier ([`engine/symbolic_verifier.py`](engine/symbolic_verifier.py))**:
  - Bit-exact verification across `i1`, `i8`, `i16`, `i32`, `i64`, and `ptr` bitvectors with SHA-256 content-addressed memoization (`_VERIFICATION_CACHE`).
  - Proves `mem2reg` stack-to-register promotion, diamond `if/else` conditional stores, multi-way `switch` + `phi` CFGs, local `alloca` `getelementptr` **SROA (Scalar Replacement of Aggregates)**, overflow-checked intrinsics (`@llvm.{sadd,uadd,ssub,usub,smul,umul}.with.overflow.*` + `extractvalue`), and bitwise intrinsics (`@llvm.smax`, `@llvm.smin`, `@llvm.umax`, `@llvm.umin`, `@llvm.abs`, `@llvm.bswap`, `@llvm.ctpop`, `@llvm.ctlz`, `@llvm.cttz`, `@llvm.fshl`, `@llvm.fshr`, `freeze`).
  - Catches signed overflow poison (`nsw` stripping), arithmetic mutations, and dropped bounds guards with Alive2-formatted counterexamples.
- **CWE-Mapped Static Vulnerability Scanner ([`server/mcp_server.py`](server/mcp_server.py))**:
  - Automatically detects **CWE-120** (`scanf`, `strcpy`/`__strcpy_chk`, `strcat`/`__strcat_chk`, `gets`, `sprintf`), **CWE-125/787** (unchecked `getelementptr`), **CWE-134** (uncontrolled format string in `@printf`), **CWE-190** (integer overflow feeding `@malloc`), **CWE-415** (double-free), **CWE-416** (use-after-free), and **CWE-674** (deep stack recursion), exporting to JSON and **SARIF 2.1.0**.

---

## 🧠 Agent Rules & Specialized Skills

Ecstasy ships with modular agent rules and on-demand skills for zero-defect autonomous engineering:
- **Rules**: [`AGENTS.md`](AGENTS.md), [`GEMINI.md`](GEMINI.md), [`.agents/rules/llvm-verification-rules.md`](.agents/rules/llvm-verification-rules.md), [`.agents/rules/llm-agent-efficiency.md`](.agents/rules/llm-agent-efficiency.md), [`.agents/rules/multi-agent-consensus.md`](.agents/rules/multi-agent-consensus.md)
- **Skills ([`.agents/skills/`](.agents/skills/))**:
  - `parallel-agent-council`: Parallel multi-agent task fan-out, group roundtable trade-off debate, and 0% bad quality gate.
  - `llvm-ir-verification`: Formal LLVM IR transformation and Z3/Alive2 equivalence proving.
  - `cegar-counterexample-debugging`: Counterexample-guided root-cause isolation and repair.
  - `security-audit-and-cbom`: CWE memory vulnerability auditing, SARIF 2.1.0 export, and HMAC-SHA256 CBOM attestation.
  - `high-velocity-engineering`: Context compaction (`compact_ir_for_llm`) and $O(N)$ SSA pre-gate validation (`validate_llm_ir_output`).

---

## 🧪 Testing

```bash
pytest -v
```
All **91/91** unit, symbolic verification, multi-agent deliberation, CWE security, SARIF export, and whole-corpus benchmark tests run in ~3 seconds with zero external cloud dependencies required.

---

## 📄 License

Apache-2.0 License — Built with **Multi-Agent LLVM Synthesis + Alive2 + Z3 SMT**.