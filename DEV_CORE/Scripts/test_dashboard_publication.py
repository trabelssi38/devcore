"""Fault injection against temporary publication artifacts only."""
import importlib.util
from pathlib import Path

import pytest


def load_publication():
    spec = importlib.util.spec_from_file_location(
        'dashboard_publication_fixture', Path(__file__).parent / 'dashboard' / 'publication.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_atomic_replace_publishes_exact_utf8_after_complete_write(tmp_path, monkeypatch):
    module = load_publication()
    target = tmp_path / 'index.html'
    target.write_bytes(b'previous snapshot')
    text = 'mémoire\nnext\r\n<script>fixture</script>'
    original_replace = module.os.replace
    def observe(source, destination):
        assert Path(source).parent == target.parent
        assert target.read_bytes() == b'previous snapshot'
        assert Path(source).read_bytes() == text.encode('utf-8')
        original_replace(source, destination)
    monkeypatch.setattr(module.os, 'replace', observe)
    module.atomic_write_text(target, text)
    assert target.read_bytes() == text.encode('utf-8')
    assert sorted(p.name for p in tmp_path.iterdir()) == ['index.html']


@pytest.mark.parametrize('failure', ['encoding', 'fsync', 'replace'])
@pytest.mark.parametrize('exists', [True, False])
def test_failed_publication_preserves_previous_artifact_and_cleans_temporary(tmp_path, monkeypatch, failure, exists):
    module = load_publication()
    target = tmp_path / 'payload.json'
    if exists:
        target.write_bytes(b'previous snapshot')
    def refused(*args):
        raise OSError('fixture publication refused')
    if failure != 'encoding':
        monkeypatch.setattr(module.os, failure, refused)
    text = 'invalid surrogate: \ud800' if failure == 'encoding' else 'new snapshot'
    with pytest.raises((OSError, UnicodeEncodeError)):
        module.atomic_write_text(target, text)
    assert (target.read_bytes() if exists else target.exists()) == (b'previous snapshot' if exists else False)
    assert sorted(p.name for p in tmp_path.iterdir()) == (['payload.json'] if exists else [])
