#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define PI 3.14159265358979323846

typedef struct { double re, im; } complex_t;

/* Complex multiply */
static complex_t cmul(complex_t a, complex_t b) {
    return (complex_t){ a.re*b.re - a.im*b.im, a.re*b.im + a.im*b.re };
}

/* Complex add / subtract */
static complex_t cadd(complex_t a, complex_t b) { return (complex_t){ a.re+b.re, a.im+b.im }; }
static complex_t csub(complex_t a, complex_t b) { return (complex_t){ a.re-b.re, a.im-b.im }; }

/* Cooley-Tukey FFT (radix-2, iterative) */
void fft(complex_t *X, int n, int inverse) {
    /* Bit-reversal permutation */
    for (int i = 1, j = 0; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) { complex_t tmp = X[i]; X[i] = X[j]; X[j] = tmp; }
    }

    /* FFT butterfly */
    for (int len = 2; len <= n; len <<= 1) {
        double ang = 2 * PI / len * (inverse ? -1 : 1);
        complex_t wlen = { cos(ang), sin(ang) };
        for (int i = 0; i < n; i += len) {
            complex_t w = { 1.0, 0.0 };
            for (int j = 0; j < len/2; j++) {
                complex_t u = X[i+j];
                complex_t v = cmul(X[i+j+len/2], w);
                X[i+j]         = cadd(u, v);
                X[i+j+len/2]   = csub(u, v);
                w = cmul(w, wlen);
            }
        }
    }

    if (inverse)
        for (int i = 0; i < n; i++) { X[i].re /= n; X[i].im /= n; }
}

/* Naive DFT O(n^2) — optimization target */
void dft_naive(double *x, complex_t *X, int n) {
    for (int k = 0; k < n; k++) {
        X[k].re = 0.0; X[k].im = 0.0;
        for (int t = 0; t < n; t++) {
            double angle = 2 * PI * k * t / n;
            X[k].re += x[t] * cos(angle);   /* cos/sin recomputed for same angle */
            X[k].im -= x[t] * sin(angle);
        }
    }
}

/* Power spectral density */
void psd(complex_t *X, double *P, int n) {
    for (int i = 0; i < n; i++)
        P[i] = (X[i].re * X[i].re + X[i].im * X[i].im) / n;
}

/* Convolution via FFT */
void fft_convolve(double *a, double *b, double *out, int n) {
    complex_t *fa = calloc(n, sizeof(complex_t));
    complex_t *fb = calloc(n, sizeof(complex_t));
    for (int i = 0; i < n; i++) { fa[i].re = a[i]; fb[i].re = b[i]; }
    fft(fa, n, 0);
    fft(fb, n, 0);
    for (int i = 0; i < n; i++) fa[i] = cmul(fa[i], fb[i]);
    fft(fa, n, 1);
    for (int i = 0; i < n; i++) out[i] = fa[i].re;
    free(fa); free(fb);
}

/* FIR low-pass filter (windowed sinc) */
void fir_lowpass(double cutoff, int taps, double *h) {
    int M = taps - 1;
    for (int i = 0; i <= M; i++) {
        if (i == M/2)
            h[i] = 2.0 * cutoff;
        else {
            double x = PI * (i - M/2.0);
            h[i] = sin(2.0 * PI * cutoff * (i - M/2.0)) / x;
        }
        /* Hamming window */
        h[i] *= 0.54 - 0.46 * cos(2.0 * PI * i / M);
    }
}

/* Apply FIR filter */
void fir_filter(double *signal, int n, double *h, int taps, double *out) {
    for (int i = 0; i < n; i++) {
        out[i] = 0.0;
        for (int j = 0; j < taps; j++) {
            if (i - j >= 0)
                out[i] += h[j] * signal[i - j];
        }
    }
}

/* Zero-crossing rate */
double zero_crossing_rate(double *signal, int n) {
    int crossings = 0;
    for (int i = 1; i < n; i++)
        if ((signal[i] >= 0) != (signal[i-1] >= 0))
            crossings++;
    return (double)crossings / (n - 1);
}

/* Root mean square energy */
double rms_energy(double *signal, int n) {
    double sum = 0.0;
    for (int i = 0; i < n; i++)
        sum += signal[i] * signal[i];
    return sqrt(sum / n);
}

int main(void) {
    int n = 1024;
    complex_t *X = calloc(n, sizeof(complex_t));
    double *P    = malloc(n * sizeof(double));

    /* Synthesize: 50Hz + 120Hz sine wave */
    for (int i = 0; i < n; i++)
        X[i].re = sin(2*PI*50*i/n) + 0.5*sin(2*PI*120*i/n);

    fft(X, n, 0);
    psd(X, P, n);

    double max_power = 0.0;
    int peak_bin = 0;
    for (int i = 0; i < n/2; i++)
        if (P[i] > max_power) { max_power = P[i]; peak_bin = i; }

    printf("Peak frequency bin: %d (power=%.4f)\n", peak_bin, max_power);

    free(X); free(P);
    return 0;
}
