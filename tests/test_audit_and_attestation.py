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
