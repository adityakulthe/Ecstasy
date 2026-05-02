// File 1: The callee that always returns 256
__attribute__((noinline)) int get_limit() {
    return 256;
}

// Made with Bob
