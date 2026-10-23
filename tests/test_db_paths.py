"""数据库路径选择的测试。"""

import os
import sys

import pytest

from app import db


def test_development_path(monkeypatch):
    monkeypatch.delenv("TODO_DB", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert db.get_db_path() == db.BASE_DIR / "data" / "todo.db"


def test_env_override(tmp_path, monkeypatch):
    custom = tmp_path / "custom.db"
    monkeypatch.setenv("TODO_DB", str(custom))
    assert db.get_db_path() == custom


@pytest.mark.skipif(os.name != "nt", reason="Windows 用户数据目录")
def test_frozen_path_uses_localappdata(tmp_path, monkeypatch):
    monkeypatch.delenv("TODO_DB", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert db.get_db_path() == tmp_path / "todo-cli" / "todo.db"
