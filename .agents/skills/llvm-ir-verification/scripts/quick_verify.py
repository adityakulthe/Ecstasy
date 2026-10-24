#!/usr/bin/env python3
"""Quick CLI helper forllvm-ir-verification skill: verifies two LLVM IR snippets or files via Z3 SMT."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from engine.symbolic_verifier import verify_ir_equivalence


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: quick_verify.py <orig.ll> <opt.ll>")
        return 2
    orig = Path(sys.argv[1]).read_text(encoding="utf-8")
    opt = Path(sys.argv[2]).read_text(encoding="utf-8")
    report = verify_ir_equivalence(orig, opt)
    print(f"Verdict: {report.verdict.value} (proved={report.proved}, time={report.solver_time_ms:.2f}ms)")
    print(report.output)
    return 0 if report.proved else 1


if __name__ == "__main__":
    raise SystemExit(main())
