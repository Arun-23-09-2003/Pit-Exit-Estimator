function evaluation = evaluate_filters(filter_results, driver_series, evaluation_targets, cfg)
%EVALUATE_FILTERS Classification-first evaluation for rejoin-order prediction.
% For each pit case:
% 1) use decision time and realized rejoin time from evaluation targets
% 2) propagate only the rest of the grid from decision->rejoin with
%    phase-binned mean input profiles estimated from history up to decision
% 3) compare predicted rejoin position to realized position (true/false)

n_filters = numel(filter_results);
summary_rows = local_empty_summary_table(n_filters);
all_case_rows = local_empty_case_table(0);

track_length_m = local_track_length(driver_series, cfg);
tol = cfg.evaluation.position_match_tolerance;

for f = 1:n_filters
    fr = filter_results(f);
    case_table = local_rejoin_case_metrics(fr, driver_series, evaluation_targets, cfg, track_length_m, tol);

    valid = case_table.is_prediction_available & isfinite(case_table.realized_rejoin_position);
    correct = valid & case_table.is_correct_prediction;
    within_one = valid & case_table.is_within_one_position;

    summary_rows.filter_name(f) = string(fr.filter_name);
    summary_rows.accuracy(f) = local_ratio(sum(correct), sum(valid));
    summary_rows.within_one_accuracy(f) = local_ratio(sum(within_one), sum(valid));
    summary_rows.true_count(f) = sum(correct);
    summary_rows.false_count(f) = sum(valid) - sum(correct);
    summary_rows.n_rejoin_cases(f) = height(case_table);
    summary_rows.n_predicted_cases(f) = sum(valid);
    summary_rows.prediction_coverage(f) = local_ratio(sum(valid), height(case_table));

    all_case_rows = [all_case_rows; case_table]; %#ok<AGROW>
end

evaluation = struct();
evaluation.summary_metrics = summary_rows;
evaluation.rejoin_case_metrics = all_case_rows;

end

function case_table = local_rejoin_case_metrics(filter_result, driver_series, targets, cfg, track_length_m, tol)
if ismember("case_valid", targets.Properties.VariableNames)
    targets = targets(targets.case_valid, :);
end

case_table = local_empty_case_table(0);
if isempty(targets)
    return;
end

n = height(targets);
case_table = local_empty_case_table(n);

for r = 1:n
    target_driver = targets.driver_number(r);
    t_decision = targets.decision_time_t_rel_s(r);
    t_rejoin = targets.realized_rejoin_t_rel_s(r);
    if ismember("realized_rejoin_position", targets.Properties.VariableNames)
        realized_rejoin_position = targets.realized_rejoin_position(r);
    else
        realized_rejoin_position = NaN;
    end
    if ~isfinite(realized_rejoin_position)
        realized_rejoin_position = local_realized_position_from_series(driver_series, target_driver, t_rejoin, cfg.evaluation.max_time_error_s);
    end
    if ismember("realized_s_m", targets.Properties.VariableNames)
        rejoin_anchor_s = targets.realized_s_m(r);
    else
        rejoin_anchor_s = NaN;
    end

    [predicted_rejoin_position, n_cars_used, n_steps_total, max_t_match_err] = local_predict_position_from_rest_grid( ...
        filter_result, driver_series, target_driver, t_decision, t_rejoin, rejoin_anchor_s, track_length_m, cfg);

    case_table.filter_name(r) = string(filter_result.filter_name);
    case_table.prediction_case_id(r) = targets.prediction_case_id(r);
    case_table.driver_number(r) = target_driver;
    case_table.decision_time_t_rel_s(r) = t_decision;
    case_table.rejoin_t_rel_s(r) = t_rejoin;
    case_table.rejoin_reference_s_m(r) = rejoin_anchor_s;
    case_table.predicted_rejoin_position(r) = predicted_rejoin_position;
    case_table.realized_rejoin_position(r) = realized_rejoin_position;
    case_table.rejoin_position_error(r) = predicted_rejoin_position - realized_rejoin_position;
    case_table.n_rest_grid_cars_used(r) = n_cars_used;
    case_table.total_propagation_steps(r) = n_steps_total;
    case_table.decision_state_match_error_s(r) = max_t_match_err;

    is_available = isfinite(predicted_rejoin_position) && isfinite(realized_rejoin_position);
    case_table.is_prediction_available(r) = is_available;
    case_table.is_correct_prediction(r) = is_available && abs(predicted_rejoin_position - realized_rejoin_position) <= tol;
    case_table.is_within_one_position(r) = is_available && abs(predicted_rejoin_position - realized_rejoin_position) <= (1.0 + tol);
end

end

function [pred_pos, n_cars_used, n_steps_total, max_t_match_err] = local_predict_position_from_rest_grid( ...
    filter_result, driver_series, target_driver, t_decision, t_rejoin, rejoin_anchor_s, track_length_m, cfg)
