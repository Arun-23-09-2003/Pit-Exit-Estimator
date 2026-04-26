from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", lowered)
    return cleaned.strip("_")


def build_session_id(year: int, grand_prix: str, session_name: str) -> str:
    return f"{year}_{_slugify(grand_prix)}_{_slugify(session_name)}"


@dataclass
class OpenF1DataCollector:
    project_root: Path
    base_url: str = "https://api.openf1.org/v1"
    timeout_s: int = 30
    max_retries: int = 3
    retry_backoff_s: float = 1.5

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root)
        self.raw_root = self.project_root / "data" / "raw"
        self.raw_root.mkdir(parents=True, exist_ok=True)

    def _read_json_response(self, endpoint: str, params: dict[str, Any]) -> Any:
        clean_params = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base_url}/{endpoint}?{urlencode(clean_params)}"
        request = Request(url, headers={"User-Agent": "pit-exit-estimator/0.1"})

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout_s) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                # OpenF1 may return 404 for valid endpoints when a filter has no rows.
                if exc.code == 404:
                    return []
                last_error = exc
                if attempt == self.max_retries:
                    break
                time.sleep(self.retry_backoff_s * attempt)
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                time.sleep(self.retry_backoff_s * attempt)

        raise RuntimeError(
            f"OpenF1 request failed for endpoint='{endpoint}' params={clean_params}: {last_error}"
        ) from last_error

    def _http_get(self, endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        payload = self._read_json_response(endpoint=endpoint, params=params)
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []

    def _collect_car_data(self, session_key: Any, drivers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        driver_numbers: list[int] = []
        for row in drivers:
            value = row.get("driver_number")
            if value is None:
                continue
            try:
                driver_numbers.append(int(value))
            except (TypeError, ValueError):
                continue
        driver_numbers = sorted(set(driver_numbers))

        if not driver_numbers:
            return self._http_get("car_data", {"session_key": session_key})

        telemetry_rows: list[dict[str, Any]] = []
        for driver_number in driver_numbers:
            rows = self._http_get(
                "car_data",
                {"session_key": session_key, "driver_number": driver_number},
            )
            telemetry_rows.extend(rows)

        if not telemetry_rows:
            return telemetry_rows

        deduped = {
            (str(row.get("date")), row.get("driver_number"), row.get("meeting_key")): row
            for row in telemetry_rows
            if isinstance(row, dict)
        }
        return list(deduped.values())

    @staticmethod
    def _extract_datetime(session_obj: dict[str, Any]) -> datetime:
        value = session_obj.get("date_start") or session_obj.get("date")
        if value is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        text = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    def _select_session(
        self, sessions: list[dict[str, Any]], grand_prix: str, session_name: str
    ) -> dict[str, Any]:
        gp_slug = _slugify(grand_prix)
        session_slug = _slugify(session_name)

        def score(candidate: dict[str, Any]) -> tuple[int, datetime]:
            fields = " ".join(
                str(candidate.get(k, ""))
                for k in (
                    "meeting_name",
                    "location",
                    "country_name",
                    "circuit_short_name",
                    "session_name",
                    "session_type",
                )
            )
            fields_slug = _slugify(fields)
            session_field = _slugify(str(candidate.get("session_name", "")))

            points = 0
            if gp_slug and gp_slug in fields_slug:
                points += 2
            if session_slug and session_slug == session_field:
                points += 2
            return points, self._extract_datetime(candidate)

        ranked = sorted(sessions, key=score, reverse=True)
        return ranked[0] if ranked else {}

    def discover_session(self, year: int, grand_prix: str, session_name: str) -> dict[str, Any]:
        sessions = self._http_get("sessions", {"year": year, "session_name": session_name})
        if not sessions:
            sessions = self._http_get("sessions", {"year": year})
        selected = self._select_session(sessions, grand_prix, session_name)
        if not selected:
            raise RuntimeError(
                f"No OpenF1 session found for year={year}, grand_prix='{grand_prix}', session='{session_name}'."
            )
        return selected

    def _collect_payloads(
        self,
        session_key: Any,
        meeting_key: Any,
        year: int,
        drivers: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        specs: list[tuple[str, str, dict[str, Any]]] = [
            ("sessions_same_year", "sessions", {"year": year}),
            ("position", "position", {"session_key": session_key}),
            ("intervals", "intervals", {"session_key": session_key}),
            ("laps", "laps", {"session_key": session_key}),
            ("race_control", "race_control", {"session_key": session_key, "meeting_key": meeting_key}),
            ("pit", "pit", {"session_key": session_key}),
            ("weather", "weather", {"session_key": session_key}),
        ]

        payloads: dict[str, list[dict[str, Any]]] = {"drivers": drivers}
        payloads["car_data"] = self._collect_car_data(session_key=session_key, drivers=drivers)
        for file_stem, endpoint, params in specs:
            payloads[file_stem] = self._http_get(endpoint=endpoint, params=params)
        return payloads

    @staticmethod
    def _quality_flags(payloads: dict[str, list[dict[str, Any]]]) -> dict[str, bool]:
        return {
            "has_drivers": bool(payloads.get("drivers")),
            "has_car_data": bool(payloads.get("car_data")),
            "has_position": bool(payloads.get("position")),
            "has_intervals": bool(payloads.get("intervals")),
            "has_pit": bool(payloads.get("pit")),
        }

    def collect_session(self, year: int, grand_prix: str, session_name: str = "Race") -> str:
        session = self.discover_session(year, grand_prix, session_name)
        session_id = build_session_id(year, grand_prix, session_name)

        session_key = session.get("session_key")
        meeting_key = session.get("meeting_key")

        out_dir = self.raw_root / session_id
        out_dir.mkdir(parents=True, exist_ok=True)

        drivers = self._http_get("drivers", {"session_key": session_key})
        payloads = self._collect_payloads(
            session_key=session_key,
            meeting_key=meeting_key,
            year=year,
            drivers=drivers,
        )
        payloads["session_selected"] = [session]

        for name, rows in payloads.items():
            with (out_dir / f"{name}.json").open("w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)

        quality_flags = self._quality_flags(payloads)
        manifest = {
            "session_id": session_id,
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
            "base_url": self.base_url,
            "collector_settings": {
                "timeout_s": self.timeout_s,
                "max_retries": self.max_retries,
                "retry_backoff_s": self.retry_backoff_s,
            },
            "row_counts": {name: len(rows) for name, rows in payloads.items()},
            "quality_flags": quality_flags,
            "selected_session": {
                "meeting_name": session.get("meeting_name"),
                "session_name": session.get("session_name"),
                "session_key": session_key,
                "meeting_key": meeting_key,
            },
        }
        with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        warnings: list[str] = []
        for flag_name, flag_value in quality_flags.items():
            if not flag_value:
                warnings.append(f"Missing or empty dataset: {flag_name}")
        report = {
            "session_id": session_id,
            "raw_dir": str(out_dir),
            "warnings": warnings,
        }
        with (out_dir / "collection_report.json").open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return session_id
