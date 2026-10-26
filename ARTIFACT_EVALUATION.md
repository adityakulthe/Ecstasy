# Ecstasy Artifact Evaluation Guide

This guide describes how to replicate all experimental results, formal SMT proofs, and benchmark evaluations presented in the **Ecstasy** research paper.

---

## 1. Artifact Overview

- **Badges Applied For**:
  - ✅ **Artifacts Available**
  - ✅ **Artifacts Evaluated — Functional**
  - ✅ **Results Replicated**
- **Repository**: [https://github.com/adityakulthe/Ecstasy](https://github.com/adityakulthe/Ecstasy)
- **Primary Contacts**: Aditya Kulthe (`adityakulthe12@gmail.com`)
- **Key Claims Evaluated**:
  1. **Zero False Positives & Negatives**: 100.0% precision, 100.0% recall, $F_1 = 1.00$ on the vulnerability corpus.
  2. **Microsecond SMT Solving Latency**: Mean solving time $< 1.0$ ms per function with Z3 SMT.
  3. **Zero-Divergence Invariant**: 100% of generated patches preserve bit-accurate equivalence on valid input domains.
  4. **Hyperproperty Verification**: Proves 2-Safety Constant-Time ($\mathcal{CT}$), Speculative Non-Interference ($\mathcal{SNI}$), and Fault-Injection Parity Immunity ($\mathcal{FII}$).
  5. **Cloud-Native Gatekeeper**: Turnkey in-toto v1.0 DSSE supply-chain attestations verified by Google Cloud Binary Authorization and Kubernetes admission webhooks.

---

## 2. Requirements & Environment Setup

### Software Requirements
- **Operating Systems**: macOS (Apple Silicon or Intel), Linux (Ubuntu 22.04+ / Debian 12 / RHEL 9)
- **Python**: Version 3.10, 3.11, or 3.12
- **Core Toolchains**:
  - `z3` (Z3 SMT Solver v4.12+)
  - `clang` & `llvm` (LLVM 15+)

### Quick Installation
```bash
# Clone the repository
git clone https://github.com/adityakulthe/Ecstasy.git
cd Ecstasy

# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .[dev]

# Run system diagnostic health check
ecstasy doctor
```

---

## 3. One-Command Full Experiment Replication

To replicate all experimental tables, benchmark metrics, and formal verification proofs in a single run:

```bash
# Run automated research evaluation harness
python -m engine.research_evaluator
# Or via the Ecstasy CLI
ecstasy research-eval --latex
```

Expected output:
- Complete confusion matrix (TP: 6, TN: 2, FP: 0, FN: 0)
- Precision: 100.0%, Recall: 100.0%, F1: 1.00
- Mean latency: $< 1.0$ ms
- LaTeX table printed to stdout and saved to `docs/benchmark_results.tex`.

---

## 4. Step-by-Step Individual Experiment Replication

### Experiment 1: Full Test Suite Verification (100% Pass Rate)
```bash
pytest -q --tb=short
```
*Expected Result*: All 179+ tests pass in $< 8.0$ seconds with 0 errors.

### Experiment 2: Formal Proof Certificate Export (SMT-LIB2, Lean 4, Coq)
```bash
ecstasy formal-proofs tests/fixtures/combined.ll --lean4 -o /tmp/theorem.lean
cat /tmp/theorem.lean
```
*Expected Result*: Machine-checkable Lean 4 theorem proving Zero-Divergence refinement.

### Experiment 3: Hyperproperty Verification (2-Safety Constant-Time & SNI)
```bash
# Constant-Time side-channel audit
ecstasy constant-time demo_corpus/unsafe/buffer_overflow.c

# Speculative Non-Interference (Spectre v1/v2)
ecstasy spectre tests/fixtures/combined.ll
```
*Expected Result*: Formal SMT proof showing whether Speculative Non-Interference holds.

### Experiment 4: Google Cloud Binary Authorization & Kubernetes Gatekeeper
```bash
# Generate signed in-toto v1.0 DSSE attestation carrying Z3 proofs
ecstasy attest demo_corpus/unsafe/buffer_overflow.c -o /tmp/attestation.json

# Verify admission against Google Cloud Binary Authorization policy
python deploy/gcp/gcp_gatekeeper.py --verify-attestation /tmp/attestation.json
```
*Expected Result*: `Decision: 🟢 ADMIT (Workload Allowed)` with all security checks passing.

---

## 5. Artifact Directory Structure

```
Ecstasy/
├── engine/                       # Core Provable Cyber Defense Engine
│   ├── formal_semantics.py       # Operational semantics & Lean 4 / SMT-LIB2 exporter
│   ├── hyperproperty_prover.py   # 2-Safety CT, SNI, and glitch immunity provers
│   ├── research_evaluator.py     # Statistical evaluation and LaTeX table generator
│   ├── symbolic_verifier.py      # Translation validator & Z3 symbolic executor
│   ├── smt_vulnerability_prover.py # SMT reachability & exploit synthesizer
│   ├── pqc_verifier.py           # ML-KEM / ML-DSA post-quantum constant-time verifier
│   ├── ebpf_verifier.py          # Linux kernel packet bounds & stack verifier
│   ├── fault_resilience.py       # Dual-rail glitch resilience synthesizer
│   └── attestation_bundle.py     # in-toto v1.0 & DSSE supply-chain signer
├── deploy/                       # Cloud-Native Gatekeepers
│   ├── gcp/cloudbuild.yaml       # Google Cloud Build pipeline
│   ├── gcp/binary_authorization_policy.yaml # GKE admission policy
│   ├── gcp/gcp_gatekeeper.py    # GCP Binary Authorization evaluation engine
│   └── k8s/admission_controller.py # Kubernetes Validating Admission Webhook
├── paper/                        # Academic Publications & Reports
│   ├── ecstasy_paper.md          # Full academic paper (Markdown)
│   └── ecstasy_pldi.tex          # Publication-ready LaTeX paper
├── demo_corpus/                  # Standardized Benchmark Targets
└── tests/                        # 179+ formal unit & integration tests
```
