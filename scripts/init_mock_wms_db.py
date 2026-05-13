#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mock_wms_db_common import default_db_path, initialize_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Initialize the minimal SQLite database for the V3.0 Mock WMS data layer.'
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=default_db_path(),
        help='SQLite database path. Defaults to data/mock_wms.db under the repo root.',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_path = initialize_database(args.db_path)
    print(f'[mock_wms_db] Initialized tasks table at: {db_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
