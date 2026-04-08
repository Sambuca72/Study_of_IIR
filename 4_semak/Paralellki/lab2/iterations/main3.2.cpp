#include <iostream>
#include <vector>
#include <cmath>
#include <omp.h>
#include <chrono>
#include <unistd.h>

#ifndef NUM_THREADS
#define NUM_THREADS 1
#endif

const double TOLERANCE = 1e-6;
const int MAX_ITER = 20000;


void print_vector(const std::vector<double>& v) {
    for (double val : v) {
        std::cout << val << " ";
    }
    std::cout << std::endl;
}

double norm(const std::vector<double>& x_new, const std::vector<double>& x_old) {
    double sum = 0.0;

    #pragma omp parallel num_threads(NUM_THREADS)
    {
        int nthreads = omp_get_num_threads();
        int threadid = omp_get_thread_num();

        int items_per_thread = x_new.size() / nthreads;

        int lb = threadid * items_per_thread;
        int ub = (threadid == nthreads - 1) ? (x_new.size() - 1) : (lb + items_per_thread - 1);

        double local_sum = 0.0;
        for (int i = lb; i <= ub; i++) {
            local_sum += pow(x_new[i] - x_old[i], 2);
        }

        #pragma omp atomic
        sum += local_sum;
    }

    return sqrt(sum);
}


std::vector<double> simple_iteration(const std::vector<std::vector<double>>& A, const std::vector<double>& b, double tau) {
    int n = A.size();
    std::vector<double> x(n, 0.0);
    std::vector<double> x_new(n, 0.0);
    
    for (int iter = 0; iter < MAX_ITER; iter++) {
        #pragma omp parallel num_threads(NUM_THREADS)
        {
            int nthreads = omp_get_num_threads();
            int threadid = omp_get_thread_num();
    
            int items_per_thread = n / nthreads;
    
            int lb = threadid * items_per_thread;
            int ub = (threadid == nthreads - 1) ? (n - 1) : (lb + items_per_thread - 1);
    
            for (int i = lb; i <= ub; i++) {
                double sum = 0.0;
                for (int j = 0; j < n; j++) {
                    sum += A[i][j] * x[j];
                }
                x_new[i] = x[i] - tau * (sum - b[i]);
            }
        }
        
        if (norm(x_new, x) < TOLERANCE) {
            std::cout << "Сошлось за " << iter + 1 << " итераций.\n";
            return x_new;
        }

        x = x_new;
    }
    
    std::cout << "Не сошлось за " << MAX_ITER << " итераций.\n";
    return x_new;
}

int main() {
    int N;
    std::cout << "Введите размерность N: ";
    std::cin >> N;

    
    std::vector<std::vector<double>> A(N, std::vector<double>(N, 1.0));
    for (int i = 0; i < N; i++) {
        A[i][i] = 2.0;
    }

    
    std::vector<double> b(N, N + 1.0);

    
    double tau = 1.0 / 1000.0;

    const auto start{std::chrono::steady_clock::now()};
    std::vector<double> x = simple_iteration(A, b, tau);
    const auto end{std::chrono::steady_clock::now()};
    const std::chrono::duration<double> elapsed_seconds{end - start};

    std::cout << "Your calculations took " <<
                elapsed_seconds.count() <<
                " seconds to run chrono.\n";

    std::cout << "Решение: ";
    print_vector(x);

    return 0;
}