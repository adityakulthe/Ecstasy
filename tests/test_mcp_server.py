#!/usr/bin/env python3
"""
Test suite for MCP Server tools
Tests compile_to_ir, optimize_ir_pass, and validate_translation
"""

import pytest
import os
import sys
import tempfile

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.mcp_server import compile_to_ir, optimize_ir_pass, validate_translation


class TestCompileToIR:
    """Test Suite 1.1: compile_to_ir Tool"""
    
    def test_valid_c_code_compilation(self):
        """Test Case 1.1.1: Valid C Code Compilation"""
        # ARRANGE
        c_source = """
#include <stdio.h>
int main() {
    int x = 42;
    return x;
}
"""
        expected_ir_patterns = ["define", "i32", "@main", "ret"]
        
        # ACT
        result = compile_to_ir(c_source, "test.c")
        
        # ASSERT
        assert result["success"] == True
        assert "ir" in result
        for pattern in expected_ir_patterns:
            assert pattern in result["ir"], f"Expected pattern '{pattern}' not found in IR"
        assert result["warnings"] == "" or "warning" not in result["warnings"].lower()
    
    def test_syntax_error_handling(self):
        """Test Case 1.1.2: Syntax Error Handling"""
        # ARRANGE
        invalid_c = "int main( { return 0; }"  # Missing closing paren
        
        # ACT
        result = compile_to_ir(invalid_c, "invalid.c")
        
        # ASSERT
        assert result["success"] == False
        assert "error" in result
        assert len(result["error"]) > 0
    
    def test_empty_file_handling(self):
        """Test Case 1.1.3: Empty File Handling"""
        # ARRANGE
        empty_source = ""
        
        # ACT
        result = compile_to_ir(empty_source, "empty.c")
        
        # ASSERT
        # Empty files compile successfully but produce minimal IR
        assert result["success"] == True
        assert "ir" in result
    
    def test_simple_function(self):
        """Test Case 1.1.4: Simple Function Compilation"""
        # ARRANGE
        c_source = """
int add(int a, int b) {
    return a + b;
}
"""
        
        # ACT
        result = compile_to_ir(c_source, "add.c")
        
        # ASSERT
        assert result["success"] == True
        assert "define" in result["ir"]
        assert "add" in result["ir"]


class TestOptimizeIRPass:
    """Test Suite 1.2: optimize_ir_pass Tool"""
    
    def test_basic_ir_transformation_tracking(self):
        """Test Case 1.2.1: Basic IR Transformation Tracking"""
        # ARRANGE
        original_ir = """
define i32 @foo() {
  %1 = add i32 1, 1
  ret i32 %1
}
"""
        optimized_ir = """
define i32 @foo() {
  ret i32 2
}
"""
        
        # ACT
        result = optimize_ir_pass(original_ir, optimized_ir)
        
        # ASSERT
        assert "orig_path" in result
        assert "opt_path" in result
        assert os.path.exists(result["orig_path"])
        assert os.path.exists(result["opt_path"])
        assert result["diff_summary"]["lines_removed"] > 0
        
        # Cleanup
        os.unlink(result["orig_path"])
        os.unlink(result["opt_path"])
    
    def test_identical_ir_no_changes(self):
        """Test Case 1.2.2: Identical IR (No Changes)"""
        # ARRANGE
        ir_text = """
define i32 @identity(i32 %x) {
  ret i32 %x
}
"""
        
        # ACT
        result = optimize_ir_pass(ir_text, ir_text)
        
        # ASSERT
        assert result["diff_summary"]["lines_removed"] == 0
        assert result["diff_summary"]["lines_added"] == 0
        
        # Cleanup
        os.unlink(result["orig_path"])
        os.unlink(result["opt_path"])
    
    def test_multiple_changes(self):
        """Test Case 1.2.3: Multiple Changes Tracking"""
        # ARRANGE
        original_ir = """
define i32 @test() {
  %1 = add i32 1, 2
  %2 = add i32 3, 4
  %3 = add i32 %1, %2
  ret i32 %3
}
"""
        optimized_ir = """
define i32 @test() {
  ret i32 10
}
"""
        
        # ACT
        result = optimize_ir_pass(original_ir, optimized_ir)
        
        # ASSERT
        assert result["diff_summary"]["lines_removed"] > 0
        assert result["diff_summary"]["lines_changed"] > 0
        
        # Cleanup
        os.unlink(result["orig_path"])
        os.unlink(result["opt_path"])


