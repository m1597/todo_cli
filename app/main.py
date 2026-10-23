from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db


# __file__ 指向 app/main.py；resolve() 得到绝对路径，parent 就是 app 目录。
BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动时建表；关闭时不需要额外清理。"""
    db.init_db()
    yield


app = FastAPI(title="待办清单", lifespan=lifespan)

# 把 URL /static/xxx 映射到 app/static/xxx，浏览器才能加载 CSS 和 JS。
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Jinja2 负责把 templates 里的 HTML 模板渲染成最终页面。
templates = Jinja2Templates(directory=BASE_DIR / "templates")

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
    filters = normalize_filters(status, priority, tag, q, sort)
    return render_index(request, filters=filters, msg=msg)


@app.post("/tasks")
def create_task(
    request: Request,
    title: str = Form(...),
    priority: str = Form("medium"),
    due: str = Form(""),
    tags: str = Form(""),
):
    try:
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
    # POST 之后重定向，刷新页面不会重复提交（PRG 模式）。
    return RedirectResponse("/?msg=added", status_code=303)


@app.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: int):
    new_done = db.toggle_task(task_id)
    if new_done is None:
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
        # 保留用户刚填的内容，方便直接修改。
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
