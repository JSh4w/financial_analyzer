#pragma once 

#include <vector>
#include <array>
#include <string>
#include <cmath>
#include <numbers>

/**
    Hidden Markov Model with Student-t emissions for regime detection on returns
*/
class HMM {
public:
    // No Parameter as fixed type
    HMM();

    // Training, to adjust parameter values using Baum-Welch (EM algorithm)
    void fit(const std::vector<double>& observations, int max_iterations = 100, double tolerance = 1e-4);

    // Inference
    std::vector<int> decode(const std::vector<double>& observations ) const;
    double log_likelihood(const std::vector<double>& observations ) const;

    // Getters
    const auto& means() const { return mu_; }
    const auto& scales() const { return sigma_; }
    const auto& transitions() const { return A_; }

    // Persistance
    // save function for post trained parameters
    void save(const std::string& path) const; // method wwont modify any class members
    // load function of trained parameters
    void load(const std::string& path);

private:
    // Internal state
    // number of states - we are fixing this for the class
    // since its a custom HMM not general
    static constexpr int N = 3;
    // State probabilities init
    // used once i.e pi_ -> A[t0]pi_ ...
    std::array<double , N> pi_;
    // State Transition Matrix
    std::array<std::array<double, N>,N> A_;
    // Emission paramters 
    // mean, variance and degrees of freedom (might be fixed)
    std::array<double, N> mu_, sigma_, nu_;

    // Inference helpers, 
    // Feeding observations of log returns = std::log(prices[t]/ prices[t-1])
    // returns are scale invariant 
    std::vector<std::array<double, N>> forward(const std::vector<double>& obs) const;
    std::vector<std::array<double, N>> backward(const std::vector<double>& obs) const;
    double emission(double x, int state) const;


    // we also need pi 
    double pi = std::numbers::pi;

};