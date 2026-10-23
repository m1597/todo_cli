import json
import os
import re
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path


# ===========================================================================
# 这个文件只负责“数据怎么存、怎么取”，不关心网页长什么样。
# 数据库是 SQLite：整个数据库就是一个普通文件（开发时是 data/todo.db）。
#
# SQL 里看到的 ? 是占位符，真正的值通过 execute 的第二个参数传进去。
# 这样不用把用户输入拼进 SQL 字符串，可以避免 SQL 注入。
# ===========================================================================

# app/db.py 的上两级是项目根目录；开发时数据库放在 data/ 下。
BASE_DIR = Path(__file__).resolve().parent.parent

PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}
PRIORITY_KEYS = {"高": "high", "中": "medium", "低": "low"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def default_db_path():
    """开发时用项目内 data/；打包后写到用户数据目录，避免写进临时解压目录。"""
    # sys.frozen 是 PyInstaller 打包后才会有的标记。
    if getattr(sys, "frozen", False):
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        else:
            base = Path.home() / ".local" / "share"
        return base / "todo-cli" / "todo.db"
    return BASE_DIR / "data" / "todo.db"


def get_db_path():
    """每次调用时读取环境变量，测试可以用 TODO_DB 指向临时数据库。"""
    # 环境变量优先；没有设置时再使用默认路径。
    return Path(os.environ.get("TODO_DB", default_db_path()))


# @contextmanager 让 get_conn 可以用 with 语句调用：
#     with get_conn() as conn:
#         ...
# 进入 with 时执行 yield 之前的代码，离开时执行 yield 之后的代码。
# 这里的作用是：正常结束自动提交，出错自动回滚，最后一定关闭连接。
@contextmanager
def get_conn():
    """打开数据库连接；正常结束时提交，出错时回滚，最后一定关闭。"""
    conn = sqlite3.connect(get_db_path())
    # row_factory 让查询结果可以按列名取值，例如 row["done"]，而不是 row[2]。
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
    db_path = get_db_path()
    # parents=True 会连同不存在的上级目录一起创建；exist_ok=True 表示已存在也不报错。
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                -- id 是自增编号，删除后不会复用。
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                -- SQLite 没有布尔类型，用 0/1 表示，CHECK 限制只能取这两个值。
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                priority TEXT NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('high', 'medium', 'low')),
                due TEXT,
                -- 标签是一个列表，这里存成 JSON 字符串，例如 ["生活","购物"]。
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def normalize_title(value):
    """去掉首尾空白；空标题直接报错。"""
    title = (value or "").strip()
    if not title:
        raise ValueError("待办内容不能为空")
    return title


def normalize_priority(value):
    """把 high/medium/low 或 高/中/低 统一成英文键。"""
    normalized = (value or "medium").strip().lower()
    if normalized in PRIORITY_LABELS:
        return normalized
    if normalized in PRIORITY_KEYS:
        return PRIORITY_KEYS[normalized]
    raise ValueError("优先级只能是 high、medium、low")


def normalize_due(value):
    """校验 YYYY-MM-DD；空字符串表示没有截止日期。"""
    due = (value or "").strip()
    if not due:
        return None
    try:
        # fromisoformat 会检查日期是否真实存在，例如 2026-13-40 会报错。
        return date.fromisoformat(due).isoformat()
    except ValueError as error:
        raise ValueError("截止日期格式应为 YYYY-MM-DD") from error


def parse_tags(value):
    """把“生活, 购物”或“生活 购物”拆成去重后的标签列表。"""
    if not value:
        return []
    result = []
    # 正则 [,\uFF0C\s]+ 表示：英文逗号、中文逗号或空白，连续出现都算分隔符。
    for part in re.split(r"[,，\s]+", value):
        tag = part.strip().lstrip("#")
        if tag and tag not in result:
            result.append(tag)
    return result


def row_to_task(row):
    """把数据库行转换成模板和接口都容易使用的字典。"""
    # dict(row) 把 sqlite3.Row 转成普通字典，方便后面修改。
    task = dict(row)
    # 数据库里 done 是 0/1，这里转成 True/False，模板判断更自然。
    task["done"] = bool(task["done"])
    try:
        # tags 存的是 JSON 字符串，这里还原成 Python 列表。
        task["tags"] = json.loads(task["tags"] or "[]")
    except (TypeError, json.JSONDecodeError):
        task["tags"] = []
    # 未完成、有截止日期、且日期早于今天，就是逾期。
    task["overdue"] = False
    if not task["done"] and task["due"]:
        try:
            task["overdue"] = date.fromisoformat(task["due"]) < date.today()
        except ValueError:
            task["overdue"] = False
    return task


