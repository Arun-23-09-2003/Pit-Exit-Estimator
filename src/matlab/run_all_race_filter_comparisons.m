% Run MATLAB filter comparisons for all requested 2024 race sessions.
% Sessions that do not yet have complete processed data are skipped cleanly.

clearvars;
clc;

this_dir = fileparts(mfilename("fullpath"));
addpath(this_dir);
addpath(genpath(this_dir));

cfg = matlab_config_default();

requested_sessions = [
    "2024_bahrain_race"
    "2024_monaco_race"
    "2024_silverstone_race"
    "2024_spa_race"
    "2024_abu_dhabi_race"
];

all_summary = table();
run_log = table('Size', [numel(requested_sessions), 4], ...
    'VariableTypes', ["string", "string", "string", "string"], ...
    'VariableNames', ["session_id", "status", "message", "output_dir"]);

for i = 1:numel(requested_sessions)
    session_id = requested_sessions(i);
    run_log.session_id(i) = session_id;

    if ~is_processed_session_ready(cfg.project_root, session_id)
        msg = "processed files are not ready";
        fprintf("[SKIP] %s: %s\n", session_id, msg);
        run_log.status(i) = "skipped";
        run_log.message(i) = msg;
        run_log.output_dir(i) = "";
        continue;
    end

    try
        fprintf("[START] %s\n", session_id);
        [evaluation, output_paths] = run_filter_comparison_for_session(session_id, cfg);
        all_summary = [all_summary; evaluation.summary_metrics]; %#ok<AGROW>

        run_log.status(i) = "ok";
        run_log.message(i) = "";
        run_log.output_dir(i) = string(output_paths.session_dir);
        fprintf("[OK] %s\n", session_id);
    catch ME
        run_log.status(i) = "failed";
        run_log.message(i) = string(ME.message);
        run_log.output_dir(i) = "";
        fprintf("[FAILED] %s: %s\n", session_id, ME.message);
    end
end

batch_dir = fullfile(cfg.output.root_dir, "batch_2024_races");
if ~isfolder(batch_dir)
    mkdir(batch_dir);
end

summary_path = fullfile(batch_dir, "combined_summary_metrics.csv");
log_path = fullfile(batch_dir, "run_log.csv");

if ~isempty(all_summary)
    writetable(all_summary, summary_path);
end
writetable(run_log, log_path);

disp("Batch MATLAB runner complete.");
disp(run_log);
if ~isempty(all_summary)
    disp("Combined summary:");
    disp(all_summary);
end
fprintf("Run log: %s\n", log_path);
fprintf("Combined summary: %s\n", summary_path);

