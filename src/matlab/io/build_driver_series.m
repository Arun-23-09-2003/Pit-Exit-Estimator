function driver_series = build_driver_series(drivers, obs, cfg)
%BUILD_DRIVER_SERIES Build per-driver estimation streams from observation table.

if isempty(drivers) || isempty(obs)
    driver_series = struct([]);
    return;
end

drivers = sortrows(drivers, "car_index");
in_mask = true(height(drivers), 1);
if ismember("included_in_estimation", drivers.Properties.VariableNames)
    in_mask = drivers.included_in_estimation;
end
drivers = drivers(in_mask, :);

driver_series = repmat(struct( ...
    "driver_number", NaN, ...
    "car_index", NaN, ...
    "t", [], ...
    "z", [], ...
    "avail", [], ...
    "u", [], ...
    "flags", [], ...
    "lap_progress", [], ...
    "position_obs", [], ...
    "gap_to_leader_obs_s", [], ...
    "row_valid_for_prediction", []), height(drivers), 1);

for i = 1:height(drivers)
    dnum = drivers.driver_number(i);
    car_index = drivers.car_index(i);

    rows = obs(obs.driver_number == dnum, :);
    if isempty(rows)
        warning("No observation rows found for driver %d", dnum);
        continue;
    end

    if ismember("row_valid_for_estimation", rows.Properties.VariableNames)
        rows = rows(rows.row_valid_for_estimation, :);
    end
    rows = sortrows(rows, "t_rel_s");
    rows = rows(~isnan(rows.t_rel_s), :);
    if isempty(rows)
        warning("No valid estimation rows after filtering for driver %d", dnum);
        continue;
    end

    if cfg.resample_dt_s > 0
        rows = local_downsample_rows(rows, cfg.resample_dt_s);
    end

    if cfg.max_rows_per_driver > 0 && height(rows) > cfg.max_rows_per_driver
        idx = unique(round(linspace(1, height(rows), cfg.max_rows_per_driver)));
        rows = rows(idx, :);
    end

    throttle = clamp01(rows.throttle_input_pct / 100.0);
    brake = clamp01(rows.brake_input_pct / 100.0);
    drs = clamp01(rows.drs_input_active);

    driver_series(i).driver_number = dnum;
    driver_series(i).car_index = car_index;
    driver_series(i).t = rows.t_rel_s;
    driver_series(i).z = [rows.s_obs_m, rows.v_obs_mps, rows.a_obs_mps2];
    driver_series(i).avail = [rows.s_obs_available, rows.v_obs_available, rows.a_obs_available];
    driver_series(i).u = [throttle, brake, drs];
    driver_series(i).flags = [rows.is_in_pit_lane, rows.is_under_sc, rows.is_under_vsc];
    driver_series(i).lap_progress = rows.lap_progress;
    driver_series(i).position_obs = rows.position_obs;
    driver_series(i).gap_to_leader_obs_s = rows.gap_to_leader_obs_s;
    driver_series(i).row_valid_for_prediction = rows.row_valid_for_prediction;
end

end

function out = local_downsample_rows(rows, dt)
if height(rows) < 2
    out = rows;
    return;
end

bin = round(rows.t_rel_s / dt) * dt;
[group_id, ~] = findgroups(bin);
idx = splitapply(@(x) x(end), (1:height(rows))', group_id);
out = rows(idx, :);
out.t_rel_s = round(out.t_rel_s / dt) * dt;
out = sortrows(out, "t_rel_s");
end

function y = clamp01(x)
y = x;
y(y < 0) = 0;
y(y > 1) = 1;
end

