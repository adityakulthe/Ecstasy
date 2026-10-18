import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

_cached_model = None

def get_model() -> Optional[Any]:
    """Lazily initialize IBM watsonx.ai model inference client if credentials exist."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    url = os.getenv("WATSONX_URL")
    api_key = os.getenv("WATSONX_APIKEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    if not url or not api_key:
        return None
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        _cached_model = ModelInference(
            model_id=os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct"),
            credentials=Credentials(url=url, api_key=api_key),
            project_id=project_id
        )
        return _cached_model
    except Exception as e:
        print(f"  ⚠️  watsonx client initialization skipped: {e}")
        return None

class _LazyModelProxy:
    """Proxy object that delegates to the lazy model instance."""
    def chat(self, *args, **kwargs):
        m = get_model()
        if m is None:
            raise RuntimeError("WATSONX credentials not configured or client initialization failed")
        return m.chat(*args, **kwargs)

model = _LazyModelProxy()

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
    non_comment_lines = [l.split(";")[0].strip() for l in ir_text.splitlines() if l.split(";")[0].strip()]
    if not non_comment_lines:
        return False
    cleaned = "\n".join(non_comment_lines)
    open_braces = cleaned.count('{')
    close_braces = cleaned.count('}')
    return open_braces > 0 and open_braces == close_braces

def optimize_ir_deterministic(ir: str) -> str:
    """Deterministic LLVM optimization pass when offline or as fallback."""
    clang_bin = shutil.which("clang")
    if clang_bin:
        in_path = None
        out_path = None
        try:
            clean_ir = re.sub(r'\boptnone\b\s*', '', ir)
            with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as in_f:
                in_f.write(clean_ir)
                in_path = in_f.name
            out_path = in_path.replace(".ll", "_opt.ll")
            cmd = [clang_bin, "-S", "-emit-llvm", "-O2", "-x", "ir", in_path, "-o", out_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and os.path.exists(out_path):
                with open(out_path, "r") as f:
                    opt_ir = f.read()
                if is_valid_ir(opt_ir):
                    return opt_ir
        except Exception:
            pass
        finally:
            for p in (in_path, out_path):
                if p and os.path.exists(p):
                    try:
                        os.unlink(p)
                    except Exception:
                        pass
    return ir

def run(ir: str) -> str:
    if get_model() is not None:
        try:
            response = model.chat(messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Optimize this LLVM IR. If you cannot safely optimize it, return it EXACTLY as provided:\n\n{ir}"}
            ], params={"max_new_tokens": 8192, "temperature": 0.1})
            output = response["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if Granite adds them anyway
            output = re.sub(r"^```[a-z]*\n?", "", output, flags=re.MULTILINE)
            output = re.sub(r"\n?```$", "", output, flags=re.MULTILINE)
            result = output.strip()
            
            # Validate that the output is valid and complete LLVM IR
            if not result or "define" not in result:
                print("  ⚠️  Invalid IR output, using deterministic fallback")
                return optimize_ir_deterministic(ir)
            
            if not is_valid_ir(result):
                print("  ⚠️  Granite output truncated — using deterministic fallback")
                return optimize_ir_deterministic(ir)
            
            return result
        except Exception as e:
            print(f"  ⚠️  Error in ir_architect AI: {e}, using deterministic fallback")
    
    return optimize_ir_deterministic(ir)

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
