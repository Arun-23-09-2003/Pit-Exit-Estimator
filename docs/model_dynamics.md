# Pit Rejoin Estimator: Dynamics Model

## Purpose

This document defines the filter dynamics for the pit rejoin estimator.
The project stays fully in a Kalman-filter framing:

- causal recursive estimation
- physically interpretable states
- explicit system inputs
- mode-switched linear dynamics with controlled approximations

This is not an ML model.

## State and Inputs

Per car `i`, the state is:

`x_k^(i) = [s_k^(i), v_k^(i), a_k^(i)]^T`

where:

- `s` is unwrapped along-track distance (m)
- `v` is along-track speed (m/s)
- `a` is along-track acceleration (m/s^2)

Per car `i`, the system input is:

`u_k^(i) = [u_throttle_k, u_brake_k, u_drs_k]^T`

where:

- `u_throttle_k = throttle_input_pct / 100`
- `u_brake_k = brake_input_pct / 100`
- `u_drs_k = drs_input_active` (`0` or `1`)

The full-field state stacks all cars:

`X_k = [x_k^(1); x_k^(2); ...; x_k^(N)]`, with `N = 20`.

## Periodic Race Coordinate

Racing is periodic lap-to-lap, with local variations.
We represent periodicity using lap phase:

`phi_k = mod(s_k, L_track) / L_track`

where `L_track = track_length_m`.

`phi_k` is not a state.
It is a scheduling variable used to apply phase-dependent nominal dynamics.

## Per-Car Dynamics with Inputs

For a selected regime `r`, use:

`x_{k+1} = F_r(dt, rho_a_r) x_k + B_r u_k + c_r(phi_k) + w_k`

with `w_k ~ N(0, Q_r)`.

Base kinematics:

`s_{k+1} = s_k + v_k*dt + 0.5*a_k*dt^2 + w_s`

`v_{k+1} = v_k + a_k*dt + w_v`

Acceleration channel:

`a_{k+1} = rho_a_r*a_k + g_th_r*u_throttle_k - g_br_r*u_brake_k + g_drs_r*u_drs_k + b_r(phi_k) + w_a`

Interpretation:

- `rho_a_r` controls acceleration memory in regime `r`
- `g_th_r`, `g_br_r`, `g_drs_r` are regime-specific input gains
- `b_r(phi_k)` is periodic forcing term for lap-phase effects

## DRS-On and DRS-Off Regimes

Under green conditions (not pit, not SC, not VSC), use two dynamics regimes:

- `green_free_air_no_drs` when `u_drs_k = 0`
- `green_traffic_drs` when `u_drs_k = 1`

This is the project approximation for overtakes and traffic influence:

- DRS-on regime approximates traffic and pass-attempt context.
- DRS-off regime approximates free-air behavior.

The state definition stays the same in both regimes.
Only `(F_r, B_r, c_r, Q_r)` change.

## Global Mode Logic

Regime selection at each step is:

1. If `is_in_pit_lane = 1`, use `pit_mode`.
2. Else if `is_under_sc = 1`, use `sc_mode`.
3. Else if `is_under_vsc = 1`, use `vsc_mode`.
4. Else if `drs_input_active = 1`, use `green_traffic_drs`.
5. Else use `green_free_air_no_drs`.

This keeps switching deterministic and causal.

## Periodic Term Construction (`b_r(phi)`)

To keep projections clean and causal:

1. Build phase bins over `phi in [0, 1)`.
2. Compute per-bin acceleration residual averages from past data only.
3. Update bin values with exponential forgetting to allow lap-to-lap variation.
4. Freeze the profile at decision time for branch projection.

This gives periodic structure without leaking future information.

## Predict-Update Workflow

For each car and each time step:

1. Read current inputs and mode flags.
2. Select regime `r`.
3. Compute `phi_k` from predicted `s_k`.
4. Predict using `(F_r, B_r, c_r(phi_k), Q_r)`.
5. Update with available measurements (`s_obs_m`, `v_obs_mps`, optional `a_obs_mps2`).

For pit decision branching:

- clone posterior at `t_dec`
- freeze periodic profile and regime parameters at `t_dec`
- propagate target in pit mode with pit uncertainty
- propagate others with current non-pit regimes
- evaluate rejoin outputs at pit exit crossing

## Why These Approximations Are Clean

1. Inputs are explicit and physical.
   Throttle, brake, and DRS affect acceleration rather than becoming hidden latent terms.

2. Periodicity is handled as scheduling, not state inflation.
   `phi_k` captures lap structure without adding hard-to-identify states.

3. Regime switching is simple and interpretable.
   Pit, SC, VSC, DRS-on, and DRS-off are meaningful operational modes.

4. Overtake effects are approximated with DRS regime split.
   This avoids pairwise interaction explosion while still modeling traffic context.

5. The model remains causal and MATLAB-friendly.
   No future data is required for prediction at a decision time.

## Known Limits (Accepted for Course Scope)

- DRS is a proxy for traffic and overtaking pressure, not a full interaction model.
- Brake input may be coarse depending on source encoding.
- No explicit tire thermal or degradation state is included.
- No full 2D track geometry is used in the state.

These are deliberate to keep the project focused on recursive filtering.

## Implementation Defaults (Initial Pass)

- Start with fixed `dt` from `observation_table.csv`.
- Initialize `rho_a_r = 1` in all regimes, then tune per regime.
- Fit `g_th_r`, `g_br_r`, `g_drs_r` from causal historical slices and regularize.
- Use 20 to 50 phase bins for `b_r(phi)` with exponential forgetting.
- Tune `Q_r` per regime (`green_free_air_no_drs`, `green_traffic_drs`, `sc`, `vsc`, `pit`).
- Validate on rejoin metrics in `evaluation_targets.csv`.
