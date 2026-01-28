#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "../src/hmm.h"
#include <cmath>

namespace py = pybind11;

// Helper function to convert numpy array to std::vector
std::vector<double> numpy_to_vector(py::array_t<double> arr) {
    auto buf = arr.request();
    double* ptr = static_cast<double*>(buf.ptr);
    return std::vector<double>(ptr, ptr + buf.size);
}

// Helper function to convert std::vector to numpy array
py::array_t<int> vector_to_numpy(const std::vector<int>& vec) {
    return py::array_t<int>(vec.size(), vec.data());
}

// Helper function to convert std::array to list
template<size_t N>
py::list array_to_list(const std::array<double, N>& arr) {
    py::list result;
    for (const auto& val : arr) {
        result.append(val);
    }
    return result;
}

// Helper function to calculate log returns from prices
std::vector<double> prices_to_returns(const std::vector<double>& prices) {
    if (prices.size() < 2) {
        throw std::runtime_error("Need at least 2 prices to calculate returns");
    }

    std::vector<double> returns;
    returns.reserve(prices.size() - 1);

    for (size_t i = 1; i < prices.size(); i++) {
        if (prices[i-1] <= 0 || prices[i] <= 0) {
            throw std::runtime_error("Prices must be positive");
        }
        returns.push_back(std::log(prices[i] / prices[i-1]));
    }

    return returns;
}

// Wrapper class to add convenience methods
class HMMWrapper : public HMM {
public:
    // Constructor
    HMMWrapper() : HMM() {}

    // Fit from numpy array of returns
    void fit_numpy(py::array_t<double> observations, int max_iterations = 100, double tolerance = 1e-4) {
        auto obs_vec = numpy_to_vector(observations);
        this->fit(obs_vec, max_iterations, tolerance);
    }

    // Fit from numpy array of prices (calculates log returns)
    void fit_from_prices(py::array_t<double> prices, int max_iterations = 100, double tolerance = 1e-4) {
        auto price_vec = numpy_to_vector(prices);
        auto returns = prices_to_returns(price_vec);
        this->fit(returns, max_iterations, tolerance);
    }

    // Decode from numpy array of returns
    py::array_t<int> decode_numpy(py::array_t<double> observations) const {
        auto obs_vec = numpy_to_vector(observations);
        auto states = this->decode(obs_vec);
        return vector_to_numpy(states);
    }

    // Decode from numpy array of prices (calculates log returns)
    py::array_t<int> decode_from_prices(py::array_t<double> prices) const {
        auto price_vec = numpy_to_vector(prices);
        auto returns = prices_to_returns(price_vec);
        auto states = this->decode(returns);
        return vector_to_numpy(states);
    }

    // Log likelihood from numpy array
    double log_likelihood_numpy(py::array_t<double> observations) const {
        auto obs_vec = numpy_to_vector(observations);
        return this->log_likelihood(obs_vec);
    }

    // Get means as Python list
    py::list get_means() const {
        return array_to_list(this->means());
    }

    // Get scales as Python list
    py::list get_scales() const {
        return array_to_list(this->scales());
    }
};

PYBIND11_MODULE(hmm_regime, m) {
    m.doc() = "Hidden Markov Model for financial regime detection with Student-t emissions";

    py::class_<HMMWrapper>(m, "HMM")
        .def(py::init<>(), "Create a new HMM with 3 states (Bear, Neutral, Bull)")

        // Training methods
        .def("fit", &HMMWrapper::fit_numpy,
             py::arg("returns"),
             py::arg("max_iterations") = 100,
             py::arg("tolerance") = 1e-4,
             "Train the HMM on log returns using Baum-Welch algorithm\n\n"
             "Args:\n"
             "    returns: numpy array of log returns\n"
             "    max_iterations: maximum number of EM iterations (default: 100)\n"
             "    tolerance: convergence threshold for log-likelihood (default: 1e-4)")

        .def("fit_from_prices", &HMMWrapper::fit_from_prices,
             py::arg("prices"),
             py::arg("max_iterations") = 100,
             py::arg("tolerance") = 1e-4,
             "Train the HMM on close prices (automatically calculates log returns)\n\n"
             "Args:\n"
             "    prices: numpy array of close prices\n"
             "    max_iterations: maximum number of EM iterations (default: 100)\n"
             "    tolerance: convergence threshold for log-likelihood (default: 1e-4)")

        // Inference methods
        .def("decode", &HMMWrapper::decode_numpy,
             py::arg("returns"),
             "Decode the most likely state sequence using Viterbi algorithm\n\n"
             "Args:\n"
             "    returns: numpy array of log returns\n\n"
             "Returns:\n"
             "    numpy array of state indices (0=Bear, 1=Neutral, 2=Bull)")

        .def("decode_from_prices", &HMMWrapper::decode_from_prices,
             py::arg("prices"),
             "Decode the most likely state sequence from prices\n\n"
             "Args:\n"
             "    prices: numpy array of close prices\n\n"
             "Returns:\n"
             "    numpy array of state indices (0=Bear, 1=Neutral, 2=Bull)")

        .def("log_likelihood", &HMMWrapper::log_likelihood_numpy,
             py::arg("returns"),
             "Calculate the log-likelihood of the observations\n\n"
             "Args:\n"
             "    returns: numpy array of log returns\n\n"
             "Returns:\n"
             "    float: log-likelihood value")

        // Getters
        .def("means", &HMMWrapper::get_means,
             "Get the learned mean returns for each state\n\n"
             "Returns:\n"
             "    list: [bear_mean, neutral_mean, bull_mean]")

        .def("scales", &HMMWrapper::get_scales,
             "Get the learned volatility (scale) for each state\n\n"
             "Returns:\n"
             "    list: [bear_scale, neutral_scale, bull_scale]");

    // Helper function to convert prices to returns (exposed for convenience)
    m.def("prices_to_returns", [](py::array_t<double> prices) {
        auto price_vec = numpy_to_vector(prices);
        auto returns = prices_to_returns(price_vec);
        return py::array_t<double>(returns.size(), returns.data());
    }, py::arg("prices"),
    "Convert close prices to log returns\n\n"
    "Args:\n"
    "    prices: numpy array of close prices\n\n"
    "Returns:\n"
    "    numpy array of log returns");
}
