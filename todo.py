import argparse  # 解析终端输入的命令和参数
import json  # 在 Python 数据和 JSON 文本之间转换
from pathlib import Path  # 处理 Linux 和 Windows 的文件路径


# __file__ 是当前脚本的路径；resolve() 得到绝对路径，parent 取所在目录。
# 用 / 拼接路径，因此数据文件始终放在脚本旁边，不受终端当前目录影响。
DATA_FILE = Path(__file__).resolve().parent / "tasks.json"


def load_tasks():
    """从 JSON 文件读取待办列表；尚未创建文件时返回空列表。"""
    if not DATA_FILE.exists():
        return []
    # 先读取 UTF-8 文本，再把 JSON 文本转换为 Python 列表和字典。
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_tasks(tasks):
    """把整个待办列表保存到 JSON 文件。"""
    # ensure_ascii=False 保留中文；indent=2 用两个空格缩进，方便查看。
    # write_text 会创建文件，或覆盖已有文件内容。
    DATA_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    """解析用户命令，执行对应操作，并显示结果。"""
    parser = argparse.ArgumentParser(description="命令行待办清单")
    # 子命令分别是 list、add、done；选中的名字保存在 args.command 中。
    # required=True 表示必须提供一个子命令。
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="查看待办")
    # add 接收待办内容，例如：python todo.py add "学习 Python"。
    add_parser = commands.add_parser("add", help="添加待办")
    add_parser.add_argument("title", help="待办内容，包含空格时请加双引号")
    done_parser = commands.add_parser("done", help="标记待办为完成")
    # type=int 自动把编号转成整数；输入非整数时 argparse 会提示错误。
    done_parser.add_argument("id", type=int, help="待办编号")
    args = parser.parse_args()

    # strip() 去掉内容两端的空白，防止添加只包含空格的待办。
    if args.command == "add" and not args.title.strip():
        parser.error("待办内容不能为空")

    try:
        tasks = load_tasks()
        if args.command == "add":
            # 取已有编号的最大值再加 1；列表为空时从编号 1 开始。
            task_id = max((task["id"] for task in tasks), default=0) + 1
            # 每条待办是一个字典，包含编号、内容和完成状态。
            tasks.append({"id": task_id, "title": args.title.strip(), "done": False})
            save_tasks(tasks)
            print(f"已添加待办 {task_id}：{args.title.strip()}")
        elif args.command == "done":
            # next() 找到第一个编号匹配的待办；没有匹配时返回 None。
            task = next((task for task in tasks if task["id"] == args.id), None)
            if task is None:
                # 非零退出码表示命令失败，同时向终端显示原因。
                parser.exit(1, f"找不到编号为 {args.id} 的待办\n")
            if task["done"]:
                print(f"待办 {args.id} 已经完成")
            else:
                # task 指向列表中的原字典，修改后保存整个列表即可。
                task["done"] = True
                save_tasks(tasks)
                print(f"已完成待办 {args.id}：{task['title']}")
        # 前面已处理 add 和 done，剩下的情况就是 list。
        elif not tasks:
            print("暂无待办")
        else:
            for task in tasks:
                # 根据布尔值选择标记：[x] 表示完成，[ ] 表示未完成。
                status = "x" if task["done"] else " "
                print(f"{task['id']}. [{status}] {task['title']}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        # 将文件读写或数据格式错误转换成提示，并以退出码 1 结束。
        parser.exit(1, f"无法读取或保存待办：{error}\n")


# 直接运行此文件时调用 main()；被其他 Python 文件导入时不执行命令。
if __name__ == "__main__":
    main()
