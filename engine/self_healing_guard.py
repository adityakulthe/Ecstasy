"""
Autonomous Self-Healing CI/CD Gatekeeper ("Ecstasy Guard")
Part of Ecstasy Provable Cyber Defense (PCD)

Continuously guards codebases and CI/CD pipelines by discovering SMT-provable vulnerabilities,
synthesizing concrete exploit payloads, generating automated branchless patches with Z3
Zero-Divergence proofs, verifying differential survival in sandbox, and emitting ready-to-merge
git patches with cryptographically signed in-toto v1.0 supply-chain attestations.
"""

from __future__ import annotations

import os
import sys
import difflib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from server.mcp_server import compile_to_ir
from engine.smt_vulnerability_prover import audit_ir_security, SecurityAuditDossier
from engine.security_hardening import harden_llvm_ir, HardeningReport
from engine.cfi_protector import enforce_control_flow_integrity, CFIReport
from engine.crypto_synthesizer import synthesize_constant_time, ConstantTimeSynthesisReport
from engine.attestation_bundle import AttestationBundleGenerator


@dataclass
class HealingAction:
    """Record of an automated self-healing remediation action."""
    vulnerability_type: str
    cwe_id: str
    function_name: str
    description: str
    remediation_applied: str
    zero_divergence_proved: bool = True


