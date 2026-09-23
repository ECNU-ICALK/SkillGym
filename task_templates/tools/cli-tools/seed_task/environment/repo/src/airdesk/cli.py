from __future__ import annotations

import argparse
import json
from importlib import metadata
from pathlib import Path
from typing import Any

from . import __version__
from .data import AirportDataStore
from .release import build_release

DEFAULT_DATA_DIR = Path("/app/data/ourairports")
DEFAULT_CONTRACT = Path("/app/data/contracts/release_contract.json")
DEFAULT_OUTPUT_DIR = Path("/app/output/release")


def format_payload(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def emit_payload(payload: Any, output_format: str) -> None:
    if output_format == "json":
        print(format_payload(payload), end="")
    else:
        if isinstance(payload, str):
            print(payload, end="" if payload.endswith("\n") else "\n")
            return
        if isinstance(payload, dict):
            for key, value in payload.items():
                print(f"{key}: {value}")
            return
        print(payload)


def _installed_version() -> str:
    try:
        return metadata.version("airdesk")
    except metadata.PackageNotFoundError:
        return __version__


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="output format",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="airdesk")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))

    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("version", help="show package version")
    _add_format_argument(version_parser)

    stats_parser = subparsers.add_parser("stats", help="show dataset statistics")
    _add_format_argument(stats_parser)

    airport_parser = subparsers.add_parser("airport", help="show airport by ident")
    airport_parser.add_argument("ident")
    _add_format_argument(airport_parser)

    country_parser = subparsers.add_parser("country", help="show airports for ISO country code")
    country_parser.add_argument("iso_country")
    country_parser.add_argument("--limit", type=int, default=None)
    _add_format_argument(country_parser)

    release_parser = subparsers.add_parser("release", help="build release artifacts under output directory")
    release_parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    release_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    release_parser.add_argument(
        "--build-target",
        default="python -m airdesk release",
        help="record the workflow target used to produce the delivery",
    )
    release_parser.add_argument(
        "--require-package-lock",
        action="store_true",
        help="require the package workflow lock before generating release outputs",
    )
    _add_format_argument(release_parser)

    return parser


def render_help_text() -> str:
    return build_parser().format_help()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        emit_payload(
            {"package_name": "airdesk", "version": _installed_version()},
            args.format,
        )
        return 0

    if args.command == "release":
        manifest = build_release(
            data_dir=args.data_dir,
            contract_path=args.contract,
            output_dir=args.output_dir,
            build_target=args.build_target,
            require_package_lock=args.require_package_lock,
        )
        emit_payload(manifest, args.format)
        return 0

    try:
        store = AirportDataStore(args.data_dir)
    except FileNotFoundError as exc:
        print(str(exc))
        return 2

    if args.command == "stats":
        emit_payload(store.stats(), args.format)
        return 0

    if args.command == "airport":
        row = store.get_airport(args.ident)
        if row is None:
            print(f"airport not found: {args.ident}")
            return 1
        emit_payload(row, args.format)
        return 0

    if args.command == "country":
        rows = store.get_country_airports(args.iso_country, limit=args.limit)
        emit_payload(
            {
                "country_code": args.iso_country.strip().upper(),
                "returned": len(rows),
                "airports": rows,
            },
            args.format,
        )
        return 0

    parser.print_help()
    return 2
