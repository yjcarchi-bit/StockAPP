"""CLI entrypoint for migrating legacy PKL cache into MySQL."""

from __future__ import annotations

import argparse
import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

from app.services.pkl_migration import migrate_pkl_cache


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy pkl cache files into MySQL daily_bars")
    parser.add_argument("--cache-dir", default=os.path.join(PROJECT_ROOT, "data", ".cache"), help="PKL cache directory")
    parser.add_argument(
        "--resume-file",
        default=os.path.join(BACKEND_DIR, "scripts", ".migrate_pkl_state.json"),
        help="Resume state file path",
    )
    parser.add_argument("--force", action="store_true", help="Reprocess files even if state says processed")
    args = parser.parse_args()

    result = migrate_pkl_cache(cache_dir=args.cache_dir, resume_file=args.resume_file, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
