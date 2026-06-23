#include <boost/program_options.hpp>

#include <chrono>
#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace po = boost::program_options;

struct ProgramOptions {
    int size = 128;
    double epsilon = 1e-6;
    long long max_iterations = 1'000'000;
    std::string output = "result.txt";
    bool print_matrix = false;
    int check_every = 100;
    bool skip_grid_copy = true;
};

struct SolveResult {
    std::vector<double> matrix;
    long long iterations = 0;
    double error = 0.0;
    double seconds = 0.0;
};

double lerp(double left, double right, double t) {
    return left + (right - left) * t;
}

std::vector<double> make_initial_grid(int size) {
    const double top_left = 10.0;
    const double top_right = 20.0;
    const double bottom_right = 30.0;
    const double bottom_left = 20.0;

    std::vector<double> grid(static_cast<std::size_t>(size) * size, 0.0);

    for (int i = 0; i < size; ++i) {
        const double t = static_cast<double>(i) / static_cast<double>(size - 1);
        grid[static_cast<std::size_t>(i) * size] = lerp(top_left, bottom_left, t);
        grid[static_cast<std::size_t>(i) * size + size - 1] = lerp(top_right, bottom_right, t);
    }

    for (int j = 0; j < size; ++j) {
        const double t = static_cast<double>(j) / static_cast<double>(size - 1);
        grid[j] = lerp(top_left, top_right, t);
        grid[static_cast<std::size_t>(size - 1) * size + j] = lerp(bottom_left, bottom_right, t);
    }

    return grid;
}

SolveResult solve_heat_equation(int size,
                                double epsilon,
                                long long max_iterations,
                                int check_every,
                                bool skip_grid_copy) {
    std::vector<double> grid_a = make_initial_grid(size);
    std::vector<double> grid_b = skip_grid_copy ? make_initial_grid(size)
                                                : grid_a;

    double* a = grid_a.data();
    double* b = grid_b.data();
    double* current = a;
    double* next = b;
    const std::size_t cell_count = static_cast<std::size_t>(size) * size;
#if !defined(_OPENACC)
    (void)cell_count;
#endif

    long long iterations = 0;
    double error = 0.0;

    if (check_every < 1) {
        check_every = 1;
    }

    const auto started = std::chrono::steady_clock::now();

#if defined(_OPENACC)
#pragma acc data copy(a[0:cell_count], b[0:cell_count])
#endif
    {
        for (long long iteration = 1; iteration <= max_iterations; ++iteration) {
            const bool check_now = (iteration % check_every == 0)
                                || (iteration == max_iterations);

            if (check_now) {
                error = 0.0;
#if defined(_OPENACC)
#pragma acc parallel loop collapse(2) present(current[0:cell_count], next[0:cell_count]) reduction(max:error) async(1)
#endif
                for (int i = 1; i < size - 1; ++i) {
                    for (int j = 1; j < size - 1; ++j) {
                        const int index = i * size + j;
                        const double new_value = 0.25 * (
                            current[index - size] +
                            current[index + size] +
                            current[index - 1] +
                            current[index + 1]
                        );

                        double difference = new_value - current[index];
                        if (difference < 0.0) {
                            difference = -difference;
                        }
                        if (difference > error) {
                            error = difference;
                        }

                        next[index] = new_value;
                    }
                }
#if defined(_OPENACC)
#pragma acc wait(1)
#endif
            } else {
#if defined(_OPENACC)
#pragma acc parallel loop collapse(2) present(current[0:cell_count], next[0:cell_count]) async(1)
#endif
                for (int i = 1; i < size - 1; ++i) {
                    for (int j = 1; j < size - 1; ++j) {
                        const int index = i * size + j;
                        next[index] = 0.25 * (
                            current[index - size] +
                            current[index + size] +
                            current[index - 1] +
                            current[index + 1]
                        );
                    }
                }
            }

            std::swap(current, next);
            iterations = iteration;

            if (check_now && error < epsilon) {
                break;
            }
        }
#if defined(_OPENACC)
#pragma acc wait(1)
#endif
    }

    const auto finished = std::chrono::steady_clock::now();
    const std::chrono::duration<double> elapsed = finished - started;

    if (current == b) {
        grid_a.swap(grid_b);
    }

    return SolveResult{std::move(grid_a), iterations, error, elapsed.count()};
}

