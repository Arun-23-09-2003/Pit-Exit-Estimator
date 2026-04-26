from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from data_collection import OpenF1DataCollector, build_session_id
from data_preprocessing import RaceDataPreprocessor


DEFAULT_YEAR = 2024
DEFAULT_SESSION_NAME = "Race"
DEFAULT_GRAND_PRIXES = [
    "bahrain",
    "monaco",
    "silverstone",
    "spa",
    "abu dhabi",
]
ALIASES = {
    "abu dabhi": "abu dhabi",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", lowered)
    return cleaned.strip("_")


def _normalize_gp_name(name: str) -> str:
    key = _slugify(name).replace("_", " ")
    return ALIASES.get(key, key)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch collect and preprocess OpenF1 sessions."
    )
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--session-name", type=str, default=DEFAULT_SESSION_NAME)
    parser.add_argument(
        "--grand-prixes",
        nargs="+",
        default=DEFAULT_GRAND_PRIXES,
        help="List of grand prix names. Example: --grand-prixes bahrain monaco spa",
    )
    parser.add_argument(
        "--interim-dir-name",
        type=str,
        default="interim",
        help="Name of the interim data directory under data/.",
    )
    parser.add_argument(
        "--continue-on-error",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Continue remaining sessions even if one fails.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    collector = OpenF1DataCollector(project_root=PROJECT_ROOT)
    preprocessor = RaceDataPreprocessor(
        project_root=PROJECT_ROOT,
        interm_dir_name=args.interim_dir_name,
    )

    grand_prixes = [_normalize_gp_name(gp) for gp in args.grand_prixes]
    results: list[dict[str, Any]] = []
    failures = 0

    for gp in grand_prixes:
        session_id = build_session_id(args.year, gp, args.session_name)
        print(f"[START] {gp} -> {session_id}")
        try:
            collected_session_id = collector.collect_session(
                year=args.year,
                grand_prix=gp,
                session_name=args.session_name,
            )
            report = preprocessor.preprocess_session(session_id=collected_session_id)
            result = {
                "grand_prix": gp,
                "session_id": collected_session_id,
                "status": "ok",
                "counts": report["counts"],
                "ready_for_estimation": report["quality_report"]["ready_for_estimation"],
                "raw_dir": report["raw_dir"],
                "interim_dir": report["interim_dir"],
                "processed_dir": report["processed_dir"],
            }
            print(
                f"[OK] {gp}: rows={report['counts']['observation_rows']} "
                f"pit_events={report['counts']['pit_events']} "
                f"ready={report['quality_report']['ready_for_estimation']}"
            )
        except Exception as exc:
            failures += 1
            result = {
                "grand_prix": gp,
                "session_id": session_id,
                "status": "failed",
                "error": str(exc),
            }
            print(f"[FAILED] {gp}: {exc}")
            if not args.continue_on_error:
                results.append(result)
                break
        results.append(result)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "year": args.year,
        "session_name": args.session_name,
        "grand_prixes_requested": grand_prixes,
        "successful_sessions": sum(1 for r in results if r.get("status") == "ok"),
        "failed_sessions": failures,
        "results": results,
    }

    summary_dir = PROJECT_ROOT / "data" / "processed"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"batch_summary_{args.year}_{_slugify(args.session_name)}.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[SUMMARY] {summary_path}")
    print(f"[SUMMARY] success={summary['successful_sessions']} failed={summary['failed_sessions']}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
