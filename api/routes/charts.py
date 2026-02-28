"""
Chart serving API routes.
"""

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from api.auth import get_current_user
from config import settings

router = APIRouter(tags=["charts"])


@router.get("/api/charts/{code}")
async def api_chart(
    code: str,
    days: int = 120,
    style: str = "dark",
    username: str = Depends(get_current_user),
):
    """Generate and serve a K-line chart image."""
    try:
        from services.chart_service import BatchChartConfig, create_chart_service

        svc = create_chart_service()
        config = BatchChartConfig(days=days, style=style)
        result = svc.generate_charts_for_codes([code], config=config)

        if result.success and result.generated_files:
            file_path = result.generated_files[0]
            if file_path.exists():
                return FileResponse(
                    str(file_path),
                    media_type="image/png",
                    filename=f"{code}_{days}d.png",
                )

        return {"error": "Chart generation failed", "details": result.error_message}

    except Exception as e:
        return {"error": str(e)}
