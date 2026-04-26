function [x_end, n_steps] = propagate_open_loop_with_profile( ...
    x0, t0, t1, profile, flags_ref, track_length_m, cfg)
%PROPAGATE_OPEN_LOOP_WITH_PROFILE Propagate one car with profile-based inputs.

x_end = x0(:);
n_steps = 0;

if ~isfinite(t0) || ~isfinite(t1) || t1 <= t0
    return;
end

dt_ref = cfg.propagation.dt_s;
t = t0;

while t < t1
    dt = min(dt_ref, t1 - t);
    if dt < cfg.min_dt_s
        break;
    end

    u = input_from_phase_profile(profile, x_end(1), track_length_m);
    mode_name = mode_from_inputs(flags_ref, u(3));
    x_end = state_transition(x_end, u', dt, mode_name, track_length_m, cfg);

    t = t + dt;
    n_steps = n_steps + 1;
end

end

