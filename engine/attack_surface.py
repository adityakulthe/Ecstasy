"""
MITRE ATT&CK Matrix & Cyber Attack Surface Synthesizer
Part of Ecstasy Provable Cyber Defense (PCD)

Maps SMT-proven vulnerabilities and side channels to the MITRE ATT&CK Enterprise Matrix,
computes quantitative Attack Surface Metrics, and generates ATT&CK Navigator v4.3 layers
and NIST SP 800-218 (SSDF) / ISO 26262 ASIL-D compliance matrices.
"""

from __future__ import annotations

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

from engine.smt_vulnerability_prover import SecurityAuditDossier, VulnerabilityFinding
from engine.crypto_timing_verifier import TimingAuditReport


# MITRE ATT&CK Enterprise Mapping Dictionary for low-level CWE vulnerabilities
ATTACK_CWE_MAPPING: Dict[str, Dict[str, str]] = {
    "CWE-125": {
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "comment": "Buffer Out-of-Bounds Read: leaks cryptographic secrets or memory layout (ASLR bypass)",
    },
    "CWE-787": {
        "technique_id": "T1068",
        "technique_name": "Exploitation for Privilege Escalation",
        "tactic": "Privilege Escalation",
        "comment": "Out-of-Bounds Write: stack or heap corruption leading to arbitrary code execution",
    },
    "CWE-369": {
        "technique_id": "T1499",
        "technique_name": "Endpoint Denial of Service",
        "tactic": "Impact",
        "comment": "Divide by Zero: triggers unhandled CPU exception / SIGFPE causing service crash",
    },
    "CWE-190": {
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "comment": "Integer Overflow in memory allocation sizing leading to heap buffer overflow",
    },
    "CWE-415": {
        "technique_id": "T1068",
        "technique_name": "Exploitation for Privilege Escalation",
        "tactic": "Privilege Escalation",
        "comment": "Double-Free: memory allocator metadata corruption leading to arbitrary write",
    },
    "CWE-416": {
        "technique_id": "T1068",
        "technique_name": "Exploitation for Privilege Escalation",
        "tactic": "Privilege Escalation",
        "comment": "Use-After-Free: stale heap pointer dereference enabling control-flow hijacking",
    },
    "CWE-208": {
        "technique_id": "T1005",
        "technique_name": "Data from Local System",
        "tactic": "Collection",
        "comment": "Observable Timing Discrepancy: secret-dependent branch leaks cryptographic key bits",
    },
    "CWE-385": {
        "technique_id": "T1005",
        "technique_name": "Data from Local System",
        "tactic": "Collection",
        "comment": "Covert Timing Channel: secret-dependent table lookup causes cache-line timing leaks",
    },
}


@dataclass
class AttackTechniqueMapping:
    """Individual technique mapped to an SMT vulnerability finding."""
    technique_id: str
    technique_name: str
    tactic: str
    cwe_id: str
    function_name: str
    severity: str
    cvss_score: float
    comment: str


@dataclass
class AttackSurfaceReport:
    """Comprehensive Attack Surface & MITRE ATT&CK analysis report."""
    attack_surface_score: float  # 0.0 to 100.0 (lower is safer)
    vulnerabilities_count: int
    techniques_count: int
    mitigation_coverage_pct: float
    nist_ssdf_compliant: bool
    iso_26262_compliant: bool
    techniques: List[AttackTechniqueMapping] = field(default_factory=list)
    navigator_layer: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_surface_score": self.attack_surface_score,
            "vulnerabilities_count": self.vulnerabilities_count,
            "techniques_count": self.techniques_count,
            "mitigation_coverage_pct": self.mitigation_coverage_pct,
            "nist_ssdf_compliant": self.nist_ssdf_compliant,
            "iso_26262_compliant": self.iso_26262_compliant,
            "techniques": [asdict(t) for t in self.techniques],
            "navigator_layer": self.navigator_layer,
        }


