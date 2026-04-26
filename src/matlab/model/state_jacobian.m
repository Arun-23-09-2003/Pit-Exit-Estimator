function F = state_jacobian(x, dt, mode_name, track_length_m, cfg)
%STATE_JACOBIAN Jacobian of nonlinear state transition wrt state x.

if ~isfinite(dt) || dt < cfg.min_dt_s
    dt = cfg.min_dt_s;
end

m = mode_params(cfg, mode_name);
[~, db_ds] = periodic_forcing(x(1), track_length_m, m);

F = eye(3);
F(1, 2) = dt;
F(1, 3) = 0.5 * dt^2;
F(2, 3) = dt;
F(3, 1) = db_ds;
F(3, 3) = m.rho_a;

end

