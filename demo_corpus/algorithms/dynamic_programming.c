#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_N 10000
#define INF 1e18

/* Fibonacci — naive exponential (classic optimization target) */
long long fib_naive(int n) {
    if (n <= 1) return n;
    return fib_naive(n-1) + fib_naive(n-2);
}

/* Fibonacci — memoized */
static long long memo[100] = {0};
long long fib_memo(int n) {
    if (n <= 1) return n;
    if (memo[n]) return memo[n];
    return memo[n] = fib_memo(n-1) + fib_memo(n-2);
}

/* 0/1 Knapsack */
int knapsack(int *weights, int *values, int n, int capacity) {
    int **dp = malloc((n+1) * sizeof(int*));
    for (int i = 0; i <= n; i++) dp[i] = calloc(capacity+1, sizeof(int));

    for (int i = 1; i <= n; i++)
        for (int w = 0; w <= capacity; w++) {
            dp[i][w] = dp[i-1][w];
            if (weights[i-1] <= w) {
                int val = dp[i-1][w - weights[i-1]] + values[i-1];
                if (val > dp[i][w]) dp[i][w] = val;
            }
        }

    int result = dp[n][capacity];
    for (int i = 0; i <= n; i++) free(dp[i]);
    free(dp);
    return result;
}

/* Longest Common Subsequence */
int lcs(char *s1, char *s2, int m, int n) {
    int **dp = malloc((m+1) * sizeof(int*));
    for (int i = 0; i <= m; i++) dp[i] = calloc(n+1, sizeof(int));

    for (int i = 1; i <= m; i++)
        for (int j = 1; j <= n; j++) {
            if (s1[i-1] == s2[j-1])
                dp[i][j] = dp[i-1][j-1] + 1;
            else
                dp[i][j] = dp[i-1][j] > dp[i][j-1] ? dp[i-1][j] : dp[i][j-1];
        }

    int result = dp[m][n];
    for (int i = 0; i <= m; i++) free(dp[i]);
    free(dp);
    return result;
}

/* Edit distance (Levenshtein) */
int edit_distance(char *s1, char *s2, int m, int n) {
    int **dp = malloc((m+1) * sizeof(int*));
    for (int i = 0; i <= m; i++) {
        dp[i] = malloc((n+1) * sizeof(int));
        dp[i][0] = i;
    }
    for (int j = 0; j <= n; j++) dp[0][j] = j;

    for (int i = 1; i <= m; i++)
        for (int j = 1; j <= n; j++) {
            int cost = (s1[i-1] != s2[j-1]);
            int del  = dp[i-1][j] + 1;
            int ins  = dp[i][j-1] + 1;
            int sub  = dp[i-1][j-1] + cost;
            dp[i][j] = del < ins ? (del < sub ? del : sub) : (ins < sub ? ins : sub);
        }

    int result = dp[m][n];
    for (int i = 0; i <= m; i++) free(dp[i]);
    free(dp);
    return result;
}

/* Coin change (minimum coins) */
int coin_change(int *coins, int n_coins, int amount) {
    int *dp = malloc((amount+1) * sizeof(int));
    for (int i = 0; i <= amount; i++) dp[i] = amount + 1;
    dp[0] = 0;
    for (int i = 1; i <= amount; i++)
        for (int j = 0; j < n_coins; j++)
            if (coins[j] <= i && dp[i - coins[j]] + 1 < dp[i])
                dp[i] = dp[i - coins[j]] + 1;
    int result = dp[amount] > amount ? -1 : dp[amount];
    free(dp);
    return result;
}

/* Matrix chain multiplication (minimum operations) */
int matrix_chain(int *p, int n) {
    int **dp = malloc(n * sizeof(int*));
    for (int i = 0; i < n; i++) dp[i] = calloc(n, sizeof(int));

    for (int len = 2; len < n; len++)
        for (int i = 1; i < n - len + 1; i++) {
            int j = i + len - 1;
            dp[i][j] = 2147483647;
            for (int k = i; k < j; k++) {
                int cost = dp[i][k] + dp[k+1][j] + p[i-1]*p[k]*p[j];
                if (cost < dp[i][j]) dp[i][j] = cost;
            }
        }

    int result = dp[1][n-1];
    for (int i = 0; i < n; i++) free(dp[i]);
    free(dp);
    return result;
}

/* Longest increasing subsequence (O(n^2)) */
int lis(int *arr, int n) {
    int *dp = malloc(n * sizeof(int));
    for (int i = 0; i < n; i++) dp[i] = 1;
    int max_len = 1;
    for (int i = 1; i < n; i++) {
        for (int j = 0; j < i; j++)
            if (arr[j] < arr[i] && dp[j] + 1 > dp[i])
                dp[i] = dp[j] + 1;
        if (dp[i] > max_len) max_len = dp[i];
    }
    free(dp);
    return max_len;
}

/* Maximum subarray (Kadane's) */
int max_subarray(int *arr, int n) {
    int max_so_far = arr[0], max_ending_here = arr[0];
    for (int i = 1; i < n; i++) {
        max_ending_here = arr[i] > max_ending_here + arr[i] ? arr[i] : max_ending_here + arr[i];
        if (max_ending_here > max_so_far) max_so_far = max_ending_here;
    }
    return max_so_far;
}

/* Rod cutting */
int rod_cutting(int *prices, int n) {
    int *dp = calloc(n+1, sizeof(int));
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= i; j++)
            if (prices[j-1] + dp[i-j] > dp[i])
                dp[i] = prices[j-1] + dp[i-j];
    int result = dp[n];
    free(dp);
    return result;
}

int main(void) {
    printf("Fib(10) naive: %lld\n", fib_naive(10));
    printf("Fib(40) memo:  %lld\n", fib_memo(40));

    int weights[] = {2, 3, 4, 5};
    int values[]  = {3, 4, 5, 6};
    printf("Knapsack(capacity=8): %d\n", knapsack(weights, values, 4, 8));

    char s1[] = "ABCBDAB", s2[] = "BDCAB";
    printf("LCS: %d\n", lcs(s1, s2, 7, 5));
    printf("Edit distance: %d\n", edit_distance(s1, s2, 7, 5));

    int coins[] = {1, 5, 10, 25};
    printf("Coin change(67): %d\n", coin_change(coins, 4, 67));

    int arr[] = {10, 9, 2, 5, 3, 7, 101, 18};
    printf("LIS: %d\n", lis(arr, 8));

    int subarr[] = {-2,1,-3,4,-1,2,1,-5,4};
    printf("Max subarray: %d\n", max_subarray(subarr, 9));

    return 0;
}
