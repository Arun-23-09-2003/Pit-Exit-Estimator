function [z_pred, H] = measurement_model(x)
%MEASUREMENT_MODEL Observation model for [s, v, a].
% Identity mapping from state to measurement.

z_pred = x;
H = eye(3);

end

