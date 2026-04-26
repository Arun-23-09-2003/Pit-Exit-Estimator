function result = run_batch_lumve(driver_series, session_metadata, cfg)
%RUN_BATCH_LUMVE Windowed weighted least-variance unbiased estimate.
% This implementation estimates x_k = [s_k; v_k; a_k] from trailing-window
% linear observation equations plus a model-based prior from k-1.

result = struct();
result.filter_name = "BatchLUMVE";
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

    [x_prev, P_prev] = initial_state_from_series(ds, cfg);

    x_hat = nan(n, 3);
    p_diag = nan(n, 3);
    mode_name = strings(n, 1);
    left_idx = 1;

    for k = 1:n
        tk = ds.t(k);
        t_min = tk - cfg.lumve.window_s;
        while left_idx < k && ds.t(left_idx) < t_min
            left_idx = left_idx + 1;
        end
        idx = left_idx:k;

        A = [];
        b = [];
        w = [];

        for j = idx(:)'
            tau = ds.t(j) - tk;

            if ds.avail(j, 1) && isfinite(ds.z(j, 1))
                A = [A; 1.0, tau, 0.5 * tau^2]; %#ok<AGROW>
                b = [b; ds.z(j, 1)]; %#ok<AGROW>
                w = [w; 1.0 / max(cfg.R_diag(1), cfg.epsilon)]; %#ok<AGROW>
            end

            if ds.avail(j, 2) && isfinite(ds.z(j, 2))
                A = [A; 0.0, 1.0, tau]; %#ok<AGROW>
                b = [b; ds.z(j, 2)]; %#ok<AGROW>
                w = [w; 1.0 / max(cfg.R_diag(2), cfg.epsilon)]; %#ok<AGROW>
            end

            if ds.avail(j, 3) && isfinite(ds.z(j, 3))
                A = [A; 0.0, 0.0, 1.0]; %#ok<AGROW>
                b = [b; ds.z(j, 3)]; %#ok<AGROW>
                w = [w; 1.0 / max(cfg.R_diag(3), cfg.epsilon)]; %#ok<AGROW>
            end
        end

        mode_k = mode_from_inputs(ds.flags(max(k - 1, 1), :), ds.u(max(k - 1, 1), 3));
        mode_name(k) = mode_k;

        % Add dynamic prior from previous step to keep estimates stable.
        if k == 1
            x_prior = x_prev;
        else
            dt = ds.t(k) - ds.t(k - 1);
            if ~isfinite(dt) || dt < cfg.min_dt_s
                dt = cfg.min_dt_s;
            end
            x_prior = state_transition(x_prev, ds.u(k - 1, :)', dt, mode_k, track_length_m, cfg);
        end

        A = [A; eye(3)]; %#ok<AGROW>
        b = [b; x_prior]; %#ok<AGROW>
        prior_var = cfg.lumve.prior_std(:).^2;
        w = [w; 1.0 ./ max(prior_var, cfg.epsilon)]; %#ok<AGROW>

        if size(A, 1) < cfg.lumve.min_rows
            x_curr = x_prior;
            P_curr = P_prev;
        else
            W = diag(w);
            M = A' * W * A + cfg.lumve.ridge * eye(3);
            rhs = A' * W * b;
            x_curr = M \ rhs;
            P_curr = pinv(M);
            P_curr = (P_curr + P_curr') * 0.5 + cfg.covariance_jitter * eye(3);
        end

        x_hat(k, :) = x_curr';
        p_diag(k, :) = diag(P_curr)';

        x_prev = x_curr;
        P_prev = P_curr;
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
