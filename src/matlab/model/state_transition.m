function x_next = state_transition(x, u, dt, mode_name, track_length_m, cfg)
%STATE_TRANSITION Nonlinear state transition model.
% x = [s; v; a], u = [throttle; brake; drs].

if ~isfinite(dt) || dt < cfg.min_dt_s
    dt = cfg.min_dt_s;
end

m = mode_params(cfg, mode_name);
[b_phi, ~] = periodic_forcing(x(1), track_length_m, m);

s_next = x(1) + x(2) * dt + 0.5 * x(3) * dt^2;
v_next = x(2) + x(3) * dt;
a_next = m.rho_a * x(3) + m.g_th * u(1) - m.g_br * u(2) + m.g_drs * u(3) + b_phi;

x_next = [s_next; v_next; a_next];

end

