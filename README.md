# Project Context Summary

## Working Project Idea
The project is a Formula 1 pit rejoin prediction problem framed as a **sequential state estimation** task.

At a chosen **pit decision point** during a race, the goal is to use only the **current and past data available up to that moment** to estimate the state of the full field and then predict where a target car would **rejoin after pitting**.

The intended strategic use case is for **undercut, overcut, and general pit strategy decisions**.

---

## Final Problem Framing
The estimator will track **all 20 cars** in the race, not just a local pack.

For each car, the state is currently planned as:

\[
x_k^{(i)} = [s_k^{(i)},\ v_k^{(i)},\ a_k^{(i)}]
\]

where:

- \(s_k^{(i)}\) = unwrapped along-track distance
- \(v_k^{(i)}\) = along-track speed
- \(a_k^{(i)}\) = along-track acceleration

The filter state will be based on these physical states because they are easier to interpret and estimate cleanly.

From the estimated full-field state, the project will derive higher-level race outputs such as:

- projected rejoin position
- projected delta to leader
- projected gap to the car ahead
- projected gap to the car behind

These outputs are **not the internal state**, they are derived quantities used for interpretation and validation.

---

## Rejoin Definition
For simplicity, **rejoin** is defined as:

- the instant the target car **crosses pit exit and is back on track**

This is the reference event against which predictions will be compared.

---

## Prediction Setup
At a selected pit decision point:

1. Use all available race data up to that moment to estimate the **current full-field state**
2. Create a hypothetical **pit branch** for the target car
3. Propagate the target car through the pit lane using a **pit-lane loss model with uncertainty**
4. Propagate the rest of the field forward from their current estimated states
5. Predict the target car’s rejoin state relative to the full field

The important constraint is that **no future information should be used** for the prediction, except possibly as a fallback simplification if setting up a fully causal pit-loss model becomes too painful.

---

## Pit Loss Assumption
The preferred approach is to use a **nominal pit-lane loss model** for the race context, such as:

- normal green-flag pit loss
- safety car pit loss
- virtual safety car pit loss

with uncertainty around that value during propagation.

There was also acknowledgment that, if this becomes too annoying to set up causally, the actual pit-lane loss from the real event could be used as a simplification, but that is not the preferred framing.

---

## Data Source and Tooling Plan
The intended data source is **OpenF1**.

Planned workflow:

- use Python for **data retrieval, cleanup, and setup**
- use MATLAB for the actual **state estimation, simulation, and evaluation**

This was chosen because the course project itself is expected to end in MATLAB, while Python is more convenient for pulling and organizing race data.

---

## Validation Plan
The reference for validation will be the **actual observed race outcome** from the dataset.

Main validation targets at pit exit:

- actual rejoin position
- actual delta to leader
- actual gap to the car ahead
- actual gap to the car behind

So the project is not just estimating the current race state, it is evaluating whether the sequential estimator can make a tactically useful pit rejoin prediction.

---

## Filter Direction
The project is intended to be built as a clean **sequential estimator**, not a batch fitting or regression problem.

The discussion ruled out several earlier ideas because they were drifting too much toward:
- offline latent-variable fitting
- parameter estimation that could be done with batch solvers
- problems where Kalman filtering was not the natural tool

The current pit rejoin formulation was chosen because it is much more naturally a recursive predict-update problem.

Exact filter choice has not been fully locked yet, but the likely candidates are from:

- KF
- EKF
- UKF
- PF

with the multi-car pit rejoin setting likely pushing the implementation toward a nonlinear filter.

---

## Repo / Project Organization Decisions
The repo will be kept relatively simple.

Main design decisions so far:

- do not overbuild the repo structure
- do not split the repo purely by language
- organize work more by **project stage** as it develops
- keep documentation strong, but not pointlessly verbose
- use markdown where it adds meaning, not everywhere for no reason

Earlier ideas about excessive folder-level documentation were deliberately scaled back.

---

## Current Conceptual Status
At this point, the project has a clean conceptual core:

- full-field sequential race-state estimation
- pit decision point prediction
- physically meaningful internal states
- strategy-relevant derived outputs
- validation against actual rejoin outcome

What remains is to turn this into:
- a precise measurement model
- a propagation model
- a pit branch mechanism
- a chosen filter implementation
- and a clean data pipeline from OpenF1 into MATLAB-ready inputs