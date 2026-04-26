function ready = is_processed_session_ready(project_root, session_id)
%IS_PROCESSED_SESSION_READY True when all processed contract files exist.

processed_dir = fullfile(project_root, "data", "processed", string(session_id));
required_files = [
    "session_metadata.json"
    "drivers.csv"
    "observation_table.csv"
    "pit_events.csv"
    "evaluation_targets.csv"
];

ready = isfolder(processed_dir);
if ~ready
    return;
end

for i = 1:numel(required_files)
    if ~isfile(fullfile(processed_dir, required_files(i)))
        ready = false;
        return;
    end
end

end

