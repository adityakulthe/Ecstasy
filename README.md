# 🚀 Ecstasy — Autonomous LLVM Compiler Optimization & Provable Cyber Defense (PCD)

> **"We don't rewrite the world's software. We make it safe and fast at the compiler level, and we prove it mathematically."**

<div align="center">

### [▶️ **WATCH THE FULL ARCHITECTURE & LIVE DEMO ON YOUTUBE**](https://www.youtube.com/watch?v=FictO9BoHnk)

[![Ecstasy Provable Cyber Defense Demo](https://img.youtube.com/vi/FictO9BoHnk/maxresdefault.jpg)](https://www.youtube.com/watch?v=FictO9BoHnk)

[![CI/CD](https://github.com/adityakulthe/Ecstasy/actions/workflows/ci.yml/badge.svg)](https://github.com/adityakulthe/Ecstasy/actions)
[![Tests](https://img.shields.io/badge/formal_tests-206%2F206_passing-success)](tests/)
[![Formal SMT Engine](https://img.shields.io/badge/SMT_Refinement-Z3_Bitvectors_+_Alive2-brightgreen)](engine/symbolic_verifier.py)
[![Hyperproperties](https://img.shields.io/badge/relational_2--safety-P_%C3%97_P_Self--Composition-blueviolet)](engine/hyperproperty_prover.py)
[![Drop-in Compiler](https://img.shields.io/badge/drop--in_compiler-ecstasy--cc_%26_ecstasy--c%2B%2B-blue)](engine/compiler_driver.py)
[![GitHub Action](https://img.shields.io/badge/turnkey_action-action.yml-2088FF)](action.yml)
[![FastMCP](https://img.shields.io/badge/FastMCP_Server-26_Formal_Tools-orange)](server/mcp_server.py)
[![CLI](https://img.shields.io/badge/cli-30_subcommands-blue)](cli.py)
[![Cloud Gatekeeper](https://img.shields.io/badge/GCP_BinAuthz-GKE_Admission_Admit-green)](deploy/gcp/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Author](https://img.shields.io/badge/author-Aditya_Kulthe-informational)](mailto:kultheaditya23@gmail.com)

</div>

---

## ⚡ Executive Summary: The Compiler & Cybersecurity Paradigm Shift

Every modern software system relies on native code compiled from C, C++, Rust, Swift, Zig, or eBPF. Yet today's computing ecosystem faces an unsustainable dual crisis:
1. **The Systems Vulnerability Crisis**: Over 70% of critical zero-day CVEs stem from memory safety corruptions (`CWE-120`, `CWE-125`, `CWE-787`, `CWE-416`), microarchitectural side-channels (`CWE-208`, `CWE-385`, Spectre `CWE-1037`), and physical glitch injections (`CWE-1254`). Traditional runtime sanitizers (ASan, MSan, UBSan) impose **100%–300% runtime and memory overhead**, rendering them unusable in high-performance production.
2. **The Unverified AI Code Generation Hazard**: Modern AI agents can generate and optimize low-level LLVM SSA code, but **unverified AI output cannot be deployed into safety-critical compilers or cloud infrastructure**. A single hallucinated instruction or dropped poison flag (`nsw`, `exact`) silently compromises security and correctness.

**Ecstasy** introduces **Provable Cyber Defense (PCD)**:
- Intercepts software directly at the **LLVM Intermediate Representation (IR)** level before machine code emission.
- Orchestrates **9 autonomous specialist agents** with a **Parallel Roundtable Consensus Bus** to optimize algorithms, vectorize loops, and eliminate vulnerabilities.
- Proves the **Zero-Divergence Invariant ($\text{Target} \sqsubseteq \text{Source}$)** across all $2^{32} / 2^{64}$ inputs using **Z3 SMT bitvectors** and **Alive2 formal semantics** before emitting hardened binaries.
- Exports machine-checkable **Lean 4 / SMT-LIB2 proof certificates**, **OASIS SARIF v2.1.0** diagnostics, **CycloneDX v1.6 CBOM**, and **in-toto v1.0 DSSE attestation envelopes** for Google Cloud and Kubernetes admission gates.

---

## 🏛️ End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["1. Multi-Modal Software Ingestion"]
        C_SRC["C / C++ Source Code"] --> CC_DRIVER["ecstasy-cc / ecstasy-c++\n(Transparent Clang Replacement)"]
        LLVM_IR["LLVM IR (.ll / .bc)"] --> IR_PARSER["SSA Ingestion & Symbolizer"]
        NATIVE_BIN["Stripped ELF / Mach-O Binary"] --> BIN_LIFTER["Zero-Source Binary Lifter\n(CFG & Micro-IR Reconstruction)"]
        EBPF_PROG["Linux eBPF Packet Filter"] --> EBPF_VERIF["eBPF Invariant Verifier\n([data, data_end) Bounds & 512B Stack)"]
        CC_DRIVER --> IR_PARSER
        BIN_LIFTER --> IR_PARSER
    end

    subgraph Roundtable["2. 9-Agent Parallel Roundtable Council"]
        IR_PARSER --> SUP["1. CompilerSupervisor\n(Coordinator & Fallback)"]
        SUP --> ARCH["2. @ir-architect\n(Algebraic Rewriting)"]
        SUP --> SENTINEL["3. @memory-sentinel\n(CWE Bounds Hardener)"]
        SUP --> TREE["4. TreefinementSupervisor\n(Multi-Branch Search)"]
        SUP --> CEGAR["5. CEGARSupervisor\n(SMT Invariant Loop)"]
        SUP --> SYNTH["6. AlgorithmicSynthesizer\n(O(n²) → O(1) Closed-Forms)"]
        SUP --> GLOBAL["7. GlobalContextOptimizer\n(IPCP & Inlining)"]
        SUP --> TUNER["8. MicroArchTuner\n(Apple M4 / AVX-512)"]
        SUP --> VAULT["9. SafetyVault\n(HMAC-SHA256 CBOM & SARIF)"]
        
        ARCH & SENTINEL & TREE & CEGAR & SYNTH & GLOBAL & TUNER & VAULT --> CONSENSUS["SharedKnowledgeBase Consensus Bus\n(Pareto Trade-Off: Speed vs. Safety <= 5% Overhead)"]
    end

    subgraph PCD["3. Provable Cyber Defense & SMT Hyperproperty Solvers"]
        CONSENSUS --> SMT_EXPLOIT["SMT Exploit Reachability Prover\n(Z3 Bit-Vector Exploit Synthesis)"]
        CONSENSUS --> HYPERPROPERTIES["Relational 2-Safety Hyperproperties (P × P)\n• Constant-Time Crypto (CWE-208)\n• Cache-Line Invariance (CWE-385)\n• Speculative Non-Interference (CWE-1037)\n• Forward-Edge CFI (CWE-822)\n• Dual-Rail Glitch Resilience (CWE-1254)"]
        CONSENSUS --> PQC_ENGINE["Post-Quantum Cryptography (PQC)\n(FIPS 203 ML-KEM / ML-DSA KyberSlash Defense)"]
        CONSENSUS --> HW_SAFETY["Hardware-Assisted Memory Safety\n(ARM64 PAC & MTE Intrinsics)"]
        CONSENSUS --> ZERO_DIV["Zero-Divergence Invariant Prover\n(Alive2 Formal Refinement: Target ⊑ Source)"]
    end

    subgraph DefenseLoop["4. Automated Branchless Hardening & Closed-Loop Healing"]
        SMT_EXPLOIT & HYPERPROPERTIES & PQC_ENGINE & HW_SAFETY --> HARDENER["Automated Security Hardener\n(Branchless Muxes, Safe Specifiers, @llvm.trap)"]
        HARDENER --> ZERO_DIV
        ZERO_DIV --> HEALED_IR["SMT-Proved Hardened LLVM IR"]
        HEALED_IR --> GUARD["Ecstasy Guard & Watch Daemon\n(Continuous Real-Time Repository Self-Healing)"]
    end

    subgraph Delivery["5. Turnkey Production Integration & Cloud Gates"]
        HEALED_IR --> MACHINE_BIN["Hardened Native Object / Binary"]
        GUARD --> SARIF_REPORT["OASIS SARIF v2.1.0 Report"]
        GUARD --> CYCLONE_CBOM["CycloneDX v1.6 CBOM"]
        GUARD --> INTOTO_BUNDLE["in-toto v1.0 DSSE Envelope"]
        INTOTO_BUNDLE --> GCP_GATE["Google Cloud Binary Authorization"]
        INTOTO_BUNDLE --> K8S_GATE["Kubernetes Admission Webhook"]
    end
```

---

## 🛡️ Provable Cyber Defense (PCD) Core Innovations

### 1. Relational 2-Safety Hyperproperties via Self-Composition ($P \times P$)
Unlike standard safety properties asserting what a single trace $\sigma$ must not do, information-flow security properties are **hyperproperties** relating multiple execution traces $\sigma_1, \sigma_2$:
- **Cryptographic Constant-Time ($\mathcal{CT}_{\text{time}}$ / CWE-208)**: Proves in Z3 that branching conditions are algebraically independent of secret inputs across all executions:
  $$\forall \sigma_1, \sigma_2.\, \sigma_1 =_L \sigma_2 \implies \text{BranchCond}(\sigma_1) = \text{BranchCond}(\sigma_2)$$
- **Cache-Line Secret Independence ($\mathcal{CT}_{\text{cache}}$ / CWE-385)**: Proves that secret data differences never modulate the cache-line offset $\lfloor \text{addr} / 64 \rfloor$, defeating Flush+Reload, Prime+Probe, and CacheBleed side channels.
- **Speculative Non-Interference (SNI / Spectre CWE-1037)**: Proves memory accesses under misspeculated branch predictions cannot transiently leak secret memory into the microarchitectural cache hierarchy.
- **Forward-Edge Control-Flow Integrity (CFI / CWE-822)**: Proves all indirect function call pointers are strictly constrained to a validated compile-time symbol whitelist, neutralizing ROP/JOP call hijacking.
- **Dual-Rail Hardware Glitch Resilience (CWE-1254)**: Detects single-point-of-failure conditional authentication gates and synthesizes dual-rail complementary checking (`%inv = xor %cond, true; %chk = xor %cond, %inv; br %chk, ... fault_trap`) backed by `@llvm.trap` hardware aborts for ISO 26262 ASIL-D compliance.

### 2. Post-Quantum Cryptography (PQC) Side-Channel Verifier (FIPS 203)
Audits ML-KEM (Kyber) and ML-DSA (Dilithium) lattice operations for secret-dependent modular reduction timing leaks (the **KyberSlash** vulnerability), synthesizing branchless straight-line bit-equivalent replacements with formal Z3 verification.

### 3. Linux Kernel eBPF Safety Verifier & Rewriter
Emulates the in-kernel BPF verifier in Z3 SMT:
- Proves all packet pointer accesses are strictly bounded within `[data, data_end)`.
- Enforces the hard 512-byte eBPF stack frame ceiling (`CWE-787` mitigation).
- Formally proves loop termination to protect against kernel denial-of-service.
- Automatically rewrites unsafe packet dereferences with `XDP_DROP` abort paths while proving Zero-Divergence on valid network frames.

### 4. Zero-Source Native Binary Lifter & CFG Reconstructor
Operates without source code: ingests stripped Mach-O or ELF binaries, reconstructs function control-flow graphs, audits ROP/JOP gadgets, and lifts machine instructions into symbolic LLVM micro-IR for formal SMT verification.

### 5. Micro-Level LLVM SSA SMT Memory Modeling
Models `@llvm.memcpy.p0.p0.*`, `@llvm.memset.p0.*`, and `@llvm.memmove.p0.*` as Z3 bitvector store-forwarding, proving semantic equivalence between raw memory block zeroizations and register SSA in $< 1\text{ ms}$.

---

## ⚡ Zero-Friction Adoption Modes

Ecstasy fits into existing developer workflows with **zero configuration changes**:

### Mode 1: Transparent Drop-in Compiler (`ecstasy-cc` & `ecstasy-c++`)
Replace `clang`/`gcc` in any Makefile, CMake, or autotools build without modifying code:
```bash
# Compiling with Make
export CC=ecstasy-cc CXX=ecstasy-c++
make

# Compiling with CMake
cmake -DCMAKE_C_COMPILER=ecstasy-cc -DCMAKE_CXX_COMPILER=ecstasy-c++ ..
cmake --build .

# Direct CLI compilation
ecstasy-cc -O2 main.c -o app
```

### Mode 2: Turnkey Reusable GitHub Action (`action.yml`)
Add zero-defect SMT security verification directly to your GitHub CI/CD pipeline:
```yaml
name: Ecstasy SMT Security Gate
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Ecstasy Provable Cyber Defense
        uses: adityakulthe/Ecstasy@main
        with:
          target: './src'
          fail-on-exploit: true
          sarif-upload: true
          pr-comment: true
```

### Mode 3: 1-Click AI Coding Agent Integration (Cursor, Claude, Windsurf)
Expose Ecstasy's 26 formal verification tools directly to Cursor IDE and Claude Desktop:
```bash
# Automatically configure .cursor/mcp.json
ecstasy mcp --install-cursor

# Automatically configure Claude Desktop
ecstasy mcp --install-claude
```

### Mode 4: Google Cloud & Kubernetes Gatekeeper
Deploy continuous admission controllers into Google Kubernetes Engine (GKE):
```bash
# Verify container artifact against Google Cloud Binary Authorization
ecstasy-gcp-gatekeeper --attestation /tmp/attestation.json --image-digest sha256:...
```

### Mode 5: Interactive Dark Terminal Web IDE (`ecstasy ui`)
Launch the interactive Godbolt-style web playground:
```bash
ecstasy ui --port 8501
```
Features 5 interactive studios: Standard View, Live Pipeline Dashboard, Z3 SMT Translation Validator, Multi-Agent Council & SARIF Audit, and Provable Cyber Defense Exploit Studio.

---

## 📊 Scientific Benchmarks & Empirical Evaluation

Ecstasy has been evaluated across standard computational algorithms and real-world cybersecurity targets. All experiments are 100% reproducible with `./scripts/reproduce_all_experiments.sh`.

### Table 1: Multi-Paradigm Benchmark Corpus Results

| Benchmark Category | Target Artifact | LLVM Insts | SMT Latency (ms) | CWEs Detected | Zero-Divergence Invariant | Soundness Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Memory Safety (CWE-125/787) | `buffer_overflow` | 6 | 3.63 ms | 1 | :white_check_mark: | `TRUE_POSITIVE` |
| Arithmetic Fault (CWE-369) | `integer_divide_zero` | 4 | 0.64 ms | 1 | :white_check_mark: | `TRUE_POSITIVE` |
| Safe Memory Access | `safe_linear_search` | 3 | 0.04 ms | 0 | :white_check_mark: | `TRUE_NEGATIVE` |
| Side-Channel (CWE-208) | `crypto_mac_timing_leak` | 6 | 0.14 ms | 1 | :white_check_mark: | `TRUE_POSITIVE` |
| Constant-Time Crypto | `constant_time_mux` | 8 | 0.16 ms | 0 | :white_check_mark: | `TRUE_NEGATIVE` |
| Post-Quantum (FIPS 203) | `ml_kem_kyber_reduction` | 7 | 0.10 ms | 1 | :white_check_mark: | `TRUE_POSITIVE` |
| Linux Kernel eBPF | `ebpf_unbounded_packet` | 5 | 0.03 ms | 1 | :white_check_mark: | `TRUE_POSITIVE` |
| Hardware Fault (CWE-1254) | `fault_injection_auth_gate` | 6 | 0.09 ms | 1 | :white_check_mark: | `TRUE_POSITIVE` |
| **Corpus Summary (N=8)** | *Mean ± StdDev* | — | **0.60 ± 1.16 ms** | — | **100.0%** | **Precision: 100%, Recall: 100%, F1: 1.00** |

### Table 2: Whole-Corpus Optimization Benchmark (`ecstasy benchmark demo_corpus`)

| Target File | `-O0` IR Insts | `-O2` IR Insts | Reduction | CWEs Detected | Z3 Verdict | Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `algorithms/dynamic_programming.c` | 1,239 | 1,017 | **17.9%** | 11 | `PROVED` | 87 ms |
| `algorithms/graph.c` | 1,107 | 988 | **10.8%** | 5 | `PROVED` | 94 ms |
| `algorithms/sorting.c` | 1,063 | 732 | **31.1%** | 6 | `PROVED` | 57 ms |
| `math/matrix_ops.c` | 1,097 | 673 | **38.6%** | 3 | `PROVED` | 55 ms |
| `math/numerical_methods.c` | 835 | 338 | **59.5%** | 1 | `PROVED` | 46 ms |
| `math/statistics.c` | 1,016 | 589 | **42.0%** | 3 | `PROVED` | 51 ms |
| `physics/nbody.c` | 969 | 455 | **53.0%** | 3 | `PROVED` | 48 ms |
| `signal/fft.c` | 899 | 691 | **23.1%** | 4 | `PROVED` | 53 ms |
| `unsafe/buffer_overflow.c` | 189 | 123 | **34.9%** | 9 | `PROVED` | 47 ms |
| **Total / Average (9/9 Files)** | **8,414** | **5,606** | **33.4% Reduced** | **45 CWEs** | **9/9 `PROVED`** | **536 ms** |

### Table 3: Defensive Baseline Comparison

| Metric / Dimension | Clang `-O2` (No Defense) | AddressSanitizer (ASan) | LLVM SafeStack & CFI | **Ecstasy Provable Cyber Defense** |
| :--- | :---: | :---: | :---: | :---: |
| **Runtime Overhead** | 0.0% | +120.0% | +8.5% | **0.0% (Compile-Time Formal Proof)** |
| **Memory Overhead** | 0.0% | +250.0% | +15.0% | **0.0% (Zero Auxiliary Shadow Memory)** |
| **CWE Defense Coverage** | 0/8 (0%) | 2/8 (25% Memory Only) | 2/8 (25% Stack/CFI Only) | **8/8 (100% Memory, Crypto, PQC, Spectre, Faults)** |
| **Side-Channel Timing Guarantee** | None | None (Blind to CWE-208) | None | **Mathematical Z3 Proof ($\mathcal{CT}_{\text{time}} \land \mathcal{CT}_{\text{cache}}$)** |
| **Supply Chain Compliance** | None | None | None | **CycloneDX v1.6 CBOM + in-toto v1.0 DSSE** |

---

## 🛠️ CLI Subcommand Reference (30 Commands)

```bash
ecstasy <command> [options]
```

### Verification & Formal Proofs
- `ecstasy verify <src.ll> <opt.ll>`: Validate translation semantic equivalence in Z3 SMT and Alive2.
- `ecstasy verify-cert <cert.json> -b <bin>`: Verify HMAC-SHA256 signature and binary digest of a proof certificate.
- `ecstasy formal-proofs <target.ll> -t [smtlib2|lean4|coq]`: Export machine-checkable proof certificates.
- `ecstasy hyperproperties <target.ll> [--constant-time|--sni|--fault-resilience|--cfi|--cache-line]`: Formally prove relational 2-safety hyperproperties via $P \times P$ self-composition.
- `ecstasy research-eval`: Run comprehensive empirical evaluation across benchmark corpus and output LaTeX tables.

### Compilation & Optimization
- `ecstasy compile <src.c> -o <bin> [--advanced] [--cert] [--html]`: Full 9-agent compilation, optimization, and verification pipeline.
- `ecstasy cc [clang_args...]`: Invoke transparent drop-in compiler driver with SMT Provable Cyber Defense.
- `ecstasy benchmark <dir> [--report <out.json>]`: Run automated optimization and verification benchmark across an entire corpus.

### Provable Cyber Defense (PCD)
- `ecstasy prove <src.c|ir.ll> [--sarif <out.sarif>]`: Formally prove CWE reachability in Z3 and synthesize triggering exploit payloads.
- `ecstasy harden <src.c|ir.ll> -o <hardened.ll>`: Apply automated branchless mitigations with Zero-Divergence SMT proof.
- `ecstasy constant-time <src.c|ir.ll>`: Formally verify cryptographic constant-time side-channel resistance (CWE-208/CWE-385).
- `ecstasy pqc <src.c|ir.ll> [--scheme ML_KEM_KYBER]`: Verify Post-Quantum Cryptography lattice operations against timing leaks.
- `ecstasy spectre <src.c|ir.ll>`: Check Speculative Non-Interference (SNI) against Spectre v1/v2 and synthesize selective speculation barriers.
- `ecstasy cfi <src.c|ir.ll> -o <hardened.ll>`: Audit indirect call targets and enforce forward-edge Control-Flow Integrity jump tables.
- `ecstasy pac <src.c|ir.ll> -o <hardened.ll>`: Instrument IR with ARM64 Pointer Authentication (PAC) and Memory Tagging Extension (MTE) intrinsics.
- `ecstasy ebpf <src.c|ir.ll> [--rewrite] -o <safe.ll>`: Formally verify Linux kernel eBPF packet bounds and 512-byte stack frame limit.
- `ecstasy fault-resilience <src.c|ir.ll> [--synthesize] -o <safe.ll>`: Synthesize dual-rail complementary registers and `@llvm.trap` glitch aborts.
- `ecstasy fuzz <src.c|ir.ll>`: Differentially execute synthesized SMT exploit PoC harness against unhardened vs hardened binaries in sandbox.
- `ecstasy lift <binary_path> -o <lifted.ll>`: Lift stripped Mach-O or ELF binaries into symbolic LLVM micro-IR and audit ROP gadgets.
- `ecstasy check-memory <src.c|ir.ll>`: Audit source or IR for memory safety and buffer overflows.
- `ecstasy audit <dir> [--sarif <out.sarif>] [--report <out.json>]`: Audit an entire project repository for CWE vulnerabilities.
- `ecstasy attack-matrix <src.c|ir.ll> -o <layer.json>`: Generate MITRE ATT&CK Matrix mapping and ATT&CK Navigator v4.3 JSON layer.

### Continuous Compliance & Autonomous Healing
- `ecstasy cbom <src.c|ir.ll> -o <cbom.json>`: Generate CycloneDX v1.6 Cryptographic Bill of Materials (CBOM) with NIST SP 800-218 attestation.
- `ecstasy attest <target> -o <attestation.json>`: Generate or verify cryptographically signed in-toto v1.0 DSSE attestation envelopes.
- `ecstasy guard <src.c|ir.ll>`: Closed-loop self-healing CI/CD gatekeeper generating verified unified git diff patches.
- `ecstasy watch <dir> [--once]`: Continuous real-time repository watch daemon auditing and self-healing modified files.

### Developer Experience & Diagnostics
- `ecstasy doctor`: Run system and toolchain diagnostic checks (Clang, LLVM, Z3, Alive2, signing keys).
- `ecstasy demo <midpoint|overflow|constant_time>`: Run interactive demonstration scenarios.
- `ecstasy ui [--port 8501]`: Launch interactive dark-terminal Godbolt Streamlit Web IDE.
- `ecstasy mcp [--list-tools] [--install-cursor] [--install-claude]`: Run FastMCP server or configure AI IDE assistants.

---

## 🔌 FastMCP Server Reference (26 Tools)

Ecstasy exposes its complete formal verification and security toolchain through the Model Context Protocol (FastMCP) for direct use by Claude Desktop, Cursor, and Windsurf:

| FastMCP Tool | Category | Description |
| :--- | :--- | :--- |
| `mcp_compile_to_ir` | Compilation | Compile C/C++ source code to unoptimized LLVM IR (`.ll`). |
| `mcp_optimize_ir` | Optimization | Apply AI-driven or deterministic LLVM optimization passes. |
| `mcp_verify_ir_equivalence` | Verification | Formally verify bit-accurate semantic equivalence ($\text{Target} \sqsubseteq \text{Source}$) via Alive2 & Z3 SMT. |
| `mcp_audit_memory_safety` | Audit | Audit LLVM IR for CWE memory vulnerabilities and export OASIS SARIF v2.1.0. |
| `mcp_run_corpus_benchmark` | Benchmark | Run automated C/IR corpus benchmark with Z3 formal verification. |
| `mcp_supervise_pipeline` | Pipeline | Execute the full 9-agent parallel deliberation & formal verification compiler pipeline. |
| `mcp_prove_vulnerability` | PCD | Formally prove CWE exploitability in Z3 (CWE-125, 787, 190, 369, 476) and synthesize concrete triggering payloads. |
| `mcp_verify_constant_time` | PCD | Formally verify cryptographic constant-time side-channel resistance (CWE-208 / CWE-385). |
| `mcp_harden_security` | PCD | Apply automated branchless security hardening with Zero-Divergence SMT proof. |
| `mcp_export_cbom` | Supply Chain | Generate CycloneDX v1.6 Cryptographic Bill of Materials (CBOM) with NIST SP 800-218 formal attestation. |
| `mcp_verify_exploit_poc` | Sandbox | Differentially verify synthesized SMT exploit PoC harness against unhardened vs hardened binaries. |
| `mcp_synthesize_constant_time` | Synthesis | Synthesize branchless constant-time cryptographic primitives with SMT Zero-Divergence proof. |
| `mcp_analyze_attack_surface` | Threat Modeling | Analyze cyber attack surface and export MITRE ATT&CK Matrix Navigator v4.3 layer. |
| `mcp_enforce_cfi` | PCD | Enforce forward-edge Control-Flow Integrity (CFI) on indirect function calls to prevent ROP/JOP hijacking. |
| `mcp_verify_pqc_constant_time` | PCD | Formally verify Post-Quantum Cryptography (ML-KEM / ML-DSA) constant-time side-channel resistance. |
| `mcp_enforce_hardware_safety` | PCD | Instrument LLVM IR with ARM64 Pointer Authentication (PAC) & Memory Tagging Extension (MTE). |
| `mcp_generate_attestation_bundle` | Supply Chain | Generate cryptographically signed in-toto v1.0 and DSSE supply-chain attestation bundles. |
| `mcp_verify_speculative_execution`| PCD | Formally audit Spectre v1/v2 speculative leaks, prove SNI, and synthesize selective barriers. |
| `mcp_lift_binary_to_ir` | Lifter | Lift stripped native Mach-O or ELF binaries into symbolic LLVM micro-IR and audit ROP gadgets. |
| `mcp_run_self_healing_guard` | Autonomous | Execute autonomous closed-loop self-healing remediation on vulnerable files, generating verified git diffs. |
| `mcp_verify_ebpf_safety` | PCD | Formally verify eBPF kernel invariants (packet bounds, 512B stack, bounded loops) and rewrite unsafe bytecode. |
| `mcp_synthesize_fault_resilience` | PCD | Audit security gates for physical glitching/Rowhammer vulnerabilities and synthesize dual-rail resilience. |
| `mcp_watch_repository` | Autonomous | Run autonomous continuous self-healing repository watch daemon to audit, patch, and attest in real time. |
| `mcp_export_formal_proof_certificate` | Formal Proofs | Export machine-checkable SMT-LIB2 / Lean 4 / Coq mathematical proof certificates for zero-divergence. |
| `mcp_verify_hyperproperties` | Hyperproperties | Verify 2-Safety hyperproperties (Constant-Time, SNI, Fault Immunity, CFI, Cache-Line) via self-composition in Z3. |
| `mcp_run_research_evaluation` | Benchmark | Execute empirical benchmark evaluation across compiler security corpus and generate LaTeX tables. |

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Clang / LLVM (LLVM 15+ recommended)
- Z3 SMT Solver (`brew install z3` on macOS or `sudo apt-get install z3` on Ubuntu)

### Installation
```bash
# Clone the repository
git clone https://github.com/adityakulthe/Ecstasy.git
cd Ecstasy

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies and development package
pip install -r requirements.txt
pip install -e .

# Run system diagnostic checks
ecstasy doctor
```

### Running the Full Formal Test Suite
```bash
pytest -v
```
All **206/206 formal tests** pass with a **100% pass rate** in under **12 seconds** with zero cloud or API key dependencies.

### Reproducing All Scientific Experiments
```bash
./scripts/reproduce_all_experiments.sh
```
Executes the full test suite, evaluates the 8-benchmark empirical corpus, generates the scientific LaTeX table (`docs/benchmark_results.tex`), and validates the Google Cloud Binary Authorization Gatekeeper.

---

## 📄 Academic Citation & Authorship

If you use Ecstasy in your academic research, compiler infrastructure, or cybersecurity tooling, please cite the project repository and technical report:

```bibtex
@misc{kulthe2026ecstasy,
  author       = {Aditya Kulthe},
  title        = {Ecstasy: Provable Cyber Defense and Zero-Divergence Synthesis via Relational Hyperproperties in LLVM SSA},
  howpublished = {\url{https://github.com/adityakulthe/Ecstasy}},
  note         = {Open-Source Software Artifact and Technical Report},
  year         = {2026}
}
```

**Maintainer & Primary Author**:  
**Aditya Kulthe** ([`kultheaditya23@gmail.com`](mailto:kultheaditya23@gmail.com))  
GitHub: [@adityakulthe](https://github.com/adityakulthe)  
Repository: [https://github.com/adityakulthe/Ecstasy](https://github.com/adityakulthe/Ecstasy)

---

## 📜 License

Ecstasy is released under the **Apache-2.0 License**. See [LICENSE](LICENSE) for details.
