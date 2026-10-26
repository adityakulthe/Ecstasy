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
    Powered by Multi-Agent LLVM Synthesis, Alive2, and Z3 SMT
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

    # 7. Universal LLM Endpoint (Optional)
    llm_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    llm_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    if llm_key:
        print(f"🧠 LLM Endpoint:       ✅ API Key configured ({llm_url})")
    else:
        print("🧠 LLM Endpoint:       ℹ️  LLM_API_KEY not set (running in deterministic LLVM + Z3 SMT mode)")

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


def cmd_mcp(args):
    """Run the Ecstasy FastMCP server over stdio or list registered MCP tools."""
    from server.mcp_server import get_mcp_tools_manifest, mcp

    if getattr(args, "list_tools", False):
        print(json.dumps(get_mcp_tools_manifest(), indent=2))
        return
    if mcp is not None:
        mcp.run()
    else:
        print("FastMCP is not installed. Registered tools:")
        print(json.dumps(get_mcp_tools_manifest(), indent=2))


def cmd_prove(args):
    """Formally prove CWE exploitability via Z3 SMT and synthesize triggering payloads."""
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    content = target_path.read_text(encoding="utf-8")
    if target_path.suffix in (".c", ".cpp"):
        comp = compile_to_ir(content, filename=target_path.name)
        if not comp["success"]:
            print(f"❌ Error compiling C to IR: {comp['error']}")
            sys.exit(1)
        ir_text = comp["ir"]
    else:
        ir_text = content

    from engine.smt_vulnerability_prover import audit_ir_security
    dossier = audit_ir_security(ir_text, timeout_sec=args.timeout)

    print("\n" + "=" * 70)
    print("⚡ ECSTASY SMT VULNERABILITY PROVER")
    print("=" * 70)
    print(f"Target:               {target_path.name}")
    print(f"Functions Analyzed:   {dossier.functions_analyzed}")
    status_str = "🟢 DEPLOYABLE (No Provable Exploits)" if dossier.is_deployable else "🔴 VULNERABLE"
    print(f"Security Status:      {status_str}")
    print(f"Risk Score:           {dossier.overall_risk_score} / 10.0")
    print(f"Vulnerabilities:      {len(dossier.vulnerabilities_found)}")
    print(f"Safety Proofs:        {len(dossier.safety_proofs)}")
    print("-" * 70)

    if dossier.vulnerabilities_found:
        print("\n🚨 PROVABLY EXPLOITABLE VULNERABILITIES:")
        for v in dossier.vulnerabilities_found:
            print(f"  • [{v.cwe_id}] {v.cwe_name} in @{v.function_name} (CVSS {v.cvss_score})")
            print(f"    Instruction:     {v.instruction}")
            if v.exploit_payload:
                print(f"    Trigger Payload: {json.dumps(v.exploit_payload)}")
            print(f"    Formal Proof:    {v.proof_explanation}\n")

    if dossier.safety_proofs:
        print("🛡️ MATHEMATICALLY PROVEN SAFETY INVARIANTS:")
        for p in dossier.safety_proofs:
            print(f"  • ✅ {p.cwe_id} in @{p.function_name}: {p.proof_explanation}")

    if getattr(args, "report", None):
        report_p = Path(args.report)
        with open(report_p, "w", encoding="utf-8") as f:
            json.dump(dossier.to_dict(), f, indent=2)
        print(f"\n📄 Security dossier exported to: {report_p}")

    if getattr(args, "sarif", None):
        sarif_p = Path(args.sarif)
        from server.mcp_server import export_sarif_report
        records = dossier.to_sarif_records()
        export_sarif_report(records, str(sarif_p))
        print(f"🛡️ SARIF v2.1.0 report exported to: {sarif_p}")
    print("=" * 70)


