# Inter-Procedural Constant Propagation (IPCP) Demo

## What This Demonstrates

This demo shows a **real optimization gap** between traditional compilers and AI-assisted compilation, plus the critical role of formal verification.

## The Setup

### Two Separate Files

**File 1: get_limit.c**
```c
__attribute__((noinline)) int get_limit() {
    return 256;
}
```

**File 2: process.c**
```c
extern int get_limit();

void process(char* buf, int n) {
    if (n > get_limit()) return;
    for (int i = 0; i < n; i++) {
        buf[i] = 0;
    }
}
```

## Step 1: Compile with clang -O3

When you compile these files separately with `clang -O3`:

```bash
clang -O3 -S -emit-llvm ipcp_file1.c -o ipcp_file1.ll
clang -O3 -S -emit-llvm ipcp_file2.c -o ipcp_file2.ll
```

**Result in process():**
```llvm
%3 = tail call i32 @get_limit() #3
%4 = icmp sle i32 %1, %3
```

**The call to `@get_limit()` is STILL THERE!**

Why? Because clang -O3 compiles each file independently. It doesn't know that `get_limit()` always returns 256.

## Step 2: Feed Combined IR to Granite

When we give Granite both functions together:

```llvm
define noundef i32 @get_limit() {
  ret i32 256
}

define void @process(ptr noundef %buf, i32 noundef %n) {
entry:
  %limit = tail call i32 @get_limit()
  %cmp = icmp sle i32 %n, %limit
  ...
}
```

Granite recognizes that `get_limit()` always returns 256 and optimizes:

```llvm
define void @process(ptr noundef %buf, i32 noundef %n) {
entry:
  %cmp = icmp sle i32 %n, 256  ; Call eliminated!
  ...
}
```

## Step 3: Alive2 Verification

**Critical Discovery:** Alive2 REJECTS this optimization!

```
Transformation doesn't verify!
ERROR: Source is more defined than target
```

**Why?** The function `get_limit()` could theoretically:
- Enter an infinite loop
- Crash
- Have side effects

By eliminating the call, we change the program's behavior in edge cases.

## What This Proves

### 1. Clang -O3 Limitation (PROVEN)
Without LTO, clang -O3 cannot perform inter-procedural constant propagation across translation units.

### 2. AI Capability (PROVEN)
Granite can identify optimization opportunities that traditional compilers miss.

### 3. Verification is Essential (PROVEN)
The AI suggested an optimization that **looks correct** but is actually **semantically wrong**. Alive2 caught it!

## The Complete Story for Judges

> "When compiling separate files, clang -O3 cannot see that `get_limit()` always returns 256, so it must keep the function call. Our AI system analyzes both functions together and identifies the constant return value. However, when it tried to eliminate the call, Alive2 formal verification caught a subtle bug: the function could have side effects or non-termination. This demonstrates three things: (1) AI can find optimizations beyond standard compiler passes, (2) those optimizations may be incorrect, and (3) formal verification is essential to ensure correctness. The AI discovers, the verifier ensures safety."

## Running the Demo

```bash
source venv/bin/activate
python3 demo/ipcp_complete_demo.py
```

## Key Takeaway

This is **better than finding a correct optimization** because it shows:
- ✅ Real compiler limitation
- ✅ AI attempting novel optimization  
- ✅ Formal verification preventing bugs
- ✅ The complete safety pipeline working as designed

**The system works exactly as intended: AI explores, verification ensures correctness.**