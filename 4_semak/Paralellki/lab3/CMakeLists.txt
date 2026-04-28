cmake_minimum_required(VERSION 3.15)

project(laba)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)

add_executable(a)
add_executable(b)

target_sources(a PRIVATE task1/a.cpp)

target_sources(b PRIVATE task2/main.cpp)

target_link_libraries(a PRIVATE Threads::Threads)
target_link_libraries(b PRIVATE Threads::Threads)