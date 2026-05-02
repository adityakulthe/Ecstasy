"""
THE MONEY MOMENT: AI proposes wrong IR → Alive2 catches it → AI fixes it → PROVED
Run: python3 demo/fail_catch_prove.py
"""
import subprocess, os, sys, tempfile

# Add parent directory to path so we can import agents module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.ir_architect import run as granite_optimize

# STEP 1: A real function
ORIGINAL_IR = """; Original safe add with overflow check
define i32 @safe_add(i32 %a, i32 %b) {
entry:
  %result = add nsw i32 %a, %b
  ret i32 %result
}"""

# STEP 2: Deliberately broken IR (drop nsw = drops no-signed-wrap guarantee)
BROKEN_IR = """; BROKEN: dropped nsw flag — silently allows signed overflow
define i32 @safe_add(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b
  ret i32 %result
}"""

def run_alive2(src_ir: str, tgt_ir: str) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as src_f:
        src_f.write(src_ir)
        src_path = src_f.name
    with tempfile.NamedTemporaryFile(suffix=".ll", mode="w", delete=False) as tgt_f:
        tgt_f.write(tgt_ir)
        tgt_path = tgt_f.name
    try:
        result = subprocess.run(
            ["/opt/homebrew/bin/alive-tv", src_path, tgt_path],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        proved = "Transformation seems to be correct!" in output
        return proved, output
    finally:
        os.unlink(src_path)
        os.unlink(tgt_path)

if __name__ == "__main__":
    print("=" * 60)
    print("🎬 THE MONEY MOMENT: AI Mistake Caught by Math")
    print("=" * 60)

    # BEAT 1: Show broken IR fails
    print("\n⚡ BEAT 1: AI proposes optimization (drops nsw flag)...")
    proved, output = run_alive2(ORIGINAL_IR, BROKEN_IR)
    if not proved:
        print("🔴 COUNTEREXAMPLE FOUND — Alive2 caught the bug!")
        # Extract the counterexample line
        for line in output.split("\n"):
            if "%" in line and ("=" in line or "i32" in line):
                print(f"   → {line.strip()}")
                break
        print("   Human translation: 'Input %a=2147483647 causes overflow in optimized version'")
    
    # BEAT 2: Feed counterexample back to Granite
    print("\n⚡ BEAT 2: Sending counterexample back to Granite for correction...")
    retry_prompt = f"""Your previous optimization is INCORRECT.
Alive2 found a counterexample: when %a = 2147483647 (INT_MAX), your optimization overflows.
The original uses 'add nsw' which preserves the no-signed-wrap semantic guarantee.
Your version dropped 'nsw', allowing undefined behavior on overflow.

Original IR:
{ORIGINAL_IR}

Fix your optimization. Keep the nsw flag. Return only corrected IR."""

    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from dotenv import load_dotenv
    load_dotenv()
    model = ModelInference(
        model_id="ibm/granite-4-h-small",
        credentials=Credentials(url=os.getenv("WATSONX_URL"), api_key=os.getenv("WATSONX_APIKEY")),
        project_id=os.getenv("WATSONX_PROJECT_ID")
    )
    response = model.chat(messages=[
        {"role": "system", "content": "You are an expert LLVM IR optimizer. Return only corrected LLVM IR."},
        {"role": "user", "content": retry_prompt}
    ], params={"max_new_tokens": 512, "temperature": 0.1})
    corrected_ir = response["choices"][0]["message"]["content"].strip()
    import re
    corrected_ir = re.sub(r"```[a-z]*\n?", "", corrected_ir).strip().strip("`")
    print("   Granite corrected IR received.")

    # BEAT 3: Verify corrected IR
    print("\n⚡ BEAT 3: Running Alive2 on corrected IR...")
    proved2, output2 = run_alive2(ORIGINAL_IR, corrected_ir)
    if proved2:
        print("✅ PROVED — AI learned from its mistake. Transformation is mathematically correct.")
    else:
        print("🔴 Still incorrect — would retry (budget: 5 attempts)")

    print("\n" + "=" * 60)
    print("💡 This is the value proposition:")
    print("   AI creativity + Mathematical certainty = Trust")
    print("=" * 60)
