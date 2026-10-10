# 命令行待办清单

一个用于学习 Python 和 vibe coding 的小项目，支持添加、查看和标记完成。

## 环境

安装 Python 3.7 或以上版本。程序只使用标准库，无需安装第三方依赖。
在终端进入 `todo_cli` 目录后运行下面的命令。

## 运行方法

Linux：

```bash
python3 todo.py add "学习 Python"
python3 todo.py list
python3 todo.py done 1
```

Windows（PowerShell 或命令提示符）：

```powershell
py todo.py add "学习 Python"
py todo.py list
py todo.py done 1
```

如果你的环境已经配置了 `python` 命令，也可以用它替换 `python3` 或 `py`。
待办内容请用双引号包起来；`done` 后面填写实际的待办编号。

查看帮助：

```bash
python todo.py --help
python todo.py add --help
python todo.py done --help
```

Linux 或 Windows 上同样可以按上述规则替换 `python`。

## 检查步骤

1. 运行 `add "练习命令行"`，记录输出中的编号。
2. 运行 `list`，确认新待办显示为 `[ ]`（未完成）。
3. 运行 `done 编号`，将“编号”替换为第一步得到的数字。
4. 再次运行 `list`，确认这条待办显示为 `[x]`（已完成）。
5. 关闭终端，重新进入项目目录运行 `list`，确认完成状态仍然保留。

以上各步的命令前都需要加上 `python todo.py`，或对应系统的启动命令。
没有待办时，`list` 显示“暂无待办”；重复完成会提示已经完成。
空白内容、无效编号和不存在的编号会得到错误提示。

## 文件安排

```text
todo_cli/
├── todo.py       # 解析命令、操作待办、读取和保存数据
├── tasks.json    # 第一次添加待办时自动创建
└── README.md     # 使用说明和检查步骤
```

`tasks.json` 始终保存在 `todo.py` 所在目录，使用 UTF-8 编码保存中文。
每条待办包含 `id`（编号）、`title`（内容）和 `done`（是否完成）。

代码中，`argparse` 负责解析命令，`pathlib` 负责处理跨系统路径，
`json` 负责把 Python 数据转换为文件内容以及读取回来。
