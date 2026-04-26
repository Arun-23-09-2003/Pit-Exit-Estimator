function u = input_from_phase_profile(profile, s, track_length_m)
%INPUT_FROM_PHASE_PROFILE Lookup estimated inputs by current lap phase.

if ~(isfinite(track_length_m) && track_length_m > 0)
    track_length_m = 1.0;
end

phi = mod(s, track_length_m) / track_length_m;
bin = floor(phi * profile.n_bins) + 1;
bin = min(max(bin, 1), profile.n_bins);

u = profile.mean_u(bin, :);
u = local_clamp_inputs(u);

end

function u = local_clamp_inputs(u)
u(1) = min(max(u(1), 0.0), 1.0);  % throttle
u(2) = min(max(u(2), 0.0), 1.0);  % brake
u(3) = min(max(u(3), 0.0), 1.0);  % drs proxy
end

