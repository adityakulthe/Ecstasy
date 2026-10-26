"""
Comprehensive Tests for Ecstasy Composite Provable Cyber Defense Suite (Phase 32):
- Speculative Execution & Spectre v1/v2 Formal Verifier & Barrier Synthesizer
- Zero-Source Stripped Binary Lifter, CFG Reconstructor & SMT Prover
- Autonomous Self-Healing CI/CD Gatekeeper ('Ecstasy Guard')
- New CLI commands and FastMCP tools
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

from engine.speculative_verifier import SpeculativeVerifier, SpectreVariant
from engine.binary_lifter import BinaryLifter, BinaryFormat
from engine.self_healing_guard import SelfHealingGuard
from server.mcp_server import (
    mcp_verify_speculative_execution,
    mcp_lift_binary_to_ir,
    mcp_run_self_healing_guard,
)
import cli


SPECTRE_VULN_IR = """
define i32 @spectre_victim(i32 %x, ptr %arr1, ptr %arr2) {
entry:
  %cmp = icmp ult i32 %x, 16
  br i1 %cmp, label %safe, label %err
safe:
  %p1 = getelementptr inbounds i8, ptr %arr1, i32 %x
  %secret = load i8, ptr %p1
  %p2 = getelementptr inbounds i8, ptr %arr2, i8 %secret
  %leak = load i8, ptr %p2
  ret i32 0
err:
  ret i32 -1
}
"""

SPECTRE_SAFE_IR = """
define i32 @safe_compute(i32 %a, i32 %b) {
entry:
  %res = add i32 %a, %b
  ret i32 %res
}
"""


class TestSpeculativeVerifier:
    """Test suite for Spectre v1/v2 speculative side-channel formal verification."""

    def test_spectre_v1_leak_detection(self):
        verifier = SpeculativeVerifier()
        audit = verifier.audit_speculation_safety(SPECTRE_VULN_IR)
        assert not audit.is_speculation_safe
        assert len(audit.findings) >= 1
        f = audit.findings[0]
        assert f.variant == SpectreVariant.SPECTRE_V1.value
        assert f.cwe_id == "CWE-1037"
        assert "Bounds Check Bypass" in f.description

    def test_spectre_barrier_synthesis_arm64(self):
        verifier = SpeculativeVerifier()
        synth = verifier.synthesize_speculative_barriers(SPECTRE_VULN_IR, target_arch="arm64")
        assert len(synth.patches) >= 1
        assert synth.sni_proved
        assert synth.zero_divergence_proved
        assert "@llvm.aarch64.csdb" in synth.hardened_ir

    def test_spectre_barrier_synthesis_x86(self):
        verifier = SpeculativeVerifier()
        synth = verifier.synthesize_speculative_barriers(SPECTRE_VULN_IR, target_arch="x86")
        assert len(synth.patches) >= 1
        assert synth.sni_proved
        assert "lfence" in synth.hardened_ir

    def test_spectre_immune_code(self):
        verifier = SpeculativeVerifier()
        audit = verifier.audit_speculation_safety(SPECTRE_SAFE_IR)
        assert audit.is_speculation_safe
        assert len(audit.findings) == 0
        assert audit.sni_proved


class TestBinaryLifter:
    """Test suite for Zero-Source native binary lifting and security auditing."""

    def test_identify_format(self):
        lifter = BinaryLifter()
        target_bin = "/bin/ls" if os.path.exists("/bin/ls") else sys.executable
        fmt, arch = lifter.identify_format(target_bin)
        assert fmt != BinaryFormat.UNKNOWN
        assert arch != "unknown"

    def test_disassemble_and_lift_ir(self):
        lifter = BinaryLifter()
        target_bin = "/bin/ls" if os.path.exists("/bin/ls") else sys.executable
        lifted = lifter.lift_binary_to_ir(target_bin)
        assert lifted.functions_count > 0
        assert len(lifted.recovered_functions) > 0
        assert "define" in lifted.llvm_ir
        assert "; Target Architecture:" in lifted.llvm_ir

    def test_audit_binary_safety_rop_and_canaries(self):
        lifter = BinaryLifter()
        target_bin = "/bin/ls" if os.path.exists("/bin/ls") else sys.executable
        audit = lifter.audit_binary_safety(target_bin)
        assert audit.rop_gadgets_found > 0
        assert 0.0 <= audit.risk_score <= 10.0
        assert 0.0 <= audit.stack_canary_coverage_pct <= 100.0


class TestSelfHealingGuard:
    """Test suite for autonomous CI/CD vulnerability discovery and closed-loop repair."""

    def test_guard_audit_and_heal_file(self):
        guard = SelfHealingGuard()
        vuln_ir = """
        define i32 @unprotected_math(i32 %x, i32 %y) {
        entry:
          %div = sdiv i32 %x, %y
          ret i32 %div
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(vuln_ir)
            t_path = f.name

        try:
            res = guard.audit_and_heal_file(t_path, auto_patch=False)
            assert res.status == "HEALED"
            assert res.original_vulnerabilities_count >= 1
            assert res.patches_applied_count >= 1
            assert "select" in res.hardened_ir
            assert res.attestation_bundle is not None
        finally:
            if os.path.exists(t_path):
                os.unlink(t_path)

    def test_guard_clean_file(self):
        guard = SelfHealingGuard()
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(SPECTRE_SAFE_IR)
            t_path = f.name

        try:
            res = guard.audit_and_heal_file(t_path)
            assert res.status == "CLEAN"
            assert res.patches_applied_count == 0
        finally:
            if os.path.exists(t_path):
                os.unlink(t_path)

    def test_guard_auto_patch_generation(self):
        guard = SelfHealingGuard()
        vuln_ir = """
        define i32 @overflow_div(i32 %a, i32 %b) {
        entry:
          %res = sdiv i32 %a, %b
          ret i32 %res
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(vuln_ir)
            t_path = f.name

        out_dir = tempfile.mkdtemp()
        try:
            res = guard.audit_and_heal_file(t_path, auto_patch=True, output_dir=out_dir)
            assert res.status == "HEALED"
            patch_file = Path(out_dir) / f"{Path(t_path).stem}.patch"
            healed_file = Path(out_dir) / f"{Path(t_path).stem}.healed.ll"
            assert patch_file.exists()
            assert healed_file.exists()
        finally:
            if os.path.exists(t_path):
                os.unlink(t_path)
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)


class TestCompositeCLI:
    """Test suite for new CLI subcommands: spectre, lift, guard."""

    def test_cli_cmd_spectre(self, capsys):
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(SPECTRE_VULN_IR)
            ir_path = f.name

        try:
            class DummyArgs:
                target = ir_path
                synthesize = True
                arch = "arm64"
                output = None
                timeout = 15

            cli.cmd_spectre(DummyArgs())
            captured = capsys.readouterr().out
            assert "SPECULATIVE EXECUTION & SPECTRE FORMAL VERIFIER" in captured
            assert "Zero-Divergence Proved: ✅ YES" in captured
            assert "SNI Proved:            ✅ YES" in captured
        finally:
            if os.path.exists(ir_path):
                os.unlink(ir_path)

    def test_cli_cmd_lift(self, capsys):
        target_bin = "/bin/ls" if os.path.exists("/bin/ls") else sys.executable
        with tempfile.NamedTemporaryFile(suffix=".lifted.ll", delete=False) as f:
            out_ir = f.name

        try:
            class DummyArgs:
                binary = target_bin
                output = out_ir
                no_audit = False
                timeout = 15

            cli.cmd_lift(DummyArgs())
            captured = capsys.readouterr().out
            assert "ZERO-SOURCE STRIPPED BINARY LIFTER" in captured
            assert "Functions Recovered:" in captured
            assert os.path.exists(out_ir)
        finally:
            if os.path.exists(out_ir):
                os.unlink(out_ir)

    def test_cli_cmd_guard(self, capsys):
        vuln_ir = """
        define i32 @guard_test(i32 %x, i32 %y) {
        entry:
          %div = sdiv i32 %x, %y
          ret i32 %div
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(vuln_ir)
            t_path = f.name

        try:
            class DummyArgs:
                target = t_path
                auto_patch = False
                output = None
                timeout = 15

            cli.cmd_guard(DummyArgs())
            captured = capsys.readouterr().out
            assert "AUTONOMOUS SELF-HEALING CI/CD GATEKEEPER" in captured
            assert "Remediation Status:    🔧 HEALED" in captured
        finally:
            if os.path.exists(t_path):
                os.unlink(t_path)


class TestCompositeMCPTools:
    """Test suite for FastMCP tools integration: spectre, lifter, guard."""

    def test_mcp_verify_speculative_execution(self):
        audit = mcp_verify_speculative_execution(SPECTRE_VULN_IR, synthesize_barriers=False)
        assert not audit["is_speculation_safe"]
        assert audit["findings_count"] >= 1

        synth = mcp_verify_speculative_execution(SPECTRE_VULN_IR, synthesize_barriers=True, target_arch="arm64")
        assert synth["sni_proved"]
        assert synth["patches_count"] >= 1

    def test_mcp_lift_binary_to_ir(self):
        target_bin = "/bin/ls" if os.path.exists("/bin/ls") else sys.executable
        res = mcp_lift_binary_to_ir(target_bin, audit_safety=True)
        assert res["functions_count"] > 0
        assert "audit_report" in res

    def test_mcp_run_self_healing_guard(self):
        vuln_ir = """
        define i32 @mcp_guard_fn(i32 %a, i32 %b) {
        entry:
          %div = sdiv i32 %a, %b
          ret i32 %div
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(vuln_ir)
            t_path = f.name

        try:
            res = mcp_run_self_healing_guard(t_path, auto_patch=False)
            assert res["status"] == "HEALED"
            assert res["patches_applied_count"] >= 1
        finally:
            if os.path.exists(t_path):
                os.unlink(t_path)
