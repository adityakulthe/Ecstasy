"""
Comprehensive Tests for Ecstasy Provable Cyber Defense (PCD) Phase 31:
- Post-Quantum Cryptography (PQC) Constant-Time Verifier & Synthesizer (ML-KEM / ML-DSA)
- ARM64 Hardware Memory Safety (PAC & MTE) IR Instrumentation & SMT Invariants
- in-toto v1.0 & DSSE Cryptographic Supply Chain Attestation
- Dedicated CLI subcommands and FastMCP tools
"""

import os
import json
import tempfile
from pathlib import Path
import pytest

from engine.pqc_verifier import PQCVerifier, PQCScheme
from engine.hardware_safety import HardwareSafetyTransformer, HardwareSecurityFeature
from engine.attestation_bundle import AttestationBundleGenerator
from server.mcp_server import (
    mcp_verify_pqc_constant_time,
    mcp_enforce_hardware_safety,
    mcp_generate_attestation_bundle,
)
import cli


KYBER_LEAKY_IR = """
define i32 @kyber_reduce(i32 %x) {
entry:
  %cmp = icmp sge i32 %x, 3329
  br i1 %cmp, label %sub_label, label %done
sub_label:
  %res = sub i32 %x, 3329
  ret i32 %res
done:
  ret i32 %x
}
"""

KYBER_CONSTANT_TIME_IR = """
define i32 @kyber_ct_reduce(i32 %x) {
entry:
  %diff = sub i32 %x, 3329
  %shift = ashr i32 %diff, 31
  %mask = and i32 3329, %shift
  %res = add i32 %diff, %mask
  ret i32 %res
}
"""

DILITHIUM_LEAKY_IR = """
define i32 @dilithium_reduce(i32 %x) {
entry:
  %cmp = icmp sge i32 %x, 8380417
  br i1 %cmp, label %sub_label, label %done
sub_label:
  %res = sub i32 %x, 8380417
  ret i32 %res
done:
  ret i32 %x
}
"""

HARDWARE_SAFETY_TARGET_IR = """
define i32 @secure_dispatch(ptr %callee, i32 %arg) {
entry:
  %buffer = alloca [64 x i8], align 16
  %out = call i32 %callee(i32 %arg)
  ret i32 %out
}
"""


class TestPQCVerifier:
    """Test suite for Post-Quantum Cryptography constant-time formal verification & synthesis."""

    def test_pqc_kyber_timing_leak_detection(self):
        verifier = PQCVerifier()
        report = verifier.verify_pqc_constant_time(KYBER_LEAKY_IR, scheme="ML_KEM_KYBER")
        assert not report.is_constant_time
        assert report.modulus == 3329
        assert report.scheme == "ML_KEM_KYBER"
        assert len(report.violations) >= 1
        assert any(v.vulnerability_type == "VARIABLE_TIME_MODULAR_REDUCTION" for v in report.violations)

    def test_pqc_kyber_branchless_synthesis_and_zero_divergence(self):
        verifier = PQCVerifier()
        synth = verifier.synthesize_constant_time_pqc(KYBER_LEAKY_IR, scheme="ML_KEM_KYBER")
        assert synth.zero_divergence_proved
        assert synth.constant_time_proved
        assert len(synth.patches) == 1
        assert "%ct_diff_x = sub i32 %x, 3329" in synth.constant_time_ir
        assert "%ct_mask_x = and i32 3329, %ct_shift_x" in synth.constant_time_ir

    def test_pqc_dilithium_modulus_audit(self):
        verifier = PQCVerifier()
        report = verifier.verify_pqc_constant_time(DILITHIUM_LEAKY_IR, scheme="ML_DSA_DILITHIUM")
        assert not report.is_constant_time
        assert report.modulus == 8380417
        assert report.scheme == "ML_DSA_DILITHIUM"
        assert len(report.violations) >= 1

    def test_pqc_constant_time_clean_code(self):
        verifier = PQCVerifier()
        report = verifier.verify_pqc_constant_time(KYBER_CONSTANT_TIME_IR, scheme="ML_KEM_KYBER")
        assert report.is_constant_time
        assert len(report.violations) == 0
        assert "Zero secret-dependent modular reduction branches" in report.proof_explanation

    def test_pqc_division_timing_detection(self):
        verifier = PQCVerifier()
        div_ir = """
        define i32 @poly_div(i32 %secret_coeff, i32 %divisor) {
        entry:
          %res = sdiv i32 %secret_coeff, %divisor
          ret i32 %res
        }
        """
        report = verifier.verify_pqc_constant_time(div_ir, secret_params=["secret_coeff"])
        assert not report.is_constant_time
        assert any(v.vulnerability_type == "DIVISION_TIMING" for v in report.violations)


