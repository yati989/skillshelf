"""Command-line interface for the global approval-gated personal profile."""

import argparse
import json
import sys
from pathlib import Path

from .personal_context import PersonalContextStore


def _json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parser():
    result = argparse.ArgumentParser(prog="personal-context")
    result.add_argument("--root", type=Path, help="Override the global profile root")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("export-markdown", help="Export the approved narrative without generating new wording")
    listing = commands.add_parser("list")
    listing.add_argument("--category")
    listing.add_argument("--scope")
    get = commands.add_parser("get")
    get.add_argument("key")
    propose = commands.add_parser("propose")
    propose.add_argument("payload", type=Path)
    approve = commands.add_parser("approve")
    approve.add_argument("proposal_id")
    approve.add_argument("--key", action="append")
    reject = commands.add_parser("reject")
    reject.add_argument("proposal_id")
    reject.add_argument("--reason", required=True)
    reject.add_argument("--key", action="append")
    no_change = commands.add_parser("record-no-change")
    no_change.add_argument("payload", type=Path)
    imported = commands.add_parser("import-approved")
    imported.add_argument("payload", type=Path)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    profile = PersonalContextStore(args.root)
    try:
        if args.command == "init":
            output = profile.initialize()
        elif args.command == "export-markdown":
            output = profile.export_markdown()
        elif args.command == "list":
            output = profile.index(args.category, args.scope)
        elif args.command == "get":
            output = profile.get(args.key)
        elif args.command == "propose":
            output = profile.propose(_json(args.payload))
        elif args.command == "approve":
            output = profile.approve(args.proposal_id, args.key)
        elif args.command == "reject":
            output = profile.reject(args.proposal_id, args.reason, args.key)
        elif args.command == "record-no-change":
            payload = _json(args.payload)
            output = profile.record_no_change(payload["source"], payload["reason"])
        elif args.command == "import-approved":
            payload = _json(args.payload)
            output = profile.apply_approved_facts(payload["facts"], payload["source"])
        else:
            raise AssertionError("Unhandled command")
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