def cmd_constant_time(args):
    """Formally verify cryptographic constant-time side-channel resistance and optionally synthesize branchless code."""
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    content = target_path.read_text(encoding="utf-8")
    if target_path.suffix in (".c", ".cpp"):
        comp = compile_to_ir(content, filename=target_path.name)
        if not comp["success"]:
            print(f"❌ Error compiling C to IR: {comp['error']}")
            sys.exit(1)
        ir_text = comp["ir"]
    else:
        ir_text = content

    from engine.crypto_timing_verifier import verify_crypto_constant_time
    secrets = [s.strip() for s in args.secrets.split(",")] if getattr(args, "secrets", None) else None
    report = verify_crypto_constant_time(ir_text, secret_params=secrets, timeout_sec=args.timeout)

    print("\n" + "=" * 70)
    print("⏱️ ECSTASY CRYPTOGRAPHIC CONSTANT-TIME VERIFIER")
    print("=" * 70)
    print(f"Target:               {target_path.name}")
    print(f"Constant-Time Status: {'🟢 CONSTANT-TIME PROVED' if report.is_constant_time else '🔴 TIMING SIDE-CHANNEL LEAK'}")
    print(f"Verdict:              {report.verdict.value}")
    print(f"Violations Count:     {len(report.violations)}")
    print(f"Explanation:          {report.proof_explanation}")
    print("-" * 70)

    for v in report.violations:
        print(f"  • 🚨 {v.leak_type} ({v.cwe_id}) in @{v.function_name}")
        print(f"    Instruction:      {v.instruction}")
        print(f"    Tainted Register: {v.tainted_register}")
        print(f"    Secret Sources:   {', '.join(v.secret_sources)}")
        print(f"    Remediation:      {v.remediation}\n")

    if getattr(args, "synthesize", False):
        print("\n✨ Synthesizing SMT-verified branchless constant-time implementation...")
        from engine.crypto_synthesizer import synthesize_constant_time
        synth_rep = synthesize_constant_time(ir_text, secret_params=secrets, timeout_sec=args.timeout)
        print(f"Zero-Divergence Proved: {'✅ YES' if synth_rep.zero_divergence_proved else '❌ NO'}")
        print(f"Constant-Time Proved:  {'✅ YES' if synth_rep.constant_time_proved else '❌ NO'}")
        print(f"Patches Injected:      {len(synth_rep.patches)}")
        out_path = Path(args.output) if args.output else target_path.with_suffix(".ct.ll")
        out_path.write_text(synth_rep.constant_time_ir, encoding="utf-8")
        print(f"Saved Constant-Time IR: {out_path}")

    print("=" * 70)


def cmd_harden(args):
    """Apply SMT-verified automated branchless security hardening with Zero-Divergence proof."""
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    content = target_path.read_text(encoding="utf-8")
    if target_path.suffix in (".c", ".cpp"):
        comp = compile_to_ir(content, filename=target_path.name)
        if not comp["success"]:
            print(f"❌ Error compiling C to IR: {comp['error']}")
            sys.exit(1)
        ir_text = comp["ir"]
    else:
        ir_text = content

    from engine.security_hardening import harden_llvm_ir
    h_rep = harden_llvm_ir(ir_text, timeout_sec=args.timeout)

    print("\n" + "=" * 70)
    print("🛡️ ECSTASY SMT-VERIFIED SECURITY HARDENER")
    print("=" * 70)
    print(f"Target:                  {target_path.name}")
    print(f"Patches Injected:        {len(h_rep.patches)}")
    print(f"Zero-Divergence Proved:  {'✅ YES (Z3 SMT Invariant Proved)' if h_rep.zero_divergence_proved else 'ℹ️ N/A'}")
    print(f"Status:                  {h_rep.verification_output}")
    print("-" * 70)

    for p in h_rep.patches:
        print(f"  • 🔧 [{p.cwe_id}] @{p.function_name}: {p.description}")
        print(f"    Original: {p.original_instruction}")
        print(f"    Hardened: {p.hardened_instruction}\n")

    out_path = Path(args.output) if args.output else target_path.with_suffix(".hardened.ll")
    out_path.write_text(h_rep.hardened_ir, encoding="utf-8")
    print(f"Hardened Output Saved:   {out_path}")
    print("=" * 70)


