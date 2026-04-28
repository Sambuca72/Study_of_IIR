#include <vector>
#include <iostream>
#include <cmath>
#include <chrono>
#include <thread>
#include <barrier>
#include <atomic>

int N_VAL = 40000;

void parallel_initialize(std::vector<double> &A, std::vector<double> &b, int n, int threads)
{
    std::vector<std::jthread> workers; // контейнер для потоков
    for(int t = 0; t < threads; t++)
    {
        workers.emplace_back([&, t]()
        {
            int chunk = n / threads; // делим строки матрицы между потоками
            int lb = t * chunk;
            int ub = (t == threads - 1) ? n : lb + chunk;
            
            for (int i = lb; i < ub; i++)
            {
                for (int j = 0; j < n; j++)
                {
                    A[i * n + j] = static_cast<double>(i + j); // запись в разные строки A
                }
                b[i] = static_cast<double>(i); // параллельно запись в вектор b 
            }
        });
    }
}

void multiply_matrix_vector(const std::vector<double> &A, const std::vector<double> &b, std::vector<double> &c, int n, int threads)
{
    std::vector<std::jthread> workers; 
    for(int t = 0; t < threads; t++)
    {
        workers.emplace_back([&, t]()
        {
            int chunk = n / threads; 
            int lb = t * chunk;
            int ub = (t == threads - 1) ? n : lb + chunk;

            for (int i = lb; i < ub; i++)
            {
                double sum = 0.0;
                for (int j = 0; j < n; j++)
                {
                    sum += A[i * n + j] * b[j]; 
                }
                c[i] = sum;
            }
        });
    }
}

int main()
{
    int iter = 5; 
    std::vector<int> threads_num = {1, 2, 4, 7, 8, 16, 20, 40};

    std::cout << "Allocating memory for N = " << N_VAL << "..." << std::endl;
    std::vector<double> A(static_cast<size_t>(N_VAL) * N_VAL);
    std::vector<double> b(N_VAL);
    std::vector<double> c(N_VAL);
    std::cout << "Memory allocated." << std::endl;

    double time_t1 = 1.0;

    for(const int threads : threads_num)
    {
        std::cout << "\nRunning with " << threads << " threads..." << std::endl;
        std::vector<double> measurements;

        for(int i = 0; i < iter; i++)
        {
            parallel_initialize(A, b, N_VAL, threads);

            const auto start = std::chrono::steady_clock::now();
            multiply_matrix_vector(A, b, c, N_VAL, threads);
            const auto end = std::chrono::steady_clock::now();
            
            const std::chrono::duration<double> dur = end - start;
            measurements.push_back(dur.count());
            std::cout << "  Iter " << i + 1 << ": " << dur.count() << " s" << std::endl;
        }

        double avg_time = 0;
        for(double t : measurements) avg_time += t;
        avg_time /= iter;

        if (threads == 1) time_t1 = avg_time;
        double speedup = time_t1 / avg_time;

        std::cout << "Average time: " << avg_time << "s" << std::endl;
        std::cout << "Speedup (S" << threads << "): " << speedup << std::endl;
    }
    return 0;
}