function result = run_ukf(driver_series, session_metadata, cfg)
%RUN_UKF Unscented Kalman Filter per driver.

result = struct();
result.filter_name = "UKF";
if isempty(driver_series)
    result.drivers = struct([]);
else
    template = local_empty_driver_result(driver_series(1));
    result.drivers = repmat(template, numel(driver_series), 1);
end

track_length_m = double(session_metadata.track_length_m);
if ~isfinite(track_length_m)
    track_length_m = 1.0;
end

for i = 1:numel(driver_series)
    ds = driver_series(i);
    n = numel(ds.t);
    if n == 0
        result.drivers(i) = local_empty_driver_result(ds);
        continue;
    end

    [x, P] = initial_state_from_series(ds, cfg);

    x_hat = nan(n, 3);
    p_diag = nan(n, 3);
    mode_name = strings(n, 1);

    x_hat(1, :) = x';
    p_diag(1, :) = diag(P)';
    mode_name(1) = mode_from_inputs(ds.flags(1, :), ds.u(1, 3));

    for k = 2:n
        dt = ds.t(k) - ds.t(k - 1);
        if ~isfinite(dt) || dt < cfg.min_dt_s
            dt = cfg.min_dt_s;
        end

        current_mode = mode_from_inputs(ds.flags(k - 1, :), ds.u(k - 1, 3));
        m = mode_params(cfg, current_mode);
        Q = diag(m.q_diag);

        [X, Wm, Wc] = ukf_sigma_points(x, P, cfg);
        n_sigma = size(X, 2);

        X_pred = zeros(3, n_sigma);
        for s = 1:n_sigma
            X_pred(:, s) = state_transition(X(:, s), ds.u(k - 1, :)', dt, current_mode, track_length_m, cfg);
        end

        x_pred = zeros(3, 1);
        for s = 1:n_sigma
            x_pred = x_pred + Wm(s) * X_pred(:, s);
        end

        P_pred = zeros(3, 3);
        for s = 1:n_sigma
            dx = X_pred(:, s) - x_pred;
            P_pred = P_pred + Wc(s) * (dx * dx');
        end
        P_pred = P_pred + Q;
        P_pred = (P_pred + P_pred') * 0.5 + cfg.covariance_jitter * eye(3);

        avail = logical(ds.avail(k, :));
        if any(avail)
            Z_pred = X_pred(avail, :);

            z_mean = zeros(sum(avail), 1);
            for s = 1:n_sigma
                z_mean = z_mean + Wm(s) * Z_pred(:, s);
            end

            S = zeros(sum(avail), sum(avail));
            Pxz = zeros(3, sum(avail));
            for s = 1:n_sigma
                dz = Z_pred(:, s) - z_mean;
                dx = X_pred(:, s) - x_pred;
                S = S + Wc(s) * (dz * dz');
                Pxz = Pxz + Wc(s) * (dx * dz');
            end

            R = diag(cfg.R_diag(avail));
            S = S + R;
            S = (S + S') * 0.5 + cfg.covariance_jitter * eye(size(S));

            K = Pxz / S;
            z = ds.z(k, avail)';
            x = x_pred + K * (z - z_mean);
            P = P_pred - K * S * K';
            P = (P + P') * 0.5 + cfg.covariance_jitter * eye(3);
        else
            x = x_pred;
            P = P_pred;
        end

        x_hat(k, :) = x';
        p_diag(k, :) = diag(P)';
        mode_name(k) = current_mode;
    end

    result.drivers(i) = struct( ...
        "driver_number", ds.driver_number, ...
        "car_index", ds.car_index, ...
        "t", ds.t, ...
        "x_hat", x_hat, ...
        "p_diag", p_diag, ...
        "mode_name", mode_name);
end

end

function out = local_empty_driver_result(ds)
out = struct( ...
    "driver_number", ds.driver_number, ...
    "car_index", ds.car_index, ...
    "t", ds.t, ...
    "x_hat", zeros(0, 3), ...
    "p_diag", zeros(0, 3), ...
    "mode_name", strings(0, 1));
end
