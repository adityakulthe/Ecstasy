#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_V 1000
#define INF 2147483647

typedef struct Edge { int to, weight, next; } Edge;

int head[MAX_V], edge_cnt;
Edge edges[MAX_V * MAX_V];

void add_edge(int u, int v, int w) {
    edges[edge_cnt] = (Edge){v, w, head[u]};
    head[u] = edge_cnt++;
}

/* BFS */
void bfs(int src, int n, int *dist) {
    int *queue = malloc(n * sizeof(int));
    for (int i = 0; i < n; i++) dist[i] = -1;
    dist[src] = 0;
    int front = 0, back = 0;
    queue[back++] = src;
    while (front < back) {
        int u = queue[front++];
        for (int e = head[u]; e != -1; e = edges[e].next) {
            int v = edges[e].to;
            if (dist[v] == -1) { dist[v] = dist[u] + 1; queue[back++] = v; }
        }
    }
    free(queue);
}

/* DFS (iterative) */
void dfs(int src, int n, int *visited) {
    int *stack = malloc(n * sizeof(int));
    int top = 0;
    stack[top++] = src;
    while (top > 0) {
        int u = stack[--top];
        if (visited[u]) continue;
        visited[u] = 1;
        for (int e = head[u]; e != -1; e = edges[e].next)
            if (!visited[edges[e].to]) stack[top++] = edges[e].to;
    }
    free(stack);
}

/* Dijkstra (naive O(V^2) — no priority queue) */
void dijkstra(int src, int n, int *dist) {
    int *visited = calloc(n, sizeof(int));
    for (int i = 0; i < n; i++) dist[i] = INF;
    dist[src] = 0;

    for (int iter = 0; iter < n; iter++) {
        /* Find min unvisited */
        int u = -1;
        for (int i = 0; i < n; i++)
            if (!visited[i] && (u == -1 || dist[i] < dist[u])) u = i;
        if (u == -1 || dist[u] == INF) break;
        visited[u] = 1;

        for (int e = head[u]; e != -1; e = edges[e].next) {
            int v = edges[e].to, w = edges[e].weight;
            if (dist[u] + w < dist[v]) dist[v] = dist[u] + w;
        }
    }
    free(visited);
}

/* Bellman-Ford (handles negative edges) */
int bellman_ford(int src, int n, int *dist) {
    for (int i = 0; i < n; i++) dist[i] = INF;
    dist[src] = 0;

    for (int i = 0; i < n - 1; i++)
        for (int u = 0; u < n; u++)
            if (dist[u] != INF)
                for (int e = head[u]; e != -1; e = edges[e].next) {
                    int v = edges[e].to, w = edges[e].weight;
                    if (dist[u] + w < dist[v]) dist[v] = dist[u] + w;
                }

    /* Detect negative cycles */
    for (int u = 0; u < n; u++)
        if (dist[u] != INF)
            for (int e = head[u]; e != -1; e = edges[e].next)
                if (dist[u] + edges[e].weight < dist[edges[e].to]) return 0;
    return 1;
}

/* Floyd-Warshall all-pairs shortest path */
void floyd_warshall(int dist[MAX_V][MAX_V], int n) {
    for (int k = 0; k < n; k++)
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                if (dist[i][k] != INF && dist[k][j] != INF)
                    if (dist[i][k] + dist[k][j] < dist[i][j])
                        dist[i][j] = dist[i][k] + dist[k][j];
}

/* Union-Find for Kruskal */
int parent[MAX_V], rank_uf[MAX_V];
int find(int x) { return parent[x] == x ? x : (parent[x] = find(parent[x])); }
void unite(int a, int b) {
    a = find(a); b = find(b);
    if (a == b) return;
    if (rank_uf[a] < rank_uf[b]) { int t=a; a=b; b=t; }
    parent[b] = a;
    if (rank_uf[a] == rank_uf[b]) rank_uf[a]++;
}

typedef struct { int u, v, w; } KEdge;
int cmp_edge(const void *a, const void *b) { return ((KEdge*)a)->w - ((KEdge*)b)->w; }

/* Kruskal's MST */
int kruskal(KEdge *kedges, int m, int n) {
    qsort(kedges, m, sizeof(KEdge), cmp_edge);
    for (int i = 0; i < n; i++) { parent[i] = i; rank_uf[i] = 0; }
    int mst_weight = 0;
    for (int i = 0; i < m; i++) {
        if (find(kedges[i].u) != find(kedges[i].v)) {
            unite(kedges[i].u, kedges[i].v);
            mst_weight += kedges[i].w;
        }
    }
    return mst_weight;
}

/* Topological sort (Kahn's algorithm) */
int topo_sort(int n, int *order) {
    int *in_degree = calloc(n, sizeof(int));
    for (int u = 0; u < n; u++)
        for (int e = head[u]; e != -1; e = edges[e].next)
            in_degree[edges[e].to]++;

    int *queue = malloc(n * sizeof(int));
    int front = 0, back = 0;
    for (int i = 0; i < n; i++) if (in_degree[i] == 0) queue[back++] = i;

    int cnt = 0;
    while (front < back) {
        int u = queue[front++];
        order[cnt++] = u;
        for (int e = head[u]; e != -1; e = edges[e].next) {
            int v = edges[e].to;
            if (--in_degree[v] == 0) queue[back++] = v;
        }
    }
    free(in_degree); free(queue);
    return cnt == n;   /* 1 if DAG, 0 if cycle */
}

int main(void) {
    int n = 6;
    memset(head, -1, sizeof(head));
    edge_cnt = 0;

    add_edge(0, 1, 4); add_edge(0, 2, 3);
    add_edge(1, 3, 2); add_edge(2, 3, 1);
    add_edge(3, 4, 5); add_edge(4, 5, 1);

    int dist[MAX_V];
    dijkstra(0, n, dist);
    printf("Dijkstra from 0: ");
    for (int i = 0; i < n; i++) printf("%d ", dist[i]);
    printf("\n");

    int visited[MAX_V] = {0};
    dfs(0, n, visited);
    printf("DFS visited: ");
    for (int i = 0; i < n; i++) printf("%d ", visited[i]);
    printf("\n");

    return 0;
}
