"""Command-line operations for the conversational reading workspace."""

import argparse
import json
import sys
from pathlib import Path

from .reading import ReadingWorkspace


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--root', type=Path, required=True,
                        help='Shared .kb-workspace directory')
    commands = result.add_subparsers(dest='command', required=True)
    for name in ('init', 'context', 'resources'):
        commands.add_parser(name)
    ingest = commands.add_parser('ingest', help='Prepare a supplied local resource')
    ingest.add_argument('path', type=Path)
    ingest.add_argument('--title', required=True)
    ingest.add_argument('--source-id')
    ingest.add_argument('--author')
    reuse = commands.add_parser('reuse', help='Link an existing tutor extraction')
    reuse.add_argument('path', type=Path)
    search = commands.add_parser('search', help='Find passages with source locations')
    search.add_argument('query')
    search.add_argument('--source-id')
    search.add_argument('--limit', type=int, default=3)
    read = commands.add_parser('read', help='Read a bounded source or section')
    read.add_argument('source_id')
    read.add_argument('--section')
    read.add_argument('--source-hash')
    read.add_argument('--max-chars', type=int, default=16000)
    review = commands.add_parser('review', help='Record completed extraction inspection')
    review.add_argument('source_id')
    review.add_argument('--reason', required=True)
    note = commands.add_parser('save-note', help='Save a cited session, wiki, or self note')
    note.add_argument('payload', type=Path)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    workspace = ReadingWorkspace(args.root)
    try:
        if args.command == 'init':
            result = workspace.initialize()
        elif args.command == 'context':
            result = workspace.context()
        elif args.command == 'resources':
            result = workspace.resources()
        elif args.command == 'ingest':
            result = workspace.ingest(args.path, args.title, args.source_id, args.author)
        elif args.command == 'reuse':
            result = workspace.reuse(args.path)
        elif args.command == 'search':
            if not 1 <= args.limit <= 20:
                raise ValueError('limit must be between 1 and 20')
            result = workspace.search(args.query, args.source_id, args.limit)
        elif args.command == 'read':
            if not 1 <= args.max_chars <= 100000:
                raise ValueError('max-chars must be between 1 and 100000')
            result = workspace.read(args.source_id, args.section, args.max_chars,
                                    args.source_hash)
        elif args.command == 'review':
            result = workspace.review(args.source_id, args.reason)
        elif args.command == 'save-note':
            with args.payload.open(encoding='utf-8') as stream:
                payload = json.load(stream)
            if not isinstance(payload, dict):
                raise ValueError('Note payload must be a JSON object')
            result = workspace.save_note(payload)
        else:
            raise AssertionError('Unhandled command')
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
