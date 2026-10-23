"""页面反馈、表单保留和安全相关测试。"""

from app import db

FLASHES = {
    "added": "已添加待办",
    "done": "已标记为完成",
    "undone": "已取消完成",
    "deleted": "已删除待办",
    "cleared": "已清空已完成待办",
    "updated": "已保存修改",
}


def test_default_form_values(client):
    page = client.get("/").text
    assert 'value="medium" selected' in page
    assert 'class="empty-icon"' in page


def test_flash_messages(client):
    for code, text in FLASHES.items():
        page = client.get(f"/?msg={code}").text
        assert 'class="flash"' in page
        assert text in page


def test_invalid_flash_code_is_ignored(client):
    page = client.get("/?msg=%3Cscript%3Ealert(1)%3C/script%3E").text
    assert 'class="flash"' not in page
    assert "<script>alert(1)</script>" not in page


def test_form_values_preserved_on_error(client):
    response = client.post(
        "/tasks",
        data={
            "title": "保留输入",
            "priority": "high",
            "due": "2026-13-40",
            "tags": "工作, 重要",
        },
    )
    assert response.status_code == 400
    assert "日期格式" in response.text
    assert 'value="保留输入"' in response.text
    assert 'value="2026-13-40"' in response.text
    assert 'value="工作, 重要"' in response.text
    assert 'value="high" selected' in response.text
    assert db.stats()["total"] == 0


def test_title_is_escaped(client):
    client.post(
        "/tasks",
        data={
            "title": "<script>alert(1)</script>",
            "priority": "medium",
            "due": "",
            "tags": "",
        },
        follow_redirects=False,
    )
    page = client.get("/").text
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_aria_labels_and_static_files(client):
    client.post(
        "/tasks",
        data={"title": "任务", "priority": "medium", "due": "", "tags": ""},
        follow_redirects=False,
    )
    page = client.get("/").text
    assert 'aria-label="标记待办' in page
    assert 'aria-label="编辑待办' in page
    assert 'aria-label="删除待办' in page
    assert client.get("/static/favicon.svg").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_edit_page_404(client):
    assert client.get("/tasks/999/edit").status_code == 404
