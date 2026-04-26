function output_paths = export_filter_results(filter_results, evaluation, cfg)
%EXPORT_FILTER_RESULTS Write comparative outputs to disk.

session_dir = fullfile(cfg.output.root_dir, cfg.session_id);
if ~isfolder(session_dir)
    mkdir(session_dir);
end

summary_csv = fullfile(session_dir, "summary_metrics.csv");
rejoin_csv = fullfile(session_dir, "rejoin_case_metrics.csv");
mat_file = fullfile(session_dir, "filter_outputs.mat");

writetable(evaluation.summary_metrics, summary_csv);
writetable(evaluation.rejoin_case_metrics, rejoin_csv);

if cfg.output.save_mat
    save(mat_file, "filter_results", "evaluation", "cfg", "-v7.3");
end

output_paths = struct();
output_paths.session_dir = session_dir;
output_paths.summary_csv = summary_csv;
output_paths.rejoin_csv = rejoin_csv;
output_paths.mat_file = mat_file;

end

