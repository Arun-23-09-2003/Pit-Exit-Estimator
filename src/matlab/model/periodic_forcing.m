function [b_phi, db_ds] = periodic_forcing(s, track_length_m, m)
%PERIODIC_FORCING Phase-scheduled acceleration forcing and derivative.

if ~(isfinite(track_length_m) && track_length_m > 0)
    track_length_m = 1.0;
end

phi = mod(s, track_length_m) / track_length_m;
theta = 2.0 * pi * phi;

b_phi = m.periodic_amp_1 * sin(theta) + m.periodic_amp_2 * cos(theta);

dtheta_ds = 2.0 * pi / track_length_m;
db_dtheta = m.periodic_amp_1 * cos(theta) - m.periodic_amp_2 * sin(theta);
db_ds = db_dtheta * dtheta_ds;

end

