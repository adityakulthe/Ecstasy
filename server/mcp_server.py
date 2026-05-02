#!/usr/bin/env python3
"""
AI Compiler - MCP Server
Provides three core tools for LLVM IR compilation, optimization, and validation.
"""

import os
import subprocess
import tempfile
import difflib
import re
from typing import Dict, Any, Optional
from pathlib import Path


def compile_to_ir(c_source: str, filename: str) -> Dict[str, Any]:
    """
    Compile C/C++ source code to LLVM IR using clang.
    
    Args:
        c_source: The C/C++ source code as a string
        filename: The filename (used to determine language: .c or .cpp)
        
    Returns:
        Dictionary with:
        - success: bool
        - ir: str (LLVM IR code if successful)
        - error: str (error message if failed)
        - warnings: str (compiler warnings)
    """
    try:
        # Create temporary file for source code
        with tempfile.NamedTemporaryFile(mode='w', suffix=filename, delete=False) as src_file:
            src_file.write(c_source)
            src_path = src_file.name
        
        # Create temporary file for IR output
        ir_fd, ir_path = tempfile.mkstemp(suffix='.ll')
        os.close(ir_fd)
        
        try:
            # Compile to IR with -O0 (no optimization)
            cmd = [
                'clang',
                '-S',  # Generate assembly (IR in this case)
                '-emit-llvm',  # Emit LLVM IR instead of native assembly
                '-O0',  # No optimization
                '-o', ir_path,
                src_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Read the generated IR
            with open(ir_path, 'r') as f:
                ir_code = f.read()
            
            # Check for errors
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': result.stderr,
                    'warnings': result.stdout
                }
            
            return {
                'success': True,
                'ir': ir_code,
                'warnings': result.stderr,
                'error': ''
            }
            
        finally:
            # Clean up temporary files
            if os.path.exists(src_path):
                os.unlink(src_path)
            if os.path.exists(ir_path):
                os.unlink(ir_path)
                
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Compilation timeout (30 seconds)',
            'warnings': ''
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Compilation error: {str(e)}',
            'warnings': ''
        }


def optimize_ir_pass(original_ir: str, optimized_ir: str) -> Dict[str, Any]:
    """
    Register an IR transformation by saving both versions and computing a diff.
    
    Args:
        original_ir: The original LLVM IR code
        optimized_ir: The optimized LLVM IR code
        
    Returns:
        Dictionary with:
        - orig_path: str (path to original IR file)
        - opt_path: str (path to optimized IR file)
        - diff_summary: dict with lines_added, lines_removed, lines_changed
    """
    try:
        # Create temporary files for both IR versions
        orig_fd, orig_path = tempfile.mkstemp(suffix='_orig.ll', prefix='ir_')
        opt_fd, opt_path = tempfile.mkstemp(suffix='_opt.ll', prefix='ir_')
        
        # Write IR to files
        with os.fdopen(orig_fd, 'w') as f:
            f.write(original_ir)
        with os.fdopen(opt_fd, 'w') as f:
            f.write(optimized_ir)
        
        # Compute diff
        orig_lines = original_ir.splitlines(keepends=True)
        opt_lines = optimized_ir.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(orig_lines, opt_lines, lineterm=''))
        
        # Count changes
        lines_added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        lines_removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        lines_changed = max(lines_added, lines_removed)
        
        return {
            'orig_path': orig_path,
            'opt_path': opt_path,
            'diff_summary': {
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'lines_changed': lines_changed
            }
        }
        
    except Exception as e:
        return {
            'error': f'Failed to register IR transformation: {str(e)}'
        }


def validate_translation(orig_ir_path: str, opt_ir_path: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Validate IR transformation using Alive2 translation validator.
    
    Args:
        orig_ir_path: Path to original IR file
        opt_ir_path: Path to optimized IR file
        timeout: Timeout in seconds (default: 60)
        
    Returns:
        Dictionary with:
        - verdict: str ("PROVED", "FAILED", "TIMEOUT", "ERROR")
        - proved: bool
        - counterexample: Optional[str] (if verification failed)
        - output: str (full Alive2 output)
    """
    try:
        # Check if files exist
        if not os.path.exists(orig_ir_path):
            return {
                'verdict': 'ERROR',
                'proved': False,
                'counterexample': None,
                'output': f'Original IR file not found: {orig_ir_path}'
            }
        
        if not os.path.exists(opt_ir_path):
            return {
                'verdict': 'ERROR',
                'proved': False,
                'counterexample': None,
                'output': f'Optimized IR file not found: {opt_ir_path}'
            }
        
        # Run Alive2
        cmd = ['alive-tv', orig_ir_path, opt_ir_path]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout + result.stderr
            
            # Parse Alive2 output
            if 'Transformation seems to be correct' in output or '1 correct transformation' in output:
                return {
                    'verdict': 'PROVED',
                    'proved': True,
                    'counterexample': None,
                    'output': output
                }
            elif 'ERROR' in output or 'Transformation doesn\'t verify' in output:
                # Extract counterexample if present
                counterexample = None
                if 'Example:' in output:
                    # Extract the counterexample section
                    example_start = output.find('Example:')
                    example_section = output[example_start:example_start+500]
                    counterexample = example_section
                
                return {
                    'verdict': 'FAILED',
                    'proved': False,
                    'counterexample': counterexample,
                    'output': output
                }
            else:
                return {
                    'verdict': 'ERROR',
                    'proved': False,
                    'counterexample': None,
                    'output': output
                }
                
        except subprocess.TimeoutExpired:
            return {
                'verdict': 'TIMEOUT',
                'proved': False,
                'counterexample': None,
                'output': f'Alive2 verification timeout after {timeout} seconds'
            }
            
    except FileNotFoundError:
        return {
            'verdict': 'ERROR',
            'proved': False,
            'counterexample': None,
            'output': 'alive-tv command not found. Please install Alive2.'
        }
    except Exception as e:
        return {
            'verdict': 'ERROR',
            'proved': False,
            'counterexample': None,
            'output': f'Validation error: {str(e)}'
        }


# MCP Server setup (if using FastMCP)
if __name__ == '__main__':
    print("AI Compiler MCP Server")
    print("=" * 50)
    print("\nAvailable tools:")
    print("1. compile_to_ir - Compile C/C++ to LLVM IR")
    print("2. optimize_ir_pass - Register IR transformation")
    print("3. validate_translation - Validate with Alive2")
    print("\nServer ready for tool calls.")

# Made with Bob
