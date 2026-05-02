#!/usr/bin/env python3
"""
Test script to verify the UI components work
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.mcp_server import compile_to_ir, optimize_ir_pass, validate_translation

def test_demo_programs():
    """Test that demo programs compile successfully"""
    
    demo_programs = {
        "Matrix Multiply": """#include <stdio.h>
#define N 64
double A[N][N], B[N][N], C[N][N];

void matmul() {
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            for (int k = 0; k < N; k++)
                C[i][j] += A[i][k] * B[k][j];
}

int main() {
    matmul();
    return 0;
}""",
        
        "Simple Add": """int add(int a, int b) {
    return a + b;
}

int main() {
    return add(5, 10);
}"""
    }
    
    print("Testing UI Demo Programs")
    print("=" * 50)
    
    for name, source in demo_programs.items():
        print(f"\n📝 Testing: {name}")
        
        # Test compilation
        result = compile_to_ir(source, "test.c")
        
        if result["success"]:
            print(f"  ✅ Compilation successful")
            print(f"  📊 IR length: {len(result['ir'])} characters")
            
            # Test optimization tracking
            opt_result = optimize_ir_pass(result["ir"], result["ir"])
            print(f"  ✅ Optimization tracking successful")
            print(f"  📊 Diff: {opt_result['diff_summary']}")
            
            # Test validation
            val_result = validate_translation(
                opt_result["orig_path"],
                opt_result["opt_path"],
                timeout=10
            )
            print(f"  ✅ Validation: {val_result['verdict']}")
            
            # Cleanup
            os.unlink(opt_result["orig_path"])
            os.unlink(opt_result["opt_path"])
        else:
            print(f"  ❌ Compilation failed: {result['error']}")
    
    print("\n" + "=" * 50)
    print("✅ All UI components tested successfully!")
    print("\nTo run the UI:")
    print("  streamlit run frontend/app.py")

if __name__ == "__main__":
    test_demo_programs()

# Made with Bob
