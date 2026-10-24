"""Command line entry points.

funderready demo                                   # generate + load a synthetic charity
funderready demo --seed 11 --org "Holdout 11"      # a different charity, for holdout checks
funderready generate --out data/demo --seed 7      # just write the messy CSVs
funderready load --org "Leith Community Sports" --folder data/demo
funderready load --org "..." --sheet signups=<sheet-id>:<gid> --sheet sessions=...
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from funderready import generator
from funderready.loader import SHEETS, csv_folder_rows, dataset_name, load_org
from funderready.pseudonymise import Pseudonymiser
from funderready.sources import read_google_sheet

DEMO_ORG = "Leith Community Sports"
DEMO_KEY = "demo-key-not-for-real-data-0001"


def _pseudonymiser(allow_demo_key: bool) -> Pseudonymiser:
    key = os.environ.get("FUNDERREADY_PSEUDO_KEY")
    if not key:
        if not allow_demo_key:
            sys.exit("Set FUNDERREADY_PSEUDO_KEY (16+ characters) before loading real data.")
        key = DEMO_KEY
    return Pseudonymiser(key)


def cmd_generate(args: argparse.Namespace) -> int:
    ds = generator.generate(seed=args.seed)
    paths = generator.write(ds, Path(args.out))
    print(f"Wrote {len(paths)} sheets and {len(ds.planted)} planted issues to {args.out}")
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    if args.sheet:
        sheets = {}
        for spec in args.sheet:
            name, _, ref = spec.partition("=")
            sheet_id, _, gid = ref.partition(":")
            sheets[name] = read_google_sheet(sheet_id, gid or "0")
        missing = set(SHEETS) - set(sheets)
        if missing:
            sys.exit(f"Missing --sheet for: {', '.join(sorted(missing))}")
    else:
        sheets = csv_folder_rows(Path(args.folder))
    info = load_org(args.org, sheets, _pseudonymiser(allow_demo_key=args.demo))
    print(info)
    print(f"Loaded into schema {dataset_name(args.org)}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    out = Path(args.out)
    cmd_generate(argparse.Namespace(seed=args.seed, out=out))
    return cmd_load(argparse.Namespace(org=args.org, folder=out, sheet=None, demo=True))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(prog="funderready")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("generate", help="Write a synthetic messy charity dataset")
    p.add_argument("--out", default="data/demo")
    p.add_argument("--seed", type=int, default=7)
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("load", help="Pseudonymise and load one organisation")
    p.add_argument("--org", required=True)
    p.add_argument("--folder", default="data/demo", help="Folder of <sheet>.csv files")
    p.add_argument("--sheet", action="append", help="name=<google-sheet-id>[:<gid>]")
    p.add_argument("--demo", action="store_true", help="Allow the built-in demo key")
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("demo", help="Generate and load the synthetic demo organisation")
    p.add_argument("--out", default="data/demo")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--org", default=DEMO_ORG, help="Organisation name for the synthetic data")
    p.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
