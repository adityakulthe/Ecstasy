#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Classic buffer overflow — no bounds checking on user input */
void greet_user(char *name) {
    char buf[16];
    strcpy(buf, name);   /* ⚠️ UNSAFE: no length check */
    printf("Hello, %s!\n", buf);
}

/* Unsafe scanf — can overflow stack buffer */
void read_username(void) {
    char username[32];
    scanf("%s", username);   /* ⚠️ UNSAFE: no width specifier */
    printf("User: %s\n", username);
}

/* gets() — removed from C11 but still compiled by many codebases */
void legacy_input(void) {
    char line[64];
    /* gets(line); */   /* ⚠️ UNSAFE: unbounded read — left as comment */
    fgets(line, sizeof(line), stdin);
    printf("Input: %s\n", line);
}

/* Off-by-one error in loop */
void process_array(int *arr, int n) {
    int sum = 0;
    for (int i = 0; i <= n; i++)   /* ⚠️ UNSAFE: reads arr[n] (out of bounds) */
        sum += arr[i];
    printf("Sum: %d\n", sum);
}

/* Use-after-free */
void use_after_free_demo(void) {
    int *ptr = malloc(10 * sizeof(int));
    for (int i = 0; i < 10; i++) ptr[i] = i;
    free(ptr);
    printf("Value: %d\n", ptr[5]);   /* ⚠️ UNSAFE: use after free */
}

/* Double-free */
void double_free_demo(void) {
    char *buf = malloc(100);
    strncpy(buf, "hello", 100);
    free(buf);
    free(buf);   /* ⚠️ UNSAFE: double free */
}

/* Integer overflow leading to heap underallocation */
void int_overflow_alloc(int len) {
    /* If len is large enough, len+1 overflows to a small number */
    char *buf = malloc(len + 1);   /* ⚠️ UNSAFE: no overflow check */
    if (!buf) return;
    memset(buf, 'A', len);
    buf[len] = '\0';
    free(buf);
}

/* Format string vulnerability */
void log_message(char *user_input) {
    printf(user_input);   /* ⚠️ UNSAFE: format string attack */
}

/* Stack-based buffer overflow in recursive function */
int vulnerable_sum(int n) {
    char padding[1024];   /* large stack allocation in each frame */
    memset(padding, 0, sizeof(padding));
    if (n <= 0) return 0;
    return n + vulnerable_sum(n - 1);   /* deep recursion = stack exhaustion */
}

/* Null pointer dereference */
void null_deref(int *ptr) {
    if (ptr == NULL)
        printf("Error: null\n");
    /* Missing else — falls through and dereferences */
    printf("Value: %d\n", *ptr);   /* ⚠️ UNSAFE if ptr is NULL */
}

/* Unsafe string concatenation */
void build_path(char *base, char *filename) {
    char path[256];
    strcpy(path, base);
    strcat(path, "/");           /* ⚠️ UNSAFE: no bounds check */
    strcat(path, filename);      /* ⚠️ UNSAFE: could overflow path[] */
    printf("Path: %s\n", path);
}

/* Signed integer overflow (undefined behavior) */
int signed_overflow(int a, int b) {
    return a + b;   /* ⚠️ UNSAFE: overflow is UB in C */
}

int main(void) {
    /* Safe calls for demo */
    int arr[] = {1, 2, 3, 4, 5};
    /* process_array(arr, 5); — skipped to avoid crash */

    greet_user("Alice");
    build_path("/home/user", "file.txt");

    int x = signed_overflow(2000000000, 200000000);
    printf("Overflow result: %d\n", x);

    return 0;
}
