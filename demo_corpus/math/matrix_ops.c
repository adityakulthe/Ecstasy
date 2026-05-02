#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#define MAX_N 512

/* Dense matrix multiply — naive O(n^3), no cache tiling */
void matmul(double *A, double *B, double *C, int n) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) {
            C[i*n+j] = 0.0;
            for (int k = 0; k < n; k++)
                C[i*n+j] += A[i*n+k] * B[k*n+j];
        }
}

/* Matrix transpose — in-place for square */
void transpose(double *A, int n) {
    for (int i = 0; i < n; i++)
        for (int j = i+1; j < n; j++) {
            double tmp = A[i*n+j];
            A[i*n+j] = A[j*n+i];
            A[j*n+i] = tmp;
        }
}

/* Frobenius norm */
double frobenius_norm(double *A, int n) {
    double sum = 0.0;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            sum += A[i*n+j] * A[i*n+j];
    return sqrt(sum);
}

/* Determinant via cofactor expansion — O(n!) */
double determinant(double A[MAX_N][MAX_N], int n) {
    if (n == 1) return A[0][0];
    if (n == 2) return A[0][0]*A[1][1] - A[0][1]*A[1][0];

    double det = 0.0;
    double sub[MAX_N][MAX_N];

    for (int c = 0; c < n; c++) {
        int subi = 0;
        for (int i = 1; i < n; i++) {
            int subj = 0;
            for (int j = 0; j < n; j++) {
                if (j == c) continue;
                sub[subi][subj] = A[i][j];
                subj++;
            }
            subi++;
        }
        det += (c % 2 == 0 ? 1 : -1) * A[0][c] * determinant(sub, n-1);
    }
    return det;
}

/* LU decomposition (Doolittle) */
void lu_decompose(double *A, double *L, double *U, int n) {
    for (int i = 0; i < n; i++) {
        /* Upper triangular */
        for (int k = i; k < n; k++) {
            double sum = 0.0;
            for (int j = 0; j < i; j++)
                sum += L[i*n+j] * U[j*n+k];
            U[i*n+k] = A[i*n+k] - sum;
        }
        /* Lower triangular */
        for (int k = i; k < n; k++) {
            if (i == k)
                L[i*n+i] = 1.0;
            else {
                double sum = 0.0;
                for (int j = 0; j < i; j++)
                    sum += L[k*n+j] * U[j*n+i];
                L[k*n+i] = (A[k*n+i] - sum) / U[i*n+i];
            }
        }
    }
}

/* Forward substitution Ly = b */
void forward_sub(double *L, double *b, double *y, int n) {
    for (int i = 0; i < n; i++) {
        y[i] = b[i];
        for (int j = 0; j < i; j++)
            y[i] -= L[i*n+j] * y[j];
    }
}

/* Back substitution Ux = y */
void back_sub(double *U, double *y, double *x, int n) {
    for (int i = n-1; i >= 0; i--) {
        x[i] = y[i];
        for (int j = i+1; j < n; j++)
            x[i] -= U[i*n+j] * x[j];
        x[i] /= U[i*n+i];
    }
}

/* Power iteration for dominant eigenvalue */
double power_iteration(double *A, double *v, int n, int max_iter) {
    double *Av = (double *)malloc(n * sizeof(double));
    double lambda = 0.0;

    for (int iter = 0; iter < max_iter; iter++) {
        /* Av = A * v */
        for (int i = 0; i < n; i++) {
            Av[i] = 0.0;
            for (int j = 0; j < n; j++)
                Av[i] += A[i*n+j] * v[j];
        }
        /* Rayleigh quotient */
        double num = 0.0, den = 0.0;
        for (int i = 0; i < n; i++) {
            num += v[i] * Av[i];
            den += v[i] * v[i];
        }
        lambda = num / den;

        /* Normalize */
        double norm = 0.0;
        for (int i = 0; i < n; i++) norm += Av[i] * Av[i];
        norm = sqrt(norm);
        for (int i = 0; i < n; i++) v[i] = Av[i] / norm;
    }
    free(Av);
    return lambda;
}

/* Strassen 2x2 base case (illustrative) */
void strassen_2x2(double A[2][2], double B[2][2], double C[2][2]) {
    double m1 = (A[0][0] + A[1][1]) * (B[0][0] + B[1][1]);
    double m2 = (A[1][0] + A[1][1]) *  B[0][0];
    double m3 =  A[0][0] * (B[0][1] - B[1][1]);
    double m4 =  A[1][1] * (B[1][0] - B[0][0]);
    double m5 = (A[0][0] + A[0][1]) *  B[1][1];
    double m6 = (A[1][0] - A[0][0]) * (B[0][0] + B[0][1]);
    double m7 = (A[0][1] - A[1][1]) * (B[1][0] + B[1][1]);

    C[0][0] = m1 + m4 - m5 + m7;
    C[0][1] = m3 + m5;
    C[1][0] = m2 + m4;
    C[1][1] = m1 - m2 + m3 + m6;
}

int main(void) {
    int n = 64;
    double *A = calloc(n*n, sizeof(double));
    double *B = calloc(n*n, sizeof(double));
    double *C = calloc(n*n, sizeof(double));

    for (int i = 0; i < n*n; i++) { A[i] = i * 0.01; B[i] = (n*n - i) * 0.01; }

    matmul(A, B, C, n);
    printf("Frobenius norm of C: %f\n", frobenius_norm(C, n));

    free(A); free(B); free(C);
    return 0;
}
