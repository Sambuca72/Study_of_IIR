#include <iostream>
#include <vector>
#include <cmath>
#include <omp.h>
#include <chrono>
#include <unistd.h>

#ifndef NUM_THREADS
#define NUM_THREADS 80
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
    
    #pragma omp parallel for schedule(guided, 20) reduction(+:sum) num_threads(NUM_THREADS)
    for (size_t i = 0; i < x_new.size(); i++) {
        sum += pow(x_new[i] - x_old[i], 2);
    }

    return sqrt(sum);
}


std::vector<double> simple_iteration(const std::vector<std::vector<double>>& A, const std::vector<double>& b, double tau) {
    int n = A.size();
    std::vector<double> x(n, 0.0);
    std::vector<double> x_new(n, 0.0);
    
    for (int iter = 0; iter < MAX_ITER; iter++) {
        #pragma omp parallel for schedule(guided, 20) num_threads(NUM_THREADS)
        for (int i = 0; i < n; i++) {
            double sum = 0.0;
            for (int j = 0; j < n; j++) {
                sum += A[i][j] * x[j];
            }
            x_new[i] = x[i] - tau * (sum - b[i]);
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