def list_tasks(status="all", priority="", tag="", search="", sort="id"):
    """按状态、优先级、标签和关键词筛选，再按指定字段排序。"""
    # 根据筛选条件动态拼接 WHERE 片段，clauses 放 SQL，params 放对应的值。
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
        # instr(a, b) 返回 b 在 a 中出现的位置，> 0 表示找到了。
        # lower() 只影响英文字母；中文按原样做子串匹配。
        clauses.append("instr(lower(title), lower(?)) > 0")
        params.append(search)

    sql = "SELECT * FROM tasks"
    if clauses:
        # " AND ".join(...) 把多个条件用 AND 连起来。
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"

    with get_conn() as conn:
        # 第二个参数 params 会依次填进 SQL 里的 ? 占位符。
        rows = conn.execute(sql, params).fetchall()
    tasks = [row_to_task(row) for row in rows]

    if tag:
        # 标签是 JSON 字符串，直接在 SQL 里匹配不方便，所以取出来后再过滤。
        # casefold() 让比较忽略大小写。
        tasks = [
            task
            for task in tasks
            if any(tag.casefold() == item.casefold() for item in task["tags"])
        ]
    return sort_tasks(tasks, sort)


def sort_tasks(tasks, sort):
    """按优先级或截止日期排序；编号顺序是数据库的默认顺序。"""
    if sort == "priority":
        # lambda 是一个临时的小函数；sorted 会用它的返回值作为排序依据。
        # 返回元组 (优先级数字, 编号) 表示先比优先级，再比编号。
        return sorted(
            tasks,
            key=lambda task: (PRIORITY_ORDER.get(task["priority"], 9), task["id"]),
        )
    if sort == "due":
        # 没有截止日期的 task["due"] is None 为 True，排在最后。
        return sorted(
            tasks,
            key=lambda task: (task["due"] is None, task["due"] or "", task["id"]),
        )
    return tasks


def get_task(task_id):
    """按编号查询一条待办；找不到时返回 None。"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_task(row) if row else None


def create_task(title, priority="medium", due="", tags=""):
    """校验表单内容并插入一条新待办，返回新编号。"""
    # 先校验、清洗，全部通过后再写数据库。
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
    # lastrowid 是刚插入那一行的 id。
    return cursor.lastrowid


def update_task(task_id, title, priority, due="", tags=""):
    """更新一条待办；编号不存在时返回 False。"""
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
    # rowcount 表示实际改到了几行；0 行说明编号不存在。
    return cursor.rowcount > 0


def toggle_task(task_id):
    """切换完成状态；返回切换后的状态，编号不存在时返回 None。"""
    with get_conn() as conn:
        row = conn.execute("SELECT done FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        # 原来是 0 就变 1，原来是 1 就变 0。
        new_done = not bool(row["done"])
        conn.execute(
            "UPDATE tasks SET done = ? WHERE id = ?",
            (1 if new_done else 0, task_id),
        )
    return new_done


def delete_task(task_id):
    """删除一条待办；编号不存在时返回 False。"""
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return cursor.rowcount > 0


def clear_completed():
    """删除所有已完成的待办，返回删除数量。"""
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE done = 1")
    return cursor.rowcount


def stats():
    """统计总数、完成数、逾期数和各优先级数量。"""
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                -- COUNT(*) 数总行数；SUM(done) 把 1 加起来就是完成数。
                COUNT(*) AS total,
                COALESCE(SUM(done), 0) AS done,
                -- CASE WHEN 相当于 SQL 里的 if：满足条件记 1，否则记 0，再求和。
                COALESCE(SUM(
                    CASE WHEN done = 0 AND due IS NOT NULL AND due < ? THEN 1 ELSE 0 END
                ), 0) AS overdue
            FROM tasks
            """,
            (today,),
        ).fetchone()
        # GROUP BY priority 会按优先级分组，再数每组有多少行。
        priority_rows = conn.execute(
            "SELECT priority, COUNT(*) AS count FROM tasks GROUP BY priority"
        ).fetchall()

    total = row["total"]
    done = row["done"]
    # 先准备 0，再把数据库查到的数量填进去。
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
