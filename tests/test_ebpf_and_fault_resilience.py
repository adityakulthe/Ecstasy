"""
Comprehensive Test Suite for Ecstasy Phase 33:
- eBPF Kernel Safety Verifier & Automated Rewriter
- Hardware Fault Injection & Dual-Rail Glitch Resilience Synthesizer
- Autonomous Continuous Repository Self-Healing Daemon ("Ecstasy Watch")
- FastMCP Tools & CLI Integration
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

from engine.ebpf_verifier import (
    EBPFVerifier,
    EBPFVerdict,
    EBPFViolation,
    EBPFPatch,
    EBPFReport,
)
from engine.fault_resilience import (
    FaultResilienceSynthesizer,
    FaultMechanism,
    GlitchVulnerability,
    FaultResiliencePatch,
    FaultResilienceReport,
)
from engine.self_healing_daemon import (
    SelfHealingDaemon,
    DaemonStatus,
    WatchEvent,
)
from server.mcp_server import (
    mcp_verify_ebpf_safety,
    mcp_synthesize_fault_resilience,
    mcp_watch_repository,
)


class TestEBPFKernelVerifier:
    """Tests for eBPF kernel invariants: packet bounds, stack limit, and loop bounds."""

    def test_ebpf_unbounded_packet_access_and_rewriter(self):
        verifier = EBPFVerifier(timeout_sec=10)

        # Unbounded packet dereference without data_end check
        unsafe_ebpf_ir = """
        define i32 @filter_packet(ptr %ctx) {
        entry:
            %pkt_ptr = load ptr, ptr %ctx, align 8
            %val = load i32, ptr %pkt_ptr, align 4
            %cmp = icmp eq i32 %val, 42
            br i1 %cmp, label %pass, label %drop
        pass:
            ret i32 1
        drop:
            ret i32 2
        }
        """

        # 1. Audit should flag packet access violation
        audit = verifier.verify_ebpf_safety(unsafe_ebpf_ir, target_name="filter_packet")
        assert audit.verdict == EBPFVerdict.REJECTED_UNSAFE
        assert audit.is_kernel_acceptable is False
        assert len(audit.violations) >= 1
        v = audit.violations[0]
        assert v.violation_type == "UNBOUNDED_PACKET_ACCESS"
        assert v.cwe_id == "CWE-125"

        # 2. Automated rewriter should inject [data, data_end) check and XDP_DROP
        rewrite_rep = verifier.verify_and_rewrite_ebpf(unsafe_ebpf_ir, target_name="filter_packet")
        assert rewrite_rep.verdict == EBPFVerdict.REWRITTEN_SAFE
        assert rewrite_rep.is_kernel_acceptable is True
        assert len(rewrite_rep.patches) >= 1
        assert "ret i32 2" in rewrite_rep.rewritten_ir or "icmp ule" in rewrite_rep.rewritten_ir
        assert rewrite_rep.zero_divergence_proved is True

    def test_ebpf_stack_frame_limit_512b(self):
        verifier = EBPFVerifier(timeout_sec=10)

        # Violates the Linux kernel 512-byte eBPF stack limit
        stack_overflow_ir = """
        define i32 @handle_xdp(ptr %ctx) {
        entry:
            %large_buffer = alloca [600 x i8], align 1
            ret i32 1
        }
        """

        audit = verifier.verify_ebpf_safety(stack_overflow_ir, target_name="handle_xdp")
        assert audit.verdict == EBPFVerdict.REJECTED_UNSAFE
        assert any(v.violation_type == "STACK_FRAME_OVERFLOW" for v in audit.violations)
        assert any(v.cwe_id == "CWE-787" for v in audit.violations)

    def test_ebpf_compliant_program(self):
        verifier = EBPFVerifier(timeout_sec=10)

        # Perfectly bounded eBPF packet filter
        safe_ebpf_ir = """
        define i32 @xdp_pass(ptr %ctx) {
        entry:
            %small_buf = alloca [64 x i8], align 1
            %data_end = load ptr, ptr %ctx, align 8
            %ok = icmp ule ptr %small_buf, %data_end
            br i1 %ok, label %proceed, label %drop
        proceed:
            ret i32 1
        drop:
            ret i32 2
        }
        """

        audit = verifier.verify_ebpf_safety(safe_ebpf_ir, target_name="xdp_pass")
        assert audit.verdict == EBPFVerdict.VERIFIED_SAFE
        assert audit.is_kernel_acceptable is True
        assert len(audit.violations) == 0


class TestFaultResilienceSynthesizer:
    """Tests for physical glitch, laser fault injection, and Rowhammer mitigation."""

    def test_glitch_vulnerability_detection(self):
        synth = FaultResilienceSynthesizer(timeout_sec=10)

        # Critical authentication check vulnerable to single-instruction glitch skip
        auth_gate_ir = """
        define i32 @verify_admin_signature(i32 %sig) {
        entry:
            %is_valid = icmp eq i32 %sig, 31337
            br i1 %is_valid, label %grant_root, label %deny_root
        grant_root:
            ret i32 1
        deny_root:
            ret i32 0
        }
        """

        audit = synth.audit_fault_vulnerabilities(auth_gate_ir, target_name="verify_admin")
        assert audit.is_resilient is False
        assert len(audit.vulnerabilities) >= 1
        v = audit.vulnerabilities[0]
        assert v.cwe_id == "CWE-1254"
        assert v.condition_register == "%is_valid"

    def test_dual_rail_complement_synthesis_and_smt_proof(self):
        synth = FaultResilienceSynthesizer(timeout_sec=10)

        auth_gate_ir = """
        define i32 @check_crypto_token(i32 %token) {
        entry:
            %match = icmp eq i32 %token, 777
            br i1 %match, label %privileged, label %rejected
        privileged:
            ret i32 1
        rejected:
            ret i32 0
        }
        """

        hardened_rep = synth.synthesize_fault_resilience(auth_gate_ir, target_name="check_crypto_token")
        assert hardened_rep.is_resilient is True
        assert len(hardened_rep.patches) >= 1
        assert hardened_rep.zero_divergence_proved is True
        assert hardened_rep.fault_immunity_proved is True
        assert hardened_rep.hardware_trap_proved is True
        assert "@llvm.trap" in hardened_rep.hardened_ir
        assert "xor i1" in hardened_rep.hardened_ir or "dual_rail" in hardened_rep.hardened_ir


class TestSelfHealingDaemon:
    """Tests for continuous repository file watcher and real-time SMT auto-patcher."""

    def test_daemon_single_scan_and_auto_patch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            vuln_file = tmp_path / "vulnerable_crypto.ll"
            vuln_file.write_text("""
            define i32 @insecure_memcmp(ptr %p1, ptr %p2) {
            entry:
                %c = icmp eq ptr %p1, %p2
                br i1 %c, label %same, label %diff
            same:
                ret i32 0
            diff:
                ret i32 1
            }
            """, encoding="utf-8")

            daemon = SelfHealingDaemon(repo_dir=str(tmp_path), auto_patch=True)
            status = daemon.run_single_scan()

            assert status.files_tracked >= 1
            assert status.events_processed >= 1
            assert len(status.recent_events) >= 1
            event = status.recent_events[0]
            assert event.file_path == str(vuln_file)

    def test_daemon_status_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            clean_file = tmp_path / "clean_calc.ll"
            clean_file.write_text("""
            define i32 @add(i32 %a, i32 %b) {
            entry:
                %res = add i32 %a, %b
                ret i32 %res
            }
            """, encoding="utf-8")

            daemon = SelfHealingDaemon(repo_dir=str(tmp_path), auto_patch=False)
            daemon.start_daemon(max_iterations=1)
            status = daemon.get_status()

            assert status.is_running is False
            assert status.files_tracked >= 1
            assert status.events_processed >= 1


class TestMCPNewTools:
    """Verify newly registered FastMCP tools."""

    def test_mcp_verify_ebpf_safety_tool(self):
        ebpf_ir = """
        define i32 @xdp_prog(ptr %ctx) {
        entry:
            %pkt = load ptr, ptr %ctx, align 8
            %val = load i32, ptr %pkt, align 4
            ret i32 %val
        }
        """
        # Audit
        res = mcp_verify_ebpf_safety(ebpf_ir, rewrite=False)
        assert res["verdict"] == "REJECTED_UNSAFE"
        assert res["is_kernel_acceptable"] is False

        # Rewrite
        res_rw = mcp_verify_ebpf_safety(ebpf_ir, rewrite=True)
        assert res_rw["verdict"] == "REWRITTEN_SAFE"
        assert res_rw["is_kernel_acceptable"] is True
        assert len(res_rw["patches"]) >= 1

    def test_mcp_synthesize_fault_resilience_tool(self):
        gate_ir = """
        define i32 @gate(i32 %in) {
        entry:
            %ok = icmp eq i32 %in, 100
            br i1 %ok, label %t, label %f
        t:
            ret i32 1
        f:
            ret i32 0
        }
        """
        res = mcp_synthesize_fault_resilience(gate_ir, synthesize=True)
        assert res["is_resilient"] is True
        assert res["fault_immunity_proved"] is True
        assert res["hardware_trap_proved"] is True

    def test_mcp_watch_repository_tool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            sample_file = tmp_path / "sample.ll"
            sample_file.write_text("define i32 @foo() { ret i32 0 }", encoding="utf-8")

            res = mcp_watch_repository(str(tmp_path), single_scan=True, auto_patch=False)
            assert res["files_tracked"] >= 1
            assert res["events_processed"] >= 1


class TestCLINewCommands:
    """Verify execution of new CLI subcommands: ebpf, fault-resilience, watch."""

    def test_cli_ebpf_subcommand(self, tmp_path):
        ir_file = tmp_path / "ebpf_test.ll"
        ir_file.write_text("""
        define i32 @xdp_test(ptr %ctx) {
        entry:
            %pkt = load ptr, ptr %ctx, align 8
            %v = load i32, ptr %pkt, align 4
            ret i32 %v
        }
        """, encoding="utf-8")

        from cli import main
        import sys

        # Test audit
        sys.argv = ["cli.py", "ebpf", str(ir_file)]
        main()

        # Test rewrite
        out_file = tmp_path / "ebpf_out.ll"
        sys.argv = ["cli.py", "ebpf", str(ir_file), "--rewrite", "-o", str(out_file)]
        main()
        assert out_file.exists()

    def test_cli_fault_resilience_subcommand(self, tmp_path):
        ir_file = tmp_path / "fault_test.ll"
        ir_file.write_text("""
        define i32 @auth(i32 %key) {
        entry:
            %c = icmp eq i32 %key, 999
            br i1 %c, label %pass, label %fail
        pass:
            ret i32 1
        fail:
            ret i32 0
        }
        """, encoding="utf-8")

        from cli import main
        import sys

        # Test audit
        sys.argv = ["cli.py", "fault-resilience", str(ir_file)]
        main()

        # Test synthesize
        out_file = tmp_path / "fault_out.ll"
        sys.argv = ["cli.py", "fault-resilience", str(ir_file), "--synthesize", "-o", str(out_file)]
        main()
        assert out_file.exists()

    def test_cli_watch_subcommand(self, tmp_path):
        sample_file = tmp_path / "foo.ll"
        sample_file.write_text("define i32 @bar() { ret i32 1 }", encoding="utf-8")

        from cli import main
        import sys

        sys.argv = ["cli.py", "watch", str(tmp_path), "--once"]
        main()
