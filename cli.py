#!/usr/bin/env python3
"""
Ecstasy CLI - Formally Verified AI Compiler Pipeline
Command-line interface for compiling, optimizing, verifying, and securing C and LLVM code.
"""

import sys
import os
import time
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

    if args.cert:
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

    print("=" * 65)


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


def cmd_ui(args):
    print(f"🚀 Launching Ecstasy Dark Terminal IDE on port {args.port}...")
    import subprocess
    ui_script = Path(__file__).parent / "frontend" / "app.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(ui_script),
        "--server.port", str(args.port),
        "--server.headless", "true"
    ])


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

    # verify
    verify_p = subparsers.add_parser("verify", help="Formally verify semantic equivalence between two LLVM IR files")
    verify_p.add_argument("orig", help="Original LLVM IR file (.ll)")
    verify_p.add_argument("opt", help="Transformed LLVM IR file (.ll)")
    verify_p.add_argument("--timeout", type=int, default=60, help="SMT timeout in seconds")

    # demo
    demo_p = subparsers.add_parser("demo", help="Run interactive demonstration scenarios")
    demo_p.add_argument("name", help="Demo name: midpoint, overflow, retry, ipcp, full, cegar")

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
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "ui":
        cmd_ui(args)


if __name__ == "__main__":
    main()
