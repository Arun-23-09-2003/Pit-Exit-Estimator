function pit = normalize_pit_events(pit)
%NORMALIZE_PIT_EVENTS Normalize processed pit events table.

if isempty(pit)
    return;
end

numeric_cols = [
    "driver_number", "pit_entry_t_rel_s", "pit_exit_t_rel_s", ...
    "pit_lane_time_s", "pit_stop_time_s", "rejoin_lap_number"
];
logical_cols = ["pit_under_sc", "pit_under_vsc", "pit_event_valid"];

for i = 1:numel(numeric_cols)
    col = numeric_cols(i);
    if ismember(col, pit.Properties.VariableNames)
        pit.(col) = parse_numeric_column(pit.(col));
    end
end

for i = 1:numel(logical_cols)
    col = logical_cols(i);
    if ismember(col, pit.Properties.VariableNames)
        pit.(col) = parse_logical_column(pit.(col));
    end
end

if ismember("session_id", pit.Properties.VariableNames)
    pit.session_id = string(pit.session_id);
end
if ismember("pit_event_id", pit.Properties.VariableNames)
    pit.pit_event_id = string(pit.pit_event_id);
end

pit = sortrows(pit, ["driver_number", "pit_entry_t_rel_s"]);

end
