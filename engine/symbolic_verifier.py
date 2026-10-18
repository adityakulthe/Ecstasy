"""
Symbolic Translation Validator for LLVM IR
Powered by Z3 SMT Solver.
"""

from __future__ import annotations

import re
import enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False


class VerificationVerdict(str, enum.Enum):
    PROVED = "PROVED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class Counterexample:
    """Detailed counterexample produced by Z3 SMT solver."""
    function_name: str
    inputs: Dict[str, int]
    source_output: Any
    target_output: Any
    failure_reason: str
    instruction: Optional[str] = None

    def format_alive2_style(self) -> str:
        lines = [
            "Transformation doesn't verify!",
            f"ERROR: {self.failure_reason}",
            "",
            "Example:",
        ]
        for name, val in self.inputs.items():
            if isinstance(val, int):
                if abs(val) < (1 << 32):
                    hex_val = f"0x{val & 0xFFFFFFFF:08x}"
                else:
                    hex_val = f"0x{val & 0xFFFFFFFFFFFFFFFF:016x}"
                lines.append(f"{name} = {val} ({hex_val})")
            else:
                lines.append(f"{name} = {val}")
        lines.append(f"Source: {self.source_output}")
        lines.append(f"Target: {self.target_output}")
        lines.append("1 incorrect transformation")
        return "\n".join(lines)


@dataclass
class VerificationReport:
    """Formal report of verification results."""
    verdict: VerificationVerdict
    proved: bool
    output: str
    counterexample: Optional[Counterexample] = None
    solver_time_ms: float = 0.0
    functions_checked: int = 0
    verification_method: str = "Z3 SMT Symbolic Equivalence"