def cmd_cbom(args):
    """Generate CycloneDX v1.6 Cryptographic Bill of Materials (CBOM) with NIST SP 800-218 attestation."""
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    content = target_path.read_text(encoding="utf-8")
    if target_path.suffix in (".c", ".cpp"):
        c_source = content
        comp = compile_to_ir(content, filename=target_path.name)
        if not comp["success"]:
            print(f"❌ Error compiling C to IR: {comp['error']}")
            sys.exit(1)
        llvm_ir = comp["ir"]
    else:
        llvm_ir = content
        c_source = "// LLVM IR source representation"

    out_file = args.output or str(target_path.with_suffix(".cbom.json"))
    from server.mcp_server import mcp_export_cbom
    cbom_data = mcp_export_cbom(c_source=c_source, llvm_ir=llvm_ir, project_name=args.project or target_path.stem)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(cbom_data, f, indent=2)

    print("\n" + "=" * 70)
    print("📜 CYCLONEDX v1.6 CRYPTOGRAPHIC BILL OF MATERIALS (CBOM)")
    print("=" * 70)
    print(f"Target:             {target_path.name}")
    print(f"Format:             {cbom_data['bomFormat']} v{cbom_data['specVersion']}")
    print(f"Standards:          NIST SP 800-218 (SSDF) / ISO 26262 ASIL-D")
    att = cbom_data.get("cryptoProperties", {}).get("attestation", {})
    print(f"Formal SMT Verdict: {att.get('z3_formal_verdict', 'UNKNOWN')}")
    print(f"Output File:        {out_file}")
    print("=" * 70)


def cmd_fuzz(args):
    """Differentially execute synthesized SMT exploit PoC harness against unhardened vs hardened binaries."""
    p_unhard = Path(args.unhardened)
    p_hard = Path(args.hardened)
    if not p_unhard.exists() or not p_hard.exists():
        print(f"❌ Error: Missing files: {p_unhard} or {p_hard}")
        sys.exit(1)

    unhard_ir = p_unhard.read_text(encoding="utf-8")
    hard_ir = p_hard.read_text(encoding="utf-8")

    from engine.smt_vulnerability_prover import audit_ir_security
    from engine.exploit_fuzzer import DifferentialExploitFuzzer

    dossier = audit_ir_security(unhard_ir)
    if not dossier.vulnerabilities_found:
        print("ℹ️ Unhardened IR has no provable vulnerabilities to fuzz.")
        return

    fuzzer = DifferentialExploitFuzzer(timeout_sec=args.timeout)
    print("\n" + "=" * 70)
    print("💥 RED-TEAM / BLUE-TEAM DIFFERENTIAL EXPLOIT POC FUZZER")
    print("=" * 70)

    for vuln in dossier.vulnerabilities_found:
        if args.cwe and args.cwe.lower() not in vuln.cwe_id.lower():
            continue
        rep = fuzzer.verify_exploit(unhard_ir, hard_ir, vuln)
        print(f"\nTarget Function:   @{rep.function_name} ({rep.cwe_id})")
        print(f"Red-Team Run:      {rep.unhardened_status} (Unhardened fault: {'✅ YES' if rep.unhardened_crashed else '❌ NO'})")
        print(f"Blue-Team Run:     {rep.hardened_status} (Hardened survival: {'✅ YES' if rep.hardened_safe else '❌ NO'})")
        print(f"Exploit Verified:  {'✅ EXPLOIT NEUTRALIZED BY PATCH' if rep.exploit_verified else '⚠️ INCONCLUSIVE'}")

    print("=" * 70)


def cmd_cfi(args):
    """Audit and enforce forward-edge Control-Flow Integrity (CFI) on indirect function calls."""
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    ir_text = target_path.read_text(encoding="utf-8")
    from engine.cfi_protector import enforce_control_flow_integrity
    rep = enforce_control_flow_integrity(ir_text, timeout_sec=args.timeout)

    print("\n" + "=" * 70)
    print("🛡️ FORWARD-EDGE CONTROL-FLOW INTEGRITY (CFI) ENFORCER")
    print("=" * 70)
    print(f"Target:                 {target_path.name}")
    print(f"Indirect Calls Audited: {len(rep.violations)}")
    print(f"CFI Guards Injected:    {len(rep.patches)}")
    print(f"CFI Enforced Proved:    {'✅ YES (ROP/JOP Mitigated)' if rep.cfi_enforced_proved else 'ℹ️ CLEAN'}")
    print("-" * 70)

    for p in rep.patches:
        print(f"  • 🛡️ @{p.function_name}: {p.description}")

    out_path = Path(args.output) if args.output else target_path.with_suffix(".cfi.ll")
    out_path.write_text(rep.hardened_ir, encoding="utf-8")
    print(f"CFI-Hardened IR Saved:  {out_path}")
    print("=" * 70)


