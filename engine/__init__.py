"""
Ecstasy Formal Verification Engine
Production-grade symbolic execution and translation validator for LLVM IR using Z3 SMT Solver.
"""

from .symbolic_verifier import (
    SymbolicIRVerifier,
    VerificationVerdict,
    VerificationReport,
    Counterexample,
    verify_ir_equivalence,
)

__all__ = [
    "SymbolicIRVerifier",
    "VerificationVerdict",
    "VerificationReport",
    "Counterexample",
    "verify_ir_equivalence",
]