class TestHardwareSafetyTransformer:
    """Test suite for ARM64 Pointer Authentication (PAC) and Memory Tagging Extension (MTE)."""

    def test_pac_indirect_call_instrumentation(self):
        transformer = HardwareSafetyTransformer()
        report = transformer.instrument_hardware_safety(HARDWARE_SAFETY_TARGET_IR, enable_pac=True, enable_mte=False)
        assert report.pac_guards_count == 1
        assert report.mte_tags_count == 0
        assert report.zero_divergence_proved
        assert report.hardware_trap_proved
        assert "@llvm.ptrauth.auth" in report.hardened_ir

    def test_mte_stack_allocation_tagging(self):
        transformer = HardwareSafetyTransformer()
        report = transformer.instrument_hardware_safety(HARDWARE_SAFETY_TARGET_IR, enable_pac=False, enable_mte=True)
        assert report.pac_guards_count == 0
        assert report.mte_tags_count == 1
        assert "@llvm.aarch64.irg" in report.hardened_ir

    def test_hardware_safety_combined_features(self):
        transformer = HardwareSafetyTransformer()
        report = transformer.instrument_hardware_safety(HARDWARE_SAFETY_TARGET_IR, enable_pac=True, enable_mte=True)
        assert report.pac_guards_count == 1
        assert report.mte_tags_count == 1
        assert report.zero_divergence_proved
        assert report.hardware_trap_proved
        assert len(report.patches) == 2


class TestAttestationBundleGenerator:
    """Test suite for in-toto v1.0 and DSSE supply-chain attestation generation and verification."""

    def test_in_toto_statement_and_dsse_generation(self):
        gen = AttestationBundleGenerator()
        artifacts = [
            {"name": "test.c", "digest": {"sha256": "1111222233334444"}},
            {"name": "test.ll", "digest": {"sha256": "5555666677778888"}},
        ]
        bundle = gen.generate_bundle(
            target_name="test.c",
            artifacts=artifacts,
            formal_verdict="PROVED",
            zero_divergence_proved=True,
        )
        assert bundle["payloadType"] == "application/vnd.in-toto+json"
        assert len(bundle["signatures"]) == 1
        assert bundle["signatures"][0]["keyid"] == "ecstasy-vault-ed25519-primary"

    def test_attestation_bundle_verification_valid(self):
        gen = AttestationBundleGenerator()
        artifacts = [{"name": "module.ll", "digest": {"sha256": "abcdef0123456789"}}]
        bundle = gen.generate_bundle(
            target_name="module.ll",
            artifacts=artifacts,
            formal_verdict="PROVED",
            zero_divergence_proved=True,
        )
        report = gen.verify_bundle(bundle)
        assert report.valid
        assert report.signature_valid
        assert report.formal_proofs_verified
        assert report.subject_count == 1
        assert len(report.issues) == 0

    def test_attestation_bundle_verification_tampered_fails(self):
        gen = AttestationBundleGenerator()
        bundle = gen.generate_bundle(
            target_name="module.ll",
            artifacts=[{"name": "module.ll", "digest": {"sha256": "abcdef0123456789"}}],
            formal_verdict="PROVED",
        )
        # Tamper signature
        bundle["signatures"][0]["sig"] = "dGFtcGVyZWQtc2lnbmF0dXJl"
        report = gen.verify_bundle(bundle)
        assert not report.valid
        assert not report.signature_valid
        assert any("mismatch" in iss for iss in report.issues)


