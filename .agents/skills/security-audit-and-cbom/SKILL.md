---
name: security-audit-and-cbom
description: >-
  Use this skill when auditing C/C++ files or directories for memory safety vulnerabilities,
  injecting bounds checks with @memory-sentinel, or generating cryptographic proof
  certificates (HMAC-SHA256) and executive HTML attestations.
---

# Security Audit & Cryptographic Bill of Materials (CBOM) Skill

Use this workflow when auditing codebases for memory safety vulnerabilities or generating compliance certificates (EU AI Act / NIST SP 800-218 SSDF / CISA Memory-Safe Roadmaps).

## 1. Batch Security Audit Workflow
Run the CLI audit command across any C/C++ file or directory:
```bash
/Users/adityakulthe/Ecstasy/.venv/bin/python cli.py audit <path> --report audit_report.json
```
- **Detected Vulnerability Classes**:
  - Unbounded pointer arithmetic (`getelementptr` without dominating `icmp ult` guard)
  - Unsafe C library calls (`@strcpy`, `@strcat`, `@gets`, `@sprintf`, `@scanf`)
- **Zero-Token Fast Path**: Pure arithmetic functions without memory operations bypass LLM calls automatically via [`_has_memory_or_unsafe_ops`](file:///Users/adityakulthe/Ecstasy/agents/memory_sentinel.py#L69-L72).

## 2. Cryptographic Attestation & Executive HTML Export
Generate a tamper-evident HMAC-SHA256 certificate and executive HTML report:
```bash
/Users/adityakulthe/Ecstasy/.venv/bin/python cli.py compile <source.c> \
  -o build/program.out \
  --cert build/program.proof.json \
  --html build/program.attestation.html
```
Verify certificate integrity and tamper detection:
```bash
/Users/adityakulthe/Ecstasy/.venv/bin/python cli.py certify --verify build/program.proof.json
```
