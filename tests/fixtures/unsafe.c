#include <stdio.h>

int main() {
    char buf[10];
    scanf("%s", buf);  // Unsafe: no bounds checking!
    printf("%s\n", buf);
    return 0;
}

// Made with Bob
