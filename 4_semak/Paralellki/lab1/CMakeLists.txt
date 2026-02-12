cmake_minimum_required(VERSION 3.10)

project(SinArray)

set(CMAKE_CXX_STANDARD 17)

option(USE_DOUBLE OFF)

if(USE_DOUBLE)
    add_definitions(-DUSE_DOUBLE)
else()
    add_definitions(-DUSE_FLOAT)
endif()

add_executable(sin task1.cpp)