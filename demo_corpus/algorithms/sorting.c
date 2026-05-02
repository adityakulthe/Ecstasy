#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Bubble sort — O(n^2), no early exit */
void bubble_sort(int *arr, int n) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n - 1; j++)
            if (arr[j] > arr[j+1]) {
                int tmp = arr[j]; arr[j] = arr[j+1]; arr[j+1] = tmp;
            }
}

/* Selection sort */
void selection_sort(int *arr, int n) {
    for (int i = 0; i < n-1; i++) {
        int min = i;
        for (int j = i+1; j < n; j++)
            if (arr[j] < arr[min]) min = j;
        int tmp = arr[i]; arr[i] = arr[min]; arr[min] = tmp;
    }
}

/* Insertion sort */
void insertion_sort(int *arr, int n) {
    for (int i = 1; i < n; i++) {
        int key = arr[i], j = i - 1;
        while (j >= 0 && arr[j] > key) { arr[j+1] = arr[j]; j--; }
        arr[j+1] = key;
    }
}

/* Merge sort */
static void merge(int *arr, int l, int m, int r) {
    int n1 = m - l + 1, n2 = r - m;
    int *L = malloc(n1 * sizeof(int));
    int *R = malloc(n2 * sizeof(int));
    for (int i = 0; i < n1; i++) L[i] = arr[l+i];
    for (int j = 0; j < n2; j++) R[j] = arr[m+1+j];
    int i = 0, j = 0, k = l;
    while (i < n1 && j < n2) arr[k++] = (L[i] <= R[j]) ? L[i++] : R[j++];
    while (i < n1) arr[k++] = L[i++];
    while (j < n2) arr[k++] = R[j++];
    free(L); free(R);
}
void merge_sort(int *arr, int l, int r) {
    if (l < r) {
        int m = (l + r) / 2;
        merge_sort(arr, l, m);
        merge_sort(arr, m+1, r);
        merge(arr, l, m, r);
    }
}

/* Quicksort (pivot = last element — pathological on sorted input) */
static int partition(int *arr, int lo, int hi) {
    int pivot = arr[hi], i = lo - 1;
    for (int j = lo; j < hi; j++)
        if (arr[j] <= pivot) { i++; int t=arr[i];arr[i]=arr[j];arr[j]=t; }
    int t=arr[i+1];arr[i+1]=arr[hi];arr[hi]=t;
    return i+1;
}
void quicksort(int *arr, int lo, int hi) {
    if (lo < hi) {
        int p = partition(arr, lo, hi);
        quicksort(arr, lo, p-1);
        quicksort(arr, p+1, hi);
    }
}

/* Heapsort */
static void heapify(int *arr, int n, int i) {
    int largest = i, l = 2*i+1, r = 2*i+2;
    if (l < n && arr[l] > arr[largest]) largest = l;
    if (r < n && arr[r] > arr[largest]) largest = r;
    if (largest != i) {
        int t=arr[i]; arr[i]=arr[largest]; arr[largest]=t;
        heapify(arr, n, largest);
    }
}
void heapsort(int *arr, int n) {
    for (int i = n/2-1; i >= 0; i--) heapify(arr, n, i);
    for (int i = n-1; i > 0; i--) {
        int t=arr[0]; arr[0]=arr[i]; arr[i]=t;
        heapify(arr, i, 0);
    }
}

/* Counting sort */
void counting_sort(int *arr, int n, int max_val) {
    int *count = calloc(max_val+1, sizeof(int));
    for (int i = 0; i < n; i++) count[arr[i]]++;
    int idx = 0;
    for (int i = 0; i <= max_val; i++)
        while (count[i]-- > 0) arr[idx++] = i;
    free(count);
}

/* Radix sort (LSD, base 10) */
static void counting_sort_digit(int *arr, int n, int exp) {
    int *out = malloc(n * sizeof(int));
    int count[10] = {0};
    for (int i = 0; i < n; i++) count[(arr[i]/exp) % 10]++;
    for (int i = 1; i < 10; i++) count[i] += count[i-1];
    for (int i = n-1; i >= 0; i--) out[--count[(arr[i]/exp)%10]] = arr[i];
    memcpy(arr, out, n*sizeof(int));
    free(out);
}
void radix_sort(int *arr, int n) {
    int mx = arr[0];
    for (int i = 1; i < n; i++) if (arr[i] > mx) mx = arr[i];
    for (int exp = 1; mx/exp > 0; exp *= 10)
        counting_sort_digit(arr, n, exp);
}

/* Binary search */
int binary_search(int *arr, int n, int target) {
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}

int main(void) {
    int n = 10000;
    int *arr = malloc(n * sizeof(int));
    srand(42);
    for (int i = 0; i < n; i++) arr[i] = rand() % 100000;

    int *copy = malloc(n * sizeof(int));

    memcpy(copy, arr, n*sizeof(int)); heapsort(copy, n);
    printf("Heapsort done. arr[0]=%d arr[n-1]=%d\n", copy[0], copy[n-1]);

    memcpy(copy, arr, n*sizeof(int)); merge_sort(copy, 0, n-1);
    printf("Mergesort done. arr[0]=%d arr[n-1]=%d\n", copy[0], copy[n-1]);

    printf("Binary search for 50000: index=%d\n", binary_search(copy, n, 50000));

    free(arr); free(copy);
    return 0;
}
