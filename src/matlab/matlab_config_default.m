function cfg = matlab_config_default()
%MATLAB_CONFIG_DEFAULT Default configuration for comparative filter runs.

this_file = mfilename("fullpath");
this_dir = fileparts(this_file);             % .../src/matlab
src_dir = fileparts(this_dir);               % .../src
project_root = fileparts(src_dir);           % repo root

cfg = struct();
cfg.project_root = project_root;
cfg.session_id = "2024_monaco_race";
cfg.session_name = "Race";

% Data reduction for practical runtimes in MATLAB.
cfg.resample_dt_s = 0.50;
cfg.max_rows_per_driver = 50000;
cfg.min_dt_s = 1e-3;

% Measurement model z = [s, v, a].
cfg.R_diag = [25.0^2, 2.0^2, 1.5^2];

% Initial state covariance.
cfg.P0_diag = [200.0^2, 20.0^2, 8.0^2];

% Small numerical regularizers.
cfg.epsilon = 1e-9;
cfg.covariance_jitter = 1e-9;

% Batch LUMVE settings.
cfg.lumve = struct();
cfg.lumve.window_s = 12.0;
cfg.lumve.min_rows = 8;
cfg.lumve.ridge = 1e-6;
cfg.lumve.prior_std = [45.0, 4.0, 2.0];

% UKF settings.
cfg.ukf = struct();
cfg.ukf.alpha = 1e-2;
cfg.ukf.beta = 2.0;
cfg.ukf.kappa = 0.0;

% Evaluation settings.
cfg.evaluation = struct();
cfg.evaluation.max_time_error_s = 2.0;
cfg.evaluation.position_match_tolerance = 0.5;

% Open-loop propagation for rejoin-order evaluation.
cfg.propagation = struct();
cfg.propagation.dt_s = 0.50;
cfg.propagation.input_phase_bins = 40;
cfg.propagation.min_history_rows = 30;
cfg.propagation.default_u = [0.55, 0.08, 0.0];

% Mode-dependent dynamics settings.
cfg.mode = struct();

cfg.mode.green_free_air_no_drs = local_mode( ...
    0.95, 1.40, 2.30, 0.40, [4.0, 2.0, 1.0], 0.10, 0.05);
cfg.mode.green_traffic_drs = local_mode( ...
    0.95, 1.35, 2.25, 0.85, [4.5, 2.3, 1.1], 0.12, 0.06);
cfg.mode.sc_mode = local_mode( ...
    0.90, 0.20, 1.60, 0.00, [3.0, 1.8, 0.8], 0.04, 0.02);
cfg.mode.vsc_mode = local_mode( ...
    0.92, 0.40, 1.80, 0.00, [3.2, 1.9, 0.9], 0.05, 0.03);
cfg.mode.pit_mode = local_mode( ...
    0.85, 0.10, 2.60, 0.00, [5.0, 2.8, 1.4], 0.03, 0.01);

% Output paths.
cfg.output = struct();
cfg.output.root_dir = fullfile(project_root, "results", "matlab");
cfg.output.save_mat = true;

end

function m = local_mode(rho_a, g_th, g_br, g_drs, q_diag, periodic_amp_1, periodic_amp_2)
m = struct();
m.rho_a = rho_a;
m.g_th = g_th;
m.g_br = g_br;
m.g_drs = g_drs;
m.q_diag = q_diag;
m.periodic_amp_1 = periodic_amp_1;
m.periodic_amp_2 = periodic_amp_2;
end