class AttackSurfaceAnalyzer:
    """
    Synthesizes cyber attack surface profiles, maps findings to MITRE ATT&CK,
    and produces ATT&CK Navigator v4.3 visualization layers.
    """

    def analyze(
        self,
        dossier: SecurityAuditDossier,
        timing_report: Optional[TimingAuditReport] = None,
        layer_name: str = "Ecstasy Provable Cyber Defense Layer",
    ) -> AttackSurfaceReport:
        """
        Analyze an SMT security dossier and timing report to produce an ATT&CK Matrix report.
        """
        mappings: List[AttackTechniqueMapping] = []
        cwe_seen = set()

        for v in dossier.vulnerabilities_found:
            base_cwe = v.cwe_id.split("/")[0].strip()
            meta = ATTACK_CWE_MAPPING.get(base_cwe, {
                "technique_id": "T1190",
                "technique_name": "Exploit Public-Facing Application",
                "tactic": "Initial Access",
                "comment": v.description,
            })
            mappings.append(
                AttackTechniqueMapping(
                    technique_id=meta["technique_id"],
                    technique_name=meta["technique_name"],
                    tactic=meta["tactic"],
                    cwe_id=v.cwe_id,
                    function_name=v.function_name,
                    severity=v.severity,
                    cvss_score=v.cvss_score,
                    comment=meta["comment"],
                )
            )
            cwe_seen.add(base_cwe)

        if timing_report and not timing_report.is_constant_time:
            for viol in timing_report.violations:
                cwe_key = viol.cwe_id
                meta = ATTACK_CWE_MAPPING.get(cwe_key, {
                    "technique_id": "T1005",
                    "technique_name": "Data from Local System",
                    "tactic": "Collection",
                    "comment": viol.description,
                })
                mappings.append(
                    AttackTechniqueMapping(
                        technique_id=meta["technique_id"],
                        technique_name=meta["technique_name"],
                        tactic=meta["tactic"],
                        cwe_id=cwe_key,
                        function_name=viol.function_name,
                        severity="HIGH",
                        cvss_score=7.4,
                        comment=meta["comment"],
                    )
                )
                cwe_seen.add(cwe_key)

        unique_techniques = {m.technique_id for m in mappings}
        
        # Calculate Attack Surface Score: sum of CVSS / 100 normalized
        raw_score = sum(m.cvss_score for m in mappings)
        attack_surface_score = min(100.0, round(raw_score * 1.5, 1))

        # Mitigation coverage: automated hardening patches exist for CWE-125, CWE-787, CWE-369, CWE-208, CWE-14
        mitigatable_cwes = {"CWE-125", "CWE-787", "CWE-369", "CWE-208", "CWE-14"}
        mitigatable_count = sum(1 for m in mappings if any(mc in m.cwe_id for mc in mitigatable_cwes))
        coverage_pct = round((mitigatable_count / len(mappings) * 100.0) if mappings else 100.0, 1)

        # Standards compliance
        nist_compliant = len(mappings) == 0 or coverage_pct == 100.0
        iso_compliant = len(mappings) == 0

        # Build ATT&CK Navigator v4.3 Layer
        navigator_layer = self._generate_navigator_layer(mappings, layer_name=layer_name)

        return AttackSurfaceReport(
            attack_surface_score=attack_surface_score,
            vulnerabilities_count=len(mappings),
            techniques_count=len(unique_techniques),
            mitigation_coverage_pct=coverage_pct,
            nist_ssdf_compliant=nist_compliant,
            iso_26262_compliant=iso_compliant,
            techniques=mappings,
            navigator_layer=navigator_layer,
        )

    def _generate_navigator_layer(
        self,
        mappings: List[AttackTechniqueMapping],
        layer_name: str,
    ) -> Dict[str, Any]:
        """Construct a valid MITRE ATT&CK Navigator v4.3 JSON layer."""
        tech_entries: List[Dict[str, Any]] = []
        tech_map: Dict[str, List[AttackTechniqueMapping]] = {}

        for m in mappings:
            tech_map.setdefault(m.technique_id, []).append(m)

        for tid, items in tech_map.items():
            max_cvss = max(i.cvss_score for i in items)
            # Normalize color from green (#2ecc71) for low to red (#e74c3c) for critical
            color = "#e74c3c" if max_cvss >= 9.0 else "#e67e22" if max_cvss >= 7.0 else "#f1c40f"
            comments = " | ".join(f"{i.cwe_id} in @{i.function_name}: {i.comment}" for i in items)

            tech_entries.append({
                "techniqueID": tid,
                "score": max_cvss,
                "color": color,
                "comment": comments,
                "enabled": True,
            })

        return {
            "name": layer_name,
            "versions": {
                "attack": "15",
                "navigator": "4.3",
                "layer": "4.3",
            },
            "domain": "enterprise-attack",
            "description": "Formally synthesized attack surface layer generated by Ecstasy Provable Cyber Defense.",
            "gradient": {
                "colors": ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
                "minValue": 0.0,
                "maxValue": 10.0,
            },
            "techniques": tech_entries,
        }


def analyze_attack_surface(
    dossier: SecurityAuditDossier,
    timing_report: Optional[TimingAuditReport] = None,
    layer_name: str = "Ecstasy Provable Cyber Defense Layer",
) -> AttackSurfaceReport:
    """Convenience helper to analyze attack surface and export ATT&CK Matrix layer."""
    analyzer = AttackSurfaceAnalyzer()
    return analyzer.analyze(dossier, timing_report=timing_report, layer_name=layer_name)
