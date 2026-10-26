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


class TestLLMAgentEfficiencyRules:
    """Tests for LLM token compaction, structural SSA pre-gate, and workspace rule files."""

    def test_compact_ir_for_llm_strips_optnone_and_boilerplate(self):
        from agents.agent_rules import compact_ir_for_llm
        raw_ir = """; ModuleID = 'input.c'
; Function Attrs: noinline nounwind optnone ssp uwtable
define i32 @add(i32 %a, i32 %b) optnone {
entry:


  %r = add nsw i32 %a, %b
  ret i32 %r
}
"""
        compacted = compact_ir_for_llm(raw_ir)
        assert "optnone" not in compacted
        assert "; ModuleID" not in compacted
        assert "; Function Attrs:" not in compacted
        assert "\n\n\n" not in compacted
        assert "define i32 @add(i32 %a, i32 %b)" in compacted

    def test_validate_llm_ir_output_catches_ssa_and_signature_bugs(self):
        from agents.agent_rules import validate_llm_ir_output
        src_ir = """
define i32 @calc(i32 %x) {
entry:
  %a = add i32 %x, 1
  ret i32 %a
}
"""
        # Valid candidate
        ok, msg = validate_llm_ir_output(src_ir, src_ir)
        assert ok is True

        # Duplicate SSA register definition
        dup_ssa_ir = """
define i32 @calc(i32 %x) {
entry:
  %a = add i32 %x, 1
  %a = mul i32 %x, 2
  ret i32 %a
}
"""
        ok_ssa, msg_ssa = validate_llm_ir_output(src_ir, dup_ssa_ir)
        assert ok_ssa is False
        assert "SSA violation" in msg_ssa

        # Return type mismatch
        bad_sig_ir = """
define i64 @calc(i32 %x) {
entry:
  ret i64 0
}
"""
        ok_sig, msg_sig = validate_llm_ir_output(src_ir, bad_sig_ir)
        assert ok_sig is False
        assert "Return type mismatch" in msg_sig

    def test_memory_sentinel_zero_token_fast_path(self):
        from agents.memory_sentinel import _has_memory_or_unsafe_ops, run
        pure_arith = """
define i32 @square(i32 %x) {
entry:
  %r = mul nsw i32 %x, %x
  ret i32 %r
}
"""
        assert _has_memory_or_unsafe_ops(pure_arith) is False
        assert run(pure_arith) == pure_arith

    def test_workspace_agent_rule_files_exist_and_are_compact(self):
        repo_root = Path(__file__).parent.parent
        agents_md = repo_root / "AGENTS.md"
        gemini_md = repo_root / "GEMINI.md"
        llvm_rules = repo_root / ".agents" / "rules" / "llvm-verification-rules.md"
        eff_rules = repo_root / ".agents" / "rules" / "llm-agent-efficiency.md"
        consensus_rules = repo_root / ".agents" / "rules" / "multi-agent-consensus.md"

        assert agents_md.exists()
        assert gemini_md.exists()
        assert llvm_rules.exists()
        assert eff_rules.exists()
        assert consensus_rules.exists()
        # Enforce < 150 lines litmus test on root AGENTS.md
        assert len(agents_md.read_text(encoding="utf-8").splitlines()) < 150

    def test_llvm_intrinsics_and_freeze_symbolic_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence, VerificationVerdict
        orig_ir = """
define i32 @max_val(i32 %a, i32 %b) {
entry:
  %cmp = icmp sgt i32 %a, %b
  %res = select i1 %cmp, i32 %a, i32 %b
  ret i32 %res
}
"""
        opt_ir = """
define i32 @max_val(i32 %a, i32 %b) {
entry:
  %af = freeze i32 %a
  %res = tail call i32 @llvm.smax.i32(i32 %af, i32 %b)
  ret i32 %res
}
"""
        report = verify_ir_equivalence(orig_ir, opt_ir)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_verification_sha256_memoization_cache(self):
        from engine.symbolic_verifier import verify_ir_equivalence, _VERIFICATION_CACHE
        ir1 = "define i32 @id(i32 %x) { entry:\n ret i32 %x\n}"
        ir2 = "define i32 @id(i32 %x) { entry:\n %y = add i32 %x, 0\n ret i32 %y\n}"
        r1 = verify_ir_equivalence(ir1, ir2)
        r2 = verify_ir_equivalence(ir1, ir2)
        assert r1 is r2
        assert len(_VERIFICATION_CACHE) > 0

    def test_workspace_skills_frontmatter_valid(self):
        repo_root = Path(__file__).parent.parent
        skills_dir = repo_root / ".agents" / "skills"
        expected_skills = [
            "llvm-ir-verification",
            "cegar-counterexample-debugging",
            "security-audit-and-cbom",
            "high-velocity-engineering",
            "parallel-agent-council",
        ]
        for skill_name in expected_skills:
            skill_md = skills_dir / skill_name / "SKILL.md"
            assert skill_md.exists(), f"Missing skill {skill_name}"
            text = skill_md.read_text(encoding="utf-8")
            assert text.startswith("---\n")
            assert f"name: {skill_name}" in text
            assert "description:" in text

    def test_parallel_multi_agent_group_deliberation_and_consensus(self):
        from agents.supervisor import CompilerSupervisor
        supervisor = CompilerSupervisor(use_advanced_agents=True)
        c_code = """
        int compute_series(int n) {
            int s = 0;
            for (int i = 0; i < 8; i++) {
                s += i;
            }
            return s + n;
        }
        """
        res = supervisor.supervise_compilation(c_code)
        try:
            assert res["success"] is True
            assert res["final_verdict"] == "PROVED"
            assert "group_deliberation" in res
            delib = res["group_deliberation"]
            assert delib["quality_gate_passed"] is True
            assert delib["messages_exchanged"] >= 5
            assert len(delib["participating_agents"]) >= 4
            assert delib["selected_strategy"] == "PARETO_OPTIMAL_VERIFIED_RELEASE"
            assert "100% Z3 semantic equivalence" in delib["rationale"]
        finally:
            if res.get("binary_path") and os.path.exists(res["binary_path"]):
                os.unlink(res["binary_path"])

    def test_sroa_local_alloca_getelementptr_symbolic_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence, VerificationVerdict
        orig_ir = """
define i32 @pair_sum(i32 %a, i32 %b) {
entry:
  %pair = alloca [2 x i32], align 4
  %p0 = getelementptr inbounds [2 x i32], ptr %pair, i64 0, i64 0
  store i32 %a, ptr %p0, align 4
  %p1 = getelementptr inbounds [2 x i32], ptr %pair, i64 0, i64 1
  store i32 %b, ptr %p1, align 4
  %v0 = load i32, ptr %p0, align 4
  %v1 = load i32, ptr %p1, align 4
  %sum = add i32 %v0, %v1
  ret i32 %sum
}
"""
        opt_ir = """
define i32 @pair_sum(i32 %a, i32 %b) {
entry:
  %sum = add i32 %a, %b
  ret i32 %sum
}
"""
        bad_ir = """
define i32 @pair_sum(i32 %a, i32 %b) {
entry:
  %sum = sub i32 %a, %b
  ret i32 %sum
}
"""
        r_ok = verify_ir_equivalence(orig_ir, opt_ir)
        assert r_ok.verdict == VerificationVerdict.PROVED
        assert r_ok.proved is True

        r_bad = verify_ir_equivalence(orig_ir, bad_ir)
        assert r_bad.verdict == VerificationVerdict.FAILED
        assert r_bad.proved is False

    def test_bitwise_intrinsics_bswap_ctpop_fshl_symbolic_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence, VerificationVerdict
        orig_rotl = """
define i32 @rotl8(i32 %x) {
entry:
  %shl = shl i32 %x, 8
  %shr = lshr i32 %x, 24
  %res = or i32 %shl, %shr
  ret i32 %res
}
"""
        opt_fshl = """
define i32 @rotl8(i32 %x) {
entry:
  %res = tail call i32 @llvm.fshl.i32(i32 %x, i32 %x, i32 8)
  ret i32 %res
}
"""
        r_rot = verify_ir_equivalence(orig_rotl, opt_fshl)
        assert r_rot.verdict == VerificationVerdict.PROVED

        orig_bswap16 = """
define i16 @swap16(i16 %x) {
entry:
  %hi = lshr i16 %x, 8
  %lo = shl i16 %x, 8
  %res = or i16 %hi, %lo
  ret i16 %res
}
"""
        opt_bswap16 = """
define i16 @swap16(i16 %x) {
entry:
  %res = call i16 @llvm.bswap.i16(i16 %x)
  ret i16 %res
}
"""
        r_bswap = verify_ir_equivalence(orig_bswap16, opt_bswap16)
        assert r_bswap.verdict == VerificationVerdict.PROVED

    def test_cwe_vulnerability_scanner_detects_uaf_double_free_and_format_string(self):
        from server.mcp_server import compile_to_ir, apply_memory_safety
        repo_root = Path(__file__).parent.parent
        c_src = (repo_root / "demo_corpus" / "unsafe" / "buffer_overflow.c").read_text(encoding="utf-8")
        comp = compile_to_ir(c_src, "buffer_overflow.c")
        assert comp["success"] is True
        safety = apply_memory_safety(comp["ir"], use_ai=False, verbose=False)
        assert safety["checks_added"] >= 8
        findings_blob = "\n".join(safety["check_locations"])
        for cwe_tag in ("CWE-120", "CWE-134", "CWE-190", "CWE-415", "CWE-416", "CWE-674", "CWE-125/787"):
            assert cwe_tag in findings_blob, f"Expected {cwe_tag} in findings"

    def test_whole_corpus_benchmark_all_9_files_proved(self):
        from engine.corpus_benchmark import run_corpus_benchmark
        repo_root = Path(__file__).parent.parent
        res = run_corpus_benchmark(repo_root / "demo_corpus")
        assert res["files_benchmarked"] == 9
        assert res["proved_files"] == 9
        assert res["all_proved"] is True
        assert res["overall_reduction_pct"] > 25.0
        assert res["total_cwe_guards"] >= 40

    def test_switch_and_multi_predecessor_phi_symbolic_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence, VerificationVerdict
        switch_ir = """
define i32 @dispatch(i32 %x) {
entry:
  switch i32 %x, label %sw.default [
    i32 0, label %sw.bb0
    i32 1, label %sw.bb1
  ]
sw.bb0:
  br label %sw.epilog
sw.bb1:
  br label %sw.epilog
sw.default:
  br label %sw.epilog
sw.epilog:
  %res = phi i32 [ 10, %sw.bb0 ], [ 20, %sw.bb1 ], [ 99, %sw.default ]
  ret i32 %res
}
"""
        select_ir = """
define i32 @dispatch(i32 %x) {
entry:
  %c1 = icmp eq i32 %x, 1
  %s1 = select i1 %c1, i32 20, i32 99
  %c0 = icmp eq i32 %x, 0
  %res = select i1 %c0, i32 10, i32 %s1
  ret i32 %res
}
"""
        report = verify_ir_equivalence(switch_ir, select_ir)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_sarif_2_1_0_security_report_export(self, tmp_path):
        from server.mcp_server import export_sarif_report
        records = [
            {
                "file": "demo_corpus/unsafe/buffer_overflow.c",
                "checks_injected": 2,
                "status": "hardened",
                "findings": [
                    "CWE-120: Unsafe C library call (@strcpy): destination buffer bounds guard required",
                    "CWE-416: Use-after-free pointer dereference after @free in @use_after_free_demo",
                ],
            }
        ]
        sarif_file = tmp_path / "audit.sarif"
        payload = export_sarif_report(records, str(sarif_file))
        assert sarif_file.exists()
        assert payload["version"] == "2.1.0"
        assert len(payload["runs"][0]["results"]) == 2
        rule_ids = {r["ruleId"] for r in payload["runs"][0]["results"]}
        assert "CWE-120" in rule_ids
        assert "CWE-416" in rule_ids

    def test_overflow_checked_intrinsics_and_extractvalue_symbolic_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence, VerificationVerdict
        checked_add_ir = """
define i32 @checked_uadd_clamp(i32 %a, i32 %b) {
entry:
  %pair = call { i32, i1 } @llvm.uadd.with.overflow.i32(i32 %a, i32 %b)
  %sum = extractvalue { i32, i1 } %pair, 0
  %ovf = extractvalue { i32, i1 } %pair, 1
  %res = select i1 %ovf, i32 -1, i32 %sum
  ret i32 %res
}
"""
        manual_uadd_clamp_ir = """
define i32 @checked_uadd_clamp(i32 %a, i32 %b) {
entry:
  %sum = add i32 %a, %b
  %ovf = icmp ult i32 %sum, %a
  %res = select i1 %ovf, i32 -1, i32 %sum
  ret i32 %res
}
"""
        broken_uadd_ir = """
define i32 @checked_uadd_clamp(i32 %a, i32 %b) {
entry:
  %sum = add i32 %a, %b
  ret i32 %sum
}
"""
        r_ok = verify_ir_equivalence(checked_add_ir, manual_uadd_clamp_ir)
        assert r_ok.verdict == VerificationVerdict.PROVED
        assert r_ok.proved is True

        r_bad = verify_ir_equivalence(checked_add_ir, broken_uadd_ir)
        assert r_bad.verdict == VerificationVerdict.FAILED
        assert r_bad.proved is False

    def test_cegar_supervisor_clang_optimization_fallback(self):
        from agents.cegar_supervisor import CEGARSupervisor
        unopt_ir = """
define i32 @square_val(i32 %x) optnone noinline {
entry:
  %slot = alloca i32, align 4
  store i32 %x, ptr %slot, align 4
  %v1 = load i32, ptr %slot, align 4
  %v2 = load i32, ptr %slot, align 4
  %prod = mul nsw i32 %v1, %v2
  ret i32 %prod
}
"""
        sup = CEGARSupervisor(max_iterations=2)
        opt_ir = sup._apply_optimization(unopt_ir, "performance")
        assert "alloca i32" not in opt_ir
        assert "mul nsw i32" in opt_ir

    def test_treefinement_supervisor_clang_fallback_and_microarch_simd_detection(self):
        from agents.treefinement_supervisor import TreefinementSupervisor
        from agents.microarch_tuner import MicroArchitecturalTuner, CPUTarget

        unopt_ir = """
define i32 @double_it(i32 %x) optnone noinline {
entry:
  %slot = alloca i32, align 4
  store i32 %x, ptr %slot, align 4
  %v = load i32, ptr %slot, align 4
  %res = add nsw i32 %v, %v
  ret i32 %res
}
"""
        tree_sup = TreefinementSupervisor(max_depth=2, branch_factor=3)
        opt_ir = tree_sup._run_opt_pass(unopt_ir, "loop-unroll,slp-vectorizer")
        assert "alloca i32" not in opt_ir

        simd_ir = """
define <4 x i32> @vec_add(<4 x i32> %a, <4 x i32> %b) {
entry:
  %res = add <4 x i32> %a, %b
  ret <4 x i32> %res
}
"""
        tuner = MicroArchitecturalTuner(CPUTarget.APPLE_M4)
        sim = tuner.simulate_on_hardware(simd_ir)
        assert sim.vector_utilization > 0.0

    def test_safety_vault_handles_serialized_dict_reasoning_logs(self):
        from agents.safety_vault import SafetyVault

        vault = SafetyVault()
        cert = vault.generate_certificate(
            project_name="ecstasy_test",
            source_code="int f(int x) { return x + 1; }",
            ir_code="define i32 @f(i32 %x) { %r = add nsw i32 %x, 1 ret i32 %r }",
            binary_path=None,
            z3_verdict="PROVED",
            reasoning_logs=[
                {"iteration": 1, "verdict": "FAILED"},
                {"iteration": 2, "verdict": "PROVED"},
            ],
        )
        summary = cert.proof_chain["reasoning_summary"]
        assert summary[0]["iteration"] == 1
        assert summary[0]["verdict"] == "FAILED"
        assert summary[1]["iteration"] == 2
        assert summary[1]["verdict"] == "PROVED"

    def test_provider_agnostic_llm_client_and_zero_ibm_dependencies(self):
        from agents.llm_client import UniversalLLMClient

        repo_root = Path(__file__).parent.parent
        req_txt = (repo_root / "requirements.txt").read_text(encoding="utf-8")
        pyproject_txt = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
        env_example_txt = (repo_root / ".env.example").read_text(encoding="utf-8")

        assert "ibm-watsonx-ai" not in req_txt
        assert "ibm-watsonx-ai" not in pyproject_txt
        assert "WATSONX" not in env_example_txt
        assert "LLM_API_KEY" in env_example_txt

        client = UniversalLLMClient(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model_id="gpt-4o-mini",
        )
        assert client.api_key == "test-key"
        assert client.base_url == "https://api.openai.com/v1"
        assert client.model_id == "gpt-4o-mini"

    def test_saturating_arithmetic_and_bitreverse_intrinsics_symbolic_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. Unsigned saturating addition: @llvm.uadd.sat.i32(a, b) == (a + b < a) ? -1 : (a + b)
        src_uadd_sat = """
        define i32 @uadd_sat_fn(i32 %a, i32 %b) {
        entry:
          %sum = add i32 %a, %b
          %ovf = icmp ult i32 %sum, %a
          %res = select i1 %ovf, i32 -1, i32 %sum
          ret i32 %res
        }
        """
        tgt_uadd_sat = """
        declare i32 @llvm.uadd.sat.i32(i32, i32)
        define i32 @uadd_sat_fn(i32 %a, i32 %b) {
        entry:
          %res = call i32 @llvm.uadd.sat.i32(i32 %a, i32 %b)
          ret i32 %res
        }
        """
        res_uadd = verify_ir_equivalence(src_uadd_sat, tgt_uadd_sat)
        assert res_uadd.verdict == "PROVED"
        assert res_uadd.proved is True

        # 2. Unsigned saturating subtraction: @llvm.usub.sat.i32(a, b) == (a < b) ? 0 : (a - b)
        src_usub_sat = """
        define i32 @usub_sat_fn(i32 %a, i32 %b) {
        entry:
          %udf = icmp ult i32 %a, %b
          %diff = sub i32 %a, %b
          %res = select i1 %udf, i32 0, i32 %diff
          ret i32 %res
        }
        """
        tgt_usub_sat = """
        declare i32 @llvm.usub.sat.i32(i32, i32)
        define i32 @usub_sat_fn(i32 %a, i32 %b) {
        entry:
          %res = call i32 @llvm.usub.sat.i32(i32 %a, i32 %b)
          ret i32 %res
        }
        """
        res_usub = verify_ir_equivalence(src_usub_sat, tgt_usub_sat)
        assert res_usub.verdict == "PROVED"
        assert res_usub.proved is True

        # 3. Involution of bitreverse: bitreverse(bitreverse(x)) == x
        src_bitrev = """
        define i32 @id_bitrev(i32 %x) {
        entry:
          ret i32 %x
        }
        """
        tgt_bitrev = """
        declare i32 @llvm.bitreverse.i32(i32)
        define i32 @id_bitrev(i32 %x) {
        entry:
          %r1 = call i32 @llvm.bitreverse.i32(i32 %x)
          %r2 = call i32 @llvm.bitreverse.i32(i32 %r1)
          ret i32 %r2
        }
        """
        res_bitrev = verify_ir_equivalence(src_bitrev, tgt_bitrev)
        assert res_bitrev.verdict == "PROVED"
        assert res_bitrev.proved is True

    def test_fastmcp_server_tools_and_manifest(self):
        from server.mcp_server import (
            get_mcp_tools_manifest,
            mcp_audit_memory_safety,
            mcp_compile_to_ir,
            mcp_optimize_ir,
            mcp_verify_ir_equivalence,
        )

        manifest = get_mcp_tools_manifest()
        assert len(manifest) == 14
        names = {t["name"] for t in manifest}
        assert "mcp_compile_to_ir" in names
        assert "mcp_verify_ir_equivalence" in names
        assert "mcp_audit_memory_safety" in names
        assert "mcp_prove_vulnerability" in names
        assert "mcp_verify_constant_time" in names
        assert "mcp_harden_security" in names
        assert "mcp_export_cbom" in names
        assert "mcp_verify_exploit_poc" in names
        assert "mcp_synthesize_constant_time" in names
        assert "mcp_analyze_attack_surface" in names
        assert "mcp_enforce_cfi" in names

        c_src = "int double_val(int x) { return x + x; }\n"
        comp = mcp_compile_to_ir(c_src)
        assert comp["success"] is True
        opt = mcp_optimize_ir(comp["ir"], use_ai=False)
        assert opt["success"] is True
        ver = mcp_verify_ir_equivalence(comp["ir"], opt["optimized_ir"])
        assert ver["verdict"] == "PROVED"
        audit = mcp_audit_memory_safety(comp["ir"], include_sarif=True)
        assert "sarif" in audit
        assert audit["sarif"]["version"] == "2.1.0"

    def test_llvm19_flags_and_insertvalue_aggregate_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. LLVM 19/21 flags: or disjoint, zext nneg, icmp samesign
        src_flags = """
        define i64 @bit_pack(i32 %x) {
        entry:
          %masked = and i32 %x, 255
          %cmp = icmp ult i32 %masked, 128
          %sel = select i1 %cmp, i32 %masked, i32 0
          %or_val = add i32 %sel, 256
          %ext = zext i32 %or_val to i64
          ret i64 %ext
        }
        """
        tgt_flags = """
        define i64 @bit_pack(i32 %x) {
        entry:
          %masked = and i32 %x, 255
          %cmp = icmp samesign ult i32 %masked, 128
          %sel = select i1 %cmp, i32 %masked, i32 0
          %or_val = or disjoint i32 %sel, 256
          %ext = zext nneg i32 %or_val to i64
          ret i64 %ext
        }
        """
        res_flags = verify_ir_equivalence(src_flags, tgt_flags)
        assert res_flags.verdict == "PROVED"
        assert res_flags.proved is True

        # 2. Aggregate insertvalue + extractvalue equivalence
        src_agg = """
        define i32 @pair_sum(i32 %a, i32 %b) {
        entry:
          %s = add i32 %a, %b
          ret i32 %s
        }
        """
        tgt_agg = """
        define i32 @pair_sum(i32 %a, i32 %b) {
        entry:
          %p0 = insertvalue { i32, i32 } poison, i32 %a, 0
          %p1 = insertvalue { i32, i32 } %p0, i32 %b, 1
          %x = extractvalue { i32, i32 } %p1, 0
          %y = extractvalue { i32, i32 } %p1, 1
          %s = add i32 %x, %y
          ret i32 %s
        }
        """
        res_agg = verify_ir_equivalence(src_agg, tgt_agg)
        assert res_agg.verdict == "PROVED"
        assert res_agg.proved is True

    def test_zero_legacy_vendor_markers_in_source(self):
        repo_root = Path(__file__).parent.parent
        for subdir in ("agents", "engine", "server", "frontend", "demo"):
            for path in (repo_root / subdir).rglob("*.py"):
                txt = path.read_text(encoding="utf-8")
                assert "WATSONX_APIKEY" not in txt, f"Found WATSONX_APIKEY in {path}"
                assert "Made with Bob" not in txt, f"Found Made with Bob in {path}"

    def test_simd_vector_lane_parallel_and_reduction_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. Scalar 4-way sum vs. SIMD <4 x i32> insertelement + @llvm.vector.reduce.add.v4i32
        src_scalar_sum = """
        define i32 @sum4(i32 %a, i32 %b, i32 %c, i32 %d) {
        entry:
          %s0 = add i32 %a, %b
          %s1 = add i32 %s0, %c
          %s2 = add i32 %s1, %d
          ret i32 %s2
        }
        """
        tgt_simd_sum = """
        declare i32 @llvm.vector.reduce.add.v4i32(<4 x i32>)
        define i32 @sum4(i32 %a, i32 %b, i32 %c, i32 %d) {
        entry:
          %v0 = insertelement <4 x i32> poison, i32 %a, i64 0
          %v1 = insertelement <4 x i32> %v0, i32 %b, i64 1
          %v2 = insertelement <4 x i32> %v1, i32 %c, i64 2
          %v3 = insertelement <4 x i32> %v2, i32 %d, i64 3
          %res = call i32 @llvm.vector.reduce.add.v4i32(<4 x i32> %v3)
          ret i32 %res
        }
        """
        res_sum = verify_ir_equivalence(src_scalar_sum, tgt_simd_sum)
        assert res_sum.verdict == "PROVED"
        assert res_sum.proved is True

        # 2. Lane-parallel vector add + shufflevector + extractelement equivalence
        src_vec_op = """
        define i32 @dot_like(<2 x i32> %x, <2 x i32> %y) {
        entry:
          %sum = add <2 x i32> %x, %y
          %swapped = shufflevector <2 x i32> %sum, <2 x i32> poison, <2 x i32> <i32 1, i32 0>
          %e0 = extractelement <2 x i32> %swapped, i64 0
          %e1 = extractelement <2 x i32> %swapped, i64 1
          %tot = add i32 %e0, %e1
          ret i32 %tot
        }
        """
        tgt_vec_op = """
        declare i32 @llvm.vector.reduce.add.v2i32(<2 x i32>)
        define i32 @dot_like(<2 x i32> %x, <2 x i32> %y) {
        entry:
          %rx = call i32 @llvm.vector.reduce.add.v2i32(<2 x i32> %x)
          %ry = call i32 @llvm.vector.reduce.add.v2i32(<2 x i32> %y)
          %tot = add i32 %rx, %ry
          ret i32 %tot
        }
        """
        res_vec = verify_ir_equivalence(src_vec_op, tgt_vec_op)
        assert res_vec.verdict == "PROVED"
        assert res_vec.proved is True

    def test_bounded_loop_unrolling_symbolic_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. SSA phi constant-trip loop (sum_{i=0..3} i * x = 6 * x) vs closed-form mul
        src_phi_loop = """
        define i32 @weighted_sum(i32 %x) {
        entry:
          br label %for.cond
        for.cond:
          %i = phi i32 [ 0, %entry ], [ %i.next, %for.body ]
          %acc = phi i32 [ 0, %entry ], [ %acc.next, %for.body ]
          %cmp = icmp slt i32 %i, 4
          br i1 %cmp, label %for.body, label %for.end
        for.body:
          %term = mul i32 %x, %i
          %acc.next = add i32 %acc, %term
          %i.next = add i32 %i, 1
          br label %for.cond
        for.end:
          ret i32 %acc
        }
        """
        tgt_closed = """
        define i32 @weighted_sum(i32 %x) {
        entry:
          %res = mul i32 %x, 6
          ret i32 %res
        }
        """
        res_phi = verify_ir_equivalence(src_phi_loop, tgt_closed)
        assert res_phi.verdict == "PROVED"
        assert res_phi.proved is True

        # 2. -O0 alloca/store/load constant-trip loop (4 iterations of acc += x) vs shl %x, 2
        src_o0_loop = """
        define i32 @quad_o0(i32 %x) {
        entry:
          %i = alloca i32, align 4
          %acc = alloca i32, align 4
          store i32 0, ptr %i, align 4
          store i32 0, ptr %acc, align 4
          br label %for.cond
        for.cond:
          %0 = load i32, ptr %i, align 4
          %cmp = icmp slt i32 %0, 4
          br i1 %cmp, label %for.body, label %for.end
        for.body:
          %1 = load i32, ptr %acc, align 4
          %add = add i32 %1, %x
          store i32 %add, ptr %acc, align 4
          %2 = load i32, ptr %i, align 4
          %inc = add i32 %2, 1
          store i32 %inc, ptr %i, align 4
          br label %for.cond
        for.end:
          %3 = load i32, ptr %acc, align 4
          ret i32 %3
        }
        """
        tgt_shl = """
        define i32 @quad_o0(i32 %x) {
        entry:
          %res = shl i32 %x, 2
          ret i32 %res
        }
        """
        res_o0 = verify_ir_equivalence(src_o0_loop, tgt_shl)
        assert res_o0.verdict == "PROVED"
        assert res_o0.proved is True

    def test_interprocedural_call_inlining_and_ipcp_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        src_ipcp = """
        define i32 @affine_scale(i32 %v, i32 %factor, i32 %bias) {
        entry:
          %prod = mul i32 %v, %factor
          %sum = add i32 %prod, %bias
          ret i32 %sum
        }
        define i32 @compute_entry(i32 %x) {
        entry:
          %r = call i32 @affine_scale(i32 %x, i32 5, i32 7)
          ret i32 %r
        }
        """
        tgt_inlined = """
        define i32 @compute_entry(i32 %x) {
        entry:
          %prod = mul i32 %x, 5
          %sum = add i32 %prod, 7
          ret i32 %sum
        }
        """
        res_ok = verify_ir_equivalence(src_ipcp, tgt_inlined)
        assert res_ok.verdict == "PROVED"
        assert res_ok.proved is True

        tgt_buggy = """
        define i32 @compute_entry(i32 %x) {
        entry:
          %prod = mul i32 %x, 5
          %sum = add i32 %prod, 8
          ret i32 %sum
        }
        """
        res_bug = verify_ir_equivalence(src_ipcp, tgt_buggy)
        assert res_bug.verdict == "FAILED"
        assert res_bug.proved is False
        assert res_bug.counterexample is not None

    def test_qf_abv_symbolic_array_dynamic_gep_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. Dynamic store-to-load forwarding with non-aliasing store at idx + 1 -> PROVED
        src_non_alias = """
        define i32 @dyn_array_forward(i64 %idx, i32 %val) {
        entry:
          %arr = alloca [16 x i32], align 16
          %p_i = getelementptr inbounds [16 x i32], ptr %arr, i64 0, i64 %idx
          store i32 %val, ptr %p_i, align 4
          %next = add i64 %idx, 1
          %p_next = getelementptr inbounds [16 x i32], ptr %arr, i64 0, i64 %next
          store i32 99, ptr %p_next, align 4
          %loaded = load i32, ptr %p_i, align 4
          ret i32 %loaded
        }
        """
        tgt_forwarded = """
        define i32 @dyn_array_forward(i64 %idx, i32 %val) {
        entry:
          ret i32 %val
        }
        """
        res_ok = verify_ir_equivalence(src_non_alias, tgt_forwarded)
        assert res_ok.verdict == "PROVED"
        assert res_ok.proved is True

        # 2. Potentially aliasing symbolic indices %i and %j where %i == %j overwrites %a with %b -> FAILED
        src_alias = """
        define i32 @may_alias(i64 %i, i64 %j, i32 %a, i32 %b) {
        entry:
          %arr = alloca [16 x i32], align 16
          %pi = getelementptr inbounds [16 x i32], ptr %arr, i64 0, i64 %i
          store i32 %a, ptr %pi, align 4
          %pj = getelementptr inbounds [16 x i32], ptr %arr, i64 0, i64 %j
          store i32 %b, ptr %pj, align 4
          %v = load i32, ptr %pi, align 4
          ret i32 %v
        }
        """
        tgt_bad_forward = """
        define i32 @may_alias(i64 %i, i64 %j, i32 %a, i32 %b) {
        entry:
          ret i32 %a
        }
        """
        res_alias = verify_ir_equivalence(src_alias, tgt_bad_forward)
        assert res_alias.verdict == "FAILED"
        assert res_alias.proved is False
        assert res_alias.counterexample is not None

    def test_simd_vector_predication_casts_and_intrinsics_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. Predicated vector icmp sgt + select <4 x i1> vs @llvm.smax.v4i32 -> PROVED
        src_pred_max = """
        define <4 x i32> @vec_max(<4 x i32> %a, <4 x i32> %b) {
        entry:
          %cmp = icmp sgt <4 x i32> %a, %b
          %res = select <4 x i1> %cmp, <4 x i32> %a, <4 x i32> %b
          ret <4 x i32> %res
        }
        """
        tgt_smax_intr = """
        define <4 x i32> @vec_max(<4 x i32> %a, <4 x i32> %b) {
        entry:
          %res = call <4 x i32> @llvm.smax.v4i32(<4 x i32> %a, <4 x i32> %b)
          ret <4 x i32> %res
        }
        """
        res_ok = verify_ir_equivalence(src_pred_max, tgt_smax_intr)
        assert res_ok.verdict == "PROVED"
        assert res_ok.proved is True

        # 2. Vector mask sext <4 x i1> to <4 x i32> bitwise blend vs predicated select -> PROVED
        src_mask_blend = """
        define <4 x i32> @vec_relu(<4 x i32> %x) {
        entry:
          %pos = icmp sgt <4 x i32> %x, zeroinitializer
          %mask = sext <4 x i1> %pos to <4 x i32>
          %res = and <4 x i32> %x, %mask
          ret <4 x i32> %res
        }
        """
        tgt_select_relu = """
        define <4 x i32> @vec_relu(<4 x i32> %x) {
        entry:
          %pos = icmp sgt <4 x i32> %x, zeroinitializer
          %res = select <4 x i1> %pos, <4 x i32> %x, <4 x i32> <i32 0, i32 0, i32 0, i32 0>
          ret <4 x i32> %res
        }
        """
        res_relu = verify_ir_equivalence(src_mask_blend, tgt_select_relu)
        assert res_relu.verdict == "PROVED"
        assert res_relu.proved is True

        # 3. Inverted predicate bug (icmp slt vs @llvm.smax.v4i32) -> FAILED
        src_buggy_pred = """
        define <4 x i32> @vec_max(<4 x i32> %a, <4 x i32> %b) {
        entry:
          %cmp = icmp slt <4 x i32> %a, %b
          %res = select <4 x i1> %cmp, <4 x i32> %a, <4 x i32> %b
          ret <4 x i32> %res
        }
        """
        res_bug = verify_ir_equivalence(src_buggy_pred, tgt_smax_intr)
        assert res_bug.verdict == "FAILED"
        assert res_bug.proved is False
        assert res_bug.counterexample is not None

    def test_ieee754_qf_fp_floating_point_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. Double fneg elimination holds for all IEEE-754 floats (including -0.0 and NaN) -> PROVED
        src_dneg = """
        define float @fp_dneg(float %x) {
        entry:
          %n1 = fneg float %x
          %n2 = fneg float %n1
          ret float %n2
        }
        """
        tgt_id = """
        define float @fp_dneg(float %x) {
        entry:
          ret float %x
        }
        """
        res_dneg = verify_ir_equivalence(src_dneg, tgt_id)
        assert res_dneg.verdict == "PROVED"
        assert res_dneg.proved is True

        # 2. fadd float %x, 0.0 -> %x WITHOUT nsz fails on IEEE-754 signed zero (-0.0) -> FAILED
        src_add_zero = """
        define float @fp_add_zero(float %x) {
        entry:
          %r = fadd float %x, 0.0
          ret float %r
        }
        """
        tgt_add_zero = """
        define float @fp_add_zero(float %x) {
        entry:
          ret float %x
        }
        """
        res_signed_zero = verify_ir_equivalence(src_add_zero, tgt_add_zero)
        assert res_signed_zero.verdict == "FAILED"
        assert res_signed_zero.proved is False
        assert res_signed_zero.counterexample is not None

        # 3. fadd nsz nnan float %x, 0.0 -> %x WITH nsz + nnan fast-math flags -> PROVED
        src_nsz = """
        define float @fp_add_zero_nsz(float %x) {
        entry:
          %r = fadd nsz nnan float %x, 0.0
          ret float %r
        }
        """
        tgt_nsz = """
        define float @fp_add_zero_nsz(float %x) {
        entry:
          ret float %x
        }
        """
        res_nsz = verify_ir_equivalence(src_nsz, tgt_nsz)
        assert res_nsz.verdict == "PROVED"
        assert res_nsz.proved is True

        # 4. @llvm.fabs.f32 and fcmp olt/oge/ord equivalence -> PROVED
        src_fabs = """
        define float @abs_mag(float %x) {
        entry:
          %a = call float @llvm.fabs.f32(float %x)
          %b = call float @llvm.fabs.f32(float %a)
          ret float %b
        }
        """
        tgt_fabs = """
        define float @abs_mag(float %x) {
        entry:
          %a = call float @llvm.fabs.f32(float %x)
          ret float %a
        }
        """
        res_fabs = verify_ir_equivalence(src_fabs, tgt_fabs)
        assert res_fabs.verdict == "PROVED"
        assert res_fabs.proved is True

    def test_void_function_and_pointer_parameter_post_state_verification(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. -O0 alloca-indirect pointer swap vs -O2 direct pointer swap -> PROVED
        src_o0_swap = """
        define void @swap_i32(ptr %a, ptr %b) {
        entry:
          %a.addr = alloca ptr, align 8
          %b.addr = alloca ptr, align 8
          %tmp = alloca i32, align 4
          store ptr %a, ptr %a.addr, align 8
          store ptr %b, ptr %b.addr, align 8
          %0 = load ptr, ptr %a.addr, align 8
          %1 = load i32, ptr %0, align 4
          store i32 %1, ptr %tmp, align 4
          %2 = load ptr, ptr %b.addr, align 8
          %3 = load i32, ptr %2, align 4
          %4 = load ptr, ptr %a.addr, align 8
          store i32 %3, ptr %4, align 4
          %5 = load i32, ptr %tmp, align 4
          %6 = load ptr, ptr %b.addr, align 8
          store i32 %5, ptr %6, align 4
          ret void
        }
        """
        tgt_o2_swap = """
        define void @swap_i32(ptr %a, ptr %b) {
        entry:
          %0 = load i32, ptr %a, align 4
          %1 = load i32, ptr %b, align 4
          store i32 %1, ptr %a, align 4
          store i32 %0, ptr %b, align 4
          ret void
        }
        """
        res_swap = verify_ir_equivalence(src_o0_swap, tgt_o2_swap)
        assert res_swap.verdict == "PROVED"
        assert res_swap.proved is True

        # 2. Direct swap vs branchless XOR swap -> PROVED
        tgt_xor_swap = """
        define void @swap_i32(ptr %a, ptr %b) {
        entry:
          %va = load i32, ptr %a, align 4
          %vb = load i32, ptr %b, align 4
          %x1 = xor i32 %va, %vb
          %new_b = xor i32 %x1, %vb
          %new_a = xor i32 %x1, %new_b
          store i32 %new_a, ptr %a, align 4
          store i32 %new_b, ptr %b, align 4
          ret void
        }
        """
        res_xor = verify_ir_equivalence(tgt_o2_swap, tgt_xor_swap)
        assert res_xor.verdict == "PROVED"
        assert res_xor.proved is True

        # 3. Buggy swap that overwrites *b with *a instead of swapping -> FAILED
        tgt_buggy_swap = """
        define void @swap_i32(ptr %a, ptr %b) {
        entry:
          %0 = load i32, ptr %a, align 4
          %1 = load i32, ptr %b, align 4
          store i32 %1, ptr %a, align 4
          store i32 %1, ptr %b, align 4
          ret void
        }
        """
        res_bug = verify_ir_equivalence(src_o0_swap, tgt_buggy_swap)
        assert res_bug.verdict == "FAILED"
        assert res_bug.proved is False
        assert res_bug.counterexample is not None

    def test_interprocedural_pointer_mutation_inlining(self):
        from engine.symbolic_verifier import verify_ir_equivalence

        # 1. Caller stack alloca + call void @swap_i32(ptr %x, ptr %y) vs direct SSA subtract
        src_caller_swap = """
        define void @swap_i32(ptr %a, ptr %b) {
        entry:
          %0 = load i32, ptr %a, align 4
          %1 = load i32, ptr %b, align 4
          store i32 %1, ptr %a, align 4
          store i32 %0, ptr %b, align 4
          ret void
        }

        define i32 @test_caller(i32 %a, i32 %b) {
        entry:
          %x = alloca i32, align 4
          %y = alloca i32, align 4
          store i32 %a, ptr %x, align 4
          store i32 %b, ptr %y, align 4
          call void @swap_i32(ptr %x, ptr %y)
          %rx = load i32, ptr %x, align 4
          %ry = load i32, ptr %y, align 4
          %diff = sub i32 %rx, %ry
          ret i32 %diff
        }
        """

        tgt_caller_swap = """
        define void @swap_i32(ptr %a, ptr %b) {
        entry:
          %0 = load i32, ptr %a, align 4
          %1 = load i32, ptr %b, align 4
          store i32 %1, ptr %a, align 4
          store i32 %0, ptr %b, align 4
          ret void
        }

        define i32 @test_caller(i32 %a, i32 %b) {
        entry:
          %diff = sub i32 %b, %a
          ret i32 %diff
        }
        """
        res_proved = verify_ir_equivalence(src_caller_swap, tgt_caller_swap)
        assert res_proved.verdict == "PROVED"
        assert res_proved.proved is True

        # 2. Buggy caller expecting sub %a, %b instead of sub %b, %a -> FAILED
        tgt_buggy_caller = """
        define void @swap_i32(ptr %a, ptr %b) {
        entry:
          %0 = load i32, ptr %a, align 4
          %1 = load i32, ptr %b, align 4
          store i32 %1, ptr %a, align 4
          store i32 %0, ptr %b, align 4
          ret void
        }

        define i32 @test_caller(i32 %a, i32 %b) {
        entry:
          %diff = sub i32 %a, %b
          ret i32 %diff
        }
        """
        res_failed = verify_ir_equivalence(src_caller_swap, tgt_buggy_caller)
        assert res_failed.verdict == "FAILED"
        assert res_failed.proved is False
        assert res_failed.counterexample is not None

    def test_smt_prover_divide_by_zero_exploit_synthesis(self):
        from engine.smt_vulnerability_prover import audit_ir_security, VulnerabilityVerdict

        # 1. Unbounded symbolic divisor -> EXPLOITABLE with synthesized exploit payload (b == 0)
        vuln_ir = """
        define i32 @vuln_divide(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        dossier = audit_ir_security(vuln_ir)
        assert dossier.is_deployable is False
        assert len(dossier.vulnerabilities_found) == 1
        vuln = dossier.vulnerabilities_found[0]
        assert vuln.cwe_id == "CWE-369"
        assert vuln.verdict == VulnerabilityVerdict.EXPLOITABLE
        assert vuln.exploit_payload is not None
        assert "%b" in vuln.exploit_payload
        assert vuln.exploit_payload["%b"] == 0

        # 2. Constant non-zero divisor -> PROVABLY_SAFE
        safe_ir = """
        define i32 @safe_divide(i32 %a) {
        entry:
          %res = sdiv i32 %a, 10
          ret i32 %res
        }
        """
        dossier_safe = audit_ir_security(safe_ir)
        assert dossier_safe.is_deployable is True
        assert len(dossier_safe.vulnerabilities_found) == 0
        assert len(dossier_safe.safety_proofs) == 1
        assert dossier_safe.safety_proofs[0].verdict == VulnerabilityVerdict.PROVABLY_SAFE

    def test_smt_prover_buffer_out_of_bounds_exploit_synthesis(self):
        from engine.smt_vulnerability_prover import audit_ir_security, VulnerabilityVerdict

        # 1. Symbolic array index with buffer capacity 10 -> EXPLOITABLE
        oob_ir = """
        define i32 @vuln_array_access(i32 %idx) {
        entry:
          %buf = alloca [10 x i32], align 4
          %ptr = getelementptr inbounds [10 x i32], ptr %buf, i64 0, i32 %idx
          %val = load i32, ptr %ptr, align 4
          ret i32 %val
        }
        """
        dossier = audit_ir_security(oob_ir)
        assert dossier.is_deployable is False
        assert len(dossier.vulnerabilities_found) == 1
        vuln = dossier.vulnerabilities_found[0]
        assert vuln.cwe_id == "CWE-125/787"
        assert vuln.verdict == VulnerabilityVerdict.EXPLOITABLE
        assert vuln.exploit_payload is not None
        assert "%idx" in vuln.exploit_payload
        oob_idx = vuln.exploit_payload["%idx"]
        assert oob_idx < 0 or oob_idx >= 10

        # 2. Statically in-bounds index 4 -> PROVABLY_SAFE
        inbounds_ir = """
        define i32 @safe_array_access() {
        entry:
          %buf = alloca [10 x i32], align 4
          %ptr = getelementptr inbounds [10 x i32], ptr %buf, i64 0, i64 4
          %val = load i32, ptr %ptr, align 4
          ret i32 %val
        }
        """
        dossier_inbounds = audit_ir_security(inbounds_ir)
        assert dossier_inbounds.is_deployable is True
        assert len(dossier_inbounds.vulnerabilities_found) == 0
        assert len(dossier_inbounds.safety_proofs) == 1
        assert dossier_inbounds.safety_proofs[0].verdict == VulnerabilityVerdict.PROVABLY_SAFE

    def test_crypto_timing_side_channel_verification(self):
        from engine.crypto_timing_verifier import verify_crypto_constant_time, TimingVerdict

        # 1. Non-constant-time crypto kernel: secret influences branch condition (CWE-208)
        leaky_branch_ir = """
        define i32 @compare_mac(i32 %key, i32 %input) {
        entry:
          %match = icmp eq i32 %key, %input
          br i1 %match, label %then, label %else
        then:
          ret i32 1
        else:
          ret i32 0
        }
        """
        report_branch = verify_crypto_constant_time(leaky_branch_ir)
        assert report_branch.is_constant_time is False
        assert report_branch.verdict == TimingVerdict.TIMING_LEAK
        assert len(report_branch.violations) == 1
        assert report_branch.violations[0].leak_type == "BRANCH_TIMING_LEAK"

        # 2. Non-constant-time crypto kernel: secret influences table lookup address (CWE-385)
        leaky_cache_ir = """
        define i32 @aes_sbox_lookup(ptr %sbox, i32 %key, i32 %pt) {
        entry:
          %idx = xor i32 %key, %pt
          %ptr = getelementptr inbounds i32, ptr %sbox, i32 %idx
          %val = load i32, ptr %ptr, align 4
          ret i32 %val
        }
        """
        report_cache = verify_crypto_constant_time(leaky_cache_ir)
        assert report_cache.is_constant_time is False
        assert report_cache.verdict == TimingVerdict.TIMING_LEAK
        assert any(v.leak_type == "CACHE_TIMING_LEAK" for v in report_cache.violations)

        # 3. Constant-time crypto kernel: branchless bitwise logic
        constant_time_ir = """
        define i32 @constant_time_mux(i32 %key, i32 %val_a, i32 %val_b) {
        entry:
          %mask = ashr i32 %key, 31
          %inv = xor i32 %mask, -1
          %t1 = and i32 %val_a, %mask
          %t2 = and i32 %val_b, %inv
          %res = or i32 %t1, %t2
          ret i32 %res
        }
        """
        report_ct = verify_crypto_constant_time(constant_time_ir)
        assert report_ct.is_constant_time is True
        assert report_ct.verdict == TimingVerdict.CONSTANT_TIME
        assert len(report_ct.violations) == 0

    def test_fastmcp_cybersecurity_tools(self):
        from server.mcp_server import mcp_prove_vulnerability, mcp_verify_constant_time

        sample_ir = """
        define i32 @calc(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        vuln_res = mcp_prove_vulnerability(sample_ir)
        assert "vulnerabilities_count" in vuln_res
        assert vuln_res["vulnerabilities_count"] == 1
        assert vuln_res["vulnerabilities"][0]["cwe_id"] == "CWE-369"

        ct_res = mcp_verify_constant_time(sample_ir)
        assert "is_constant_time" in ct_res
        assert ct_res["is_constant_time"] is True

    def test_security_hardener_divide_by_zero_mitigation(self):
        from engine.security_hardening import harden_llvm_ir
        from engine.smt_vulnerability_prover import audit_ir_security

        vuln_div_ir = """
        define i32 @unprotected_div(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        # Hardening pass
        h_rep = harden_llvm_ir(vuln_div_ir)
        assert len(h_rep.patches) >= 1
        assert h_rep.patches[0].cwe_id == "CWE-369"
        assert "_div_is_zero" in h_rep.hardened_ir
        assert "select" in h_rep.hardened_ir

        # Hardened IR should no longer have an unconstrained divide-by-zero vulnerability
        dossier = audit_ir_security(h_rep.hardened_ir)
        assert len(dossier.vulnerabilities_found) == 0

    def test_security_hardener_buffer_bounds_mitigation(self):
        from engine.security_hardening import harden_llvm_ir

        vuln_buf_ir = """
        define i32 @unbounded_lookup(i32 %idx) {
        entry:
          %buf = alloca [10 x i32], align 4
          %ptr = getelementptr inbounds [10 x i32], ptr %buf, i64 0, i32 %idx
          %val = load i32, ptr %ptr, align 4
          ret i32 %val
        }
        """
        h_rep = harden_llvm_ir(vuln_buf_ir)
        assert len(h_rep.patches) >= 1
        assert h_rep.patches[0].cwe_id == "CWE-125/787"
        assert "_clamped_idx" in h_rep.hardened_ir
        assert "select" in h_rep.hardened_ir

    def test_cyclonedx_cbom_generation(self):
        from agents.safety_vault import SafetyVault

        vault = SafetyVault()
        cert = vault.generate_certificate(
            project_name="CryptoCore",
            source_code="int crypto_func() { return 1; }",
            ir_code="define i32 @crypto_func() {\nentry:\n  ret i32 1\n}",
            binary_path=None,
            z3_verdict="PROVED",
        )
        cbom = vault.export_cbom(certificate=cert)
        assert cbom["bomFormat"] == "CycloneDX"
        assert cbom["specVersion"] == "1.6"
        assert "metadata" in cbom
        assert "cryptoProperties" in cbom
        attestation = cbom["cryptoProperties"]["attestation"]
        assert "NIST SP 800-218" in attestation["standard"]
        assert attestation["z3_formal_verdict"] == "PROVED"
        assert len(attestation["signature"]) > 0

    def test_mcp_harden_security_and_cbom_tools(self):
        from server.mcp_server import mcp_harden_security, mcp_export_cbom

        vuln_ir = """
        define i32 @div(i32 %a, i32 %b) {
        entry:
          %r = sdiv i32 %a, %b
          ret i32 %r
        }
        """
        hardened = mcp_harden_security(vuln_ir)
        assert "patches_count" in hardened
        assert hardened["patches_count"] >= 1
        assert "hardened_ir" in hardened

        cbom = mcp_export_cbom(llvm_ir=vuln_ir, project_name="TestMCPProject")
        assert cbom["bomFormat"] == "CycloneDX"
        assert cbom["specVersion"] == "1.6"

    def test_differential_exploit_fuzzer_sandbox(self):
        from engine.smt_vulnerability_prover import audit_ir_security
        from engine.security_hardening import harden_llvm_ir
        from engine.exploit_fuzzer import DifferentialExploitFuzzer

        vuln_div_ir = """
        define i32 @unprotected_divide(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        dossier = audit_ir_security(vuln_div_ir)
        assert len(dossier.vulnerabilities_found) >= 1
        finding = dossier.vulnerabilities_found[0]
        assert finding.cwe_id == "CWE-369"
        assert finding.exploit_payload.get("%b") == 0

        h_rep = harden_llvm_ir(vuln_div_ir)
        fuzzer = DifferentialExploitFuzzer(timeout_sec=5)
        rep = fuzzer.verify_exploit(vuln_div_ir, h_rep.hardened_ir, finding)

        assert rep.function_name == "unprotected_divide"
        assert rep.cwe_id == "CWE-369"
        assert "main" in rep.poc_c_source
        assert rep.unhardened_crashed is True
        assert "SIGFPE" in rep.unhardened_status or "CRASHED" in rep.unhardened_status
        assert rep.hardened_safe is True
        assert rep.hardened_status == "SAFE_EXIT_0"
        assert rep.exploit_verified is True

    def test_sarif_codeflows_and_threadflows_generation(self):
        from server.mcp_server import export_sarif_report

        records = [
            {
                "file": "crypto_core.c",
                "findings": [
                    "CWE-125 Buffer Out-of-Bounds: Exploit trigger: %idx=100",
                    "CWE-369 Divide by Zero: Exploit trigger: %b=0",
                ],
            }
        ]
        sarif = export_sarif_report(records)
        assert sarif["version"] == "2.1.0"
        results = sarif["runs"][0]["results"]
        assert len(results) == 2
        for r in results:
            assert r["level"] == "error"
            assert "codeFlows" in r
            flows = r["codeFlows"]
            assert len(flows) >= 1
            thread_flows = flows[0]["threadFlows"]
            assert len(thread_flows) >= 1
            steps = thread_flows[0]["locations"]
            assert len(steps) == 2
            assert "Step 1" in steps[0]["location"]["message"]["text"]
            assert "Step 2" in steps[1]["location"]["message"]["text"]

    def test_mcp_verify_exploit_poc_tool(self):
        from server.mcp_server import mcp_verify_exploit_poc, mcp_harden_security

        unhardened_ir = """
        define i32 @unprotected_divide(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        h_res = mcp_harden_security(unhardened_ir)
        hardened_ir = h_res["hardened_ir"]

        poc_res = mcp_verify_exploit_poc(
            unhardened_ir=unhardened_ir,
            hardened_ir=hardened_ir,
            function_name="unprotected_divide",
            cwe_id="CWE-369",
            exploit_payload={"%a": 42, "%b": 0},
        )

        assert poc_res["function_name"] == "unprotected_divide"
        assert poc_res["cwe_id"] == "CWE-369"
        assert poc_res["unhardened_crashed"] is True
        assert poc_res["hardened_safe"] is True
        assert poc_res["exploit_verified"] is True

    def test_crypto_synthesizer_constant_time_transformation(self):
        from engine.crypto_synthesizer import synthesize_constant_time

        timing_leaking_ir = """
        define i32 @compare_mac(i32 %key, i32 %input) {
        entry:
          %match = icmp eq i32 %key, %input
          br i1 %match, label %then, label %else
        then:
          ret i32 1
        else:
          ret i32 0
        }
        """
        report = synthesize_constant_time(timing_leaking_ir)
        assert len(report.patches) == 1
        assert report.patches[0].leak_type == "BRANCH_TIMING_LEAK"
        assert report.zero_divergence_proved is True
        assert report.constant_time_proved is True
        assert "select" in report.constant_time_ir
        assert "br " not in report.constant_time_ir

    def test_mitre_attack_surface_analysis_and_navigator_layer(self):
        from engine.smt_vulnerability_prover import audit_ir_security
        from engine.crypto_timing_verifier import verify_crypto_constant_time
        from engine.attack_surface import analyze_attack_surface

        vuln_ir = """
        define i32 @crypto_and_div(i32 %a, i32 %b, i32 %key, i32 %input) {
        entry:
          %res = sdiv i32 %a, %b
          %match = icmp eq i32 %key, %input
          br i1 %match, label %then, label %else
        then:
          ret i32 %res
        else:
          ret i32 0
        }
        """
        dossier = audit_ir_security(vuln_ir)
        ct_rep = verify_crypto_constant_time(vuln_ir)
        att_rep = analyze_attack_surface(dossier, ct_rep)

        assert att_rep.attack_surface_score > 0.0
        assert att_rep.vulnerabilities_count >= 2
        assert att_rep.techniques_count >= 2
        assert att_rep.mitigation_coverage_pct == 100.0
        assert att_rep.nist_ssdf_compliant is True

        nav = att_rep.navigator_layer
        assert nav["versions"]["navigator"] == "4.3"
        assert nav["domain"] == "enterprise-attack"
        assert len(nav["techniques"]) >= 2
        tids = {t["techniqueID"] for t in nav["techniques"]}
        assert "T1499" in tids  # CWE-369 DoS
        assert "T1005" in tids  # CWE-208 Timing side-channel

    def test_mcp_synthesize_constant_time_and_attack_surface_tools(self):
        from server.mcp_server import mcp_synthesize_constant_time, mcp_analyze_attack_surface

        leaking_ir = """
        define i32 @verify_token(i32 %secret_key, i32 %candidate) {
        entry:
          %cmp = icmp eq i32 %secret_key, %candidate
          br i1 %cmp, label %valid, label %invalid
        valid:
          ret i32 100
        invalid:
          ret i32 -1
        }
        """
        synth_res = mcp_synthesize_constant_time(leaking_ir)
        assert synth_res["patches_count"] == 1
        assert synth_res["zero_divergence_proved"] is True
        assert synth_res["constant_time_proved"] is True
        assert "select" in synth_res["constant_time_ir"]

        attack_res = mcp_analyze_attack_surface(leaking_ir)
        assert attack_res["attack_surface_score"] > 0
        assert attack_res["techniques_count"] >= 1
        assert "navigator_layer" in attack_res
        assert attack_res["navigator_layer"]["domain"] == "enterprise-attack"

    def test_cfi_protector_indirect_call_hardening(self):
        from engine.cfi_protector import enforce_control_flow_integrity

        indirect_call_ir = """
        define i32 @dispatch_handler(ptr %handler, i32 %val) {
        entry:
          %res = call i32 %handler(i32 %val)
          ret i32 %res
        }
        """
        rep = enforce_control_flow_integrity(indirect_call_ir)
        assert len(rep.violations) == 1
        assert rep.violations[0].cwe_id == "CWE-822"
        assert len(rep.patches) == 1
        assert rep.cfi_enforced_proved is True
        assert "_safe_callee" in rep.hardened_ir
        assert "select" in rep.hardened_ir

    def test_mcp_enforce_cfi_tool(self):
        from server.mcp_server import mcp_enforce_cfi

        indirect_ir = """
        define void @process_event(ptr %cb, ptr %data) {
        entry:
          call void %cb(ptr %data)
          ret void
        }
        """
        res = mcp_enforce_cfi(indirect_ir)
        assert res["violations_count"] == 1
        assert res["patches_count"] == 1
        assert res["cfi_enforced_proved"] is True
        assert "hardened_ir" in res
        assert "_safe_callee" in res["hardened_ir"]


class TestCyberDefenseCLI:
    """Comprehensive test suite for Ecstasy Provable Cyber Defense (PCD) CLI subcommands."""

    def test_cli_cmd_prove(self, capsys):
        c_target = Path(__file__).parent.parent / "demo_corpus" / "unsafe" / "buffer_overflow.c"

        with tempfile.NamedTemporaryFile(suffix=".sarif", delete=False) as f_sarif, \
             tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_rep:
            sarif_path = f_sarif.name
            rep_path = f_rep.name

        try:
            class DummyArgs:
                target = str(c_target)
                sarif = sarif_path
                report = rep_path
                timeout = 15

            cli.cmd_prove(DummyArgs())
            out = capsys.readouterr().out
            assert "ECSTASY SMT VULNERABILITY PROVER" in out
            assert "Security Status:" in out
            assert os.path.exists(sarif_path)
            assert os.path.exists(rep_path)

            with open(sarif_path, "r", encoding="utf-8") as f:
                sarif_data = json.load(f)
            assert sarif_data["version"] == "2.1.0"

            with open(rep_path, "r", encoding="utf-8") as f:
                rep_data = json.load(f)
            assert "functions_analyzed" in rep_data
            assert rep_data["functions_analyzed"] > 0
        finally:
            if os.path.exists(sarif_path):
                os.unlink(sarif_path)
            if os.path.exists(rep_path):
                os.unlink(rep_path)

    def test_cli_cmd_constant_time_and_synthesis(self, capsys):
        leaking_ir = """
        define i32 @compare_mac(i32 %key, i32 %input) {
        entry:
          %match = icmp eq i32 %key, %input
          br i1 %match, label %then, label %else
        then:
          ret i32 1
        else:
          ret i32 0
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", delete=False, mode="w") as f_in, \
             tempfile.NamedTemporaryFile(suffix=".ct.ll", delete=False) as f_out:
            f_in.write(leaking_ir)
            f_in.flush()
            in_path = f_in.name
            out_path = f_out.name

        try:
            class DummyArgs:
                target = in_path
                secrets = "key"
                synthesize = True
                output = out_path
                timeout = 15

            cli.cmd_constant_time(DummyArgs())
            out = capsys.readouterr().out
            assert "ECSTASY CRYPTOGRAPHIC CONSTANT-TIME VERIFIER" in out
            assert "BRANCH_TIMING_LEAK" in out
            assert "Zero-Divergence Proved: ✅ YES" in out
            assert os.path.exists(out_path)

            hardened_ir = Path(out_path).read_text(encoding="utf-8")
            assert "select" in hardened_ir
            assert "br " not in hardened_ir
        finally:
            if os.path.exists(in_path):
                os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_cli_cmd_harden(self, capsys):
        div_ir = """
        define i32 @unprotected_divide(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", delete=False, mode="w") as f_in, \
             tempfile.NamedTemporaryFile(suffix=".hardened.ll", delete=False) as f_out:
            f_in.write(div_ir)
            f_in.flush()
            in_path = f_in.name
            out_path = f_out.name

        try:
            class DummyArgs:
                target = in_path
                output = out_path
                timeout = 15

            cli.cmd_harden(DummyArgs())
            out = capsys.readouterr().out
            assert "ECSTASY SMT-VERIFIED SECURITY HARDENER" in out
            assert "Patches Injected:        1" in out
            assert os.path.exists(out_path)

            hardened = Path(out_path).read_text(encoding="utf-8")
            assert "_safe_den" in hardened
            assert "select" in hardened
        finally:
            if os.path.exists(in_path):
                os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_cli_cmd_cbom(self, capsys):
        with tempfile.NamedTemporaryFile(suffix=".c", delete=False, mode="w") as f_c, \
             tempfile.NamedTemporaryFile(suffix=".cbom.json", delete=False) as f_out:
            f_c.write("int crypto_core() { return 42; }\n")
            f_c.flush()
            c_path = f_c.name
            cbom_path = f_out.name

        try:
            class DummyArgs:
                target = c_path
                output = cbom_path
                project = "CryptoApp"

            cli.cmd_cbom(DummyArgs())
            out = capsys.readouterr().out
            assert "CYCLONEDX v1.6 CRYPTOGRAPHIC BILL OF MATERIALS" in out
            assert "NIST SP 800-218" in out
            assert os.path.exists(cbom_path)

            with open(cbom_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["bomFormat"] == "CycloneDX"
            assert data["specVersion"] == "1.6"
        finally:
            if os.path.exists(c_path):
                os.unlink(c_path)
            if os.path.exists(cbom_path):
                os.unlink(cbom_path)

    def test_cli_cmd_fuzz(self, capsys):
        unhard_ir = """
        define i32 @unprotected_divide(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        hard_ir = """
        define i32 @unprotected_divide(i32 %a, i32 %b) {
        entry:
          %_div_is_zero = icmp eq i32 %b, 0
          %_safe_den = select i1 %_div_is_zero, i32 1, i32 %b
          %res = sdiv i32 %a, %_safe_den
          ret i32 %res
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", delete=False, mode="w") as f_u, \
             tempfile.NamedTemporaryFile(suffix=".ll", delete=False, mode="w") as f_h:
            f_u.write(unhard_ir)
            f_u.flush()
            f_h.write(hard_ir)
            f_h.flush()
            u_path = f_u.name
            h_path = f_h.name

        try:
            class DummyArgs:
                unhardened = u_path
                hardened = h_path
                cwe = "CWE-369"
                timeout = 5

            cli.cmd_fuzz(DummyArgs())
            out = capsys.readouterr().out
            assert "DIFFERENTIAL EXPLOIT POC FUZZER" in out
            assert "Red-Team Run:" in out
            assert "Blue-Team Run:" in out
            assert "SAFE_EXIT_0" in out
        finally:
            if os.path.exists(u_path):
                os.unlink(u_path)
            if os.path.exists(h_path):
                os.unlink(h_path)

    def test_cli_cmd_cfi(self, capsys):
        indirect_ir = """
        define i32 @dispatch_handler(ptr %handler, i32 %val) {
        entry:
          %res = call i32 %handler(i32 %val)
          ret i32 %res
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", delete=False, mode="w") as f_in, \
             tempfile.NamedTemporaryFile(suffix=".cfi.ll", delete=False) as f_out:
            f_in.write(indirect_ir)
            f_in.flush()
            in_path = f_in.name
            out_path = f_out.name

        try:
            class DummyArgs:
                target = in_path
                output = out_path
                timeout = 15

            cli.cmd_cfi(DummyArgs())
            out = capsys.readouterr().out
            assert "FORWARD-EDGE CONTROL-FLOW INTEGRITY (CFI) ENFORCER" in out
            assert "CFI Guards Injected:    1" in out
            assert os.path.exists(out_path)

            cfi_ir = Path(out_path).read_text(encoding="utf-8")
            assert "_safe_callee" in cfi_ir
        finally:
            if os.path.exists(in_path):
                os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_cli_cmd_attack_matrix(self, capsys):
        vuln_ir = """
        define i32 @vuln(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", delete=False, mode="w") as f_in, \
             tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_out:
            f_in.write(vuln_ir)
            f_in.flush()
            in_path = f_in.name
            out_path = f_out.name

        try:
            class DummyArgs:
                target = in_path
                output = out_path
                timeout = 15

            cli.cmd_attack_matrix(DummyArgs())
            out = capsys.readouterr().out
            assert "MITRE ATT&CK ENTERPRISE MATRIX & ATTACK SURFACE" in out
            assert "Attack Surface Score:" in out
            assert os.path.exists(out_path)

            with open(out_path, "r", encoding="utf-8") as f:
                nav = json.load(f)
            assert nav["domain"] == "enterprise-attack"
            assert nav["versions"]["navigator"] == "4.3"
        finally:
            if os.path.exists(in_path):
                os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)