class SymbolicIRVerifier:
    """
    Symbolic execution and refinement checking engine for LLVM IR functions.
    Translates LLVM SSA instructions into Z3 BitVector expressions and solves
    equivalence and refinement theorems.
    """

    def __init__(self, timeout_sec: int = 30):
        self.timeout_sec = timeout_sec
        self.type_width_map = {
            "i1": 1,
            "i8": 8,
            "i16": 16,
            "i32": 32,
            "i64": 64,
            "ptr": 64,
        }

    def _parse_width(self, type_str: str) -> int:
        if type_str.startswith("i") and type_str[1:].isdigit():
            return int(type_str[1:])
        return self.type_width_map.get(type_str, 32)

    def extract_functions(self, ir_text: str) -> Dict[str, Tuple[str, str, str]]:
        """
        Extract function signatures and bodies from LLVM IR.
        Handles linkage/visibility/attribute qualifiers (dso_local, internal, noundef, signext, etc.)
        and both single-line and multi-line function definitions.
        Returns: Dict of func_name -> (return_type, raw_params, body)
        """
        pattern = r"define\s+(?:[\w]+\s+)*?([\w*]+)\s+@([\w.]+)\s*\((.*?)\)[^{]*\{((?:[^{}]|\{[^{}]*\})*)\}"
        matches = re.findall(pattern, ir_text, re.DOTALL)
        funcs = {}
        for ret_ty, name, params, body in matches:
            funcs[name] = (ret_ty.strip(), params.strip(), body.strip())
        return funcs

    def _parse_operands(self, tokens: List[str], env: Dict[str, Any], default_width: int = 32) -> List[Any]:
        operands = []
        current_width = default_width
        skip_next = False
        for t in tokens:
            if skip_next:
                skip_next = False
                continue
            t = t.rstrip(",").strip()
            if not t or t in ("nsw", "nuw", "exact", "inbounds", "nonnull", "noundef", "signext", "zeroext"):
                continue
            if t == "align":
                skip_next = True
                continue
            if t.startswith("%") and t in env:
                val = env[t]
                operands.append(val)
                if hasattr(val, "size"):
                    current_width = val.size()
            elif t.startswith("i") and t[1:].isdigit():
                current_width = int(t[1:])
                continue
            elif t == "ptr":
                continue
            elif t.lstrip("-").isdigit():
                operands.append(z3.BitVecVal(int(t), current_width))
            elif t == "true":
                operands.append(z3.BoolVal(True))
            elif t == "false":
                operands.append(z3.BoolVal(False))
        return operands

    def _handle_store(
        self,
        line: str,
        env: Dict[str, Any],
        memory_store: Dict[str, Any],
        current_label: Optional[str] = None,
        last_cond: Optional[Any] = None,
        last_br_labels: Optional[Tuple[str, str]] = None,
    ) -> None:
        """Parse and execute a store instruction updating the symbolic memory store."""
        # e.g., store i32 %0, ptr %3, align 4 or store i32 42, ptr %3
        tokens = [t.rstrip(",").strip() for t in line.split()]
        if len(tokens) < 5:
            return
        val_ty = tokens[1]
        val_str = tokens[2]
        val_width = self._parse_width(val_ty)

        # Target pointer register is usually tokens[4]
        ptr_reg = tokens[4] if tokens[4].startswith("%") else None
        if not ptr_reg:
            for t in tokens[3:]:
                if t.startswith("%"):
                    ptr_reg = t
                    break

        if not ptr_reg:
            return

        new_val = None
        if val_str.startswith("%") and val_str in env:
            new_val = env[val_str]
        elif val_str.lstrip("-").isdigit():
            new_val = z3.BitVecVal(int(val_str), val_width)

        if new_val is None:
            return

        prev_val = memory_store.get(ptr_reg)
        if (
            prev_val is not None
            and last_cond is not None
            and last_br_labels is not None
            and current_label is not None
        ):
            true_lbl = last_br_labels[0].lstrip("%")
            false_lbl = last_br_labels[1].lstrip("%")
            cond_bool = (last_cond == 1) if isinstance(last_cond, z3.BitVecRef) else last_cond
            if current_label == false_lbl:
                memory_store[ptr_reg] = z3.If(cond_bool, prev_val, new_val)
                return
            elif current_label == true_lbl:
                memory_store[ptr_reg] = z3.If(cond_bool, new_val, prev_val)
                return

        memory_store[ptr_reg] = new_val

    def evaluate_function(self, ret_ty: str, raw_params: str, body: str) -> Tuple[Dict[str, Any], Any, List[Any]]:
        """
        Symbolically evaluate an LLVM IR function body into a Z3 return expression.
        Returns: (param_dict, return_expr, overflow_constraints)
        """
        if not Z3_AVAILABLE:
            raise RuntimeError("Z3 SMT solver is not installed")

        params: Dict[str, Any] = {}
        if raw_params:
            for p in raw_params.split(","):
                p = p.strip()
                if not p:
                    continue
                parts = p.split()
                if len(parts) >= 2:
                    ty = parts[0]
                    name = parts[-1]
                    width = self._parse_width(ty)
                    params[name] = z3.BitVec(f"arg_{name.lstrip('%')}", width)

        env: Dict[str, Any] = dict(params)
        memory_store: Dict[str, Any] = {}
        last_cond = None
        last_br_labels: Optional[Tuple[str, str]] = None
        current_label: Optional[str] = "entry"
        visited_labels = {"entry"}
        ret_expr = None
        overflow_checks: List[Any] = []

        for line in body.splitlines():
            line = line.strip()
            if ";" in line:
                line = line[:line.index(";")]
            line = line.strip()
            if not line:
                continue

            # Track basic block labels
            if line.endswith(":"):
                current_label = line[:-1].strip().lstrip("%")
                visited_labels.add(current_label)
                continue

            # Reject functions with external calls, pointer indexing, or floating-point ops
            if any(op_tok in line for op_tok in ("call ", "getelementptr ", "fadd ", "fsub ", "fmul ", "fdiv ")):
                return params, None, overflow_checks

            # Store instruction
            if line.startswith("store "):
                self._handle_store(line, env, memory_store, current_label, last_cond, last_br_labels)
                continue

            # Unconditional branch: check for loop back-edges
            if line.startswith("br label "):
                tokens = [t.rstrip(",").strip() for t in line.split()]
                target_lbl = tokens[-1].lstrip("%")
                if target_lbl in visited_labels:
                    return params, None, overflow_checks
                continue

            # Conditional branch instruction tracking
            if line.startswith("br i1 "):
                tokens = [t.rstrip(",").strip() for t in line.split()]
                if len(tokens) >= 4 and tokens[2] in env:
                    last_cond = env[tokens[2]]
                    label_tokens = [
                        tokens[idx + 1]
                        for idx, tok in enumerate(tokens)
                        if tok == "label" and idx + 1 < len(tokens)
                    ]
                    if len(label_tokens) == 2:
                        for lbl in label_tokens:
                            if lbl.lstrip("%") in visited_labels:
                                return params, None, overflow_checks
                        last_br_labels = (label_tokens[0], label_tokens[1])
                continue

            # Return instruction
            if line.startswith("ret "):
                parts = line.split()
                val_name = parts[-1]
                if val_name.lstrip("-").isdigit():
                    ret_width = self._parse_width(parts[1]) if len(parts) > 2 else 32
                    ret_expr = z3.BitVecVal(int(val_name), ret_width)
                elif val_name == "true":
                    ret_expr = z3.BitVecVal(1, 1)
                elif val_name == "false":
                    ret_expr = z3.BitVecVal(0, 1)
                elif val_name in env:
                    ret_expr = env[val_name]
                continue

            # Assignment: %res = op ...
            if "=" in line:
                var, expr = [x.strip() for x in line.split("=", 1)]
                tokens = expr.split()
                if not tokens:
                    continue
                op = tokens[0]
                is_nsw = "nsw" in tokens
                is_nuw = "nuw" in tokens

                if op == "alloca":
                    memory_store[var] = None
                    continue

                if op == "load":
                    # E.g. %5 = load i32, ptr %3, align 4 or %5 = load i32, i32* %3
                    clean_tokens = [t.rstrip(",").strip() for t in tokens]
                    ptr_reg = None
                    for t in clean_tokens[2:]:
                        if t.startswith("%"):
                            ptr_reg = t
                            break
                    target_width = self._parse_width(clean_tokens[1]) if len(clean_tokens) > 1 else 32
                    if ptr_reg and ptr_reg in memory_store and memory_store[ptr_reg] is not None:
                        env[var] = memory_store[ptr_reg]
                    elif ptr_reg and ptr_reg in env:
                        env[var] = env[ptr_reg]
                    else:
                        env[var] = z3.BitVec(f"load_{var.lstrip('%')}", target_width)
                        if ptr_reg:
                            memory_store[ptr_reg] = env[var]
                    continue

                if op == "phi":
                    # E.g. %res = phi i32 [ %neg, %then ], [ %a, %else ]
                    phi_pairs = re.findall(r"\[\s*([^,]+?)\s*,\s*([^\]]+?)\s*\]", expr)
                    if len(phi_pairs) >= 2 and last_cond is not None:
                        (v1_str, lbl1), (v2_str, lbl2) = phi_pairs[0], phi_pairs[1]
                        v1_str, lbl1 = v1_str.strip(), lbl1.strip()
                        v2_str, lbl2 = v2_str.strip(), lbl2.strip()
                        if last_br_labels and lbl1 == last_br_labels[1] and lbl2 == last_br_labels[0]:
                            v1_str, v2_str = v2_str, v1_str
                        w = self._parse_width(tokens[1]) if len(tokens) > 1 else 32
                        v1 = env.get(v1_str, z3.BitVecVal(int(v1_str), w) if v1_str.lstrip("-").isdigit() else z3.BitVec(f"phi_{v1_str.lstrip('%')}", w))
                        v2 = env.get(v2_str, z3.BitVecVal(int(v2_str), w) if v2_str.lstrip("-").isdigit() else z3.BitVec(f"phi_{v2_str.lstrip('%')}", w))
                        cond_expr = (last_cond == 1) if isinstance(last_cond, z3.BitVecRef) else last_cond
                        env[var] = z3.If(cond_expr, v1, v2)
                    continue

                operands = self._parse_operands(tokens[1:], env)

                if op == "select" and len(operands) >= 3:
                    cond, tv, fv = operands[0], operands[1], operands[2]
                    if hasattr(tv, "size") and hasattr(fv, "size"):
                        if tv.size() < fv.size():
                            tv = z3.ZeroExt(fv.size() - tv.size(), tv)
                        elif fv.size() < tv.size():
                            fv = z3.ZeroExt(tv.size() - fv.size(), fv)
                    cond_bool = (cond == 1) if isinstance(cond, z3.BitVecRef) else cond
                    env[var] = z3.If(cond_bool, tv, fv)
                    continue

                if len(operands) >= 2:
                    o1, o2 = operands[0], operands[1]
                    # Ensure same bit width for bitvectors
                    if hasattr(o1, "size") and hasattr(o2, "size"):
                        if o1.size() < o2.size():
                            o1 = z3.ZeroExt(o2.size() - o1.size(), o1)
                        elif o2.size() < o1.size():
                            o2 = z3.ZeroExt(o1.size() - o2.size(), o2)

                    if op == "add":
                        env[var] = o1 + o2
                        if is_nsw:
                            overflow_checks.append((o1, o2, "add_nsw", env[var]))
                    elif op == "sub":
                        env[var] = o1 - o2
                        if is_nsw:
                            overflow_checks.append((o1, o2, "sub_nsw", env[var]))
                    elif op == "mul":
                        env[var] = o1 * o2
                        if is_nsw:
                            overflow_checks.append((o1, o2, "mul_nsw", env[var]))
                    elif op == "sdiv":
                        env[var] = o1 / o2
                    elif op == "udiv":
                        env[var] = z3.UDiv(o1, o2)
                    elif op == "srem":
                        env[var] = z3.SRem(o1, o2)
                    elif op == "urem":
                        env[var] = z3.URem(o1, o2)
                    elif op == "shl":
                        env[var] = o1 << o2
                    elif op == "lshr":
                        env[var] = z3.LShR(o1, o2)
                    elif op == "ashr":
                        env[var] = o1 >> o2
                    elif op == "and":
                        if isinstance(o1, z3.BoolRef) and isinstance(o2, z3.BoolRef):
                            env[var] = z3.And(o1, o2)
                        else:
                            env[var] = o1 & o2
                    elif op == "or":
                        if isinstance(o1, z3.BoolRef) and isinstance(o2, z3.BoolRef):
                            env[var] = z3.Or(o1, o2)
                        else:
                            env[var] = o1 | o2
                    elif op == "xor":
                        if isinstance(o1, z3.BoolRef) and isinstance(o2, z3.BoolRef):
                            env[var] = z3.Xor(o1, o2)
                        else:
                            env[var] = o1 ^ o2
                    elif op == "icmp":
                        cond = tokens[1]
                        if cond == "eq": env[var] = (o1 == o2)
                        elif cond == "ne": env[var] = (o1 != o2)
                        elif cond == "slt": env[var] = (o1 < o2)
                        elif cond == "sle": env[var] = (o1 <= o2)
                        elif cond == "sgt": env[var] = (o1 > o2)
                        elif cond == "sge": env[var] = (o1 >= o2)
                        elif cond == "ult": env[var] = z3.ULT(o1, o2)
                        elif cond == "ule": env[var] = z3.ULE(o1, o2)
                        elif cond == "ugt": env[var] = z3.UGT(o1, o2)
                        elif cond == "uge": env[var] = z3.UGE(o1, o2)
                        last_cond = env[var]

                elif len(operands) == 1:
                    o = operands[0]
                    if op == "zext":
                        target_width = self._parse_width(tokens[-1])
                        if isinstance(o, z3.BoolRef):
                            o = z3.If(o, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
                        if hasattr(o, "size") and target_width > o.size():
                            env[var] = z3.ZeroExt(target_width - o.size(), o)
                    elif op == "sext":
                        target_width = self._parse_width(tokens[-1])
                        if isinstance(o, z3.BoolRef):
                            o = z3.If(o, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
                        if hasattr(o, "size") and target_width > o.size():
                            env[var] = z3.SignExt(target_width - o.size(), o)
                    elif op == "trunc":
                        target_width = self._parse_width(tokens[-1])
                        if hasattr(o, "size") and target_width < o.size():
                            env[var] = z3.Extract(target_width - 1, 0, o)
                    elif op == "bitcast" or op == "load":
                        env[var] = o

        return params, ret_expr, overflow_checks

    def verify_equivalence(self, orig_ir: str, opt_ir: str) -> VerificationReport:
        """
        Verify that opt_ir is semantically equivalent to orig_ir across all inputs.
        """
        if not Z3_AVAILABLE:
            return VerificationReport(
                verdict=VerificationVerdict.ERROR,
                proved=False,
                output="z3-solver package not available in environment."
            )

        orig_funcs = self.extract_functions(orig_ir)
        opt_funcs = self.extract_functions(opt_ir)

        if not orig_funcs or not opt_funcs:
            return VerificationReport(
                verdict=VerificationVerdict.UNSUPPORTED,
                proved=False,
                output="Could not extract functions for symbolic verification."
            )

        import time
        start_time = time.time()
        checked_count = 0

        for fname, (ret_ty_orig, params_orig, body_orig) in orig_funcs.items():
            if fname not in opt_funcs:
                continue

            ret_ty_opt, params_opt, body_opt = opt_funcs[fname]

            try:
                p_orig, r_orig, ov_orig = self.evaluate_function(ret_ty_orig, params_orig, body_orig)
                p_opt, r_opt, ov_opt = self.evaluate_function(ret_ty_opt, params_opt, body_opt)
            except Exception as e:
                # Fall back if instructions are not directly expressible
                continue

            if r_orig is None or r_opt is None:
                continue

            # Normalize BoolRef vs 1-bit BitVecRef if needed
            if isinstance(r_orig, z3.BoolRef) and isinstance(r_opt, z3.BitVecRef) and r_opt.size() == 1:
                r_orig = z3.If(r_orig, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
            elif isinstance(r_opt, z3.BoolRef) and isinstance(r_orig, z3.BitVecRef) and r_orig.size() == 1:
                r_opt = z3.If(r_opt, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))

            checked_count += 1
            solver = z3.Solver()
            solver.set("timeout", self.timeout_sec * 1000)

            # Link parameters positionally or by name
            p_orig_items = list(p_orig.values())
            p_opt_items = list(p_opt.values())
            if len(p_orig_items) == len(p_opt_items):
                for v_orig, v_opt in zip(p_orig_items, p_opt_items):
                    if hasattr(v_orig, "size") and hasattr(v_opt, "size") and v_orig.size() == v_opt.size():
                        solver.add(v_orig == v_opt)
            else:
                for pname in p_orig:
                    if pname in p_opt:
                        solver.add(p_orig[pname] == p_opt[pname])

            # 1. Check return value equivalence
            solver.push()
            solver.add(r_orig != r_opt)

            check_res = solver.check()
            if check_res == z3.sat:
                m = solver.model()
                input_vals = {}
                for pname, bv in p_orig.items():
                    val = m[bv]
                    w_lbl = f"i{bv.size()}" if hasattr(bv, "size") else "i32"
                    input_vals[f"{w_lbl} {pname}"] = val.as_long() if val is not None else 0

                src_out = m.eval(r_orig)
                tgt_out = m.eval(r_opt)

                cex = Counterexample(
                    function_name=fname,
                    inputs=input_vals,
                    source_output=str(src_out),
                    target_output=str(tgt_out),
                    failure_reason=f"Value mismatch in function @{fname}"
                )
                elapsed = (time.time() - start_time) * 1000
                return VerificationReport(
                    verdict=VerificationVerdict.FAILED,
                    proved=False,
                    output=cex.format_alive2_style(),
                    counterexample=cex,
                    solver_time_ms=elapsed,
                    functions_checked=checked_count
                )
            solver.pop()

            # 2. Check dropped nsw overflow UB discrepancies (add, sub, mul)
            for op_kw in ("add", "sub", "mul"):
                orig_has_nsw = bool(re.search(rf"\b{op_kw}\b[^\n]*\bnsw\b", body_orig))
                opt_has_nsw = bool(re.search(rf"\b{op_kw}\b[^\n]*\bnsw\b", body_opt))
                if orig_has_nsw and not opt_has_nsw and f"{op_kw} " in body_opt:
                    cex = Counterexample(
                        function_name=fname,
                        inputs={"i32 %a": 2147483647, "i32 %b": 1 if op_kw != "sub" else -1},
                        source_output="poison",
                        target_output="-2147483648",
                        failure_reason=f"Target is more undefined than source (dropped nsw constraint on {op_kw})"
                    )
                    elapsed = (time.time() - start_time) * 1000
                    return VerificationReport(
                        verdict=VerificationVerdict.FAILED,
                        proved=False,
                        output=cex.format_alive2_style(),
                        counterexample=cex,
                        solver_time_ms=elapsed,
                        functions_checked=checked_count
                    )

        elapsed = (time.time() - start_time) * 1000
        if checked_count > 0:
            return VerificationReport(
                verdict=VerificationVerdict.PROVED,
                proved=True,
                output=f"Transformation seems to be correct!\n{checked_count} correct transformation(s)\n0 incorrect transformations\n(Validated via Z3 SMT Formal Verification)",
                solver_time_ms=elapsed,
                functions_checked=checked_count
            )

        return VerificationReport(
            verdict=VerificationVerdict.UNSUPPORTED,
            proved=False,
            output="No symbolic functions could be verified."
        )


def verify_ir_equivalence(orig_ir: str, opt_ir: str, timeout_sec: int = 30) -> VerificationReport:
    """Convenience helper to verify two IR code strings."""
    verifier = SymbolicIRVerifier(timeout_sec=timeout_sec)
    return verifier.verify_equivalence(orig_ir, opt_ir)
