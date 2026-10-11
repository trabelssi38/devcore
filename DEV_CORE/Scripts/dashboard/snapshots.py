"""Committed dashboard generations. Caller serializes writers with DashboardLock."""
from contextlib import contextmanager, ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from .publication import atomic_write_text
from .generation_lock import DashboardLock

NAMES = {'dashboard_payload.json', 'payload_hash.txt', 'index.html', 'index_terminal.html'}
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_SNAPSHOT_STORAGE_BYTES = 256 * 1024 * 1024
MAX_SNAPSHOT_GENERATIONS = 512
MAX_GENERATION_FILES = 12


class SnapshotCapacityError(RuntimeError):
    """Publication refused before extending a bounded local store."""


def check_snapshot_capacity(root, artifacts):
    """Bound logical bytes and directory counts, including abandoned stages.

    Conservative peak allowance includes one temporary artifact and metadata.
    Caller holds the writer lock. No files are removed; readers stay valid.
    """
    root = Path(root)
    if set(artifacts) != NAMES:
        raise ValueError('Dashboard snapshot requires four artifacts')
    sizes = [len(text.encode('utf-8')) for text in artifacts.values()]
    if any(size > MAX_ARTIFACT_BYTES for size in sizes):
        raise ValueError('Dashboard snapshot artifact too large')
    reserve = sum(sizes) + max(sizes) + 12288
    count = 0
    used = 0
    generations = root / 'generations'
    if generations.exists():
        if not generations.is_dir() or not generations.resolve().is_relative_to(root.resolve()):
            raise SnapshotCapacityError('Invalid dashboard generations root')
        with os.scandir(generations) as directories:
            for directory in directories:
                count += 1
                if count >= MAX_SNAPSHOT_GENERATIONS:
                    raise SnapshotCapacityError('Dashboard snapshot generation limit reached')
                path = Path(directory.path)
                if (not re.fullmatch('[0-9a-f]{32}', directory.name)
                        or not directory.is_dir(follow_symlinks=False)
                        or path.resolve().parent != generations.resolve()):
                    raise SnapshotCapacityError('Unexpected dashboard generation entry')
                with os.scandir(path) as files:
                    for index, entry in enumerate(files, 1):
                        if index > MAX_GENERATION_FILES or not entry.is_file(follow_symlinks=False):
                            raise SnapshotCapacityError('Unexpected dashboard generation contents')
                        used += entry.stat(follow_symlinks=False).st_size
                        if used + reserve > MAX_SNAPSHOT_STORAGE_BYTES:
                            raise SnapshotCapacityError('Dashboard snapshot storage byte limit reached')
    if reserve > MAX_SNAPSHOT_STORAGE_BYTES:
        raise SnapshotCapacityError('Dashboard snapshot storage byte limit reached')
    return {'generations': count, 'stored_bytes': used, 'reserved_bytes': reserve}



def _json_file(path, limit=4096):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise RuntimeError('Dashboard snapshot metadata too large')
    return json.loads(raw), raw


def publish_snapshot(root, artifacts):
    """Build unreferenced files, then atomically commit one small pointer.

    Collection is separate and must run under the same writer lock.
    This is local publication, not an ACL or power-loss durability guarantee.
    """
    if set(artifacts) != NAMES:
        raise ValueError('Dashboard snapshot requires four artifacts')
    encoded = {name: text.encode('utf-8') for name, text in artifacts.items()}
    if any(len(data) > MAX_ARTIFACT_BYTES for data in encoded.values()):
        raise ValueError('Dashboard snapshot artifact too large')
    expected = hashlib.sha256(encoded['dashboard_payload.json']).hexdigest()
    if artifacts['payload_hash.txt'] != expected:
        raise ValueError('Dashboard snapshot payload hash mismatch')
    root = Path(root)
    check_snapshot_capacity(root, artifacts)
    generation = uuid.uuid4().hex
    directory = root / 'generations' / generation
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version': 1, 'generation': generation, 'files': {}}
    for name, text in artifacts.items():
        atomic_write_text(directory / name, text)
        manifest['files'][name] = {'bytes': len(encoded[name]), 'sha256': hashlib.sha256(encoded[name]).hexdigest()}
    metadata = json.dumps(manifest, sort_keys=True)
    atomic_write_text(directory / 'manifest.json', metadata)
    pointer = {'schema_version': 1, 'generation': generation,
               'manifest_sha256': hashlib.sha256(metadata.encode('utf-8')).hexdigest()}
    atomic_write_text(root / 'current.json', json.dumps(pointer, sort_keys=True))
    return generation


