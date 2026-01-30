#include "hmm.h"
#include <iostream>
#include <vector>
#include <random>

int main() {
    std::cout << "=== HMM Test with Synthetic Data ===" << std::endl;

    // Create synthetic data with 3 clear regimes
    std::vector<double> observations;
    std::random_device rd;
    std::mt19937 gen(rd());

    // Bear market: mean = -0.02, small variance (observations 0-32)
    std::normal_distribution<> bear(-0.02, 0.01);
    for (int i = 0; i < 33; i++) {
        observations.push_back(bear(gen));
    }

    // Neutral market: mean = 0.0, small variance (observations 33-65)
    std::normal_distribution<> neutral(0.0, 0.015);
    for (int i = 0; i < 33; i++) {
        observations.push_back(neutral(gen));
    }

    // Bull market: mean = 0.02, small variance (observations 66-99)
    std::normal_distribution<> bull(0.02, 0.01);
    for (int i = 0; i < 34; i++) {
        observations.push_back(bull(gen));
    }

    std::cout << "Generated " << observations.size() << " observations" << std::endl;
    std::cout << "True regimes: Bear (0-32), Neutral (33-65), Bull (66-99)" << std::endl;

    // Create and train HMM
    HMM model;

    std::cout << "\n--- Before Training ---" << std::endl;
    std::cout << "Initial log-likelihood: " << model.log_likelihood(observations) << std::endl;
    std::cout << "Initial means: ";
    auto initial_means = model.means();
    for (int i = 0; i < 3; i++) {
        std::cout << initial_means[i] << " ";
    }
    std::cout << std::endl;

    // Train the model
    std::cout << "\n--- Training ---" << std::endl;
    model.fit(observations, 1000, 0.0);

    std::cout << "\n--- After Training ---" << std::endl;
    std::cout << "Final log-likelihood: " << model.log_likelihood(observations) << std::endl;

    auto trained_means = model.means();
    auto trained_scales = model.scales();

    std::cout << "\nLearned parameters:" << std::endl;
    for (int i = 0; i < 3; i++) {
        std::cout << "State " << i << ": mean = " << trained_means[i]
                  << ", scale = " << trained_scales[i] << std::endl;
    }

    // Decode the most likely state sequence
    std::cout << "\n--- Decoding ---" << std::endl;
    auto states = model.decode(observations);

    // Count states in each segment
    int bear_segment[3] = {0, 0, 0};
    int neutral_segment[3] = {0, 0, 0};
    int bull_segment[3] = {0, 0, 0};

    for (int i = 0; i < 33; i++) bear_segment[states[i]]++;
    for (int i = 33; i < 66; i++) neutral_segment[states[i]]++;
    for (int i = 66; i < 100; i++) bull_segment[states[i]]++;

    std::cout << "Decoded states in Bear segment (0-32): ";
    std::cout << "State0=" << bear_segment[0] << " State1=" << bear_segment[1]
              << " State2=" << bear_segment[2] << std::endl;

    std::cout << "Decoded states in Neutral segment (33-65): ";
    std::cout << "State0=" << neutral_segment[0] << " State1=" << neutral_segment[1]
              << " State2=" << neutral_segment[2] << std::endl;

    std::cout << "Decoded states in Bull segment (66-99): ";
    std::cout << "State0=" << bull_segment[0] << " State1=" << bull_segment[1]
              << " State2=" << bull_segment[2] << std::endl;

    std::cout << "\n=== Test Complete ===" << std::endl;

    return 0;
}
