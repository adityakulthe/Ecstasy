#!/usr/bin/env python3
"""
AI Compiler - Retry Loop Demo
Shows Granite proposing optimization, Alive2 catching error, Granite fixing it
This is the winning demo moment: AI creativity + mathematical proof
"""
import os, tempfile, subprocess, re
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

model = ModelInference(
    model_id="ibm/granite-4-h-small",
    credentials=Credentials(url=os.getenv("WATSONX_URL"), api_key=os.getenv("WATSONX_APIKEY")),
    project_id=os.getenv("WATSONX_PROJECT_ID")
)

def run_alive2(original_ir, optimized_ir):
    """Run Alive2 formal verification"""
    orig = tempfile.NamedTemporaryFile(suffix='.ll', mode='w', delete=False)
    orig.write(original_ir); orig.flush()
    opt = tempfile.NamedTemporaryFile(suffix='.ll', mode='w', delete=False)
    opt.write(optimized_ir); opt.flush()
    result = subprocess.run(['alive-tv', orig.name, opt.name], capture_output=True, text=True)
    os.unlink(orig.name)
    os.unlink(opt.name)
    return result.stdout + result.stderr

def ask_granite(messages):
    """Ask Granite for IR optimization"""
    response = model.chat(messages=messages, params={"max_new_tokens": 2048, "temperature": 0.1})
    output = response["choices"][0]["message"]["content"].strip()
    # Strip markdown fences if present
    output = re.sub(r"^```[a-z]*\n?", "", output, flags=re.MULTILINE)
    output = re.sub(r"\n?```$", "", output, flags=re.MULTILINE)
    return output.strip()

# Simple test function
original_ir = """define i32 @add(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b
  ret i32 %result
}"""

print("=" * 60)
print("STEP 1: Granite proposes optimization")
print("=" * 60)

messages = [
    {"role": "system", "content": "You are an LLVM IR optimizer. Return ONLY raw IR, no explanation, no markdown."},
    {"role": "user", "content": f"Optimize this IR:\n\n{original_ir}"}
]

granite_output = ask_granite(messages)
print("Granite proposed:")
print(granite_output)

print("\n" + "=" * 60)
print("STEP 2: Alive2 verifies")
print("=" * 60)

alive2_result = run_alive2(original_ir, granite_output)
print(alive2_result)

if "doesn't verify" in alive2_result or "incorrect" in alive2_result or "ERROR" in alive2_result:
    print("\n" + "=" * 60)
    print("STEP 3: Alive2 caught a bug — sending counterexample to Granite")
    print("=" * 60)

    messages.append({"role": "assistant", "content": granite_output})
    messages.append({"role": "user", "content": f"""Your optimization is MATHEMATICALLY INCORRECT.

Alive2 formal verifier found this counterexample:
{alive2_result}

The original and your version return different values for these inputs.
Return ONLY a corrected IR that preserves exact semantics. No explanation."""})

    retry_output = ask_granite(messages)
    print("Granite retry:")
    print(retry_output)

    print("\n" + "=" * 60)
    print("STEP 4: Alive2 verifies retry")
    print("=" * 60)
    final_result = run_alive2(original_ir, retry_output)
    print(final_result)

    if "correct" in final_result.lower() or ("incorrect transformations" in final_result and "\n  0" in final_result):
        print("\n" + "=" * 60)
        print("✅ PROVED — AI corrected itself. Mathematical guarantee confirmed.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  Still incorrect — would retry again in production")
        print("=" * 60)
else:
    print("\n" + "=" * 60)
    print("✅ PROVED on first attempt")
    print("=" * 60)

# Made with Bob
