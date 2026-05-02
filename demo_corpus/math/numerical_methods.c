#include <stdio.h>
#include <math.h>
#include <stdlib.h>

#define PI 3.14159265358979323846
#define EPSILON 1e-10
#define MAX_ITER 10000

/* Newton-Raphson root finding */
double newton_raphson(double (*f)(double), double (*df)(double), double x0, int max_iter) {
    double x = x0;
    for (int i = 0; i < max_iter; i++) {
        double fx = f(x);
        if (fabs(fx) < EPSILON) break;
        x = x - fx / df(x);
    }
    return x;
}

/* Bisection method */
double bisection(double (*f)(double), double a, double b, double tol) {
    double fa = f(a);
    double mid = a;
    while ((b - a) / 2.0 > tol) {
        mid = (a + b) / 2.0;
        double fm = f(mid);
        if (fabs(fm) < tol) break;
        if (fa * fm < 0) { b = mid; }
        else { a = mid; fa = fm; }
    }
    return mid;
}

/* Secant method */
double secant(double (*f)(double), double x0, double x1, int max_iter) {
    for (int i = 0; i < max_iter; i++) {
        double f0 = f(x0), f1 = f(x1);
        if (fabs(f1 - f0) < EPSILON) break;
        double x2 = x1 - f1 * (x1 - x0) / (f1 - f0);
        x0 = x1;
        x1 = x2;
        if (fabs(x1 - x0) < EPSILON) break;
    }
    return x1;
}

/* Simpson's rule integration */
double simpsons(double (*f)(double), double a, double b, int n) {
    if (n % 2 != 0) n++;
    double h = (b - a) / n;
    double sum = f(a) + f(b);
    for (int i = 1; i < n; i++) {
        double x = a + i * h;
        sum += (i % 2 == 0 ? 2.0 : 4.0) * f(x);
    }
    return sum * h / 3.0;
}

/* Gaussian quadrature (5-point) */
double gauss_legendre_5(double (*f)(double), double a, double b) {
    static const double nodes[] = {
        -0.9061798459, -0.5384693101, 0.0,
         0.5384693101,  0.9061798459
    };
    static const double weights[] = {
        0.2369268851, 0.4786286705, 0.5688888889,
        0.4786286705, 0.2369268851
    };
    double mid = (a + b) / 2.0;
    double half = (b - a) / 2.0;
    double result = 0.0;
    for (int i = 0; i < 5; i++)
        result += weights[i] * f(mid + half * nodes[i]);
    return half * result;
}

/* Runge-Kutta 4th order ODE solver */
void rk4(double (*f)(double, double), double y0, double t0, double t1, int steps, double *y_out) {
    double h = (t1 - t0) / steps;
    double t = t0, y = y0;
    y_out[0] = y;
    for (int i = 1; i <= steps; i++) {
        double k1 = f(t, y);
        double k2 = f(t + h/2, y + h*k1/2);
        double k3 = f(t + h/2, y + h*k2/2);
        double k4 = f(t + h, y + h*k3);
        y += h * (k1 + 2*k2 + 2*k3 + k4) / 6.0;
        t += h;
        y_out[i] = y;
    }
}

/* Euler method ODE (naive, for comparison) */
void euler(double (*f)(double, double), double y0, double t0, double t1, int steps, double *y_out) {
    double h = (t1 - t0) / steps;
    double t = t0, y = y0;
    y_out[0] = y;
    for (int i = 1; i <= steps; i++) {
        y += h * f(t, y);
        t += h;
        y_out[i] = y;
    }
}

/* Gradient descent for f(x) = x^4 - 3x^3 + 2 */
double gradient_descent(double x0, double lr, int iters) {
    double x = x0;
    for (int i = 0; i < iters; i++) {
        double grad = 4*x*x*x - 9*x*x;
        x -= lr * grad;
    }
    return x;
}

/* Trapezoidal rule */
double trapezoidal(double (*f)(double), double a, double b, int n) {
    double h = (b - a) / n;
    double sum = (f(a) + f(b)) / 2.0;
    for (int i = 1; i < n; i++)
        sum += f(a + i * h);
    return sum * h;
}

/* Romberg integration (Richardson extrapolation) */
double romberg(double (*f)(double), double a, double b, int order) {
    double R[10][10];
    int n = 1;
    R[0][0] = (f(a) + f(b)) * (b - a) / 2.0;
    for (int i = 1; i < order; i++) {
        n *= 2;
        double h = (b - a) / n;
        double sum = 0.0;
        for (int k = 1; k < n; k += 2)
            sum += f(a + k * h);
        R[i][0] = R[i-1][0] / 2.0 + h * sum;
        for (int j = 1; j <= i; j++) {
            double factor = pow(4.0, j);
            R[i][j] = (factor * R[i][j-1] - R[i-1][j-1]) / (factor - 1);
        }
    }
    return R[order-1][order-1];
}

/* Taylor series for e^x (redundant computation — good optimization target) */
double taylor_exp(double x, int terms) {
    double result = 0.0;
    double term = 1.0;
    for (int n = 0; n < terms; n++) {
        result += term;
        term *= x / (n + 1);   /* recomputes factorial incrementally */
    }
    return result;
}

/* Taylor series for sin(x) */
double taylor_sin(double x, int terms) {
    double result = 0.0;
    double sign = 1.0;
    double power = x;
    double fact = 1.0;
    for (int n = 0; n < terms; n++) {
        result += sign * power / fact;
        sign = -sign;
        power *= x * x;
        fact *= (2*n + 2) * (2*n + 3);
    }
    return result;
}

/* Helper functions for root finding demos */
static double f_cubic(double x) { return x*x*x - x - 2; }
static double df_cubic(double x) { return 3*x*x - 1; }
static double f_ode(double t, double y) { return -2 * y + t; }

int main(void) {
    double root = newton_raphson(f_cubic, df_cubic, 1.5, 100);
    printf("Newton root of x^3-x-2: %f\n", root);

    double integ = simpsons(sin, 0.0, PI, 1000);
    printf("Integral of sin(0..pi): %f\n", integ);

    double *y = malloc(1001 * sizeof(double));
    rk4(f_ode, 1.0, 0.0, 5.0, 1000, y);
    printf("RK4 y(5) for y'=-2y+t: %f\n", y[1000]);

    printf("Taylor exp(1): %f\n", taylor_exp(1.0, 20));
    printf("Taylor sin(pi/6): %f\n", taylor_sin(PI/6, 15));

    free(y);
    return 0;
}
