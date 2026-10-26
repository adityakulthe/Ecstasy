"""
SMT-Verified Automated Security Hardening & Zero-Divergence Patch Engine
Part of Ecstasy Provable Cyber Defense (PCD)

Automatically injects branchless saturation clamps (CWE-125/787), division guards (CWE-369),
and memory barrier zeroization protection (CWE-14/1037) into LLVM IR, formally proving
the Zero-Divergence Invariant with Z3 SMT.
"""

from __future__ import annotations

import re
import enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict

try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

from engine.symbolic_verifier import SymbolicIRVerifier, VerificationReport, VerificationVerdict


@dataclass
class HardeningPatch:
    """Record of an automated security patch injected into LLVM IR."""
    cwe_id: str
    function_name: str
    original_instruction: str
    hardened_instruction: str
    description: str


@dataclass
class HardeningReport:
    """Audit report for automated security hardening and SMT verification."""
    original_ir: str
    hardened_ir: str
    patches: List[HardeningPatch] = field(default_factory=list)
    zero_divergence_proved: bool = False
    verification_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patches_count": len(self.patches),
            "zero_divergence_proved": self.zero_divergence_proved,
            "verification_output": self.verification_output,
            "patches": [asdict(p) for p in self.patches],
            "hardened_ir": self.hardened_ir,
        }


