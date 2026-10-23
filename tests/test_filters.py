"""筛选、排序、搜索和统计的测试。"""

import pytest

from app import db

TITLES = ("买牛奶", "写周报", "交房租", "读书")


def titles_in(page):
    """从任务列表区域提取标题，并保持页面上的先后顺序。"""
    section = page.split('class="task-list"', 1)[1]
    found = []
    for title in TITLES:
        index = section.find(title)
        if index != -1:
            found.append((index, title))
    return [title for _, title in sorted(found)]


@pytest.fixture()
def sample(client, add_task):
    ids = {
        "买牛奶": add_task("买牛奶", "high", "2000-01-01", "生活,购物"),
        "写周报": add_task("写周报", "low", "2999-12-31", "工作"),
        "交房租": add_task("交房租", "medium", "2000-01-01", "生活"),
        "读书": add_task("读书", "high", "", "学习"),
    }
    client.post(f"/tasks/{ids['交房租']}/toggle")
    client.post(f"/tasks/{ids['读书']}/toggle")
    return ids


def test_stats(sample):
    data = db.stats()
    assert data["total"] == 4
    assert data["pending"] == 2
    assert data["done"] == 2
    assert data["overdue"] == 1
    assert data["priority"] == {"high": 2, "medium": 1, "low": 1}


def test_status_filters(client, sample):
    assert set(titles_in(client.get("/?status=pending").text)) == {
        "买牛奶",
        "写周报",
    }
    assert set(titles_in(client.get("/?status=done").text)) == {
        "交房租",
        "读书",
    }
    assert titles_in(client.get("/?status=overdue").text) == ["买牛奶"]


def test_priority_tag_and_search(client, sample):
    assert set(titles_in(client.get("/?priority=high").text)) == {"买牛奶", "读书"}
    assert set(titles_in(client.get("/?tag=生活").text)) == {"买牛奶", "交房租"}
    assert titles_in(client.get("/?q=周报").text) == ["写周报"]


def test_combined_filters(client, sample):
    page = client.get("/?status=pending&priority=high&tag=生活&q=牛奶").text
    assert titles_in(page) == ["买牛奶"]


def test_sort_priority(client, sample):
    assert titles_in(client.get("/?sort=priority").text) == [
        "买牛奶",
        "读书",
        "交房租",
        "写周报",
    ]


def test_sort_due(client, sample):
    assert titles_in(client.get("/?sort=due").text) == [
        "买牛奶",
        "交房租",
        "写周报",
        "读书",
    ]


def test_overdue_badge(client, sample):
    page = client.get("/").text
    assert "badge due overdue" in page
    assert "2000-01-01 · 已逾期" in page


def test_invalid_filters_fallback(client, sample):
    page = client.get("/?status=nope&priority=nope&sort=nope").text
    assert set(titles_in(page)) == set(TITLES)


def test_empty_result_message(client, sample):
    page = client.get("/?q=不存在").text
    assert "没有符合条件的待办" in page
    assert 'class="empty-icon"' in page


def test_overdue_count_updates(client, sample):
    client.post(f"/tasks/{sample['买牛奶']}/toggle")
    assert db.stats()["overdue"] == 0
    assert "没有符合条件的待办" in client.get("/?status=overdue").text
