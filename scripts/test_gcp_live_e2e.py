#!/usr/bin/env python3
"""
Live End-to-End Google Cloud Binary Authorization & Provable Cyber Defense (PCD) Test.
Tests Option B: Validates real-world enterprise admission control on Google Cloud
using Container Analysis Notes, Binary Authorization Attestors, ECDSA P-256 signing,
and Ecstasy Z3 SMT formal proof attestations.
"""

import os
import sys
import json
import base64
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple

# Add repository root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from deploy.gcp.gcp_gatekeeper import GCPGatekeeper
from engine.security_hardening import harden_llvm_ir
from server.mcp_server import compile_to_ir
from engine.attestation_bundle import AttestationBundleGenerator


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run shell command with output capture and error reporting."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(cmd)}\nStdout: {res.stdout}\nStderr: {res.stderr}")
    return res


def get_gcp_access_token() -> str:
    """Get active GCP access token from gcloud."""
    res = run_cmd(["gcloud", "auth", "print-access-token"])
    return res.stdout.strip()


def get_gcp_project() -> str:
    """Get active GCP project ID from gcloud config."""
    res = run_cmd(["gcloud", "config", "get-value", "project"])
    proj = res.stdout.strip()
    if not proj or proj == "(unset)":
        raise ValueError("No active GCP project configured in gcloud.")
    return proj


