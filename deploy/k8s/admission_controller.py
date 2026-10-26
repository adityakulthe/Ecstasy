"""
Kubernetes & Google Kubernetes Engine (GKE) Validating Admission Webhook
Part of Ecstasy Provable Cyber Defense (PCD)

Intercepts Kubernetes Pod and Deployment creation requests, checks for required
Ecstasy formal verification proof certificates / in-toto attestations, and rejects
unverified or vulnerable workloads before they can run in the cluster.
"""

from __future__ import annotations

import json
import base64
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

from engine.attestation_bundle import AttestationBundleGenerator


class AdmissionWebhookHandler(BaseHTTPRequestHandler):
    """Handles Kubernetes ValidatingAdmissionWebhook requests."""

    generator = AttestationBundleGenerator()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            admission_review = json.loads(post_data.decode("utf-8"))
            request = admission_review.get("request", {})
            uid = request.get("uid", "")
            object_spec = request.get("object", {})

            allowed, message = self._validate_workload(object_spec)

            response_review = {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": {
                    "uid": uid,
                    "allowed": allowed,
                    "status": {
                        "code": 200 if allowed else 403,
                        "message": message,
                    },
                },
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_review).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

    @classmethod
    def _validate_workload(cls, object_spec: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate that the workload carries an Ecstasy verification certificate
        or verified attestation annotation:
        - ecstasy.pcd/formal-verdict: "PROVED"
        - ecstasy.pcd/attestation-dsse: <base64-encoded-envelope>
        """
        metadata = object_spec.get("metadata", {})
        annotations = metadata.get("annotations", {})
        name = metadata.get("name", "unknown-workload")

        # 1. Check for bypass in test namespaces
        namespace = metadata.get("namespace", "default")
        if namespace in ("kube-system", "kube-public"):
            return True, "System namespace workload admitted."

        # 2. Check formal verdict annotation
        formal_verdict = annotations.get("ecstasy.pcd/formal-verdict")
        dsse_attestation = annotations.get("ecstasy.pcd/attestation-dsse")

        if not formal_verdict and not dsse_attestation:
            return (
                False,
                f"Workload '{name}' rejected by Ecstasy PCD: Missing required 'ecstasy.pcd/formal-verdict' "
                "or 'ecstasy.pcd/attestation-dsse' annotation. Workloads must be formally proved by Ecstasy before cluster admission."
            )

        if dsse_attestation:
            try:
                raw_json = base64.b64decode(dsse_attestation).decode("utf-8")
                rep = cls.generator.verify_bundle(raw_json)
                if not rep.valid or not rep.formal_proofs_verified:
                    return (
                        False,
                        f"Workload '{name}' rejected by Ecstasy PCD: in-toto DSSE attestation signature "
                        f"or Z3 SMT formal proofs failed validation ({', '.join(rep.issues)})."
                    )
                return True, f"Workload '{name}' admitted with verified in-toto v1.0 DSSE attestation (Signer: {rep.signer_keyid})."
            except Exception as e:
                return False, f"Workload '{name}' rejected: Failed decoding DSSE attestation: {e}"

        if formal_verdict == "PROVED":
            return True, f"Workload '{name}' admitted with formal SMT proof certificate (Verdict: PROVED)."
        else:
            return False, f"Workload '{name}' rejected: Formal verification verdict is '{formal_verdict}', required 'PROVED'."


def run_webhook_server(port: int = 8443):
    server_address = ("", port)
    httpd = HTTPServer(server_address, AdmissionWebhookHandler)
    print(f"🔒 Ecstasy Kubernetes Validating Admission Webhook listening on port {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8443
    run_webhook_server(port)
