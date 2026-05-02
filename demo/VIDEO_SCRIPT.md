# 3-Minute Video Demonstration Script

## Opening (15 seconds)

"Hi, I'm demonstrating an AI-powered compiler that uses IBM Granite 4.0 for optimization and Alive2 for formal verification. Let me show you how it works."

## Demo 1: Basic Pipeline (60 seconds)

**Show:** `demo/demo.py`

```bash
source venv/bin/activate
python3 demo/demo.py
```

**Narrate while running:**
- "Here's unsafe C code with a buffer overflow"
- "Our pipeline compiles it to LLVM IR"
- "Nine AI agents analyze and optimize it"
- "Alive2 formally verifies every transformation"
- "The result: hardened, verified binary"

**Key points to highlight:**
- ✅ Compilation successful
- ✅ Memory safety checks added
- ✅ Alive2 verification: PROVED
- ✅ Final binary created

## Demo 2: AI Finds What Clang Misses (60 seconds)

**Show:** `demo/ipcp_complete_demo.py`

```bash
python3 demo/ipcp_complete_demo.py
```

**Narrate:**
- "Here are two C files compiled separately"
- "Clang -O3 keeps the function call - it can't see across files"
- "Our AI sees both functions together"
- "It recognizes the constant and tries to optimize"
- "But Alive2 catches a subtle bug - the function could have side effects"

**Key message:**
"AI discovers optimizations beyond standard passes, but formal verification ensures we never introduce bugs."

## Demo 3: CEGAR Loop (45 seconds)

**Show:** `demo/granite_cegar_demo.py` (if time permits)

```bash
python3 demo/granite_cegar_demo.py
```

**Narrate:**
- "When Alive2 finds a bug, it provides a counterexample"
- "Granite reads the Z3 values and generates a targeted fix"
- "This is counterexample-guided refinement in action"

## Closing (30 seconds)

**Show:** Architecture diagram or README

**Key points:**
1. **AI-Powered:** IBM Granite 4.0 via watsonx.ai
2. **Formally Verified:** Every transformation proved with Alive2 + Z3
3. **Language-Agnostic:** Works with any LLVM language (Rust, Swift, Julia, Zig)
4. **Production-Ready:** Catches bugs that AI suggests, ensures correctness

"The system combines AI creativity with mathematical proof. AI explores, verification ensures safety."

---

## Backup Answers for Judges

### Q: "What does your AI do that clang -O3 doesn't?"

**A:** "Clang -O3 cannot perform inter-procedural constant propagation across translation units without LTO. Our demo shows a function call that -O3 keeps but our AI recognizes as constant. However, when the AI tried to eliminate it, Alive2 caught a subtle bug. This shows AI can find novel optimizations, but verification is essential."

### Q: "How do you know the AI optimizations are correct?"

**A:** "We don't trust the AI blindly. Every transformation goes through Alive2, which uses Z3 to mathematically prove equivalence. In our IPCP demo, the AI suggested an optimization that looked correct but was actually wrong - Alive2 caught it. The AI discovers, the verifier ensures safety."

### Q: "Why not just use LLVM's existing passes?"

**A:** "LLVM passes are excellent but limited to predefined patterns. AI can recognize novel optimization opportunities, especially in complex inter-procedural scenarios. The key innovation is combining AI exploration with formal verification - we get the best of both worlds."

### Q: "What about performance overhead?"

**A:** "Verification happens at compile-time, not runtime. The final binary has zero overhead. The compilation takes longer, but you get mathematically proven correctness and AI-discovered optimizations."

### Q: "Can this work with languages other than C?"

**A:** "Absolutely. We operate on LLVM IR, so any language that compiles to LLVM works automatically - Rust, Swift, Julia, Zig, etc. The demo uses C for clarity, but the pipeline is language-agnostic."

---

## Technical Details (If Asked)

- **Model:** IBM Granite 4.0 (ibm/granite-4-h-small) via watsonx.ai
- **Verification:** Alive2 + Z3 SMT solver
- **Architecture:** 9 specialized AI agents with shared knowledge base
- **CEGAR:** Counterexample-guided refinement with AI-generated patches
- **Safety:** HMAC-SHA256 integrity proofs for all certificates

---

## Files to Have Open

1. `demo/demo.py` - Main demonstration
2. `demo/ipcp_complete_demo.py` - IPCP example
3. `demo/IPCP_DEMO_SUMMARY.md` - Explanation
4. `README.md` - Architecture overview
5. `tests/fixtures/unsafe.c` - Example input

---

## Timing Breakdown

- **0:00-0:15** - Introduction
- **0:15-1:15** - Basic pipeline demo
- **1:15-2:15** - IPCP optimization demo
- **2:15-3:00** - Closing and key takeaways

**Total: 3 minutes**