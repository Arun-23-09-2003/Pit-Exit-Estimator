function obs = normalize_observation_table(obs)
%NORMALIZE_OBSERVATION_TABLE Convert observation table columns to numeric/logical.

if isempty(obs)
    return;
end

numeric_cols = [
    "t_rel_s", "driver_number", "car_index", "lap_number", "lap_progress", ...
    "s_obs_m", "v_obs_mps", "a_obs_mps2", ...
    "throttle_input_pct", "brake_input_pct", "drs_input_active", ...
    "position_obs", "gap_to_leader_obs_s", "gap_ahead_obs_s", "gap_behind_obs_s"
];

logical_cols = [
    "is_in_pit_lane", "is_under_sc", "is_under_vsc", ...
    "s_obs_available", "v_obs_available", "a_obs_available", ...
    "throttle_input_available", "brake_input_available", "drs_input_available", ...
    "row_valid_for_estimation", "row_valid_for_prediction"
];

for i = 1:numel(numeric_cols)
    col = numeric_cols(i);
    if ismember(col, obs.Properties.VariableNames)
        obs.(col) = parse_numeric_column(obs.(col));
    end
end

for i = 1:numel(logical_cols)
    col = logical_cols(i);
    if ismember(col, obs.Properties.VariableNames)
        obs.(col) = parse_logical_column(obs.(col));
    end
end

if ismember("session_id", obs.Properties.VariableNames)
    obs.session_id = string(obs.session_id);
end
if ismember("t_utc", obs.Properties.VariableNames)
    obs.t_utc = string(obs.t_utc);
end

obs = sortrows(obs, ["driver_number", "t_rel_s"]);

end