void save_matrix_text(const std::string& path, const std::vector<double>& matrix, int size) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Cannot open output file: " + path);
    }

    out << std::setprecision(12);
    for (int i = 0; i < size; ++i) {
        for (int j = 0; j < size; ++j) {
            if (j != 0) {
                out << ' ';
            }
            out << matrix[static_cast<std::size_t>(i) * size + j];
        }
        out << '\n';
    }
}

void print_matrix(const std::vector<double>& matrix, int size) {
    std::cout << std::fixed << std::setprecision(4);
    for (int i = 0; i < size; ++i) {
        for (int j = 0; j < size; ++j) {
            std::cout << std::setw(10) << matrix[static_cast<std::size_t>(i) * size + j];
        }
        std::cout << '\n';
    }
}

ProgramOptions parse_options(int argc, char** argv) {
    ProgramOptions options;

    po::options_description description("Heat equation options");
    description.add_options()
        ("help,h", "show help")
        ("size,n", po::value<int>(&options.size)->default_value(options.size), "square grid size")
        ("epsilon,e", po::value<double>(&options.epsilon)->default_value(options.epsilon), "target precision")
        ("iterations,i", po::value<long long>(&options.max_iterations)->default_value(options.max_iterations), "maximum iteration count")
        ("output,o", po::value<std::string>(&options.output)->default_value(options.output), "output matrix text file")
        ("print,p", po::bool_switch(&options.print_matrix), "print the resulting matrix")
        ("check-every,k", po::value<int>(&options.check_every)->default_value(options.check_every),
            "check error every K iterations")
        ("skip-grid-copy", po::bool_switch(&options.skip_grid_copy),
            "initialize second buffer separately (no host copy)");

    po::variables_map variables;
    po::store(po::parse_command_line(argc, argv, description), variables);

    if (variables.count("help") != 0) {
        std::cout << description << '\n';
        std::exit(0);
    }

    po::notify(variables);

    if (options.size < 3) {
        throw std::invalid_argument("Grid size must be at least 3.");
    }
    if (options.epsilon <= 0.0) {
        throw std::invalid_argument("Epsilon must be positive.");
    }
    if (options.max_iterations <= 0) {
        throw std::invalid_argument("Maximum iteration count must be positive.");
    }
    if (options.check_every <= 0) {
        throw std::invalid_argument("check-every must be positive.");
    }

    return options;
}

int main(int argc, char** argv) {
    try {
        const ProgramOptions options = parse_options(argc, argv);
        const SolveResult result = solve_heat_equation(
            options.size,
            options.epsilon,
            options.max_iterations,
            options.check_every,
            options.skip_grid_copy
        );

        save_matrix_text(options.output, result.matrix, options.size);

        std::cout << "grid_size: " << options.size << "x" << options.size << '\n';
        std::cout << "iterations: " << result.iterations << '\n';
        std::cout << "error: " << std::setprecision(12) << result.error << '\n';
        std::cout << "time_sec: " << std::fixed << std::setprecision(6) << result.seconds << '\n';
        std::cout << "check_every: " << options.check_every << '\n';
        std::cout << "skip_grid_copy: " << (options.skip_grid_copy ? "true" : "false") << '\n';
        std::cout << "output: " << options.output << '\n';

        if (options.print_matrix || options.size == 10 || options.size == 13) {
            std::cout << "\nresult matrix:\n";
            print_matrix(result.matrix, options.size);
        }

        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }
}
