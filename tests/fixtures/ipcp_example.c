// Example showing optimization that clang -O3 misses without LTO
// Compile with: clang -O3 -S -emit-llvm ipcp_example.c -o ipcp_example.ll

// Force function boundary - clang -O3 CANNOT inline this
__attribute__((noinline)) int get_limit() {
    return 256;
}

void process(char* buf, int n) {
    // This check is redundant since get_limit() always returns 256
    // But clang -O3 doesn't know that without LTO
    if (n > get_limit()) return;
    
    for (int i = 0; i < n; i++) {
        buf[i] = 0;
    }
}

// Made with Bob
