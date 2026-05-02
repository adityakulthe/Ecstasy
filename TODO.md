# Ecstasy Compiler TODO List
## Critical Path to Winning Submission

---

## TIER 1 — WITHOUT THESE YOU CANNOT WIN

### TASK 1: Replace all 9 mock agents with real Bob/watsonx API calls
**Priority: CRITICAL**

This is the single most critical gap between current state and a winning submission. The README says "9/9 production agents ✅" but notes admit they use test doubles. If a judge asks to run the pipeline live and Bob never actually gets called, we lose immediately.

#### Subtasks:
- [ ] **Agent 2 (@ir-architect) - START HERE**
  - Get one real Bob Custom Mode call working end-to-end before touching any other agent
  - Prompt to Bob should be tight: feed raw LLVM IR, return only modified IR, no explanation, no markdown
  - Test in isolation before integration
  
- [ ] **Agent 3 (@memory-sentinel)**
  - Replicate Agent 2 pattern after Agent 2 is stable
  - Same tight prompt structure
  
- [ ] **Granite 4.0 Supervisor**
  - Test IAM token generation first in isolation before wiring into pipeline
  - Most common failure point is authentication, not logic
  - Have fallback where supervisor degrades gracefully if API is slow
  - Do not let API timeout crash entire demo
  
- [ ] **Agents 4-9 (Treefinement, CEGAR, Algorithmic Synthesizer, Global Context, Micro-Arch Tuner, Safety Vault)**
  - Wire them if time permits
  - DO NOT sacrifice demo stability of Agents 1-3 to add agents 4-9 that might break things
  - A clean 3-agent real pipeline beats a crashing 9-agent mock pipeline every time
  
- [ ] **Remove misleading labels**
  - Remove "✅ Production" labels from README for any agent still using test doubles
  - Replace with "✅ Architected, integration in progress"
  - Judges will check GitHub - misrepresented status is worse than having 3 real agents instead of 9

---

### TASK 2: Build the "AI proposes → Alive2 catches mistake → AI retries → PROVED" demo sequence
**Priority: CRITICAL**

This is the most impressive thing we can show. It is the entire justification for the project's existence. Right now we only show the success path — input goes in, PROVED comes out. That is boring. The real story is the system catching an AI mistake with math.

#### Subtasks:
- [ ] **Construct deliberately incorrect IR transformation**
  - Take valid optimized IR and manually introduce subtle semantic error
  - Examples: change `add nsw` to `add` (dropping no-signed-wrap flag), or change bounds check from `icmp slt` to `icmp ult` (signed to unsigned)
  
- [ ] **Feed to Alive2 and capture counterexample**
  - Will produce counterexample with specific input values that expose the bug
  
- [ ] **Script the retry sequence**
  - Take counterexample, pass back to Bob with message: "Your optimization is incorrect. Here is the input that proves it. The original returns X, your version returns Y. Revise your transformation."
  - Let Bob produce corrected version
  - Run Alive2 again
  - Get PROVED
  
- [ ] **Format Alive2 counterexample output for readability**
  - Raw output like `i32 %a = 2147483647` means nothing to non-compiler judge
  - Add one-line annotation: "This specific input value causes the optimized version to overflow. The original does not."
  
- [ ] **Rehearse until it runs in under 90 seconds and never fails**
  - Hard-code the specific C function and specific incorrect transformation
  - Hit this sequence every single time
  - This three-beat sequence — WRONG, counterexample, PROVED — is the money moment

---

### TASK 3: Find and verify one non-trivial optimization that -O3 genuinely misses
**Priority: CRITICAL**

This is the credibility anchor. The mul→shl example is a known LLVM peephole. If we show it, any judge who knows compilers will dismiss the entire project in ten seconds.

#### Subtasks:
- [ ] **Find candidate optimization**
  - Best candidates: inter-procedural optimizations requiring understanding two functions together
  - Example: getter function always returns value within known range, caller redundantly bounds-checks that value
  - -O3 cannot eliminate redundant check because it doesn't know getter's invariant
  - Context-aware LLM can see both and propose elimination
  
- [ ] **Use Godbolt.org to verify**
  - Paste candidate function
  - Switch between -O1, -O2, -O3, and -Os
  - Look for IR instructions that survive all optimization levels
  - That is the target
  
- [ ] **Verify with Alive2 before demo**
  - Run original IR and LLM-proposed IR through alive-tv
  - Confirm PROVED
  - Confirm LLM output is materially different from what -O3 produces
  
- [ ] **DELETE mul→shl example entirely from codebase**
  - Not just from demo - delete it completely
  - Under pressure we will reach for the thing that works
  - If it's still there we will use it

