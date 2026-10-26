# Getting Started with Ecstasy: Provable Cyber Defense (PCD)

Ecstasy is an AI-powered compiler optimization and Provable Cyber Defense (PCD) engine that hardens code against critical vulnerabilities (`CWE-120`, `CWE-125`, `CWE-200`, `CWE-208`, `CWE-416`, `CWE-1240`) and mathematically proves Zero-Divergence functional refinement ($\text{Target} \sqsubseteq \text{Source}$) using the Z3 SMT solver, Lean 4, and Coq.

---

## ⚡ 1. Quick Installation

### Prerequisites
- Python 3.10+
- Clang / LLVM (LLVM 15+)
- Z3 SMT Solver

### Install via pip (Developer / Source)
```bash
git clone https://github.com/adityakulthe/Ecstasy.git
cd Ecstasy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Verify your installation:
```bash
ecstasy doctor
```

---

## 🔨 2. Drop-in Compiler Replacement (`ecstasy-cc` & `ecstasy-c++`)

Ecstasy can act as a **transparent drop-in replacement for Clang/GCC** in any existing build system.

### Compiling with Make
```bash
export CC=ecstasy-cc
export CXX=ecstasy-c++
make
```

### Compiling with CMake
```bash
mkdir build && cd build
cmake -DCMAKE_C_COMPILER=ecstasy-cc -DCMAKE_CXX_COMPILER=ecstasy-c++ ..
cmake --build .
```

### Direct Compilation
```bash
# Compile and link with SMT-verified Provable Cyber Defense
ecstasy-cc -O2 src/main.c -o my_app

# Compile object files individually (-c)
ecstasy-cc -c src/module1.c -o module1.o
ecstasy-cc -c src/module2.c -o module2.o
ecstasy-cc module1.o module2.o -o my_app

# Enable verbose SMT verification logs and export Lean 4 proof certificates
ecstasy-cc --ecstasy-verbose --ecstasy-proofs -O2 src/main.c -o my_app
```

---

## 🛡️ 3. 1-Click GitHub Actions CI/CD Integration

Protect your team's repository on every push and pull request. Add `.github/workflows/ecstasy.yml`:

```yaml
name: Ecstasy Provable Cyber Defense

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  contents: read
  security-events: write
  pull-requests: write

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run Ecstasy SMT Verification
        uses: adityakulthe/Ecstasy@main
        with:
          target: './src'
          fail-on-exploit: true
          sarif-output: 'ecstasy-audit.sarif'
          cbom-output: 'ecstasy-cbom.json'
          pr-comment: true

      - name: Upload OASIS SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: ecstasy-audit.sarif
```

---

## 🤖 4. 1-Click AI Coding Agent Integration (Cursor & Claude)

Ecstasy includes a 26-tool **FastMCP** server that acts as a formal verification guardrail for AI coding assistants.

### Configure for Cursor IDE
```bash
# Installs configuration into .cursor/mcp.json
ecstasy mcp --install-cursor

# Or install globally for your entire user account (~/.cursor/mcp.json)
ecstasy mcp --install-cursor --global
```

### Configure for Claude Desktop
```bash
# Installs configuration into claude_desktop_config.json
ecstasy mcp --install-claude
```

### Inspect Configuration JSON
```bash
ecstasy mcp --print-config
```

Once installed, your AI agent can automatically verify that generated C/C++ code is free of memory exploits, constant-time compliant, and semantically equivalent before running it.

---

## 💻 5. Interactive Godbolt-Style Web Explorer

Launch the local interactive visual IDE:
```bash
ecstasy ui
```
Opens in your browser at `http://localhost:8501`:
- Load pre-configured vulnerability presets (Buffer Overflow, Spectre v1, Kyber MAC Timing Leak, eBPF OOB Access, Fault Glitching).
- Side-by-side LLVM IR and disassembly diff.
- Live Z3 SMT solver counterexamples, Lean 4 / Coq proof certificates, and CycloneDX CBOM inspector.

---

## 🔬 6. Research & Scientific Verification

```bash
# Export machine-checkable Lean 4 proof certificates
ecstasy formal-proofs target.ll --lean4 -o proof.lean

# Verify 2-Safety Hyperproperties via self-composition (Constant-Time, SNI, Fault Parity)
ecstasy hyperproperties target.ll --ct --sni --fault

# Run whole-corpus benchmark and generate publication LaTeX tables
ecstasy research-eval --latex -o docs/benchmark_results.tex
```