def resolve_snapshot(root):
    """Pin one committed generation. A corrupt pointer never falls back to legacy."""
    root = Path(root)
    pointer_path = root / 'current.json'
    try:
        pointer, _ = _json_file(pointer_path)
    except FileNotFoundError:
        return None
    if (not isinstance(pointer, dict) or pointer.get('schema_version') != 1
            or not isinstance(pointer.get('generation'), str)
            or not re.fullmatch('[0-9a-f]{32}', pointer['generation'])):
        raise RuntimeError('Invalid dashboard snapshot pointer')
    directory = root / 'generations' / pointer['generation']
    if not directory.resolve().is_relative_to(root.resolve()) or (directory / 'manifest.json').resolve().parent != directory.resolve():
        raise RuntimeError('Dashboard snapshot escapes its root')
    manifest, raw = _json_file(directory / 'manifest.json')
    if hashlib.sha256(raw).hexdigest() != pointer.get('manifest_sha256'):
        raise RuntimeError('Dashboard snapshot manifest hash mismatch')
    if (not isinstance(manifest, dict) or manifest.get('schema_version') != 1
            or manifest.get('generation') != pointer['generation']
            or not isinstance(manifest.get('files'), dict) or set(manifest['files']) != NAMES):
        raise RuntimeError('Invalid dashboard snapshot manifest')
    return directory, manifest


class SnapshotCatalogLock(DashboardLock):
    """Brief gate shared by file-handle acquisition and future collection."""
    def __init__(self, root, wait_timeout=1):
        super().__init__(wait_timeout=wait_timeout)
        self.lock_path = Path(root) / 'catalog.lock'


def collect_snapshots(root, keep_recent=3):
    """Bounded nonrecursive collection; caller holds the generation writer lock.

    Keep current plus newest directories. Catalog gate prevents opening files
    during removal; already opened readers retain bytes or defer Windows GC.
    No unexpected entry is removed. Validate all candidates before mutation.
    """
    if type(keep_recent) is not int or keep_recent < 2:
        raise ValueError('Snapshot retention must keep at least two generations')
    root = Path(root)
    result = {'removed': [], 'deferred': [], 'retained': []}
    if not (root / 'current.json').exists():
        return result
    with SnapshotCatalogLock(root):
        current = resolve_snapshot(root)
        if current is None:
            raise RuntimeError('Dashboard snapshot pointer disappeared')
        generations = root / 'generations'
        directories = []
        with os.scandir(generations) as entries:
            for entry in entries:
                if len(directories) >= MAX_SNAPSHOT_GENERATIONS:
                    raise SnapshotCapacityError('Too many generations to collect in one pass')
                path = Path(entry.path)
                if (not re.fullmatch('[0-9a-f]{32}', entry.name)
                        or not entry.is_dir(follow_symlinks=False)
                        or path.resolve().parent != generations.resolve()):
                    raise SnapshotCapacityError('Unexpected dashboard generation entry')
                directories.append((entry.stat(follow_symlinks=False).st_mtime_ns, path))
        directories.sort(key=lambda item: (item[0], item[1].name), reverse=True)
        protected = {path for _, path in directories[:keep_recent]}
        protected.add(current[0])
        candidates = []
        for _, path in directories:
            if path in protected:
                result['retained'].append(path.name)
                continue
            files = []
            with os.scandir(path) as entries:
                for entry in entries:
                    if len(files) >= MAX_GENERATION_FILES:
                        raise SnapshotCapacityError('Unexpected dashboard generation contents')
                    known = entry.name in NAMES | {'manifest.json'}
                    temporary = any(re.fullmatch(r'\.' + re.escape(name) + r'\.[A-Za-z0-9_-]+\.tmp', entry.name)
                                    for name in NAMES | {'manifest.json'})
                    file_path = Path(entry.path)
                    if (not (known or temporary) or not entry.is_file(follow_symlinks=False)
                            or file_path.resolve().parent != path.resolve()):
                        raise SnapshotCapacityError('Unexpected dashboard generation contents')
                    files.append(file_path)
            candidates.append((path, files))
        for path, files in candidates:
            # Open artifact handles usually make the first unlink fail on Windows.
            # Keep manifest until all artifacts/temporary files have been removed.
            files.sort(key=lambda file: (file.name == 'manifest.json', file.name))
            try:
                for file in files:
                    file.unlink()
                path.rmdir()
            except OSError:
                result['deferred'].append(path.name)
            else:
                result['removed'].append(path.name)
    return result


