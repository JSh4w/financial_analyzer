#include "hmm.h"
#include <iostream>
#include <cmath>

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

void HMM::fit(){
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
    double denominator = std::tgamma(nu/2) * std::sqrt(nu * pi) * sigma;
    double base = 1.0 + (z * z) / nu;
    double exponent = -(nu+1)/ 2.0;

    return (numerator/ denominator) * std::pow(base,exponent);
}

std::vector<std::array<double, N>> HMM::forward(const std::vector<double>& obs) const {
    // compute a(t,i) = P(observations[0:t], state[t]=i)
    //observatiions obs len T, 
    //forward[s,1] <- pi_s * b_s(o_a)
    int T = obs.size();
    std::vector<std::array<double, N>> alpha(T);
    // The std array is for each possible state in a column of the trellace
    // THe vector is the lenght of the number of sequences
    
    // Initialisation:
    // init from starting point pi_ P(state = i)
    // , with first observation obs[0]
    for (int i = 0 ; i < N ; ++i ) {
        alpha[0][i] = pi_[i] * emission(obs[0], i)
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