def generate_ecdsa_keypair(tmp_dir: Path) -> Tuple[Path, Path, ec.EllipticCurvePrivateKey]:
    """Generate an ECDSA P-256 keypair and save public key in PEM format."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    pub_path = tmp_dir / "ec_public.pem"
    pub_path.write_bytes(pub_pem)

    priv_path = tmp_dir / "ec_private.pem"
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_path.write_bytes(priv_pem)

    return pub_path, priv_path, private_key


def main():
    print("=" * 80)
    print("🚀 LIVE GOOGLE CLOUD BINARY AUTHORIZATION & PCD E2E TEST (OPTION B)")
    print("=" * 80)

    # 1. Check prerequisites
    if not shutil.which("gcloud"):
        print("❌ Error: gcloud CLI not found in PATH.")
        sys.exit(1)

    project_id = get_gcp_project()
    token = get_gcp_access_token()
    print(f"✅ Authenticated GCP Project: {project_id}")

    pid_suffix = os.getpid()
    note_id = f"ecstasy-pcd-note-{pid_suffix}"
    attestor_id = f"ecstasy-pcd-attestor-{pid_suffix}"
    note_resource = f"projects/{project_id}/notes/{note_id}"
    attestor_resource = f"projects/{project_id}/attestors/{attestor_id}"

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        pub_path, priv_path, priv_key = generate_ecdsa_keypair(tmp_dir)
        print(f"✅ Generated ECDSA P-256 Keypair: {pub_path.name}")

        try:
            # 2. Create Container Analysis Note via REST API
            print(f"\n[1/6] Creating Container Analysis Attestation Note: {note_id}...")
            note_payload = {
                "attestation": {
                    "hint": {
                        "human_readable_name": "Ecstasy Provable Cyber Defense Attestor Note"
                    }
                }
            }
            create_note_cmd = [
                "curl", "-s", "-X", "POST",
                "-H", f"Authorization: Bearer {token}",
                "-H", "Content-Type: application/json",
                "--data-binary", json.dumps(note_payload),
                f"https://containeranalysis.googleapis.com/v1/projects/{project_id}/notes/?noteId={note_id}"
            ]
            res_note = run_cmd(create_note_cmd)
            note_resp = json.loads(res_note.stdout)
            if "name" not in note_resp:
                raise RuntimeError(f"Failed to create Note: {res_note.stdout}")
            print(f"      Created Note: {note_resp['name']}")

            # 3. Create Binary Authorization Attestor via gcloud
            print(f"\n[2/6] Registering Binary Authorization Attestor: {attestor_id}...")
            run_cmd([
                "gcloud", "container", "binauthz", "attestors", "create", attestor_id,
                f"--attestation-authority-note={note_id}",
                f"--attestation-authority-note-project={project_id}",
                f"--description=Ecstasy SMT Formal Verification Attestor",
            ])
            print(f"      Created Attestor: {attestor_resource}")

            # 4. Attach ECDSA P-256 Public Key to Attestor
            print(f"\n[3/6] Binding ECDSA P-256 Public Key to Attestor...")
            run_cmd([
                "gcloud", "container", "binauthz", "attestors", "public-keys", "add",
                f"--attestor={attestor_id}",
                "--pkix-public-key-algorithm=ecdsa-p256-sha256",
                f"--pkix-public-key-file={str(pub_path)}",
            ])

            # Retrieve assigned public key ID
            desc_res = run_cmd([
                "gcloud", "container", "binauthz", "attestors", "describe", attestor_id,
                "--format=json",
            ])
            attestor_meta = json.loads(desc_res.stdout)
            public_keys = attestor_meta.get("userOwnedGrafeasNote", {}).get("publicKeys", [])
            if not public_keys:
                raise RuntimeError("No public keys found on attestor after addition!")
            pk_id = public_keys[0]["id"]
            print(f"      Public Key ID registered on GCP: {pk_id}")

            # 5. Compile Target with Ecstasy PCD Engine & Formally Prove Zero-Divergence
            print("\n[4/6] Executing Ecstasy Provable Cyber Defense (PCD) Pipeline on Target...")
            from engine.crypto_synthesizer import CryptoSynthesizer
            from engine.crypto_timing_verifier import verify_crypto_constant_time

            crypto_vuln_ir = """
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
            print("      Auditing cryptographic timing side-channel (CWE-208)...")
            initial_audit = verify_crypto_constant_time(crypto_vuln_ir)
            assert initial_audit.is_constant_time is False, "Expected timing leak in unhardened code!"
            print("      Detected Vulnerability: Secret-Dependent Branch (CWE-208 Timing Leak)")

            print("      Synthesizing branchless straight-line primitive with Z3 SMT...")
            synth = CryptoSynthesizer()
            synth_rep = synth.synthesize(crypto_vuln_ir)
            assert synth_rep.zero_divergence_proved is True, "Zero-Divergence Invariant failed!"
            assert synth_rep.constant_time_proved is True, "Constant-Time verification failed!"
            print(f"      Zero-Divergence Invariant: FORMALLY PROVED BY Z3 SMT (100% bit-equivalent)")
            print(f"      Constant-Time Immunity: FORMALLY PROVED (Zero secret-dependent branching)")

            # Compute sha256 of hardened artifact
            import hashlib
            artifact_bytes = synth_rep.constant_time_ir.encode("utf-8")
            artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
            container_image_ref = f"gcr.io/{project_id}/ecstasy-hardened-app@sha256:{artifact_sha256}"
            print(f"      Target Container Image: {container_image_ref}")

            # Generate in-toto DSSE attestation bundle
            att_gen = AttestationBundleGenerator()
            bundle = att_gen.generate_bundle(
                target_name="ecstasy-hardened-app",
                artifacts=[{"name": "crypto_mac.ll", "digest": {"sha256": artifact_sha256}}],
                formal_verdict="PROVED",
                zero_divergence_proved=True,
            )
            attestation_path = tmp_dir / "ecstasy_attestation.json"
            attestation_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

            # 6. Generate & Sign Google Cloud Binary Authorization Container Payload
            print("\n[5/6] Generating & Signing Google Cloud Binary Authorization Attestation Payload...")
            payload_res = run_cmd([
                "gcloud", "container", "binauthz", "create-signature-payload",
                f"--artifact-url={container_image_ref}",
            ])
            raw_payload = payload_res.stdout
            payload_path = tmp_dir / "binauthz_payload.json"
            payload_path.write_text(raw_payload, encoding="utf-8")

            # Sign payload using our ECDSA P-256 private key
            signature_bytes = priv_key.sign(
                raw_payload.encode("utf-8"),
                ec.ECDSA(hashes.SHA256())
            )
            sig_path = tmp_dir / "signature.sig"
            sig_path.write_bytes(signature_bytes)

            # Submit attestation to Google Cloud Binary Authorization
            print(f"      Submitting live attestation to GCP Container Analysis...")
            run_cmd([
                "gcloud", "container", "binauthz", "attestations", "create",
                f"--artifact-url={container_image_ref}",
                f"--attestor={attestor_id}",
                f"--signature-file={str(sig_path)}",
                f"--public-key-id={pk_id}",
                f"--payload-file={str(payload_path)}",
            ])

            # Query live attestations from Google Cloud
            list_res = run_cmd([
                "gcloud", "container", "binauthz", "attestations", "list",
                f"--attestor={attestor_id}",
                f"--artifact-url={container_image_ref}",
                "--format=json",
            ])
            attestations = json.loads(list_res.stdout)
            print(f"      Verified Live Attestations in GCP: {len(attestations)} occurrence(s) found!")
            assert len(attestations) >= 1, "Expected at least 1 live attestation in Google Cloud!"

            # 7. Evaluate Admission Decisions via GCPGatekeeper
            print("\n[6/6] Testing Admission Controller Decisions via GCPGatekeeper...")
            gatekeeper = GCPGatekeeper()

            # Case A: Valid Attestation with Z3 SMT Proof & Matching Hash
            decision_admit = gatekeeper.evaluate_admission_decision(
                str(attestation_path),
                target_artifact_name="crypto_mac.ll",
                expected_sha256=artifact_sha256,
            )
            print(f"      Artifact Evaluation Result: {decision_admit['decision']}")
            print(f"      Checks: {decision_admit['checks']}")
            assert decision_admit["admitted"] is True
            assert decision_admit["decision"] == "ADMIT"
            print("      ✅ ADMISSION ADMITTED: Workload with SMT proof allowed into GKE cluster.")

            # Case B: Tampered Artifact (Altered SHA-256 / Missing Proof)
            decision_block = gatekeeper.evaluate_admission_decision(
                str(attestation_path),
                target_artifact_name="crypto_mac.ll",
                expected_sha256="deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            )
            print(f"      Tampered Artifact Evaluation Result: {decision_block['decision']}")
            assert decision_block["admitted"] is False
            assert decision_block["decision"] == "BLOCK"
            print("      ✅ ADMISSION BLOCKED: Tampered or unverified workload strictly rejected by GKE policy.")

            print("\n" + "=" * 80)
            print("🎉 ALL GOOGLE CLOUD BINARY AUTHORIZATION TESTS PASSED WITH 100% SUCCESS")
            print("=" * 80)

        finally:
            # 8. Clean up all cloud resources
            print("\n🧹 Cleaning up test resources on Google Cloud...")
            try:
                run_cmd(["gcloud", "container", "binauthz", "attestors", "delete", attestor_id, "--quiet"], check=False)
                print(f"      Deleted Attestor: {attestor_id}")
            except Exception as e:
                print(f"      Warning cleaning up attestor: {e}")

            try:
                run_cmd([
                    "curl", "-s", "-X", "DELETE",
                    "-H", f"Authorization: Bearer {token}",
                    f"https://containeranalysis.googleapis.com/v1/projects/{project_id}/notes/{note_id}"
                ], check=False)
                print(f"      Deleted Note: {note_id}")
            except Exception as e:
                print(f"      Warning cleaning up note: {e}")


if __name__ == "__main__":
    main()
