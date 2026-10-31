"""Print the GeoCase catalog as JSON for the plugin's skills (Plan 55).

Run with the user's own Python, the one their tests use::

    python catalog.py cases [--category C] [--geometry-type G] [--format F]
                            [--risk TERM ...] [--tag TAG ...]
    python catalog.py case <case_id>
    python catalog.py risks

It reads the catalog through the installed ``geocase`` package and touches
only ``geocase.__all__``, so it works against any release that keeps the v1.0
promise, not only this repo. Standard library plus ``geocase``.

Exit codes: 0 on success, 2 for a bad request (unknown case id, bad filter),
3 when ``geocase`` is not importable.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

INSTALL_HINT = (
    "geocase is not importable from this Python ({python}).\n"
    "Install it into the environment your tests use: pip install geocase"
)


def _summary(meta: Any) -> dict[str, Any]:
    return {
        "id": meta.id,
        "title": meta.title,
        "category": meta.category,
        "format": meta.format,
        "geometry_type": meta.geometry_type,
        "risk_types": list(meta.risk_types),
    }


def _cases(geocase: Any, args: argparse.Namespace) -> Any:
    found = geocase.list_cases(
        category=args.category,
        geometry_type=args.geometry_type,
        format=args.format,
        risk_types_any=args.risk or None,
        tags_any=args.tag or None,
    )
    return [_summary(meta) for meta in found]


def _case(geocase: Any, args: argparse.Namespace) -> Any:
    try:
        meta = geocase.get_case(args.case_id)
    except KeyError:
        raise ValueError(f"unknown case id: {args.case_id}") from None
    record = meta.model_dump(mode="json")
    record["notes"] = None
    try:
        notes_path = geocase.load_case(meta.id).notes_path
    except geocase.RemoteCaseUnavailableError:
        notes_path = None
    if notes_path is not None and notes_path.is_file():
        record["notes"] = notes_path.read_text(encoding="utf-8")
    return record


def _risks(geocase: Any, args: argparse.Namespace) -> Any:
    return geocase.risk_types()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    cases = commands.add_parser("cases", help="list cases, optionally filtered")
    cases.add_argument("--category", help="vector, raster or netcdf")
    cases.add_argument("--geometry-type", help="e.g. Polygon, Point")
    cases.add_argument("--format", help="e.g. geojson, geotiff")
    cases.add_argument(
        "--risk",
        action="append",
        help="risk type or family (e.g. crs/axis_order, crs); repeat for any-of",
    )
    cases.add_argument("--tag", action="append", help="tag; repeat for any-of")
    cases.set_defaults(handler=_cases)

    case = commands.add_parser("case", help="one case's metadata and notes")
    case.add_argument("case_id")
    case.set_defaults(handler=_case)

    risks = commands.add_parser("risks", help="risk type -> case ids")
    risks.set_defaults(handler=_risks)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        import geocase
    except ImportError:
        print(INSTALL_HINT.format(python=sys.executable), file=sys.stderr)
        return 3
    try:
        result = args.handler(geocase, args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
