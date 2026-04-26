function data = load_processed_session(cfg)
%LOAD_PROCESSED_SESSION Load processed session contract files into MATLAB.

processed_dir = fullfile(cfg.project_root, "data", "processed", cfg.session_id);
if ~isfolder(processed_dir)
    error("Processed directory not found: %s", processed_dir);
end

session_metadata_path = fullfile(processed_dir, "session_metadata.json");
drivers_path = fullfile(processed_dir, "drivers.csv");
obs_path = fullfile(processed_dir, "observation_table.csv");
pit_path = fullfile(processed_dir, "pit_events.csv");
eval_path = fullfile(processed_dir, "evaluation_targets.csv");

required_files = { ...
    char(session_metadata_path), ...
    char(drivers_path), ...
    char(obs_path), ...
    char(pit_path), ...
    char(eval_path)};
for i = 1:numel(required_files)
    if ~isfile(required_files{i})
        error("Required processed file is missing: %s", required_files{i});
    end
end

data = struct();
data.paths = struct();
data.paths.processed_dir = processed_dir;

data.session_metadata = jsondecode(fileread(session_metadata_path));
data.drivers = normalize_drivers_table(readtable(drivers_path, "TextType", "string"));
data.observation_table = normalize_observation_table(readtable(obs_path, "TextType", "string"));
data.pit_events = normalize_pit_events(readtable(pit_path, "TextType", "string"));
data.evaluation_targets = normalize_evaluation_targets(readtable(eval_path, "TextType", "string"));

end
