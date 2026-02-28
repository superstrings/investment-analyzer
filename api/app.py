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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Paths that don't require authentication
PUBLIC_PATHS = {"/login", "/docs", "/openapi.json", "/favicon.ico"}
# DingTalk webhook doesn't use cookie auth (uses its own verification)
PUBLIC_PREFIXES = ("/api/dingtalk", "/dingtalk/")


class AuthRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated requests to login page."""

    async def dispatch(self, request: Request, call_next):
        from config import settings

        # Skip if no auth configured
        if not settings.web.auth_token:
            return await call_next(request)

        path = request.url.path

        # Allow public paths
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Check authentication
        cookie_token = request.cookies.get("auth_token")
        bearer = request.headers.get("authorization", "")
        query_token = request.query_params.get("token", "")

        authenticated = (
            (cookie_token and cookie_token == settings.web.auth_token)
            or (bearer.startswith("Bearer ") and bearer[7:] == settings.web.auth_token)
            or (query_token and query_token == settings.web.auth_token)
        )

        if not authenticated:
            # API requests get 401; page requests get redirected to login
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            return RedirectResponse(url="/login", status_code=302)

        return await call_next(request)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Investment Analyzer",
        description="投资分析自动化系统",
        version="0.2.0",
    )

    # Auth middleware
    app.add_middleware(AuthRedirectMiddleware)

    # Templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Include API routes
    from api.routes.alerts import router as alerts_router
    from api.routes.analysis import router as analysis_router
    from api.routes.calendar import router as calendar_router
    from api.routes.charts import router as charts_router
    from api.routes.dashboard import router as dashboard_router
    from api.routes.dingtalk import router as dingtalk_router
    from api.routes.manual_positions import router as manual_positions_router
    from api.routes.plans import router as plans_router
    from api.routes.portfolio import router as portfolio_router
    from api.routes.signals import router as signals_router
    from api.routes.stock import router as stock_router
    from api.routes.watchlist import router as watchlist_router

    app.include_router(dingtalk_router)
    app.include_router(alerts_router)
    app.include_router(portfolio_router)
    app.include_router(manual_positions_router)
    app.include_router(watchlist_router)
    app.include_router(signals_router)
    app.include_router(plans_router)
    app.include_router(calendar_router)
    app.include_router(analysis_router)
    app.include_router(charts_router)
    app.include_router(stock_router)
    app.include_router(dashboard_router)

    # Login page
    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Render login page."""
        return templates.TemplateResponse("login.html", {"request": request})

    # Login action
    @app.post("/login")
    async def login(request: Request):
        """Username/password login - set cookie and return JSON."""
        from config import settings

        try:
            data = await request.json()
        except Exception:
            data = {}

        username = data.get("username", "")
        password = data.get("password", "")

        if (
            settings.web.username
            and username == settings.web.username
            and password == settings.web.password
        ):
            response = JSONResponse({"success": True, "redirect": "/"})
            response.set_cookie(
                "auth_token", settings.web.auth_token, httponly=True, samesite="lax"
            )
            return response

        # No auth configured — allow through
        if not settings.web.username and not settings.web.auth_token:
            return JSONResponse({"success": True, "redirect": "/"})

        return JSONResponse(
            {"success": False, "error": "用户名或密码错误"}, status_code=401
        )

    # Dashboard pages (HTML)
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/portfolio", response_class=HTMLResponse)
    async def portfolio_page(request: Request):
        return templates.TemplateResponse("portfolio.html", {"request": request})

    @app.get("/watchlist", response_class=HTMLResponse)
    async def watchlist_page(request: Request):
        return templates.TemplateResponse("watchlist.html", {"request": request})

    @app.get("/signals", response_class=HTMLResponse)
    async def signals_page(request: Request):
        return templates.TemplateResponse("signals.html", {"request": request})

    @app.get("/plans", response_class=HTMLResponse)
    async def plans_page(request: Request):
        return templates.TemplateResponse("plans.html", {"request": request})

    @app.get("/calendar", response_class=HTMLResponse)
    async def calendar_page(request: Request):
        return templates.TemplateResponse("calendar.html", {"request": request})

    @app.get("/stock/{market}/{code}", response_class=HTMLResponse)
    async def stock_page(request: Request, market: str, code: str):
        return templates.TemplateResponse(
            "stock.html", {"request": request, "market": market, "code": code}
        )

    return app
