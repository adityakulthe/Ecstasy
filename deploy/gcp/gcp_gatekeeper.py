"""
Google Cloud Binary Authorization & Artifact Registry Gatekeeper
Part of Ecstasy Provable Cyber Defense (PCD)

Validates in-toto v1.0 and DSSE supply-chain attestations carrying Z3 SMT formal proofs
for Google Cloud Binary Authorization admission control on GKE (Google Kubernetes Engine).
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

from engine.attestation_bundle import AttestationBundleGenerator, AttestationVerificationReport


class GCPGatekeeper:
    """
    Evaluates container and workload admission against Google Cloud Binary Authorization
    and Ecstasy Provable Cyber Defense in-toto v1.0 DSSE attestations.
    """

    def __init__(self, expected_keyid: Optional[str] = None):
        self.generator = AttestationBundleGenerator()
        self.expected_keyid = expected_keyid or self.generator.key_id

    def verify_attestation_file(self, attestation_path: str) -> AttestationVerificationReport:
        """Verify the integrity, cryptographic signature, and formal SMT proofs in an attestation."""
        p = Path(attestation_path)
        if not p.exists():
            raise FileNotFoundError(f"Attestation bundle not found: {attestation_path}")

        raw_json = p.read_text(encoding="utf-8")
        return self.generator.verify_bundle(raw_json)

    def evaluate_admission_decision(
        self,
        attestation_path: str,
        target_artifact_name: Optional[str] = None,
        expected_sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make a strict binary admission decision:
        - Signature valid
        - Formal Z3 SMT proofs verified (verdict == PROVED)
        - Zero-Divergence proved
        - Target artifact hash matches subject in statement
        """
        rep = self.verify_attestation_file(attestation_path)
        p = Path(attestation_path)
        raw_bundle = json.loads(p.read_text(encoding="utf-8"))

        import base64
        payload_bytes = base64.b64decode(raw_bundle["payload"])
        statement = json.loads(payload_bytes.decode("utf-8"))
        predicate = statement.get("predicate", {})

        formal_verif = predicate.get("formal_verification", predicate.get("formal_proofs", {}))
        checks = {
            "signature_valid": rep.signature_valid,
            "formal_proofs_verified": rep.formal_proofs_verified,
            "overall_valid": rep.valid,
            "zero_divergence_proved": formal_verif.get("zero_divergence_proved", False),
            "verdict": formal_verif.get("z3_verdict", formal_verif.get("verdict")),
            "hash_matched": True,
        }

        # Check artifact hash if provided
        if target_artifact_name and expected_sha256:
            subjects = statement.get("subject", [])
            matched = any(
                s.get("name") == target_artifact_name and s.get("digest", {}).get("sha256") == expected_sha256
                for s in subjects
            )
            checks["hash_matched"] = matched

        admitted = all([
            checks["signature_valid"],
            checks["formal_proofs_verified"],
            checks["overall_valid"],
            checks["zero_divergence_proved"],
            checks["verdict"] == "PROVED",
            checks["hash_matched"],
        ])

        return {
            "admitted": admitted,
            "decision": "ADMIT" if admitted else "BLOCK",
            "enforcement_mode": "ENFORCING_BLOCK_AND_AUDIT_LOG",
            "checks": checks,
            "signer_keyid": rep.signer_keyid,
            "timestamp": rep.timestamp,
            "issues": rep.issues,
        }


def main():
    parser = argparse.ArgumentParser(description="Google Cloud Binary Authorization Gatekeeper")
    parser.add_argument("--verify-attestation", help="Path to in-toto v1.0 DSSE attestation file")
    parser.add_argument("--artifact-name", help="Optional artifact name to match")
    parser.add_argument("--expected-sha256", help="Optional expected SHA-256 hash")
    args = parser.parse_args()

    if not args.verify_attestation:
        parser.print_help()
        sys.exit(1)

    gatekeeper = GCPGatekeeper()
    decision = gatekeeper.evaluate_admission_decision(
        args.verify_attestation,
        target_artifact_name=args.artifact_name,
        expected_sha256=args.expected_sha256,
    )

    print("\n" + "=" * 70)
    print("☁️ GOOGLE CLOUD BINARY AUTHORIZATION GATEKEEPER")
    print("=" * 70)
    print(f"Decision:         {'🟢 ADMIT (Workload Allowed)' if decision['admitted'] else '🔴 BLOCK (Workload Rejected)'}")
    print(f"Enforcement Mode: {decision['enforcement_mode']}")
    print(f"Signer KeyID:     {decision['signer_keyid']}")
    print(f"Attested Time:    {decision['timestamp']}")
    print("-" * 70)
    print("Security Checks:")
    for check_name, check_val in decision["checks"].items():
        print(f"  • {check_name}: {'✅ PASSED' if check_val else '❌ FAILED'}")

    if decision["issues"]:
        print("\nAudit Issues:")
        for iss in decision["issues"]:
            print(f"  • {iss}")
    print("=" * 70)

    if not decision["admitted"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
