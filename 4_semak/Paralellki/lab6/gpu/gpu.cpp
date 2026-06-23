#include <iostream>
#include <boost/program_options.hpp>
#include <cmath>
#include <vector>
#include <fstream>
#include <iomanip>
#include <chrono>

namespace opt = boost::program_options;

void save(const double* m, int s, const std::string& fn) {
    std::ofstream f(fn);
    for (int i = 0; i < s; ++i) {
        for (int j = 0; j < s; ++j) f << std::setw(10) << std::fixed << std::setprecision(4) << m[i * s + j];
        f << "\n";
    }
}

int main(int argc, char** argv) {
    int size, max_it; double acc;
    opt::options_description desc("Опции");
    desc.add_options()("accuracy", opt::value<double>(&acc)->default_value(1e-6))
                      ("size", opt::value<int>(&size)->default_value(1024))
                      ("iterations", opt::value<int>(&max_it)->default_value(1000000));
    opt::variables_map vm; opt::store(opt::parse_command_line(argc, argv, desc), vm); opt::notify(vm);

    std::vector<double> m1(size * size, 0.0), m2(size * size, 0.0);
    auto init = [&](std::vector<double>& m) {
        m[0] = 10; m[size - 1] = 20; m[size * size - 1] = 30; m[size * (size - 1)] = 20;
        for (int i = 1; i < size - 1; i++) {
            double t = (double)i / (size - 1);
            m[i] = 10 + t * (20 - 10);
            m[i * size] = 10 + t * (20 - 10);
            m[i * size + size - 1] = 20 + t * (30 - 20);
            m[size * (size - 1) + i] = 20 + t * (30 - 20);
        }
    };
    init(m1); init(m2);

    double *cur = m1.data(), *next = m2.data(), error = 1.0;
    int iter = 0;
    auto start = std::chrono::high_resolution_clock::now();

    #pragma acc data copyin(cur[0:size*size], next[0:size*size]) copy(error)
    {
        while (iter < max_it && error > acc) {
            if ((iter + 1) % 10000 == 0) {
                error = 0.0;
                #pragma acc update device(error)
                #pragma acc parallel loop collapse(2) present(cur, next) reduction(max:error) async(1)
                for (int i = 1; i < size - 1; i++) {
                    for (int j = 1; j < size - 1; j++) {
                        next[i * size + j] = 0.25 * (cur[(i - 1) * size + j] + cur[(i + 1) * size + j] + cur[i * size + j - 1] + cur[i * size + j + 1]);
                        error = fmax(error, fabs(next[i * size + j] - cur[i * size + j]));
                    }
                }
                #pragma acc update self(error) wait(1)
            } else {
                #pragma acc parallel loop collapse(2) present(cur, next) async(1)
                for (int i = 1; i < size - 1; i++) {
                    for (int j = 1; j < size - 1; j++) {
                        next[i * size + j] = 0.25 * (cur[(i - 1) * size + j] + cur[(i + 1) * size + j] + cur[i * size + j - 1] + cur[i * size + j + 1]);
                    }
                }
            }
            std::swap(cur, next);
            iter++;
        }
        #pragma acc wait(1)
        #pragma acc update self(cur[0:size*size])
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::cout << "Time: " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() << " ms, Error: " << error << ", Iterations: " << iter << "\n";

    if (size == 13 || size == 10) {
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) std::cout << std::fixed << std::setprecision(4) << cur[i * size + j] << " ";
            std::cout << "\n";
        }
    }
    save(cur, size, "matrix.txt");
    return 0;
}