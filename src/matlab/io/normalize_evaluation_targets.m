function targets = normalize_evaluation_targets(targets)
%NORMALIZE_EVALUATION_TARGETS Normalize evaluation targets table.

if isempty(targets)
    return;
end

numeric_cols = [
    "driver_number", "decision_time_t_rel_s", "realized_rejoin_t_rel_s", ...
    "realized_rejoin_position", "realized_gap_to_leader_s", ...
    "realized_gap_ahead_s", "realized_gap_behind_s", ...
    "realized_s_m", "realized_v_mps"
];

for i = 1:numel(numeric_cols)
    col = numeric_cols(i);
    if ismember(col, targets.Properties.VariableNames)
        targets.(col) = parse_numeric_column(targets.(col));
    end
end

if ismember("case_valid", targets.Properties.VariableNames)
    targets.case_valid = parse_logical_column(targets.case_valid);
end

if ismember("session_id", targets.Properties.VariableNames)
    targets.session_id = string(targets.session_id);
end
if ismember("prediction_case_id", targets.Properties.VariableNames)
    targets.prediction_case_id = string(targets.prediction_case_id);
end

targets = sortrows(targets, ["driver_number", "realized_rejoin_t_rel_s"]);

end
