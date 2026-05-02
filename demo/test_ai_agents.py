#!/usr/bin/env python3
"""
Quick demo to show AI agents in action
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.supervisor import CompilerSupervisor

# Simple test code
test_code = """
int add(int a, int b) {
    return a + b;
}

int main() {
    return add(5, 10);
}
"""

print("=" * 60)
print("AI Compiler Demo - Granite 4.0 Agents")
print("=" * 60)
print()

supervisor = CompilerSupervisor(max_retries=1)
result = supervisor.supervise_compilation(test_code)

print()
print("=" * 60)
print("RESULTS:")
print(f"✅ Success: {result['success']}")
print(f"✅ Verdict: {result['final_verdict']}")
print(f"✅ Phases: {result['phases_completed']}")
print(f"✅ Binary: {result.get('binary_path', 'N/A')}")
print("=" * 60)

# Made with Bob
