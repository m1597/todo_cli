import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


# conftest.py 是 pytest 的特殊文件：里面定义的 fixture 可以被同目录的测试直接用。
#
# fixture 可以理解成“每个测试开始前自动准备好的环境”。
# 函数里有 yield：yield 之前做准备工作，yield 之后做收尾工作。
@pytest.fixture()
def client(tmp_path, monkeypatch):
    """每个测试使用独立的临时数据库，结束后自动清理。"""
    # tmp_path 是 pytest 自动提供的临时目录，每个测试各不相同。
    # monkeypatch 可以临时修改环境变量，测试结束后自动还原。
    monkeypatch.setenv("TODO_DB", str(tmp_path / "test.db"))
    # TestClient 会像浏览器一样向 FastAPI 发请求；
    # with 语句会触发应用启动（也就是执行 init_db 建表）。
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def add_task(client):
    """快速新增一条待办，并返回它的编号。"""

    # 这是一个“工厂函数”：测试里可以多次调用 _add(...) 创建不同任务。
    def _add(title, priority="medium", due="", tags=""):
        response = client.post(
            "/tasks",
            data={"title": title, "priority": priority, "due": due, "tags": tags},
            follow_redirects=False,
        )
        # 新增成功后服务器会返回 303 重定向。
        assert response.status_code == 303
        # 新增的待办按 id 排序在最后，取它的编号返回给测试。
        return db.list_tasks()[-1]["id"]

    return _add
