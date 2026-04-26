function [evaluation, output_paths] = run_filter_comparison_for_session(session_id, cfg)
%RUN_FILTER_COMPARISON_FOR_SESSION Run all filters for one processed session.

cfg.session_id = string(session_id);

fprintf("Loading processed session: %s\n", cfg.session_id);
data = load_processed_session(cfg);
cfg.track_length_m = double(data.session_metadata.track_length_m);

fprintf("Preparing per-driver time series for %s...\n", cfg.session_id);
driver_series = build_driver_series(data.drivers, data.observation_table, cfg);

fprintf("Running Batch LUMVE for %s...\n", cfg.session_id);
lumve_result = run_batch_lumve(driver_series, data.session_metadata, cfg);

fprintf("Running EKF for %s...\n", cfg.session_id);
ekf_result = run_ekf(driver_series, data.session_metadata, cfg);

fprintf("Running UKF for %s...\n", cfg.session_id);
ukf_result = run_ukf(driver_series, data.session_metadata, cfg);

filter_results = [lumve_result, ekf_result, ukf_result];

fprintf("Evaluating rejoin-position predictions for %s...\n", cfg.session_id);
evaluation = evaluate_filters(filter_results, driver_series, data.evaluation_targets, cfg);
evaluation.summary_metrics.session_id = repmat(cfg.session_id, height(evaluation.summary_metrics), 1);
evaluation.summary_metrics = movevars(evaluation.summary_metrics, "session_id", "Before", "filter_name");
if ~isempty(evaluation.rejoin_case_metrics)
    evaluation.rejoin_case_metrics.session_id = repmat(cfg.session_id, height(evaluation.rejoin_case_metrics), 1);
    evaluation.rejoin_case_metrics = movevars(evaluation.rejoin_case_metrics, "session_id", "Before", "filter_name");
end

fprintf("Exporting MATLAB outputs for %s...\n", cfg.session_id);
output_paths = export_filter_results(filter_results, evaluation, cfg);

end

