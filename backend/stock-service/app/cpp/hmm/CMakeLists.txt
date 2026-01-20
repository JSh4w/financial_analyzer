cmake_minimum_required(VERSION 3.16)
project(hmm_regime VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build the HMM executable
add_executable(hmm_regime src/hmm.cpp)
