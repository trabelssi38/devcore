import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


class FakeRepository:
    def __init__(self, tasks=None, fail=False):
        self.tasks = tasks or []
        self.fail = fail
        self.calls = []

    def list_tasks(self, project: str):
        self.calls.append(project)
        if self.fail:
            raise RuntimeError("repository unavailable")
        return self.tasks


def task(task_id: str):
    from devcore_api.contracts import TaskContract

    return TaskContract(id=task_id, title=f"Task {task_id}", status="todo", mode="coding")


def test_dual_read_defaults_to_legacy_json_source() -> None:
    from devcore_api.ports import DualReadTaskRepository

    legacy = FakeRepository([task("T-101")])
    sql = FakeRepository([task("T-201")])

    tasks = DualReadTaskRepository(legacy_repository=legacy, sql_repository=sql, mode="json").list_tasks("devcore")

    assert [item.id for item in tasks] == ["T-101"]
    assert legacy.calls == ["devcore"]
    assert sql.calls == []


def test_dual_read_can_cutover_to_sql_source() -> None:
    from devcore_api.ports import DualReadTaskRepository

    legacy = FakeRepository([task("T-101")])
    sql = FakeRepository([task("T-201")])

    tasks = DualReadTaskRepository(legacy_repository=legacy, sql_repository=sql, mode="sql").list_tasks("devcore")

    assert [item.id for item in tasks] == ["T-201"]
    assert legacy.calls == []
    assert sql.calls == ["devcore"]


def test_dual_read_compares_sql_and_json_but_serves_legacy() -> None:
    from devcore_api.ports import DualReadTaskRepository

    legacy = FakeRepository([task("T-101")])
    sql = FakeRepository([task("T-201")])
    mismatches = []

    tasks = DualReadTaskRepository(
        legacy_repository=legacy,
        sql_repository=sql,
        mode="dual",
        on_mismatch=mismatches.append,
    ).list_tasks("devcore")

    assert [item.id for item in tasks] == ["T-101"]
    assert mismatches == ["task_read_mismatch: project=devcore legacy=1 sql=1"]


def test_dual_read_falls_back_to_legacy_when_sql_unavailable() -> None:
    from devcore_api.ports import DualReadTaskRepository

    legacy = FakeRepository([task("T-101")])
    sql = FakeRepository(fail=True)

    tasks = DualReadTaskRepository(legacy_repository=legacy, sql_repository=sql, mode="dual").list_tasks("devcore")

    assert [item.id for item in tasks] == ["T-101"]


def test_dual_read_reports_sql_unavailability() -> None:
    from devcore_api.ports import DualReadTaskRepository

    warnings = []
    repo = DualReadTaskRepository(
        legacy_repository=FakeRepository([task("T-101")]),
        sql_repository=FakeRepository(fail=True),
        mode="dual",
        on_mismatch=warnings.append,
    )
    assert repo.list_tasks("devcore")[0].id == "T-101"
    assert warnings == ["task_read_sql_unavailable: project=devcore"]


def test_dual_read_detects_changed_fields_with_same_task_ids() -> None:
    from devcore_api.ports import DualReadTaskRepository

    legacy = FakeRepository([task("T-101")])
    changed = task("T-101").model_copy(update={"title": "Changed title"})
    sql = FakeRepository([changed])
    mismatches = []

    DualReadTaskRepository(
        legacy_repository=legacy,
        sql_repository=sql,
        mode="dual",
        on_mismatch=mismatches.append,
    ).list_tasks("devcore")
    assert mismatches == ["task_read_mismatch: project=devcore legacy=1 sql=1"]


def test_dual_read_detects_version_divergence() -> None:
    from devcore_api.ports import DualReadTaskRepository
    legacy = task("T-101").model_copy(update={"version": 2})
    sql = task("T-101").model_copy(update={"version": 3})
    warnings = []
    result = DualReadTaskRepository(legacy_repository=FakeRepository([legacy]),
                                   sql_repository=FakeRepository([sql]), mode="dual",
                                   on_mismatch=warnings.append).list_tasks("devcore")
    assert result[0].version == 2
    assert warnings == ["task_read_mismatch: project=devcore legacy=1 sql=1"]
