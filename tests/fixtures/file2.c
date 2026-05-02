// file2.c - separate translation unit
extern int get_buffer_limit();

void process(char* buf, int n) {
    if (n > get_buffer_limit()) return;
    for (int i = 0; i < n; i++) 
        buf[i] = 0;
}

// Made with Bob
