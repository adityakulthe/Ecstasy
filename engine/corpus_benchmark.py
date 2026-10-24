"""
Whole-Corpus Compiler Optimization, CWE Security Audit, and Formal Verification Benchmark Engine.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Any, List

from server.mcp_server import compile_to_ir, apply_memory_safety, _verify_ir_semantics
from agents.ir_architect import optimize_ir_deterministic


def count_ir_instructions(ir_text: str) -> int:
    """Count executable LLVM IR instructions inside function definitions."""
    count = 0
    in_func = False
    for raw_line in ir_text.splitlines():
        line = raw_line.split(";")[0].strip()
        if not line:
            continue
        if line.startswith("define "):
            in_func = True
            continue
        if in_func:
            if line == "}":
                in_func = False
                continue
            if line.endswith(":"):
                continue
            count += 1
    return count


def run_corpus_benchmark(target_path: str | Path = "demo_corpus") -> Dict[str, Any]:
    """
    Benchmark Ecstasy compilation, -O2 IR optimization, CWE memory audit,
    and Z3/Alive2 formal verification across a file or directory corpus.
    """
    root = Path(target_path)
    if not root.exists():
        raise FileNotFoundError(f"Benchmark target path not found: {root}")

    extensions = {".c", ".cpp", ".cc", ".cxx"}
    if root.is_file():
        files = [root]
    else:
        files = sorted(
            p for p in root.rglob("*") if p.suffix.lower() in extensions and not p.name.startswith(".")
        )

    records: List[Dict[str, Any]] = []
    total_orig_insts = 0
    total_opt_insts = 0
    total_cwe_guards = 0
    proved_count = 0
    start_all = time.time()

    for fpath in files:
        t0 = time.time()
        src = fpath.read_text(encoding="utf-8", errors="ignore")
        comp = compile_to_ir(src, fpath.name)
        if not comp.get("success"):
            records.append(
                {
                    "file": str(fpath.relative_to(root) if root.is_dir() else fpath.name),
                    "compiled": False,
                    "orig_instructions": 0,
                    "opt_instructions": 0,
                    "reduction_pct": 0.0,
                    "cwe_guards": 0,
                    "cwe_findings": [],
                    "verdict": "ERROR",
                    "elapsed_ms": round((time.time() - t0) * 1000, 2),
                }
            )
            continue

        orig_ir = comp["ir"]
        opt_ir = optimize_ir_deterministic(orig_ir)

        orig_insts = count_ir_instructions(orig_ir)
        opt_insts = count_ir_instructions(opt_ir)
        reduction_pct = (
            round(((orig_insts - opt_insts) / orig_insts) * 100.0, 2) if orig_insts > 0 else 0.0
        )

        safety_res = apply_memory_safety(orig_ir, use_ai=False, verbose=False)
        cwe_guards = safety_res.get("checks_added", 0)
        cwe_findings = safety_res.get("check_locations", [])

        proved, _ = _verify_ir_semantics(orig_ir, opt_ir)
        verdict = "PROVED" if proved else "FAILED"
        if proved:
            proved_count += 1

        total_orig_insts += orig_insts
        total_opt_insts += opt_insts
        total_cwe_guards += cwe_guards

        records.append(
            {
                "file": str(fpath.relative_to(root) if root.is_dir() else fpath.name),
                "compiled": True,
                "orig_instructions": orig_insts,
                "opt_instructions": opt_insts,
                "reduction_pct": reduction_pct,
                "cwe_guards": cwe_guards,
                "cwe_findings": cwe_findings,
                "verdict": verdict,
                "elapsed_ms": round((time.time() - t0) * 1000, 2),
            }
        )

    overall_reduction_pct = (
        round(((total_orig_insts - total_opt_insts) / total_orig_insts) * 100.0, 2)
        if total_orig_insts > 0
        else 0.0
    )

    return {
        "scope": str(root),
        "files_benchmarked": len(records),
        "total_orig_instructions": total_orig_insts,
        "total_opt_instructions": total_opt_insts,
        "overall_reduction_pct": overall_reduction_pct,
        "total_cwe_guards": total_cwe_guards,
        "proved_files": proved_count,
        "all_proved": proved_count == len(records) and len(records) > 0,
        "total_elapsed_ms": round((time.time() - start_all) * 1000, 2),
        "records": records,
    }
