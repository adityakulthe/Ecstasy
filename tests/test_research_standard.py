"""
Comprehensive Test Suite for Ecstasy Academic & Research Standards:
- Formal Operational Semantics & Zero-Divergence Refinement Theorems
- SMT-LIB2, Lean 4, and Coq Machine-Checkable Proof Certificate Exporter
- Theoretical 2-Safety Hyperproperty Verification (CT, SNI, Fault Immunity)
- Scientific Benchmark & Empirical Research Evaluator
- FastMCP Research Tools & CLI Integration
"""

import sys
import json
import pytest
from pathlib import Path

from engine.formal_semantics import (
    FormalSemanticsEngine,
    FormalProofCertificate,
    SemanticEvent,
    SemanticEventType,
)
from engine.hyperproperty_prover import (
    HyperpropertyProver,
    HyperpropertyType,
    HyperpropertyProofReport,
)
from engine.research_evaluator import (
    ResearchEvaluator,
    ResearchEvaluationReport,
    BenchmarkExecutionMetric,
)
from server.mcp_server import (
    mcp_export_formal_proof_certificate,
    mcp_verify_hyperproperties,
    mcp_run_research_evaluation,
)


class TestFormalSemanticsEngine:
    """Tests for small-step operational semantics, refinement theorems, and proof certificates."""

    def test_zero_divergence_refinement_proof_and_certificates(self):
        engine = FormalSemanticsEngine(timeout_sec=10)

        orig_ir = """
        define i32 @add_nums(i32 %a, i32 %b) {
        entry:
            %res = add i32 %a, %b
            ret i32 %res
        }
        """

        hardened_ir = """
        define i32 @add_nums(i32 %a, i32 %b) {
        entry:
            %res = add i32 %b, %a
            ret i32 %res
        }
        """

        cert = engine.prove_zero_divergence_refinement(orig_ir, hardened_ir, function_name="add_nums")
        assert cert.is_proved is True
        assert cert.theorem_type == "ZERO_DIVERGENCE"
        assert cert.logic == "QF_BV"
        assert "(set-logic QF_BV)" in cert.smtlib2_code
        assert "theorem add_nums_zero_divergence_soundness" in cert.lean4_code
        assert "Theorem add_nums_soundness" in cert.coq_code
        assert "Bit-Vectors" in cert.smtlib2_code

    def test_translation_validation_proof(self):
        engine = FormalSemanticsEngine(timeout_sec=10)

        orig_ir = """
        define i32 @f(i32 %x) {
        entry:
            %r = mul i32 %x, 2
            ret i32 %r
        }
        """
        opt_ir = """
        define i32 @f(i32 %x) {
        entry:
            %r = shl i32 %x, 1
            ret i32 %r
        }
        """

        cert = engine.prove_translation_validation(orig_ir, opt_ir, function_name="f")
        assert cert.is_proved is True
        assert cert.theorem_type == "TRANSLATION_VALIDATION"
        assert cert.target_name == "f"


class TestHyperpropertyProver:
    """Tests for 2-Safety Constant-Time, Speculative Non-Interference, and Glitch Immunity."""

    def test_constant_time_2_safety_hyperproperty(self):
        prover = HyperpropertyProver(timeout_sec=10)

        # Leaking code with secret-dependent branch
        leaking_ir = """
        define i32 @check(i32 %key, i32 %in) {
        entry:
            %c = icmp eq i32 %key, %in
            br i1 %c, label %t, label %f
        t:
            ret i32 1
        f:
            ret i32 0
        }
        """
        rep_leak = prover.prove_constant_time_hyperproperty(leaking_ir, function_name="check")
        assert rep_leak.is_proved is False
        assert rep_leak.counterexample_trace is not None

        # Safe branchless multiplexer
        safe_ir = """
        define i32 @mux(i32 %key, i32 %a, i32 %b) {
        entry:
            %m = ashr i32 %key, 31
            %inv = xor i32 %m, -1
            %t1 = and i32 %a, %m
            %t2 = and i32 %b, %inv
            %r = or i32 %t1, %t2
            ret i32 %r
        }
        """
        rep_safe = prover.prove_constant_time_hyperproperty(safe_ir, function_name="mux")
        assert rep_safe.is_proved is True
        assert rep_safe.self_composition_verified is True

    def test_speculative_non_interference_hyperproperty(self):
        prover = HyperpropertyProver(timeout_sec=10)

        # Barrier-protected safe function
        safe_spectre_ir = """
        define i32 @spectre_safe(i32 %x, ptr %arr) {
        entry:
            call void @llvm.aarch64.csdb()
            %p = getelementptr i32, ptr %arr, i32 %x
            %v = load i32, ptr %p
            ret i32 %v
        }
        declare void @llvm.aarch64.csdb()
        """
        rep = prover.prove_speculative_non_interference(safe_spectre_ir, function_name="spectre_safe")
        assert rep.is_proved is True
        assert rep.hyperproperty == HyperpropertyType.SPECULATIVE_NON_INTERFERENCE

    def test_fault_injection_parity_immunity(self):
        prover = HyperpropertyProver(timeout_sec=10)

        ir = "define i32 @auth_gate() { ret i32 0 }"
        rep = prover.prove_fault_injection_immunity(ir, function_name="auth_gate")
        assert rep.is_proved is True
        assert "Immunity against clock/voltage glitching" in rep.security_guarantee

    def test_control_flow_integrity_hyperproperty(self):
        prover = HyperpropertyProver(timeout_sec=10)

        # Protected indirect call with CFI check
        protected_ir = """
        define void @call_fn(ptr %target) {
        entry:
            call void @__cfi_check(ptr %target)
            call void %target()
            ret void
        }
        declare void @__cfi_check(ptr)
        """
        rep = prover.prove_control_flow_integrity(protected_ir, function_name="call_fn")
        assert rep.is_proved is True
        assert rep.hyperproperty == HyperpropertyType.CONTROL_FLOW_INTEGRITY

        # Unguarded indirect call
        unguarded_ir = """
        define void @call_fn(ptr %target) {
        entry:
            call void %target()
            ret void
        }
        """
        rep_un = prover.prove_control_flow_integrity(unguarded_ir, function_name="call_fn")
        assert rep_un.is_proved is False
        assert rep_un.counterexample_trace is not None

    def test_cache_line_invariance_hyperproperty(self):
        prover = HyperpropertyProver(timeout_sec=10)

        # Straight-line branchless code with constant address
        safe_ir = """
        define i32 @const_access(i32 %key, ptr %buf) {
        entry:
            %p = getelementptr i32, ptr %buf, i32 0
            %v = load i32, ptr %p
            ret i32 %v
        }
        """
        rep = prover.prove_cache_line_invariance(safe_ir, function_name="const_access")
        assert rep.is_proved is True
        assert rep.hyperproperty == HyperpropertyType.CACHE_LINE_INVARIANCE


