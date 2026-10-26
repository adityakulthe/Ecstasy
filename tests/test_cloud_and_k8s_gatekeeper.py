"""
Tests for Google Cloud Binary Authorization Gatekeeper & Kubernetes Admission Controller
Part of Ecstasy Provable Cyber Defense (PCD)
"""

import os
import sys
import json
import base64
import tempfile
import pytest
from pathlib import Path

from engine.attestation_bundle import AttestationBundleGenerator
from deploy.gcp.gcp_gatekeeper import GCPGatekeeper
from deploy.k8s.admission_controller import AdmissionWebhookHandler


class TestGCPBinaryAuthorizationGatekeeper:
    """Test suite for GCP Gatekeeper evaluating in-toto v1.0 DSSE attestations."""

    def test_admit_valid_smt_proved_attestation(self, tmp_path):
        gen = AttestationBundleGenerator()
        artifact_content = "define i32 @safe_func() { ret i32 0 }"
        digest = gen.compute_content_digests(artifact_content)

        bundle = gen.generate_bundle(
            target_name="service_core",
            artifacts=[{"name": "service_core.ll", "digest": digest}],
            formal_verdict="PROVED",
            zero_divergence_proved=True,
        )

        att_file = tmp_path / "valid_bundle.json"
        att_file.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

        gatekeeper = GCPGatekeeper()
        decision = gatekeeper.evaluate_admission_decision(
            str(att_file),
            target_artifact_name="service_core.ll",
            expected_sha256=digest["sha256"],
        )

        assert decision["admitted"] is True
        assert decision["decision"] == "ADMIT"
        assert decision["checks"]["signature_valid"] is True
        assert decision["checks"]["formal_proofs_verified"] is True
        assert decision["checks"]["zero_divergence_proved"] is True
        assert decision["checks"]["hash_matched"] is True

    def test_block_tampered_or_unproved_attestation(self, tmp_path):
        gen = AttestationBundleGenerator()
        bundle = gen.generate_bundle(
            target_name="unsafe_service",
            artifacts=[],
            formal_verdict="FAILED",
            zero_divergence_proved=False,
        )

        att_file = tmp_path / "unproved_bundle.json"
        att_file.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

        gatekeeper = GCPGatekeeper()
        decision = gatekeeper.evaluate_admission_decision(str(att_file))

        assert decision["admitted"] is False
        assert decision["decision"] == "BLOCK"
        assert decision["checks"]["verdict"] == "FAILED"

    def test_gcp_gatekeeper_cli_invocation(self, tmp_path):
        gen = AttestationBundleGenerator()
        bundle = gen.generate_bundle(
            target_name="cli_test",
            artifacts=[],
            formal_verdict="PROVED",
            zero_divergence_proved=True,
        )
        att_file = tmp_path / "cli_bundle.json"
        att_file.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

        import subprocess
        res = subprocess.run(
            [sys.executable, "deploy/gcp/gcp_gatekeeper.py", "--verify-attestation", str(att_file)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
        assert "ADMIT (Workload Allowed)" in res.stdout


class TestK8sAdmissionWebhook:
    """Test suite for Kubernetes & GKE Validating Admission Webhook."""

    def test_validate_workload_with_proved_annotation(self):
        pod_spec = {
            "metadata": {
                "name": "crypto-vault-pod",
                "namespace": "production",
                "annotations": {
                    "ecstasy.pcd/formal-verdict": "PROVED",
                },
            }
        }
        allowed, msg = AdmissionWebhookHandler._validate_workload(pod_spec)
        assert allowed is True
        assert "admitted with formal SMT proof certificate" in msg

    def test_reject_workload_without_formal_proof(self):
        pod_spec = {
            "metadata": {
                "name": "unverified-pod",
                "namespace": "production",
                "annotations": {},
            }
        }
        allowed, msg = AdmissionWebhookHandler._validate_workload(pod_spec)
        assert allowed is False
        assert "rejected by Ecstasy PCD: Missing required" in msg

    def test_validate_workload_with_dsse_attestation(self):
        gen = AttestationBundleGenerator()
        bundle = gen.generate_bundle(
            target_name="k8s_secure_pod",
            artifacts=[],
            formal_verdict="PROVED",
            zero_divergence_proved=True,
        )
        raw_json = json.dumps(bundle)
        b64_att = base64.b64encode(raw_json.encode("utf-8")).decode("utf-8")

        pod_spec = {
            "metadata": {
                "name": "k8s-attested-pod",
                "namespace": "production",
                "annotations": {
                    "ecstasy.pcd/attestation-dsse": b64_att,
                },
            }
        }
        allowed, msg = AdmissionWebhookHandler._validate_workload(pod_spec)
        assert allowed is True
        assert "admitted with verified in-toto v1.0 DSSE attestation" in msg

    def test_system_namespace_bypass(self):
        pod_spec = {
            "metadata": {
                "name": "coredns",
                "namespace": "kube-system",
            }
        }
        allowed, msg = AdmissionWebhookHandler._validate_workload(pod_spec)
        assert allowed is True
        assert "System namespace" in msg

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_GCP_TESTS") and not Path.home().joinpath(".config/gcloud").exists(),
        reason="Google Cloud live credentials not present in environment",
    )
    def test_live_gcp_binary_authorization_lifecycle(self):
        """Live test validating Google Cloud Container Analysis and Binary Authorization API."""
        import shutil
        import subprocess
        if not shutil.which("gcloud"):
            pytest.skip("gcloud CLI not installed")

        res_auth = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
        if res_auth.returncode != 0:
            pytest.skip("gcloud not authenticated")

        script_path = Path(__file__).resolve().parent.parent / "scripts" / "test_gcp_live_e2e.py"
        assert script_path.exists(), "test_gcp_live_e2e.py script not found"

        res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        assert res.returncode == 0, f"Live GCP test failed:\n{res.stdout}\n{res.stderr}"
        assert "ALL GOOGLE CLOUD BINARY AUTHORIZATION TESTS PASSED WITH 100% SUCCESS" in res.stdout

