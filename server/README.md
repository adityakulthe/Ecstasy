# MCP Server - AI Compiler Tools

This MCP (Model Context Protocol) server provides three core tools for the AI Compiler project:

1. **compile_to_ir** - Compile C/C++ source code to LLVM IR
2. **optimize_ir_pass** - Register and track IR transformations
3. **validate_translation** - Validate transformations using Alive2

## Installation

### Prerequisites

- Python 3.10+
- Clang/LLVM 14+
- Alive2 (optional, for validation)

### Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify clang is installed
clang --version

# Verify Alive2 is installed (optional)
alive-tv --version
```

## Tool Documentation

### 1. compile_to_ir

Compiles C/C++ source code to LLVM IR using clang with no optimizations (-O0).

**Input:**
```python
{
    "c_source": str,    # C/C++ source code
    "filename": str     # Filename (e.g., "test.c" or "test.cpp")
}
```

**Output:**
```python
{
    "success": bool,
    "ir": str,          # LLVM IR code (if successful)
    "error": str,       # Error message (if failed)
    "warnings": str     # Compiler warnings
}
```

**Example:**
```python
from server.mcp_server import compile_to_ir

result = compile_to_ir("""
int add(int a, int b) {
    return a + b;
}
""", "add.c")

if result["success"]:
    print(result["ir"])
else:
    print(f"Error: {result['error']}")
```

### 2. optimize_ir_pass

Registers an IR transformation by saving both original and optimized versions, and computing a diff summary.

**Input:**
```python
{
    "original_ir": str,    # Original LLVM IR
    "optimized_ir": str    # Optimized LLVM IR
}
```

**Output:**
```python
{
    "orig_path": str,      # Path to original IR file
    "opt_path": str,       # Path to optimized IR file
    "diff_summary": {
        "lines_added": int,
        "lines_removed": int,
        "lines_changed": int
    }
}
```

**Example:**
```python
from server.mcp_server import optimize_ir_pass

original = """
define i32 @foo() {
  %1 = add i32 1, 1
  ret i32 %1
}
"""

optimized = """
define i32 @foo() {
  ret i32 2
}
"""

result = optimize_ir_pass(original, optimized)
print(f"Original IR saved to: {result['orig_path']}")
print(f"Optimized IR saved to: {result['opt_path']}")
print(f"Changes: {result['diff_summary']}")
```

### 3. validate_translation

Validates an IR transformation using Alive2 translation validator with Z3 SMT solver.

**Input:**
```python
{
    "orig_ir_path": str,   # Path to original IR file
    "opt_ir_path": str,    # Path to optimized IR file
    "timeout": int         # Timeout in seconds (default: 60)
}
```

**Output:**
```python
{
    "verdict": str,              # "PROVED", "FAILED", "TIMEOUT", or "ERROR"
    "proved": bool,              # True if transformation is correct
    "counterexample": str|None,  # Counterexample if verification failed
    "output": str                # Full Alive2 output
}
```

**Example:**
```python
from server.mcp_server import validate_translation

result = validate_translation(
    "/tmp/orig.ll",
    "/tmp/opt.ll",
    timeout=30
)

if result["verdict"] == "PROVED":
    print("✅ Transformation is correct!")
elif result["verdict"] == "FAILED":
    print(f"❌ Transformation is incorrect!")
    print(f"Counterexample: {result['counterexample']}")
else:
    print(f"⚠️ {result['verdict']}: {result['output']}")
```

## Full Pipeline Example

```python
from server.mcp_server import compile_to_ir, optimize_ir_pass, validate_translation

# Step 1: Compile C code to IR
c_source = """
int multiply(int x) {
    return x * 2;
}
"""

compile_result = compile_to_ir(c_source, "test.c")
if not compile_result["success"]:
    print(f"Compilation failed: {compile_result['error']}")
    exit(1)

original_ir = compile_result["ir"]

# Step 2: Apply optimization (example: strength reduction)
optimized_ir = original_ir.replace("mul i32 %x, 2", "shl i32 %x, 1")

# Step 3: Register the transformation
transform_result = optimize_ir_pass(original_ir, optimized_ir)

# Step 4: Validate with Alive2
validation_result = validate_translation(
    transform_result["orig_path"],
    transform_result["opt_path"]
)

print(f"Verdict: {validation_result['verdict']}")
print(f"Proved: {validation_result['proved']}")
```

## Testing

Run the test suite:

```bash
# Run all MCP server tests
pytest tests/test_mcp_server.py -v

# Run with coverage
pytest tests/test_mcp_server.py --cov=server --cov-report=html

# Run specific test
pytest tests/test_mcp_server.py::TestCompileToIR::test_valid_c_code_compilation -v
```

## Error Handling

All tools return structured error information:

- **Compilation errors**: Syntax errors, type errors, etc.
- **File errors**: Missing files, permission issues
- **Timeout errors**: Long-running validations
- **Tool errors**: Missing dependencies (clang, alive-tv)

## Notes

- Temporary files are created in the system temp directory
- IR files from `optimize_ir_pass` should be cleaned up after validation
- Alive2 validation can be slow for complex transformations
- If Alive2 is not installed, validation will return ERROR verdict

## Integration with IBM Bob

These tools are designed to be called by IBM Bob Custom Modes:

- **@ir-architect**: Uses all three tools to propose and validate optimizations
- **@memory-sentinel**: Uses compile_to_ir and validate_translation for safety checks

See `agents/bob_modes.md` for Bob integration details.