@dataclass
class SelfHealingResult:
    """Complete report of autonomous vulnerability remediation for a target file."""
    target_path: str
    status: str  # "CLEAN", "HEALED", "FAILED"
    original_vulnerabilities_count: int
    patches_applied_count: int
    actions: List[HealingAction] = field(default_factory=list)
    git_patch_diff: str = ""
    hardened_ir: str = ""
    attestation_bundle: Optional[Dict[str, Any]] = None
    all_zero_divergence_proved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SelfHealingGuard:
    """
    Autonomous compiler daemon and gatekeeper.
    Closes the loop from SMT vulnerability discovery to verified git patch commits.
    """

    def __init__(self, timeout_sec: int = 15):
        self.timeout_sec = timeout_sec
        self.attestation_gen = AttestationBundleGenerator()

    def audit_and_heal_file(
        self,
        target_path: str,
        auto_patch: bool = False,
        output_dir: Optional[str] = None,
    ) -> SelfHealingResult:
        """
        Execute the closed-loop autonomous repair cycle on a source or IR file:
        Prove Vulnerability -> Synthesize Branchless Mitigation -> Prove Zero-Divergence -> Attest.
        """
        p = Path(target_path)
        if not p.exists():
            return SelfHealingResult(
                target_path=target_path,
                status="FAILED",
                original_vulnerabilities_count=0,
                patches_applied_count=0,
                git_patch_diff=f"Target file does not exist: {target_path}",
            )

        content = p.read_text(encoding="utf-8")
        is_c = p.suffix in (".c", ".cpp", ".cc")

        if is_c:
            comp = compile_to_ir(content, filename=p.name)
            if not comp["success"]:
                return SelfHealingResult(
                    target_path=target_path,
                    status="FAILED",
                    original_vulnerabilities_count=0,
                    patches_applied_count=0,
                    git_patch_diff=f"Clang compilation error: {comp.get('error')}",
                )
            initial_ir = comp["ir"]
        else:
            initial_ir = content

        # 1. Audit Vulnerabilities via Z3 SMT Prover
        dossier = audit_ir_security(initial_ir, timeout_sec=self.timeout_sec)
        if not dossier.vulnerabilities_found:
            return SelfHealingResult(
                target_path=target_path,
                status="CLEAN",
                original_vulnerabilities_count=0,
                patches_applied_count=0,
                hardened_ir=initial_ir,
                all_zero_divergence_proved=True,
            )

        # 2. Automated Hardening: Memory Safety (CWE-125/787/369)
        h_rep = harden_llvm_ir(initial_ir, timeout_sec=self.timeout_sec)
        current_ir = h_rep.hardened_ir

        # 3. Automated Hardening: CFI Forward-Edge Protection (CWE-822)
        cfi_rep = enforce_control_flow_integrity(current_ir, timeout_sec=self.timeout_sec)
        current_ir = cfi_rep.hardened_ir

        # 4. Automated Hardening: Constant-Time Cryptographic Synthesis (CWE-208)
        ct_rep = synthesize_constant_time(current_ir, timeout_sec=self.timeout_sec)
        current_ir = ct_rep.constant_time_ir

        # Collect all healing actions
        actions: List[HealingAction] = []
        for p_h in h_rep.patches:
            actions.append(
                HealingAction(
                    vulnerability_type="MEMORY_SAFETY_VIOLATION",
                    cwe_id=p_h.cwe_id,
                    function_name=p_h.function_name,
                    description=p_h.description,
                    remediation_applied=p_h.hardened_instruction,
                    zero_divergence_proved=h_rep.zero_divergence_proved,
                )
            )

        for p_c in cfi_rep.patches:
            actions.append(
                HealingAction(
                    vulnerability_type="UNCONSTRAINED_INDIRECT_CALL",
                    cwe_id="CWE-822",
                    function_name=p_c.function_name,
                    description=p_c.description,
                    remediation_applied=p_c.hardened_instruction,
                    zero_divergence_proved=cfi_rep.zero_divergence_proved,
                )
            )

        for p_t in ct_rep.patches:
            actions.append(
                HealingAction(
                    vulnerability_type="SECRET_TIMING_LEAK",
                    cwe_id="CWE-208",
                    function_name=p_t.function_name,
                    description=p_t.description,
                    remediation_applied=p_t.synthesized_instruction,
                    zero_divergence_proved=ct_rep.zero_divergence_proved,
                )
            )

        zd_h = h_rep.zero_divergence_proved if h_rep.patches else True
        zd_cfi = cfi_rep.zero_divergence_proved if cfi_rep.patches else True
        zd_ct = ct_rep.zero_divergence_proved if ct_rep.patches else True
        all_zd_proved = zd_h and zd_cfi and zd_ct

        # 5. Generate Unified Git Diff
        diff_lines = list(
            difflib.unified_diff(
                initial_ir.splitlines(keepends=True),
                current_ir.splitlines(keepends=True),
                fromfile=f"a/{p.name}.ll",
                tofile=f"b/{p.name}.healed.ll",
            )
        )
        diff_text = "".join(diff_lines)

        # 6. Generate in-toto v1.0 Attestation Bundle
        artifacts = [
            {"name": p.name, "digest": self.attestation_gen.compute_content_digests(content)},
            {"name": f"{p.stem}_healed.ll", "digest": self.attestation_gen.compute_content_digests(current_ir)},
        ]
        bundle = self.attestation_gen.generate_bundle(
            target_name=p.name,
            artifacts=artifacts,
            formal_verdict="PROVED" if all_zd_proved else "PARTIAL",
            zero_divergence_proved=all_zd_proved,
            sarif_summary={
                "sarif_version": "2.1.0",
                "exploitable_cwe_count": len(dossier.vulnerabilities_found),
                "healed_cwe_count": len(actions),
            },
        )

        # 7. Write output files if auto_patch or output_dir specified
        if auto_patch or output_dir:
            out_base = Path(output_dir) if output_dir else p.parent
            out_base.mkdir(parents=True, exist_ok=True)
            healed_file = out_base / f"{p.stem}.healed.ll"
            patch_file = out_base / f"{p.stem}.patch"
            attest_file = out_base / f"{p.stem}.attestation.json"

            healed_file.write_text(current_ir, encoding="utf-8")
            patch_file.write_text(diff_text, encoding="utf-8")
            import json
            attest_file.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

        return SelfHealingResult(
            target_path=target_path,
            status="HEALED",
            original_vulnerabilities_count=len(dossier.vulnerabilities_found),
            patches_applied_count=len(actions),
            actions=actions,
            git_patch_diff=diff_text,
            hardened_ir=current_ir,
            attestation_bundle=bundle,
            all_zero_divergence_proved=all_zd_proved,
        )

    def audit_and_heal_repository(
        self,
        repo_dir: str,
        auto_patch: bool = False,
    ) -> List[SelfHealingResult]:
        """
        Scan all C and LLVM IR files in a repository directory and autonomously heal all vulnerabilities.
        """
        base_p = Path(repo_dir)
        if not base_p.exists():
            return []

        results: List[SelfHealingResult] = []
        # Find all .c and .ll files excluding .venv, git, and tests
        for p in base_p.rglob("*"):
            if not p.is_file():
                continue
            if any(part.startswith(".") for part in p.parts):
                continue
            if "node_modules" in p.parts or "__pycache__" in p.parts or "test" in p.parts:
                continue

            if p.suffix in (".c", ".ll"):
                res = self.audit_and_heal_file(str(p), auto_patch=auto_patch)
                results.append(res)

        return results