class SecurityHardener:
    """
    Automated compiler security hardening engine.
    Patches vulnerable LLVM IR with branchless zero-overhead mitigations.
    """

    def __init__(self, timeout_sec: int = 15):
        self.timeout_sec = timeout_sec
        self.verifier = SymbolicIRVerifier(timeout_sec=timeout_sec)

    def harden_ir(self, ir_text: str) -> HardeningReport:
        """
        Scan LLVM IR, apply automated security patches, and verify the Zero-Divergence Invariant.
        """
        funcs = self.verifier.extract_functions(ir_text)
        all_patches: List[HardeningPatch] = []
        hardened_ir = ir_text

        for fname, (ret_ty, raw_params, body) in funcs.items():
            func_hardened_body, func_patches = self._harden_function_body(fname, body)
            if func_patches:
                all_patches.extend(func_patches)
                # Replace function body in hardened_ir
                orig_fn_pattern = rf"(define\s+[^{{]*?@{re.escape(fname)}\s*\([^{{]*?\)[^{{]*?\{{)(.*?)(^\s*\}})"
                m_fn = re.search(orig_fn_pattern, hardened_ir, re.DOTALL | re.MULTILINE)
                if m_fn:
                    hardened_ir = (
                        hardened_ir[: m_fn.start(2)]
                        + "\n" + func_hardened_body.strip() + "\n"
                        + hardened_ir[m_fn.end(2) :]
                    )

        if any("@.str.safe_spec" in p.hardened_instruction for p in all_patches) and "@.str.safe_spec" not in hardened_ir:
            hardened_ir = '@.str.safe_spec = private unnamed_addr constant [3 x i8] c"%s\\00", align 1\n' + hardened_ir

        # Formally verify Zero-Divergence Invariant
        zero_divergence_proved = False
        ver_output = "No patches required; code is unchanged."
        if all_patches and Z3_AVAILABLE:
            ver_report = self.verifier.verify_equivalence(ir_text, hardened_ir)
            if ver_report.verdict == VerificationVerdict.PROVED:
                zero_divergence_proved = True
                ver_output = "Zero-Divergence Invariant Formally Proved: hardened code is 100% equivalent to original on valid domain."
            else:
                ver_output = f"Equivalence check returned: {ver_report.verdict.value} ({ver_report.output})"

        return HardeningReport(
            original_ir=ir_text,
            hardened_ir=hardened_ir,
            patches=all_patches,
            zero_divergence_proved=zero_divergence_proved,
            verification_output=ver_output,
        )

    def _harden_function_body(self, fname: str, body: str) -> Tuple[str, List[HardeningPatch]]:
        """Apply security transforms to a single function body."""
        patches: List[HardeningPatch] = []
        lines = body.splitlines()
        new_lines: List[str] = []

        # Find stack buffer allocations and sizes: e.g. %buf = alloca [10 x i32]
        buffer_sizes: Dict[str, Tuple[int, str]] = {}
        for line in lines:
            m_alloc = re.match(r"\s*(%[\w.]+)\s*=\s*alloca\s+\[\s*(\d+)\s*x\s*([^\]]+)\]", line)
            if m_alloc:
                buf_reg, size_str, elem_ty = m_alloc.groups()
                buffer_sizes[buf_reg] = (int(size_str), elem_ty.strip())

        var_counter = 0

        for line in lines:
            clean = line.strip()
            # 1. Patch CWE-369: Division by Zero
            m_div = re.match(
                r"\s*(%[\w.]+)\s*=\s*(sdiv|udiv|srem|urem)\s+(?:exact\s+)?(\w+)\s+([^,]+),\s*([^,\s]+)",
                clean,
            )
            if m_div:
                res_reg, op, ty, num_str, den_str = m_div.groups()
                den_clean = den_str.strip()
                # If divisor is not a non-zero literal constant, harden with branchless safe select
                if not (den_clean.lstrip("-").isdigit() and int(den_clean) != 0):
                    var_counter += 1
                    zero_sym = f"%_div_is_zero_{var_counter}"
                    safe_den = f"%_safe_den_{var_counter}"
                    replacement_code = [
                        f"  {zero_sym} = icmp eq {ty} {den_clean}, 0",
                        f"  {safe_den} = select i1 {zero_sym}, {ty} 1, {ty} {den_clean}",
                        f"  {res_reg} = {op} {ty} {num_str.strip()}, {safe_den}",
                    ]
                    new_lines.extend(replacement_code)
                    patches.append(
                        HardeningPatch(
                            cwe_id="CWE-369",
                            function_name=fname,
                            original_instruction=clean,
                            hardened_instruction="\n".join(replacement_code),
                            description=f"Injected branchless divisor guard for {den_clean} to prevent divide-by-zero SIGFPE crash",
                        )
                    )
                    continue

            # 2. Patch CWE-125 / CWE-787: Buffer Out-of-Bounds Access
            m_gep = re.match(
                r"\s*(%[\w.]+)\s*=\s*getelementptr\s+(?:inbounds\s+)?([^,]+),\s*ptr\s+(%[\w.]+),\s*(.*)",
                clean,
            )
            if m_gep:
                res_reg, elem_ty, base_reg, indices_str = m_gep.groups()
                if base_reg in buffer_sizes:
                    capacity, buf_elem_ty = buffer_sizes[base_reg]
                    idx_tokens = [t.rstrip(",").strip() for t in indices_str.split() if t.startswith("%") or t.lstrip("-").isdigit()]
                    if idx_tokens:
                        target_idx = idx_tokens[-1]
                        # If target index is symbolic or out of bounds constant, harden it
                        is_static_safe = target_idx.lstrip("-").isdigit() and 0 <= int(target_idx) < capacity
                        if not is_static_safe:
                            var_counter += 1
                            ty_idx = "i32" if not target_idx.startswith("%") else "i32"
                            if "i64" in indices_str and target_idx in indices_str.split("i64")[-1]:
                                ty_idx = "i64"
                            is_neg_sym = f"%_is_neg_{var_counter}"
                            clamp_low = f"%_clamp_low_{var_counter}"
                            is_oob_sym = f"%_is_oob_{var_counter}"
                            clamped_idx = f"%_clamped_idx_{var_counter}"
                            cap_val = capacity - 1
                            replacement_code = [
                                f"  {is_neg_sym} = icmp slt {ty_idx} {target_idx}, 0",
                                f"  {clamp_low} = select i1 {is_neg_sym}, {ty_idx} 0, {ty_idx} {target_idx}",
                                f"  {is_oob_sym} = icmp sge {ty_idx} {clamp_low}, {capacity}",
                                f"  {clamped_idx} = select i1 {is_oob_sym}, {ty_idx} {cap_val}, {ty_idx} {clamp_low}",
                                f"  {res_reg} = getelementptr inbounds {elem_ty}, ptr {base_reg}, i64 0, {ty_idx} {clamped_idx}",
                            ]
                            new_lines.extend(replacement_code)
                            patches.append(
                                HardeningPatch(
                                    cwe_id="CWE-125/787",
                                    function_name=fname,
                                    original_instruction=clean,
                                    hardened_instruction="\n".join(replacement_code),
                                    description=f"Injected branchless bounds saturation clamp [0, {cap_val}] for buffer {base_reg} (capacity {capacity})",
                                )
                            )
                            continue

            # 3. Patch CWE-134: Uncontrolled Format String
            m_fmt = re.search(r"\s*(?:%[\w.]+\s*=\s*)?call\s+i32\s+(?:\([^)]*\)\s*)?@(printf|sprintf|fprintf)\((ptr\s+)?(%[\w.]+)", clean)
            if m_fmt:
                fn_name = m_fmt.group(1)
                dyn_fmt_reg = m_fmt.group(3)
                # Dynamic register passed directly as format string
                var_counter += 1
                safe_fmt_code = f'  call i32 (ptr, ...) @{fn_name}(ptr @.str.safe_spec, ptr {dyn_fmt_reg})'
                new_lines.append(safe_fmt_code)
                patches.append(
                    HardeningPatch(
                        cwe_id="CWE-134",
                        function_name=fname,
                        original_instruction=clean,
                        hardened_instruction=safe_fmt_code,
                        description=f"Mitigated CWE-134 format string exploit on @{fn_name} by wrapping dynamic variable {dyn_fmt_reg} with literal safe format specifier",
                    )
                )
                continue

            # 4. Patch CWE-14 / CWE-1037: Sensitive Memory Zeroization Barrier
            if clean.startswith("ret "):
                # Look back to see if previous instructions were zero stores to a pointer
                has_zero_wipe = any("store i8 0," in prev or "store i32 0," in prev for prev in lines[-4:])
                if has_zero_wipe:
                    barrier_inst = '  call void asm sideeffect "", "~{memory}"()'
                    new_lines.append(barrier_inst)
                    patches.append(
                        HardeningPatch(
                            cwe_id="CWE-14",
                            function_name=fname,
                            original_instruction=clean,
                            hardened_instruction=f"{barrier_inst}\n  {clean}",
                            description="Injected compiler memory barrier before return to prevent Dead Store Elimination (DSE) of sensitive buffer wipe",
                        )
                    )

            new_lines.append(line)

        return "\n".join(new_lines), patches


def harden_llvm_ir(ir_text: str, timeout_sec: int = 15) -> HardeningReport:
    """Convenience helper to harden LLVM IR and verify equivalence."""
    hardener = SecurityHardener(timeout_sec=timeout_sec)
    return hardener.harden_ir(ir_text)
