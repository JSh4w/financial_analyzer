#include "hmm.h"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <numeric>

// Maths notation source:
// https://web.stanford.edu/~jurafsky/slp3/A.pdf
// EM for gaussian https://stephens999.github.io/fiveMinuteStats/intro_to_em.html
// EM for Student-t https://people.smp.uq.edu.au/GeoffMcLachlan/pm_sc00.pdf

// Constructor
HMM::HMM() {
    // initial probabilities or being in each state
    for (int i=0; i < N; ++i) {
        pi_[i] = 1.0 / N;
    }
    // Transition Matrix (uniform)
    for (int i=0; i < N; ++i) {
        for (int j=0; j < N; ++j) {
            A_[i][j] = 1.0 / N;
        }
    }
    // Emission paramters for 3 regimes
    // Bear (negative), Neutral (flat), Bull (positive)
    mu_ = {-0.02, 0.0, 0.02}; // means of each regime
    sigma_ = {0.03, 0.03, 0.03}; // volatility 
    nu_ = {5.0, 5.0, 5.0}; // degrees of freedom, currently fixed
}


double HMM::emission(double x, int state) const{
    // PDF formula is
    // f(t) = gamma((v+1)/2) / (sqrt(pi*v) * gamma(v/2)) * B
    // where  B = (1 + (t^2)/v) ^ (-(v+1)/2)
    // gamma is the gamma function
    // v = nu = degrees of freedom
    // note t is the general/scaled form
    // for an observation x = -log(price[t] / price[t-1]),
    // we need the transformed variable to mean mu_ and sigma_
    // we must account for the Jacobian of the transformation
    // generalised formula becomes f(x | mu, sigma, nu) = (1/sigma) *
    // f_standard((x-mu)/sigma | nu)


    double mu = mu_[state];
    double sigma = sigma_[state];
    double nu = nu_[state];

    // student-t PDF formula
    double z = ( x - mu) / sigma;
    double numerator = std::tgamma((nu+1)/ 2.0);
    double denominator = std::tgamma(nu/2.0) * std::sqrt(nu * M_PI) * sigma;
    double base = 1.0 + (z * z) / nu;
    double exponent = -(nu+1)/ 2.0;

    return (numerator/ denominator) * std::pow(base,exponent);
}

std::vector<std::array<double, HMM::N>> HMM::forward(
    const std::vector<double>& obs
) const {
    // compute a(t,i) = P(observations[0:t], state[t]=i)
    //observatiions obs len T, 
    //forward[s,1] <- pi_s * b_s(o_a)
    size_t T = obs.size();
    std::vector<std::array<double, N>> alpha(T);
    // The std array is for each possible state in a column of the trellace
    // THe vector is the lenght of the number of sequences
    
    // Initialisation:
    // init from starting point pi_ P(state = i)
    // , with first observation obs[0]
    for (int i = 0 ; i < N ; ++i ) {
        alpha[0][i] = pi_[i] * emission(obs[0], i);
    }

    // Recursion:
    // a_t(j) = Sum(i=1,N) a_t-1(i) A_ij b_j(o_t)
    /* 
    - where a is the probability of being in state j after seeing the
    first t observations
    - A_ij is the transition probability of state q_i to q_j
    - b_j(o_t) is the state observation likelihood of observation 
    symbol o_t given current state j. (emission(obs[t], j)
    */ 
    for (size_t t = 1; t < T; t++){
        for (int j = 0; j < N; j++){
            double sum = 0.0;
            for (int i =0; i < N; i++){
                sum += alpha[t-1][i] * A_[i][j];
            }
            alpha[t][j] = sum * emission(obs[t],j);
        } 
    }
    return alpha;
} 

double HMM::log_likelihood(
    const std::vector<double>& observations
) const {
    // Termination of forward algorithm
    // Get forward probabilities
    auto alpha = forward(observations);
    int T = observations.size();

    // Sum the final forward probabilities across all states
    double sum = std::accumulate(alpha[T-1].begin(), alpha[T-1].end(), 0.0);

    // Return log of the sum
    return std::log(sum);
}



std::vector<int> HMM::decode(const std::vector<double>& observations ) const {
    // The Viterbi Algorithm
    // Given an HMM lambda = (A,B) and a sequence of observations
    // O, find the most probable sequence of states Q
    // Searching each possible state sequence and maximising 
    // is exponential. Instead use Viterbi
    
    // First starts similar to forward algorithm
    // Except we use the maximum probability to reach each state
    // rather than the sum
    // This means we observe the most probable path to each state
    // v_t(j) = max  P(q_1, q_t-1, o1, o2, ... ot,qt = j | lambda)
    int T = observations.size();
    std::vector<std::array<double,N>> v(T);
    std::vector<std::array<int,N>> backtrace(T);
    // initialisation
    for (int i = 0 ; i < N ; ++i ) {
        v[0][i] = pi_[i] * emission(observations[0], i);
    }
    // recursion
    double tmp;
    for (int t = 1; t < T; t++) {
        for (int j = 0; j < N; j++) {
            v[t][j] = 0 ;
            backtrace[t][j] = 0;
            for (int i = 0; i < N; i++) {
                tmp = v[t-1][i] * A_[i][j] * emission(observations[t], j);
                if (tmp > v[t][j]) {
                    v[t][j] = tmp;
                    backtrace[t][j] = i;
                }
            }
        }
    }
    // Termination; best final state
    int best_final_state = 0;
    double max_prob = v[T-1][0];
    for (int i = 1; i < N; i++) {
        if (v[T-1][i] > max_prob) {
            max_prob = v[T-1][i];
            best_final_state = i;
        }
    }
    
    // Backtrace to reconstruct and provide the best path
    std::vector<int> path(T);
    path[T-1] = best_final_state;
    for (int t = T-2; t >= 0; t--) {
        path[t] = backtrace[t+1][path[t+1]];
    }
    return path;
}