pred_pos = NaN;
n_cars_used = 0;
n_steps_total = 0;
max_t_match_err = NaN;

if ~(isfinite(t_decision) && isfinite(t_rejoin) && t_rejoin > t_decision && isfinite(rejoin_anchor_s))
    return;
end

s_end = [];
t_match_err = [];

for i = 1:numel(filter_result.drivers)
    dr = filter_result.drivers(i);
    if dr.driver_number == target_driver || isempty(dr.t)
        continue;
    end

    [x0, dt0] = local_state_at_time(dr, t_decision);
    if any(~isfinite(x0))
        continue;
    end

    ds = local_series_by_driver(driver_series, dr.driver_number);
    if isempty(ds)
        continue;
    end

    profile = estimate_input_profile(ds, t_decision, cfg);
    flags_ref = local_flags_at_time(ds, t_decision);
    flags_ref(1) = false; % rest-of-grid propagation ignores pit mode for target scenario

    [x_end, n_steps] = propagate_open_loop_with_profile( ...
        x0, t_decision, t_rejoin, profile, flags_ref, track_length_m, cfg);

    if isfinite(x_end(1))
        s_end(end + 1, 1) = x_end(1); %#ok<AGROW>
        t_match_err(end + 1, 1) = dt0; %#ok<AGROW>
        n_steps_total = n_steps_total + n_steps;
    end
end

if isempty(s_end)
    return;
end

pred_pos = sum(s_end > rejoin_anchor_s) + 1;
n_cars_used = numel(s_end);
if ~isempty(t_match_err)
    max_t_match_err = max(t_match_err);
end
end

function [x, dt_abs] = local_state_at_time(dr, t_query)
x = [NaN; NaN; NaN];
dt_abs = NaN;
if isempty(dr.t)
    return;
end
[dt_abs, j] = min(abs(dr.t - t_query));
x = dr.x_hat(j, :)';
end

function flags = local_flags_at_time(ds, t_query)
flags = [false, false, false];
if isempty(ds.t) || isempty(ds.flags)
    return;
end

idx = find(ds.t <= t_query, 1, "last");
if isempty(idx)
    [~, idx] = min(abs(ds.t - t_query));
end
flags = logical(ds.flags(idx, :));
end

function ds = local_series_by_driver(driver_series, driver_number)
idx = find([driver_series.driver_number] == driver_number, 1, "first");
if isempty(idx)
    ds = [];
else
    ds = driver_series(idx);
end
end

function pos = local_realized_position_from_series(driver_series, driver_number, t_query, max_time_error_s)
pos = NaN;
ds = local_series_by_driver(driver_series, driver_number);
if isempty(ds) || isempty(ds.t) || isempty(ds.position_obs)
    return;
end
[dt_abs, j] = min(abs(ds.t - t_query));
if dt_abs <= max_time_error_s && isfinite(ds.position_obs(j))
    pos = ds.position_obs(j);
end
end

function track_length_m = local_track_length(driver_series, cfg)
if isfield(cfg, "track_length_m") && isfinite(cfg.track_length_m) && cfg.track_length_m > 0
    track_length_m = cfg.track_length_m;
    return;
end

track_length_m = NaN;
for i = 1:numel(driver_series)
    ds = driver_series(i);
    if isempty(ds.z)
        continue;
    end
    s = ds.z(:, 1);
    lp = ds.lap_progress;
    mask = isfinite(s) & isfinite(lp) & lp > 0.1 & lp < 0.9;
    if any(mask)
        cand = median(s(mask) ./ max(lp(mask), 1e-3), "omitnan");
        if isfinite(cand) && cand > 1000 && cand < 10000
            track_length_m = cand;
            break;
        end
    end
end

if ~isfinite(track_length_m)
    track_length_m = 5000.0;
end
end

function t = local_empty_summary_table(n)
t = table('Size', [n, 8], ...
    'VariableTypes', ["string", "double", "double", "double", "double", "double", "double", "double"], ...
    'VariableNames', ["filter_name", "accuracy", "within_one_accuracy", ...
                      "true_count", "false_count", "n_rejoin_cases", ...
                      "n_predicted_cases", "prediction_coverage"]);
end

function t = local_empty_case_table(n)
t = table('Size', [n, 15], ...
    'VariableTypes', ["string", "string", "double", "double", "double", "double", ...
                      "double", "double", "double", "double", "double", "double", ...
                      "logical", "logical", "logical"], ...
    'VariableNames', ["filter_name", "prediction_case_id", "driver_number", ...
                      "decision_time_t_rel_s", "rejoin_t_rel_s", "rejoin_reference_s_m", ...
                      "predicted_rejoin_position", "realized_rejoin_position", "rejoin_position_error", ...
                      "n_rest_grid_cars_used", "total_propagation_steps", "decision_state_match_error_s", ...
                      "is_prediction_available", "is_correct_prediction", "is_within_one_position"]);
end

function y = local_ratio(num, den)
if den <= 0
    y = NaN;
else
    y = num / den;
end
end
