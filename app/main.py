from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db


# ===========================================================================
# 这个文件是 Web 版的“入口和路由表”。
# 浏览器请求先到 uvicorn，再交给 FastAPI；FastAPI 根据 URL 找到下面的函数。
# 函数负责返回 HTML 页面或重定向，真正的数据操作交给 db.py。
#
# 先理解三件事就够了：
# 1. @app.get(...) / @app.post(...) 是“登记路由”的特殊写法，不是普通调用。
# 2. 参数里的 Form(...) 表示从 HTML 表单里读取字段。
# 3. 修改数据后返回 RedirectResponse，让浏览器重新打开首页。
# ===========================================================================

# __file__ 指向 app/main.py；resolve() 得到绝对路径，parent 就是 app 目录。
BASE_DIR = Path(__file__).resolve().parent


# lifespan 是服务启动、关闭时自动执行的钩子。
# yield 之前做启动准备（建数据库表），yield 之后做清理（这里不需要）。
@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动时建表；关闭时不需要额外清理。"""
    db.init_db()
    yield


# app 是 FastAPI 应用对象；uvicorn 启动时就是找这个变量。
app = FastAPI(title="待办清单", lifespan=lifespan)

# mount 把 /static/... 交给 StaticFiles，直接返回磁盘上的 CSS、JS 等文件。
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Jinja2 负责把 templates 里的 HTML 模板渲染成最终页面。
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# 这些是页面允许的筛选、排序取值，和模板里的下拉框一一对应。
FILTER_STATUSES = ("all", "pending", "done", "overdue")
SORT_OPTIONS = ("id", "priority", "due")

# 重定向时只传短代码，页面再翻译成提示文字，避免把任意文本塞进 URL。
FLASH_MESSAGES = {
    "added": "已添加待办",
    "done": "已标记为完成",
    "undone": "已取消完成",
    "deleted": "已删除待办",
    "cleared": "已清空已完成待办",
    "updated": "已保存修改",
}


def normalize_filters(status="all", priority="", tag="", q="", sort="id"):
    """把 URL 参数收敛到允许的取值，避免非法参数影响查询。"""
    # 用户可以在地址栏随手改参数，所以这里先“洗干净”再交给数据库。
    return {
        "status": status if status in FILTER_STATUSES else "all",
        "priority": priority if priority in db.PRIORITY_LABELS else "",
        "tag": (tag or "").strip(),
        "search": (q or "").strip(),
        "sort": sort if sort in SORT_OPTIONS else "id",
    }


def render_index(
    request: Request,
    filters=None,
    error=None,
    status_code=200,
    form=None,
    msg="",
):
    """准备模板需要的所有数据，然后交给 Jinja2 渲染。"""
    filters = filters or normalize_filters()
    # 表单默认值：出错时用用户刚才填写的内容覆盖默认值。
    form = {
        "title": "",
        "priority": "medium",
        "due": "",
        "tags": "",
        **(form or {}),
    }
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        # context 里的键名，就是模板里可以直接使用的变量名。
        # **filters 是字典解包，等价于 status=..., priority=... 这样逐个传参。
        context={
            "title": "待办清单",
            "tasks": db.list_tasks(**filters),
            "stats": db.stats(),
            "priorities": db.PRIORITY_LABELS,
            "filters": filters,
            "form": form,
            "error": error,
            "flash": FLASH_MESSAGES.get(msg),
        },
        status_code=status_code,
    )


# @app.get 不是“立刻调用函数”，而是告诉 FastAPI：
# 以后收到 GET / 时，请调用下面的 index 函数。
@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    status: str = "all",
    priority: str = "",
    tag: str = "",
    q: str = "",
    sort: str = "id",
    msg: str = "",
):
    """显示待办列表，并支持按条件筛选和排序。"""
    # URL 里 ?status=pending&sort=due 这样的参数，会自动进入同名参数。
    filters = normalize_filters(status, priority, tag, q, sort)
    return render_index(request, filters=filters, msg=msg)


# POST /tasks 接收“添加待办”表单。
# Form(...) 里的 ... 表示这个字段必须提供；Form("") 表示可以不填，默认空字符串。
@app.post("/tasks")
def create_task(
    request: Request,
    title: str = Form(...),
    priority: str = Form("medium"),
    due: str = Form(""),
    tags: str = Form(""),
):
    try:
        # 校验和写入数据库都在 db.py 里，失败时抛出 ValueError。
        db.create_task(title, priority, due, tags)
    except ValueError as error:
        # 校验失败时把错误和刚填的内容一起带回首页。
        form = {
            "title": title,
            "priority": priority if priority in db.PRIORITY_LABELS else "medium",
            "due": due,
            "tags": tags,
        }
        return render_index(request, error=str(error), form=form, status_code=400)
    # 303 是“去另一个地址看看”，浏览器会改成 GET 打开首页。
    # 这样刷新页面不会重复提交表单，叫 PRG（Post / Redirect / Get）。
    return RedirectResponse("/?msg=added", status_code=303)


# 路径里的 {task_id} 会被 FastAPI 转成整数，再传给函数。
@app.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: int):
    new_done = db.toggle_task(task_id)
    if new_done is None:
        # 这里抛出异常，FastAPI 会直接返回 404，后面的代码不再执行。
        raise HTTPException(status_code=404, detail="找不到该待办")
    msg = "done" if new_done else "undone"
    return RedirectResponse(f"/?msg={msg}", status_code=303)


@app.post("/tasks/{task_id}/delete")
def delete_task(task_id: int):
    if not db.delete_task(task_id):
        raise HTTPException(status_code=404, detail="找不到该待办")
    return RedirectResponse("/?msg=deleted", status_code=303)


@app.post("/tasks/clear")
def clear_completed():
    db.clear_completed()
    return RedirectResponse("/?msg=cleared", status_code=303)


# GET 编辑页：先把待办查出来，再把数据交给 edit.html 填写表单。
@app.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_page(request: Request, task_id: int):
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到该待办")
    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "title": f"编辑待办 {task_id}",
            "task": task,
            "priorities": db.PRIORITY_LABELS,
            "error": None,
        },
    )


# POST 编辑页：接收修改后的表单并保存。
@app.post("/tasks/{task_id}/edit")
def update_task(
    request: Request,
    task_id: int,
    title: str = Form(...),
    priority: str = Form("medium"),
    due: str = Form(""),
    tags: str = Form(""),
):
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到该待办")
    try:
        db.update_task(task_id, title, priority, due, tags)
    except ValueError as error:
        # 这里用 submitted 而不是数据库里的 task，是为了保留用户刚改的内容。
        submitted = {
            "id": task_id,
            "title": title,
            "priority": priority if priority in db.PRIORITY_LABELS else "medium",
            "due": due or None,
            "tags": db.parse_tags(tags),
            "done": task["done"],
        }
        return templates.TemplateResponse(
            request=request,
            name="edit.html",
            context={
                "title": f"编辑待办 {task_id}",
                "task": submitted,
                "priorities": db.PRIORITY_LABELS,
                "error": str(error),
            },
            status_code=400,
        )
    return RedirectResponse("/?msg=updated", status_code=303)