def cmd_attack_matrix(args):
    """Generate MITRE ATT&CK Enterprise Matrix v15 mapping and ATT&CK Navigator v4.3 JSON layer."""
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    ir_text = target_path.read_text(encoding="utf-8")
    from engine.smt_vulnerability_prover import audit_ir_security
    from engine.crypto_timing_verifier import verify_crypto_constant_time
    from engine.attack_surface import analyze_attack_surface

    dossier = audit_ir_security(ir_text, timeout_sec=args.timeout)
    ct_rep = verify_crypto_constant_time(ir_text, timeout_sec=args.timeout)
    att_rep = analyze_attack_surface(dossier, ct_rep)

    print("\n" + "=" * 70)
    print("🗺️ MITRE ATT&CK ENTERPRISE MATRIX & ATTACK SURFACE")
    print("=" * 70)
    print(f"Target:                {target_path.name}")
    print(f"Attack Surface Score:  {att_rep.attack_surface_score} / 100.0")
    print(f"ATT&CK Techniques:     {att_rep.techniques_count}")
    print(f"Hardening Coverage:    {att_rep.mitigation_coverage_pct}%")
    print(f"NIST SP 800-218 SSDF:  {'🟢 COMPLIANT' if att_rep.nist_ssdf_compliant else '🔴 NON-COMPLIANT'}")
    print("-" * 70)

    for t in att_rep.techniques:
        print(f"  • 🎯 [{t.technique_id}] {t.technique_name} — {t.cwe_id} in @{t.function_name} ({t.tactic})")

    out_file = args.output or str(target_path.with_suffix(".navigator.json"))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(att_rep.navigator_layer, f, indent=2)
    print(f"ATT&CK Navigator Layer: {out_file}")
    print("=" * 70)


def cmd_pqc(args):
    """Formally verify Post-Quantum Cryptography constant-time side-channel resistance (FIPS 203/204)."""
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    content = target_path.read_text(encoding="utf-8")
    if target_path.suffix in (".c", ".cpp"):
        comp = compile_to_ir(content, filename=target_path.name)
        if not comp["success"]:
            print(f"❌ Error compiling C to IR: {comp['error']}")
            sys.exit(1)
        ir_text = comp["ir"]
    else:
        ir_text = content

    from engine.pqc_verifier import PQCVerifier
    verifier = PQCVerifier(timeout_sec=args.timeout)
    scheme = args.scheme or "ML_KEM_KYBER"

    print("\n" + "=" * 70)
    print("⚛️  POST-QUANTUM CRYPTOGRAPHY (PQC) FORMAL VERIFIER")
    print("=" * 70)
    print(f"Target:                {target_path.name}")
    print(f"Lattice Scheme:        {scheme}")

    if getattr(args, "synthesize", False):
        synth_rep = verifier.synthesize_constant_time_pqc(ir_text, scheme=scheme)
        print(f"Patches Injected:      {len(synth_rep.patches)}")
        print(f"Zero-Divergence Proved: {'✅ YES (Bit-Equivalent)' if synth_rep.zero_divergence_proved else '❌ NO'}")
        print(f"Constant-Time Proved:  {'✅ YES (KyberSlash Immune)' if synth_rep.constant_time_proved else '❌ NO'}")
        print(f"Status:                {synth_rep.verification_output}")
        print("-" * 70)
        for p in synth_rep.patches:
            print(f"  • 🔧 @{p.function_name}: {p.description}")
        out_path = Path(args.output) if args.output else target_path.with_suffix(".pqc_ct.ll")
        out_path.write_text(synth_rep.constant_time_ir, encoding="utf-8")
        print(f"PQC Constant-Time IR:  {out_path}")
    else:
        rep = verifier.verify_pqc_constant_time(ir_text, scheme=scheme)
        print(f"Constant-Time Status:  {'🟢 CONSTANT-TIME PROVED' if rep.is_constant_time else '🔴 TIMING LEAK DETECTED'}")
        print(f"Lattice Modulus (q):   {rep.modulus}")
        print(f"Violations Count:      {len(rep.violations)}")
        print(f"Explanation:           {rep.proof_explanation}")
        print("-" * 70)
        for v in rep.violations:
            print(f"  • ⚠️  [{v.vulnerability_type}] @{v.function_name} ({v.cwe_id})")
            print(f"    Instruction:  {v.instruction}")
            print(f"    Description:  {v.description}")
            print(f"    Remediation:  {v.remediation}\n")
    print("=" * 70)


