import os
import re
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

from agents.agent_rules import (
    MEMORY_SENTINEL_SYSTEM_RULES,
    compact_ir_for_llm,
    clean_llm_ir_response,
    validate_llm_ir_output,
)

_get_watsonx_model = get_model
model = _LazyModelProxy()

SYSTEM_PROMPT = MEMORY_SENTINEL_SYSTEM_RULES

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

def _has_memory_or_unsafe_ops(ir: str) -> bool:
    """Fast-path check: skip LLM call if IR has no pointer indexing, memory loads/stores, or unsafe calls."""
    markers = ("getelementptr", "load ", "store ", "@strcpy", "@strcat", "@gets", "@sprintf", "@scanf", "@free")
    return any(m in ir for m in markers)

def run(ir: str) -> str:
    # Rule: Zero-token fast path for pure register/arithmetic functions
    if not _has_memory_or_unsafe_ops(ir):
        return ir

    if get_model() is not None:
        try:
            compacted_ir = compact_ir_for_llm(ir)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Harden this LLVM IR for memory safety. If there are no memory operations to harden, return it EXACTLY as provided:\n\n{compacted_ir}"}
            ]
            response = model.chat(
                messages=messages,
                params={"max_new_tokens": 8192, "temperature": 0.1}
            )
            raw_output = response["choices"][0]["message"]["content"]
            result = clean_llm_ir_response(raw_output)
            
            valid_struct, reason = validate_llm_ir_output(ir, result)
            if not valid_struct or "define" not in result or not is_valid_ir(result):
                print(f"  ⚠️  LLM IR rejected by pre-gate ({reason}), returning original")
                return ir
                
            return result
        except Exception as e:
            print(f"  ⚠️  Error in memory_sentinel AI: {e}, using original IR")
            return ir
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
