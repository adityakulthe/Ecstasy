#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define MAX_BODIES 1000
#define G 6.674e-11
#define DT 0.01
#define SOFTENING 1e-9

typedef struct {
    double x, y, z;
    double vx, vy, vz;
    double mass;
} Body;

/* Naive O(n^2) N-body gravitational simulation */
void compute_forces(Body *bodies, int n, double *fx, double *fy, double *fz) {
    memset(fx, 0, n * sizeof(double));
    memset(fy, 0, n * sizeof(double));
    memset(fz, 0, n * sizeof(double));

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (i == j) continue;
            double dx = bodies[j].x - bodies[i].x;
            double dy = bodies[j].y - bodies[i].y;
            double dz = bodies[j].z - bodies[i].z;

            /* Distance computed redundantly for both i and j */
            double dist2 = dx*dx + dy*dy + dz*dz + SOFTENING;
            double dist  = sqrt(dist2);
            double dist3 = dist2 * dist;

            double f = G * bodies[i].mass * bodies[j].mass / dist3;
            fx[i] += f * dx;
            fy[i] += f * dy;
            fz[i] += f * dz;
        }
    }
}

/* Leapfrog integrator */
void step_leapfrog(Body *bodies, int n, double dt) {
    double *fx = malloc(n * sizeof(double));
    double *fy = malloc(n * sizeof(double));
    double *fz = malloc(n * sizeof(double));

    compute_forces(bodies, n, fx, fy, fz);

    for (int i = 0; i < n; i++) {
        double ax = fx[i] / bodies[i].mass;
        double ay = fy[i] / bodies[i].mass;
        double az = fz[i] / bodies[i].mass;

        bodies[i].vx += ax * dt;
        bodies[i].vy += ay * dt;
        bodies[i].vz += az * dt;

        bodies[i].x += bodies[i].vx * dt;
        bodies[i].y += bodies[i].vy * dt;
        bodies[i].z += bodies[i].vz * dt;
    }
    free(fx); free(fy); free(fz);
}

/* Total kinetic energy */
double kinetic_energy(Body *bodies, int n) {
    double ke = 0.0;
    for (int i = 0; i < n; i++) {
        double v2 = bodies[i].vx*bodies[i].vx
                  + bodies[i].vy*bodies[i].vy
                  + bodies[i].vz*bodies[i].vz;
        ke += 0.5 * bodies[i].mass * v2;
    }
    return ke;
}

/* Total potential energy */
double potential_energy(Body *bodies, int n) {
    double pe = 0.0;
    for (int i = 0; i < n; i++)
        for (int j = i+1; j < n; j++) {
            double dx = bodies[j].x - bodies[i].x;
            double dy = bodies[j].y - bodies[i].y;
            double dz = bodies[j].z - bodies[i].z;
            double dist = sqrt(dx*dx + dy*dy + dz*dz + SOFTENING);
            pe -= G * bodies[i].mass * bodies[j].mass / dist;
        }
    return pe;
}

/* Center of mass */
void center_of_mass(Body *bodies, int n, double *cx, double *cy, double *cz) {
    double total_mass = 0.0;
    *cx = *cy = *cz = 0.0;
    for (int i = 0; i < n; i++) {
        total_mass += bodies[i].mass;
        *cx += bodies[i].mass * bodies[i].x;
        *cy += bodies[i].mass * bodies[i].y;
        *cz += bodies[i].mass * bodies[i].z;
    }
    *cx /= total_mass;
    *cy /= total_mass;
    *cz /= total_mass;
}

/* Angular momentum */
void angular_momentum(Body *bodies, int n, double *Lx, double *Ly, double *Lz) {
    *Lx = *Ly = *Lz = 0.0;
    for (int i = 0; i < n; i++) {
        *Lx += bodies[i].mass * (bodies[i].y * bodies[i].vz - bodies[i].z * bodies[i].vy);
        *Ly += bodies[i].mass * (bodies[i].z * bodies[i].vx - bodies[i].x * bodies[i].vz);
        *Lz += bodies[i].mass * (bodies[i].x * bodies[i].vy - bodies[i].y * bodies[i].vx);
    }
}

/* Initialize solar system (simplified) */
void init_solar_system(Body *bodies, int *n) {
    *n = 5;
    /* Sun */
    bodies[0] = (Body){0,0,0, 0,0,0, 1.989e30};
    /* Mercury */
    bodies[1] = (Body){5.79e10, 0, 0, 0, 47400, 0, 3.285e23};
    /* Venus */
    bodies[2] = (Body){1.082e11, 0, 0, 0, 35020, 0, 4.867e24};
    /* Earth */
    bodies[3] = (Body){1.496e11, 0, 0, 0, 29780, 0, 5.972e24};
    /* Mars */
    bodies[4] = (Body){2.279e11, 0, 0, 0, 24130, 0, 6.390e23};
}

/* Barnes-Hut quadrant check (simplified 2D) */
typedef struct BHNode {
    double cx, cy, size;
    double mass, cmx, cmy;
    int body_idx;
    struct BHNode *children[4];
} BHNode;

BHNode* new_node(double cx, double cy, double size) {
    BHNode *n = calloc(1, sizeof(BHNode));
    n->cx = cx; n->cy = cy; n->size = size;
    n->body_idx = -1;
    return n;
}

void free_tree(BHNode *node) {
    if (!node) return;
    for (int i = 0; i < 4; i++) free_tree(node->children[i]);
    free(node);
}

int main(void) {
    int n;
    Body bodies[MAX_BODIES];
    init_solar_system(bodies, &n);

    printf("Initial energy: KE=%.3e PE=%.3e Total=%.3e\n",
        kinetic_energy(bodies, n),
        potential_energy(bodies, n),
        kinetic_energy(bodies, n) + potential_energy(bodies, n));

    /* Simulate 100 steps */
    for (int step = 0; step < 100; step++)
        step_leapfrog(bodies, n, DT * 86400);   /* DT in days */

    double cx, cy, cz;
    center_of_mass(bodies, n, &cx, &cy, &cz);
    printf("Center of mass after 100 steps: (%.3e, %.3e, %.3e)\n", cx, cy, cz);

    printf("Final energy:   KE=%.3e PE=%.3e Total=%.3e\n",
        kinetic_energy(bodies, n),
        potential_energy(bodies, n),
        kinetic_energy(bodies, n) + potential_energy(bodies, n));

    return 0;
}
