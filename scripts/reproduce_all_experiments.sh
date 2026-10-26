#!/usr/bin/env bash
# ==============================================================================
# Ecstasy Provable Cyber Defense - Scientific Experiment Reproduction Script
# Reproduces all benchmark numbers, confusion matrices, and LaTeX tables.
# ==============================================================================

set -euo pipefail

echo "========================================================================"
echo "🔬 ECSTASY: REPRODUCING ALL SCIENTIFIC BENCHMARKS & EXPERIMENTS"
echo "========================================================================"

# Use local virtualenv if present
PYTHON_BIN="python3"
PYTEST_BIN="pytest"
if [ -d ".venv" ]; then
    PYTHON_BIN=".venv/bin/python"
    PYTEST_BIN=".venv/bin/pytest"
fi

# 1. Run Complete Test Suite
echo ""
echo "[1/4] Running Formal Test Suite (100% Pass Rate Target)..."
"$PYTEST_BIN" -q --tb=short

# 2. Run Research Evaluation Engine
echo ""
echo "[2/4] Running Research Evaluator & SMT Solvers across Benchmark Corpus..."
"$PYTHON_BIN" -c "
from engine.research_evaluator import ResearchEvaluator
evaluator = ResearchEvaluator()
report = evaluator.run_comprehensive_evaluation()
print(f'Benchmarks Evaluated: {report.total_benchmarks_evaluated}')
print(f'Precision:            {report.precision * 100:.1f}%')
print(f'Recall:               {report.recall * 100:.1f}%')
print(f'F1 Score:             {report.f1_score:.2f}')
print(f'Mean SMT Latency:     {report.mean_latency_ms:.2f} ms')
print(f'Zero-Divergence:      {report.zero_divergence_success_rate * 100:.1f}%')
"

# 3. Export Publication LaTeX Table
echo ""
echo "[3/4] Generating Scientific LaTeX Benchmark Table..."
"$PYTHON_BIN" -c "
from engine.research_evaluator import ResearchEvaluator
evaluator = ResearchEvaluator()
report = evaluator.run_comprehensive_evaluation()
import os
os.makedirs('docs', exist_ok=True)
with open('docs/benchmark_results.tex', 'w') as f:
    f.write(report.generate_latex_table())
print('Saved: docs/benchmark_results.tex')
"

# 4. Verify Google Cloud & Kubernetes Gatekeeper
echo ""
echo "[4/4] Verifying Google Cloud Binary Authorization Gatekeeper..."
"$PYTHON_BIN" -c "
from engine.attestation_bundle import AttestationBundleGenerator
from deploy.gcp.gcp_gatekeeper import GCPGatekeeper
import json, tempfile
gen = AttestationBundleGenerator()
bundle = gen.generate_bundle(target_name='repro_test', artifacts=[], formal_verdict='PROVED', zero_divergence_proved=True)
with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
    json.dump(bundle, f)
    tmp_path = f.name
gk = GCPGatekeeper()
decision = gk.evaluate_admission_decision(tmp_path)
print(f'GCP Gatekeeper Admission Decision: {decision[\"decision\"]}')
assert decision['admitted'] is True
import os
os.unlink(tmp_path)
"

echo ""
echo "========================================================================"
echo "✅ ALL EXPERIMENTS REPRODUCED SUCCESSFULLY WITH ZERO DEFECTS"
echo "========================================================================"
