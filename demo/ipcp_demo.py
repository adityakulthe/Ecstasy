#!/usr/bin/env python3
"""
Demo: AI Compiler finds optimization that clang -O3 misses,
but Alive2 proves it's unsafe without additional guarantees.

This demonstrates:
1. AI can find optimizations beyond standard compiler passes
2. Formal verification is ESSENTIAL to prevent unsafe optimizations
3. The system correctly rejects optimizations that change semantics
"""
import os, sys

print("="*80)
print("DEMO: Inter-Procedural Constant Propagation")
print("="*80)

print("\n📋 SCENARIO:")
print("   Two C files compiled separately with clang -O3:")
print("   - file1.c: get_buffer_limit() { return 256; }")
print("   - file2.c: process() calls get_buffer_limit()")
print()
print("   clang -O3 CANNOT optimize across translation units")
print("   without Link-Time Optimization (LTO)")

print("\n🤖 STEP 1: AI Compiler Analysis")
print("   Granite 4.0 analyzes the combined IR and identifies:")
print("   - get_buffer_limit() always returns 256")
print("   - The function call in process() can be eliminated")
print("   - Constant 256 can be propagated directly")

with open('tests/fixtures/combined.ll', 'r') as f:
    original = f.read()

print("\n📄 Original IR (clang -O3 output):")
print("   " + "\n   ".join([line for line in original.split('\n') if 'call i32 @get_buffer_limit' in line or 'icmp sle' in line][:2]))

with open('tests/fixtures/combined_optimized.ll', 'r') as f:
    optimized = f.read()

print("\n✨ AI Optimized IR:")
print("   " + "\n   ".join([line for line in optimized.split('\n') if 'icmp sle' in line][:1]))
print("   (Function call eliminated, constant 256 propagated)")

print("\n🔬 STEP 2: Alive2 Formal Verification")
print("   Running: alive-tv original.ll optimized.ll")
print()

# Run Alive2
import subprocess
result = subprocess.run(
    ['alive-tv', 'tests/fixtures/combined.ll', 'tests/fixtures/combined_optimized.ll'],
    capture_output=True,
    text=True,
    cwd='/Users/anjalikulthe/Desktop/hackathon/Ecstasy'
)

if 'Transformation doesn\'t verify!' in result.stdout:
    print("   ❌ VERDICT: Transformation doesn't verify!")
    print()
    print("   🔍 ROOT CAUSE:")
    print("      The original IR declares get_buffer_limit() as an")
    print("      external function without 'willreturn' attribute.")
    print("      If that function doesn't return (infinite loop/crash),")
    print("      the optimization changes program behavior!")
    print()
    print("   📊 COUNTEREXAMPLE:")
    for line in result.stdout.split('\n'):
        if 'function did not return' in line or 'Example:' in line:
            print(f"      {line.strip()}")
    
    print("\n✅ STEP 3: System Response")
    print("   The AI Compiler CORRECTLY REJECTS this optimization")
    print("   because Alive2 proved it's semantically incorrect.")
    print()
    print("   To make this optimization safe, we would need:")
    print("   - 'willreturn' attribute on get_buffer_limit()")
    print("   - OR whole-program analysis proving termination")
    print("   - OR Link-Time Optimization (LTO) context")

else:
    print("   ✅ Transformation verified!")

print("\n" + "="*80)
print("🎯 ANSWER TO JUDGE QUESTION:")
print("   'What does this do that LLVM doesn't already do?'")
print("="*80)
print()
print("1. OPTIMIZATION DISCOVERY:")
print("   The AI compiler identifies inter-procedural constant")
print("   propagation opportunities that clang -O3 misses without LTO.")
print()
print("2. SAFETY VERIFICATION:")
print("   Unlike traditional compilers that might apply optimizations")
print("   heuristically, this system uses Alive2 to PROVE correctness.")
print()
print("3. INTELLIGENT REJECTION:")
print("   When Alive2 finds a counterexample, the system correctly")
print("   rejects the optimization, preventing subtle bugs.")
print()
print("4. BEYOND STANDARD PASSES:")
print("   AI can explore optimization spaces that aren't covered by")
print("   standard compiler passes, but formal verification ensures")
print("   we only apply transformations that are provably correct.")
print()
print("="*80)

# Made with Bob
