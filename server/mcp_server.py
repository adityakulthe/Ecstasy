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


def optimize_ir_pass(original_ir: str, use_ai: bool = True) -> Dict[str, Any]:
    """
    Optimize LLVM IR using AI (Granite 4.0) or deterministic fallback.
    
    Args:
        original_ir: The original LLVM IR code
        use_ai: Whether to use AI optimization (default: True)
        
    Returns:
        Dictionary with:
        - orig_path: str (path to original IR file)
        - opt_path: str (path to optimized IR file)
        - optimized_ir: str (optimized IR code)
        - diff_summary: dict with lines_added, lines_removed, lines_changed
        - transformation_applied: bool
        - transformation_type: str
    """
    try:
        optimized_ir = original_ir
        transformation_applied = False
        transformation_type = "none"
        
        # Try to use AI optimization if enabled
        if use_ai:
            try:
                # Import here to avoid circular dependency
                import sys
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                from agents.granite_direct import GraniteDirectAgent
                
                print("🤖 Calling Granite 4.0 for IR optimization...")
                agent = GraniteDirectAgent()
                result = agent.ir_architect(original_ir)
                
                if result.get('transformation_applied', False):
                    optimized_ir = result.get('optimized_ir', original_ir)
                    transformation_applied = True
                    transformation_type = result.get('transformation_type', 'ai-optimization')
                    print(f"✅ AI optimization applied: {transformation_type}")
                    return _finalize_optimization(original_ir, optimized_ir, transformation_applied, transformation_type)
                    
            except Exception as e:
                print(f"⚠️  AI optimization failed: {e}")
                print("   Falling back to deterministic optimization")
        
        # Deterministic fallback: Apply real LLVM optimizations
        print("🔧 Applying deterministic LLVM optimizations...")
        optimized_ir, transformation_applied, transformation_type = _apply_llvm_opt(original_ir)
        
        if transformation_applied:
            print(f"✅ Deterministic optimization applied: {transformation_type}")
        else:
            print("ℹ️  No optimizations applicable")
        
        return _finalize_optimization(original_ir, optimized_ir, transformation_applied, transformation_type)
        
    except Exception as e:
        return {
            'error': f'Failed to optimize IR: {str(e)}'
        }


def _apply_llvm_opt(original_ir: str) -> tuple[str, bool, str]:
    """
    Apply deterministic LLVM optimizations using opt tool.
    
    Returns:
        Tuple of (optimized_ir, transformation_applied, transformation_type)
    """
    try:
        # Write IR to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ll', delete=False) as f:
            f.write(original_ir)
            input_path = f.name
        
        output_path = input_path.replace('.ll', '_opt.ll')
        
        # Run LLVM opt with -O2 optimizations
        cmd = [
            'opt',
            '-O2',  # Standard optimization level
            '-S',   # Output LLVM assembly
            input_path,
            '-o', output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            with open(output_path, 'r') as f:
                optimized_ir = f.read()
            
            # Check if IR actually changed
            if optimized_ir != original_ir:
                transformation_type = "llvm-O2-optimization"
                transformation_applied = True
            else:
                transformation_type = "none"
                transformation_applied = False
                optimized_ir = original_ir
        else:
            print(f"   ⚠️  opt failed: {result.stderr}")
            optimized_ir = original_ir
            transformation_applied = False
            transformation_type = "none"
        
        # Cleanup
        try:
            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
        except:
            pass
        
        return optimized_ir, transformation_applied, transformation_type
        
    except subprocess.TimeoutExpired:
        print("   ⚠️  opt timeout")
        return original_ir, False, "none"
    except FileNotFoundError:
        print("   ⚠️  opt not found - install LLVM tools")
        return original_ir, False, "none"
    except Exception as e:
        print(f"   ⚠️  opt error: {e}")
        return original_ir, False, "none"


def _finalize_optimization(original_ir: str, optimized_ir: str, transformation_applied: bool, transformation_type: str) -> Dict[str, Any]:
    """
    Finalize optimization by creating temp files and computing diff.
    """
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
        'optimized_ir': optimized_ir,
        'diff_summary': {
            'lines_added': lines_added,
            'lines_removed': lines_removed,
            'lines_changed': lines_changed
        },
        'transformation_applied': transformation_applied,
        'transformation_type': transformation_type
    }


def apply_memory_safety(ir_code: str, use_ai: bool = True) -> Dict[str, Any]:
    """
    Apply memory safety hardening using AI (@memory-sentinel).
    
    Args:
        ir_code: LLVM IR code to harden
        use_ai: Whether to use AI hardening (default: True)
        
    Returns:
        Dictionary with:
        - hardened_ir: str (hardened IR code)
        - checks_added: int
        - check_locations: list
        - safety_applied: bool
    """
    try:
        hardened_ir = ir_code
        checks_added = 0
        check_locations = []
        safety_applied = False
        
        # Try to use AI hardening if enabled
        if use_ai:
            try:
                import sys
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                from agents.granite_direct import GraniteDirectAgent
                
                print("🛡️  Calling @memory-sentinel for safety hardening...")
                agent = GraniteDirectAgent()
                result = agent.memory_sentinel(ir_code)
                
                if result.get('checks_added', 0) > 0:
                    hardened_ir = result.get('hardened_ir', ir_code)
                    checks_added = result.get('checks_added', 0)
                    check_locations = result.get('check_locations', [])
                    safety_applied = True
                    print(f"✅ Memory safety checks added: {checks_added}")
                else:
                    print("ℹ️  No safety checks needed")
                    
            except Exception as e:
                print(f"⚠️  Memory safety hardening failed: {e}")
                print("   Using original IR")
        
        return {
            'hardened_ir': hardened_ir,
            'checks_added': checks_added,
            'check_locations': check_locations,
            'safety_applied': safety_applied
        }
        
    except Exception as e:
        return {
            'hardened_ir': ir_code,
            'checks_added': 0,
            'check_locations': [],
            'safety_applied': False,
            'error': f'Failed to apply memory safety: {str(e)}'
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
