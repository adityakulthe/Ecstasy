#!/usr/bin/env python3
"""
Test the supervisor with real Granite agents integrated
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.supervisor import CompilerSupervisor

# Simple test C code
TEST_C_CODE = """
int add(int a, int b) {
    return a + b;
}
"""

def main():
    print("=" * 60)
    print("Testing Supervisor with Real Granite Agents")
    print("=" * 60)
    
    supervisor = CompilerSupervisor(max_retries=3)
    
    print("\n🚀 Running full pipeline...")
    result = supervisor.supervise_compilation(TEST_C_CODE, "test.c")
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Phases completed: {result['phases_completed']}")
    print(f"Final verdict: {result['final_verdict']}")
    print(f"Total retries: {result['total_retries_used']}")
    print(f"Fallback used: {result['fallback_used']}")
    
    if result['binary_path']:
        print(f"Binary created: {result['binary_path']}")
    
    if result['error']:
        print(f"Error: {result['error']}")
    
    print("\n✅ Integration test complete!")

if __name__ == "__main__":
    main()

# Made with Bob
