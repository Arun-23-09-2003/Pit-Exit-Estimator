from __future__ import annotations

import argparse
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from data_collection import OpenF1DataCollector, build_session_id
from data_preprocessing import RaceDataPreprocessor


# ------------------------------------------------------------
# Default values; can be overridden with CLI args.
# ------------------------------------------------------------
YEAR = 2024
GRAND_PRIX = "monaco"
SESSION_NAME = "Race"

# Pipeline switches
COLLECT_RAW = True
BUILD_INTERM_AND_PROCESSED = True

# Optional override; default uses repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# ------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect OpenF1 race data and build estimator-ready datasets."
    )
    parser.add_argument("--year", type=int, default=YEAR, help="Race year (e.g., 2024).")
    parser.add_argument("--grand-prix", type=str, default=GRAND_PRIX, help="Grand Prix name.")
    parser.add_argument("--session-name", type=str, default=SESSION_NAME, help="Session name (e.g., race).")
    parser.add_argument(
        "--collect-raw",
        action=argparse.BooleanOptionalAction,
        default=COLLECT_RAW,
        help="Collect raw data from OpenF1 before preprocessing.",
    )
    parser.add_argument(
        "--build-processed",
        action=argparse.BooleanOptionalAction,
        default=BUILD_INTERM_AND_PROCESSED,
        help="Build interim and processed exports from existing raw data.",
    )
    parser.add_argument(
        "--interim-dir-name",
        type=str,
        default="interim",
        help="Name of the interim data directory under data/.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    session_id = build_session_id(args.year, args.grand_prix, args.session_name)

    collector = OpenF1DataCollector(project_root=PROJECT_ROOT)
    if args.collect_raw:
        session_id = collector.collect_session(
            year=args.year,
            grand_prix=args.grand_prix,
            session_name=args.session_name,
        )

    if args.build_processed:
        preprocessor = RaceDataPreprocessor(
            project_root=PROJECT_ROOT,
            interm_dir_name=args.interim_dir_name,
        )
        report = preprocessor.preprocess_session(session_id=session_id)

        print("Pipeline complete.")
        print(f"session_id: {report['session_id']}")
        print(f"raw: {report['raw_dir']}")
        print(f"interim: {report['interim_dir']}")
        print(f"processed: {report['processed_dir']}")
        print(f"counts: {report['counts']}")
        print(f"ready_for_estimation: {report['quality_report']['ready_for_estimation']}")
    else:
        print("Raw collection complete.")
        print(f"session_id: {session_id}")
        print(f"raw: {PROJECT_ROOT / 'data' / 'raw' / session_id}")


if __name__ == "__main__":
    main()
