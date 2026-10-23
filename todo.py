import argparse  # 解析终端输入的命令和参数
import json  # 在 Python 数据和 JSON 文本之间转换
from datetime import date  # 校验和比较截止日期
from pathlib import Path  # 处理 Linux 和 Windows 的文件路径


# __file__ 是当前脚本的路径；resolve() 得到绝对路径，parent 取所在目录。
# 用 / 拼接路径，因此数据文件始终放在脚本旁边，不受终端当前目录影响。
DATA_FILE = Path(__file__).resolve().parent / "tasks.json"

# 优先级在文件里存英文键，显示时转成中文，方便阅读和排序。
PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}
PRIORITY_KEYS = {"高": "high", "中": "medium", "低": "low"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def load_tasks():
    """从 JSON 文件读取待办列表；尚未创建文件时返回空列表。"""
    if not DATA_FILE.exists():
        return []
    # 先读取 UTF-8 文本，再把 JSON 文本转换为 Python 列表和字典。
    # 用 utf-8-sig 读取，既能处理普通 UTF-8，也能兼容带 BOM 的文件。
    tasks = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
    if not isinstance(tasks, list):
        raise ValueError("待办数据不是列表")
    return [normalize_task(task) for task in tasks]


def save_tasks(tasks):
    """把整个待办列表保存到 JSON 文件。"""
    # ensure_ascii=False 保留中文；indent=2 用两个空格缩进，方便查看。
    # write_text 会创建文件，或覆盖已有文件内容。
    DATA_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize_task(task):
    """补齐旧数据缺少的字段，兼容只有 id/title/done 的文件。"""
    if not isinstance(task, dict):
        raise ValueError("待办数据格式不正确")
    task.setdefault("priority", "medium")
    task.setdefault("due", None)
    task.setdefault("tags", [])
    return task


def parse_priority(value):
    """把 high/medium/low 或 高/中/低 统一转换成内部使用的英文键。"""
    normalized = value.strip().lower()
    if normalized in PRIORITY_LABELS:
        return normalized
    if normalized in PRIORITY_KEYS:
        return PRIORITY_KEYS[normalized]
    raise argparse.ArgumentTypeError("优先级只能是 high、medium、low（或 高、中、低）")


def parse_due(value):
    """校验 YYYY-MM-DD 格式的日期，并返回标准写法。"""
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError as error:
        raise argparse.ArgumentTypeError("日期格式应为 YYYY-MM-DD") from error


def clean_tags(tags):
    """去掉标签两端空白和开头的 #，并去除重复项。"""
    result = []
    for tag in tags:
        cleaned = tag.strip().lstrip("#")
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def find_task(tasks, task_id):
    """按编号查找待办；没有匹配时返回 None。"""
    return next((task for task in tasks if task["id"] == task_id), None)


def is_overdue(task):
    """未完成且截止日期早于今天就视为逾期。"""
    return (
        not task["done"]
        and task["due"] is not None
        and date.fromisoformat(task["due"]) < date.today()
    )


def format_task(task):
    """把一条待办格式化成一行文本。"""
    status = "x" if task["done"] else " "
    line = (
        f"{task['id']}. [{status}] "
        f"[{PRIORITY_LABELS.get(task['priority'], '中')}] {task['title']}"
    )
    if task["due"]:
        line += f" @ {task['due']}"
        if is_overdue(task):
            line += "（已逾期）"
    if task["tags"]:
        line += " " + " ".join(f"#{tag}" for tag in task["tags"])
    return line


def sort_tasks(tasks, key):
    """按编号、优先级或截止日期排序；没有截止日期的排在最后。"""
    if key == "priority":
        return sorted(
            tasks,
            key=lambda task: (PRIORITY_ORDER.get(task["priority"], 9), task["id"]),
        )
    if key == "due":
        return sorted(
            tasks,
            key=lambda task: (task["due"] is None, task["due"] or "", task["id"]),
        )
    return sorted(tasks, key=lambda task: task["id"])


def build_parser():
    """定义所有子命令和参数。"""
    parser = argparse.ArgumentParser(description="命令行待办清单")
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list", help="查看待办")
    state = list_parser.add_mutually_exclusive_group()
    state.add_argument("--pending", action="store_true", help="只看未完成")
    state.add_argument("--done", action="store_true", help="只看已完成")
    state.add_argument("--overdue", action="store_true", help="只看已逾期")
    list_parser.add_argument("-p", "--priority", type=parse_priority, help="按优先级筛选")
    list_parser.add_argument("-t", "--tag", help="按标签筛选")
    list_parser.add_argument("-s", "--search", help="按关键词搜索标题")
    list_parser.add_argument(
        "--sort",
        choices=("id", "priority", "due"),
        default="id",
        help="排序方式：id、priority、due（默认 id）",
    )

    add_parser = commands.add_parser("add", help="添加待办")
    add_parser.add_argument("title", help="待办内容，包含空格时请加双引号")
    add_parser.add_argument(
        "-p",
        "--priority",
        type=parse_priority,
        default="medium",
        help="优先级：high、medium、low（默认 medium）",
    )
    add_parser.add_argument("-d", "--due", type=parse_due, help="截止日期，格式 YYYY-MM-DD")
    add_parser.add_argument(
        "-t", "--tag", action="append", default=[], help="标签，可重复使用"
    )

    done_parser = commands.add_parser("done", help="标记待办为完成")
    done_parser.add_argument("id", type=int, help="待办编号")

    undone_parser = commands.add_parser("undone", help="把待办改回未完成")
    undone_parser.add_argument("id", type=int, help="待办编号")

    edit_parser = commands.add_parser("edit", help="编辑待办")
    edit_parser.add_argument("id", type=int, help="待办编号")
    edit_parser.add_argument("title", nargs="?", help="新的待办内容")
    edit_parser.add_argument("-p", "--priority", type=parse_priority, help="新的优先级")
    due_group = edit_parser.add_mutually_exclusive_group()
    due_group.add_argument("-d", "--due", type=parse_due, help="新的截止日期")
    due_group.add_argument("--no-due", action="store_true", help="清空截止日期")
    tag_group = edit_parser.add_mutually_exclusive_group()
    tag_group.add_argument(
        "-t", "--tag", action="append", help="替换全部标签，可重复使用"
    )
    tag_group.add_argument("--no-tags", action="store_true", help="清空标签")

    del_parser = commands.add_parser("del", help="删除待办")
    del_parser.add_argument("id", type=int, help="待办编号")

    clear_parser = commands.add_parser("clear", help="批量清空待办")
    scope = clear_parser.add_mutually_exclusive_group()
    scope.add_argument("--done", action="store_true", help="只清空已完成（默认）")
    scope.add_argument("--all", action="store_true", help="清空全部")
    clear_parser.add_argument("-y", "--yes", action="store_true", help="跳过确认")

    search_parser = commands.add_parser("search", help="搜索待办")
    search_parser.add_argument("keyword", help="搜索关键词")

    commands.add_parser("stats", help="查看统计信息")
    return parser


def cmd_add(tasks, args):
    """添加一条待办。"""
    # 取已有编号的最大值再加 1；列表为空时从编号 1 开始。
    task_id = max((task["id"] for task in tasks), default=0) + 1
    task = {
        "id": task_id,
        "title": args.title.strip(),
        "done": False,
        "priority": args.priority,
        "due": args.due,
        "tags": clean_tags(args.tag),
    }
    tasks.append(task)
    save_tasks(tasks)
    print(f"已添加待办 {task_id}：{task['title']}")


def cmd_list(tasks, args):
    """按条件筛选并显示待办。"""
    result = tasks
    if args.pending:
        result = [task for task in result if not task["done"]]
    elif args.done:
        result = [task for task in result if task["done"]]
    elif args.overdue:
        result = [task for task in result if is_overdue(task)]

    if args.priority:
        result = [task for task in result if task["priority"] == args.priority]
    if args.tag:
        tag = args.tag.strip().lstrip("#").casefold()
        result = [
            task
            for task in result
            if any(tag == item.casefold() for item in task["tags"])
        ]
    if args.search:
        keyword = args.search.casefold()
        result = [task for task in result if keyword in task["title"].casefold()]

    result = sort_tasks(result, args.sort)
    if not result:
        print("暂无可显示的待办")
        return
    for task in result:
        print(format_task(task))


def cmd_done(tasks, parser, args):
    """把一条待办标记为完成。"""
    task = find_task(tasks, args.id)
    if task is None:
        parser.exit(1, f"找不到编号为 {args.id} 的待办\n")
    if task["done"]:
        print(f"待办 {args.id} 已经完成")
        return
    # task 指向列表中的原字典，修改后保存整个列表即可。
    task["done"] = True
    save_tasks(tasks)
    print(f"已完成待办 {args.id}：{task['title']}")


def cmd_undone(tasks, parser, args):
    """把一条已完成的待办改回未完成。"""
    task = find_task(tasks, args.id)
    if task is None:
        parser.exit(1, f"找不到编号为 {args.id} 的待办\n")
    if not task["done"]:
        print(f"待办 {args.id} 还没有完成")
        return
    task["done"] = False
    save_tasks(tasks)
    print(f"已取消完成待办 {args.id}：{task['title']}")


def cmd_edit(tasks, parser, args):
    """修改待办的标题、优先级、截止日期或标签。"""
    task = find_task(tasks, args.id)
    if task is None:
        parser.exit(1, f"找不到编号为 {args.id} 的待办\n")

    if args.title is not None:
        task["title"] = args.title.strip()
    if args.priority:
        task["priority"] = args.priority
    if args.due:
        task["due"] = args.due
    if args.no_due:
        task["due"] = None
    if args.tag is not None:
        task["tags"] = clean_tags(args.tag)
    if args.no_tags:
        task["tags"] = []

    save_tasks(tasks)
    print(f"已更新待办 {args.id}：{format_task(task)}")


def cmd_del(tasks, parser, args):
    """删除一条待办。"""
    # enumerate 同时得到下标和待办，删除时需要下标。
    index = next(
        (index for index, task in enumerate(tasks) if task["id"] == args.id),
        None,
    )
    if index is None:
        parser.exit(1, f"找不到编号为 {args.id} 的待办\n")
    removed = tasks.pop(index)
    save_tasks(tasks)
    print(f"已删除待办 {removed['id']}：{removed['title']}")


def cmd_clear(tasks, args):
    """批量清空已完成待办或全部待办。"""
    targets = tasks if args.all else [task for task in tasks if task["done"]]
    if not targets:
        print("没有可清空的待办")
        return
    count = len(targets)
    if not args.yes:
        answer = input(f"将删除 {count} 条待办，确认吗？[y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("已取消")
            return

    if args.all:
        tasks.clear()
    else:
        tasks[:] = [task for task in tasks if not task["done"]]
    save_tasks(tasks)
    print(f"已清空 {count} 条待办")


def cmd_search(tasks, args):
    """按关键词搜索标题和标签。"""
    keyword = args.keyword.casefold()
    result = [
        task
        for task in tasks
        if keyword in task["title"].casefold()
        or any(keyword in tag.casefold() for tag in task["tags"])
    ]
    result = sort_tasks(result, "id")
    if not result:
        print("没有匹配的待办")
        return
    for task in result:
        print(format_task(task))


def cmd_stats(tasks):
    """显示总数、完成情况、逾期数量和优先级分布。"""
    if not tasks:
        print("暂无待办")
        return
    total = len(tasks)
    done = sum(1 for task in tasks if task["done"])
    overdue = sum(1 for task in tasks if is_overdue(task))
    print(
        f"总计 {total} 条：未完成 {total - done} 条，"
        f"已完成 {done} 条，已逾期 {overdue} 条"
    )
    for key in ("high", "medium", "low"):
        count = sum(1 for task in tasks if task["priority"] == key)
        print(f"  {PRIORITY_LABELS[key]}优先级：{count} 条")


def main():
    """解析用户命令，执行对应操作，并显示结果。"""
    parser = build_parser()
    args = parser.parse_args()

    # strip() 去掉内容两端的空白，防止添加只包含空格的待办。
    if args.command == "add" and not args.title.strip():
        parser.error("待办内容不能为空")
    if (
        args.command == "edit"
        and args.title is not None
        and not args.title.strip()
    ):
        parser.error("待办内容不能为空")
    if args.command == "edit" and not any(
        (
            args.title is not None,
            args.priority,
            args.due,
            args.no_due,
            args.tag is not None,
            args.no_tags,
        )
    ):
        parser.error("请至少指定一项要修改的内容")

    try:
        tasks = load_tasks()
        if args.command == "add":
            cmd_add(tasks, args)
        elif args.command == "list":
            cmd_list(tasks, args)
        elif args.command == "done":
            cmd_done(tasks, parser, args)
        elif args.command == "undone":
            cmd_undone(tasks, parser, args)
        elif args.command == "edit":
            cmd_edit(tasks, parser, args)
        elif args.command == "del":
            cmd_del(tasks, parser, args)
        elif args.command == "clear":
            cmd_clear(tasks, args)
        elif args.command == "search":
            cmd_search(tasks, args)
        elif args.command == "stats":
            cmd_stats(tasks)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        # 将文件读写或数据格式错误转换成提示，并以退出码 1 结束。
        parser.exit(1, f"无法读取或保存待办：{error}\n")


# 直接运行此文件时调用 main()；被其他 Python 文件导入时不执行命令。
if __name__ == "__main__":
    main()