---

### TASK 4: Update README to remove "✅ Production" labels for agents still using test doubles
**Priority: HIGH**

- [ ] Change misleading badges
- [ ] Replace with honest status: "✅ Architected, integration in progress"
- [ ] Judges who check GitHub will read README
- [ ] Getting caught misrepresenting status is worse than having 3 real agents instead of 9

---

## TIER 2 — THESE SEPARATE YOU FROM OTHER TEAMS

### TASK 5: Reframe every piece of communication from "compiler replacement" to "overnight hardening tool"
**Priority: HIGH**

#### Subtasks:
- [ ] **Update README, slides, and demo script**
  - New single sentence: "You run this once overnight on your legacy C codebase when you cut a release. You get back a verified, memory-hardened binary without touching a single line of source code."
  
- [ ] **Fix ACCLAIM paper citation**
  - Current: "1.25x faster than clang -O3 (ACCLAIM research, April 2026)" - implies it's our result
  - Correct: "Recent research (ACCLAIM, April 2026) demonstrates that LLM-guided IR optimization can achieve 1.25x average speedup over -O3. Our system targets the same approach with formal verification as the correctness guarantee."
  
- [ ] **Open pitch with CISA 2026 in first 30 seconds**
  - "Regulators now require enterprises to remediate memory safety vulnerabilities. Rewriting legacy C in Rust costs $2.4 trillion. We do it at the compiler level instead, and we prove it with math."
  - Non-compiler judges understand this immediately

---

### TASK 6: Test the full pipeline on one real open source C file
**Priority: HIGH**

#### Subtasks:
- [ ] **Pick single self-contained C file under 300 lines**
  - Good options: `sds.c` from Redis (simple dynamic strings), base64 implementation from libb64, or `adler32.c` from zlib
  - Must compile cleanly with `clang -O0 -S -emit-llvm`
  
- [ ] **Run full pipeline and document what happens**
  - Does it produce IR?
  - Does Bob propose a transformation?
  - Does Alive2 verify it?
  
- [ ] **Document exact failure modes if it fails**
  - Prepared answer: "Our current implementation works on function-level IR up to approximately N instructions. Full translation unit support is the next engineering milestone."
  
- [ ] **Add to demo as "real world test" slide if it works**
  - One working real-world example is worth more than four working toy examples

---

### TASK 7: Build a live pipeline dashboard for the demo
**Priority: MEDIUM**

#### Subtasks:
- [ ] **Add page/section to Streamlit UI showing pipeline running in real time**
  - Input IR on left
  - Pipeline stage in middle (compiling → Bob analyzing → proposing transformation → Alive2 verifying)
  - Result on right
  
- [ ] **Make Alive2 result visually prominent**
  - PROVED should appear in large green text
  - COUNTEREXAMPLE should appear in large red text
  - Readable from back of conference room
  
- [ ] **Add progress indicator showing which of 9 agents has run**
  - Even if some agents still being wired up
  - Shows pipeline stages running in sequence
  - Gives judges visual understanding of architecture

---

### TASK 8: Update all README badges to reflect actual status
**Priority: MEDIUM**

#### Current badges:
- agents: 9/9 production ❌ MISLEADING
- tests: 44/44 passing ✅
- coverage: 100% ✅

#### Changes needed:
- [ ] Change to: `pipeline: verified end-to-end` and `agents: 9 implemented` (without "production")
- [ ] Keep test count and coverage if they are real
- [ ] Judges and evaluators will check GitHub
- [ ] Misrepresented badges get noticed and remembered negatively

---

## TIER 3 — PRODUCTION POLISH

### TASK 9: Prepare and rehearse answers to the five hardest judge questions
**Priority: MEDIUM**

Write these down. Say them out loud. Make sure every team member can answer all five.

- [ ] **Question 1: "This is too slow for production use."**
  - Answer: "Correct. This is not a build-time tool. It is a one-time hardening pass you run once when you cut a release, not on every commit. The LLM call is minutes for a function, not hours for a codebase."

- [ ] **Question 2: "LLVM's existing passes already do this."**
  - Answer: "LLVM passes are deterministic heuristics with no semantic understanding of intent. They cannot reason across function boundaries or understand algorithmic invariants. Show me the LLVM pass that reads a getter function, understands its return range invariant, and eliminates a redundant bounds check in its caller. It does not exist."

