cmake_minimum_required(VERSION 3.24)
project(content_diff_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_native python/bindings.cpp src/diff_engine.cpp)
target_include_directories(_native PRIVATE include)
