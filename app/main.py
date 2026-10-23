from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# __file__ 指向 app/main.py；resolve() 得到绝对路径，parent 就是 app 目录。
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="待办清单")

# 把 URL /static/xxx 映射到 app/static/xxx，浏览器才能加载 CSS 和 JS。
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Jinja2 负责把 templates 里的 HTML 模板渲染成最终页面。
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """渲染首页；数据库和增删改查会在下一阶段接入。"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "待办清单"},
    )
