import os
import re
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

model = ModelInference(
    model_id="ibm/granite-4-h-small",
    credentials=Credentials(
        url=os.getenv("WATSONX_URL"),
        api_key=os.getenv("WATSONX_APIKEY")
    ),
    project_id=os.getenv("WATSONX_PROJECT_ID")
)

SYSTEM_PROMPT = """You are an expert in memory safety and LLVM IR hardening.
INPUT: Raw LLVM IR text.
OUTPUT: Only the hardened LLVM IR — no explanation, no markdown, no commentary.

CRITICAL RULES:
1. PRESERVE the original computation and return values exactly
2. Only ADD safety checks, never modify existing logic
3. For simple functions without memory operations, return them UNCHANGED
4. Add bounds checks only for actual array/pointer operations
5. Insert calls to @__bounds_fail() only when truly needed
6. NEVER change arithmetic operations or return statements
7. When in doubt, return the IR UNCHANGED
8. Return raw IR text only, no markdown
9. ALWAYS return COMPLETE IR with all closing braces"""

def is_valid_ir(ir_text: str) -> bool:
    """Validate IR is complete and well-formed"""
    if not ir_text or not ir_text.strip():
        return False
    open_braces = ir_text.count('{')
    close_braces = ir_text.count('}')
    return open_braces == close_braces and ir_text.strip().endswith('}')

def run(ir: str) -> str:
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Harden this LLVM IR for memory safety. If there are no memory operations to harden, return it EXACTLY as provided:\n\n{ir}"}
        ]
        response = model.chat(
            messages=messages,
            params={"max_new_tokens": 4096, "temperature": 0.1}
        )
        output = response["choices"][0]["message"]["content"].strip()
        output = re.sub(r"^```[a-z]*\n?", "", output, flags=re.MULTILINE)
        output = re.sub(r"\n?```$", "", output, flags=re.MULTILINE)
        result = output.strip()
        
        # Validate that the output is valid and complete LLVM IR
        if not result or "define" not in result:
            print("  ⚠️  Invalid IR output, returning original")
            return ir
        
        if not is_valid_ir(result):
            print("  ⚠️  Granite output truncated — using original IR")
            return ir
            
        return result
    except Exception as e:
        print(f"  ⚠️  Error in memory_sentinel: {e}, returning original")
        return ir

if __name__ == "__main__":
    test_ir = """define i32 @access(i32* %arr, i32 %idx) {
entry:
  %ptr = getelementptr i32, i32* %arr, i32 %idx
  %val = load i32, i32* %ptr
  ret i32 %val
}"""
    print("=== INPUT IR ===")
    print(test_ir)
    print("\n=== HARDENED OUTPUT IR ===")
    print(run(test_ir))

# Made with Bob