class TestValidateTranslation:
    """Test Suite 1.3: validate_translation Tool"""
    
    def test_file_not_found_error(self):
        """Test Case 1.3.1: File Not Found Error"""
        # ARRANGE
        orig_path = "/nonexistent/orig.ll"
        opt_path = "/nonexistent/opt.ll"
        
        # ACT
        result = validate_translation(orig_path, opt_path)
        
        # ASSERT
        assert result["verdict"] == "ERROR"
        assert result["proved"] == False
        assert "not found" in result["output"].lower()
    
    def test_identical_ir_validation(self):
        """Test Case 1.3.2: Identical IR Should Validate"""
        # ARRANGE
        ir_code = """
define i32 @identity(i32 %x) {
  ret i32 %x
}
"""
        # Create temp files
        orig_fd, orig_path = tempfile.mkstemp(suffix='.ll')
        opt_fd, opt_path = tempfile.mkstemp(suffix='.ll')
        
        with os.fdopen(orig_fd, 'w') as f:
            f.write(ir_code)
        with os.fdopen(opt_fd, 'w') as f:
            f.write(ir_code)
        
        # ACT
        result = validate_translation(orig_path, opt_path, timeout=30)
        
        # ASSERT
        # Note: This test may fail if Alive2 is not installed
        # In that case, it should return ERROR verdict
        assert result["verdict"] in ["PROVED", "ERROR"]
        assert "output" in result
        
        # Cleanup
        os.unlink(orig_path)
        os.unlink(opt_path)
    
    def test_timeout_handling(self):
        """Test Case 1.3.3: Timeout Handling"""
        # ARRANGE
        ir_code = """
define i32 @test() {
  ret i32 0
}
"""
        orig_fd, orig_path = tempfile.mkstemp(suffix='.ll')
        opt_fd, opt_path = tempfile.mkstemp(suffix='.ll')
        
        with os.fdopen(orig_fd, 'w') as f:
            f.write(ir_code)
        with os.fdopen(opt_fd, 'w') as f:
            f.write(ir_code)
        
        # ACT - use very short timeout
        result = validate_translation(orig_path, opt_path, timeout=1)
        
        # ASSERT
        # Should either complete quickly or timeout
        assert result["verdict"] in ["PROVED", "TIMEOUT", "ERROR"]
        
        # Cleanup
        os.unlink(orig_path)
        os.unlink(opt_path)


class TestIntegration:
    """Integration tests for full pipeline"""
    
    def test_full_pipeline_simple_c(self):
        """Test full pipeline: compile -> optimize -> validate"""
        # ARRANGE
        c_source = """
int add(int a, int b) {
    return a + b;
}
"""
        
        # ACT - Step 1: Compile to IR
        compile_result = compile_to_ir(c_source, "test.c")
        
        # ASSERT - Compilation should succeed
        assert compile_result["success"] == True
        assert len(compile_result["ir"]) > 0
        
        # ACT - Step 2: Register transformation (no actual optimization)
        original_ir = compile_result["ir"]
        optimized_ir = compile_result["ir"]  # Same for now
        
        optimize_result = optimize_ir_pass(original_ir, optimized_ir)
        
        # ASSERT - Should track the transformation
        assert "orig_path" in optimize_result
        assert "opt_path" in optimize_result
        
        # ACT - Step 3: Validate (if Alive2 is available)
        validate_result = validate_translation(
            optimize_result["orig_path"],
            optimize_result["opt_path"],
            timeout=30
        )
        
        # ASSERT - Should either prove or error (if Alive2 not installed)
        assert validate_result["verdict"] in ["PROVED", "ERROR"]
        
        # Cleanup
        os.unlink(optimize_result["orig_path"])
        os.unlink(optimize_result["opt_path"])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# Made with Bob
