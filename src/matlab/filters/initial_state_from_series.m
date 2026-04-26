function [x0, P0] = initial_state_from_series(ds, cfg)
%INITIAL_STATE_FROM_SERIES Build initial state/covariance from first valid row.

x0 = [0.0; 0.0; 0.0];
for i = 1:3
    if ds.avail(1, i) && isfinite(ds.z(1, i))
        x0(i) = ds.z(1, i);
    end
end

P0 = diag(cfg.P0_diag);

end

