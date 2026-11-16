#!/usr/bin/env python3
"""Append-only course records and resumable checkpoints; Python standard library only."""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = 1
KINDS = {
    'source', 'source-set', 'source-status', 'approval', 'placement', 'plan',
    'lesson', 'assignment', 'assessment', 'attempt', 'result', 'ability',
    'review', 'session', 'decision',
}
PHASES = {'setup', 'research', 'planning', 'lesson', 'assessment', 'review',
          'paused', 'course-complete'}
MODES = {'coaching', 'conversation', 'assessment', 'text'}
EVIDENCE = {'live_audio', 'audio_recording', 'transcript', 'typed',
            'learner_report', 'none'}
ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    with open(path, encoding='utf-8') as stream:
        return json.load(stream)


def course_path(value):
    path = Path(value).expanduser().resolve()
    skill = Path(__file__).resolve().parents[1]
    require(path != skill and skill not in path.parents,
            'Learner data must live outside the installed skill.')
    return path


@contextmanager
def lock(path):
    with open(path / '.course.lock', 'a', encoding='utf-8') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Another writer is saving this course; reread and retry.') from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def atomic_json(path, value):
    """Replace one complete document; a failed write leaves the previous file intact."""
    descriptor, temporary = tempfile.mkstemp(prefix='.course-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def project(document):
    require(document.get('schema_version') == SCHEMA, 'Unsupported course schema.')
    require(isinstance(document.get('events'), list), 'Invalid event history.')
    state = {'revision': len(document['events']), 'config': document['config'],
             'records': {}, 'checkpoint': None, 'activity_checkpoints': {}}
    for event in document['events']:
        if event['type'] == 'record':
            kind, identifier = event['kind'], event['id']
            records = state['records'].setdefault(kind, {})
            require(identifier not in records, 'Duplicate record in saved history.')
            records[identifier] = event
        elif event['type'] == 'checkpoint':
            state['checkpoint'] = event
            activity = event['data'].get('activity_id')
            if activity:
                state['activity_checkpoints'][activity] = event
        else:
            raise ValueError('Unknown saved event type.')
    return state


def lookup(state, kind, identifier):
    return state['records'].get(kind, {}).get(identifier)


def approved(state, kind, identifier):
    decisions = [item['data']['decision']
                 for item in state['records'].get('approval', {}).values()
                 if item['data']['target_kind'] == kind
                 and item['data']['target_id'] == identifier]
    return bool(decisions) and decisions[-1] == 'approved'


def validate_record(event, state):
    require(set(event) == {'type', 'kind', 'id', 'data'},
            'A record needs exactly type, kind, id, data.')
    kind, identifier, data = event['kind'], event['id'], event['data']
    require(isinstance(kind, str) and kind in KINDS, 'Unknown record kind.')
    require(isinstance(identifier, str) and ID.fullmatch(identifier), 'Invalid record ID.')
    require(isinstance(data, dict) and bool(data), 'Record data must be a nonempty object.')
    require(not lookup(state, kind, identifier),
            'Record already exists; use a new ID and supersedes, never overwrite.')
    if 'supersedes' in data:
        require(lookup(state, kind, data['supersedes']), 'supersedes must reference the same kind.')
    if kind == 'source-set':
        sources = data.get('source_ids')
        require(isinstance(sources, list) and sources, 'source-set needs source_ids.')
        require(all(isinstance(s, str) and lookup(state, 'source', s) for s in sources),
                'source-set references a missing source.')
    if kind == 'plan':
        require(lookup(state, 'source-set', data.get('source_set_id', '')),
                'A plan needs an existing source_set_id.')
    if kind == 'approval':
        target_kind, target_id = data.get('target_kind'), data.get('target_id')
        require(target_kind in {'source', 'source-set', 'plan'}, 'Invalid approval target kind.')
        target = lookup(state, target_kind, target_id)
        require(target, 'Approval target does not exist.')
        require(data.get('decision') in {'approved', 'rejected', 'deferred'}, 'Invalid decision.')
        require(nonempty(data.get('learner_evidence')), 'Record the actual learner approval/decision.')
        if data['decision'] == 'approved' and target_kind == 'source-set':
            require(all(approved(state, 'source', s) for s in target['data']['source_ids']),
                    'Every source needs individual approval first.')
        if data['decision'] == 'approved' and target_kind == 'plan':
            require(approved(state, 'source-set', target['data']['source_set_id']),
                    'The plan source set must be approved first.')


def validate_checkpoint(event, state):
    require(set(event) == {'type', 'data'}, 'A checkpoint needs exactly type and data.')
    data = event['data']
    require(isinstance(data, dict), 'Checkpoint data must be an object.')
    require(data.get('phase') in PHASES, 'Invalid phase.')
    require(data.get('mode') in MODES, 'Invalid mode.')
    require(data.get('evidence_type') in EVIDENCE, 'Invalid evidence_type.')
    require(nonempty(data.get('next_step')), 'Checkpoint needs a concrete next_step.')
    activity = data.get('activity_id')
    require(activity is None or (isinstance(activity, str) and ID.fullmatch(activity)),
            'Invalid activity_id.')
    if data['phase'] in {'lesson', 'assessment', 'review', 'course-complete'}:
        plan_id = data.get('plan_id')
        require(lookup(state, 'plan', plan_id) and approved(state, 'plan', plan_id),
                'Teaching/practice needs an explicitly approved plan_id.')
    if data['phase'] == 'assessment':
        require(activity, 'Assessment needs an activity_id for its independent checkpoint.')
        require(lookup(state, 'assessment', data.get('assessment_id')),
                'Assessment checkpoint needs an existing assessment_id.')


def initialize(path, config):
    require(isinstance(config, dict), 'Config must be an object.')
    for field in ('course_id', 'language', 'variety', 'explanation_language'):
        require(nonempty(config.get(field)), f'Config needs {field}.')
    require(ID.fullmatch(config['course_id']), 'Invalid course_id.')
    require(isinstance(config.get('goals'), list) and config['goals']
            and all(nonempty(item) for item in config['goals']), 'Config needs a nonempty goals list.')
    path.mkdir(parents=True, exist_ok=True)
    with lock(path):
        require(not (path / 'course.json').exists(), 'Course already exists; show/resume it.')
        document = {'schema_version': SCHEMA, 'created_at': now(),
                    'config': config, 'events': []}
        atomic_json(path / 'course.json', document)
    return project(document)


def save(path, payload, expected_revision):
    events = payload if isinstance(payload, list) else [payload]
    require(bool(events), 'Empty event batch.')
    with lock(path):
        document = read_json(path / 'course.json')
        require(len(document['events']) == expected_revision,
                'Revision changed; show the course, reconcile, and retry. Nothing saved.')
        updated = copy.deepcopy(document)
        for event in events:
            state = project(updated)
            require(isinstance(event, dict), 'Event must be an object.')
            if event.get('type') == 'record':
                validate_record(event, state)
            elif event.get('type') == 'checkpoint':
                validate_checkpoint(event, state)
            else:
                raise ValueError('Event type must be record or checkpoint.')
            stored = copy.deepcopy(event)
            stored['sequence'] = len(updated['events']) + 1
            stored['saved_at'] = now()
            updated['events'].append(stored)
        atomic_json(path / 'course.json', updated)
    return project(updated)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--course', required=True, help='Explicit course directory, outside the skill.')
    sub = parser.add_subparsers(dest='command', required=True)
    init_parser = sub.add_parser('init')
    init_parser.add_argument('--config', required=True, help='Config JSON file.')
    save_parser = sub.add_parser('save')
    save_parser.add_argument('--event', required=True, help='Event or atomic event-list JSON file.')
    save_parser.add_argument('--expected-revision', required=True, type=int)
    show_parser = sub.add_parser('show')
    show_parser.add_argument('--history', action='store_true')
    show_parser.add_argument('--kind', choices=sorted(KINDS))
    show_parser.add_argument('--id')
    args = parser.parse_args()
    try:
        path = course_path(args.course)
        if args.command == 'init':
            result = initialize(path, read_json(args.config))
        elif args.command == 'save':
            state = save(path, read_json(args.event), args.expected_revision)
            result = {'saved': True, 'revision': state['revision'], 'checkpoint': state['checkpoint']}
        else:
            require(not args.id or args.kind, '--id requires --kind.')
            require(not args.history or (not args.kind and not args.id),
                    '--history cannot be combined with record filters.')
            document = read_json(path / 'course.json')
            state = project(document)
            if args.history:
                result = document
            elif args.kind:
                result = state['records'].get(args.kind, {})
                if args.id:
                    require(args.id in result, 'Record not found.')
                    result = result[args.id]
            else:
                result = state
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
