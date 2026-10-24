#!/usr/bin/env python3
"""
Ecstasy CLI - Formally Verified AI Compiler Pipeline
Command-line interface for compiling, optimizing, verifying, and securing C and LLVM code.
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.mcp_server import compile_to_ir, optimize_ir_pass, validate_translation
from agents.supervisor import CompilerSupervisor
from agents.safety_vault import SafetyVault


def print_banner():
    banner = r"""
  ______ _____  _____ _______       _______     __
 |  ____/ ____|/ ____|__   __|/\    / ____\ \   / /
 | |__ | |    | (___    | |  /  \  | (___  \ \_/ / 
 |  __|| |     \___ \   | | / /\ \  \___ \  \   /  
 | |___| |____ ____) |  | |/ ____ \ ____) |  | |   
 |______\_____|_____/   |_/_/    \_\_____/   |_|   
    Formally-Verified AI Compiler & Security Pipeline
    Powered by IBM Granite 4.0, Alive2, and Z3 SMT
    """
    print(banner)


def cmd_compile(args):
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ Error: File not found: {source_path}")
        sys.exit(1)

    with open(source_path, "r") as f:
        c_code = f.read()

    print(f"\n📂 Compiling: {source_path.name}")
    print(f"⚙️  Orchestration: {'Advanced (9-Agent Suite)' if args.advanced else 'Standard (Orchestrator)'}")
    print(f"🔁 Max Retries: {args.retries}\n")

    supervisor = CompilerSupervisor(max_retries=args.retries, use_advanced_agents=args.advanced)
    start_time = time.time()
    result = supervisor.supervise_compilation(c_code, str(source_path))
    elapsed = time.time() - start_time

    print("\n" + "=" * 65)
    print("📋 COMPILATION RESULTS")
    print("=" * 65)
    print(f"Status:        {'✅ SUCCESS' if result.get('success') else '❌ FAILED'}")
    print(f"SMT Verdict:   {result.get('final_verdict', 'UNKNOWN')}")
    print(f"Phases Done:   {', '.join(result.get('phases_completed', []))}")
    print(f"Retries Used:  {result.get('total_retries_used', 0)}")
    print(f"Elapsed Time:  {elapsed:.2f}s")

    if result.get("binary_path"):
        out_bin = args.output or source_path.with_suffix(".out")
        import shutil
        shutil.copy(result["binary_path"], out_bin)
        print(f"Output Binary: {out_bin}")

    if args.cert or args.html:
        vault = SafetyVault()
        cert = vault.generate_certificate(
            project_name=source_path.stem,
            source_code=c_code,
            ir_code=result.get("hardened_ir", ""),
            binary_path=result.get("binary_path"),
            z3_verdict=result.get("final_verdict", "UNKNOWN")
        )
        cert_path = source_path.with_suffix(".proof.json")
        vault.export_certificate(cert, str(cert_path))
        print(f"Proof Cert:    {cert_path} (ID: {cert.certificate_id})")

        if args.html:
            html_path = Path(args.html) if isinstance(args.html, str) and args.html != "True" else source_path.with_suffix(".proof.html")
            vault.export_html_report(cert, str(html_path))
            print(f"HTML Report:   {html_path}")

    if args.report:
        report_path = Path(args.report)
        report_payload = {
            "source": str(source_path),
            "status": "SUCCESS" if result.get("success") else "FAILED",
            "verdict": result.get("final_verdict", "UNKNOWN"),
            "phases_completed": result.get("phases_completed", []),
            "retries_used": result.get("total_retries_used", 0),
            "elapsed_seconds": round(elapsed, 3),
            "binary_path": result.get("binary_path")
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2)
        print(f"JSON Report:   {report_path}")

    print("=" * 65)


def cmd_audit(args):
    target_dir = Path(args.path)
    if not target_dir.exists():
        print(f"❌ Error: Path not found: {target_dir}")
        sys.exit(1)

    extensions = {".c", ".cpp", ".cc", ".cxx", ".ll"}
    if target_dir.is_file():
        files = [target_dir]
    else:
        files = sorted([p for p in target_dir.rglob("*") if p.suffix.lower() in extensions and not p.name.startswith(".")])

    if not files:
        print(f"ℹ️  No C/C++ or LLVM IR files found in: {target_dir}")
        sys.exit(0)

    print("\n" + "=" * 75)
    print(f"🛡️  ECSTASY SECURITY & MEMORY SAFETY AUDIT")
    print(f"📁 Target Scope: {target_dir} ({len(files)} file(s))")
    print("=" * 75)

    from server.mcp_server import apply_memory_safety

    audit_records = []
    total_checks = 0
    total_vulnerable = 0

    print(f"{'FILE':<35} | {'CHECKS':<8} | {'STATUS':<10} | {'FINDINGS'}")
    print("-" * 75)

    for fpath in files:
        rel_name = str(fpath.relative_to(target_dir)) if target_dir.is_dir() else fpath.name
        if len(rel_name) > 34:
            disp_name = "..." + rel_name[-31:]
        else:
            disp_name = rel_name

        try:
            content = fpath.read_text(errors="ignore")
            if fpath.suffix.lower() in {".c", ".cpp", ".cc", ".cxx"}:
                compile_res = compile_to_ir(content, fpath.name)
                ir_code = compile_res.get("ir", "") if compile_res["success"] else ""
            else:
                ir_code = content

            if not ir_code:
                print(f"{disp_name:<35} | {'0':<8} | {'⚠️ SKIP':<10} | Syntax or compile error")
                continue

            res = apply_memory_safety(ir_code, use_ai=not args.offline, verbose=False)
            checks = res.get("checks_added", 0)
            total_checks += checks

            if checks > 0:
                total_vulnerable += 1
                status = "🔴 HARDEN"
                findings = "; ".join(res.get("check_locations", []))[:30]
            else:
                status = "🟢 CLEAN"
                findings = "No memory vulnerabilities"

            print(f"{disp_name:<35} | {checks:<8} | {status:<10} | {findings}")

            audit_records.append({
                "file": str(fpath),
                "checks_injected": checks,
                "status": "hardened" if checks > 0 else "clean",
                "findings": res.get("check_locations", [])
            })
        except Exception as e:
            print(f"{disp_name:<35} | {'0':<8} | {'❌ ERROR':<10} | {str(e)[:30]}")

    print("-" * 75)
    print(f"Audit Summary: {len(files)} files scanned | {total_vulnerable} vulnerable | {total_checks} guards injected")
    print("=" * 75)

    if args.report:
        report_p = Path(args.report)
        from datetime import datetime
        report_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "scope": str(target_dir),
            "files_scanned": len(files),
            "vulnerable_files": total_vulnerable,
            "guards_injected": total_checks,
            "records": audit_records
        }
        with open(report_p, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"📄 Audit report exported to: {report_p}")

    if getattr(args, "sarif", None):
        from server.mcp_server import export_sarif_report
        sarif_p = Path(args.sarif)
        export_sarif_report(audit_records, str(sarif_p))
        print(f"🛡️  SARIF 2.1.0 report exported to: {sarif_p}")



def cmd_verify(args):
    p1 = Path(args.orig)
    p2 = Path(args.opt)

    if not p1.exists() or not p2.exists():
        print(f"❌ Error: Missing file(s): {p1} or {p2}")
        sys.exit(1)

    print(f"\n🔬 Formally verifying translation:")
    print(f"   Source IR: {p1}")
    print(f"   Target IR: {p2}")

    res = validate_translation(str(p1), str(p2), timeout=args.timeout)

    print("\n" + "=" * 65)
    print("🔬 FORMAL VERIFICATION VERDICT")
    print("=" * 65)
    print(f"Verdict: {res['verdict']}")
    print(f"Proved:  {res['proved']}")
    if res.get("counterexample"):
        print(f"\n⚠️  Counterexample Discovered:\n{res['counterexample']}")
    print("\nFull Validator Trace:")
    print(res["output"])
    print("=" * 65)


def cmd_demo(args):
    demo_name = args.name.lower()
    demo_map = {
        "midpoint": "demo/the_demo.py",
        "java": "demo/the_demo.py",
        "overflow": "demo/fail_catch_prove.py",
        "catch": "demo/fail_catch_prove.py",
        "retry": "demo/retry_demo.py",
        "ipcp": "demo/ipcp_demo.py",
        "full": "demo/full_pipeline_demo.py",
        "cegar": "demo/granite_cegar_demo.py",
        "comprehensive": "demo/comprehensive_demo.py"
    }

    if demo_name not in demo_map:
        print(f"❌ Unknown demo '{demo_name}'. Available demos:")
        for k in sorted(demo_map.keys()):
            print(f"   • {k}")
        sys.exit(1)

    target_script = Path(__file__).parent / demo_map[demo_name]
    print(f"🚀 Running demo: {demo_name} ({target_script.name})...\n")
    import subprocess
    subprocess.run([sys.executable, str(target_script)])


def cmd_verify_cert(args):
    cert_path = Path(args.cert)
    if not cert_path.exists():
        print(f"❌ Error: Certificate file not found: {cert_path}")
        sys.exit(1)

    vault = SafetyVault()
    res = vault.verify_certificate(str(cert_path), args.binary)

    print("\n" + "=" * 65)
    print("🔐 CRYPTOGRAPHIC PROOF VERIFICATION")
    print("=" * 65)
    print(f"Certificate ID: {res.certificate_id}")
    print(f"Authentic:      {'✅ VALID' if res.valid else '❌ INVALID'}")
    print(f"Verified At:    {res.verified_at}")
    if res.issues:
        print("⚠️  Issues Discovered:")
        for issue in res.issues:
            print(f"   • {issue}")
    else:
        print("🛡️  All cryptographic hashes and SMT verdicts verified successfully.")
    print("=" * 65)


def cmd_doctor(args):
    import platform
    import shutil
    import subprocess

    print("\n" + "=" * 65)
    print("🩺 ECSTASY SYSTEM & TOOLCHAIN DIAGNOSTICS")
    print("=" * 65)

    # 1. OS & Architecture
    print(f"🖥️  OS / Architecture:  {platform.system()} {platform.machine()} ({platform.platform()})")
    print(f"🐍 Python Runtime:     {sys.version.split()[0]} ({sys.executable})")

    # 2. Clang Compiler
    clang_path = shutil.which("clang")
    if clang_path:
        try:
            ver = subprocess.run([clang_path, "--version"], capture_output=True, text=True, timeout=5).stdout.splitlines()[0]
            print(f"🔨 Clang Compiler:     ✅ {ver} ({clang_path})")
        except Exception:
            print(f"🔨 Clang Compiler:     ✅ Found at {clang_path}")
    else:
        print("🔨 Clang Compiler:     ❌ Not found in PATH")

    # 3. LLVM Opt
    opt_path = shutil.which("opt")
    if not opt_path:
        for cand in ("/opt/homebrew/opt/llvm/bin/opt", "/usr/local/opt/llvm/bin/opt"):
            if os.path.exists(cand):
                opt_path = cand
                break
    if opt_path:
        print(f"⚡ LLVM Opt:           ✅ Found at {opt_path}")
    elif clang_path:
        print(f"⚡ LLVM Optimizer:     ✅ Built-in Clang LLVM IR -O2 pipeline ({clang_path} -O2 -x ir)")
    else:
        print("⚡ LLVM Opt:           ⚠️  Not in PATH (optional for raw SMT verification)")


    # 4. Z3 SMT Solver
    try:
        import z3
        z3_ver = z3.get_version_string() if hasattr(z3, "get_version_string") else getattr(z3, "__version__", "unknown")
        print(f"📐 Z3 SMT Solver:      ✅ Installed (v{z3_ver})")
    except ImportError:
        print("📐 Z3 SMT Solver:      ❌ z3-solver not installed")

    # 5. Alive2 Translation Validator
    alive_path = shutil.which("alive-tv") or ("/opt/homebrew/bin/alive-tv" if os.path.exists("/opt/homebrew/bin/alive-tv") else None)
    if alive_path:
        print(f"🔬 Alive2 Validator:   ✅ Found at {alive_path}")
    else:
        print("🔬 Alive2 Validator:   ℹ️  Native binary not found — using Pure-Python Z3 SMT Engine")

    # 6. Safety Vault Key
    key_dir = Path.home() / ".ecstasy"
    key_file = key_dir / "signing.key"
    if key_file.exists():
        print(f"🔐 Cryptographic Key:  ✅ Configured ({key_file})")
    else:
        print(f"🔐 Cryptographic Key:  ℹ️  Will be generated automatically on first cert export")

    # 7. IBM watsonx AI
    watson_key = os.getenv("WATSONX_APIKEY")
    if watson_key:
        print(f"🧠 watsonx AI API:     ✅ API Key configured ({watson_key[:4]}...{watson_key[-4:]})")
    else:
        print("🧠 watsonx AI API:     ℹ️  WATSONX_APIKEY not set (running in deterministic offline mode)")

    print("=" * 65)


def cmd_check_memory(args):
    input_path = Path(args.target)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)

    print(f"\n🛡️  Analyzing Memory Safety for: {input_path.name}")
    content = input_path.read_text()
    if input_path.suffix in (".c", ".cpp", ".cc"):
        compile_res = compile_to_ir(content, input_path.name)
        if not compile_res["success"]:
            print(f"❌ Clang compilation error: {compile_res.get('error')}")
            sys.exit(1)
        ir_code = compile_res["ir"]
    else:
        ir_code = content

    from server.mcp_server import apply_memory_safety
    safety_res = apply_memory_safety(ir_code, use_ai=not args.offline)

    print("\n" + "=" * 65)
    print("🛡️  MEMORY SAFETY AUDIT REPORT")
    print("=" * 65)
    print(f"Checks Injected:  {safety_res.get('checks_added', 0)}")
    print(f"Hardened Applied: {'✅ YES' if safety_res.get('safety_applied') else 'ℹ️  CLEAN (No vulnerabilities)'}")
    locations = safety_res.get('check_locations', [])
    if locations:
        print("📍 Vulnerability Locations Addressed:")
        for loc in locations:
            print(f"   • {loc}")
    if args.output:
        out_p = Path(args.output)
        out_p.write_text(safety_res.get("hardened_ir", ir_code))
        print(f"📄 Hardened IR exported to: {out_p}")
    print("=" * 65)


def cmd_ui(args):
    print(f"🚀 Launching Ecstasy Dark Terminal IDE on port {args.port}...")
    import subprocess
    ui_script = Path(__file__).parent / "frontend" / "app.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(ui_script),
        "--server.port", str(args.port),
        "--server.headless", "true"
    ])


def cmd_benchmark(args):
    from engine.corpus_benchmark import run_corpus_benchmark

    target = Path(args.path)
    if not target.exists():
        print(f"❌ Error: Benchmark path not found: {target}")
        sys.exit(1)

    res = run_corpus_benchmark(target)
    print("\n" + "=" * 88)
    print("⚡ ECSTASY WHOLE-CORPUS OPTIMIZATION, CWE SECURITY & Z3 FORMAL VERIFICATION BENCHMARK")
    print(f"📁 Target Corpus: {res['scope']} ({res['files_benchmarked']} file(s))")
    print("=" * 88)
    print(f"{'FILE':<32} | {'-O0 IR':<7} | {'OPT IR':<7} | {'REDUCED':<8} | {'CWEs':<5} | {'VERDICT':<8} | {'TIME'}")
    print("-" * 88)
    for rec in res["records"]:
        fname = rec["file"]
        if len(fname) > 31:
            fname = "..." + fname[-28:]
        print(
            f"{fname:<32} | {rec['orig_instructions']:<7} | {rec['opt_instructions']:<7} | "
            f"{rec['reduction_pct']:>6.1f}% | {rec['cwe_guards']:<5} | {rec['verdict']:<8} | {rec['elapsed_ms']:.0f}ms"
        )
    print("-" * 88)
    print(
        f"TOTAL / AVG                      | {res['total_orig_instructions']:<7} | "
        f"{res['total_opt_instructions']:<7} | {res['overall_reduction_pct']:>6.1f}% | "
        f"{res['total_cwe_guards']:<5} | {res['proved_files']}/{res['files_benchmarked']} PROVED | "
        f"{res['total_elapsed_ms']:.0f}ms"
    )
    print("=" * 88)

    if args.report:
        out_p = Path(args.report)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"📄 Benchmark report exported to: {out_p}")


def main():
    parser = argparse.ArgumentParser(
        description="Ecstasy - Formally Verified AI Compiler Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # compile
    compile_p = subparsers.add_parser("compile", help="Compile and formally verify a C file")
    compile_p.add_argument("source", help="Path to C source file")
    compile_p.add_argument("-o", "--output", help="Output binary path")
    compile_p.add_argument("--retries", type=int, default=3, help="Max AI retry budget")
    compile_p.add_argument("--advanced", action="store_true", help="Enable 9-agent pipeline")
    compile_p.add_argument("--cert", action="store_true", help="Generate cryptographic proof certificate")
    compile_p.add_argument("--html", nargs="?", const="True", help="Export executive HTML attestation report")
    compile_p.add_argument("--report", help="Export full compilation audit report as JSON")

    # verify
    verify_p = subparsers.add_parser("verify", help="Formally verify semantic equivalence between two LLVM IR files")
    verify_p.add_argument("orig", help="Original LLVM IR file (.ll)")
    verify_p.add_argument("opt", help="Transformed LLVM IR file (.ll)")
    verify_p.add_argument("--timeout", type=int, default=60, help="SMT timeout in seconds")

    # verify-cert
    cert_p = subparsers.add_parser("verify-cert", help="Verify authenticity and integrity of a proof certificate")
    cert_p.add_argument("cert", help="Path to proof certificate JSON file")
    cert_p.add_argument("-b", "--binary", help="Optional path to binary to verify SHA-256 hash")

    # check-memory
    mem_p = subparsers.add_parser("check-memory", help="Audit C or LLVM IR for memory safety & buffer overflow protection")
    mem_p.add_argument("target", help="Path to C (.c) or LLVM IR (.ll) file")
    mem_p.add_argument("-o", "--output", help="Optional path to output hardened IR")
    mem_p.add_argument("--offline", action="store_true", help="Run deterministic checks without cloud AI")

    # audit
    audit_p = subparsers.add_parser("audit", help="Audit an entire directory or project for memory vulnerabilities")
    audit_p.add_argument("path", help="Directory path to recursively scan and audit")
    audit_p.add_argument("--report", help="Export audit findings to JSON report file")
    audit_p.add_argument("--sarif", help="Export audit findings in OASIS SARIF v2.1.0 format")
    audit_p.add_argument("--offline", action="store_true", help="Run deterministic checks without cloud AI")


    # benchmark
    bench_p = subparsers.add_parser("benchmark", help="Benchmark IR optimization, CWE security audit, and Z3 verification across a corpus")
    bench_p.add_argument("path", nargs="?", default="demo_corpus", help="File or directory corpus path (default: demo_corpus)")
    bench_p.add_argument("--report", help="Optional path to export benchmark results as JSON")

    # doctor
    subparsers.add_parser("doctor", help="Run system and toolchain diagnostic checks")

    # demo
    demo_p = subparsers.add_parser("demo", help="Run interactive demonstration scenarios")
    demo_p.add_argument("name", help="Demo name: midpoint, overflow, retry, ipcp, full, cegar, comprehensive")

    # ui
    ui_p = subparsers.add_parser("ui", help="Launch Streamlit Web IDE")
    ui_p.add_argument("--port", type=int, default=8501, help="Port to bind Streamlit server")

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "compile":
        cmd_compile(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "verify-cert":
        cmd_verify_cert(args)
    elif args.command == "check-memory":
        cmd_check_memory(args)
    elif args.command == "audit":
        cmd_audit(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "ui":
        cmd_ui(args)


if __name__ == "__main__":
    main()