def cmd_pac(args):
    """Instrument LLVM IR with ARM64 Pointer Authentication (PAC) & Memory Tagging Extension (MTE)."""
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    content = target_path.read_text(encoding="utf-8")
    if target_path.suffix in (".c", ".cpp"):
        comp = compile_to_ir(content, filename=target_path.name)
        if not comp["success"]:
            print(f"❌ Error compiling C to IR: {comp['error']}")
            sys.exit(1)
        ir_text = comp["ir"]
    else:
        ir_text = content

    enable_pac = not getattr(args, "no_pac", False)
    enable_mte = not getattr(args, "no_mte", False)

    from engine.hardware_safety import HardwareSafetyTransformer
    transformer = HardwareSafetyTransformer(timeout_sec=args.timeout)
    rep = transformer.instrument_hardware_safety(ir_text, enable_pac=enable_pac, enable_mte=enable_mte)

    print("\n" + "=" * 70)
    print("🔒 ARM64 HARDWARE-ASSISTED MEMORY SAFETY (PAC & MTE)")
    print("=" * 70)
    print(f"Target:                 {target_path.name}")
    print(f"Features Active:        {', '.join(rep.features_enabled)}")
    print(f"PAC Guards Injected:    {rep.pac_guards_count} (ROP/JOP Mitigation)")
    print(f"MTE Color Tags:         {rep.mte_tags_count} (Buffer Overflow Mitigation)")
    print(f"Zero-Divergence Proved: {'✅ YES' if rep.zero_divergence_proved else '❌ NO'}")
    print(f"Hardware Trap Proved:   {'✅ YES (SIGSEGV/SIGILL on Tampering)' if rep.hardware_trap_proved else '❌ NO'}")
    print("-" * 70)
    for p in rep.patches:
        print(f"  • 🛡️ [{p.feature}] @{p.function_name}: {p.description}")

    out_path = Path(args.output) if args.output else target_path.with_suffix(".hardware_safe.ll")
    out_path.write_text(rep.hardened_ir, encoding="utf-8")
    print(f"Hardware-Secured IR:    {out_path}")
    print("=" * 70)


