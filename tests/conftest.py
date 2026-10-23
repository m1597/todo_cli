import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """每个测试使用独立的临时数据库，结束后自动清理。"""
    monkeypatch.setenv("TODO_DB", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def add_task(client):
    """快速新增一条待办，并返回它的编号。"""

    def _add(title, priority="medium", due="", tags=""):
        response = client.post(
            "/tasks",
            data={"title": title, "priority": priority, "due": due, "tags": tags},
            follow_redirects=False,
        )
        assert response.status_code == 303
        return db.list_tasks()[-1]["id"]

    return _add
