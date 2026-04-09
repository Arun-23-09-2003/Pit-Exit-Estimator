# Data Contract

## Version

`v0.1`

## Session ID

Use:

`<year>_<grand_prix>_<session_name>`

Example:

`2024_monaco_race`

Use the same `session_id` in folder names and all exported files.

## Data stages

### Raw

`data/raw/<session_id>/`

Source-native OpenF1 pulls.
No manual edits.
No estimator-specific fields.

### Interim

`data/interim/<session_id>/`

Cleaned and aligned source data.
Track progress and joins can be added here.

### Processed

`data/processed/<session_id>/`

Stable estimator-facing exports.
These files are the contract.

## Required processed files

Each session must export:

- `session_metadata.json`
- `drivers.csv`
- `observation_table.csv`
- `pit_events.csv`
- `evaluation_targets.csv`

## `session_metadata.json`

Required fields:

- `data_contract_version`
- `session_id`
- `year`
- `meeting_name`
- `session_name`
- `session_start_utc`
- `session_end_utc`
- `sampling_reference`
- `notes`

## `drivers.csv`

One row per driver.

Required columns:

- `driver_number`
- `driver_code`
- `team_name`
- `car_index`
- `included_in_estimation`
- `exclusion_reason`

`car_index` is the fixed MATLAB ordering key.

## `observation_table.csv`

One row = one car at one timestamp.

Primary key:

- `session_id`
- `t_rel_s`
- `driver_number`

Required columns:

- `session_id`
- `t_utc`
- `t_rel_s`
- `driver_number`
- `car_index`
- `lap_number`
- `is_in_pit_lane`
- `is_under_sc`
- `is_under_vsc`
- `s_obs_m`
- `v_obs_mps`
- `a_obs_mps2`
- `s_obs_available`
- `v_obs_available`
- `a_obs_available`
- `position_obs`
- `gap_to_leader_obs_s`
- `gap_ahead_obs_s`
- `gap_behind_obs_s`
- `row_valid_for_estimation`

### Notes

- `t_rel_s` is the canonical time variable for MATLAB
- `s_obs_m` is unwrapped along-track distance
- `v_obs_mps` is along-track speed
- `a_obs_mps2` is observed or derived acceleration
- missing numeric values should be `NaN` or empty
- no future information may be used to build this table at a chosen decision time

## `pit_events.csv`

One row per pit event.

Required columns:

- `session_id`
- `driver_number`
- `pit_event_id`
- `pit_entry_t_rel_s`
- `pit_exit_t_rel_s`
- `pit_lane_time_s`
- `pit_stop_time_s`
- `rejoin_lap_number`
- `pit_under_sc`
- `pit_under_vsc`
- `pit_event_valid`

### Notes

- rejoin is referenced at `pit_exit_t_rel_s`
- if `pit_stop_time_s` cannot be recovered, leave it missing

## `evaluation_targets.csv`

One row per prediction case.
This file is evaluation-only and must not be used as estimator input.

Required columns:

- `session_id`
- `prediction_case_id`
- `driver_number`
- `decision_time_t_rel_s`
- `realized_rejoin_t_rel_s`
- `realized_rejoin_position`
- `realized_gap_to_leader_s`
- `realized_gap_ahead_s`
- `realized_gap_behind_s`
- `realized_s_m`
- `realized_v_mps`
- `case_valid`

## Required units

Use these units everywhere:

- distance: meters
- speed: meters per second
- acceleration: meters per second squared
- time: seconds
- timestamps: UTC ISO 8601

## Required rules

- `t_rel_s` is the common session-relative timeline
- `car_index` is the fixed state ordering key
- `s_obs_m` must be continuous across laps
- observed fields and evaluation targets must stay in separate files
- missingness must be explicit
- processed exports must be loadable in MATLAB without per-session fixes

## Still open

These are not fixed by this doc:

- exact method to derive `s_obs_m`
- exact resampling rate
- exact source priority when feeds disagree
- exact pit-loss model for hypothetical branch rollout
- whether `a_obs_mps2` is used as a measurement or only as a state component