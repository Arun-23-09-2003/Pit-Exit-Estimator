function profile = estimate_input_profile(ds, t_cutoff, cfg)
%ESTIMATE_INPUT_PROFILE Estimate phase-binned mean input profile from history.
% Uses only rows with t <= t_cutoff (causal).

n_bins = cfg.propagation.input_phase_bins;
edges = linspace(0, 1, n_bins + 1);

profile = struct();
profile.n_bins = n_bins;
profile.edges = edges;
profile.mean_u = repmat(cfg.propagation.default_u, n_bins, 1);
profile.global_u = cfg.propagation.default_u;
profile.n_obs = zeros(n_bins, 1);

if isempty(ds.t)
    return;
end

mask = ds.t <= t_cutoff & isfinite(ds.lap_progress) & all(isfinite(ds.u), 2);
if sum(mask) < cfg.propagation.min_history_rows
    return;
end

phi = ds.lap_progress(mask);
u_hist = ds.u(mask, :);
profile.global_u = mean(u_hist, 1, "omitnan");
if any(~isfinite(profile.global_u))
    profile.global_u = cfg.propagation.default_u;
end

for b = 1:n_bins
    if b < n_bins
        in_bin = phi >= edges(b) & phi < edges(b + 1);
    else
        in_bin = phi >= edges(b) & phi <= edges(b + 1);
    end
    profile.n_obs(b) = sum(in_bin);
    if profile.n_obs(b) > 0
        mu = mean(u_hist(in_bin, :), 1, "omitnan");
        if all(isfinite(mu))
            profile.mean_u(b, :) = mu;
        else
            profile.mean_u(b, :) = profile.global_u;
        end
    else
        profile.mean_u(b, :) = profile.global_u;
    end
end

end

