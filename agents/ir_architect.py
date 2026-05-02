import os, re
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

model = ModelInference(
    model_id="ibm/granite-4-h-small",
    credentials=Credentials(url=os.getenv("WATSONX_URL"), api_key=os.getenv("WATSONX_APIKEY")),
    project_id=os.getenv("WATSONX_PROJECT_ID")
)

SYSTEM_PROMPT = """You are an expert LLVM IR optimizer that MUST preserve program semantics.
INPUT: Raw LLVM IR text.
OUTPUT: Only the modified LLVM IR — no explanation, no markdown fences, no commentary.

CRITICAL RULES:
1. NEVER change the computational result or behavior of any function
2. Preserve ALL function signatures and type signatures exactly
3. Only apply SAFE optimizations:
   - Dead code elimination (unreachable code only)
   - Instruction reordering (only when dependencies allow)
   - Register renaming
4. DO NOT simplify or modify arithmetic operations
5. DO NOT remove or change any computations
6. When in doubt, return the IR UNCHANGED
7. Return raw IR text only, no markdown
8. ALWAYS return COMPLETE IR with all closing braces"""

def is_valid_ir(ir_text: str) -> bool:
    """Validate IR is complete and well-formed"""
    if not ir_text or not ir_text.strip():
        return False
    open_braces = ir_text.count('{')
    close_braces = ir_text.count('}')
    return open_braces == close_braces and ir_text.strip().endswith('}')

def run(ir: str) -> str:
    try:
        response = model.chat(messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Optimize this LLVM IR. If you cannot safely optimize it, return it EXACTLY as provided:\n\n{ir}"}
        ], params={"max_new_tokens": 4096, "temperature": 0.1})
        output = response["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if Granite adds them anyway
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
        print(f"  ⚠️  Error in ir_architect: {e}, returning original")
        return ir

if __name__ == "__main__":
    test_ir = """; test
define i32 @add(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b
  ret i32 %result
}"""
    print("=== GRANITE OUTPUT ===")
    result = run(test_ir)
    print(result)
    print("\n✅ ir_architect is live")
