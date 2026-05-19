from __future__ import annotations

import argparse
import fcntl
import logging
import os
import sys
from contextlib import contextmanager
from typing import Dict

import yaml

from calendar_client import CalendarColorFixer
from classifier import CategoryRule
from logging_utils import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google Family Calendar auto-color fixer")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Enable writes (overrides run.dry_run)",
    )
    parser.add_argument(
        "--print-colors",
        action="store_true",
        help="Print Google event color IDs and exit",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_rules(config: Dict) -> Dict[str, CategoryRule]:
    categories = config["classification"]["categories"]
    rules: Dict[str, CategoryRule] = {}
    for name, raw in categories.items():
        rules[name] = CategoryRule(
            name=name,
            color_id=str(raw["color_id"]),
            include_keywords=list(raw.get("include_keywords", [])),
            exclude_keywords=list(raw.get("exclude_keywords", [])),
            all_day_only=bool(raw.get("all_day_only", False)),
        )
    return rules


@contextmanager
def single_instance_lock(lock_path: str):
    lock_dir = os.path.dirname(lock_path)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)
    lock_file = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        raise RuntimeError("Another instance is already running")
    try:
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


def main() -> int:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    config = load_config(args.config)
    rules = build_rules(config)

    priority = list(config["classification"]["priority"])
    run_cfg = config.get("run", {})
    default_dry_run = bool(run_cfg.get("dry_run", True))
    dry_run = False if args.write else (True if args.dry_run else default_dry_run)

    fixer = CalendarColorFixer(
        calendar_id=config["google"]["calendar_id"],
        credentials_file=config["google"]["credentials_file"],
        token_file=config["google"]["token_file"],
        past_days=int(config["window_days"]["past"]),
        future_days=int(config["window_days"]["future"]),
        rules_by_name=rules,
        priority=priority,
        allowed_organizers=config.get("allowed_organizers"),
    )

    if args.print_colors:
        fixer.print_event_colors()
        return 0

    lock_file = run_cfg.get("lock_file", ".run/color-fixer.lock")
    try:
        with single_instance_lock(lock_file):
            stats, _changes = fixer.fix_colors(dry_run=dry_run)
    except RuntimeError as exc:
        logging.warning("%s", exc)
        return 1

    logging.info(
        (
            "Finished. dry_run=%s scanned=%s matched=%s "
            "updated=%s unchanged=%s skipped=%s cancelled=%s"
        ),
        dry_run,
        stats.scanned,
        stats.matched,
        stats.updated,
        stats.unchanged,
        stats.skipped,
        stats.cancelled,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

