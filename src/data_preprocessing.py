from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _empty_df(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in columns})


def _safe_to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _safe_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _normalize_driver_number(series: pd.Series) -> pd.Series:
    return _safe_to_numeric(series).astype("Int64")


def _normalize_duration_seconds(series: pd.Series) -> pd.Series:
    out = _safe_to_numeric(series)
    if out.notna().any():
        # OpenF1 pit durations may appear as centiseconds-like values (e.g., 2358 -> 23.58 s).
        scaled_mask = out > 200.0
        out.loc[scaled_mask] = out.loc[scaled_mask] / 100.0
    out = out.where(out > 0)
    return out


def _parse_gap_seconds(value: Any) -> float:
    if value is None:
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("+", "")
    if not text or text.upper().endswith("L"):
        return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def _bool_or_zero(series: pd.Series) -> pd.Series:
    numeric = _safe_to_numeric(series)
    return numeric.fillna(0).astype(float)


@dataclass
class RaceDataPreprocessor:
    project_root: Path
    interm_dir_name: str = "interim"
    drs_open_codes: tuple[int, ...] = (10, 12, 14)

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root)
        self.raw_root = self.project_root / "data" / "raw"
        self.interm_root = self.project_root / "data" / self.interm_dir_name
        self.processed_root = self.project_root / "data" / "processed"

        self.interm_root.mkdir(parents=True, exist_ok=True)
        self.processed_root.mkdir(parents=True, exist_ok=True)

    def _read_json_rows(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return [payload]
        return []

    def _load_raw_df(self, raw_dir: Path, stem: str) -> pd.DataFrame:
        rows = self._read_json_rows(raw_dir / f"{stem}.json")
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    @staticmethod
    def _series(df: pd.DataFrame, name: str, default: Any = np.nan) -> pd.Series:
        if name in df.columns:
            return df[name]
        return pd.Series([default] * len(df), index=df.index)

    @staticmethod
    def _first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
        for name in names:
            if name in df.columns:
                return name
        return None

    def _clean_drivers(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return _empty_df(["driver_number", "driver_code", "team_name"])

        out = pd.DataFrame()
        out["driver_number"] = _normalize_driver_number(self._series(df, "driver_number"))
        code = self._series(df, "name_acronym", "")
        code = code.where(code.astype(str).str.strip() != "", self._series(df, "broadcast_name", ""))
        code = code.where(code.astype(str).str.strip() != "", self._series(df, "full_name", ""))
        out["driver_code"] = (
            code.fillna("").astype(str)
        )
        out["team_name"] = self._series(df, "team_name", "unknown").fillna("unknown").astype(str)
        out = out.dropna(subset=["driver_number"]).drop_duplicates("driver_number")
        out = out.sort_values("driver_number").reset_index(drop=True)
        return out

    @staticmethod
    def _ensure_series(df: pd.DataFrame, column: str | None, default: Any) -> pd.Series:
        if column and column in df.columns:
            return df[column]
        return pd.Series([default] * len(df), index=df.index)

    def _clean_telemetry(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return _empty_df(["date", "driver_number", "speed", "throttle", "brake", "drs"])

        out = pd.DataFrame()
        out["date"] = _safe_to_datetime(self._series(df, "date"))
        out["driver_number"] = _normalize_driver_number(self._series(df, "driver_number"))
        out["speed"] = _safe_to_numeric(self._series(df, "speed"))
        out["throttle"] = _safe_to_numeric(self._series(df, "throttle"))
        out["brake"] = _safe_to_numeric(self._series(df, "brake"))
        out["drs"] = _safe_to_numeric(self._series(df, "drs"))
        out = out.dropna(subset=["date", "driver_number"])
        out = out.sort_values(["driver_number", "date"]).drop_duplicates(
            ["driver_number", "date"], keep="last"
        )
        out = out.reset_index(drop=True)
        return out

    def _clean_positions(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return _empty_df(["date", "driver_number", "position"])
        out = pd.DataFrame()
        out["date"] = _safe_to_datetime(self._series(df, "date"))
        out["driver_number"] = _normalize_driver_number(self._series(df, "driver_number"))
        out["position"] = _safe_to_numeric(self._series(df, "position"))
        out = out.dropna(subset=["date", "driver_number"]).sort_values(["driver_number", "date"])
        return out.reset_index(drop=True)

    def _clean_intervals(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return _empty_df(["date", "driver_number", "gap_to_leader", "interval"])
        out = pd.DataFrame()
        out["date"] = _safe_to_datetime(self._series(df, "date"))
        out["driver_number"] = _normalize_driver_number(self._series(df, "driver_number"))
        out["gap_to_leader"] = self._series(df, "gap_to_leader")
        out["interval"] = self._series(df, "interval")
        out = out.dropna(subset=["date", "driver_number"]).sort_values(["driver_number", "date"])
        return out.reset_index(drop=True)

    def _clean_race_control(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return _empty_df(["date", "category", "message"])
        out = pd.DataFrame()
        out["date"] = _safe_to_datetime(self._series(df, "date"))
        out["category"] = self._series(df, "category", "").fillna("").astype(str)
        out["message"] = self._series(df, "message", "").fillna("").astype(str)
        out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        return out

    def _clean_pit(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return _empty_df(["driver_number", "pit_in_date", "pit_out_date", "pit_duration_s"])

        in_col = self._first_existing(df, ["date_of_pit_in", "pit_in_time", "pit_in_date", "date_in"])
        out_col = self._first_existing(
            df, ["date_of_pit_out", "pit_out_time", "pit_out_date", "date_out", "date"]
        )
        event_date_col = self._first_existing(df, ["date", "pit_out_time", "pit_out_date"])
        lane_dur_col = self._first_existing(df, ["lane_duration", "pit_duration", "pit_duration_s", "duration"])
        stop_dur_col = self._first_existing(df, ["stop_duration", "pit_stop_duration", "pit_duration"])

        out = pd.DataFrame()
        out["driver_number"] = _normalize_driver_number(self._series(df, "driver_number"))
        pit_out = _safe_to_datetime(self._ensure_series(df, out_col, pd.NaT))
        event_date = _safe_to_datetime(self._ensure_series(df, event_date_col, pd.NaT))
        lane_duration_s = _normalize_duration_seconds(self._ensure_series(df, lane_dur_col, np.nan))
        stop_duration_s = _normalize_duration_seconds(self._ensure_series(df, stop_dur_col, np.nan))

        out["pit_out_date"] = pit_out.where(pit_out.notna(), event_date)
        explicit_in = _safe_to_datetime(self._ensure_series(df, in_col, pd.NaT))
        derived_in = out["pit_out_date"] - pd.to_timedelta(lane_duration_s, unit="s")
        out["pit_in_date"] = explicit_in.where(explicit_in.notna(), derived_in)
        out["pit_duration_s"] = stop_duration_s.where(stop_duration_s.notna(), lane_duration_s)
        out = out.dropna(subset=["driver_number"]).sort_values(["driver_number", "pit_in_date"])
        return out.reset_index(drop=True)

    @staticmethod
    def _infer_track_length_m(session_df: pd.DataFrame, session_id: str) -> float:
        known_lengths = {
            "monaco": 3337.0,
            "monza": 5793.0,
            "spa": 7004.0,
            "silverstone": 5891.0,
            "imola": 4909.0,
            "barcelona": 4657.0,
            "hungary": 4381.0,
            "singapore": 4940.0,
            "jeddah": 6174.0,
            "melbourne": 5278.0,
            "bahrain": 5412.0,
            "miami": 5412.0,
            "austin": 5513.0,
            "mexico": 4304.0,
            "suzuka": 5807.0,
            "las_vegas": 6201.0,
            "qatar": 5419.0,
            "abu_dhabi": 5281.0,
            "zandvoort": 4259.0,
            "interlagos": 4309.0,
            "canada": 4361.0,
            "red_bull_ring": 4318.0,
            "baku": 6003.0,
        }

        if not session_df.empty:
            for key in ("circuit_short_name", "location", "meeting_name"):
                val = session_df.iloc[0].get(key)
                if val is None:
                    continue
                name = str(val).lower().replace(" ", "_")
                for k, length in known_lengths.items():
                    if k in name:
                        return length

        # fallback based on session_id tokens
        session_token = session_id.lower()
        for k, length in known_lengths.items():
            if k in session_token:
                return length
        return np.nan

    def _map_drs_active(self, drs_series: pd.Series) -> pd.Series:
        numeric = _safe_to_numeric(drs_series)
        if numeric.dropna().empty:
            return pd.Series(np.nan, index=drs_series.index)

        non_nan = set(numeric.dropna().astype(int).unique().tolist())
        if non_nan.issubset({0, 1}):
            return (numeric == 1).astype(float)
        return numeric.astype("Int64").isin(self.drs_open_codes).astype(float)

    @staticmethod
    def _cumulative_distance_m(t_rel: pd.Series, v_mps: pd.Series) -> pd.Series:
        dt = t_rel.diff().clip(lower=0).fillna(0.0)
        v_prev = v_mps.shift(1).fillna(v_mps.fillna(0.0))
        ds = (v_prev * dt).fillna(0.0)
        return ds.cumsum()

    def _extract_mode_intervals(
        self, race_control: pd.DataFrame, session_start: pd.Timestamp
    ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        sc_intervals: list[tuple[float, float]] = []
        vsc_intervals: list[tuple[float, float]] = []
        if race_control.empty:
            return sc_intervals, vsc_intervals

        events = race_control.copy()
        events["t_rel_s"] = (events["date"] - session_start).dt.total_seconds()
        events = events.dropna(subset=["t_rel_s"]).sort_values("t_rel_s")

        sc_start: float | None = None
        vsc_start: float | None = None
        for _, row in events.iterrows():
            msg = f"{row['category']} {row['message']}".upper()
            t = float(row["t_rel_s"])

            if "VIRTUAL SAFETY CAR DEPLOYED" in msg and vsc_start is None:
                vsc_start = t
            elif ("VIRTUAL SAFETY CAR ENDING" in msg or "VIRTUAL SAFETY CAR ENDED" in msg) and (
                vsc_start is not None
            ):
                vsc_intervals.append((vsc_start, t))
                vsc_start = None

            if "SAFETY CAR DEPLOYED" in msg and "VIRTUAL" not in msg and sc_start is None:
                sc_start = t
            elif ("SAFETY CAR IN THIS LAP" in msg or "SAFETY CAR ENDED" in msg) and (
                sc_start is not None
            ):
                sc_intervals.append((sc_start, t))
                sc_start = None

        if sc_start is not None and not events.empty:
            sc_intervals.append((sc_start, float(events["t_rel_s"].max())))
        if vsc_start is not None and not events.empty:
            vsc_intervals.append((vsc_start, float(events["t_rel_s"].max())))
        return sc_intervals, vsc_intervals

    @staticmethod
    def _mark_intervals(flag_series: pd.Series, t_rel: pd.Series, intervals: list[tuple[float, float]]) -> pd.Series:
        out = flag_series.copy()
        for start, end in intervals:
            out = out | ((t_rel >= start) & (t_rel <= end))
        return out

    def _build_observation_table(
        self,
        session_id: str,
        session_start: pd.Timestamp,
        track_length_m: float,
        drivers: pd.DataFrame,
        telemetry: pd.DataFrame,
        positions: pd.DataFrame,
        intervals: pd.DataFrame,
        race_control: pd.DataFrame,
        pit_df: pd.DataFrame,
    ) -> pd.DataFrame:
        columns = [
            "session_id",
            "t_utc",
            "t_rel_s",
            "driver_number",
            "car_index",
            "lap_number",
            "lap_progress",
            "is_in_pit_lane",
            "is_under_sc",
            "is_under_vsc",
            "s_obs_m",
            "v_obs_mps",
            "a_obs_mps2",
            "s_obs_available",
            "v_obs_available",
            "a_obs_available",
            "throttle_input_pct",
            "brake_input_pct",
            "drs_input_active",
            "throttle_input_available",
            "brake_input_available",
            "drs_input_available",
            "position_obs",
            "gap_to_leader_obs_s",
            "gap_ahead_obs_s",
            "gap_behind_obs_s",
            "row_valid_for_estimation",
            "row_valid_for_prediction",
        ]
        if telemetry.empty:
            return _empty_df(columns)

        obs = telemetry.copy()
        obs["session_id"] = session_id
        obs["t_utc"] = obs["date"]
        obs["t_rel_s"] = (obs["t_utc"] - session_start).dt.total_seconds()
        obs = obs.dropna(subset=["t_rel_s"]).sort_values(["driver_number", "t_rel_s"]).reset_index(drop=True)

        car_index_lookup = dict(zip(drivers["driver_number"].astype(int), np.arange(1, len(drivers) + 1)))
        obs["car_index"] = obs["driver_number"].map(car_index_lookup).astype("Int64")

        obs["v_obs_mps"] = obs["speed"] / 3.6
        obs["a_obs_mps2"] = (
            obs.groupby("driver_number", dropna=False)["v_obs_mps"].diff()
            / obs.groupby("driver_number", dropna=False)["t_rel_s"].diff()
        )
        obs["s_obs_m"] = np.nan
        for _, idx in obs.groupby("driver_number", dropna=False).groups.items():
            g = obs.loc[idx].sort_values("t_rel_s")
            s_cum = self._cumulative_distance_m(g["t_rel_s"], g["v_obs_mps"])
            obs.loc[g.index, "s_obs_m"] = s_cum.values

        if np.isfinite(track_length_m) and track_length_m > 0:
            obs["lap_number"] = np.floor(obs["s_obs_m"] / track_length_m).astype("Int64") + 1
            obs["lap_progress"] = (obs["s_obs_m"] % track_length_m) / track_length_m
        else:
            obs["lap_number"] = pd.Series(np.nan, index=obs.index, dtype="float")
            obs["lap_progress"] = pd.Series(np.nan, index=obs.index, dtype="float")

        obs["throttle_input_pct"] = _safe_to_numeric(obs["throttle"]).clip(lower=0, upper=100)
        brake_raw = _safe_to_numeric(obs["brake"])
        if brake_raw.max(skipna=True) <= 1:
            brake_raw = brake_raw * 100.0
        obs["brake_input_pct"] = brake_raw.clip(lower=0, upper=100)
        obs["drs_input_active"] = self._map_drs_active(obs["drs"])

        obs["throttle_input_available"] = obs["throttle_input_pct"].notna()
        obs["brake_input_available"] = obs["brake_input_pct"].notna()
        obs["drs_input_available"] = obs["drs"].notna()

        obs["is_in_pit_lane"] = False
        if not pit_df.empty:
            pit_work = pit_df.copy()
            pit_work["pit_in_t_rel_s"] = (pit_work["pit_in_date"] - session_start).dt.total_seconds()
            pit_work["pit_out_t_rel_s"] = (pit_work["pit_out_date"] - session_start).dt.total_seconds()
            for _, row in pit_work.dropna(subset=["pit_in_t_rel_s", "pit_out_t_rel_s"]).iterrows():
                mask = (
                    (obs["driver_number"] == row["driver_number"])
                    & (obs["t_rel_s"] >= row["pit_in_t_rel_s"])
                    & (obs["t_rel_s"] <= row["pit_out_t_rel_s"])
                )
                obs.loc[mask, "is_in_pit_lane"] = True

        sc_intervals, vsc_intervals = self._extract_mode_intervals(race_control, session_start)
        obs["is_under_sc"] = self._mark_intervals(pd.Series(False, index=obs.index), obs["t_rel_s"], sc_intervals)
        obs["is_under_vsc"] = self._mark_intervals(
            pd.Series(False, index=obs.index), obs["t_rel_s"], vsc_intervals
        )

        obs["position_obs"] = np.nan
        if not positions.empty:
            pos = positions.copy()
            pos["t_rel_s"] = (pos["date"] - session_start).dt.total_seconds()
            for drv, idx in obs.groupby("driver_number").groups.items():
                left = obs.loc[idx, ["t_rel_s"]].sort_values("t_rel_s")
                right = pos[pos["driver_number"] == drv][["t_rel_s", "position"]].dropna().sort_values("t_rel_s")
                if right.empty:
                    continue
                merged = pd.merge_asof(
                    left,
                    right,
                    on="t_rel_s",
                    direction="nearest",
                    tolerance=2.0,
                )
                obs.loc[left.index, "position_obs"] = merged["position"].values

        obs["gap_to_leader_obs_s"] = np.nan
        obs["gap_ahead_obs_s"] = np.nan
        obs["gap_behind_obs_s"] = np.nan
        if not intervals.empty:
            itv = intervals.copy()
            itv["t_rel_s"] = (itv["date"] - session_start).dt.total_seconds()
            itv["gap_to_leader_s"] = itv["gap_to_leader"].map(_parse_gap_seconds)
            itv["gap_ahead_s"] = itv["interval"].map(_parse_gap_seconds)
            for drv, idx in obs.groupby("driver_number").groups.items():
                left = obs.loc[idx, ["t_rel_s"]].sort_values("t_rel_s")
                right = (
                    itv[itv["driver_number"] == drv][["t_rel_s", "gap_to_leader_s", "gap_ahead_s"]]
                    .dropna(subset=["t_rel_s"])
                    .sort_values("t_rel_s")
                )
                if right.empty:
                    continue
                merged = pd.merge_asof(left, right, on="t_rel_s", direction="nearest", tolerance=2.0)
                obs.loc[left.index, "gap_to_leader_obs_s"] = merged["gap_to_leader_s"].values
                obs.loc[left.index, "gap_ahead_obs_s"] = merged["gap_ahead_s"].values

            if obs["position_obs"].notna().any():
                gap_df = obs[["t_rel_s", "position_obs", "gap_ahead_obs_s"]].dropna().copy()
                gap_df["position_obs"] = _safe_to_numeric(gap_df["position_obs"])
                for t_rel, slice_df in gap_df.groupby("t_rel_s"):
                    local = slice_df.sort_values("position_obs")
                    local["gap_behind_est"] = local["gap_ahead_obs_s"].shift(-1)
                    for row_idx, row in local.iterrows():
                        obs.loc[row_idx, "gap_behind_obs_s"] = row["gap_behind_est"]

        obs["s_obs_available"] = obs["s_obs_m"].notna()
        obs["v_obs_available"] = obs["v_obs_mps"].notna()
        obs["a_obs_available"] = obs["a_obs_mps2"].notna()
        obs["row_valid_for_estimation"] = obs["s_obs_available"] & obs["v_obs_available"]
        obs["row_valid_for_prediction"] = obs["row_valid_for_estimation"] & (~obs["is_in_pit_lane"])

        obs = obs[columns].sort_values(["t_rel_s", "driver_number"]).reset_index(drop=True)
        return obs

    def _build_pit_events(
        self,
        session_id: str,
        pit_df: pd.DataFrame,
        observation_table: pd.DataFrame,
        session_start: pd.Timestamp,
    ) -> pd.DataFrame:
        columns = [
            "session_id",
            "driver_number",
            "pit_event_id",
            "pit_entry_t_rel_s",
            "pit_exit_t_rel_s",
            "pit_lane_time_s",
            "pit_stop_time_s",
            "rejoin_lap_number",
            "pit_under_sc",
            "pit_under_vsc",
            "pit_event_valid",
        ]
        if pit_df.empty:
            return _empty_df(columns)

        rows: list[dict[str, Any]] = []
        for drv, grp in pit_df.groupby("driver_number"):
            grp = grp.sort_values("pit_in_date")
            for idx, (_, row) in enumerate(grp.iterrows(), start=1):
                entry = row["pit_in_date"]
                exit_ = row["pit_out_date"]
                if pd.isna(entry) or pd.isna(exit_):
                    continue

                entry_rel = np.nan
                exit_rel = np.nan
                if pd.notna(session_start):
                    entry_rel = (entry - session_start).total_seconds()
                    exit_rel = (exit_ - session_start).total_seconds()

                lane_time = exit_rel - entry_rel if np.isfinite(entry_rel) and np.isfinite(exit_rel) else np.nan

                rejoin_row = observation_table[
                    (observation_table["driver_number"] == drv)
                    & np.isfinite(observation_table["t_rel_s"])
                ]
                if rejoin_row.empty:
                    rejoin_lap = np.nan
                    pit_sc = False
                    pit_vsc = False
                else:
                    nearest_dist = (rejoin_row["t_rel_s"] - exit_rel).abs()
                    nearest_idx = nearest_dist.idxmin()
                    if nearest_dist.loc[nearest_idx] <= 2.0:
                        nearest = rejoin_row.loc[nearest_idx]
                        rejoin_lap = nearest.get("lap_number", np.nan)
                        pit_sc = bool(nearest.get("is_under_sc", False))
                        pit_vsc = bool(nearest.get("is_under_vsc", False))
                    else:
                        rejoin_lap = np.nan
                        pit_sc = False
                        pit_vsc = False

                rows.append(
                    {
                        "session_id": session_id,
                        "driver_number": drv,
                        "pit_event_id": f"{int(drv)}_{idx}",
                        "pit_entry_t_rel_s": entry_rel,
                        "pit_exit_t_rel_s": exit_rel,
                        "pit_lane_time_s": lane_time,
                        "pit_stop_time_s": row.get("pit_duration_s", np.nan),
                        "rejoin_lap_number": rejoin_lap,
                        "pit_under_sc": pit_sc,
                        "pit_under_vsc": pit_vsc,
                        "pit_event_valid": np.isfinite(entry_rel) and np.isfinite(exit_rel),
                    }
                )

        out = pd.DataFrame(rows)
        if out.empty:
            return _empty_df(columns)
        return out[columns].sort_values(["driver_number", "pit_entry_t_rel_s"]).reset_index(drop=True)

    def _build_evaluation_targets(
        self, session_id: str, pit_events: pd.DataFrame, observation_table: pd.DataFrame
    ) -> pd.DataFrame:
        columns = [
            "session_id",
            "prediction_case_id",
            "driver_number",
            "decision_time_t_rel_s",
            "realized_rejoin_t_rel_s",
            "realized_rejoin_position",
            "realized_gap_to_leader_s",
            "realized_gap_ahead_s",
            "realized_gap_behind_s",
            "realized_s_m",
            "realized_v_mps",
            "case_valid",
        ]
        if pit_events.empty or observation_table.empty:
            return _empty_df(columns)

        rows: list[dict[str, Any]] = []
        for _, ev in pit_events.iterrows():
            drv = ev["driver_number"]
            rejoin_t = ev["pit_exit_t_rel_s"]
            decision_t = ev["pit_entry_t_rel_s"] - 1.0 if np.isfinite(ev["pit_entry_t_rel_s"]) else np.nan

            obs_drv = observation_table[observation_table["driver_number"] == drv]
            if obs_drv.empty or not np.isfinite(rejoin_t):
                continue

            nearest = obs_drv.iloc[(obs_drv["t_rel_s"] - rejoin_t).abs().argmin()]
            rows.append(
                {
                    "session_id": session_id,
                    "prediction_case_id": f"{int(drv)}_{int(round(rejoin_t))}",
                    "driver_number": drv,
                    "decision_time_t_rel_s": decision_t,
                    "realized_rejoin_t_rel_s": rejoin_t,
                    "realized_rejoin_position": nearest.get("position_obs", np.nan),
                    "realized_gap_to_leader_s": nearest.get("gap_to_leader_obs_s", np.nan),
                    "realized_gap_ahead_s": nearest.get("gap_ahead_obs_s", np.nan),
                    "realized_gap_behind_s": nearest.get("gap_behind_obs_s", np.nan),
                    "realized_s_m": nearest.get("s_obs_m", np.nan),
                    "realized_v_mps": nearest.get("v_obs_mps", np.nan),
                    "case_valid": True,
                }
            )

        out = pd.DataFrame(rows)
        if out.empty:
            return _empty_df(columns)
        return out[columns].sort_values(["driver_number", "decision_time_t_rel_s"]).reset_index(drop=True)

    @staticmethod
    def _build_quality_report(
        session_id: str,
        metadata: dict[str, Any],
        drivers: pd.DataFrame,
        observation_table: pd.DataFrame,
        pit_events: pd.DataFrame,
        evaluation_targets: pd.DataFrame,
    ) -> dict[str, Any]:
        observation_rows = len(observation_table)
        if observation_rows > 0:
            availability = {
                "s_obs_available_pct": float(observation_table["s_obs_available"].mean() * 100.0),
                "v_obs_available_pct": float(observation_table["v_obs_available"].mean() * 100.0),
                "a_obs_available_pct": float(observation_table["a_obs_available"].mean() * 100.0),
                "position_obs_available_pct": float(observation_table["position_obs"].notna().mean() * 100.0),
                "gap_to_leader_available_pct": float(
                    observation_table["gap_to_leader_obs_s"].notna().mean() * 100.0
                ),
            }
        else:
            availability = {
                "s_obs_available_pct": 0.0,
                "v_obs_available_pct": 0.0,
                "a_obs_available_pct": 0.0,
                "position_obs_available_pct": 0.0,
                "gap_to_leader_available_pct": 0.0,
            }

        return {
            "session_id": session_id,
            "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
            "data_contract_version": metadata.get("data_contract_version"),
            "counts": {
                "drivers": len(drivers),
                "observation_rows": observation_rows,
                "pit_events": len(pit_events),
                "evaluation_targets": len(evaluation_targets),
            },
            "availability_percentages": availability,
            "ready_for_estimation": bool(
                len(drivers) > 0
                and observation_rows > 0
                and observation_table["row_valid_for_estimation"].any()
            ),
        }

    def preprocess_session(self, session_id: str) -> dict[str, Any]:
        raw_dir = self.raw_root / session_id
        if not raw_dir.exists():
            raise FileNotFoundError(f"Raw directory does not exist: {raw_dir}")

        interm_dir = self.interm_root / session_id
        processed_dir = self.processed_root / session_id
        interm_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        session_df = self._load_raw_df(raw_dir, "session_selected")
        drivers_raw = self._load_raw_df(raw_dir, "drivers")
        telemetry_raw = self._load_raw_df(raw_dir, "car_data")
        positions_raw = self._load_raw_df(raw_dir, "position")
        intervals_raw = self._load_raw_df(raw_dir, "intervals")
        race_control_raw = self._load_raw_df(raw_dir, "race_control")
        pit_raw = self._load_raw_df(raw_dir, "pit")

        drivers = self._clean_drivers(drivers_raw)
        telemetry = self._clean_telemetry(telemetry_raw)
        positions = self._clean_positions(positions_raw)
        intervals = self._clean_intervals(intervals_raw)
        race_control = self._clean_race_control(race_control_raw)
        pit_df = self._clean_pit(pit_raw)

        if drivers.empty and not telemetry.empty:
            inferred = pd.DataFrame(
                {
                    "driver_number": sorted(telemetry["driver_number"].dropna().astype(int).unique().tolist()),
                    "driver_code": "",
                    "team_name": "unknown",
                }
            )
            drivers = inferred

        # Interim exports
        drivers.to_csv(interm_dir / "drivers_clean.csv", index=False)
        telemetry.to_csv(interm_dir / "telemetry_clean.csv", index=False)
        positions.to_csv(interm_dir / "position_clean.csv", index=False)
        intervals.to_csv(interm_dir / "intervals_clean.csv", index=False)
        race_control.to_csv(interm_dir / "race_control_clean.csv", index=False)
        pit_df.to_csv(interm_dir / "pit_clean.csv", index=False)
        if not session_df.empty:
            with (interm_dir / "session_selected.json").open("w", encoding="utf-8") as f:
                json.dump(session_df.iloc[0].to_dict(), f, indent=2, default=str)

        if session_df.empty:
            raise RuntimeError(f"Missing session_selected.json in {raw_dir}")

        session_row = session_df.iloc[0]
        session_start = pd.to_datetime(
            session_row.get("date_start") or session_row.get("date"), utc=True, errors="coerce"
        )
        if pd.isna(session_start):
            if telemetry.empty:
                raise RuntimeError("Cannot infer session start from raw session or telemetry data.")
            session_start = telemetry["date"].min()

        track_length_m = self._infer_track_length_m(session_df, session_id)

        observation_table = self._build_observation_table(
            session_id=session_id,
            session_start=session_start,
            track_length_m=track_length_m,
            drivers=drivers,
            telemetry=telemetry,
            positions=positions,
            intervals=intervals,
            race_control=race_control,
            pit_df=pit_df,
        )
        pit_events = self._build_pit_events(session_id, pit_df, observation_table, session_start)
        evaluation_targets = self._build_evaluation_targets(session_id, pit_events, observation_table)

        # Processed exports
        metadata = {
            "data_contract_version": "v0.2",
            "session_id": session_id,
            "year": int(session_row.get("year")) if pd.notna(session_row.get("year")) else None,
            "meeting_name": session_row.get("meeting_name"),
            "session_name": session_row.get("session_name"),
            "session_start_utc": session_start.isoformat(),
            "session_end_utc": (
                pd.to_datetime(session_row.get("date_end"), utc=True, errors="coerce").isoformat()
                if pd.notna(session_row.get("date_end"))
                else None
            ),
            "sampling_reference": "OpenF1 API pulls merged on session-relative timeline",
            "track_length_m": None if pd.isna(track_length_m) else float(track_length_m),
            "notes": "Generated by src/data_preprocessing.py",
        }

        drivers_processed = drivers.copy()
        if drivers_processed.empty:
            drivers_processed = _empty_df(
                [
                    "driver_number",
                    "driver_code",
                    "team_name",
                    "car_index",
                    "included_in_estimation",
                    "exclusion_reason",
                ]
            )
        else:
            drivers_processed["car_index"] = np.arange(1, len(drivers_processed) + 1)
            drivers_processed["included_in_estimation"] = True
            drivers_processed["exclusion_reason"] = ""

        with (processed_dir / "session_metadata.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        drivers_processed.to_csv(processed_dir / "drivers.csv", index=False)
        observation_table.to_csv(processed_dir / "observation_table.csv", index=False)
        pit_events.to_csv(processed_dir / "pit_events.csv", index=False)
        evaluation_targets.to_csv(processed_dir / "evaluation_targets.csv", index=False)
        quality_report = self._build_quality_report(
            session_id=session_id,
            metadata=metadata,
            drivers=drivers_processed,
            observation_table=observation_table,
            pit_events=pit_events,
            evaluation_targets=evaluation_targets,
        )
        with (processed_dir / "quality_report.json").open("w", encoding="utf-8") as f:
            json.dump(quality_report, f, indent=2)

        return {
            "session_id": session_id,
            "raw_dir": str(raw_dir),
            "interim_dir": str(interm_dir),
            "interm_dir": str(interm_dir),
            "processed_dir": str(processed_dir),
            "counts": {
                "drivers": len(drivers_processed),
                "observation_rows": len(observation_table),
                "pit_events": len(pit_events),
                "evaluation_targets": len(evaluation_targets),
            },
            "quality_report": quality_report,
        }