class TestResearchEvaluator:
    """Tests for empirical evaluation, confusion matrix calculation, and LaTeX table emission."""

    def test_comprehensive_evaluation_and_latex_table(self):
        evaluator = ResearchEvaluator()
        report = evaluator.run_comprehensive_evaluation()

        assert report.total_benchmarks_evaluated == 8
        assert report.true_positives == 6
        assert report.true_negatives == 2
        assert report.false_positives == 0
        assert report.false_negatives == 0
        assert report.precision == 1.0
        assert report.recall == 1.0
        assert report.f1_score == 1.0
        assert report.zero_divergence_success_rate == 1.0
        assert report.mean_latency_ms < 15.0

        latex = report.generate_latex_table()
        assert r"\begin{table*}" in latex
        assert r"\caption" in latex
        assert "TRUE_POSITIVE" in latex
        assert "TRUE_NEGATIVE" in latex
        assert r"\end{table*}" in latex


class TestResearchMCPTools:
    """Tests for newly registered FastMCP research tools."""

    def test_mcp_export_formal_proof_certificate_tool(self):
        orig_ir = """
        define i32 @g(i32 %a) {
        entry:
            ret i32 %a
        }
        """
        res = mcp_export_formal_proof_certificate(orig_ir, orig_ir, function_name="g")
        assert res["is_proved"] is True
        assert "smtlib2_code" in res
        assert "lean4_code" in res
        assert "coq_code" in res

    def test_mcp_verify_hyperproperties_tool(self):
        ir = "define i32 @h(i32 %x) { entry: ret i32 0 }"
        res = mcp_verify_hyperproperties(ir, function_name="h")
        assert "constant_time" in res
        assert "speculative_non_interference" in res
        assert "fault_injection_immunity" in res
        assert "control_flow_integrity" in res
        assert "cache_line_invariance" in res

    def test_mcp_run_research_evaluation_tool(self):
        res = mcp_run_research_evaluation(export_latex=True)
        assert res["total_benchmarks_evaluated"] == 8
        assert res["confusion_matrix"]["precision" if "precision" in res["confusion_matrix"] else "true_positives"] == 6
        assert "latex_table" in res


class TestResearchCLICommands:
    """Verify execution of new research CLI subcommands: formal-proofs, hyperproperties, research-eval."""

    def test_cli_formal_proofs_command(self, tmp_path):
        ir_file = tmp_path / "simple.ll"
        ir_file.write_text("define i32 @foo(i32 %x) { entry: ret i32 %x }", encoding="utf-8")

        from cli import main
        sys.argv = ["cli.py", "formal-proofs", str(ir_file), "--lean4"]
        main()

    def test_cli_hyperproperties_command(self, tmp_path):
        ir_file = tmp_path / "hyp.ll"
        ir_file.write_text("define i32 @bar(i32 %x) { entry: ret i32 1 }", encoding="utf-8")

        from cli import main
        sys.argv = ["cli.py", "hyperproperties", str(ir_file)]
        main()

    def test_cli_research_eval_command(self, tmp_path):
        from cli import main
        out_table = tmp_path / "test_table.tex"
        sys.argv = ["cli.py", "research-eval", "--latex", "-o", str(out_table)]
        main()
        assert out_table.exists()