class PinnedSnapshot:
    """Own open files for one generation; valid only inside pin_snapshot."""
    def __init__(self, snapshot, streams):
        self.directory, self.manifest = snapshot
        self.streams = streams
        self.closed = False


@contextmanager
def pin_snapshot(root):
    """Acquire all artifact handles before releasing the brief catalog gate.

    Future GC must use the same gate while choosing/removing generations.
    Open handles keep bytes valid after POSIX unlink; Windows may defer GC.
    """
    root = Path(root)
    # No store or pointer means legacy mode; avoid creating a store on reads.
    if not (root / 'current.json').exists():
        yield None
        return
    with ExitStack() as stack:
        with SnapshotCatalogLock(root):
            snapshot = resolve_snapshot(root)
            if snapshot is None:
                raise RuntimeError('Dashboard snapshot pointer disappeared')
            directory, _ = snapshot
            streams = {}
            for name in sorted(NAMES):
                path = directory / name
                if path.resolve().parent != directory.resolve():
                    raise RuntimeError('Dashboard artifact escapes its generation')
                streams[name] = stack.enter_context(path.open('rb'))
        pinned = PinnedSnapshot(snapshot, streams)
        try:
            yield pinned
        finally:
            pinned.closed = True


def read_snapshot_artifact(snapshot, name):
    if name not in NAMES:
        raise ValueError('Unknown dashboard snapshot artifact')
    if isinstance(snapshot, PinnedSnapshot):
        if snapshot.closed:
            raise RuntimeError('Dashboard snapshot reader is closed')
        directory, manifest = snapshot.directory, snapshot.manifest
    else:
        directory, manifest = snapshot
    descriptor = manifest['files'][name]
    if (not isinstance(descriptor, dict) or type(descriptor.get('bytes')) is not int
            or not 0 <= descriptor['bytes'] <= MAX_ARTIFACT_BYTES):
        raise RuntimeError('Invalid dashboard artifact descriptor')
    if (directory / name).resolve().parent != directory.resolve():
        raise RuntimeError('Dashboard artifact escapes its generation')
    if isinstance(snapshot, PinnedSnapshot):
        stream = snapshot.streams[name]
        stream.seek(0)
        data = stream.read(descriptor['bytes'] + 1)
    else:
        with (directory / name).open('rb') as stream:
            data = stream.read(descriptor['bytes'] + 1)
    if len(data) != descriptor['bytes'] or hashlib.sha256(data).hexdigest() != descriptor.get('sha256'):
        raise RuntimeError('Dashboard snapshot artifact hash mismatch')
    return data.decode('utf-8')
