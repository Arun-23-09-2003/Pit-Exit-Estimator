% Run comparative state estimation filters on Monaco processed data.
% Filters: Batch LUMVE, EKF, UKF.

clearvars;
clc;

this_dir = fileparts(mfilename("fullpath"));
addpath(this_dir);
addpath(genpath(this_dir));

cfg = matlab_config_default();
cfg.session_id = "2024_monaco_race";

[evaluation, output_paths] = run_filter_comparison_for_session(cfg.session_id, cfg);

disp("Done. Summary metrics:");
disp(evaluation.summary_metrics);
disp("Outputs written to:");
disp(output_paths);
