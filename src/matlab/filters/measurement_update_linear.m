function [x_upd, P_upd] = measurement_update_linear(x_pred, P_pred, z_row, avail_row, cfg)
%MEASUREMENT_UPDATE_LINEAR Linear measurement update with partial availability.

[z_pred, H_full] = measurement_model(x_pred);
avail = logical(avail_row(:));

if ~any(avail)
    x_upd = x_pred;
    P_upd = P_pred;
    return;
end

z = z_row(:);
H = H_full(avail, :);
innov = z(avail) - z_pred(avail);
R = diag(cfg.R_diag(avail));

S = H * P_pred * H' + R;
S = (S + S') * 0.5 + cfg.covariance_jitter * eye(size(S));
K = (P_pred * H') / S;

x_upd = x_pred + K * innov;
I = eye(size(P_pred));
P_upd = (I - K * H) * P_pred * (I - K * H)' + K * R * K';
P_upd = (P_upd + P_upd') * 0.5 + cfg.covariance_jitter * eye(size(P_upd));

end

