"""
Tests for Ecstasy Security Auditing, Executive HTML Attestation, and C++ Compilation.
"""

import os
import json
import tempfile
from pathlib import Path
import pytest

from agents.safety_vault import SafetyVault, ProofCertificate
from server.mcp_server import compile_to_ir
import cli


class TestSafetyVaultAttestation:
    """Test suite for safety certificate and executive HTML generation."""

    def test_certificate_dynamic_versions(self):
        vault = SafetyVault()
        cert = vault.generate_certificate(
            project_name="TestProject",
            source_code="int main() { return 0; }",
            ir_code="define i32 @main() { ret i32 0 }",
            binary_path=None,
            z3_verdict="PROVED"
        )
        assert cert.z3_verdict == "PROVED"
        assert cert.certificate_id is not None
        assert cert.signature is not None
        assert cert.z3_version != "unknown"
        assert cert.source_hash.startswith("sha256:")
        assert cert.ir_hash.startswith("sha256:")

    def test_export_html_report(self):
        vault = SafetyVault()
        cert = vault.generate_certificate(
            project_name="FooModule",
            source_code="int foo(int x) { return x; }",
            ir_code="define i32 @foo(i32 %x) { ret i32 %x }",
            binary_path=None,
            z3_verdict="PROVED"
        )

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            html_path = f.name

        try:
            vault.export_html_report(cert, html_path)
            assert os.path.exists(html_path)
            content = Path(html_path).read_text(encoding="utf-8")

            # Check core sections in HTML
            assert "<!DOCTYPE html>" in content
            assert cert.certificate_id in content
            assert cert.source_hash in content
            assert cert.ir_hash in content
            assert cert.signature in content
            assert "MATHEMATICALLY VERIFIED &amp; MEMORY HARDENED" in content or "MATHEMATICALLY VERIFIED & MEMORY HARDENED" in content
            assert "Cryptographic Bill of Materials" in content
            assert "NIST SP 800-218" in content
        finally:
            if os.path.exists(html_path):
                os.unlink(html_path)

    def test_tamper_detection(self):
        vault = SafetyVault()
        cert = vault.generate_certificate(
            project_name="TamperTest",
            source_code="int a() { return 1; }",
            ir_code="define i32 @a() { ret i32 1 }",
            binary_path=None,
            z3_verdict="PROVED"
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cert_path = f.name

        try:
            vault.export_certificate(cert, cert_path)
            # Original certificate should pass verification
            res = vault.verify_certificate(cert_path)
            assert res.valid is True
            assert len(res.issues) == 0

            # Tamper with the certificate
            with open(cert_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["z3_verdict"] = "FAILED"
            with open(cert_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            # Tampered certificate should fail verification
            tampered_res = vault.verify_certificate(cert_path)
            assert tampered_res.valid is False
            assert any("Signature mismatch" in issue for issue in tampered_res.issues)
        finally:
            if os.path.exists(cert_path):
                os.unlink(cert_path)


class TestAuditCLI:
    """Test suite for ecstasy audit and batch vulnerability scanning."""

    def test_audit_directory_scanning(self, capsys):
        fixtures_dir = Path(__file__).parent / "fixtures"

        class DummyArgs:
            path = str(fixtures_dir)
            offline = True
            report = None

        cli.cmd_audit(DummyArgs())
        captured = capsys.readouterr().out

        assert "ECSTASY SECURITY & MEMORY SAFETY AUDIT" in captured
        assert "Audit Summary:" in captured
        assert "guards injected" in captured

    def test_audit_json_report_export(self):
        fixtures_dir = Path(__file__).parent / "fixtures"

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            report_path = f.name

        try:
            class DummyArgs:
                path = str(fixtures_dir)
                offline = True
                report = report_path

            cli.cmd_audit(DummyArgs())

            assert os.path.exists(report_path)
            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "timestamp" in data
            assert data["files_scanned"] > 0
            assert "guards_injected" in data
            assert "records" in data
            assert isinstance(data["records"], list)
        finally:
            if os.path.exists(report_path):
                os.unlink(report_path)


class TestCppCompilation:
    """Test suite for C++ frontend routing in MCP server."""

    def test_cpp_compilation_routing(self):
        cpp_code = """
        class Adder {
        public:
            int add(int a, int b) { return a + b; }
        };

        extern "C" int run(int x, int y) {
            Adder a;
            return a.add(x, y);
        }
        """
        result = compile_to_ir(cpp_code, filename="test.cpp")
        assert result["success"] is True
        assert "@run" in result["ir"]


class TestDeepBugRegressionSuite:
    """Regression suite covering deep compiler, Z3 symbolic verifier, and multi-agent bug fixes."""

    def test_optnone_stripping_enables_real_o2_optimization(self):
        from server.mcp_server import optimize_ir_pass
        c_code = "int add_ten(int x) { int y = x + 4; int z = y + 6; return z; }"
        comp = compile_to_ir(c_code, "optnone_test.c")
        assert comp["success"] is True
        assert "optnone" in comp["ir"]
        assert "alloca" in comp["ir"]

        opt_res = optimize_ir_pass(comp["ir"], use_ai=True)
        try:
            assert opt_res["transformation_applied"] is True
            assert "alloca" not in opt_res["optimized_ir"]
            assert "optnone" not in opt_res["optimized_ir"]
        finally:
            for k in ("orig_path", "opt_path"):
                if opt_res.get(k) and os.path.exists(opt_res[k]):
                    os.unlink(opt_res[k])

    def test_extract_functions_linkage_and_single_line(self):
        from engine.symbolic_verifier import SymbolicIRVerifier
        verifier = SymbolicIRVerifier()
        ir = """
define dso_local signext i32 @foo(i32 noundef %a) local_unnamed_addr #0 {
entry:
  ret i32 %a
}
define internal i32 @bar() { ret i32 42 }
"""
        funcs = verifier.extract_functions(ir)
        assert "foo" in funcs
        assert "bar" in funcs
        assert funcs["bar"][2].strip() == "ret i32 42"

    def test_symbolic_verifier_64bit_constants_and_reversed_phi(self):
        from engine.symbolic_verifier import verify_ir_equivalence, VerificationVerdict
        orig_ir = """
define i64 @compute64(i64 %x) {
entry:
  %p = alloca i64, align 8
  store i64 %x, ptr %p, align 8
  %v = load i64, ptr %p, align 8
  %cmp = icmp sgt i64 %v, 0
  br i1 %cmp, label %if.then, label %if.else
if.then:
  %t = add i64 %v, 4294967296
  br label %end
if.else:
  %f = add i64 %v, 1
  br label %end
end:
  %res = phi i64 [ %f, %if.else ], [ %t, %if.then ]
  ret i64 %res
}
"""
        opt_ir = """
define i64 @compute64(i64 %x) {
entry:
  %cmp = icmp sgt i64 %x, 0
  %t = add i64 %x, 4294967296
  %f = add i64 %x, 1
  %res = select i1 %cmp, i64 %t, i64 %f
  ret i64 %res
}
"""
        report = verify_ir_equivalence(orig_ir, opt_ir)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_symbolic_verifier_conditional_store_merging(self):
        from engine.symbolic_verifier import verify_ir_equivalence, VerificationVerdict
        orig_ir = """
define i32 @abs_val(i32 %x) {
entry:
  %retval = alloca i32, align 4
  %cmp = icmp slt i32 %x, 0
  br i1 %cmp, label %if.then, label %if.else
if.then:
  %neg = sub i32 0, %x
  store i32 %neg, ptr %retval, align 4
  br label %return
if.else:
  store i32 %x, ptr %retval, align 4
  br label %return
return:
  %0 = load i32, ptr %retval, align 4
  ret i32 %0
}
"""
        opt_ir = """
define i32 @abs_val(i32 %x) {
entry:
  %cmp = icmp slt i32 %x, 0
  %neg = sub i32 0, %x
  %res = select i1 %cmp, i32 %neg, i32 %x
  ret i32 %res
}
"""
        report = verify_ir_equivalence(orig_ir, opt_ir)
        assert report.verdict == VerificationVerdict.PROVED

    def test_global_context_constant_propagation_and_call_graph(self):
        from agents.global_context_agent import GlobalContextAgent
        agent = GlobalContextAgent()
        file_caller = """
define i32 @main() {
entry:
  %r = call i32 @scale(i32 noundef 7)
  ret i32 %r
}
"""
        file_callee = """
define i32 @scale(i32 noundef %x) {
entry:
  %m = mul i32 %x, 3
  ret i32 %m
}
define i32 @unused_helper(i32 %a) {
entry:
  ret i32 %a
}
"""
        agent._extract_functions(file_caller, "main.ll")
        agent._extract_call_sites(file_caller, "main.ll")
        agent._extract_functions(file_callee, "callee.ll")
        agent._extract_call_sites(file_callee, "callee.ll")
        agent._build_call_graph()
        agent._find_optimization_opportunities()
        opportunities = agent.find_interprocedural_optimizations()

        assert agent.context.functions["scale"].call_count == 1
        assert any(
            o["type"] == "constant_propagation" and o["callee"] == "scale" and "7" in o["constant_value"]
            for o in opportunities
        )
        dead_funcs = [o["function"] for o in opportunities if o["type"] == "dead_function_elimination"]
        assert "unused_helper" in dead_funcs
        assert "main" not in dead_funcs

    def test_cegar_multiline_counterexample_and_instruction_count(self):
        from agents.cegar_supervisor import CEGARSupervisor
        sup = CEGARSupervisor()
        alive_out = (
            "Transformation doesn't verify!\n"
            "ERROR: Target dropped 'nsw' flag\n\n"
            "Example:\n"
            "i32 %a = 2147483647\n"
            "i32 %b = 1\n"
            "Source: poison\n"
            "Target: -2147483648\n"
        )
        ce = sup.parse_counterexample(alive_out)
        assert ce is not None
        assert ce.failure_type == "overflow"
        assert len(ce.values) == 2
        assert ce.values[0].value == "2147483647"
        assert ce.values[1].value == "1"

        ir_with_headers = """
source_filename = "test.c"
target triple = "arm64-apple-macosx"
define i32 @f(i32 %x) #0 {
entry:
  %y = add i32 %x, 1
  ret i32 %y
}
attributes #0 = { nounwind }
!0 = !{i32 1}
"""
        assert sup.count_instructions(ir_with_headers) == 2

    def test_algorithmic_synthesizer_bubble_sort_priority_and_amd_epyc_profile(self):
        from agents.algorithmic_synthesizer import AlgorithmicSynthesizer, AlgorithmPattern
        from agents.microarch_tuner import MicroArchitecturalTuner, CPUTarget
        synth = AlgorithmicSynthesizer()
        bubble_ir = """
define void @bubble_sort(ptr %arr, i32 %n) {
entry:
  br label %for.cond
for.cond:
  br label %for.body
for.body:
  %p = getelementptr inbounds i32, ptr %arr, i64 0
  %v = load i32, ptr %p
  %cmp = icmp sgt i32 %v, 0
  store i32 %v, ptr %p
  br label %for.cond
}
"""
        match = synth.detect_pattern(bubble_ir)
        assert match is not None
        assert match.pattern == AlgorithmPattern.BUBBLE_SORT

        tuner = MicroArchitecturalTuner(CPUTarget.AMD_EPYC_GENOA)
        assert tuner.profile.name == "AMD EPYC Genoa"
        assert tuner.profile.vector_width == 512
        assert tuner.profile.supports_avx512 is True

    def test_shared_kb_conflict_deduplication_and_supervisor_certificate(self):
        from agents.shared_knowledge_base import SharedKnowledgeBase, AgentInsight
        from agents.supervisor import CompilerSupervisor
        kb = SharedKnowledgeBase()
        kb.publish_insight(AgentInsight(agent_id="a1", timestamp="now", optimizations_applied=["loop_unroll"]))
        kb.publish_insight(AgentInsight(agent_id="a2", timestamp="now", optimizations_applied=["loop_unroll"]))
        first = kb.detect_conflicts()
        second = kb.detect_conflicts()
        assert len(first) == 1
        assert len(second) == 0
        assert len(kb.conflicts) == 1

        sup = CompilerSupervisor(max_retries=2, use_advanced_agents=True)
        res = sup.supervise_compilation("int main() { return 42; }", "cert_test.c")
        try:
            assert res["success"] is True
            assert "safety-vault" in res["phases_completed"]
            assert res.get("certificate_id") is not None
        finally:
            if res.get("binary_path") and os.path.exists(res["binary_path"]):
                os.unlink(res["binary_path"])

