#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define MAX_DATA 100000

/* Mean — recomputes sum every call (no incremental update) */
double mean(double *data, int n) {
    double sum = 0.0;
    for (int i = 0; i < n; i++)
        sum += data[i];
    return sum / n;
}

/* Variance (population) */
double variance(double *data, int n) {
    double m = mean(data, n);   /* redundant: recomputes mean */
    double sum = 0.0;
    for (int i = 0; i < n; i++)
        sum += (data[i] - m) * (data[i] - m);
    return sum / n;
}

/* Standard deviation */
double std_dev(double *data, int n) {
    return sqrt(variance(data, n));   /* redundant: recomputes variance */
}

/* Median (sorts in place) */
static int cmp_double(const void *a, const void *b) {
    double x = *(double*)a, y = *(double*)b;
    return (x > y) - (x < y);
}
double median(double *data, int n) {
    double *copy = malloc(n * sizeof(double));
    memcpy(copy, data, n * sizeof(double));
    qsort(copy, n, sizeof(double), cmp_double);
    double m = (n % 2 == 0)
        ? (copy[n/2 - 1] + copy[n/2]) / 2.0
        : copy[n/2];
    free(copy);
    return m;
}

/* Pearson correlation coefficient */
double pearson(double *x, double *y, int n) {
    double mx = mean(x, n), my = mean(y, n);   /* redundant calls */
    double num = 0.0, dx2 = 0.0, dy2 = 0.0;
    for (int i = 0; i < n; i++) {
        double dx = x[i] - mx, dy = y[i] - my;
        num  += dx * dy;
        dx2  += dx * dx;
        dy2  += dy * dy;
    }
    return num / sqrt(dx2 * dy2);
}

/* Simple linear regression: y = a + b*x */
void linear_regression(double *x, double *y, int n, double *a, double *b) {
    double mx = mean(x, n), my = mean(y, n);   /* redundant calls */
    double sxy = 0.0, sxx = 0.0;
    for (int i = 0; i < n; i++) {
        sxy += (x[i] - mx) * (y[i] - my);
        sxx += (x[i] - mx) * (x[i] - mx);
    }
    *b = sxy / sxx;
    *a = my - (*b) * mx;
}

/* Polynomial regression (degree 2) via normal equations */
void poly_regression(double *x, double *y, int n, double *c) {
    /* c[0] + c[1]*x + c[2]*x^2 */
    double s[5] = {0};
    double r[3] = {0};
    for (int i = 0; i < n; i++) {
        double xi = x[i];
        s[0] += 1;
        s[1] += xi;
        s[2] += xi*xi;
        s[3] += xi*xi*xi;
        s[4] += xi*xi*xi*xi;
        r[0] += y[i];
        r[1] += y[i]*xi;
        r[2] += y[i]*xi*xi;
    }
    /* Solve 3x3 system (hardcoded Cramer's rule) */
    double A[3][3] = {{s[0],s[1],s[2]},{s[1],s[2],s[3]},{s[2],s[3],s[4]}};
    double det = A[0][0]*(A[1][1]*A[2][2]-A[1][2]*A[2][1])
               - A[0][1]*(A[1][0]*A[2][2]-A[1][2]*A[2][0])
               + A[0][2]*(A[1][0]*A[2][1]-A[1][1]*A[2][0]);
    c[0] = (r[0]*(A[1][1]*A[2][2]-A[1][2]*A[2][1])
           -A[0][1]*(r[1]*A[2][2]-A[1][2]*r[2])
           +A[0][2]*(r[1]*A[2][1]-A[1][1]*r[2]))/det;
    c[1] = (A[0][0]*(r[1]*A[2][2]-A[1][2]*r[2])
           -r[0]*(A[1][0]*A[2][2]-A[1][2]*A[2][0])
           +A[0][2]*(A[1][0]*r[2]-r[1]*A[2][0]))/det;
    c[2] = (A[0][0]*(A[1][1]*r[2]-r[1]*A[2][1])
           -A[0][1]*(A[1][0]*r[2]-r[1]*A[2][0])
           +r[0]*(A[1][0]*A[2][1]-A[1][1]*A[2][0]))/det;
}

/* Histogram (fixed bins) */
void histogram(double *data, int n, int bins, double lo, double hi) {
    int *counts = calloc(bins, sizeof(int));
    double width = (hi - lo) / bins;
    for (int i = 0; i < n; i++) {
        int b = (int)((data[i] - lo) / width);
        if (b >= 0 && b < bins) counts[b]++;
    }
    printf("Histogram (%d bins):\n", bins);
    for (int b = 0; b < bins; b++)
        printf("  [%.2f, %.2f): %d\n", lo + b*width, lo + (b+1)*width, counts[b]);
    free(counts);
}

/* Moving average (window = w) */
void moving_average(double *data, int n, int w, double *out) {
    for (int i = 0; i < n; i++) {
        double sum = 0.0;
        int count = 0;
        for (int j = i - w/2; j <= i + w/2; j++) {   /* recomputes full window each step */
            if (j >= 0 && j < n) { sum += data[j]; count++; }
        }
        out[i] = sum / count;
    }
}

/* Z-score normalization */
void z_score(double *data, int n, double *out) {
    double m = mean(data, n);
    double s = std_dev(data, n);   /* redundant: recomputes mean */
    for (int i = 0; i < n; i++)
        out[i] = (data[i] - m) / s;
}

/* Box-Muller transform: Gaussian random numbers */
void box_muller(double *u1, double *u2, double *z0, double *z1) {
    *z0 = sqrt(-2.0 * log(*u1)) * cos(2.0 * 3.14159265358979 * (*u2));
    *z1 = sqrt(-2.0 * log(*u1)) * sin(2.0 * 3.14159265358979 * (*u2));  /* sqrt recomputed */
}

int main(void) {
    int n = 10000;
    double *data = malloc(n * sizeof(double));
    double *data2 = malloc(n * sizeof(double));
    for (int i = 0; i < n; i++) {
        data[i]  = sin(i * 0.01) * 100 + (rand() % 20);
        data2[i] = cos(i * 0.01) * 100 + (rand() % 20);
    }

    printf("Mean:   %f\n", mean(data, n));
    printf("StdDev: %f\n", std_dev(data, n));
    printf("Median: %f\n", median(data, n));
    printf("Pearson correlation: %f\n", pearson(data, data2, n));

    double a, b;
    linear_regression(data, data2, n, &a, &b);
    printf("Linear regression: y = %f + %f * x\n", a, b);

    free(data); free(data2);
    return 0;
}
