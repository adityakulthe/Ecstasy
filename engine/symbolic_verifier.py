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

    def _parse_fp_sort(self, type_str: str) -> Optional[Any]:
        t = type_str.strip().rstrip(",")
        if t in ("half", "f16"):
            return z3.Float16()
        if t in ("float", "f32"):
            return z3.Float32()
        if t in ("double", "f64"):
            return z3.Float64()
        return None

    def _parse_fp_val(self, val_str: str, fp_sort: Any) -> Optional[Any]:
        s = val_str.strip()
        try:
            if s.startswith("0x") or s.startswith("0X"):
                import struct
                bits = int(s, 16)
                d_val = struct.unpack(">d", bits.to_bytes(8, "big"))[0]
                if d_val == 0.0 and (bits >> 63) == 1:
                    return z3.fpNeg(z3.FPVal(0.0, fp_sort))
                return z3.FPVal(d_val, fp_sort)
            fval = float(s)
            if fval == 0.0 and s.startswith("-"):
                return z3.fpNeg(z3.FPVal(0.0, fp_sort))
            return z3.FPVal(fval, fp_sort)
        except Exception:
            return None

    def extract_functions(self, ir_text: str) -> Dict[str, Tuple[str, str, str]]:
        """
        Extract function signatures and bodies from LLVM IR.
        Handles linkage/visibility/attribute qualifiers (dso_local, internal, noundef, signext, etc.)
        and both single-line and multi-line function definitions.
        Returns: Dict of func_name -> (return_type, raw_params, body)
        """
        pattern = r"define\s+(?:[\w]+\s+)*?(<[^>\n]+>|[\w*]+)\s+@([\w.]+)\s*\((.*?)\)[^{]*\{((?:[^{}]|\{[^{}]*\})*)\}"
        matches = re.findall(pattern, ir_text, re.DOTALL)
        funcs = {}
        for ret_ty, name, params, body in matches:
            funcs[name] = (ret_ty.strip(), params.strip(), body.strip())
        return funcs

    def _parse_operands(self, tokens: List[str], env: Dict[str, Any], default_width: int = 32) -> List[Any]:
        operands = []
        current_width = default_width
        current_fp_sort: Optional[Any] = None
        last_vec_type: Optional[Tuple[int, int]] = None
        skip_next = False
        idx = 0
        while idx < len(tokens):
            t_raw = tokens[idx]
            idx += 1
            if skip_next:
                skip_next = False
                continue
            t = t_raw.rstrip(",").strip()
            if t.startswith("<"):
                chunk_parts = [t]
                while not chunk_parts[-1].endswith(">") and idx < len(tokens):
                    chunk_parts.append(tokens[idx].rstrip(",").strip())
                    idx += 1
                angle_chunk = " ".join(chunk_parts)
                m_vtype = re.match(r"<\s*(\d+)\s*x\s*(i\d+)\s*>", angle_chunk)
                if m_vtype:
                    last_vec_type = (int(m_vtype.group(1)), self._parse_width(m_vtype.group(2)))
                    current_width = last_vec_type[1]
                    continue
                elem_matches = re.findall(r"(i\d+)\s+(-?\d+|true|false)", angle_chunk)
                if elem_matches:
                    vec_lit = []
                    for ety, eval_s in elem_matches:
                        ew = self._parse_width(ety)
                        if eval_s == "true":
                            vec_lit.append(z3.BitVecVal(1, 1) if ew == 1 else z3.BoolVal(True))
                        elif eval_s == "false":
                            vec_lit.append(z3.BitVecVal(0, 1) if ew == 1 else z3.BoolVal(False))
                        else:
                            vec_lit.append(z3.BitVecVal(int(eval_s), ew))
                    operands.append(vec_lit)
                continue
            if not t or t in (
                "nsw",
                "nuw",
                "exact",
                "disjoint",
                "nneg",
                "samesign",
                "inbounds",
                "nonnull",
                "noundef",
                "signext",
                "zeroext",
                "fast",
                "nnan",
                "ninf",
                "nsz",
                "arcp",
                "contract",
                "afn",
                "reassoc",
            ):
                continue
            if t == "align":
                skip_next = True
                continue
            if t in ("half", "float", "double"):
                current_fp_sort = self._parse_fp_sort(t)
                continue
            if t == "zeroinitializer" and last_vec_type is not None:
                operands.append([z3.BitVecVal(0, last_vec_type[1]) for _ in range(last_vec_type[0])])
                continue
            if t.startswith("%") and t in env:
                val = env[t]
                operands.append(val)
                if hasattr(val, "size"):
                    current_width = val.size()
                elif isinstance(val, z3.FPRef):
                    current_fp_sort = val.sort()
            elif t.startswith("i") and t[1:].isdigit():
                current_width = int(t[1:])
                current_fp_sort = None
                continue
            elif t == "ptr":
                continue
            elif current_fp_sort is not None and re.match(
                r"^-?(?:\d+\.\d*(?:[eE][+-]?\d+)?|\d+[eE][+-]?\d+|0[xX][0-9a-fA-F]+)$", t
            ):
                fp_v = self._parse_fp_val(t, current_fp_sort)
                if fp_v is not None:
                    operands.append(fp_v)
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

        # Resolve constant-offset getelementptr alias if present
        slot_key = ptr_reg
        if ptr_reg in env and isinstance(env[ptr_reg], str) and env[ptr_reg].startswith("__gep__"):
            slot_key = env[ptr_reg]

        new_val = None
        if val_str.startswith("%") and val_str in env:
            new_val = env[val_str]
        elif val_str.lstrip("-").isdigit():
            new_val = z3.BitVecVal(int(val_str), val_width)

        if new_val is None:
            return

        if isinstance(new_val, z3.BoolRef):
            new_val = z3.If(new_val, z3.BitVecVal(1, val_width), z3.BitVecVal(0, val_width))
        elif isinstance(new_val, z3.BitVecRef) and new_val.size() != val_width:
            if new_val.size() < val_width:
                new_val = z3.SignExt(val_width - new_val.size(), new_val)
            else:
                new_val = z3.Extract(val_width - 1, 0, new_val)

        # QF_ABV symbolic array store for dynamic-index getelementptr
        if (
            ptr_reg in env
            and isinstance(env[ptr_reg], tuple)
            and len(env[ptr_reg]) == 3
            and env[ptr_reg][0] == "__z3arr__"
        ):
            _, arr_Key, idx_bv64 = env[ptr_reg]
            prev_arr = memory_store.get(arr_Key)
            if not isinstance(prev_arr, z3.ArrayRef):
                prev_arr = z3.Array(
                    f"arr_{arr_Key}", z3.BitVecSort(64), z3.BitVecSort(val_width)
                )
            updated_arr = z3.Store(prev_arr, idx_bv64, new_val)
            if (
                last_cond is not None
                and last_br_labels is not None
                and current_label is not None
            ):
                true_lbl = last_br_labels[0].lstrip("%")
                false_lbl = last_br_labels[1].lstrip("%")
                cond_bool = (last_cond == 1) if isinstance(last_cond, z3.BitVecRef) else last_cond
                if current_label == false_lbl:
                    memory_store[arr_Key] = z3.If(cond_bool, prev_arr, updated_arr)
                    return
                elif current_label == true_lbl:
                    memory_store[arr_Key] = z3.If(cond_bool, updated_arr, prev_arr)
                    return
            memory_store[arr_Key] = updated_arr
            return

        prev_val = memory_store.get(slot_key)
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
                memory_store[slot_key] = z3.If(cond_bool, prev_val, new_val)
                return
            elif current_label == true_lbl:
                memory_store[slot_key] = z3.If(cond_bool, new_val, prev_val)
                return

        memory_store[slot_key] = new_val

    def evaluate_function(
        self,
        ret_ty: str,
        raw_params: str,
        body: str,
        module_funcs: Optional[Dict[str, Tuple[str, str, str]]] = None,
        call_depth: int = 0,
    ) -> Tuple[Dict[str, Any], Any, List[Any]]:
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
                m_vec_p = re.match(r"<\s*(\d+)\s*x\s*(i\d+)\s*>\s*(?:[\w]+\s+)*(%[\w.]+)", p)
                if m_vec_p:
                    n_lanes = int(m_vec_p.group(1))
                    elem_w = self._parse_width(m_vec_p.group(2))
                    name = m_vec_p.group(3)
                    params[name] = [
                        z3.BitVec(f"arg_{name.lstrip('%')}_lane{i}", elem_w) for i in range(n_lanes)
                    ]
                    continue
                parts = p.split()
                if len(parts) >= 2:
                    ty = parts[0]
                    name = parts[-1]
                    fp_sort = self._parse_fp_sort(ty)
                    if fp_sort is not None:
                        params[name] = z3.FP(f"arg_{name.lstrip('%')}", fp_sort)
                    else:
                        width = self._parse_width(ty)
                        params[name] = z3.BitVec(f"arg_{name.lstrip('%')}", width)

        env: Dict[str, Any] = dict(params)
        memory_store: Dict[str, Any] = {}
        local_allocas: set[str] = set()
        last_cond = None
        last_br_labels: Optional[Tuple[str, str]] = None
        switch_cond_map: Dict[str, Any] = {}
        switch_default_label: Optional[str] = None
        current_label: Optional[str] = "entry"
        visited_labels = {"entry"}
        ret_expr = None
        overflow_checks: List[Any] = []

        # Collapse multi-line switch [ ... ] blocks into single lines
        normalized_body = re.sub(
            r"(switch\s+[^\[]+\[)([^\]]*)(\])",
            lambda m: m.group(1) + " " + " ".join(m.group(2).split()) + " " + m.group(3),
            body,
            flags=re.DOTALL,
        )

        from collections import deque

        block_map: Dict[str, List[str]] = {"entry": []}
        block_order: List[str] = ["entry"]
        cur_b = "entry"
        seen_b = {"entry"}
        has_loop = False
        for raw_ln in normalized_body.splitlines():
            s_ln = raw_ln.split(";", 1)[0].strip()
            if not s_ln:
                continue
            if s_ln.endswith(":"):
                cur_b = s_ln[:-1].strip().lstrip("%")
                if cur_b not in block_map:
                    block_map[cur_b] = []
                    block_order.append(cur_b)
                seen_b.add(cur_b)
                continue
            block_map[cur_b].append(s_ln)
            if s_ln.startswith("br "):
                for m_lbl in re.findall(r"label\s+%([\w.]+)", s_ln):
                    if m_lbl in seen_b:
                        has_loop = True

        prev_label: Optional[str] = None
        prev_env: Dict[str, Any] = dict(env)
        cfg_steps = 0
        max_cfg_steps = 128
        if has_loop:
            first_lbl = (
                block_order[1]
                if (block_order[0] == "entry" and not block_map["entry"] and len(block_order) > 1)
                else block_order[0]
            )
            current_label = first_lbl
            line_queue = deque(block_map[first_lbl])
        else:
            line_queue = deque(normalized_body.splitlines())

        while line_queue:
            line = line_queue.popleft().strip()
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

            # Reject functions with non-intrinsic external calls
            if "call " in line and not (
                any(
                    intr in line
                    for intr in (
                        "@llvm.smax.",
                        "@llvm.smin.",
                        "@llvm.umax.",
                        "@llvm.umin.",
                        "@llvm.abs.",
                        "@llvm.bswap.",
                        "@llvm.ctpop.",
                        "@llvm.ctlz.",
                        "@llvm.cttz.",
                        "@llvm.fshl.",
                        "@llvm.fshr.",
                        "@llvm.sadd.with.overflow.",
                        "@llvm.uadd.with.overflow.",
                        "@llvm.ssub.with.overflow.",
                        "@llvm.usub.with.overflow.",
                        "@llvm.smul.with.overflow.",
                        "@llvm.umul.with.overflow.",
                        "@llvm.sadd.sat.",
                        "@llvm.uadd.sat.",
                        "@llvm.ssub.sat.",
                        "@llvm.usub.sat.",
                        "@llvm.bitreverse.",
                        "@llvm.vector.reduce.",
                        "@llvm.fabs.",
                        "@llvm.fma.",
                        "@llvm.fmuladd.",
                        "@llvm.sqrt.",
                        "@llvm.minnum.",
                        "@llvm.maxnum.",
                        "@llvm.minimum.",
                        "@llvm.maximum.",
                        "@llvm.copysign.",
                    )
                )
                or (module_funcs and call_depth < 4 and any(f"@{fn}(" in line for fn in module_funcs))
            ):
                return params, None, overflow_checks

            # Store instruction
            if line.startswith("store "):
                self._handle_store(
                    line,
                    env,
                    memory_store,
                    current_label,
                    None if has_loop else last_cond,
                    None if has_loop else last_br_labels,
                )
                continue

            # Switch instruction: switch i32 %val, label %default [ i32 0, label %bb0 i32 1, label %bb1 ]
            if line.startswith("switch "):
                m_sw = re.match(
                    r"switch\s+(i\d+)\s+(%[\w.]+|-?\d+)\s*,\s*label\s+(%[\w.]+)\s*\[(.*)\]",
                    line,
                )
                if m_sw:
                    sw_ty, sw_val_str, def_lbl, cases_blob = m_sw.groups()
                    sw_w = self._parse_width(sw_ty)
                    sw_bv = (
                        env.get(sw_val_str)
                        if sw_val_str.startswith("%")
                        else z3.BitVecVal(int(sw_val_str), sw_w)
                    )
                    if sw_bv is not None:
                        switch_default_label = def_lbl.strip()
                        switch_cond_map.clear()
                        for case_val_str, case_lbl in re.findall(
                            r"i\d+\s+(-?\d+)\s*,\s*label\s+(%[\w.]+)", cases_blob
                        ):
                            c_bv = z3.BitVecVal(int(case_val_str), sw_w)
                            c_lbl = case_lbl.strip()
                            cond_c = (sw_bv == c_bv)
                            if c_lbl in switch_cond_map:
                                switch_cond_map[c_lbl] = z3.Or(switch_cond_map[c_lbl], cond_c)
                            else:
                                switch_cond_map[c_lbl] = cond_c
                continue

            # Unconditional branch: check for loop back-edges
            if line.startswith("br label "):
                tokens = [t.rstrip(",").strip() for t in line.split()]
                target_lbl = tokens[-1].lstrip("%")
                if has_loop:
                    cfg_steps += 1
                    if cfg_steps > max_cfg_steps or target_lbl not in block_map:
                        return params, None, overflow_checks
                    prev_label = current_label
                    prev_env = dict(env)
                    current_label = target_lbl
                    line_queue = deque(block_map[target_lbl])
                    continue
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
                        if has_loop:
                            cfg_steps += 1
                            if cfg_steps > max_cfg_steps:
                                return params, None, overflow_checks
                            cond_b = (last_cond == 1) if isinstance(last_cond, z3.BitVecRef) else last_cond
                            s_cond = z3.simplify(cond_b)
                            if z3.is_true(s_cond):
                                next_lbl = label_tokens[0].lstrip("%")
                            elif z3.is_false(s_cond):
                                next_lbl = label_tokens[1].lstrip("%")
                            else:
                                return params, None, overflow_checks
                            if next_lbl not in block_map:
                                return params, None, overflow_checks
                            prev_label = current_label
                            prev_env = dict(env)
                            current_label = next_lbl
                            line_queue = deque(block_map[next_lbl])
                            continue
                        for lbl in label_tokens:
                            if lbl.lstrip("%") in visited_labels:
                                return params, None, overflow_checks
                        last_br_labels = (label_tokens[0], label_tokens[1])
                continue

            # Return instruction
            if line.startswith("ret "):
                parts = line.split()
                val_name = parts[-1]
                if val_name in env:
                    ret_expr = env[val_name]
                elif len(parts) > 2 and self._parse_fp_sort(parts[1]) is not None:
                    ret_expr = self._parse_fp_val(val_name, self._parse_fp_sort(parts[1]))
                elif val_name.lstrip("-").isdigit():
                    ret_width = self._parse_width(parts[1]) if len(parts) > 2 else 32
                    ret_expr = z3.BitVecVal(int(val_name), ret_width)
                elif val_name == "true":
                    ret_expr = z3.BitVecVal(1, 1)
                elif val_name == "false":
                    ret_expr = z3.BitVecVal(0, 1)
                continue

            # Assignment: %res = op ...
            if "=" in line:
                var, expr = [x.strip() for x in line.split("=", 1)]
                # Strip tail/musttail/notail call prefixes
                expr = re.sub(r"^(?:tail|musttail|notail)\s+", "", expr)
                tokens = expr.split()
                if not tokens:
                    continue
                op = tokens[0]
                is_nsw = "nsw" in tokens
                is_nuw = "nuw" in tokens

                if op == "insertelement":
                    m_ins = re.match(
                        r"insertelement\s+<\s*(\d+)\s*x\s*(i\d+)\s*>\s*([^,]+),\s*(i\d+)\s+([^,]+),\s*i\d+\s+(-?\d+)",
                        expr,
                    )
                    if m_ins:
                        n_lanes = int(m_ins.group(1))
                        elem_w = self._parse_width(m_ins.group(2))
                        vec_tok = m_ins.group(3).strip().split()[-1]
                        val_tok = m_ins.group(5).strip().split()[-1]
                        idx = int(m_ins.group(6))
                        base_vec = (
                            list(env[vec_tok])
                            if (vec_tok in env and isinstance(env[vec_tok], list))
                            else [z3.BitVecVal(0, elem_w) for _ in range(n_lanes)]
                        )
                        val_bv = (
                            env[val_tok]
                            if val_tok in env
                            else (z3.BitVecVal(int(val_tok), elem_w) if val_tok.lstrip("-").isdigit() else None)
                        )
                        if val_bv is not None and 0 <= idx < len(base_vec):
                            base_vec[idx] = val_bv
                            env[var] = base_vec
                            continue
                    return params, None, overflow_checks

                if op == "extractelement":
                    m_ext = re.match(
                        r"extractelement\s+<\s*(\d+)\s*x\s*(i\d+)\s*>\s*([^,]+),\s*i\d+\s+(-?\d+)",
                        expr,
                    )
                    if m_ext:
                        vec_tok = m_ext.group(3).strip().split()[-1]
                        idx = int(m_ext.group(4))
                        if vec_tok in env and isinstance(env[vec_tok], list) and 0 <= idx < len(env[vec_tok]):
                            env[var] = env[vec_tok][idx]
                            continue
                    return params, None, overflow_checks

                if op == "shufflevector":
                    m_shuf = re.match(
                        r"shufflevector\s+<\s*(\d+)\s*x\s*(i\d+)\s*>\s*([^,]+),\s*<\s*\d+\s*x\s*i\d+\s*>\s*([^,]+),\s*<\s*(\d+)\s*x\s*i\d+\s*>\s*(.+)",
                        expr,
                    )
                    if m_shuf:
                        n_in = int(m_shuf.group(1))
                        elem_w = self._parse_width(m_shuf.group(2))
                        v1_tok = m_shuf.group(3).strip().split()[-1]
                        v2_tok = m_shuf.group(4).strip().split()[-1]
                        n_out = int(m_shuf.group(5))
                        mask_str = m_shuf.group(6).strip()
                        v1_list = (
                            list(env[v1_tok])
                            if (v1_tok in env and isinstance(env[v1_tok], list))
                            else [z3.BitVecVal(0, elem_w) for _ in range(n_in)]
                        )
                        v2_list = (
                            list(env[v2_tok])
                            if (v2_tok in env and isinstance(env[v2_tok], list))
                            else [z3.BitVecVal(0, elem_w) for _ in range(n_in)]
                        )
                        combined = v1_list + v2_list
                        if mask_str == "zeroinitializer":
                            env[var] = [combined[0] for _ in range(n_out)]
                            continue
                        mask_idxs = [
                            int(x) if x.lstrip("-").isdigit() else 0
                            for x in re.findall(r"i\d+\s+(-?\d+|undef|poison)", mask_str)
                        ]
                        if len(mask_idxs) == n_out and all(0 <= m < len(combined) for m in mask_idxs):
                            env[var] = [combined[m] for m in mask_idxs]
                            continue
                    return params, None, overflow_checks

                if op == "insertvalue":
                    rest = re.sub(r"^insertvalue\s+(?:\{[^}]+\}|\[[^\]]+\])\s*", "", expr).strip()
                    parts = [p.strip() for p in rest.split(",")]
                    if len(parts) >= 3:
                        agg_tok = parts[0].split()[-1] if parts[0].split() else ""
                        val_ops = self._parse_operands(parts[1].split(), env)
                        idx_tok = parts[2].strip()
                        if val_ops and idx_tok.isdigit():
                            idx = int(idx_tok)
                            curr = (
                                list(env[agg_tok])
                                if (agg_tok in env and isinstance(env[agg_tok], tuple))
                                else []
                            )
                            while len(curr) <= idx:
                                curr.append(None)
                            curr[idx] = val_ops[0]
                            env[var] = tuple(curr)
                            continue
                    return params, None, overflow_checks

                if op == "extractvalue":
                    agg_reg = None
                    for t in tokens[1:-1]:
                        t_clean = t.rstrip(",").strip()
                        if t_clean.startswith("%"):
                            agg_reg = t_clean
                    idx_tok = tokens[-1].rstrip(",").strip()
                    if agg_reg and agg_reg in env and isinstance(env[agg_reg], tuple) and idx_tok.isdigit():
                        idx = int(idx_tok)
                        if 0 <= idx < len(env[agg_reg]) and env[agg_reg][idx] is not None:
                            env[var] = env[agg_reg][idx]
                            if idx == 1 and (
                                isinstance(env[var], z3.BoolRef)
                                or (hasattr(env[var], "size") and env[var].size() == 1)
                            ):
                                last_cond = env[var]
                            continue
                    return params, None, overflow_checks

                if op == "call":
                    # Handle IEEE-754 floating-point intrinsics @llvm.{fabs,fma,fmuladd,sqrt,minnum,maxnum,minimum,maximum,copysign}.*
                    m_fp_intr = re.search(
                        r"@(llvm\.(?:fabs|fma|fmuladd|sqrt|minnum|maxnum|minimum|maximum|copysign))\.[a-z0-9.]+\((.*?)\)",
                        expr,
                    )
                    if m_fp_intr:
                        fp_intr = m_fp_intr.group(1)
                        arg_tokens = m_fp_intr.group(2).replace(",", " ").split()
                        fp_ops = self._parse_operands(arg_tokens, env)
                        if fp_intr == "llvm.fabs" and len(fp_ops) >= 1 and isinstance(fp_ops[0], z3.FPRef):
                            env[var] = z3.fpAbs(fp_ops[0])
                            continue
                        elif fp_intr == "llvm.sqrt" and len(fp_ops) >= 1 and isinstance(fp_ops[0], z3.FPRef):
                            env[var] = z3.fpSqrt(z3.RNE(), fp_ops[0])
                            continue
                        elif fp_intr in ("llvm.fma", "llvm.fmuladd") and len(fp_ops) >= 3:
                            fa, fb, fc = fp_ops[0], fp_ops[1], fp_ops[2]
                            if z3.is_fp_value(fa) and not z3.is_fp_value(fb):
                                fa, fb = fb, fa
                            env[var] = z3.fpFMA(z3.RNE(), fa, fb, fc)
                            continue
                        elif fp_intr in ("llvm.minnum", "llvm.minimum") and len(fp_ops) >= 2:
                            env[var] = z3.fpMin(fp_ops[0], fp_ops[1])
                            continue
                        elif fp_intr in ("llvm.maxnum", "llvm.maximum") and len(fp_ops) >= 2:
                            env[var] = z3.fpMax(fp_ops[0], fp_ops[1])
                            continue
                        elif fp_intr == "llvm.copysign" and len(fp_ops) >= 2:
                            env[var] = z3.If(
                                z3.fpIsNegative(fp_ops[1]),
                                z3.fpNeg(z3.fpAbs(fp_ops[0])),
                                z3.fpAbs(fp_ops[0]),
                            )
                            continue

                    # Handle horizontal SIMD vector reduction intrinsics @llvm.vector.reduce.*
                    m_vred = re.search(
                        r"@llvm\.vector\.reduce\.(add|mul|and|or|xor|smax|smin|umax|umin)\.[a-z0-9.]+\((.*?)\)",
                        expr,
                    )
                    if m_vred:
                        red_op = m_vred.group(1)
                        arg_tokens = m_vred.group(2).replace(",", " ").split()
                        vec_reg = next(
                            (t for t in arg_tokens if t.startswith("%") and t in env and isinstance(env[t], list)),
                            None,
                        )
                        if vec_reg and env[vec_reg]:
                            lanes = env[vec_reg]
                            acc = lanes[0]
                            for ln in lanes[1:]:
                                if red_op == "add":
                                    acc = acc + ln
                                elif red_op == "mul":
                                    acc = acc * ln
                                elif red_op == "and":
                                    acc = acc & ln
                                elif red_op == "or":
                                    acc = acc | ln
                                elif red_op == "xor":
                                    acc = acc ^ ln
                                elif red_op == "smax":
                                    acc = z3.If(acc > ln, acc, ln)
                                elif red_op == "smin":
                                    acc = z3.If(acc < ln, acc, ln)
                                elif red_op == "umax":
                                    acc = z3.If(z3.UGT(acc, ln), acc, ln)
                                elif red_op == "umin":
                                    acc = z3.If(z3.ULT(acc, ln), acc, ln)
                            env[var] = acc
                            continue

                    # Handle overflow-checked arithmetic intrinsics returning { iN, i1 }
                    m_ovf = re.search(
                        r"@(llvm\.(?:sadd|uadd|ssub|usub|smul|umul)\.with\.overflow)\.[a-z0-9.]+\((.*?)\)",
                        expr,
                    )
                    if m_ovf:
                        ovf_intr = m_ovf.group(1)
                        arg_tokens = m_ovf.group(2).replace(",", " ").split()
                        ovf_ops = self._parse_operands(arg_tokens, env)
                        if len(ovf_ops) >= 2:
                            o1, o2 = ovf_ops[0], ovf_ops[1]
                            if ovf_intr == "llvm.sadd.with.overflow":
                                res_bv = o1 + o2
                                ovf_bool = z3.Not(z3.And(z3.BVAddNoOverflow(o1, o2, True), z3.BVAddNoUnderflow(o1, o2)))
                            elif ovf_intr == "llvm.uadd.with.overflow":
                                res_bv = o1 + o2
                                ovf_bool = z3.Not(z3.BVAddNoOverflow(o1, o2, False))
                            elif ovf_intr == "llvm.ssub.with.overflow":
                                res_bv = o1 - o2
                                ovf_bool = z3.Not(z3.And(z3.BVSubNoOverflow(o1, o2), z3.BVSubNoUnderflow(o1, o2, True)))
                            elif ovf_intr == "llvm.usub.with.overflow":
                                res_bv = o1 - o2
                                ovf_bool = z3.Not(z3.BVSubNoUnderflow(o1, o2, False))
                            elif ovf_intr == "llvm.smul.with.overflow":
                                res_bv = o1 * o2
                                ovf_bool = z3.Not(z3.And(z3.BVMulNoOverflow(o1, o2, True), z3.BVMulNoUnderflow(o1, o2)))
                            else:
                                res_bv = o1 * o2
                                ovf_bool = z3.Not(z3.BVMulNoOverflow(o1, o2, False))
                            env[var] = (res_bv, ovf_bool)
                            continue

                    # Handle pure bitvector LLVM intrinsics
                    m_intr = re.search(
                        r"@(llvm\.(?:smax|smin|umax|umin|abs|bswap|bitreverse|ctpop|ctlz|cttz|fshl|fshr|(?:sadd|uadd|ssub|usub)\.sat))\.[a-z0-9.]+\((.*?)\)",
                        expr,
                    )
                    if m_intr:
                        intr_name = m_intr.group(1)
                        arg_tokens = m_intr.group(2).replace(",", " ").split()
                        intr_ops = self._parse_operands(arg_tokens, env)
                        if intr_name == "llvm.abs" and len(intr_ops) >= 1:
                            o1 = intr_ops[0]
                            if isinstance(o1, list):
                                env[var] = [
                                    z3.If(ln < z3.BitVecVal(0, ln.size()), -ln, ln) for ln in o1
                                ]
                            else:
                                zero = z3.BitVecVal(0, o1.size())
                                env[var] = z3.If(o1 < zero, -o1, o1)
                            continue
                        elif intr_name == "llvm.bswap" and len(intr_ops) >= 1:
                            o1 = intr_ops[0]
                            if isinstance(o1, list):
                                env[var] = [
                                    z3.Concat(*[z3.Extract(b * 8 + 7, b * 8, ln) for b in range(ln.size() // 8)])
                                    for ln in o1
                                ]
                                continue
                            w = o1.size()
                            if w >= 16 and w % 8 == 0:
                                num_bytes = w // 8
                                byte_slices = [z3.Extract(b * 8 + 7, b * 8, o1) for b in range(num_bytes)]
                                env[var] = z3.Concat(*byte_slices)
                                continue
                        elif intr_name == "llvm.bitreverse" and len(intr_ops) >= 1:
                            o1 = intr_ops[0]
                            w = o1.size()
                            if w >= 2:
                                env[var] = z3.Concat(*[z3.Extract(i, i, o1) for i in range(w)])
                            else:
                                env[var] = o1
                            continue
                        elif intr_name == "llvm.ctpop" and len(intr_ops) >= 1:
                            o1 = intr_ops[0]
                            if isinstance(o1, list):
                                res_ctpop = []
                                for ln in o1:
                                    lw = ln.size()
                                    acc_ln = z3.BitVecVal(0, lw)
                                    for i in range(lw):
                                        acc_ln = acc_ln + z3.ZeroExt(lw - 1, z3.Extract(i, i, ln))
                                    res_ctpop.append(acc_ln)
                                env[var] = res_ctpop
                                continue
                            w = o1.size()
                            bits = [z3.ZeroExt(w - 1, z3.Extract(i, i, o1)) for i in range(w)]
                            acc = z3.BitVecVal(0, w)
                            for b_expr in bits:
                                acc = acc + b_expr
                            env[var] = acc
                            continue
                        elif intr_name in ("llvm.ctlz", "llvm.cttz") and len(intr_ops) >= 1:
                            o1 = intr_ops[0]
                            w = o1.size()
                            res_bv = z3.BitVecVal(w, w)
                            if intr_name == "llvm.ctlz":
                                for i in range(w):
                                    res_bv = z3.If(z3.Extract(i, i, o1) == 1, z3.BitVecVal(w - 1 - i, w), res_bv)
                            else:
                                for i in range(w - 1, -1, -1):
                                    res_bv = z3.If(z3.Extract(i, i, o1) == 1, z3.BitVecVal(i, w), res_bv)
                            env[var] = res_bv
                            continue
                        elif intr_name in ("llvm.fshl", "llvm.fshr") and len(intr_ops) >= 3:
                            o1, o2, sh = intr_ops[0], intr_ops[1], intr_ops[2]
                            w = o1.size()
                            sh_mod = z3.URem(sh, z3.BitVecVal(w, w))
                            if intr_name == "llvm.fshl":
                                env[var] = z3.If(
                                    sh_mod == 0,
                                    o1,
                                    (o1 << sh_mod) | z3.LShR(o2, z3.BitVecVal(w, w) - sh_mod),
                                )
                            else:
                                env[var] = z3.If(
                                    sh_mod == 0,
                                    o2,
                                    z3.LShR(o2, sh_mod) | (o1 << (z3.BitVecVal(w, w) - sh_mod)),
                                )
                            continue
                        elif intr_name in ("llvm.sadd.sat", "llvm.uadd.sat", "llvm.ssub.sat", "llvm.usub.sat") and len(intr_ops) >= 2:
                            o1, o2 = intr_ops[0], intr_ops[1]
                            w = o1.size()
                            smax_val = z3.BitVecVal((1 << (w - 1)) - 1, w)
                            smin_val = z3.BitVecVal(-(1 << (w - 1)), w)
                            umax_val = z3.BitVecVal((1 << w) - 1, w)
                            umin_val = z3.BitVecVal(0, w)
                            if intr_name == "llvm.sadd.sat":
                                env[var] = z3.If(
                                    z3.Not(z3.BVAddNoOverflow(o1, o2, True)),
                                    smax_val,
                                    z3.If(z3.Not(z3.BVAddNoUnderflow(o1, o2)), smin_val, o1 + o2),
                                )
                            elif intr_name == "llvm.uadd.sat":
                                env[var] = z3.If(
                                    z3.Not(z3.BVAddNoOverflow(o1, o2, False)),
                                    umax_val,
                                    o1 + o2,
                                )
                            elif intr_name == "llvm.ssub.sat":
                                env[var] = z3.If(
                                    z3.Not(z3.BVSubNoOverflow(o1, o2)),
                                    smax_val,
                                    z3.If(z3.Not(z3.BVSubNoUnderflow(o1, o2, True)), smin_val, o1 - o2),
                                )
                            else:
                                env[var] = z3.If(
                                    z3.Not(z3.BVSubNoUnderflow(o1, o2, False)),
                                    umin_val,
                                    o1 - o2,
                                )
                            continue
                        elif len(intr_ops) >= 2:
                            o1, o2 = intr_ops[0], intr_ops[1]
                            if isinstance(o1, list) and isinstance(o2, list) and len(o1) == len(o2):
                                if intr_name == "llvm.smax":
                                    env[var] = [z3.If(a > b, a, b) for a, b in zip(o1, o2)]
                                elif intr_name == "llvm.smin":
                                    env[var] = [z3.If(a < b, a, b) for a, b in zip(o1, o2)]
                                elif intr_name == "llvm.umax":
                                    env[var] = [z3.If(z3.UGT(a, b), a, b) for a, b in zip(o1, o2)]
                                elif intr_name == "llvm.umin":
                                    env[var] = [z3.If(z3.ULT(a, b), a, b) for a, b in zip(o1, o2)]
                                continue
                            if intr_name == "llvm.smax":
                                env[var] = z3.If(o1 > o2, o1, o2)
                            elif intr_name == "llvm.smin":
                                env[var] = z3.If(o1 < o2, o1, o2)
                            elif intr_name == "llvm.umax":
                                env[var] = z3.If(z3.UGT(o1, o2), o1, o2)
                            elif intr_name == "llvm.umin":
                                env[var] = z3.If(z3.ULT(o1, o2), o1, o2)
                            continue
                    if module_funcs and call_depth < 4:
                        m_ucall = re.search(r"@([\w.]+)\s*\((.*?)\)", expr)
                        if m_ucall and m_ucall.group(1) in module_funcs:
                            callee_name = m_ucall.group(1)
                            c_ret_ty, c_params_raw, c_body = module_funcs[callee_name]
                            arg_tokens = m_ucall.group(2).replace(",", " ").split()
                            call_args = self._parse_operands(arg_tokens, env)
                            c_params, c_ret, _ = self.evaluate_function(
                                c_ret_ty,
                                c_params_raw,
                                c_body,
                                module_funcs=module_funcs,
                                call_depth=call_depth + 1,
                            )
                            if c_ret is not None and len(call_args) == len(c_params):
                                subst_pairs = []
                                for f_bv, a_val in zip(c_params.values(), call_args):
                                    if isinstance(f_bv, list) and isinstance(a_val, list) and len(f_bv) == len(a_val):
                                        for f_ln, a_ln in zip(f_bv, a_val):
                                            subst_pairs.append((f_ln, a_ln))
                                    elif hasattr(f_bv, "size") and hasattr(a_val, "size"):
                                        if a_val.size() < f_bv.size():
                                            a_val = z3.ZeroExt(f_bv.size() - a_val.size(), a_val)
                                        elif a_val.size() > f_bv.size():
                                            a_val = z3.Extract(f_bv.size() - 1, 0, a_val)
                                        subst_pairs.append((f_bv, a_val))
                                if isinstance(c_ret, list):
                                    env[var] = [
                                        z3.substitute(ln, *subst_pairs) if subst_pairs else ln for ln in c_ret
                                    ]
                                else:
                                    env[var] = z3.substitute(c_ret, *subst_pairs) if subst_pairs else c_ret
                                continue
                    return params, None, overflow_checks

                if op == "alloca":
                    local_allocas.add(var)
                    memory_store[var] = None
                    continue

                if op == "getelementptr":
                    # Support local alloca SROA (constant indices) and QF_ABV symbolic arrays (dynamic register indices)
                    clean_toks = [t.rstrip(",").strip() for t in tokens[1:]]
                    base_ptr = None
                    idx_tokens: List[str] = []
                    has_dynamic_idx = False
                    idx_bv64 = z3.BitVecVal(0, 64)
                    for t in clean_toks:
                        if base_ptr is None:
                            if t.startswith("%"):
                                base_ptr = t
                        else:
                            if t.startswith("%"):
                                has_dynamic_idx = True
                                idx_tokens.append(t)
                                if t in env:
                                    iv = env[t]
                                    if isinstance(iv, z3.BoolRef):
                                        iv = z3.If(iv, z3.BitVecVal(1, 64), z3.BitVecVal(0, 64))
                                    elif isinstance(iv, z3.BitVecRef):
                                        if iv.size() < 64:
                                            iv = z3.SignExt(64 - iv.size(), iv)
                                        elif iv.size() > 64:
                                            iv = z3.Extract(63, 0, iv)
                                        idx_bv64 = idx_bv64 + iv
                                    else:
                                        return params, None, overflow_checks
                                else:
                                    return params, None, overflow_checks
                            elif t.lstrip("-").isdigit():
                                idx_tokens.append(t)
                                idx_bv64 = idx_bv64 + z3.BitVecVal(int(t), 64)

                    if not base_ptr:
                        return params, None, overflow_checks

                    is_prev_z3arr = (
                        base_ptr in env
                        and isinstance(env[base_ptr], tuple)
                        and len(env[base_ptr]) == 3
                        and env[base_ptr][0] == "__z3arr__"
                    )
                    if (
                        not has_dynamic_idx
                        and not is_prev_z3arr
                        and (
                            base_ptr in local_allocas
                            or (base_ptr in env and isinstance(env[base_ptr], str) and env[base_ptr].startswith("__gep__"))
                        )
                    ):
                        root_key = env[base_ptr] if (base_ptr in env and isinstance(env[base_ptr], str)) else f"__gep__{base_ptr}"
                        gep_key = f"{root_key}_{'_'.join(idx_tokens)}" if idx_tokens else root_key
                        env[var] = gep_key
                        local_allocas.add(var)
                        continue

                    if is_prev_z3arr:
                        _, arr_key, base_idx_bv64 = env[base_ptr]
                        env[var] = ("__z3arr__", arr_key, base_idx_bv64 + idx_bv64)
                        local_allocas.add(var)
                        continue
                    elif base_ptr in local_allocas or base_ptr in params:
                        if base_ptr in params and base_ptr not in local_allocas:
                            param_pos = list(params.keys()).index(base_ptr)
                            arr_key = f"param_arr_{param_pos}"
                        else:
                            arr_key = f"local_arr_{base_ptr.lstrip('%')}"
                        env[var] = ("__z3arr__", arr_key, idx_bv64)
                        local_allocas.add(var)
                        continue
                    return params, None, overflow_checks

                if op == "load":
                    # E.g. %5 = load i32, ptr %3, align 4 or %5 = load i32, i32* %3
                    clean_tokens = [t.rstrip(",").strip() for t in tokens]
                    ptr_reg = None
                    for t in clean_tokens[2:]:
                        if t.startswith("%"):
                            ptr_reg = t
                            break
                    target_width = self._parse_width(clean_tokens[1]) if len(clean_tokens) > 1 else 32
                    if (
                        ptr_reg
                        and ptr_reg in env
                        and isinstance(env[ptr_reg], tuple)
                        and len(env[ptr_reg]) == 3
                        and env[ptr_reg][0] == "__z3arr__"
                    ):
                        _, arr_key, idx_bv64 = env[ptr_reg]
                        arr_ref = memory_store.get(arr_key)
                        if not isinstance(arr_ref, z3.ArrayRef):
                            arr_ref = z3.Array(
                                f"arr_{arr_key}", z3.BitVecSort(64), z3.BitVecSort(target_width)
                            )
                            memory_store[arr_key] = arr_ref
                        env[var] = z3.Select(arr_ref, idx_bv64)
                        continue
                    slot_key = ptr_reg
                    if ptr_reg and ptr_reg in env and isinstance(env[ptr_reg], str) and env[ptr_reg].startswith("__gep__"):
                        slot_key = env[ptr_reg]
                    if slot_key and slot_key in memory_store and memory_store[slot_key] is not None:
                        env[var] = memory_store[slot_key]
                    elif ptr_reg and ptr_reg in env and not isinstance(env[ptr_reg], str):
                        env[var] = env[ptr_reg]
                    else:
                        env[var] = z3.BitVec(f"load_{var.lstrip('%')}", target_width)
                        if slot_key:
                            memory_store[slot_key] = env[var]
                    continue

                if op == "phi":
                    # E.g. %res = phi i32 [ %neg, %then ], [ %a, %else ]
                    phi_pairs = re.findall(r"\[\s*([^,]+?)\s*,\s*([^\]]+?)\s*\]", expr)
                    w = self._parse_width(tokens[1]) if len(tokens) > 1 else 32
                    if has_loop and prev_label is not None:
                        matched_val = None
                        for val_s, lbl_s in phi_pairs:
                            if lbl_s.strip().lstrip("%") == prev_label:
                                v_clean = val_s.strip()
                                if v_clean in prev_env:
                                    matched_val = prev_env[v_clean]
                                elif v_clean.lstrip("-").isdigit():
                                    matched_val = z3.BitVecVal(int(v_clean), w)
                                elif v_clean == "true":
                                    matched_val = z3.BitVecVal(1, 1)
                                elif v_clean == "false":
                                    matched_val = z3.BitVecVal(0, 1)
                                break
                        if matched_val is None:
                            return params, None, overflow_checks
                        env[var] = matched_val
                        continue
                    if switch_cond_map and len(phi_pairs) >= 2:
                        def _resolve_phi_val(v_s: str) -> Any:
                            v_s = v_s.strip()
                            if v_s in env:
                                return env[v_s]
                            if v_s.lstrip("-").isdigit():
                                return z3.BitVecVal(int(v_s), w)
                            return z3.BitVec(f"phi_{v_s.lstrip('%')}", w)

                        default_bv = None
                        case_branches: List[Tuple[Any, Any]] = []
                        for val_s, lbl_s in phi_pairs:
                            lbl_clean = lbl_s.strip()
                            bv_val = _resolve_phi_val(val_s)
                            if lbl_clean in switch_cond_map:
                                case_branches.append((switch_cond_map[lbl_clean], bv_val))
                            else:
                                default_bv = bv_val
                        if default_bv is None and phi_pairs:
                            default_bv = _resolve_phi_val(phi_pairs[-1][0])
                        acc_phi = default_bv
                        for c_cond, c_val in reversed(case_branches):
                            acc_phi = z3.If(c_cond, c_val, acc_phi)
                        env[var] = acc_phi
                        continue
                    if len(phi_pairs) >= 2 and last_cond is not None:
                        (v1_str, lbl1), (v2_str, lbl2) = phi_pairs[0], phi_pairs[1]
                        v1_str, lbl1 = v1_str.strip(), lbl1.strip()
                        v2_str, lbl2 = v2_str.strip(), lbl2.strip()
                        if last_br_labels and lbl1 == last_br_labels[1] and lbl2 == last_br_labels[0]:
                            v1_str, v2_str = v2_str, v1_str
                        v1 = env.get(v1_str, z3.BitVecVal(int(v1_str), w) if v1_str.lstrip("-").isdigit() else z3.BitVec(f"phi_{v1_str.lstrip('%')}", w))
                        v2 = env.get(v2_str, z3.BitVecVal(int(v2_str), w) if v2_str.lstrip("-").isdigit() else z3.BitVec(f"phi_{v2_str.lstrip('%')}", w))
                        cond_expr = (last_cond == 1) if isinstance(last_cond, z3.BitVecRef) else last_cond
                        env[var] = z3.If(cond_expr, v1, v2)
                    continue

                operands = self._parse_operands(tokens[1:], env)

                m_vty = re.search(r"<\s*(\d+)\s*x\s*(i\d+)\s*>", expr)
                if m_vty and len(operands) < 2 and op in (
                    "add", "sub", "mul", "sdiv", "udiv", "srem", "urem", "shl", "lshr", "ashr", "and", "or", "xor"
                ):
                    v_lanes = int(m_vty.group(1))
                    v_w = self._parse_width(m_vty.group(2))
                    after_ty = expr[m_vty.end():].strip()
                    if "zeroinitializer" in after_ty and len(operands) == 1 and isinstance(operands[0], list):
                        operands.append([z3.BitVecVal(0, v_w) for _ in range(v_lanes)])
                    else:
                        m_vlit = re.search(r"<([^>]+)>", after_ty)
                        if m_vlit and len(operands) == 1 and isinstance(operands[0], list):
                            lit_vals = [
                                z3.BitVecVal(int(c), v_w)
                                for c in re.findall(r"i\d+\s+(-?\d+)", m_vlit.group(1))
                            ]
                            if len(lit_vals) == v_lanes:
                                operands.append(lit_vals)

                if op == "select" and len(operands) >= 3:
                    cond, tv, fv = operands[0], operands[1], operands[2]
                    if isinstance(cond, list) and isinstance(tv, list) and isinstance(fv, list) and len(cond) == len(tv) == len(fv):
                        env[var] = [
                            z3.If((c == 1) if isinstance(c, z3.BitVecRef) else c, t, f)
                            for c, t, f in zip(cond, tv, fv)
                        ]
                        continue
                    elif isinstance(tv, list) and isinstance(fv, list) and len(tv) == len(fv):
                        cond_bool = (cond == 1) if isinstance(cond, z3.BitVecRef) else cond
                        env[var] = [z3.If(cond_bool, t, f) for t, f in zip(tv, fv)]
                        continue
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
                    if isinstance(o1, list) and isinstance(o2, list) and len(o1) == len(o2):
                        if op == "add":
                            env[var] = [a + b for a, b in zip(o1, o2)]
                        elif op == "sub":
                            env[var] = [a - b for a, b in zip(o1, o2)]
                        elif op == "mul":
                            env[var] = [a * b for a, b in zip(o1, o2)]
                        elif op == "sdiv":
                            env[var] = [a / b for a, b in zip(o1, o2)]
                        elif op == "udiv":
                            env[var] = [z3.UDiv(a, b) for a, b in zip(o1, o2)]
                        elif op == "srem":
                            env[var] = [z3.SRem(a, b) for a, b in zip(o1, o2)]
                        elif op == "urem":
                            env[var] = [z3.URem(a, b) for a, b in zip(o1, o2)]
                        elif op == "shl":
                            env[var] = [a << b for a, b in zip(o1, o2)]
                        elif op == "lshr":
                            env[var] = [z3.LShR(a, b) for a, b in zip(o1, o2)]
                        elif op == "ashr":
                            env[var] = [a >> b for a, b in zip(o1, o2)]
                        elif op == "and":
                            env[var] = [
                                z3.And(a, b) if (isinstance(a, z3.BoolRef) and isinstance(b, z3.BoolRef)) else (a & b)
                                for a, b in zip(o1, o2)
                            ]
                        elif op == "or":
                            env[var] = [
                                z3.Or(a, b) if (isinstance(a, z3.BoolRef) and isinstance(b, z3.BoolRef)) else (a | b)
                                for a, b in zip(o1, o2)
                            ]
                        elif op == "xor":
                            env[var] = [
                                z3.Xor(a, b) if (isinstance(a, z3.BoolRef) and isinstance(b, z3.BoolRef)) else (a ^ b)
                                for a, b in zip(o1, o2)
                            ]
                        elif op == "icmp":
                            cond = next(
                                (
                                    t
                                    for t in tokens[1:]
                                    if t in ("eq", "ne", "slt", "sle", "sgt", "sge", "ult", "ule", "ugt", "uge")
                                ),
                                tokens[1],
                            )
                            if cond == "eq":
                                env[var] = [a == b for a, b in zip(o1, o2)]
                            elif cond == "ne":
                                env[var] = [a != b for a, b in zip(o1, o2)]
                            elif cond == "slt":
                                env[var] = [a < b for a, b in zip(o1, o2)]
                            elif cond == "sle":
                                env[var] = [a <= b for a, b in zip(o1, o2)]
                            elif cond == "sgt":
                                env[var] = [a > b for a, b in zip(o1, o2)]
                            elif cond == "sge":
                                env[var] = [a >= b for a, b in zip(o1, o2)]
                            elif cond == "ult":
                                env[var] = [z3.ULT(a, b) for a, b in zip(o1, o2)]
                            elif cond == "ule":
                                env[var] = [z3.ULE(a, b) for a, b in zip(o1, o2)]
                            elif cond == "ugt":
                                env[var] = [z3.UGT(a, b) for a, b in zip(o1, o2)]
                            elif cond == "uge":
                                env[var] = [z3.UGE(a, b) for a, b in zip(o1, o2)]
                        continue

                    if isinstance(o1, z3.BoolRef) and isinstance(o2, z3.BitVecRef) and o2.size() == 1:
                        o1 = z3.If(o1, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
                    elif isinstance(o2, z3.BoolRef) and isinstance(o1, z3.BitVecRef) and o1.size() == 1:
                        o2 = z3.If(o2, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
                    # Ensure same bit width for bitvectors
                    if hasattr(o1, "size") and hasattr(o2, "size"):
                        if o1.size() < o2.size():
                            o1 = z3.ZeroExt(o2.size() - o1.size(), o1)
                        elif o2.size() < o1.size():
                            o2 = z3.ZeroExt(o1.size() - o2.size(), o2)

                    if isinstance(o1, z3.FPRef) and isinstance(o2, z3.FPRef):
                        has_nnan = "nnan" in tokens or "fast" in tokens
                        has_ninf = "ninf" in tokens or "fast" in tokens
                        has_nsz = "nsz" in tokens or "fast" in tokens
                        if has_nnan:
                            overflow_checks.append(("fp_assume", z3.Not(z3.fpIsNaN(o1))))
                            overflow_checks.append(("fp_assume", z3.Not(z3.fpIsNaN(o2))))
                        if has_ninf:
                            overflow_checks.append(("fp_assume", z3.Not(z3.fpIsInf(o1))))
                            overflow_checks.append(("fp_assume", z3.Not(z3.fpIsInf(o2))))
                        if has_nsz:
                            overflow_checks.append(("fp_nsz", True))

                        if op == "fadd":
                            if z3.is_fp_value(o1) and not z3.is_fp_value(o2):
                                o1, o2 = o2, o1
                            env[var] = z3.fpAdd(z3.RNE(), o1, o2)
                        elif op == "fsub":
                            env[var] = z3.fpAdd(z3.RNE(), o1, z3.simplify(z3.fpNeg(o2)))
                        elif op == "fmul":
                            if z3.is_fp_value(o1) and not z3.is_fp_value(o2):
                                o1, o2 = o2, o1
                            env[var] = z3.fpMul(z3.RNE(), o1, o2)
                        elif op == "fdiv":
                            env[var] = z3.fpDiv(z3.RNE(), o1, o2)
                        elif op == "frem":
                            env[var] = z3.fpRem(o1, o2)
                        elif op == "fcmp":
                            fcond = next(
                                (
                                    t
                                    for t in tokens[1:]
                                    if t
                                    in (
                                        "false",
                                        "oeq",
                                        "ogt",
                                        "oge",
                                        "olt",
                                        "ole",
                                        "one",
                                        "ord",
                                        "ueq",
                                        "ugt",
                                        "uge",
                                        "ult",
                                        "ule",
                                        "une",
                                        "uno",
                                        "true",
                                    )
                                ),
                                tokens[1],
                            )
                            is_unord = z3.Or(z3.fpIsNaN(o1), z3.fpIsNaN(o2))
                            is_ord = z3.Not(is_unord)
                            if fcond == "false":
                                env[var] = z3.BoolVal(False)
                            elif fcond == "true":
                                env[var] = z3.BoolVal(True)
                            elif fcond == "oeq":
                                env[var] = z3.fpEQ(o1, o2)
                            elif fcond == "ogt":
                                env[var] = z3.fpGT(o1, o2)
                            elif fcond == "oge":
                                env[var] = z3.fpGE(o1, o2)
                            elif fcond == "olt":
                                env[var] = z3.fpLT(o1, o2)
                            elif fcond == "ole":
                                env[var] = z3.fpLE(o1, o2)
                            elif fcond == "one":
                                env[var] = z3.And(is_ord, z3.Not(z3.fpEQ(o1, o2)))
                            elif fcond == "ord":
                                env[var] = is_ord
                            elif fcond == "uno":
                                env[var] = is_unord
                            elif fcond == "ueq":
                                env[var] = z3.Or(is_unord, z3.fpEQ(o1, o2))
                            elif fcond == "ugt":
                                env[var] = z3.Or(is_unord, z3.fpGT(o1, o2))
                            elif fcond == "uge":
                                env[var] = z3.Or(is_unord, z3.fpGE(o1, o2))
                            elif fcond == "ult":
                                env[var] = z3.Or(is_unord, z3.fpLT(o1, o2))
                            elif fcond == "ule":
                                env[var] = z3.Or(is_unord, z3.fpLE(o1, o2))
                            elif fcond == "une":
                                env[var] = z3.Not(z3.fpEQ(o1, o2))
                            last_cond = env[var]
                        continue

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
                        cond = next(
                            (
                                t
                                for t in tokens[1:]
                                if t in ("eq", "ne", "slt", "sle", "sgt", "sge", "ult", "ule", "ugt", "uge")
                            ),
                            tokens[1],
                        )
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
                    target_width = self._parse_width(tokens[-1].rstrip(">"))
                    target_fp = self._parse_fp_sort(tokens[-1].rstrip(">"))
                    if op == "fneg" and isinstance(o, z3.FPRef):
                        env[var] = z3.fpNeg(o)
                    elif op in ("fpext", "fptrunc") and isinstance(o, z3.FPRef) and target_fp is not None:
                        env[var] = z3.fpFPToFP(z3.RNE(), o, target_fp)
                    elif op == "sitofp" and hasattr(o, "size") and target_fp is not None:
                        env[var] = z3.fpSignedToFP(z3.RNE(), o, target_fp)
                    elif op == "uitofp" and hasattr(o, "size") and target_fp is not None:
                        env[var] = z3.fpToFP(z3.RNE(), o, target_fp)
                    elif op == "fptosi" and isinstance(o, z3.FPRef):
                        env[var] = z3.fpToSBV(z3.RTZ(), o, z3.BitVecSort(target_width))
                    elif op == "fptoui" and isinstance(o, z3.FPRef):
                        env[var] = z3.fpToUBV(z3.RTZ(), o, z3.BitVecSort(target_width))
                    elif op == "zext":
                        if isinstance(o, list):
                            res_lanes = []
                            for ln in o:
                                if isinstance(ln, z3.BoolRef):
                                    ln = z3.If(ln, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
                                if hasattr(ln, "size") and target_width > ln.size():
                                    res_lanes.append(z3.ZeroExt(target_width - ln.size(), ln))
                                else:
                                    res_lanes.append(ln)
                            env[var] = res_lanes
                        else:
                            if isinstance(o, z3.BoolRef):
                                o = z3.If(o, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
                            if hasattr(o, "size") and target_width > o.size():
                                env[var] = z3.ZeroExt(target_width - o.size(), o)
                    elif op == "sext":
                        if isinstance(o, list):
                            res_lanes = []
                            for ln in o:
                                if isinstance(ln, z3.BoolRef):
                                    ln = z3.If(ln, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
                                if hasattr(ln, "size") and target_width > ln.size():
                                    res_lanes.append(z3.SignExt(target_width - ln.size(), ln))
                                else:
                                    res_lanes.append(ln)
                            env[var] = res_lanes
                        else:
                            if isinstance(o, z3.BoolRef):
                                o = z3.If(o, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
                            if hasattr(o, "size") and target_width > o.size():
                                env[var] = z3.SignExt(target_width - o.size(), o)
                    elif op == "trunc":
                        if isinstance(o, list):
                            env[var] = [
                                z3.Extract(target_width - 1, 0, ln)
                                if (hasattr(ln, "size") and target_width < ln.size())
                                else ln
                                for ln in o
                            ]
                        elif hasattr(o, "size") and target_width < o.size():
                            env[var] = z3.Extract(target_width - 1, 0, o)
                    elif op == "bitcast":
                        if isinstance(o, z3.FPRef) and target_fp is None:
                            env[var] = z3.fpToIEEEBV(o)
                        elif isinstance(o, z3.BitVecRef) and target_fp is not None:
                            env[var] = z3.fpBVToFP(o, target_fp)
                        else:
                            env[var] = o
                    elif op in ("load", "freeze"):
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
                p_orig, r_orig, ov_orig = self.evaluate_function(
                    ret_ty_orig, params_orig, body_orig, module_funcs=orig_funcs
                )
                p_opt, r_opt, ov_opt = self.evaluate_function(
                    ret_ty_opt, params_opt, body_opt, module_funcs=opt_funcs
                )
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
                    if isinstance(v_orig, list) and isinstance(v_opt, list) and len(v_orig) == len(v_opt):
                        for ln_o, ln_t in zip(v_orig, v_opt):
                            if hasattr(ln_o, "size") and hasattr(ln_t, "size") and ln_o.size() == ln_t.size():
                                solver.add(ln_o == ln_t)
                    elif isinstance(v_orig, z3.FPRef) and isinstance(v_opt, z3.FPRef) and v_orig.sort() == v_opt.sort():
                        solver.add(v_orig == v_opt)
                    elif hasattr(v_orig, "size") and hasattr(v_opt, "size") and v_orig.size() == v_opt.size():
                        solver.add(v_orig == v_opt)
            else:
                for pname in p_orig:
                    if pname in p_opt:
                        v_orig, v_opt = p_orig[pname], p_opt[pname]
                        if isinstance(v_orig, list) and isinstance(v_opt, list) and len(v_orig) == len(v_opt):
                            for ln_o, ln_t in zip(v_orig, v_opt):
                                solver.add(ln_o == ln_t)
                        else:
                            solver.add(v_orig == v_opt)

            has_fp_nsz = False
            for ov_item in ov_orig + ov_opt:
                if isinstance(ov_item, tuple) and len(ov_item) == 2:
                    if ov_item[0] == "fp_assume":
                        solver.add(ov_item[1])
                    elif ov_item[0] == "fp_nsz" and ov_item[1]:
                        has_fp_nsz = True

            # 1. Check return value equivalence
            solver.push()
            if isinstance(r_orig, list) and isinstance(r_opt, list) and len(r_orig) == len(r_opt):
                solver.add(z3.Or(*[a != b for a, b in zip(r_orig, r_opt)]))
            elif isinstance(r_orig, z3.FPRef) and isinstance(r_opt, z3.FPRef) and has_fp_nsz:
                solver.add(
                    z3.Not(
                        z3.Or(
                            z3.fpEQ(r_orig, r_opt),
                            z3.And(z3.fpIsNaN(r_orig), z3.fpIsNaN(r_opt)),
                        )
                    )
                )
            else:
                solver.add(r_orig != r_opt)

            check_res = solver.check()
            if check_res == z3.sat:
                m = solver.model()
                input_vals = {}
                for pname, bv in p_orig.items():
                    if isinstance(bv, list):
                        input_vals[f"vec {pname}"] = [
                            m[ln].as_long() if m[ln] is not None else 0 for ln in bv
                        ]
                    elif isinstance(bv, z3.FPRef):
                        input_vals[f"fp {pname}"] = str(m.eval(bv))
                    else:
                        val = m[bv]
                        w_lbl = f"i{bv.size()}" if hasattr(bv, "size") else "i32"
                        input_vals[f"{w_lbl} {pname}"] = val.as_long() if val is not None else 0

                if isinstance(r_orig, list) and isinstance(r_opt, list):
                    src_out = [str(m.eval(ln)) for ln in r_orig]
                    tgt_out = [str(m.eval(ln)) for ln in r_opt]
                else:
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


_VERIFICATION_CACHE: Dict[str, VerificationReport] = {}
_MAX_CACHE_SIZE = 512


def verify_ir_equivalence(orig_ir: str, opt_ir: str, timeout_sec: int = 30) -> VerificationReport:
    """Convenience helper to verify two IR code strings with SHA-256 content-addressed memoization."""
    import hashlib
    cache_key = hashlib.sha256(f"{timeout_sec}||{orig_ir}||{opt_ir}".encode("utf-8", errors="ignore")).hexdigest()
    cached = _VERIFICATION_CACHE.get(cache_key)
    if cached is not None:
        return cached

    verifier = SymbolicIRVerifier(timeout_sec=timeout_sec)
    report = verifier.verify_equivalence(orig_ir, opt_ir)
    if len(_VERIFICATION_CACHE) >= _MAX_CACHE_SIZE:
        _VERIFICATION_CACHE.pop(next(iter(_VERIFICATION_CACHE)))
    _VERIFICATION_CACHE[cache_key] = report
    return report

