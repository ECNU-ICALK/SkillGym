from __future__ import annotations

import argparse
import json
from typing import Any

from .reporting import classifier_prefix, license_lookup, snapshot


def _dump(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pkgmeta-kit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("snapshot")

    license_parser = subparsers.add_parser("license")
    license_parser.add_argument("license_id")

    classifier_parser = subparsers.add_parser("classifier-prefix")
    classifier_parser.add_argument("prefix")
    classifier_parser.add_argument("--limit", type=int, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "snapshot":
        _dump(snapshot())
        return 0
    if args.command == "license":
        _dump(license_lookup(args.license_id))
        return 0
    if args.command == "classifier-prefix":
        _dump(classifier_prefix(args.prefix, args.limit))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
