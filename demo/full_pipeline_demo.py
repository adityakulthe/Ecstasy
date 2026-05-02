#!/usr/bin/env python3
"""
Comprehensive Demo: All 9 AI Agents in Action
Shows the complete AI Compiler pipeline with IBM Granite 4.0
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.supervisor import CompilerSupervisor

# Test with a more complex program
complex_code = """
#include <stdio.h>

// Bubble sort - O(n²) algorithm that could be optimized
void bubble_sort(int arr[], int n) {
    for (int i = 0; i < n-1; i++) {
        for (int j = 0; j < n-i-1; j++) {
            if (arr[j] > arr[j+1]) {
                int temp = arr[j];
                arr[j] = arr[j+1];
                arr[j+1] = temp;
            }
        }
    }
}

// Array access - potential memory safety issues
int get_element(int arr[], int index) {
    return arr[index];  // No bounds checking!
}

int main() {
    int numbers[5] = {64, 34, 25, 12, 22};
    bubble_sort(numbers, 5);
    return get_element(numbers, 2);
}
"""

print("=" * 70)
print("🚀 AI COMPILER - FULL 9-AGENT PIPELINE DEMONSTRATION")
print("=" * 70)
print()
print("📋 Test Program Features:")
print("  • Bubble sort (O(n²)) - candidate for algorithmic synthesis")
print("  • Unchecked array access - needs memory safety hardening")
print("  • Multiple functions - benefits from global context analysis")
print("  • Loops and branches - targets for hardware optimization")
print()
print("=" * 70)
print()

supervisor = CompilerSupervisor(max_retries=1)
result = supervisor.supervise_compilation(complex_code, filename="test.c")

print()
print("=" * 70)
print("📊 FINAL RESULTS")
print("=" * 70)
print(f"✅ Success: {result['success']}")
print(f"✅ Verdict: {result['final_verdict']}")
print(f"✅ Binary: {result.get('binary_path', 'N/A')}")
print(f"✅ Certificate: {result.get('certificate_id', 'N/A')}")
print()
print(f"🤖 Active Agents: {len(result['phases_completed'])}/9")
print("   Phases completed:")
for i, phase in enumerate(result['phases_completed'], 1):
    print(f"   {i}. {phase}")
print()
print(f"🔄 Total Retries: {result['total_retries_used']}")
print(f"⚠️  Fallback Used: {result['fallback_used']}")
print("=" * 70)

# Made with Bob
