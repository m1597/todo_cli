"""核心增删改查的接口测试。"""

from app import db


def test_empty_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "还没有待办" in response.text


def test_create_task(client):
    response = client.post(
        "/tasks",
        data={
            "title": "买牛奶",
            "priority": "high",
            "due": "2026-12-31",
            "tags": "生活, 购物",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/?msg=added"

    tasks = db.list_tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["title"] == "买牛奶"
    assert task["priority"] == "high"
    assert task["due"] == "2026-12-31"
    assert task["tags"] == ["生活", "购物"]
    assert task["done"] is False

    assert "买牛奶" in client.get("/").text


def test_create_validation(client):
    cases = [
        (
            {"title": "   ", "priority": "medium", "due": "", "tags": ""},
            "待办内容不能为空",
        ),
        (
            {"title": "任务", "priority": "urgent", "due": "", "tags": ""},
            "优先级",
        ),
        (
            {"title": "任务", "priority": "medium", "due": "2026-13-40", "tags": ""},
            "日期格式",
        ),
    ]
    for data, message in cases:
        response = client.post("/tasks", data=data)
        assert response.status_code == 400
        assert message in response.text
    assert db.stats()["total"] == 0


def test_toggle_done_and_undone(client, add_task):
    task_id = add_task("写周报")

    response = client.post(f"/tasks/{task_id}/toggle", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/?msg=done"
    assert db.get_task(task_id)["done"] is True

    response = client.post(f"/tasks/{task_id}/toggle", follow_redirects=False)
    assert response.headers["location"] == "/?msg=undone"
    assert db.get_task(task_id)["done"] is False


def test_edit_task(client, add_task):
    task_id = add_task("旧标题", priority="low", due="2026-01-01", tags="旧")

    page = client.get(f"/tasks/{task_id}/edit")
    assert page.status_code == 200
    assert "旧标题" in page.text

    response = client.post(
        f"/tasks/{task_id}/edit",
        data={
            "title": "新标题",
            "priority": "high",
            "due": "",
            "tags": "新, 重要",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/?msg=updated"

    task = db.get_task(task_id)
    assert task["title"] == "新标题"
    assert task["priority"] == "high"
    assert task["due"] is None
    assert task["tags"] == ["新", "重要"]


def test_delete_task(client, add_task):
    task_id = add_task("临时任务")

    response = client.post(f"/tasks/{task_id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/?msg=deleted"
    assert db.get_task(task_id) is None


def test_clear_completed(client, add_task):
    keep_id = add_task("保留")
    remove_id = add_task("删掉")
    client.post(f"/tasks/{remove_id}/toggle")

    response = client.post("/tasks/clear", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/?msg=cleared"
    assert [task["id"] for task in db.list_tasks()] == [keep_id]


def test_missing_task_404(client):
    assert client.get("/tasks/999/edit").status_code == 404
    assert client.post("/tasks/999/toggle").status_code == 404
    assert client.post("/tasks/999/delete").status_code == 404