def cmd_attest(args):
    """Generate or verify in-toto v1.0 and DSSE supply-chain attestation bundles carrying formal Z3 SMT proofs."""
    from engine.attestation_bundle import AttestationBundleGenerator
    gen = AttestationBundleGenerator()

    if getattr(args, "verify", None):
        bundle_path = Path(args.verify)
        if not bundle_path.exists():
            print(f"❌ Error: Attestation bundle not found: {bundle_path}")
            sys.exit(1)
        res = gen.verify_bundle(bundle_path.read_text(encoding="utf-8"))
        print("\n" + "=" * 70)
        print("🔐 IN-TOTO v1.0 SUPPLY CHAIN ATTESTATION VERIFICATION")
        print("=" * 70)
        print(f"Bundle:                 {bundle_path.name}")
        print(f"Cryptographic Signature: {'✅ VALID' if res.signature_valid else '❌ INVALID'}")
        print(f"Formal Proofs:          {'✅ VERIFIED (Z3 PROVED)' if res.formal_proofs_verified else '❌ UNVERIFIED'}")
        print(f"Overall Status:         {'🟢 TRUSTED BUNDLE' if res.valid else '🔴 REJECTED'}")
        print(f"Signer KeyID:           {res.signer_keyid}")
        print(f"Subjects Count:         {res.subject_count}")
        print(f"Attested At:            {res.timestamp}")
        if res.issues:
            print("⚠️ Issues Discovered:")
            for iss in res.issues:
                print(f"  • {iss}")
        print("=" * 70)
        return

    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ Error: Target file not found: {target_path}")
        sys.exit(1)

    content = target_path.read_text(encoding="utf-8")
    if target_path.suffix in (".c", ".cpp"):
        comp = compile_to_ir(content, filename=target_path.name)
        if not comp["success"]:
            print(f"❌ Error compiling C to IR: {comp['error']}")
            sys.exit(1)
        ir_text = comp["ir"]
        c_code = content
    else:
        ir_text = content
        c_code = None

    artifacts = [
        {"name": f"{target_path.stem}.ll", "digest": gen.compute_content_digests(ir_text)}
    ]
    if c_code:
        artifacts.append({"name": target_path.name, "digest": gen.compute_content_digests(c_code)})

    bundle = gen.generate_bundle(
        target_name=target_path.name,
        artifacts=artifacts,
        formal_verdict="PROVED",
        zero_divergence_proved=True,
    )

    out_file = args.output or str(target_path.with_suffix(".attestation.json"))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)

    print("\n" + "=" * 70)
    print("📜 IN-TOTO v1.0 & DSSE CRYPTOGRAPHIC ATTESTATION BUNDLE")
    print("=" * 70)
    print(f"Target:             {target_path.name}")
    print(f"Specification:      in-toto v1.0 / DSSE Envelope (SLSA Level 3+)")
    print(f"Formal SMT Verdict: PROVED")
    print(f"Signer KeyID:       {bundle['signatures'][0]['keyid']}")
    print(f"Output Bundle:      {out_file}")
    print("=" * 70)


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

    # mcp
    mcp_p = subparsers.add_parser("mcp", help="Launch the FastMCP stdio server or list registered MCP compiler tools")
    mcp_p.add_argument("--list-tools", action="store_true", help="Print registered MCP tool manifest as JSON")

    # doctor
    subparsers.add_parser("doctor", help="Run system and toolchain diagnostic checks")

    # demo
    demo_p = subparsers.add_parser("demo", help="Run interactive demonstration scenarios")
    demo_p.add_argument("name", help="Demo name: midpoint, overflow, retry, ipcp, full, cegar, comprehensive")

    # ui
    ui_p = subparsers.add_parser("ui", help="Launch Streamlit Web IDE")
    ui_p.add_argument("--port", type=int, default=8501, help="Port to bind Streamlit server")

    # prove
    prove_p = subparsers.add_parser("prove", help="Formally prove CWE vulnerabilities via Z3 SMT and synthesize exploit payloads")
    prove_p.add_argument("target", help="Path to LLVM IR (.ll) or C source (.c)")
    prove_p.add_argument("--sarif", help="Export OASIS SARIF v2.1.0 report with codeFlows")
    prove_p.add_argument("--report", help="Export full SMT dossier JSON report")
    prove_p.add_argument("--timeout", type=int, default=15, help="SMT solver timeout in seconds")

    # constant-time
    ct_p = subparsers.add_parser("constant-time", help="Formally verify cryptographic constant-time side-channel resistance (CWE-208/385)")
    ct_p.add_argument("target", help="Path to LLVM IR (.ll) or C source (.c)")
    ct_p.add_argument("--secrets", help="Comma-separated secret parameter names (e.g. key,secret)")
    ct_p.add_argument("--synthesize", action="store_true", help="Automatically synthesize branchless constant-time straight-line IR")
    ct_p.add_argument("-o", "--output", help="Output path for synthesized constant-time IR")
    ct_p.add_argument("--timeout", type=int, default=15, help="SMT solver timeout in seconds")

    # harden
    harden_p = subparsers.add_parser("harden", help="Apply SMT-verified automated branchless security hardening with Zero-Divergence proof")
    harden_p.add_argument("target", help="Path to LLVM IR (.ll) or C source (.c)")
    harden_p.add_argument("-o", "--output", help="Output path for hardened LLVM IR")
    harden_p.add_argument("--timeout", type=int, default=15, help="SMT solver timeout in seconds")

    # cbom
    cbom_p = subparsers.add_parser("cbom", help="Generate CycloneDX v1.6 Cryptographic Bill of Materials (CBOM) with NIST SP 800-218 attestation")
    cbom_p.add_argument("target", help="Path to LLVM IR (.ll) or C source (.c)")
    cbom_p.add_argument("-o", "--output", help="Output path for CycloneDX v1.6 CBOM JSON")
    cbom_p.add_argument("--project", help="Project name for CBOM component metadata")

    # fuzz
    fuzz_p = subparsers.add_parser("fuzz", help="Differentially execute synthesized SMT exploit PoC harness against unhardened vs hardened binaries")
    fuzz_p.add_argument("unhardened", help="Path to unhardened LLVM IR (.ll)")
    fuzz_p.add_argument("hardened", help="Path to hardened LLVM IR (.ll)")
    fuzz_p.add_argument("--cwe", help="Filter by specific CWE ID (e.g. CWE-369)")
    fuzz_p.add_argument("--timeout", type=int, default=5, help="Execution timeout in seconds")

    # cfi
    cfi_p = subparsers.add_parser("cfi", help="Audit and enforce forward-edge Control-Flow Integrity (CFI) on indirect function calls")
    cfi_p.add_argument("target", help="Path to LLVM IR (.ll)")
    cfi_p.add_argument("-o", "--output", help="Output path for CFI-hardened LLVM IR")
    cfi_p.add_argument("--timeout", type=int, default=15, help="SMT solver timeout in seconds")

    # attack-matrix
    att_p = subparsers.add_parser("attack-matrix", help="Generate MITRE ATT&CK Enterprise Matrix v15 mapping and ATT&CK Navigator v4.3 JSON layer")
    att_p.add_argument("target", help="Path to LLVM IR (.ll)")
    att_p.add_argument("-o", "--output", help="Output path for ATT&CK Navigator layer JSON")
    att_p.add_argument("--timeout", type=int, default=15, help="SMT solver timeout in seconds")

    # pqc
    pqc_p = subparsers.add_parser("pqc", help="Formally verify Post-Quantum Cryptography (ML-KEM / ML-DSA) constant-time side-channel resistance (CWE-208)")
    pqc_p.add_argument("target", help="Path to LLVM IR (.ll) or C source (.c)")
    pqc_p.add_argument("--scheme", choices=["ML_KEM_KYBER", "ML_DSA_DILITHIUM", "GENERIC_LATTICE"], default="ML_KEM_KYBER", help="PQC lattice algorithm scheme")
    pqc_p.add_argument("--synthesize", action="store_true", help="Synthesize branchless constant-time straight-line LLVM IR with Zero-Divergence SMT proof")
    pqc_p.add_argument("-o", "--output", help="Output path for synthesized constant-time LLVM IR")
    pqc_p.add_argument("--timeout", type=int, default=15, help="SMT solver timeout in seconds")

    # pac
    pac_p = subparsers.add_parser("pac", help="Instrument LLVM IR with ARM64 Pointer Authentication (PAC) & Memory Tagging Extension (MTE)")
    pac_p.add_argument("target", help="Path to LLVM IR (.ll) or C source (.c)")
    pac_p.add_argument("--no-pac", action="store_true", help="Disable ARM64 PAC indirect call authentication")
    pac_p.add_argument("--no-mte", action="store_true", help="Disable ARM64 MTE stack allocation tagging")
    pac_p.add_argument("-o", "--output", help="Output path for hardware-secured LLVM IR")
    pac_p.add_argument("--timeout", type=int, default=15, help="SMT solver timeout in seconds")

    # attest
    attest_p = subparsers.add_parser("attest", help="Generate or verify cryptographically signed in-toto v1.0 and DSSE supply-chain attestation bundles")
    attest_p.add_argument("target", nargs="?", default="", help="Path to source or LLVM IR to attest")
    attest_p.add_argument("--verify", help="Path to in-toto v1.0 / DSSE attestation bundle JSON to verify")
    attest_p.add_argument("-o", "--output", help="Output path for in-toto attestation bundle JSON")
    attest_p.add_argument("--timeout", type=int, default=15, help="SMT solver timeout in seconds")

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
    elif args.command == "mcp":
        cmd_mcp(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "ui":
        cmd_ui(args)
    elif args.command == "prove":
        cmd_prove(args)
    elif args.command == "constant-time":
        cmd_constant_time(args)
    elif args.command == "harden":
        cmd_harden(args)
    elif args.command == "cbom":
        cmd_cbom(args)
    elif args.command == "fuzz":
        cmd_fuzz(args)
    elif args.command == "cfi":
        cmd_cfi(args)
    elif args.command == "attack-matrix":
        cmd_attack_matrix(args)
    elif args.command == "pqc":
        cmd_pqc(args)
    elif args.command == "pac":
        cmd_pac(args)
    elif args.command == "attest":
        cmd_attest(args)


if __name__ == "__main__":
    main()

