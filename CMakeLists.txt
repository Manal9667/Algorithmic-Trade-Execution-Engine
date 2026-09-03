# CMakeLists.txt - Build configuration for Execution Optimizer
# Phase 6: Complete with benchmarking

cmake_minimum_required(VERSION 3.15)
project(executor)

# C++ standard: use C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ============================================================================
# FIND PYTHON (required for bindings)
# ============================================================================

find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# ============================================================================
# FIND PYBIND11 (required for bindings)
# ============================================================================

find_package(pybind11 CONFIG REQUIRED)

# ============================================================================
# MAIN LIBRARY
# ============================================================================

# Create library with all source files
add_library(executor_lib
    src/book.cpp
    src/engine.cpp
    src/market_data.cpp
    src/simulator.cpp
    src/algorithms.cpp
)

# Compiler options
if(MSVC)
    target_compile_options(executor_lib PRIVATE /W4 /O2)
else()
    target_compile_options(executor_lib PRIVATE -Wall -Wextra -O2)
endif()

# Include directories
target_include_directories(executor_lib PUBLIC include)

# ============================================================================
# PYTHON MODULE
# ============================================================================

# Create Python module using pybind11
pybind11_add_module(executor src/py_bindings.cpp)

# Link against our library
target_link_libraries(executor PRIVATE executor_lib)

# ============================================================================
# TESTS
# ============================================================================

enable_testing()

# Test: Order Book
add_executable(test_book tests/test_book.cpp)
target_link_libraries(test_book executor_lib)
add_test(NAME test_book COMMAND test_book)

# Test: Matching Engine
add_executable(test_engine tests/test_engine.cpp)
target_link_libraries(test_engine executor_lib)
add_test(NAME test_engine COMMAND test_engine)

# Test: Market Simulator
add_executable(test_simulator tests/test_simulator.cpp)
target_link_libraries(test_simulator executor_lib)
add_test(NAME test_simulator COMMAND test_simulator)

# Test: Algorithms
add_executable(test_algorithms tests/test_algorithms.cpp)
target_link_libraries(test_algorithms executor_lib)
add_test(NAME test_algorithms COMMAND test_algorithms)

# Test: Integration (Phase 6)
add_executable(test_integrate tests/test_integrate.cpp)
target_link_libraries(test_integrate executor_lib)
add_test(NAME test_integrate COMMAND test_integrate)

# ============================================================================
# BENCHMARKS (Phase 6)
# ============================================================================

add_executable(benchmark benchmarks/benchmark.cpp)
target_link_libraries(benchmark executor_lib)

# Optional: Add benchmark as a test
# add_test(NAME benchmark COMMAND benchmark)

# ============================================================================
# EXAMPLES
# ============================================================================

add_executable(demo example/demo.cpp)
target_link_libraries(demo executor_lib)

# ============================================================================
# SUMMARY
# ============================================================================

message(STATUS "")
message(STATUS "====================================================")
message(STATUS "  Execution Optimizer - Build Configuration")
message(STATUS "====================================================")
message(STATUS "C++ Standard: C++17")
message(STATUS "Python: ${Python3_VERSION}")
message(STATUS "pybind11: ${pybind11_VERSION}")
message(STATUS "")
message(STATUS "Targets:")
message(STATUS "  executor_lib    - C++ core library")
message(STATUS "  executor        - Python module")
message(STATUS "  test_*          - Unit tests (5 suites, 40+ tests)")
message(STATUS "  benchmark       - Performance benchmarks")
message(STATUS "  demo            - Example usage")
message(STATUS "")
message(STATUS "Build with:")
message(STATUS "  cmake --build . --config Release")
message(STATUS "")
message(STATUS "Run tests:")
message(STATUS "  ctest --output-on-failure")
message(STATUS "")
message(STATUS "Run benchmarks:")
message(STATUS "  ./Release/benchmark")
message(STATUS "")
message(STATUS "====================================================")