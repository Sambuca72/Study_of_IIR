#define _USE_MATH_DEFINES
#include <iostream>
#include <vector>
#include <cmath>

#ifndef USE_DOUBLE
#define USE_FLOAT
#endif

#ifdef USE_DOUBLE
using real_t = double;
#else
using real_t = float;
#endif

const size_t N = 10000000;

int main()
{
    std::vector<real_t> data(N);
    real_t sum = 0;

    for (size_t i = 0; i < N; ++i)
    {
        data[i] = std::sin(2.0 * M_PI * i / N);
        sum = sum + data[i];
    }

    std::cout << "Sum: " << sum << std::endl;

    return 0;
}
