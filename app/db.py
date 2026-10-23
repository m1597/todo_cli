import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path


# app/db.py 的上两级是项目根目录；数据库默认放在 data/ 下。
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("TODO_DB", BASE_DIR / "data" / "todo.db"))

PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}
PRIORITY_KEYS = {"高": "high", "中": "medium", "低": "low"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@contextmanager
def get_conn():
    """打开数据库连接；正常结束时提交，出错时回滚，最后一定关闭。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """创建数据目录和 tasks 表；重复调用不会报错。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                priority TEXT NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('high', 'medium', 'low')),
                due TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def normalize_title(value):
    title = (value or "").strip()
    if not title:
        raise ValueError("待办内容不能为空")
    return title


def normalize_priority(value):
    normalized = (value or "medium").strip().lower()
    if normalized in PRIORITY_LABELS:
        return normalized
    if normalized in PRIORITY_KEYS:
        return PRIORITY_KEYS[normalized]
    raise ValueError("优先级只能是 high、medium、low")


def normalize_due(value):
    due = (value or "").strip()
    if not due:
        return None
    try:
        return date.fromisoformat(due).isoformat()
    except ValueError as error:
        raise ValueError("截止日期格式应为 YYYY-MM-DD") from error


def parse_tags(value):
    """把“生活, 购物”或“生活 购物”拆成去重后的标签列表。"""
    if not value:
        return []
    result = []
    for part in re.split(r"[,，\s]+", value):
        tag = part.strip().lstrip("#")
        if tag and tag not in result:
            result.append(tag)
    return result


def row_to_task(row):
    """把数据库行转换成模板和接口都容易使用的字典。"""
    task = dict(row)
    task["done"] = bool(task["done"])
    try:
        task["tags"] = json.loads(task["tags"] or "[]")
    except (TypeError, json.JSONDecodeError):
        task["tags"] = []
    task["overdue"] = False
    if not task["done"] and task["due"]:
        try:
            task["overdue"] = date.fromisoformat(task["due"]) < date.today()
        except ValueError:
            task["overdue"] = False
    return task


def list_tasks(status="all", priority="", tag="", search="", sort="id"):
    """按状态、优先级、标签和关键词筛选，再按指定字段排序。"""
    clauses = []
    params = []

    if status == "pending":
        clauses.append("done = 0")
    elif status == "done":
        clauses.append("done = 1")
    elif status == "overdue":
        clauses.append("done = 0 AND due IS NOT NULL AND due < ?")
        params.append(date.today().isoformat())

    if priority:
        clauses.append("priority = ?")
        params.append(priority)

    if search:
        # lower() 只影响英文字母；中文按原样做子串匹配。
        clauses.append("instr(lower(title), lower(?)) > 0")
        params.append(search)

    sql = "SELECT * FROM tasks"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    tasks = [row_to_task(row) for row in rows]

    if tag:
        tasks = [
            task
            for task in tasks
            if any(tag.casefold() == item.casefold() for item in task["tags"])
        ]
    return sort_tasks(tasks, sort)


def sort_tasks(tasks, sort):
    """按优先级或截止日期排序；编号顺序是数据库的默认顺序。"""
    if sort == "priority":
        return sorted(
            tasks,
            key=lambda task: (PRIORITY_ORDER.get(task["priority"], 9), task["id"]),
        )
    if sort == "due":
        return sorted(
            tasks,
            key=lambda task: (task["due"] is None, task["due"] or "", task["id"]),
        )
    return tasks


def get_task(task_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_task(row) if row else None


def create_task(title, priority="medium", due="", tags=""):
    clean_title = normalize_title(title)
    clean_priority = normalize_priority(priority)
    clean_due = normalize_due(due)
    clean_tags = parse_tags(tags)
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (title, done, priority, due, tags)
            VALUES (?, 0, ?, ?, ?)
            """,
            (
                clean_title,
                clean_priority,
                clean_due,
                json.dumps(clean_tags, ensure_ascii=False),
            ),
        )
    return cursor.lastrowid


def update_task(task_id, title, priority, due="", tags=""):
    clean_title = normalize_title(title)
    clean_priority = normalize_priority(priority)
    clean_due = normalize_due(due)
    clean_tags = parse_tags(tags)
    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET title = ?, priority = ?, due = ?, tags = ?
            WHERE id = ?
            """,
            (
                clean_title,
                clean_priority,
                clean_due,
                json.dumps(clean_tags, ensure_ascii=False),
                task_id,
            ),
        )
    return cursor.rowcount > 0


def toggle_task(task_id):
    """切换完成状态；返回切换后的状态，编号不存在时返回 None。"""
    with get_conn() as conn:
        row = conn.execute("SELECT done FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        new_done = not bool(row["done"])
        conn.execute(
            "UPDATE tasks SET done = ? WHERE id = ?",
            (1 if new_done else 0, task_id),
        )
    return new_done


def delete_task(task_id):
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return cursor.rowcount > 0


def clear_completed():
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE done = 1")
    return cursor.rowcount


def stats():
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(done), 0) AS done,
                COALESCE(SUM(
                    CASE WHEN done = 0 AND due IS NOT NULL AND due < ? THEN 1 ELSE 0 END
                ), 0) AS overdue
            FROM tasks
            """,
            (today,),
        ).fetchone()
        priority_rows = conn.execute(
            "SELECT priority, COUNT(*) AS count FROM tasks GROUP BY priority"
        ).fetchall()

    total = row["total"]
    done = row["done"]
    priority_counts = {key: 0 for key in PRIORITY_LABELS}
    for priority_row in priority_rows:
        priority_counts[priority_row["priority"]] = priority_row["count"]

    return {
        "total": total,
        "done": done,
        "pending": total - done,
        "overdue": row["overdue"],
        "priority": priority_counts,
    }
