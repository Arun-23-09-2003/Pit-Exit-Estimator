function [X, Wm, Wc] = ukf_sigma_points(x, P, cfg)
%UKF_SIGMA_POINTS Compute sigma points and UKF weights.

n = numel(x);
alpha = cfg.ukf.alpha;
beta = cfg.ukf.beta;
kappa = cfg.ukf.kappa;

lambda = alpha^2 * (n + kappa) - n;
gamma = sqrt(n + lambda);

P = (P + P') * 0.5 + cfg.covariance_jitter * eye(n);
[S, p] = chol(P, "lower");
if p ~= 0
    S = chol(P + 1e-6 * eye(n), "lower");
end

X = zeros(n, 2 * n + 1);
X(:, 1) = x;
for i = 1:n
    offset = gamma * S(:, i);
    X(:, i + 1) = x + offset;
    X(:, i + 1 + n) = x - offset;
end

Wm = zeros(1, 2 * n + 1);
Wc = zeros(1, 2 * n + 1);
Wm(1) = lambda / (n + lambda);
Wc(1) = Wm(1) + (1 - alpha^2 + beta);
for i = 2:(2 * n + 1)
    Wm(i) = 1 / (2 * (n + lambda));
    Wc(i) = Wm(i);
end

end

