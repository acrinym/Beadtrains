"""beadtrain CLI — list, status, ready, couplers, init, validate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from beadtrains.catalog import all_couplers, default_train_dir, load_train, load_trains
from beadtrains.ready import find_issues_jsonl, load_bead_status_jsonl, ready_views
from beadtrains.templates import TEMPLATES, write_template
from beadtrains.validate import main as validate_main


def _dir_from(args: argparse.Namespace) -> Path:
    return default_train_dir(Path(args.dir) if getattr(args, "dir", None) else None)


def cmd_list(args: argparse.Namespace) -> int:
    trains = load_trains(_dir_from(args))
    if not trains:
        print("no .beadtrain files")
        return 0
    print(f"{'STATUS':<12} {'CARS':>4}  NAME")
    for train in trains:
        print(f"{train.status:<12} {len(train.cars):>4}  {train.name}")
        if train.one_liner:
            print(f"               {train.one_liner}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _dir_from(args)
    target = Path(args.train)
    if target.suffix == ".beadtrain" and target.is_file():
        train = load_train(target)
    else:
        matches = [item for item in load_trains(root) if item.name == args.train]
        if not matches:
            print(f"not found: {args.train}", file=sys.stderr)
            return 2
        train = matches[0]
    print(f"{train.name}  [{train.status}]  {train.title}")
    if train.one_liner:
        print(train.one_liner)
    print()
    ids = [car.id for car in train.cars]
    for car in train.cars:
        deps = ",".join(car.depends_on) if car.depends_on else "-"
        print(f"  {car.id:<16} {car.bead:<28} {car.title}")
        print(f"    depends_on={deps}  parallel_start={car.parallel_start}")
    if train.couplers:
        print()
        print("couplers:")
        for coupler in train.couplers:
            print(
                f"  {coupler.id}: {coupler.from_train}/{coupler.from_car} "
                f"-{coupler.mode}-> {coupler.to_train}/{coupler.to_car}"
            )
    missing = [car_id for car in train.cars for car_id in car.depends_on if car_id not in ids]
    if missing:
        print("dangling depends_on:", ", ".join(missing), file=sys.stderr)
    return 0


def cmd_ready(args: argparse.Namespace) -> int:
    root = _dir_from(args)
    trains = load_trains(root)
    issues = Path(args.issues) if args.issues else find_issues_jsonl(root)
    status_map = load_bead_status_jsonl(issues) if issues else None
    have = status_map is not None
    if not have:
        print(
            "note: no issues.jsonl — not marking cars ready. Pass --issues PATH.",
            file=sys.stderr,
        )
    views = ready_views(trains, status_map)
    ready = [view for view in views if view.ready]
    if args.all:
        for view in views:
            flag = "READY" if view.ready else "WAIT "
            bead_st = view.bead_status or "?"
            print(f"{flag}  {view.train}/{view.car.id}  {view.car.bead}={bead_st}  {view.reason}")
        return 0
    if not ready:
        print("no ready cars")
        return 0
    for view in ready:
        print(f"{view.train}/{view.car.id}  {view.car.bead}  {view.car.title}")
    return 0


def cmd_couplers(args: argparse.Namespace) -> int:
    trains = load_trains(_dir_from(args))
    rows = all_couplers(trains)
    if args.train:
        rows = [
            row
            for row in rows
            if args.train in (row[1].from_train, row[1].to_train, row[0].name)
        ]
    if not rows:
        print("no couplers")
        return 0
    print(f"{'MODE':<6}  FROM                         TO")
    for _host, coupler in rows:
        left = f"{coupler.from_train}/{coupler.from_car}"
        right = f"{coupler.to_train}/{coupler.to_car}"
        print(f"{coupler.mode:<6}  {left:<28} {right}")
        if coupler.note:
            print(f"        {coupler.note}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    dest = _dir_from(args)
    try:
        written = write_template(
            dest,
            args.name,
            args.template,
            bead_prefix=args.bead_prefix,
            secondary_name=args.secondary,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for path in written:
        print(f"wrote {path}")
    print("Replace placeholder bead ids with real `bd create` ids before running the train.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beadtrain",
        description="List, inspect, and scaffold .beadtrain files. Does not replace bd.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="list trains in a directory")
    list_p.add_argument("--dir", default=None, help="folder of .beadtrain files (default: .beads or cwd)")
    list_p.set_defaults(func=cmd_list)

    status_p = sub.add_parser("status", help="show one train")
    status_p.add_argument("train", help="train name or path to .beadtrain")
    status_p.add_argument("--dir", default=None)
    status_p.set_defaults(func=cmd_status)

    ready_p = sub.add_parser("ready", help="cars whose local deps and coupler gates are open")
    ready_p.add_argument("--dir", default=None)
    ready_p.add_argument(
        "--issues",
        default=None,
        help="bd export JSONL (default: <dir>/issues.jsonl)",
    )
    ready_p.add_argument("--all", action="store_true", help="print waiting cars too")
    ready_p.set_defaults(func=cmd_ready)

    coupler_p = sub.add_parser("couplers", help="cross-train joins")
    coupler_p.add_argument("train", nargs="?", help="filter to one train name")
    coupler_p.add_argument("--dir", default=None)
    coupler_p.set_defaults(func=cmd_couplers)

    init_p = sub.add_parser("init", help="write a train from a template")
    init_p.add_argument("name", help="[train].name and filename stem")
    init_p.add_argument("--template", required=True, choices=TEMPLATES)
    init_p.add_argument("--dir", default=None)
    init_p.add_argument(
        "--bead-prefix",
        default="REPLACE-ME",
        help="placeholder prefix for car bead ids (replace with real bd ids)",
    )
    init_p.add_argument("--secondary", default=None, help="coupled template: secondary train name")
    init_p.set_defaults(func=cmd_init)

    val_p = sub.add_parser("validate", help="same as validate-beadtrain")
    val_p.add_argument("paths", nargs="+")
    val_p.set_defaults(func=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
            sys.stderr.reconfigure(errors="replace")
        except Exception:
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "validate":
        return validate_main(argv[1:])
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
