# 待办清单

一个用于学习 Python 和 vibe coding 的小项目，正在从命令行版本迁移到本地 Web 应用。

## Web 版（开发中）

技术栈：Python + FastAPI + SQLite + Jinja2 + 原生 HTML/CSS/JS。

### 环境与安装

需要 Python 3.10 或以上版本。在 `todo_cli` 目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

- `.venv/` 是本项目独立的 Python 环境，依赖不会污染系统全局环境。
- `requirements.txt` 是运行依赖；`requirements-dev.txt` 额外包含测试工具。
- 如果 PowerShell 禁止运行 `Activate.ps1`，可以直接用 `.\.venv\Scripts\python.exe` 代替
  `python`，或临时执行 `Set-ExecutionPolicy -Scope Process Bypass`。

### 启动

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

然后在浏览器打开 <http://127.0.0.1:8000>。`--reload` 会在代码变化时自动重启服务，只用于开发。

### 使用

在页面上可以添加待办（内容、优先级、截止日期、标签）、点击圆圈切换完成状态、
编辑、删除，以及一键清空已完成。数据保存在 `data/todo.db`（SQLite），
首次启动时自动创建，已被 `.gitignore` 排除。

### 依赖之间的关系

- **FastAPI**：定义路由、处理请求并生成响应；安装时会自动带上 Starlette 和 Pydantic。
- **uvicorn**：真正启动 HTTP 服务、监听端口的服务器，负责把请求交给 FastAPI。
- **Jinja2**：模板引擎，把 HTML 模板和数据渲染成浏览器看到的页面。
- **StaticFiles**：Starlette 提供的静态文件服务，把 `/static/` 映射到 `app/static/`。
- **python-multipart**：解析新增和编辑表单的提交内容。

### 开发进度

- [x] 阶段 1：FastAPI 脚手架、首页、静态文件
- [x] 阶段 2：SQLite 建表和增删改查
- [ ] 阶段 3：筛选、排序、搜索、统计
- [ ] 阶段 4：样式与交互
- [ ] 阶段 5：pytest 测试和文档
- [ ] 阶段 6：PyWebView 打包桌面应用

## CLI 版本（旧）

以下为旧的命令行版本说明，暂时保留；Web 版完成后会重新整理。

## 环境

安装 Python 3.7 或以上版本。程序只使用标准库，无需安装第三方依赖。
在终端进入 `todo_cli` 目录后运行下面的命令。

## CLI 快速开始

Linux：

```bash
python3 todo.py add "买牛奶" -p high -d 2026-10-30 -t 生活
python3 todo.py list
python3 todo.py done 1
python3 todo.py stats
```

Windows（PowerShell 或命令提示符）：

```powershell
py todo.py add "买牛奶" -p high -d 2026-10-30 -t 生活
py todo.py list
py todo.py done 1
py todo.py stats
```

如果你的环境已经配置了 `python` 命令，也可以用它替换 `python3` 或 `py`。
待办内容和标签包含空格时请用双引号包起来。

## 命令一览

| 命令 | 作用 |
| --- | --- |
| `add` | 添加待办，可带优先级、截止日期和标签 |
| `list` | 查看待办，可筛选和排序 |
| `done` | 标记为已完成 |
| `undone` | 改回未完成 |
| `edit` | 修改标题、优先级、截止日期或标签 |
| `del` | 删除一条待办 |
| `clear` | 批量清空已完成或全部待办 |
| `search` | 按关键词搜索标题和标签 |
| `stats` | 查看完成情况、逾期数量和优先级分布 |

查看帮助：

```bash
python todo.py --help
python todo.py add --help
python todo.py list --help
python todo.py edit --help
python todo.py clear --help
```

## 添加待办 add

```bash
python todo.py add "写周报" -p high -d 2026-11-01 -t 工作 -t 重要
```

- `-p` / `--priority`：优先级，可选 `high`、`medium`、`low`，也接受 `高`、`中`、`低`，默认 `medium`。
- `-d` / `--due`：截止日期，格式 `YYYY-MM-DD`。
- `-t` / `--tag`：标签，可以重复使用；开头的 `#` 会自动去掉。

## 查看待办 list