- [ ] **Question 3: "Anthropic built a compiler with Claude. How are you different?"**
  - Answer: "Anthropic built a new compiler from scratch. Chris Lattner called it a competent textbook implementation with a toy code generator. We do not replace LLVM. We sit inside LLVM's proven infrastructure, propose targeted verified transformations, and prove them mathematically. That is a fundamentally different and more practical approach."

- [ ] **Question 4: "How do you handle the case where the LLM proposes something Alive2 cannot verify in reasonable time?"**
  - Answer: "We set a verification timeout per transformation. If Alive2 cannot resolve a proof within the timeout, we treat it as unverified and discard it. Safety is the invariant. No unverified transformation reaches the output binary."

- [ ] **Question 5: "What happens with undefined behavior in C?"**
  - Answer: "Undefined behavior in C means the source code has already violated the language contract. Our tool operates at the IR level where clang has already made UB-handling decisions in its IR generation. We only transform IR that is well-formed. UB in source is a separate problem that tools like UBSan address."

---

### TASK 10: Run real performance benchmarks on your actual implementation
**Priority: MEDIUM**

- [ ] **Run benchmarks on demo programs**
  - Time original binary versus optimized binary on your machine
  - Use whatever numbers you actually measure, even if smaller than 1.25x
  
- [ ] **Update README with real measured numbers**
  - Real measured numbers you can defend are worth 10x a cited number from different paper
  - If matrix multiply runs 1.08x faster, say "1.08x faster on our benchmark"
  - Do not present research paper results as your own results

---

### TASK 11: Clean up the Safety Vault agent's Zero-Knowledge Proof claims
**Priority: MEDIUM**

Current claim: Agent 9 generates "Zero-Knowledge Proof generation" and "cryptographic proof certificates."

#### Issue:
- A ZKP in formal cryptographic sense is specific mathematical construction
- What we're likely generating is signed hash of Alive2 proof output — cryptographic certificate, not ZKP

#### Options:
- [ ] **Option A: Implement real ZKP** (using library like bellman or gnark) - impressive but risky on time
- [ ] **Option B: Relabel accurately** as "cryptographic proof certificates with HMAC integrity verification" - honest and still compelling

**Warning:** If judge with cryptography background asks to explain ZKP construction and we cannot, it damages everything else we've built.

---

### TASK 12: Write one real benchmark comparison between your output and -O3 output
**Priority: LOW**

- [ ] **Take matrix multiply demo program**
  - Compile with `clang -O3`
  - Compile with your pipeline
  - Run both 1000 times
  - Measure wall clock time
  - Report actual measured speedup
  
- [ ] **Add to README and slides as real data point**
  - If speedup is small or zero, frame as: "Current optimization focus is memory safety hardening. Performance optimization is the next development phase."
  - Honesty about what system currently does versus what it's architected to do is a strength, not weakness

---

### TASK 13: Record the demo video
**Priority: LOW (but do not skip)**

Many hackathon submissions are evaluated asynchronously before live pitch.

#### Structure (exactly 3 minutes):
- [ ] **30 seconds on problem** (CISA mandate, $2.4T cost, 70% CVEs)
- [ ] **30 seconds on architecture** (show diagram)
- [ ] **90 seconds on live demo** (show fail→catch→prove sequence)
- [ ] **30 seconds on results and business case**

**Tip:** Record it twice. Use the second take. The first take always has a stumble.

---

## EXECUTION ORDER SUMMARY

Execute in strict sequence. Do not jump ahead.

1. **First:** Task 2 (fail→catch→prove demo sequence) - uses existing infrastructure, can be done immediately
2. **Second:** Task 1 Agent 2 only (real Bob @ir-architect call) - highest risk item, needs most testing time
3. **Third:** Task 3 (find non-trivial optimization) - run in parallel with Task 1, independent research work
4. **Fourth:** Task 5 (reframe all communication) - few hours, zero technical risk
5. **Fifth:** Task 1 Agent 3 then Granite supervisor - after Agent 2 is stable
6. **Sixth:** Task 6 (real C file testing) - validate pipeline on non-toy inputs
7. **Seventh:** Task 7 (dashboard) - make demo visually compelling
8. **Eighth:** Tasks 8, 10, 9 (badges, benchmark numbers, answer prep) - polish
9. **Ninth:** Task 11 (ZKP claim cleanup) - remove claim that could embarrass under questioning
10. **Last:** Task 13 (video recording) - only after everything else is stable and rehearsed

---

## Notes

- **Safety is the invariant:** No unverified transformation reaches output binary
- **Honesty over hype:** Accurate status beats misrepresented capabilities
- **Demo stability:** 3 working agents beat 9 broken agents
- **The money moment:** Showing AI mistake caught by formal verification is the entire value proposition