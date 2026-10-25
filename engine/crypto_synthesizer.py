"""
Automated Cryptographic Constant-Time Synthesizer & Branchless De-Tainter
Part of Ecstasy Provable Cyber Defense (PCD)

Automatically transforms secret-dependent branching routines (CWE-208) into
constant-time, branchless straight-line LLVM IR using SMT-verified conditional
selects and bitwise multiplexers, formally proving the Zero-Divergence Invariant
and Side-Channel Immunity with Z3.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict

try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

from engine.symbolic_verifier import SymbolicIRVerifier, VerificationVerdict
from engine.crypto_timing_verifier import CryptoTimingVerifier, TimingVerdict, TimingAuditReport


@dataclass
class ConstantTimePatch:
    """Record of an automated branchless constant-time synthesis transformation."""
    function_name: str
    leak_type: str
    original_branch: str
    synthesized_instruction: str
    description: str


@dataclass
class ConstantTimeSynthesisReport:
    """Audit report for automated constant-time cryptographic synthesis."""
    original_ir: str
    constant_time_ir: str
    patches: List[ConstantTimePatch] = field(default_factory=list)
    zero_divergence_proved: bool = False
    constant_time_proved: bool = False
    verification_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patches_count": len(self.patches),
            "zero_divergence_proved": self.zero_divergence_proved,
            "constant_time_proved": self.constant_time_proved,
            "verification_output": self.verification_output,
            "patches": [asdict(p) for p in self.patches],
            "constant_time_ir": self.constant_time_ir,
        }


class CryptoSynthesizer:
    """
    Automated compiler engine that de-taints cryptographic secrets by replacing
    timing-vulnerable branches with constant-time select/bitwise primitives.
    """

    def __init__(self, timeout_sec: int = 15):
        self.timeout_sec = timeout_sec
        self.verifier = SymbolicIRVerifier(timeout_sec=timeout_sec)
        self.timing_verifier = CryptoTimingVerifier(timeout_sec=timeout_sec)

    def synthesize(
        self,
        ir_text: str,
        secret_params: Optional[List[str]] = None,
    ) -> ConstantTimeSynthesisReport:
        """
        Scan LLVM IR for timing side channels, synthesize branchless constant-time equivalents,
        and formally prove semantic zero-divergence and side-channel immunity.
        """
        initial_audit = self.timing_verifier.verify_constant_time(ir_text, secret_params=secret_params)
        if initial_audit.is_constant_time:
            return ConstantTimeSynthesisReport(
                original_ir=ir_text,
                constant_time_ir=ir_text,
                patches=[],
                zero_divergence_proved=True,
                constant_time_proved=True,
                verification_output="Code is already constant-time; zero transformations needed.",
            )

        funcs = self.verifier.extract_functions(ir_text)
        all_patches: List[ConstantTimePatch] = []
        synthesized_ir = ir_text

        for fname, (ret_ty, raw_params, body) in funcs.items():
            func_ct_body, func_patches = self._synthesize_function(fname, ret_ty, body)
            if func_patches:
                all_patches.extend(func_patches)
                orig_fn_pattern = rf"(define\s+[^{{]*?@{re.escape(fname)}\s*\([^{{]*?\)[^{{]*?\{{)(.*?)(^\s*\}})"
                m_fn = re.search(orig_fn_pattern, synthesized_ir, re.DOTALL | re.MULTILINE)
                if m_fn:
                    synthesized_ir = (
                        synthesized_ir[: m_fn.start(2)]
                        + "\n" + func_ct_body.strip() + "\n"
                        + synthesized_ir[m_fn.end(2) :]
                    )

        # 1. Formally verify Zero-Divergence Invariant via Z3 SMT equivalence
        zero_divergence_proved = False
        ver_output = "No transformations applied."
        if all_patches and Z3_AVAILABLE:
            eq_rep = self.verifier.verify_equivalence(ir_text, synthesized_ir)
            if eq_rep.verdict == VerificationVerdict.PROVED:
                zero_divergence_proved = True
                ver_output = "Zero-Divergence Invariant Formally Proved: constant-time code is 100% equivalent to original."
            else:
                ver_output = f"Semantic check returned: {eq_rep.verdict.value} ({eq_rep.output})"

        # 2. Formally verify constant-time property on synthesized IR
        post_audit = self.timing_verifier.verify_constant_time(synthesized_ir, secret_params=secret_params)
        constant_time_proved = post_audit.is_constant_time

        return ConstantTimeSynthesisReport(
            original_ir=ir_text,
            constant_time_ir=synthesized_ir,
            patches=all_patches,
            zero_divergence_proved=zero_divergence_proved,
            constant_time_proved=constant_time_proved,
            verification_output=ver_output,
        )

    def _synthesize_function(
        self,
        fname: str,
        ret_ty: str,
        body: str,
    ) -> Tuple[str, List[ConstantTimePatch]]:
        """
        Synthesize branchless constant-time straight-line code for a branching function.
        Handles two-way branch-and-return patterns:
        br i1 %cond, label %then, label %else
        then: ret <ty> <val_then>
        else: ret <ty> <val_else>
        """
        patches: List[ConstantTimePatch] = []
        clean_lines = [l.strip() for l in body.splitlines() if l.strip() and not l.strip().startswith(";")]

        # Match conditional branch
        m_br = re.search(r"br\s+i1\s+(%[\w.]+)\s*,\s*label\s+(%?[\w.]+)\s*,\s*label\s+(%?[\w.]+)", body)
        if not m_br:
            return body, patches

        cond_reg = m_br.group(1)
        then_lbl = m_br.group(2).lstrip("%")
        else_lbl = m_br.group(3).lstrip("%")

        # Extract blocks
        blocks: Dict[str, List[str]] = {}
        curr_b = "entry"
        blocks[curr_b] = []
        for line in clean_lines:
            if line.endswith(":") and not line.startswith("%"):
                curr_b = line[:-1].strip().lstrip("%")
                blocks[curr_b] = []
            else:
                blocks[curr_b].append(line)

        # Check if then block returns a value and else block returns a value
        val_then: Optional[str] = None
        val_else: Optional[str] = None
        ret_width_ty = ret_ty or "i32"

        if then_lbl in blocks and else_lbl in blocks:
            for l in blocks[then_lbl]:
                m_ret = re.match(r"ret\s+([\w*]+)\s+(.*)", l)
                if m_ret:
                    ret_width_ty = m_ret.group(1)
                    val_then = m_ret.group(2).strip()
            for l in blocks[else_lbl]:
                m_ret = re.match(r"ret\s+([\w*]+)\s+(.*)", l)
                if m_ret:
                    ret_width_ty = m_ret.group(1)
                    val_else = m_ret.group(2).strip()

        if val_then is not None and val_else is not None:
            # Construct straight-line constant-time entry block
            entry_lines = [l for l in blocks.get("entry", []) if not l.startswith("br ")]
            select_inst = f"%_ct_mux = select i1 {cond_reg}, {ret_width_ty} {val_then}, {ret_width_ty} {val_else}"
            ret_inst = f"ret {ret_width_ty} %_ct_mux"

            new_body = "entry:\n"
            for l in entry_lines:
                new_body += f"  {l}\n"
            new_body += f"  {select_inst}\n"
            new_body += f"  {ret_inst}\n"

            patch = ConstantTimePatch(
                function_name=fname,
                leak_type="BRANCH_TIMING_LEAK",
                original_branch=m_br.group(0),
                synthesized_instruction=select_inst,
                description=f"Synthesized constant-time branchless multiplexer for @{fname} (CWE-208 mitigation)",
            )
            patches.append(patch)
            return new_body, patches

        return body, patches


def synthesize_constant_time(
    llvm_ir: str,
    secret_params: Optional[List[str]] = None,
    timeout_sec: int = 15,
) -> ConstantTimeSynthesisReport:
    """Convenience helper to synthesize constant-time cryptographic LLVM IR."""
    synth = CryptoSynthesizer(timeout_sec=timeout_sec)
    return synth.synthesize(llvm_ir, secret_params=secret_params)