```bash
python todo.py list                 # 全部
python todo.py list --pending       # 只看未完成
python todo.py list --done          # 只看已完成
python todo.py list --overdue       # 只看已逾期
python todo.py list -p high         # 只看高优先级
python todo.py list -t 工作          # 只看某个标签
python todo.py list -s 周报          # 按关键词搜索标题
python todo.py list --sort priority # 按优先级排序
python todo.py list --sort due      # 按截止日期排序
```

筛选条件可以组合使用，例如“未完成的高优先级工作”：

```bash
python todo.py list --pending -p high -t 工作
```

`--sort` 可选 `id`（默认）、`priority`、`due`；没有截止日期的排在最后。

## 完成与取消 done / undone

```bash
python todo.py done 1
python todo.py undone 1
```

重复完成或重复取消都会给出提示，不会报错。

## 编辑待办 edit

编号后面可以直接写新标题，也可以用参数只改某一项：

```bash
python todo.py edit 1 "买两盒牛奶"    # 改标题
python todo.py edit 1 -p low          # 改优先级
python todo.py edit 1 -d 2026-12-01   # 改截止日期
python todo.py edit 1 --no-due        # 清空截止日期
python todo.py edit 1 -t 日常 -t 购物 # 替换全部标签
python todo.py edit 1 --no-tags       # 清空标签
```

至少需要指定一项要修改的内容，否则会提示错误。

## 删除与批量清空 del / clear

```bash
python todo.py del 1          # 删除编号 1
python todo.py clear          # 清空所有已完成（默认）
python todo.py clear --all    # 清空全部
python todo.py clear -y       # 跳过确认
```

`clear` 会先显示将要删除的数量，输入 `y` 确认；加 `-y` 可直接执行。

## 搜索与统计 search / stats

```bash
python todo.py search 牛奶    # 标题或标签中包含关键词
python todo.py stats
```

`stats` 输出示例：

```text
总计 3 条：未完成 2 条，已完成 1 条，已逾期 1 条
  高优先级：1 条
  中优先级：1 条
  低优先级：1 条
```

## 显示格式

```text
1. [ ] [高] 买牛奶 @ 2026-10-30（已逾期） #生活 #购物
```

依次是：编号、完成状态（`[ ]` 未完成 / `[x]` 已完成）、优先级、
标题、截止日期、逾期提示、标签。

## 数据文件

`tasks.json` 始终保存在 `todo.py` 所在目录，使用 UTF-8 编码，第一次修改待办时自动创建。
它属于个人数据，已被 `.gitignore` 排除，不会提交到 Git。

每条待办包含以下字段：

```json
{
  "id": 1,
  "title": "买牛奶",
  "done": false,
  "priority": "high",
  "due": "2026-10-30",
  "tags": ["生活", "购物"]
}
```

- `priority`：`high`、`medium`、`low`
- `due`：截止日期，没有时为 `null`
- `tags`：标签列表，没有时为空列表

旧版本只有 `id`、`title`、`done` 的数据也能直接读取，修改后会自动补齐新字段；
带 BOM 的 UTF-8 文件同样兼容。

## 检查步骤

1. 运行 `add "练习命令行" -p high -d 2026-12-31 -t 学习`，记录输出中的编号。
2. 运行 `list`，确认显示未完成、高优先级、截止日期和标签。
3. 运行 `list --pending -p high`，确认能筛选出这条待办。
4. 运行 `edit 编号 "修改后的内容"`，确认标题已更新。
5. 运行 `done 编号`，再用 `list --done` 确认状态为 `[x]`。
6. 运行 `undone 编号`，确认又回到未完成。
7. 再添加一条待办并运行 `del 新编号`，确认它已消失。
8. 运行 `stats`，核对总数、完成数和优先级统计。
9. 运行 `clear --done`，确认后检查已完成项被清空。
10. 关闭终端，重新进入项目目录运行 `list`，确认剩余数据仍然保留。

空白内容、无效编号、错误日期和非法优先级都会得到错误提示。

## 文件安排

```text
todo_cli/
├── todo.py       # 解析命令、操作待办、读取和保存数据
├── tasks.json    # 第一次添加待办时自动创建（不提交）
└── README.md     # 使用说明和检查步骤
```

## 技术说明

代码中，`argparse` 负责解析命令，`pathlib` 负责处理跨系统路径，
`json` 负责把 Python 数据转换为文件内容以及读取回来，
`datetime.date` 负责校验和比较截止日期。整个项目只使用 Python 标准库。