std::vector<std::array<double, HMM::N>> HMM::backward(
    const std::vector<double>& obs
) const {
    // Probability of seeing observations from time t+1 to the end
    // given we are in state i at time t (and given automation lambda)
    // beta = P(o_t+1,....o_T | q_t = i, lambda)
    int T = obs.size();
    std::vector<std::array<double, N>> beta(T);
    // init
    for (int i = 0; i < N; i++) {
        beta[T-1][i] = 1;
    }
    // recursion
    double temp;
    for (int t = T-2; t >=0; t-- ) {
        for (int i = 0; i < N; i++) {
            temp = 0;
            for (int j = 0; j < N; j++) {
                temp += A_[i][j] * emission(obs[t+1],j) * beta[t+1][j];
            }
            beta[t][i] = temp;
        }
    }
    return beta;
}

void HMM::fit(const std::vector<double>& obs, int max_iterations, double tolerance) {
    // Baum-Welch algorithm (EM algorithm)
    // We need to train our transition matrix probabilities A_
    // and observation probability function b / emission parameters

    int T = obs.size();

    // Starting with A_
    // a_ij = E(no transitions state i to j) / E(no transitions from state i)
    // numerator = sum of epsilon = sum(1 to T-1) of P(q_t = i , q_t+1 = j | O, lambda)
    // denominator  = sum of (sum of epsilon over all j)  (use inspection)

    // epsilon = P(q_t = i , q_t+1 = j | O, lambda)
    // = P(q_t = i , q_t+1 = j ,O | lambda) / P(O| lambda) by bayes
    // using forward and backwards

    //init necessary data
    std::array<std::array<double, N>, N> A_hat;
    double num = 0.0;
    double epsilom = 0.0;
    double epsilom_sum = 0.0;
    double numerator = 0.0;
    double denominator = 0.0;
    double prev_log_likelihood = log_likelihood(obs);

    for (int d = 0; d < max_iterations; d++) {
        auto alpha = forward(obs);
        auto beta = backward(obs);


        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                // for each transition point
                numerator = 0.0;
                denominator = 0.0;
                for (int t=0; t < T-1; t++) {
                    epsilom_sum = 0.0;
                    for (int sj = 0; sj < N; sj++){
                        num = alpha[t][i] * A_[i][sj] * emission(obs[t+1],sj) * beta[t+1][sj];
                        if (sj == j) {
                            epsilom = num;
                        }
                        epsilom_sum += num;
                    }
                    numerator +=  epsilom;
                    denominator += epsilom_sum;
                }
                A_hat[i][j] = numerator / denominator;
            }
        }
        // update based on current iteration
        A_ = A_hat;

        // Estimate the emission / observation probability
        // Probability of given symbol v_k from observation vocab V
        // given state j.
        // b_j(v_k) = E(no times in state j and observing symbol v_k) / E(no times in state j)
        std::vector<std::array<double,N>> gamma(T);
        for (int t = 0; t < T; t++) {
            double sum = 0.0;
            for (int j = 0; j < N; j++) {
                gamma[t][j] = alpha[t][j] * beta[t][j];
                sum += gamma[t][j];
            }
            for (int j = 0; j < N; j++) {
                gamma[t][j] /= sum;
            }
        }
        
        //maxmisation of emission variables. We keep tails fixed for now
        for (int i = 0; i < N; i++) {
            double gamma_sum = 0.0;
            double weighted_obs_sum = 0.0;

            // update mean
            for (int t=0; t < T; t++) {
                weighted_obs_sum += gamma[t][i] * obs[t];
                gamma_sum += gamma[t][i];
            }
            mu_[i] = weighted_obs_sum / gamma_sum;

            // update scale 
            double weighted_sq_sum = 0.0;
            for (int t=0; t < T; t++) {
                double diff = obs[t] - mu_[i];
                weighted_sq_sum += gamma[t][i] * diff * diff;
            }
            sigma_[i] = std::sqrt(weighted_sq_sum/ gamma_sum);
        }
        // nu_[i] is fixed for now



        // Check convergence
        double current_log_likelihood = log_likelihood(obs);
        if (std::abs(current_log_likelihood - prev_log_likelihood) < tolerance) {
            break;  // Converged
        }
        prev_log_likelihood = current_log_likelihood;
    }
}

