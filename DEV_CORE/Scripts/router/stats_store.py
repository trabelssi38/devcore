"""Bounded atomic legacy usage snapshot; cooperative local writers, no waiting or retry."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import threading

MAX_BYTES = 1024 * 1024
MAX_TASKS = 4096
MAX_COUNTER = (1 << 63) - 1
_LOCK = threading.Lock()


@contextmanager
def usage_file_lock(path):
    """Lock a stable sidecar, never the snapshot inode replaced by publication."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + '.lock')
    with lock_path.open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError('Usage store busy') from exc
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError('Usage store busy') from exc
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    # Keep the sidecar: unlinking it can split writers across two lock inodes.


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', value) is not None


def counter(value):
    return type(value) is int and 0 <= value <= MAX_COUNTER


def read_stats(path):
    path = Path(path)
    try:
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return {'tasks': {}, 'total_tokens': 0}
    if len(raw) > MAX_BYTES:
        raise ValueError('Oversized usage snapshot')
    try:
        result = json.loads(raw.decode('utf-8-sig'))
    except (ValueError, RecursionError) as exc:
        raise ValueError('Invalid usage snapshot') from exc
    if not isinstance(result, dict) or not isinstance(result.get('tasks'), dict):
        raise ValueError('Invalid usage snapshot')
    tasks = result['tasks']
    if len(tasks) > MAX_TASKS:
        raise ValueError('Too many usage tasks')
    total = 0
    for task_id, task in tasks.items():
        if not identifier(task_id) or not isinstance(task, dict) or not identifier(task.get('mode')):
            raise ValueError('Invalid usage task')
        if not all(counter(task.get(key)) for key in ('tokens_in', 'tokens_out', 'total_tokens', 'calls')):
            raise ValueError('Invalid usage counters')
        if task['total_tokens'] != task['tokens_in'] + task['tokens_out']:
            raise ValueError('Inconsistent usage counters')
        total += task['total_tokens']
    if not counter(result.get('total_tokens')) or result['total_tokens'] != total:
        raise ValueError('Inconsistent usage total')
    return result


def update_stats(path, task_id, mode, prompt_tokens, completion_tokens):
    if not identifier(task_id) or not identifier(mode) or not counter(prompt_tokens) or not counter(completion_tokens):
        raise ValueError('Invalid usage update')
    if not _LOCK.acquire(blocking=False):
        raise ValueError('Usage store busy')
    temporary = None
    try:
        path = Path(path)
        with usage_file_lock(path):
            stats = read_stats(path)
            tasks = stats['tasks']
            if task_id not in tasks:
                if len(tasks) >= MAX_TASKS:
                    raise ValueError('Usage task capacity reached')
                tasks[task_id] = {'tokens_in': 0, 'tokens_out': 0, 'total_tokens': 0, 'calls': 0, 'mode': mode}
            task = tasks[task_id]
            task['tokens_in'] += prompt_tokens
            task['tokens_out'] += completion_tokens
            task['total_tokens'] += prompt_tokens + completion_tokens
            task['calls'] += 1
            task['mode'] = mode
            stats['total_tokens'] += prompt_tokens + completion_tokens
            if not all(counter(task[key]) for key in ('tokens_in', 'tokens_out', 'total_tokens', 'calls')) or not counter(stats['total_tokens']):
                raise ValueError('Usage counter capacity reached')
            raw = json.dumps(stats, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            if len(raw) > MAX_BYTES:
                raise ValueError('Usage snapshot capacity reached')
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
            return task['total_tokens']
    finally:
        try:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        finally:
            _LOCK.release()
