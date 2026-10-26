"""
Ecstasy Formal Verification & Provable Cyber Defense (PCD) Engine
Production-grade symbolic execution, hardware memory safety, post-quantum cryptography,
and translation validation for LLVM IR using Z3 SMT Solver.
"""

from .symbolic_verifier import (
    SymbolicIRVerifier,
    VerificationVerdict,
    VerificationReport,
    Counterexample,
    verify_ir_equivalence,
)
from .crypto_timing_verifier import (
    CryptoTimingVerifier,
    TimingVerdict,
    TimingAuditReport,
)
from .crypto_synthesizer import (
    CryptoSynthesizer,
    ConstantTimeSynthesisReport,
)
from .smt_vulnerability_prover import (
    SMTVulnerabilityProver,
    SecurityAuditDossier,
)
from .security_hardening import (
    SecurityHardener,
    HardeningReport,
)
from .cfi_protector import (
    CFIProtector,
    CFIReport,
)
from .attack_surface import (
    AttackSurfaceAnalyzer,
    AttackSurfaceReport,
)
from .exploit_fuzzer import (
    DifferentialExploitFuzzer,
    ExploitVerificationReport,
)
from .pqc_verifier import (
    PQCVerifier,
    PQCScheme,
    PQCAuditReport,
    PQCSynthesisReport,
)
from .hardware_safety import (
    HardwareSafetyTransformer,
    HardwareSafetyReport,
    HardwareSecurityFeature,
)
from .attestation_bundle import (
    AttestationBundleGenerator,
    AttestationVerificationReport,
)
from .speculative_verifier import (
    SpeculativeVerifier,
    SpectreVariant,
    SpeculativeAuditReport,
    SpeculativeSynthesisReport,
)
from .binary_lifter import (
    BinaryLifter,
    BinaryFormat,
    LiftedIRModule,
    BinaryAuditReport,
)
from .self_healing_guard import (
    SelfHealingGuard,
    HealingAction,
    SelfHealingResult,
)

__all__ = [
    "SymbolicIRVerifier",
    "VerificationVerdict",
    "VerificationReport",
    "Counterexample",
    "verify_ir_equivalence",
    "CryptoTimingVerifier",
    "TimingVerdict",
    "TimingAuditReport",
    "CryptoSynthesizer",
    "ConstantTimeSynthesisReport",
    "SMTVulnerabilityProver",
    "SecurityAuditDossier",
    "SecurityHardener",
    "HardeningReport",
    "CFIProtector",
    "CFIReport",
    "AttackSurfaceAnalyzer",
    "AttackSurfaceReport",
    "DifferentialExploitFuzzer",
    "ExploitVerificationReport",
    "PQCVerifier",
    "PQCScheme",
    "PQCAuditReport",
    "PQCSynthesisReport",
    "HardwareSafetyTransformer",
    "HardwareSafetyReport",
    "HardwareSecurityFeature",
    "AttestationBundleGenerator",
    "AttestationVerificationReport",
    "SpeculativeVerifier",
    "SpectreVariant",
    "SpeculativeAuditReport",
    "SpeculativeSynthesisReport",
    "BinaryLifter",
    "BinaryFormat",
    "LiftedIRModule",
    "BinaryAuditReport",
    "SelfHealingGuard",
    "HealingAction",
    "SelfHealingResult",
]