class TestPCDAdvancedCLI:
    """Test suite for new CLI subcommands: pqc, pac, attest."""

    def test_cli_cmd_pqc_audit(self, capsys):
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(KYBER_LEAKY_IR)
            ir_path = f.name

        try:
            class DummyArgs:
                target = ir_path
                scheme = "ML_KEM_KYBER"
                synthesize = False
                timeout = 15

            cli.cmd_pqc(DummyArgs())
            captured = capsys.readouterr().out
            assert "POST-QUANTUM CRYPTOGRAPHY (PQC) FORMAL VERIFIER" in captured
            assert "TIMING LEAK DETECTED" in captured
            assert "ML_KEM_KYBER" in captured
        finally:
            if os.path.exists(ir_path):
                os.unlink(ir_path)

    def test_cli_cmd_pqc_synthesize(self, capsys):
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(KYBER_LEAKY_IR)
            ir_path = f.name

        out_path = f"{ir_path}.synth.ll"
        try:
            class DummyArgs:
                target = ir_path
                scheme = "ML_KEM_KYBER"
                synthesize = True
                output = out_path
                timeout = 15

            cli.cmd_pqc(DummyArgs())
            captured = capsys.readouterr().out
            assert "Zero-Divergence Proved: ✅ YES" in captured
            assert "Constant-Time Proved:  ✅ YES" in captured
            assert os.path.exists(out_path)
            content = Path(out_path).read_text()
            assert "ct_diff_x" in content
        finally:
            if os.path.exists(ir_path):
                os.unlink(ir_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_cli_cmd_pac_instrumentation(self, capsys):
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(HARDWARE_SAFETY_TARGET_IR)
            ir_path = f.name

        out_path = f"{ir_path}.pac.ll"
        try:
            class DummyArgs:
                target = ir_path
                no_pac = False
                no_mte = False
                output = out_path
                timeout = 15

            cli.cmd_pac(DummyArgs())
            captured = capsys.readouterr().out
            assert "ARM64 HARDWARE-ASSISTED MEMORY SAFETY" in captured
            assert "PAC Guards Injected:    1" in captured
            assert "MTE Color Tags:         1" in captured
            assert os.path.exists(out_path)
        finally:
            if os.path.exists(ir_path):
                os.unlink(ir_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_cli_cmd_attest_generate_and_verify(self, capsys):
        with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as f:
            f.write(KYBER_CONSTANT_TIME_IR)
            ir_path = f.name

        bundle_path = f"{ir_path}.attest.json"
        try:
            # 1. Generate
            class GenArgs:
                target = ir_path
                verify = None
                output = bundle_path
                timeout = 15

            cli.cmd_attest(GenArgs())
            out_gen = capsys.readouterr().out
            assert "IN-TOTO v1.0 & DSSE CRYPTOGRAPHIC ATTESTATION BUNDLE" in out_gen
            assert os.path.exists(bundle_path)

            # 2. Verify
            class VerArgs:
                target = ""
                verify = bundle_path
                output = None
                timeout = 15

            cli.cmd_attest(VerArgs())
            out_ver = capsys.readouterr().out
            assert "IN-TOTO v1.0 SUPPLY CHAIN ATTESTATION VERIFICATION" in out_ver
            assert "Cryptographic Signature: ✅ VALID" in out_ver
            assert "TRUSTED BUNDLE" in out_ver
        finally:
            if os.path.exists(ir_path):
                os.unlink(ir_path)
            if os.path.exists(bundle_path):
                os.unlink(bundle_path)


class TestMCPAdvancedPCDTools:
    """Test suite for FastMCP tools integration."""

    def test_mcp_verify_pqc_constant_time(self):
        audit = mcp_verify_pqc_constant_time(KYBER_LEAKY_IR, scheme="ML_KEM_KYBER", synthesize=False)
        assert not audit["is_constant_time"]
        assert audit["violations_count"] >= 1

        synth = mcp_verify_pqc_constant_time(KYBER_LEAKY_IR, scheme="ML_KEM_KYBER", synthesize=True)
        assert synth["zero_divergence_proved"]
        assert synth["constant_time_proved"]

    def test_mcp_enforce_hardware_safety(self):
        rep = mcp_enforce_hardware_safety(HARDWARE_SAFETY_TARGET_IR, enable_pac=True, enable_mte=True)
        assert rep["pac_guards_count"] == 1
        assert rep["mte_tags_count"] == 1
        assert rep["zero_divergence_proved"]

    def test_mcp_generate_attestation_bundle(self):
        bundle = mcp_generate_attestation_bundle("test_mod", KYBER_CONSTANT_TIME_IR)
        assert bundle["payloadType"] == "application/vnd.in-toto+json"
        assert len(bundle["signatures"]) == 1
