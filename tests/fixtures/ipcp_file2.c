// File 2: The caller that doesn't know get_limit() returns 256
extern int get_limit();

void process(char* buf, int n) {
    // This check calls get_limit() - clang -O3 cannot eliminate it
    // because get_limit() is in a different translation unit
    if (n > get_limit()) return;
    
    for (int i = 0; i < n; i++) {
        buf[i] = 0;
    }
}

// Made with Bob
