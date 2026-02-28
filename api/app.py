"""
FastAPI application factory.

Creates the unified web application with:
- DingTalk webhook handler
- Dashboard web interface
- REST API endpoints
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Investment Analyzer",
        description="投资分析自动化系统",
        version="0.2.0",
    )

    # Templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Include API routes
    from api.routes.analysis import router as analysis_router
    from api.routes.charts import router as charts_router
    from api.routes.dashboard import router as dashboard_router
    from api.routes.dingtalk import router as dingtalk_router
    from api.routes.plans import router as plans_router
    from api.routes.portfolio import router as portfolio_router
    from api.routes.signals import router as signals_router

    app.include_router(dingtalk_router)
    app.include_router(portfolio_router)
    app.include_router(signals_router)
    app.include_router(plans_router)
    app.include_router(analysis_router)
    app.include_router(charts_router)
    app.include_router(dashboard_router)

    # Login
    @app.post("/login")
    async def login(request: Request):
        """Simple token login - set cookie."""
        from config import settings

        try:
            data = await request.json()
        except Exception:
            data = {}

        token = data.get("token", "")
        if not settings.web.auth_token or token == settings.web.auth_token:
            response = RedirectResponse(url="/", status_code=303)
            if settings.web.auth_token:
                response.set_cookie("auth_token", token, httponly=True)
            return response

        return HTMLResponse("认证失败", status_code=401)

    # Dashboard pages (HTML)
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/portfolio", response_class=HTMLResponse)
    async def portfolio_page(request: Request):
        return templates.TemplateResponse("portfolio.html", {"request": request})

    @app.get("/signals", response_class=HTMLResponse)
    async def signals_page(request: Request):
        return templates.TemplateResponse("signals.html", {"request": request})

    @app.get("/plans", response_class=HTMLResponse)
    async def plans_page(request: Request):
        return templates.TemplateResponse("plans.html", {"request": request})

    return app
